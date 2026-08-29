# -*- coding: utf-8 -*-
# //@name:MissAV 中文字幕
# //@id:missav_subtitle
# //@version:5

import ast
import base64
import hashlib
import hmac
import importlib
import json
import re
import threading
import time
from urllib.parse import quote, urlencode, urljoin, urlsplit

# requests 是无指纹回退和外部网关调用的必需传输；curl_cffi 作为可选指纹层。
import requests

try:
    curl_requests = importlib.import_module("curl_cffi.requests")
    HAS_CURL_CFFI = True
except ImportError:
    curl_requests = None
    HAS_CURL_CFFI = False

from lxml import html as lxml_html

from base.spider import Spider as BaseSpider


SCHEMA_DECLARATION = r'''
PLUGIN_CONFIG_SCHEMA = {
  "source": "declared",
  "description": "MissAV 直连插件，支持外部代理网关（FlareSolverr 或自定义）。字幕优先使用 FongMi 原生 subs；Worker 仅用于字幕转码代理或旧客户端 HLS 回退。",
  "allowAdditional": false,
  "fields": [
    {"key": "host", "label": "站点地址", "type": "string", "required": false, "defaultValue": "https://missav.ws"},
    {"key": "cookie", "label": "站点 Cookie", "type": "secret", "required": false, "description": "手动设置的 Cookie，会附加到请求头中。"},
    {"key": "timeout", "label": "请求超时秒数", "type": "number", "required": false, "defaultValue": 12},
    {"key": "gateway_timeout", "label": "FlareSolverr 网关超时秒数", "type": "number", "required": false, "defaultValue": 90, "description": "仅用于 /v1 网关；挑战页可能需要较长时间，建议不低于 90 秒。"},
    {"key": "playlist_timeout", "label": "清晰度清单超时秒数", "type": "number", "required": false, "defaultValue": 4, "description": "仅在 best/1080p/720p/480p 时读取 HLS 主清单；超时或风控后保留主清单，避免延迟起播。"},
    {"key": "play_quality", "label": "播放清晰度策略", "type": "string", "required": false, "defaultValue": "auto", "description": "auto=保留 HLS 主清单，由播放器自动平衡起播速度和清晰度；best=强制最高档；1080p/720p/480p=优先不超过目标高度的档位。"},
    {"key": "subtitle_enabled", "label": "启用中文字幕", "type": "boolean", "required": false, "defaultValue": true},
    {"key": "subtitle_mode", "label": "字幕接入方式", "type": "string", "required": false, "defaultValue": "native", "description": "native=FongMi 原生 subs；hls=Worker 包装视频，仅用于旧客户端。"},
    {"key": "subtitle_worker_base_url", "label": "字幕 Worker 地址", "type": "string", "required": false, "description": "native 模式下用于 SRT 转 VTT；留空时直接使用字幕原地址。"},
    {"key": "subtitle_sources", "label": "字幕来源顺序", "type": "string", "required": false, "defaultValue": "xunlei,subtitlecat"},
    {"key": "subtitle_cache_ttl", "label": "字幕缓存秒数", "type": "number", "required": false, "defaultValue": 21600},
    {"key": "proxy_gateway", "label": "外部代理网关地址", "type": "string", "required": false, "defaultValue": "", "description": "支持实验室现有 FlareSolverr /v1 或自定义 GET 网关。留空则直连。"},
    {"key": "gateway_url", "label": "兼容网关地址", "type": "string", "required": false, "description": "兼容旧版 ext 配置；当 proxy_gateway 未填写时使用。FlareSolverr 地址应以 /v1 结尾。"},
    {"key": "search_api_enabled", "label": "启用公开搜索接口", "type": "boolean", "required": false, "defaultValue": true, "description": "优先使用已验证的 Recombee 搜索接口，失败时回退站点搜索页。"},
    {"key": "impersonate", "label": "浏览器指纹", "type": "string", "required": false, "defaultValue": "safari17_2_ios", "description": "curl_cffi 指纹配置；可填写 safari17_2_ios、chrome124、chrome120、chrome。"},
    {"key": "max_retries", "label": "直连重试次数", "type": "number", "required": false, "defaultValue": 3, "description": "仅当未使用网关时有效，遭遇风控或网络错误时的重试次数。"}
  ]
}
PLUGIN_SCHEMA_END = 1
FILTER_CONFIG_SCHEMA = {
  "source": "declared",
  "description": "通用番号中文字幕过滤器。作用范围由 AList-TVBox 过滤器页面配置，推荐拦截 detail,player。",
  "allowAdditional": false,
  "fields": [
    {"key": "enabled", "label": "启用过滤器", "type": "boolean", "required": false, "defaultValue": true},
    {"key": "subtitle_mode", "label": "字幕接入方式", "type": "string", "required": false, "defaultValue": "native"},
    {"key": "subtitle_worker_base_url", "label": "字幕 Worker 地址", "type": "string", "required": false},
    {"key": "subtitle_sources", "label": "字幕来源顺序", "type": "string", "required": false, "defaultValue": "xunlei,subtitlecat"},
    {"key": "timeout", "label": "字幕请求超时秒数", "type": "number", "required": false, "defaultValue": 10},
    {"key": "subtitle_cache_ttl", "label": "字幕缓存秒数", "type": "number", "required": false, "defaultValue": 21600},
    {"key": "mark_detail", "label": "详情标记识别到的番号", "type": "boolean", "required": false, "defaultValue": false},
    {"key": "overwrite_subs", "label": "覆盖站点已有字幕", "type": "boolean", "required": false, "defaultValue": false}
  ]
}
FILTER_SCHEMA_END = 1
'''


