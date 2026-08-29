# -*- coding: utf-8 -*-
#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import sys
sys.path.append("..")
try:
    from base.spider import Spider as _BaseSpider
except ImportError:
    class _BaseSpider:
        pass

try:
    from base.p115 import P115 as _P115
except ImportError:
    _P115 = None


BASE_URL = "https://apidd.spthgb.com"
IMAGE_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
_SIGNING_SECRET = '71cf27bb3c0bcdf207b64abecddc970098c7421ee7203b9cdae54478478a199e7d5a6e1a57691123c1a931c057842fb73ba3b3c83bcd69c17ccf174081e3d8aa'
_SIGNATURE_NONCE = 'lpw6vgqzsp'
_LOGIN_FIELDS_B85 = {
    "username": "Y;1XTW@T<?HZVCrXKi6=Y%XJOZ2",
    "password": "ad%~MG&3?W",
    "device_uuid": "H#lQuFgY<aEjKYRWi2&0GBhn=FfuePHDWn2VmLNsIWRJ2",
    "device_name": "N;WVyMg",
    "device_model": "Ol59wc5g3CWo~bFZy;1cElM^pHbw",
}


class ProtocolError(Exception):
    pass


class SignatureUnavailable(Exception):
    pass


def _private_text(value):
    return base64.b85decode(value.encode("ascii")).decode("utf-8")


def _diagnostic(message):
    return {
        "list": [
            {
                "vod_id": "diagnostic",
                "vod_name": "JAVDB 配置/协议诊断",
                "vod_pic": "",
                "vod_remarks": message,
            }
        ]
    }


def _image_mime(data, header=""):
    for magic, mime in IMAGE_MAGIC:
        if data.startswith(magic):
            return mime
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return header if header.startswith("image/") else "application/octet-stream"


def _image_complete(data, mime):
    if mime == "image/jpeg":
        return _jpeg_complete(data)
    if mime == "image/png":
        return data.endswith(b"IEND\xaeB`\x82")
    if mime == "image/gif":
        return data.endswith(b";")
    if mime == "image/webp" and len(data) >= 12:
        return int.from_bytes(data[4:8], "little") + 8 == len(data)
    return False


def _jpeg_complete(data):
    if not data.startswith(b"\xff\xd8"):
        return False
    offset = 2
    saw_frame = False
    saw_scan = False
    while offset < len(data):
        if data[offset] != 0xFF:
            return False
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            return False
        marker = data[offset]
        offset += 1
        if marker == 0xD9:
            return saw_frame and saw_scan and offset == len(data)
        if marker == 0xD8 or marker == 0x00:
            return False
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            return False
        segment_length = int.from_bytes(data[offset:offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(data):
            return False
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            saw_frame = True
        offset += segment_length
        if marker != 0xDA:
            continue
        saw_scan = True
        while offset < len(data):
            marker_offset = data.find(b"\xff", offset)
            if marker_offset < 0 or marker_offset + 1 >= len(data):
                return False
            following = data[marker_offset + 1]
            if following == 0x00 or 0xD0 <= following <= 0xD7:
                offset = marker_offset + 2
                continue
            offset = marker_offset
            break
    return False


def decode_image_payload(data):
    if not data:
        raise ProtocolError("empty image payload")
    direct_mime = _image_mime(data)
    direct = data.rstrip(b"\r\n") if direct_mime == "image/jpeg" else data
    if direct_mime.startswith("image/") and _image_complete(direct, direct_mime):
        return direct_mime, direct
    key = data[0]
    decoded = bytes(value ^ key for value in data[1:])
    decoded_mime = _image_mime(decoded)
    if decoded_mime == "image/jpeg":
        decoded = decoded.rstrip(b"\r\n")
    if not decoded_mime.startswith("image/") or not _image_complete(decoded, decoded_mime):
        raise ProtocolError("image transform did not produce a complete recognized image")
    return decoded_mime, decoded


def _response_is_complete(response, body_length):
    content_range = response.headers.get("Content-Range")
    if content_range:
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
        return bool(match and int(match.group(1)) == 0 and int(match.group(2)) + 1 == int(match.group(3)) == body_length)
    content_length = response.headers.get("Content-Length")
    return response.status == 200 and (content_length is None or int(content_length) == body_length)


def _normalize_infohash(value):
    candidate = (value or "").strip()
    if candidate.lower().startswith("magnet:"):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(candidate).query)
        xt = next(iter(query.get("xt", [])), "")
        candidate = xt.rsplit(":", 1)[-1]
    if not re.fullmatch(r"[0-9a-fA-F]{40}", candidate):
        raise ValueError("magnet infohash must be 40 hexadecimal characters")
    return candidate.lower()


def _magnet_uri(item):
    infohash = _normalize_infohash(item.get("hash") or item.get("url"))
    magnet = "magnet:?xt=urn:btih:" + infohash
    name = str(item.get("name") or "")
    if not name and str(item.get("url") or "").lower().startswith("magnet:"):
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(str(item["url"])).query)
        name = next(iter(query.get("dn", [])), "")
    if name:
        if not name.startswith("[javdb.com]"):
            name = "[javdb.com]" + name
        magnet += "&dn=" + name
    return magnet


