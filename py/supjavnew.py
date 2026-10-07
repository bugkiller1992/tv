# coding: utf-8
import re
import json
import base64
from urllib.parse import urlencode, quote, unquote
from spider import Spider

class Spider(Spider):
    def getName(self):
        return "SupJav"

    def init(self, extend=""):
        self.host = "https://supjav.com"
        self.proxy_base = "https://py.fzcrym.link:1314"
        self.stream_api = self.proxy_base + "/stream?u="
        self.sj_hls_api = self.proxy_base + "/sj_hls?u="
        self.lk_base = "https://lk1.supremejav.com/supjav.php"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/"
        }

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def action(self, action):
        pass

    # 设置默认横屏 16:9 样式，防止卡片裁剪图片
    def get_land_style(self):
        return {
            "type": "rect",
            "ratio": 1.78
        }

    def homeContent(self, filter):
        result = {}
        cateManual = [
            {"type_id": "popular", "type_name": "热门"},
            {"type_id": "category/censored-jav", "type_name": "有码"},
            {"type_id": "category/uncensored-jav", "type_name": "无码"},
            {"type_id": "category/amateur", "type_name": "素人"},
            {"type_id": "category/chinese-subtitles", "type_name": "中文字幕"},
            {"type_id": "category/reducing-mosaic", "type_name": "无码破解"},
            {"type_id": "category/english-subtitles", "type_name": "英文字幕"}
        ]
        result['class'] = cateManual
        
        # 获取首页推荐视频
        try:
            html = self.fetch(self.host + "/zh/", headers=self.header).text
            result['list'] = self.parse_list(html)
        except Exception:
            result['list'] = []

        result['style'] = self.get_land_style()
        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        pg = str(pg) if pg else "1"
        
        if tid == "popular":
            url = f"{self.host}/zh/popular/page/{pg}"
        else:
            url = f"{self.host}/zh/{tid}/page/{pg}"

        try:
            html = self.fetch(url, headers=self.header).text
            vod_list = self.parse_list(html)
            page_count = self.parse_page_count(html)
        except Exception:
            vod_list = []
            page_count = 1

        result['list'] = vod_list
        result['page'] = pg
        result['pagecount'] = page_count
        result['limit'] = 20
        result['total'] = 999
        result['style'] = self.get_land_style()
        return result

    def detailContent(self, array):
        vid = array[0]
        url = f"{self.host}/zh/{vid}.html" if not vid.startswith("http") else vid
        
        try:
            html = self.fetch(url, headers=self.header).text
        except Exception:
            return {"list": []}

        # 匹配标题与封面
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        title = title_match.group(1).strip() if title_match else vid
        title = re.sub(r'<[^>]+>', '', title)

        pic_match = re.search(r'<div class="post-meta">.*?<img[^>]+src=["\']([^"\']+)["\']', html, re.S)
        pic = pic_match.group(1) if pic_match else ""

        # 匹配标签/演员
        tags = re.findall(r'<a href="[^"]*tag/[^"]*"[^>]*>(.*?)</a>', html)
        remarks = " ".join(tags) if tags else ""

        # 匹配线路 Hex 代码 (data-link)
        links = re.findall(r'data-link=["\']([0-9a-fA-F]{40,})["\']', html)
        names = re.findall(r'<a[^>]+data-link=["\'][^"\']+["\'][^>]*>(.*?)</a>', html)

        vod_play_from = []
        vod_play_url = []

        if links:
            for idx, lk in enumerate(links):
                name = names[idx].strip() if idx < len(names) else f"线路 {idx + 1}"
                vod_play_from.append(name)
                vod_play_url.append(f"正片${vid}|{lk}")
        else:
            vod_play_from.append("SupJav")
            vod_play_url.append(f"正片${vid}|")

        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": remarks,
            "vod_actor": "",
            "vod_director": "",
            "vod_content": title,
            "vod_play_from": "$$$".join(vod_play_from),
            "vod_play_url": "$$$".join(vod_play_url),
            "style": self.get_land_style()
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg=1):
        url = f"{self.host}/zh/page/{pg}?s={quote(key)}"
        try:
            html = self.fetch(url, headers=self.header).text
            vod_list = self.parse_list(html)
            page_count = self.parse_page_count(html)
        except Exception:
            vod_list = []
            page_count = 1

        return {
            "list": vod_list,
            "page": pg,
            "pagecount": page_count,
            "limit": 20,
            "total": 999,
            "style": self.get_land_style()
        }

    def playerContent(self, flag, id, vipFlags):
        parts = id.split("|")
        vid = parts[0]
        lk = parts[1] if len(parts) > 1 else ""

        if not lk:
            return {"parse": 0, "url": ""}

        detail_url = f"{self.host}/zh/{vid}.html"
        s1_url = f"{self.lk_base}?l={lk}"
        
        # 第一阶段：请求 supjav.php?l=
        s1 = self.fetch(self.stream_api + quote(s1_url) + "&r=" + quote(detail_url), headers=self.header).text

        # 翻转 OLID
        om = re.search(r"var\s+OLID\s*=\s*'([0-9a-f]{40,})'", s1)
        if om:
            olid = om.group(1)[::-1]
        else:
            olid = lk[::-1]

        # 第二阶段：请求 supjav.php?c=
        s2_url = f"{self.lk_base}?c={olid}"
        s2 = self.fetch(self.stream_api + quote(s2_url) + "&r=" + quote(s1_url), headers=self.header).text

        # 提取真正的流地址
        stream = self.extract_stream(s2, s1_url)
        if not stream.get("m3u8") and not stream.get("direct"):
            return {"parse": 0, "url": ""}

        if stream.get("direct"):
            return {
                "parse": 0,
                "url": stream["direct"],
                "header": self.header
            }

        m3u8 = stream["m3u8"].replace("\\", "")
        if "turboviplay" in m3u8.lower() or "turbosplayer" in m3u8.lower():
            play_url = self.sj_hls_api + quote(m3u8)
        else:
            play_url = self.stream_api + quote(m3u8)

        return {
            "parse": 0,
            "url": play_url,
            "header": self.header
        }

    def parse_list(self, html):
        vod_list = []
        # 匹配列表块
        posts = re.findall(r'<div class="post[^"]*">(.*?)</div>\s*</div>', html, re.S)
        if not posts:
            posts = re.findall(r'<div class="post[^"]*">(.*?)</article>', html, re.S)

        for post in posts:
            link_match = re.search(r'href=["\']([^"\']+)["\']', post)
            if not link_match:
                continue
            
            raw_url = link_match.group(1)
            vod_id = raw_url.rstrip("/").split("/")[-1].replace(".html", "")

            title_match = re.search(r'title=["\']([^"\']+)["\']', post) or re.search(r'alt=["\']([^"\']+)["\']', post)
            title = title_match.group(1).strip() if title_match else vod_id

            pic_match = re.search(r'data-original=["\']([^"\']+)["\']', post) or \
                        re.search(r'data-src=["\']([^"\']+)["\']', post) or \
                        re.search(r'src=["\']([^"\']+)["\']', post)
            pic = pic_match.group(1) if pic_match else ""

            remarks_match = re.search(r'<span class="date">(.*?)</span>', post)
            remarks = remarks_match.group(1).strip() if remarks_match else ""

            vod_list.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks,
                "style": self.get_land_style()
            })
        return vod_list

    def parse_page_count(self, html):
        pages = re.findall(r'<a class="page-numbers"[^>]*>(\d+)</a>', html)
        if pages:
            return max([int(p) for p in pages])
        return 1

    def unpack(self, text):
        m = re.search(r"}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)", text)
        if not m:
            return ""
        payload, base_str, count_str, keys_str = m.groups()
        base = int(base_str)
        count = int(count_str)
        keys = keys_str.split("|")
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"

        def enc(num):
            out = ""
            while num > 0:
                out = digits[num % base] + out
                num //= base
            return out or "0"

        table = {}
        for i in range(count):
            if i < len(keys) and keys[i]:
                table[enc(i)] = keys[i]

        def replace_word(match):
            word = match.group(0)
            return table.get(word, word)

        return re.sub(r"\b\w+\b", replace_word, payload)

    def voe_decode(self, html):
        m = re.search(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.S)
        if not m:
            return {}
        raw = m.group(1).strip()
        try:
            j = json.loads(raw)
            if isinstance(j, list) and len(j) > 0:
                raw = j[0]
        except Exception:
            pass

        s = str(raw)
        for k in ["@$", "^^", "~@", "%?", "*~", "!!", "#&"]:
            s = s.replace(k, "_")
        s = s.replace("_", "")

        def b64d(x):
            x = re.sub(r"[^A-Za-z0-9+/=]", "", x)
            x += "=" * ((4 - len(x) % 4) % 4)
            return base64.b64decode(x).decode("utf-8", errors="ignore")

        try:
            # ROT13 解密
            rot = ""
            for c in s:
                if "a" <= c <= "z":
                    rot += chr((ord(c) - ord("a") + 13) % 26 + ord("a"))
                elif "A" <= c <= "Z":
                    rot += chr((ord(c) - ord("A") + 13) % 26 + ord("A"))
                else:
                    rot += c
            t1 = b64d(rot)
            t2 = "".join([chr(ord(c) - 3) for c in t1])
            t3 = b64d(t2[::-1])
            return json.loads(t3)
        except Exception:
            return {}

    def extract_stream(self, s2, ref):
        if not s2:
            return {"m3u8": "", "direct": ""}

        # 直取 m3u8
        hits = re.findall(r'https?://[^\s"\'<>\\]+?\.m3u8[^\s"\'<>\\]*', s2)
        if hits:
            return {"m3u8": hits[0].replace("\\", ""), "direct": ""}

        # Packer
        if "eval(function(p,a,c,k,e" in s2:
            dec = self.unpack(s2)
            dhits = re.findall(r'https?://[^\s"\'<>\\]+?\.m3u8[^\s"\'<>\\]*', dec)
            if dhits:
                return {"m3u8": dhits[0].replace("\\", ""), "direct": ""}

        # VOE
        tgt = re.findall(r"window\.location\.href\s*=\s*'([^']+)'", s2)
        if not tgt:
            tgt = re.findall(r'https?://[a-z0-9.-]+/e/[a-z0-9]{8,}', s2)
        if tgt:
            page = self.fetch(self.stream_api + quote(tgt[0]) + "&r=" + quote(ref), headers=self.header).text
            cfg = self.voe_decode(page)
            src = str(cfg.get("source", ""))
            if ".m3u8" in src:
                return {"m3u8": src, "direct": ""}
            dau = str(cfg.get("direct_access_url", ""))
            if dau.startswith("http"):
                return {"m3u8": "", "direct": dau}
            if src.startswith("http"):
                return {"m3u8": "", "direct": src}

        return {"m3u8": "", "direct": ""}

