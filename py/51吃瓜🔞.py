# -*- coding: utf-8 -*-
# TG交流群 https://t.me/hshsjk9

import re, json, time, random
from urllib.parse import quote
try:
    import requests as _requests
except Exception:
    _requests = None
try:
    from Crypto.Cipher import AES as _AES
    from Crypto.Util.Padding import unpad as _unpad
except Exception:
    _AES = None
    _unpad = None


class Spider:
    def __init__(self):
        self.site = "https://attack.fjsxfbcm.cc"
        self.name = "51吃瓜"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _requests.Session() if _requests else None
        self._extend = {}
        self._verified = False
        self._opener = None
        self._img_key = b"f5d965df75336270"
        self._img_iv = b"97b60394abc2fbe1"
        self.cats = [
            ("mrds", "每日大赛"),
            ("whhj", "网黄合集"),
            ("mrdg", "吃瓜榜单"),
            ("qghj", "瓜友点播"),
            ("rdsj", "热门大瓜"),
            ("bkdg", "必看大瓜"),
            ("ysyl", "成人视频"),
            ("lldd", "伦理道德"),
            ("gcjq", "国产视频"),
            ("thjx", "探花精选"),
            ("xsxy", "学生校园"),
            ("whhl", "网红黑料"),
            ("snsn", "骚男骚女"),
            ("whmx", "明星爆料"),
            ("hwcg", "海外吃瓜"),
            ("rrcg", "人人吃瓜"),
            ("ldcg", "领导干部"),
            ("jpll", "软萌甜妹"),
            ("sjb", "竞技吃瓜"),
            ("qubk", "吃瓜看戏"),
            ("dcbq", "擦边撩骚"),
            ("zzs", "性爱技巧"),
            ("cgxw", "吃瓜新闻"),
            ("yczq", "原创博主"),
            ("51djc", "51剧场"),
            ("51hd", "往期活动"),
        ]

    def getDependence(self):
        return []

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return u.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi")) or "m3u8" in u

    def destroy(self):
        pass

    def action(self, action):
        return {}

    def _opener_get(self):
        if self._opener is None:
            import urllib.request
            import http.cookiejar
            jar = http.cookiejar.CookieJar()
            self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        return self._opener

    def _verify(self, force=False):
        if self._verified and not force:
            return True
        data = {
            "challenge": hex(random.getrandbits(52))[2:] + hex(int(time.time() * 1000))[2:],
            "width": 1920,
            "height": 1080,
            "language": "zh-CN",
            "platform": "Win32",
            "webdriver": 0,
            "timezone": "Asia/Shanghai",
        }
        url = self.site + "/browser-check.php?t=" + str(int(time.time() * 1000))
        h = dict(self.header)
        h["Content-Type"] = "application/json"
        h["Referer"] = self.site + "/verification.html?return=%2F"
        if self.s is not None:
            try:
                r = self.s.post(url, json=data, headers=h, timeout=12)
                if r.status_code == 200:
                    d = r.json()
                    if isinstance(d, dict) and d.get("success") is True:
                        self._verified = True
                        return True
            except Exception:
                pass
        try:
            import urllib.request
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=h, method="POST")
            with self._opener_get().open(req, timeout=12) as resp:
                d = json.loads(resp.read().decode("utf-8", "ignore"))
                if isinstance(d, dict) and d.get("success") is True:
                    self._verified = True
                    return True
        except Exception:
            pass
        return False

    def _get(self, url, referer=None):
        h = dict(self.header)
        if referer:
            h["Referer"] = referer
        if not self._verified:
            self._verify()
        txt = self._fetch_text(url, h)
        if txt and "正在验证" in txt[:2000] and "<title>正在验证</title>" in txt:
            self._verify(force=True)
            txt = self._fetch_text(url, h)
        return txt

    def _fetch_text(self, url, h):
        if self.s is not None:
            try:
                r = self.s.get(url, headers=h, timeout=12, allow_redirects=True)
                if r.status_code < 400:
                    if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
                        r.encoding = "utf-8"
                    return r.text
            except Exception:
                pass
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=h)
            with self._opener_get().open(req, timeout=12) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception:
            return ""

    def _bytes(self, url, referer=None):
        h = dict(self.header)
        if referer:
            h["Referer"] = referer
        if self.s is not None:
            try:
                r = self.s.get(url, headers=h, timeout=15)
                if r.status_code == 200 and r.content:
                    return r.content
            except Exception:
                pass
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=h)
            with self._opener_get().open(req, timeout=15) as resp:
                return resp.read()
        except Exception:
            return b""

    def _u(self, u):
        if not u:
            return u
        u = u.strip()
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http"):
            return u
        if u.startswith("/"):
            m = re.match(r"(https?://[^/]+)", self.site)
            return (m.group(1) if m else self.site) + u
        return self.site.rstrip("/") + "/" + u.lstrip("/")

    def _img(self, url):
        if not url or _AES is None:
            return b"", ""
        raw = self._bytes(url)
        if not raw:
            return b"", ""
        try:
            dec = _unpad(_AES.new(self._img_key, _AES.MODE_CBC, self._img_iv).decrypt(raw), 16)
        except Exception:
            return b"", ""
        if dec[:3] == b"\xff\xd8\xff":
            return dec, "image/jpeg"
        if dec[:4] == b"\x89PNG":
            return dec, "image/png"
        if dec[:4] == b"RIFF" and dec[8:12] == b"WEBP":
            return dec, "image/webp"
        if dec[:2] == b"\xff\xd8":
            return dec, "image/jpeg"
        return b"", ""

    def _wrap_img(self, u):
        if not u:
            return ""
        try:
            return self.getProxyUrl() + "&url=" + quote("img:" + u)
        except Exception:
            return "http://127.0.0.1:9978/proxy?do=py&url=" + quote("img:" + u)

    def _items(self, html):
        out = []
        seen = set()
        parts = re.split(r'id="post-card-(\d+)"', html)
        for i in range(1, len(parts) - 1, 2):
            pid = parts[i]
            seg = parts[i + 1][:4000]
            cov = re.search(r'(?:[xz]-(?:bg|image)-loader-url)="([^"]+)"', seg)
            tit = re.search(r'<h2 class="post-card-title"[^>]*>([^<]+)</h2>', seg)
            if pid in seen or not tit:
                continue
            seen.add(pid)
            title = _html_unescape(tit.group(1)).strip()
            if not title:
                continue
            pic = self._u(cov.group(1)) if cov else ""
            out.append({
                "vod_id": pid,
                "vod_name": title,
                "vod_pic": self._wrap_img(pic) if pic else "",
                "vod_remarks": "",
            })
        return out

    def _pagecount(self, html):
        m = re.search(r"var total\s*=\s*(\d+)", html)
        if m:
            return int(m.group(1))
        pages = re.findall(r'/category/[^/]+/(\d+)/', html)
        if pages:
            try:
                return max(int(n) for n in pages if int(n) < 100000)
            except ValueError:
                pass
        pages = re.findall(r'/search/[^/]+/(\d+)/', html)
        if pages:
            try:
                return max(int(n) for n in pages if int(n) < 100000)
            except ValueError:
                pass
        return 1

    def _video_urls(self, html):
        urls = []
        for m in re.finditer(r'"video":\{"url":"((?:https?:)?[^"]*?\.m3u8[^"]*)"', html):
            u = m.group(1).replace("\\/", "/")
            if u.startswith("//"):
                u = "https:" + u
            urls.append(u)
        return urls

    def init(self, extend=""):
        self._extend = {}
        if isinstance(extend, dict):
            self._extend = extend
        elif isinstance(extend, str) and extend.strip():
            try:
                e = json.loads(extend)
                if isinstance(e, dict):
                    self._extend = e
            except Exception:
                pass

    def homeContent(self, filter=None):
        cats = [{"type_id": slug, "type_name": name} for slug, name in self.cats]
        html = self._get(self.site + "/")
        return {"class": cats, "filters": {}, "list": self._items(html)}

    def homeVideoContent(self):
        return {"list": self._items(self._get(self.site + "/"))}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        slug = str(tid)
        if pg <= 1:
            url = self.site + "/category/" + slug + "/"
        else:
            url = self.site + "/category/" + slug + "/" + str(pg) + "/"
        html = self._get(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 25, "total": 0}
        items = self._items(html)
        pc = self._pagecount(html)
        return {"list": items, "page": pg, "pagecount": pc, "limit": 25, "total": pc * 25}

    def detailContent(self, ids):
        vid = ids
        if isinstance(ids, (list, tuple)):
            vid = ids[0] if ids else ""
        vid = str(vid).strip()
        m = re.search(r"(\d+)", vid)
        if not m:
            return {"list": []}
        pid = m.group(1)
        url = self.site + "/archives/" + pid + "/"
        html = self._get(url)
        if not html:
            return {"list": []}
        title = ""
        tm = re.search(r'<h1[^>]*>([^<]{2,120})</h1>', html)
        if tm:
            title = _html_unescape(tm.group(1)).strip()
        if not title:
            tm = re.search(r'<title>([^<]{2,120})</title>', html)
            if tm:
                title = _html_unescape(tm.group(1)).split(" | ")[0].strip()
        pic = ""
        im = re.search(r'itemprop="image" content="([^"]+)"', html)
        if im:
            pic = self._u(im.group(1))
        desc = ""
        dm = re.search(r'property="og:description" content="([^"]*)"', html)
        if dm:
            desc = _html_unescape(dm.group(1)).strip()
        urls = self._video_urls(html)
        eps = []
        for idx in range(len(urls)):
            eps.append("第" + str(idx + 1) + "集$" + url + "?ep=" + str(idx + 1))
        return {"list": [{"vod_id": pid, "vod_name": title, "vod_pic": self._wrap_img(pic) if pic else "",
                          "vod_content": desc, "vod_play_from": self.name,
                          "vod_play_url": "#".join(eps)}]}

    def searchContent(self, key, quick=False, pg="1"):
        key = str(key or "").strip()
        if not key:
            return {"list": []}
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        q = quote(key)
        if pg <= 1:
            url = self.site + "/search/" + q + "/"
        else:
            url = self.site + "/search/" + q + "/" + str(pg) + "/"
        html = self._get(url)
        if not html:
            return {"list": []}
        return {"list": self._items(html)}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids
        if isinstance(ids, (list, tuple)):
            url = ids[0] if ids else ""
        url = str(url or "").strip()
        m = re.search(r"/archives/(\d+)/", url)
        if not m:
            m = re.search(r"(\d+)", url)
        if not m:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        pid = m.group(1)
        ep = 1
        em = re.search(r"[?&]ep=(\d+)", url)
        if em:
            try:
                ep = int(em.group(1))
            except Exception:
                ep = 1
        post_url = self.site + "/archives/" + pid + "/"
        html = self._get(post_url, referer=self.site + "/")
        if not html:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        urls = self._video_urls(html)
        if not urls or ep < 1 or ep > len(urls):
            return {"parse": 0, "url": "", "header": dict(self.header)}
        stream = urls[ep - 1]
        return {"parse": 0, "url": stream, "header": {"User-Agent": self.header["User-Agent"], "Referer": post_url}}

    def localProxy(self, param):
        try:
            p = json.loads(param) if isinstance(param, str) else param
            u = p.get("url", "") if isinstance(p, dict) else ""
            if u.startswith("img:"):
                data, ct = self._img(u[4:])
                if data:
                    return [200, ct, data, {"Content-Length": str(len(data))}]
            return [404, "text/plain", b"", {}]
        except Exception:
            return [502, "text/plain", b"", {}]


def _html_unescape(s):
    import html as _h
    return _h.unescape(s) if s else s