PLUGIN_CONFIG_SCHEMA = {
    "source": "declared",
    "description": "MissAV 直连插件，支持外部代理网关（FlareSolverr 或自定义）。字幕优先使用 FongMi 原生 subs；Worker 仅用于字幕转码代理或旧客户端 HLS 回退。",
    "allowAdditional": False,
    "fields": [
        {"key": "host", "label": "站点地址", "type": "string", "required": False, "defaultValue": "https://missav.ws"},
        {"key": "cookie", "label": "站点 Cookie", "type": "secret", "required": False, "description": "手动设置的 Cookie，会附加到请求头中。"},
        {"key": "timeout", "label": "请求超时秒数", "type": "number", "required": False, "defaultValue": 12},
        {"key": "gateway_timeout", "label": "FlareSolverr 网关超时秒数", "type": "number", "required": False, "defaultValue": 90, "description": "仅用于 /v1 网关；挑战页可能需要较长时间，建议不低于 90 秒。"},
        {"key": "playlist_timeout", "label": "清晰度清单超时秒数", "type": "number", "required": False, "defaultValue": 4, "description": "仅在 best/1080p/720p/480p 时读取 HLS 主清单；超时或风控后保留主清单，避免延迟起播。"},
        {"key": "play_quality", "label": "播放清晰度策略", "type": "string", "required": False, "defaultValue": "auto", "description": "auto=保留 HLS 主清单，由播放器自动平衡起播速度和清晰度；best=强制最高档；1080p/720p/480p=优先不超过目标高度的档位。"},
        {"key": "subtitle_enabled", "label": "启用中文字幕", "type": "boolean", "required": False, "defaultValue": True},
        {"key": "subtitle_mode", "label": "字幕接入方式", "type": "string", "required": False, "defaultValue": "native", "description": "native=FongMi 原生 subs；hls=Worker 包装视频，仅用于旧客户端。"},
        {"key": "subtitle_worker_base_url", "label": "字幕 Worker 地址", "type": "string", "required": False, "description": "native 模式下用于 SRT 转 VTT；留空时直接使用字幕原地址。"},
        {"key": "subtitle_sources", "label": "字幕来源顺序", "type": "string", "required": False, "defaultValue": "xunlei,subtitlecat"},
        {"key": "subtitle_cache_ttl", "label": "字幕缓存秒数", "type": "number", "required": False, "defaultValue": 21600},
        {"key": "proxy_gateway", "label": "外部代理网关地址", "type": "string", "required": False, "defaultValue": "", "description": "支持实验室现有 FlareSolverr /v1 或自定义 GET 网关。留空则直连。"},
        {"key": "gateway_url", "label": "兼容网关地址", "type": "string", "required": False, "description": "兼容旧版 ext 配置；当 proxy_gateway 未填写时使用。FlareSolverr 地址应以 /v1 结尾。"},
        {"key": "search_api_enabled", "label": "启用公开搜索接口", "type": "boolean", "required": False, "defaultValue": True, "description": "优先使用已验证的 Recombee 搜索接口，失败时回退站点搜索页。"},
        {"key": "impersonate", "label": "浏览器指纹", "type": "string", "required": False, "defaultValue": "safari17_2_ios", "description": "curl_cffi 指纹配置；可填写 safari17_2_ios、chrome124、chrome120、chrome。"},
        {"key": "max_retries", "label": "直连重试次数", "type": "number", "required": False, "defaultValue": 3, "description": "仅当未使用网关时有效，遭遇风控或网络错误时的重试次数。"}
    ],
}

FILTER_CONFIG_SCHEMA = {
    "source": "declared",
    "description": "通用番号中文字幕过滤器。作用范围由 AList-TVBox 过滤器页面配置，推荐拦截 detail,player。",
    "allowAdditional": False,
    "fields": [
        {"key": "enabled", "label": "启用过滤器", "type": "boolean", "required": False, "defaultValue": True},
        {"key": "subtitle_mode", "label": "字幕接入方式", "type": "string", "required": False, "defaultValue": "native"},
        {"key": "subtitle_worker_base_url", "label": "字幕 Worker 地址", "type": "string", "required": False},
        {"key": "subtitle_sources", "label": "字幕来源顺序", "type": "string", "required": False, "defaultValue": "xunlei,subtitlecat"},
        {"key": "timeout", "label": "字幕请求超时秒数", "type": "number", "required": False, "defaultValue": 10},
        {"key": "subtitle_cache_ttl", "label": "字幕缓存秒数", "type": "number", "required": False, "defaultValue": 21600},
        {"key": "mark_detail", "label": "详情标记识别到的番号", "type": "boolean", "required": False, "defaultValue": False},
        {"key": "overwrite_subs", "label": "覆盖站点已有字幕", "type": "boolean", "required": False, "defaultValue": False},
    ],
}


DEFAULT_HOST = "https://missav.ws"
XUNLEI_SUBTITLE_API = "https://api-shoulei-ssl.xunlei.com/oracle/subtitle"
SUBTITLECAT_SITE = "https://subtitlecat.com"
DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 11; TV) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SEARCH_API_HOST = "https://client-rapi-missav.recombee.com"
SEARCH_API_DATABASE = "missav-default"
SEARCH_API_TOKEN = "Ikkg568nlM51RHvldlPvc2GzZPE9R4XGzaH9Qj4zK9npbbbTly1gj9K4mgRn0QlV"
DEFAULT_IMPERSONATE = "safari17_2_ios"
IMPERSONATE_ALIASES = {
    "safari17_2_ios": "safari17_2_ios",
    "safari_ios": "safari_ios",
    "safari": "safari",
    "chrome124": "chrome124",
    "chrome120": "chrome120",
    "chrome": "chrome",
}
IMPERSONATE_UA = {
    "safari17_2_ios": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 "
        "Mobile/15E148 Safari/604.1"
    ),
    "chrome124": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "chrome120": DEFAULT_UA,
}
ATVP_DETAIL_PREFIX = "atvp_detail:"
PLAY_PREFIX = "missav-play:"
STATUS_PREFIX = "missav-status:"
# 精确挑战标记（不包含裸 "cloudflare"）
CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "just a moment",
    "attention required",
    "turnstile",
)
CHALLENGE_PLATFORM_MARKERS = (
    "/cdn-cgi/challenge-platform",
    "_cf_chl_opt",
    "challenge-platform",
)
CODE_PATTERNS = (
    re.compile(r"(?<![A-Z0-9])FC2(?:[-_ ]?PPV)?[-_ ]?(\d{5,9})(?![A-Z0-9])", re.I),
    re.compile(r"(?<![A-Z0-9])([A-Z]{2,10})[-_ ]+(\d{2,7})(?![A-Z0-9])", re.I),
    re.compile(r"(?<![A-Z0-9])([A-Z]{2,10})(\d{3,7})(?![A-Z0-9])", re.I),
)
IGNORED_CODE_PREFIXES = frozenset(
    ("AAC", "AVC", "BD", "DVD", "FHD", "FPS", "H264", "H265", "HDR", "HEVC", "UHD", "WEB")
)


def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on", "y")