def _magnet_play_id(item):
    infohash = _normalize_infohash(item.get("hash") or item.get("url"))
    name = str(item.get("name") or "")
    encoded_name = base64.urlsafe_b64encode(name.encode("utf-8")).decode("ascii").rstrip("=")
    return "jdbm_" + infohash + "_" + encoded_name


def _magnet_from_play_id(value):
    raw = urllib.parse.unquote(str(value))
    match = re.fullmatch(r"jdbm_([0-9a-fA-F]{40})_([A-Za-z0-9_-]*)", raw)
    if not match:
        return _magnet_uri({"url": raw})
    encoded_name = match.group(2)
    padding = "=" * (-len(encoded_name) % 4)
    try:
        name = base64.urlsafe_b64decode(encoded_name + padding).decode("utf-8") if encoded_name else ""
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("invalid magnet play id") from error
    return _magnet_uri({"hash": match.group(1), "name": name})


def _numeric(item, *names):
    for name in names:
        value = item.get(name)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return 0.0


def _magnet_score(item):
    seeders = _numeric(item, "seeders", "seeds", "heat", "popularity")
    name = str(item.get("name") or "").lower()
    cnsub = bool(item.get("cnsub")) or any(marker in name for marker in ("中文字幕", "中字", "中文", "chinese", "chs", "cht"))
    hd = bool(item.get("hd")) or any(marker in name for marker in ("2160p", "4k", "1080p", "高清", "hd"))
    size = _numeric(item, "size")
    reasonable_size = 1 if 500 <= size <= 8000 else 0
    timestamp = 0.0
    created = str(item.get("created_at") or item.get("release_date") or "")
    match = re.match(r"(20\d{2})[-/]?(\d{2})?[-/]?(\d{2})?", created)
    if match:
        timestamp = int(match.group(1)) * 10000 + int(match.group(2) or 0) * 100 + int(match.group(3) or 0)
    return seeders, int(cnsub), int(hd), reasonable_size, timestamp, -abs(size - 2500)


def rank_magnets(items):
    unique = {}
    for raw in items or []:
        item = dict(raw)
        try:
            infohash = _normalize_infohash(item.get("hash") or item.get("url"))
        except ValueError:
            continue
        item["hash"] = infohash
        previous = unique.get(infohash)
        if previous is None or _magnet_score(item) > _magnet_score(previous):
            unique[infohash] = item
    return sorted(unique.values(), key=_magnet_score, reverse=True)


def _magnet_label(item):
    parts = [str(item.get("name") or item["hash"])]
    if item.get("cnsub"):
        parts.append("中文字幕")
    if item.get("hd"):
        parts.append("高清")
    if item.get("size") is not None:
        parts.append(f"{item['size']} MB")
    if item.get("files_count") is not None:
        parts.append(f"{item['files_count']} 文件")
    if item.get("created_at"):
        parts.append(str(item["created_at"]))
    heat = _numeric(item, "seeders", "seeds", "heat", "popularity")
    if heat:
        parts.append(f"热度/做种 {heat:g}")
    return " · ".join(parts)