def _bounded_int(value, default, minimum, maximum):
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def _classify_response(response):
    status = int(getattr(response, "status_code", 0) or 0)
    text = str(getattr(response, "text", "") or "")
    lower = text.lower()
    headers = getattr(response, "headers", {}) or {}
    if any(marker in lower for marker in CHALLENGE_MARKERS):
        return "cloudflare-managed-challenge"
    mitigated = str(headers.get("CF-Mitigated") or headers.get("cf-mitigated") or "").lower()
    if "challenge" in mitigated:
        return "cloudflare-managed-challenge"
    if status >= 400 and any(marker in lower for marker in CHALLENGE_PLATFORM_MARKERS):
        return "cloudflare-managed-challenge"
    if status == 429:
        return "rate-limited"
    if 500 <= status <= 599:
        return "upstream-error"
    if status >= 400:
        return "http-error"
    if not text.strip():
        return "empty-response"
    return "ok"


def _parse_config(value):
    if isinstance(value, dict):
        return dict(value)
    text = str(value or "").strip()
    if not text:
        return {}
    for loader in (json.loads, ast.literal_eval):
        try:
            data = loader(text)
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def _normalize_origin(value):
    text = str(value or DEFAULT_HOST).strip().rstrip("/")
    try:
        parsed = urlsplit(text)
    except Exception:
        return DEFAULT_HOST
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return DEFAULT_HOST
    return parsed.scheme + "://" + parsed.netloc


def _is_flaresolverr_gateway(value):
    """识别 FlareSolverr 的标准 /v1 端点，并允许配置末尾斜杠。"""
    try:
        parsed = urlsplit(str(value or "").strip())
    except Exception:
        return False
    return parsed.scheme in ("http", "https") and parsed.path.rstrip("/") == "/v1"


def _normalize_play_quality(value):
    text = str(value or "auto").strip().lower().replace(" ", "")
    aliases = {
        "auto": "auto",
        "adaptive": "auto",
        "abr": "auto",
        "best": "best",
        "highest": "best",
        "max": "best",
        "1080": "1080",
        "1080p": "1080",
        "720": "720",
        "720p": "720",
        "480": "480",
        "480p": "480",
    }
    return aliases.get(text, "auto")


def _normalize_impersonate(value):
    text = str(value or DEFAULT_IMPERSONATE).strip().lower().replace("-", "_")
    return IMPERSONATE_ALIASES.get(text, DEFAULT_IMPERSONATE)


def _normalize_code(prefix, number):
    upper = str(prefix or "").upper().replace("_", "-").strip("- ")
    digits = str(number or "").strip()
    if not upper or not digits:
        return ""
    if upper.startswith("FC2"):
        return "FC2-PPV-" + digits
    if upper in IGNORED_CODE_PREFIXES:
        return ""
    return upper + "-" + digits


def extract_video_code(*values):
    text = " ".join(_clean_text(value).upper() for value in values if value)
    if not text:
        return ""
    for index, pattern in enumerate(CODE_PATTERNS):
        match = pattern.search(text)
        if not match:
            continue
        if index == 0:
            return "FC2-PPV-" + match.group(1)
        code = _normalize_code(match.group(1), match.group(2))
        if code:
            return code
    return ""


def _code_matches(value, code):
    compact_value = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    compact_code = re.sub(r"[^A-Z0-9]", "", str(code or "").upper())
    return bool(compact_code and compact_code in compact_value)


def _format_duration(seconds):
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    if total <= 0:
        return ""
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return "%02d:%02d:%02d" % (hours, minutes, secs)


def _subtitle_mime(url):
    path = urlsplit(str(url or "")).path.lower()
    if path.endswith(".vtt"):
        return "text/vtt"
    if path.endswith((".ass", ".ssa")):
        return "text/x-ssa"
    return "application/x-subrip"


class SubtitleResolver:
    def _init_subtitle_resolver(self):
        if HAS_CURL_CFFI:
            self._subtitle_session = curl_requests.Session()
        else:
            self._subtitle_session = requests.Session()
        self._subtitle_session.headers.update({"User-Agent": DEFAULT_UA, "Accept-Language": "zh-CN,zh;q=0.9"})
        self._subtitle_enabled = True
        self._subtitle_mode = "native"
        self._subtitle_worker = ""
        self._subtitle_sources = ("xunlei", "subtitlecat")
        self._subtitle_timeout = 10
        self._subtitle_cache_ttl = 21600
        self._subtitle_cache = {}
        self._subtitle_lock = threading.RLock()

    def _configure_subtitles(self, config):
        self._subtitle_enabled = _bool(config.get("subtitle_enabled", config.get("enabled")), True)
        mode = str(config.get("subtitle_mode") or "native").strip().lower()
        self._subtitle_mode = mode if mode in ("native", "hls") else "native"
        self._subtitle_worker = str(config.get("subtitle_worker_base_url") or "").strip().rstrip("/")
        requested = [item.strip().lower() for item in str(config.get("subtitle_sources") or "xunlei,subtitlecat").split(",")]
        self._subtitle_sources = tuple(item for item in requested if item in ("xunlei", "subtitlecat")) or ("xunlei",)
        self._subtitle_timeout = _bounded_int(config.get("timeout"), 10, 3, 30)
        self._subtitle_cache_ttl = _bounded_int(config.get("subtitle_cache_ttl"), 21600, 60, 604800)
        with self._subtitle_lock:
            self._subtitle_cache = {}

    def _subtitle_rows(self, payload):
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        for key in ("data", "results", "items", "subtitles"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = self._subtitle_rows(value)
                if nested:
                    return nested
        return []

    def _find_xunlei_subtitle(self, code):
        try:
            response = self._subtitle_session.get(
                XUNLEI_SUBTITLE_API,
                params={"name": code},
                timeout=self._subtitle_timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return ""
        for row in self._subtitle_rows(payload):
            if not isinstance(row, dict):
                continue
            url = row.get("url") or row.get("subtitle_url") or row.get("download_url")
            if not url:
                continue
            haystack = " ".join(str(row.get(key) or "") for key in ("name", "extra_name")) + " " + str(url)
            if _code_matches(haystack, code):
                return str(url).strip()
        return ""

    def _find_subtitlecat_subtitle(self, code):
        try:
            search = self._subtitle_session.get(
                SUBTITLECAT_SITE + "/index.php",
                params={"search": code},
                timeout=self._subtitle_timeout,
            )
            search.raise_for_status()
            search_document = lxml_html.fromstring(search.text)
            detail_url = ""
            for link in search_document.xpath("//table//tbody//tr//td//a[@href] | //a[@href]"):
                href = str(link.get("href") or "").strip()
                if href and _code_matches(link.text_content() + " " + href, code):
                    detail_url = urljoin(SUBTITLECAT_SITE + "/", href)
                    break
            if not detail_url:
                return ""
            detail = self._subtitle_session.get(detail_url, timeout=self._subtitle_timeout)
            detail.raise_for_status()
            detail_document = lxml_html.fromstring(detail.text)
        except Exception:
            return ""
        candidates = []
        for link in detail_document.xpath("//a[@href]"):
            href = str(link.get("href") or "").strip()
            text = href + " " + link.text_content()
            if re.search(r"\.srt(?:\?|$)|download\.php", href, re.I):
                score = 0
                if re.search(r"zh-CN|zh_CN|simplified|简体", text, re.I):
                    score = 3
                elif re.search(r"zh|cn|chinese|中文", text, re.I):
                    score = 2
                candidates.append((score, urljoin(detail_url, href)))
        if not candidates:
            return ""
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _resolve_subtitle(self, code):
        normalized = extract_video_code(code)
        if not self._subtitle_enabled or not normalized:
            return ""
        now = time.time()
        with self._subtitle_lock:
            cached = self._subtitle_cache.get(normalized)
            if cached and now - cached[0] < self._subtitle_cache_ttl:
                return cached[1]
        subtitle_url = ""
        for source in self._subtitle_sources:
            if source == "xunlei":
                subtitle_url = self._find_xunlei_subtitle(normalized)
            elif source == "subtitlecat":
                subtitle_url = self._find_subtitlecat_subtitle(normalized)
            if subtitle_url:
                break
        with self._subtitle_lock:
            self._subtitle_cache[normalized] = (now, subtitle_url)
        return subtitle_url

    def _subtitle_track(self, subtitle_url):
        source_url = str(subtitle_url or "").strip()
        if not source_url:
            return None
        if self._subtitle_worker:
            proxy_url = self._subtitle_worker + "/subtitle.vtt?" + urlencode({"subtitle": source_url})
            return {"name": "中文字幕", "url": proxy_url, "lang": "zh-CN", "format": "text/vtt", "flag": 1}
        return {
            "name": "中文字幕",
            "url": source_url,
            "lang": "zh-CN",
            "format": _subtitle_mime(source_url),
            "flag": 1,
        }

    def _attach_native_subtitle(self, result, subtitle_url, overwrite=False):
        if not isinstance(result, dict):
            return result
        track = self._subtitle_track(subtitle_url)
        if not track:
            return result
        output = dict(result)
        existing = output.get("subs")
        if isinstance(existing, list) and existing and not overwrite:
            urls = {str(item.get("url") or "") for item in existing if isinstance(item, dict)}
            if track["url"] not in urls:
                output["subs"] = list(existing) + [track]
            return output
        output["subs"] = [track]
        return output

    def _worker_master_url(self, video_url, subtitle_url):
        if not self._subtitle_worker:
            return ""
        return self._subtitle_worker + "/master.m3u8?" + urlencode(
            {"video": str(video_url or ""), "subtitle": str(subtitle_url or "")}
        )

    def _attach_hls_subtitle(self, result, subtitle_url):
        if not isinstance(result, dict) or not self._subtitle_worker:
            return result
        output = dict(result)
        value = output.get("url")

        def wrap(item):
            text = str(item or "").strip()
            if not re.search(r"\.m3u8(?:[?#]|$)", text, re.I):
                return item
            if text.startswith(self._subtitle_worker + "/master.m3u8"):
                return item
            return self._worker_master_url(text, subtitle_url)

        if isinstance(value, list):
            converted = list(value)
            for index in range(1, len(converted), 2):
                converted[index] = wrap(converted[index])
            output["url"] = converted
        elif isinstance(value, str):
            output["url"] = wrap(value)
        return output

    def _attach_subtitle(self, result, code, overwrite=False):
        subtitle_url = self._resolve_subtitle(code)
        if not subtitle_url:
            return result
        if self._subtitle_mode == "hls":
            return self._attach_hls_subtitle(result, subtitle_url)
        return self._attach_native_subtitle(result, subtitle_url, overwrite=overwrite)


class Spider(BaseSpider, SubtitleResolver):
    name = "MissAV 中文字幕"
    backend_parse = False
    category_mode = False

    CATEGORIES = (
        ("today", "今日热门", "/dm242/cn/today-hot", "today_views"),
        ("weekly", "本周热门", "/dm168/cn/weekly-hot", "weekly_views"),
        ("monthly", "本月热门", "/dm207/cn/monthly-hot", "monthly_views"),
        ("release", "新作上市", "/dm509/cn/release", "released_at"),
        ("chinese", "中文字幕", "/dm265/cn/chinese-subtitle", "released_at"),
        ("uncensored", "无码流出", "/dm621/cn/uncensored-leak", "released_at"),
        ("fc2", "FC2", "/dm99/cn/fc2", "released_at"),
    )
    SORTS = (
        ("released_at", "发行日期"),
        ("published_at", "最近更新"),
        ("today_views", "今日浏览"),
        ("weekly_views", "本周浏览"),
        ("monthly_views", "本月浏览"),
        ("views", "总浏览"),
    )

    def __init__(self):
        BaseSpider.__init__(self)
        self._init_subtitle_resolver()
        self.host = DEFAULT_HOST
        self.timeout = 12
        self.gateway_timeout = 90
        self.cookie = ""
        self.playlist_timeout = 4
        self.play_quality = "auto"
        self.proxy_gateway = ""          # 外部网关地址
        self.flare_session = None        # FlareSolverr 服务端浏览器会话 ID
        self.impersonate = DEFAULT_IMPERSONATE
        self.search_api_enabled = True
        self.max_retries = 3
        self._request_lock = threading.Lock()

        self.session = self._build_session()

    def _build_session(self):
        if HAS_CURL_CFFI:
            try:
                session = curl_requests.Session(impersonate=self.impersonate)
            except Exception:
                session = curl_requests.Session()
        else:
            session = requests.Session()
        session.headers.update(
            {
                "User-Agent": IMPERSONATE_UA.get(self.impersonate, DEFAULT_UA),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            }
        )
        if self.cookie:
            session.headers.update({"Cookie": self.cookie})
        return session

    def init(self, extend=""):
        config = _parse_config(extend)
        self.host = _normalize_origin(config.get("host"))
        self.timeout = _bounded_int(config.get("timeout"), 12, 5, 30)
        self.gateway_timeout = _bounded_int(config.get("gateway_timeout"), 90, 10, 180)
        self.cookie = str(config.get("cookie") or "").strip()
        self.playlist_timeout = _bounded_int(config.get("playlist_timeout"), 4, 2, 10)
        self.play_quality = _normalize_play_quality(config.get("play_quality"))
        # proxy_gateway 是 e51 主字段；gateway_url 兼容旧版 ext/merged 配置。
        self.proxy_gateway = str(config.get("proxy_gateway") or config.get("gateway_url") or "").strip()
        if _is_flaresolverr_gateway(self.proxy_gateway):
            self.proxy_gateway = self.proxy_gateway.rstrip("/")
        # init 可能在同一实例上重复调用，不能复用旧网关的浏览器会话。
        self.flare_session = None
        self.impersonate = _normalize_impersonate(config.get("impersonate"))
        self.search_api_enabled = _bool(config.get("search_api_enabled"), True)
        self.max_retries = _bounded_int(config.get("max_retries"), 3, 0, 10)
        self._configure_subtitles(config)
        self.session = self._build_session()
        return None

    def getName(self):
        return self.name

    def homeContent(self, filter=False):
        result = {
            "class": [{"type_id": item[0], "type_name": item[1]} for item in self.CATEGORIES],
            "list": [],
        }
        if filter:
            options = [{"n": label, "v": value} for value, label in self.SORTS]
            result["filters"] = {
                item[0]: [{"key": "sort", "name": "排序", "value": options}]
                for item in self.CATEGORIES
            }
        return result

    def homeVideoContent(self):
        return self.categoryContent("today", "1", False, {})

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = _bounded_int(pg, 1, 1, 100000)
        options = _parse_config(extend)
        category = next((item for item in self.CATEGORIES if item[0] == str(tid)), None)
        if category is None:
            return self._empty_page(page)
        sort_value = str(options.get("sort") or category[3]).strip()
        allowed_sorts = {item[0] for item in self.SORTS}
        if sort_value not in allowed_sorts:
            sort_value = category[3]
        url = self.host + category[2] + "?" + urlencode({"sort": sort_value, "page": page})
        return self._list_page(url, page)

    def _recombee_search(self, keyword, page):
        """先走公开搜索接口，HTML 搜索页失败时仍由原逻辑回退。"""
        if not self.search_api_enabled or page != 1:
            return None
        timestamp = int(time.time())
        user_id = "anon_missav_%x" % timestamp
        path = "/search/users/%s/items/" % quote(user_id, safe="")
        unsigned = "/%s%s?frontend_timestamp=%d" % (
            SEARCH_API_DATABASE,
            path,
            timestamp,
        )
        signature = hmac.new(
            SEARCH_API_TOKEN.encode("utf-8"),
            unsigned.encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()
        url = SEARCH_API_HOST + unsigned + "&frontend_sign=" + signature
        body = {
            "searchQuery": keyword,
            "count": 50,
            "cascadeCreate": True,
            "returnProperties": True,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": self.host,
            "Referer": self.host + "/",
        }
        try:
            response = self.session.post(url, headers=headers, json=body, timeout=self.timeout)
            if _classify_response(response) != "ok":
                return None
            payload = response.json()
        except Exception:
            return None
        rows = payload.get("recomms") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return None
        items = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            values = row.get("values") if isinstance(row.get("values"), dict) else {}
            video_id = _clean_text(row.get("id"))
            if not video_id:
                continue
            title = _clean_text(values.get("title_cn") or values.get("title_zh") or values.get("title") or video_id)
            code = extract_video_code(video_id, title)
            duration = _bounded_int(values.get("duration"), 0, 0, 86400)
            remarks = " · ".join(item for item in (code, _format_duration(duration)) if item)
            if _bool(values.get("has_chinese_subtitle"), False):
                remarks = (remarks + " · 中文字幕").strip(" ·")
            items.append(
                {
                    "vod_id": ATVP_DETAIL_PREFIX + self.host + "/en/" + quote(video_id, safe="-"),
                    "vod_name": title,
                    "vod_pic": "",
                    "vod_remarks": remarks or code,
                    "vod_content": _clean_text(values.get("title_en") or values.get("title") or ""),
                }
            )
        return {
            "list": items,
            "page": page,
            "pagecount": page,
            "limit": len(items),
            "total": len(items),
            "search_source": "recombee",
        }

    def searchContent(self, key, quick=False, pg="1"):
        keyword = _clean_text(key)
        page = _bounded_int(pg, 1, 1, 100000)
        if not keyword:
            return self._empty_page(page)
        api_result = self._recombee_search(keyword, page)
        if api_result is not None:
            requested_code = extract_video_code(keyword)
            if requested_code:
                api_result["list"] = [
                    item
                    for item in api_result.get("list", [])
                    if extract_video_code(item.get("vod_name"), item.get("vod_id")) == requested_code
                ]
                api_result["limit"] = len(api_result["list"])
                api_result["total"] = len(api_result["list"])
            return api_result
        url = self.host + "/cn/search/" + quote(keyword, safe="") + "?" + urlencode({"page": page})
        result = self._list_page(url, page)
        requested_code = extract_video_code(keyword)
        if requested_code:
            result["list"] = [
                item for item in result.get("list", [])
                if extract_video_code(item.get("vod_name"), item.get("vod_id")) == requested_code
            ]
            result["limit"] = len(result["list"])
            result["total"] = len(result["list"])
        return result

    def detailContent(self, ids):
        source_id = ids[0] if isinstance(ids, (list, tuple)) and ids else ids
        value = str(source_id or "").strip()
        if value.startswith(ATVP_DETAIL_PREFIX):
            value = value[len(ATVP_DETAIL_PREFIX):]
        if value.startswith(STATUS_PREFIX):
            return {"list": [self._status_detail(value[len(STATUS_PREFIX):])]}
        detail_url = urljoin(self.host + "/", value)
        try:
            html_text, final_url = self._fetch_url(detail_url, referer=self.host + "/")
            document = lxml_html.fromstring(html_text)
            title = self._meta(document, "property", "og:title") or self._page_title(document)
            title = re.sub(r"\s*-\s*MissAV.*$", "", title, flags=re.I).strip()
            code = extract_video_code(title, final_url)
            if code and not title.upper().startswith(code.replace("-", "")) and code not in title.upper():
                title = code + " " + title
            picture = self._absolute_image(self._meta(document, "property", "og:image"), final_url)
            description = self._meta(document, "property", "og:description") or self._meta(document, "name", "description")
            duration = self._duration_seconds(document)
            uuid = self._extract_uuid(html_text)
            if not uuid:
                return {"list": [self._error_detail(final_url, code, title, picture, "未解析到视频 UUID")]}
            payload = {"detail": final_url, "uuid": uuid, "code": code, "duration": duration}
            play_id = PLAY_PREFIX + self._encode_payload(payload)
            remarks = " · ".join(item for item in (code, _format_duration(duration)) if item)
            return {
                "list": [
                    {
                        "vod_id": final_url,
                        "vod_name": title or code or "MissAV",
                        "vod_pic": picture,
                        "vod_remarks": remarks,
                        "vod_content": _clean_text(description),
                        "vod_play_from": "MissAV",
                        "vod_play_url": "正片$" + play_id,
                    }
                ]
            }
        except Exception as exc:
            return {"list": [self._error_detail(detail_url, extract_video_code(detail_url), "MissAV", "", str(exc))]}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            payload = self._decode_play_id(id)
            detail_url = str(payload.get("detail") or self.host + "/")
            quality = self.play_quality
            if quality == "auto" and self._subtitle_mode == "hls":
                quality = "best"
            video_url = self._resolve_video_url(str(payload.get("uuid") or ""), detail_url, quality)
            if not video_url:
                raise ValueError("未解析到可播放的 m3u8")
            result = {
                "parse": 0,
                "jx": 0,
                "playUrl": "",
                "url": video_url,
                "header": {"User-Agent": DEFAULT_UA, "Referer": detail_url},
            }
            return self._attach_subtitle(result, payload.get("code") or extract_video_code(detail_url))
        except Exception as exc:
            return {
                "parse": 0,
                "jx": 0,
                "playUrl": "",
                "url": "",
                "header": {},
                "msg": _clean_text(exc) or "播放解析失败",
            }

    def localProxy(self, param):
        return [404, "text/plain", None, "not found"]

    def _fetch_url(self, url, referer=None, timeout=None, retries=None):
        """
        统一请求入口。
        若配置了 proxy_gateway，则通过网关获取响应（支持 FlareSolverr 和泛化 GET）。
        否则直连，带重试和精确挑战检测。
        """
        if retries is None:
            retries = self.max_retries if not self.proxy_gateway else 0
        if timeout is None:
            timeout = self.timeout

        if self.proxy_gateway:
            return self._fetch_via_gateway(url, referer, timeout)
        else:
            return self._fetch_direct(url, referer, timeout, retries)

    def _fetch_via_gateway(self, url, referer, timeout):
        """
        网关适配层：
        - 若 gateway 包含 '/v1'，识别为 FlareSolverr，使用 POST JSON API。
        - 否则作为泛化 GET 网关（如 ?url= 参数）处理。
        """
        gateway_url = self.proxy_gateway

        # ----- 分支 1: FlareSolverr 兼容 -----
        if _is_flaresolverr_gateway(gateway_url):
            solver_timeout = max(int(timeout), self.gateway_timeout)
            if self.flare_session is None:
                self.flare_session = self._create_flare_session(gateway_url, solver_timeout)
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": solver_timeout * 1000,  # 毫秒
                "session": self.flare_session,
            }
            flaresolverr_headers = {
                "Referer": referer or self.host + "/",
                "Accept": self.session.headers.get(
                    "Accept",
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                ),
                "Accept-Language": self.session.headers.get(
                    "Accept-Language", "zh-CN,zh;q=0.9,en;q=0.6"
                ),
            }
            payload["headers"] = flaresolverr_headers
            try:
                # 使用 requests 调用 FlareSolverr
                resp = requests.post(gateway_url, json=payload, timeout=solver_timeout + 10)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") != "ok":
                    raise ValueError(f"FlareSolverr 错误: {data.get('message', '')}")
                solution = data.get("solution", {})
                if not isinstance(solution, dict):
                    raise ValueError("FlareSolverr 未返回有效 solution")
                # 更新 cookies
                for cookie in solution.get("cookies", []):
                    self.session.cookies.set(cookie["name"], cookie["value"])
                # 同步 User-Agent
                if solution.get("userAgent"):
                    self.session.headers.update({"User-Agent": solution["userAgent"]})
                # 提取响应内容
                content = solution.get("response")
                if content is None:
                    content = solution.get("body") or ""
                if not str(content).strip():
                    raise ValueError("FlareSolverr 返回空响应")
                final_url = solution.get("url") or solution.get("finalUrl") or url
                return str(content), str(final_url)
            except Exception as e:
                raise ValueError(f"FlareSolverr 调用失败: {str(e)}")

        # ----- 分支 2: 自定义泛化 GET 网关 -----
        if '?' in gateway_url:
            target = gateway_url + '&url=' + quote(url, safe='')
        else:
            target = gateway_url + '?url=' + quote(url, safe='')
        headers = {"User-Agent": DEFAULT_UA}
        if referer:
            headers["Referer"] = referer
        if self.cookie:
            headers["Cookie"] = self.cookie
        try:
            resp = requests.get(target, headers=headers, timeout=timeout + 5)
            resp.raise_for_status()
            content_type = resp.headers.get('content-type', '')
            if 'application/json' in content_type:
                data = resp.json()
                encoded = data.get('body_base64')
                if encoded:
                    try:
                        content = base64.b64decode(str(encoded), validate=True).decode('utf-8', errors='replace')
                    except Exception as exc:
                        raise ValueError('网关返回的 body_base64 无效') from exc
                else:
                    content = data.get('content') or data.get('body') or data.get('text')
                if content is None:
                    content = resp.text
                return content, resp.url
            else:
                return resp.text, resp.url
        except Exception as e:
            raise ValueError(f"网关请求失败: {str(e)}")

    def _create_flare_session(self, gateway_url, solver_timeout):
        """显式创建可复用的 FlareSolverr 浏览器会话。"""
        try:
            resp = requests.post(
                gateway_url,
                json={"cmd": "sessions.create"},
                timeout=solver_timeout + 10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "ok":
                raise ValueError(f"FlareSolverr 会话创建错误: {data.get('message', '')}")
            session_id = data.get("session")
            if not session_id:
                raise ValueError("FlareSolverr 未返回 session")
            return str(session_id)
        except Exception as exc:
            raise ValueError(f"FlareSolverr 会话创建失败: {str(exc)}")

    def _fetch_direct(self, url, referer, timeout, retries):
        """直连请求，带重试和精确挑战检测。"""
        headers = {"User-Agent": DEFAULT_UA}
        if referer:
            headers["Referer"] = referer
        if self.cookie:
            headers["Cookie"] = self.cookie

        last_exc = None
        for attempt in range(retries + 1):
            try:
                resp = self.session.get(url, headers=headers, timeout=timeout)
                if self._is_challenge(resp):
                    if attempt < retries:
                        wait = self._backoff_seconds(resp, attempt)
                        time.sleep(wait)
                        continue
                    raise ValueError("访问被风控（检测到挑战页面），请配置外部代理网关或稍后重试")
                if resp.status_code >= 400:
                    if resp.status_code == 429:
                        wait = self._backoff_seconds(resp, attempt)
                        if attempt < retries:
                            time.sleep(wait)
                            continue
                        raise ValueError(f"请求被限流 (429)，已重试 {retries} 次")
                    else:
                        raise ValueError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                return resp.text, resp.url
            except Exception as e:
                last_exc = e
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                break
        raise last_exc or RuntimeError("请求失败")

    def _is_challenge(self, resp):
        """精确判断是否为挑战页面，避免误判。"""
        return _classify_response(resp) == "cloudflare-managed-challenge"

    def _backoff_seconds(self, resp, attempt):
        """根据 Retry-After 或指数退避计算等待时间。"""
        try:
            retry_after = int(resp.headers.get('Retry-After', '0'))
            if retry_after > 0:
                return min(retry_after, 60)
        except:
            pass
        return min(2 ** (attempt + 1), 30)

    def _request_html(self, url, referer):
        """兼容旧调用。"""
        return self._fetch_url(url, referer)

    def _list_page(self, url, page):
        try:
            html_text, final_url = self._fetch_url(url, referer=self.host + "/")
            items = self._parse_list(html_text, final_url)
            pagecount = self._parse_pagecount(html_text, page)
            if items and pagecount <= page:
                # 当前页面可能不输出完整分页链接，让客户端继续探测下一页。
                pagecount = page + 1
            return {
                "list": items,
                "page": page,
                "pagecount": pagecount,
                "limit": len(items),
                "total": max(len(items), pagecount * max(len(items), 1)),
            }
        except Exception as exc:
            message = _clean_text(exc) or "列表加载失败"
            return {
                "list": [
                    {
                        "vod_id": STATUS_PREFIX + message,
                        "vod_name": "访问受限：" + message,
                        "vod_pic": "",
                        "vod_remarks": "需要用户可见的浏览器验证或稍后重试",
                    }
                ],
                "page": page,
                "pagecount": page,
                "limit": 1,
                "total": 1,
            }

    def _parse_list(self, html_text, base_url):
        document = lxml_html.fromstring(html_text)
        items = []
        seen = set()
        for link in document.xpath("//a[@href]"):
            images = link.xpath(".//img[1]")
            if not images:
                continue
            image = images[0]
            href = str(link.get("href") or "").strip()
            parsed_url = urlsplit(urljoin(base_url, href))
            path = parsed_url.path.rstrip("/")
            match = re.search(
                r"/(?:dm\d+/)?(?:(?:cn|en|ja|ko|ms|th|de|fr|vi|id|fil|pt)/)?"
                r"([a-z0-9][a-z0-9-]+)$",
                path,
                re.I,
            )
            if not match:
                continue
            slug = re.sub(
                r"-(?:chinese-subtitle|english-subtitle|uncensored-leak)$",
                "",
                match.group(1),
                flags=re.I,
            )
            title = _clean_text(link.get("title") or image.get("alt") or link.text_content())
            code = extract_video_code(title, slug)
            full_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            if not code or full_url in seen:
                continue
            seen.add(full_url)
            picture = self._absolute_image(image.get("data-src") or image.get("src"), base_url)
            parent = link.getparent()
            card_text = _clean_text(parent.text_content() if parent is not None else link.text_content())
            duration_match = re.search(r"(?<!\d)(\d{1,2}:\d{2}(?::\d{2})?)(?!\d)", card_text)
            remarks = duration_match.group(1) if duration_match else code
            if title and code not in title.upper():
                title = code + " " + title
            items.append(
                {
                    "vod_id": ATVP_DETAIL_PREFIX + full_url,
                    "vod_name": title or code,
                    "vod_pic": picture,
                    "vod_remarks": remarks,
                }
            )
        return items

    def _parse_pagecount(self, html_text, current):
        pages = [current]
        for match in re.finditer(r"[?&]page=(\d+)", str(html_text or ""), re.I):
            pages.append(_bounded_int(match.group(1), current, 1, 100000))
        return max(pages)

    def _resolve_video_url(self, uuid, detail_url, quality=None):
        if not re.fullmatch(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", uuid, re.I):
            return ""
        playlist_url = "https://surrit.com/%s/playlist.m3u8" % uuid
        selected_quality = _normalize_play_quality(quality if quality is not None else self.play_quality)
        if selected_quality == "auto":
            return playlist_url
        try:
            text, _ = self._fetch_url(playlist_url, referer=detail_url, timeout=self.playlist_timeout, retries=1)
            return self._select_playlist_variant(text, playlist_url, selected_quality)
        except Exception:
            return playlist_url

    @staticmethod
    def _playlist_variants(text, playlist_url):
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        variants = []
        pending = None
        for line in lines:
            if line.startswith("#EXT-X-STREAM-INF:"):
                attributes = {}
                for match in re.finditer(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', line, re.I):
                    attributes[match.group(1).upper()] = match.group(2).strip().strip('"')
                resolution = re.fullmatch(r"(\d+)x(\d+)", attributes.get("RESOLUTION", ""), re.I)
                try:
                    bandwidth = int(attributes.get("BANDWIDTH") or attributes.get("AVERAGE-BANDWIDTH") or 0)
                except (TypeError, ValueError):
                    bandwidth = 0
                pending = {
                    "width": int(resolution.group(1)) if resolution else 0,
                    "height": int(resolution.group(2)) if resolution else 0,
                    "bandwidth": max(bandwidth, 0),
                }
            elif pending is not None and not line.startswith("#"):
                pending["url"] = urljoin(playlist_url, line)
                variants.append(pending)
                pending = None
        return variants

    @staticmethod
    def _select_playlist_variant(text, playlist_url, quality):
        selected_quality = _normalize_play_quality(quality)
        if selected_quality == "auto":
            return playlist_url
        candidates = Spider._playlist_variants(text, playlist_url)
        if not candidates:
            return playlist_url
        score = lambda item: (item["height"], item["width"], item["bandwidth"])
        if selected_quality == "best":
            return max(candidates, key=score)["url"]
        target_height = int(selected_quality)
        within_target = [item for item in candidates if item["height"] and item["height"] <= target_height]
        if within_target:
            return max(within_target, key=score)["url"]
        known_height = [item for item in candidates if item["height"]]
        if known_height:
            return min(known_height, key=score)["url"]
        return min(candidates, key=lambda item: (item["bandwidth"] or 2 ** 63, item["url"]))["url"]

    @staticmethod
    def _pick_best_playlist(text, playlist_url):
        return Spider._select_playlist_variant(text, playlist_url, "best")

    @staticmethod
    def _extract_uuid(html_text):
        text = str(html_text or "")
        patterns = (
            r"nineyu\.com\\?/([a-f0-9-]{36})\\?/seek\\?/_0\.jpg",
            r"surrit\.com\\?/([a-f0-9-]{36})\\?/",
            r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _meta(document, attribute, value):
        if attribute not in ("name", "property"):
            return ""
        values = document.xpath("//meta[@%s=$value]/@content" % attribute, value=value)
        return _clean_text(values[0]) if values else ""

    @staticmethod
    def _page_title(document):
        values = document.xpath("//title[1]")
        return _clean_text(values[0].text_content()) if values else ""

    @staticmethod
    def _duration_seconds(document):
        values = document.xpath("//meta[@property='og:video:duration']/@content")
        return _bounded_int(values[0] if values else 0, 0, 0, 86400)

    @staticmethod
    def _absolute_image(url, base_url):
        value = urljoin(base_url, str(url or "").strip())
        return re.sub(r"/cover-t\.jpg(?=([?#]|$))", "/cover-n.jpg", value, flags=re.I)

    @staticmethod
    def _encode_payload(payload):
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_play_id(value):
        text = str(value or "").strip()
        if not text.startswith(PLAY_PREFIX):
            raise ValueError("不支持的播放 ID")
        encoded = text[len(PLAY_PREFIX):]
        encoded += "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("播放 ID 数据无效")
        return payload

    @staticmethod
    def _empty_page(page):
        return {"list": [], "page": page, "pagecount": page, "limit": 0, "total": 0}

    @staticmethod
    def _status_detail(message):
        return {
            "vod_id": STATUS_PREFIX + str(message or ""),
            "vod_name": "MissAV 状态",
            "vod_pic": "",
            "vod_remarks": "不可播放",
            "vod_content": _clean_text(message),
            "vod_play_from": "",
            "vod_play_url": "",
        }

    @staticmethod
    def _error_detail(vod_id, code, title, picture, message):
        return {
            "vod_id": vod_id,
            "vod_name": title or code or "MissAV",
            "vod_pic": picture,
            "vod_remarks": code or "解析失败",
            "vod_content": _clean_text(message),
            "vod_play_from": "",
            "vod_play_url": "",
        }


class Filter(SubtitleResolver):
    def __init__(self):
        self._init_subtitle_resolver()
        self.enabled = True
        self.mark_detail = False
        self.overwrite_subs = False
        self._play_codes = {}
        self._play_lock = threading.RLock()

    def init(self, extend="", context=None):
        config = _parse_config(extend)
        self.enabled = _bool(config.get("enabled"), True)
        self.mark_detail = _bool(config.get("mark_detail"), False)
        self.overwrite_subs = _bool(config.get("overwrite_subs"), False)
        self._configure_subtitles(config)
        with self._play_lock:
            self._play_codes = {}

    def detail(self, result, context=None):
        if not self.enabled or not isinstance(result, dict):
            return result
        vods = result.get("list")
        if not isinstance(vods, list):
            return result
        output = dict(result)
        filtered = []
        for vod in vods:
            if not isinstance(vod, dict):
                filtered.append(vod)
                continue
            item = dict(vod)
            code = extract_video_code(
                item.get("vod_name"),
                item.get("vod_remarks"),
                item.get("vod_content"),
                item.get("vod_id"),
            )
            if code:
                self._remember_play_codes(item, code)
                if self.mark_detail:
                    remarks = _clean_text(item.get("vod_remarks"))
                    if code not in remarks.upper():
                        item["vod_remarks"] = (remarks + " · 字幕候选 " + code).strip(" ·")
            filtered.append(item)
        output["list"] = filtered
        return output

    def player(self, result, context=None):
        if not self.enabled or not isinstance(result, dict) or not isinstance(context, dict):
            return result
        if str(result.get("parse") if result.get("parse") is not None else 0) not in ("0", "False", "false"):
            return result
        if not result.get("url"):
            return result
        play_id = str(context.get("id") or "").strip()
        with self._play_lock:
            cached_code = self._play_codes.get(play_id, "")
        code = cached_code or extract_video_code(
            context.get("vod_name"),
            context.get("episode_name"),
            context.get("play_from"),
            play_id,
        )
        if not code:
            return result
        return self._attach_subtitle(result, code, overwrite=self.overwrite_subs)

    def _remember_play_codes(self, vod, code):
        values = []
        for group in str(vod.get("vod_play_url") or "").split("$$$"):
            for episode in str(group or "").split("#"):
                label, separator, target = episode.partition("$")
                value = target if separator else label
                if value:
                    values.append(str(value).strip())
        for group in vod.get("group") or []:
            if not isinstance(group, dict):
                continue
            for media in group.get("media") or []:
                if isinstance(media, dict) and media.get("url"):
                    values.append(str(media.get("url")).strip())
        with self._play_lock:
            for value in values:
                if value:
                    self._play_codes[value] = code