class Spider(_BaseSpider):
    filterable = True

    def __init__(self):
        self._initialized = False
        self._token = ""
        self._timeout = 8
        self._image_proxy = False
        self._ssl_context = None

    def getName(self):
        return "JAVDB Private (Read Only)"

    def init(self, extend=""):
        config = {}
        if isinstance(extend, dict):
            config = extend
        elif isinstance(extend, str) and extend.strip().startswith("{"):
            try:
                config = json.loads(extend)
            except ValueError:
                config = {}
        self._token = str(config.get("token") or os.environ.get("JAVDB_BEARER", ""))
        self._timeout = min(15, max(3, int(config.get("timeout") or os.environ.get("JAVDB_TIMEOUT", "8"))))
        self._image_proxy = str(config.get("image_proxy") or os.environ.get("JAVDB_IMAGE_PROXY", "0")).lower() in ("1", "true", "yes")
        self._ssl_context = ssl.create_default_context()
        # 115 公共客户端(秒传/取直链): cookie 统一从 115.json 读取, 实例化即就绪
        self.p115 = _P115() if _P115 else None
        self._initialized = True

    def _login(self):
        boundary = "----javdb-tvbox-" + hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:24]
        fields = {name: _private_text(value) for name, value in _LOGIN_FIELDS_B85.items()}
        fields.update({
            "platform": "android",
            "system_version": "11",
            "app_channel": "official",
            "app_version": "official",
            "app_version_number": "1.9.35",
        })
        body = bytearray()
        for name, value in fields.items():
            body.extend(("--" + boundary + "\r\n").encode())
            body.extend((f'Content-Disposition: form-data; name="{name}"\r\n\r\n').encode())
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")
        body.extend(("--" + boundary + "--\r\n").encode())
        target = "/api/v1/sessions"
        request = urllib.request.Request(
            BASE_URL + target,
            data=bytes(body),
            headers={
                "User-Agent": "Dart/3.5 (dart:io)",
                "Accept-Language": "zh-TW",
                "Accept": "application/json",
                "Content-Type": "multipart/form-data; boundary=" + boundary,
                "jdsignature": self._signature("POST", target),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self._timeout, context=self._ssl_context) as response:
            raw = response.read(1024 * 1024 + 1)
            if response.status != 200 or len(raw) > 1024 * 1024:
                raise ProtocolError("测试账号登录请求失败")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise ProtocolError("测试账号登录响应无效") from error
        token = ((payload.get("data") or {}).get("token") if isinstance(payload, dict) else None)
        if not isinstance(payload, dict) or payload.get("success") != 1 or not isinstance(token, str) or not token:
            raise ProtocolError("测试账号登录未返回有效 token")
        self._token = token

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return None

    def homeContent(self, filter):
        classes = [           
            {"type_id": "top250", "type_name": "TOP250"},
            {"type_id": "hot", "type_name": "热播"},
            {"type_id": "censored", "type_name": "有码"},
            {"type_id": "uncensored", "type_name": "无码"},           
            {"type_id": "fc2", "type_name": "FC2"},
            {"type_id": "western", "type_name": "欧美"},
        ]
        filters = {
            "hot": [
                {"key": "period", "name": "发布时间", "value": [
                    {"n": "每日", "v": ""},
                    {"n": "每周", "v": "weekly"},
                    {"n": "每月", "v": "monthly"},
                    {"n": "每年", "v": "yearly"},
                ]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "高分", "v": ""},
                    {"n": "最新", "v": "recent"},
                    {"n": "播放", "v": "views"},
                    {"n": "周播", "v": "weekly_views"},
                    {"n": "磁力", "v": "magnet"},
                    {"n": "评分", "v": "score"},
                ]},
            ],
            "censored": [
                {"key": "period", "name": "发布时间", "value": [
                    {"n": "每日", "v": ""},
                    {"n": "每周", "v": "weekly"},
                    {"n": "每月", "v": "monthly"},
                    {"n": "每年", "v": "yearly"},
                ]},
            ],
            "uncensored": [
                {"key": "period", "name": "发布时间", "value": [
                    {"n": "每日", "v": ""},
                    {"n": "每周", "v": "weekly"},
                    {"n": "每月", "v": "monthly"},
                    {"n": "每年", "v": "yearly"},
                ]},
            ],
            "western": [
                {"key": "period", "name": "发布时间", "value": [
                    {"n": "每日", "v": ""},
                    {"n": "每周", "v": "weekly"},
                    {"n": "每月", "v": "monthly"},
                    {"n": "每年", "v": "yearly"},
                ]},
            ],
            "fc2": [
                {"key": "period", "name": "发布时间", "value": [
                    {"n": "每日", "v": ""},
                    {"n": "每周", "v": "weekly"},
                    {"n": "每月", "v": "monthly"},
                    {"n": "每年", "v": "yearly"},
                ]},
            ],
        }
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        return self.categoryContent("hot", 1, False, {})

    # type_id -> 接口 path (导航在 homeContent.classes, 路由在此处按 tid 分支, 不塞进导航)
    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid)
        # 路由: hot/top250 各自独立 path; rankings 4 个分类共用同一模板(type 由 TYPE_BY_ID 区分)
        PATH_BY_ID = {
            "hot": "/api/v1/rankings/playback?filter_by=high_score&period=daily",
            "top250": "/api/v1/movies/top?start_rank=1&type=all&type_value=&ignore_watched=false&page={page}&limit=25",
            "rankings": "/api/v1/rankings?type={type}&period=daily",
        }
        # tid -> rankings 接口的 type 取值 (与导航分离, 仅路由用)
        TYPE_BY_ID = {"censored": "0", "uncensored": "1", "western": "2", "fc2": "3"}
        if tid in TYPE_BY_ID:
            path = PATH_BY_ID["rankings"].format(type=TYPE_BY_ID[tid])
        else:
            path = PATH_BY_ID.get(tid)
            if not path:
                return _diagnostic("不支持的分类: %s" % tid)
        page = max(1, int(pg or 1))
        if page > 1 and "{page}" not in path:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}
        # 筛选选中值由框架通过 extend(dict) 传入
        flt = extend if isinstance(extend, dict) else {}
        period = (flt.get("period") or "").strip()
        sort = (flt.get("sort") or "").strip()
        if "{page}" in path:
            path = path.format(page=page)
        if period:
            if "period=" in path:
                path = re.sub(r"period=[^&]*", "period=" + urllib.parse.quote(period, safe=""), path)
            else:
                path += ("&" if "?" in path else "?") + "period=" + urllib.parse.quote(period, safe="")
        if sort and "filter_by=" in path:
            path = re.sub(r"filter_by=[^&]*", "filter_by=" + urllib.parse.quote(sort, safe=""), path)
        try:
            payload = self._api(path)
            movies = (payload.get("data") or {}).get("movies") or []
            return {"list": [self._movie_summary(movie) for movie in movies], "page": page, "pagecount": page + (1 if movies else 0), "limit": len(movies), "total": len(movies)}
        except Exception as error:
            return _diagnostic(self._public_error(error))

    def detailContent(self, ids):
        movie_id = str(ids[0] if isinstance(ids, (list, tuple)) else ids)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", movie_id):
            return _diagnostic("无效影片 ID")
        try:
            detail_payload = self._api("/api/v4/movies/" + urllib.parse.quote(movie_id, safe=""))
            detail_data = detail_payload.get("data") or {}
            movie = detail_data.get("movie") if isinstance(detail_data.get("movie"), dict) else detail_data
            magnet_payload = self._api("/api/v1/movies/" + urllib.parse.quote(movie_id, safe="") + "/magnets")
            magnets = rank_magnets((magnet_payload.get("data") or {}).get("magnets") or [])
            vod = self._movie_detail(movie_id, movie, magnets)
            return {"list": [vod]}
        except Exception as error:
            return _diagnostic(self._public_error(error))

    def searchContent(self, key, quick=False, pg=1):
        return _diagnostic("抓包未证明搜索请求参数；为避免臆造协议，本版本不实现搜索")

    def playerContent(self, flag, id, vipFlags=None):
        # 简单路径: 选集项形态 '标题$magnet', 取最后一个 $ 后的真实磁力 URI 即可
        raw_input = str(id or "")
        magnet = raw_input.rsplit("$", 1)[-1]
        magnet = urllib.parse.unquote(magnet).strip()
        if not magnet.lower().startswith("magnet:?"):
            # 不是磁力(异常数据) -> 退回原样, 让播放器自行处理
            return {"parse": 0, "url": raw_input, "header": {}}

        # 走 115 秒传取直链(内部已排除广告/预览小文件, 取体积最大正片); 失败则退回裸磁力
        if self.p115 is not None:
            pc = self.p115.offline_magnet(magnet)
            if pc:
                uh = self.p115.get_direct_url(pc)
                u, h = (uh if isinstance(uh, tuple) else (uh, {}))
                if u:
                    return {"parse": 0, "url": u, "header": h or {}}
        return {"parse": 0, "url": magnet, "header": {}}

    def localProxy(self, params):
        url = urllib.parse.unquote(str((params or {}).get("url") or ""))
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "tp.spfcas.com":
            return [403, "text/plain; charset=utf-8", b"image host rejected"]
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "JAVDB-TVBox-Private/1.0", "Accept": "image/*"})
            with urllib.request.urlopen(request, timeout=self._timeout, context=self._ssl_context or ssl.create_default_context()) as response:
                body = response.read(8 * 1024 * 1024 + 1)
                if len(body) > 8 * 1024 * 1024:
                    return [413, "text/plain; charset=utf-8", b"image too large"]
                if not _response_is_complete(response, len(body)):
                    return [502, "text/plain; charset=utf-8", b"upstream image is incomplete"]
                mime, decoded = decode_image_payload(body)
                return [200, mime, decoded]
        except Exception:
            return [502, "text/plain; charset=utf-8", b"image proxy failed"]

    def _ensure_initialized(self):
        if not self._initialized:
            self.init("")

    def _signature(self, method, target):
        del method, target
        timestamp = int(time.time())
        digest = hashlib.md5((str(timestamp) + _SIGNING_SECRET).encode()).hexdigest()
        return f"{timestamp}.{_SIGNATURE_NONCE}.{digest}"

    def _api(self, target):
        self._ensure_initialized()
        if not self._token:
            self._login()
        headers = {"User-Agent": "Dart/3.5 (dart:io)", "Accept-Language": "zh-TW", "Accept": "application/json"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        headers["jdsignature"] = self._signature("GET", target)
        request = urllib.request.Request(BASE_URL + target, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=self._timeout, context=self._ssl_context) as response:
            body = response.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                raise ProtocolError("API response exceeds 4 MiB bound")
            if response.status != 200:
                raise ProtocolError("HTTP status is not 200")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise ProtocolError("API response is not UTF-8 JSON") from error
        if not isinstance(payload, dict) or payload.get("success") != 1:
            raise ProtocolError("API business success assertion failed")
        return payload

    def _movie_summary(self, movie):
        remarks = [str(movie.get("number") or "")]
        if movie.get("release_date"):
            remarks.append(str(movie["release_date"]))
        if movie.get("has_cnsub"):
            remarks.append("中文字幕")
        if movie.get("magnets_count") is not None:
            remarks.append(f"{movie['magnets_count']} 磁力")
        picture = str(movie.get("thumb_url") or movie.get("cover_url") or "")
        if picture.startswith("https://tp.spfcas.com/"):
            try:
                proxy_base = self.getProxyUrl()
            except Exception:
                proxy_base = ""
            if proxy_base:
                picture = proxy_base + "&do=py&type=javdb_cover&url=" + urllib.parse.quote(picture, safe="")
        return {"vod_id": str(movie.get("id") or ""), "vod_name": str(movie.get("title") or movie.get("origin_title") or movie.get("number") or "未知标题"), "vod_pic": picture, "vod_remarks": " · ".join(part for part in remarks if part)}

    def _movie_detail(self, movie_id, movie, magnets):
        summary = self._movie_summary(dict(movie, id=movie_id))
        # 简单路径: 详情页不碰 115(零请求, 不转圈), 把每个磁力铺成选集项,
        # 播放时 playerContent 才离线取链。选集项形态: '标题$magnet'
        urls = []
        for item in magnets:
            label = _magnet_label(item)
            magnet = _magnet_uri(item)
            # 选集项标题: 原磁力标签(含字幕/清晰度/大小) + 115 标记; 后面跟纯磁力 URI
            ep = (label + "  [115]").replace("$", " ")
            urls.append("%s$%s" % (ep, magnet))
        summary.update({
            "vod_year": str(movie.get("release_date") or "")[:4],
            "vod_area": str(movie.get("area") or movie.get("country") or ""),
            "vod_actor": self._join_names(movie.get("actors")),
            "vod_director": self._join_names(movie.get("directors")),
            "vod_content": str(movie.get("description") or movie.get("summary") or movie.get("title") or ""),
            "vod_play_from": "115",
            "vod_play_url": "#".join(urls),
        })
        return summary

    @staticmethod
    def _join_names(value):
        if not isinstance(value, list):
            return str(value or "")
        return ", ".join(str(item.get("name") if isinstance(item, dict) else item) for item in value)

    @staticmethod
    def _public_error(error):
        if isinstance(error, SignatureUnavailable):
            return str(error)
        if isinstance(error, ProtocolError):
            return str(error)
        if isinstance(error, urllib.error.HTTPError):
            return f"API HTTP 错误 {error.code}"
        if isinstance(error, urllib.error.URLError):
            return "API 网络连接失败"
        return "客户端只读请求失败: " + type(error).__name__