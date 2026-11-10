# -*- coding: utf-8 -*-
# TG交流群 https://t.me/hshsjk9

import re, json, time, random
try:
    import requests as _requests
except Exception:
    _requests = None


class Spider:
    def __init__(self):
        self.site = "https://78vc9ew4.niu16.top"
        self.name = "腾迅影视"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _requests.Session() if _requests else None
        self._extend = {}
        self._home = None
        self._verified = False
        self._cj = None
        self._opener = None
        self._cats_cache = None
        self._fallback_cats = [
            ("1", "国产视频"),
            ("6", "国产传媒"),
            ("2", "国产探花"),
            ("7", "极品学生"),
            ("8", "野战户外"),
            ("9", "网曝黑料"),
            ("10", "日本有码"),
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

    def _verify(self):
        chal = "%x%x" % (random.getrandbits(52), int(time.time() * 1000))
        payload = {
            "challenge": chal,
            "width": 1920,
            "height": 1080,
            "language": "zh-CN",
            "platform": "Win32",
            "webdriver": 0,
            "timezone": "Asia/Shanghai",
        }
        url = self.site + "/browser-check.php?t=%d" % int(time.time() * 1000)
        if self.s is not None:
            try:
                r = self.s.post(url, json=payload, headers={"Content-Type": "application/json", "Referer": self.site + "/verification.html?return=%2F"}, timeout=12)
                if r.status_code < 400:
                    try:
                        d = r.json()
                    except Exception:
                        d = {}
                    if isinstance(d, dict) and d.get("success") is True:
                        self._verified = True
                        return True
            except Exception:
                pass
        try:
            import urllib.request
            if self._opener is None:
                import http.cookiejar
                self._cj = http.cookiejar.CookieJar()
                self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._cj))
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "Referer": self.site + "/verification.html?return=%2F", "User-Agent": self.header["User-Agent"]})
            with self._opener.open(req, timeout=12) as resp:
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
        for attempt in range(2):
            txt = ""
            if self.s is not None:
                try:
                    r = self.s.get(url, headers=h, timeout=12, allow_redirects=True)
                    if r.status_code < 400:
                        if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
                            r.encoding = "utf-8"
                        txt = r.text
                except Exception:
                    txt = ""
            if not txt and self._opener is not None:
                try:
                    import urllib.request
                    req = urllib.request.Request(url, headers=h)
                    with self._opener.open(req, timeout=12) as resp:
                        txt = resp.read().decode("utf-8", "ignore")
                except Exception:
                    txt = ""
            if not txt and self._opener is None:
                try:
                    import urllib.request
                    import http.cookiejar
                    self._cj = http.cookiejar.CookieJar()
                    self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._cj))
                    req = urllib.request.Request(url, headers=h)
                    with self._opener.open(req, timeout=12) as resp:
                        txt = resp.read().decode("utf-8", "ignore")
                except Exception:
                    txt = ""
            if txt and ("verification.html" in txt or "正在验证" in txt) and attempt == 0:
                if self._verify():
                    continue
            return txt
        return ""

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

    def _cats(self):
        if self._cats_cache is not None:
            return self._cats_cache
        html = self._home if self._home is not None else self._get(self.site + "/")
        out = []
        seen = set()
        if html:
            for tid, name in re.findall(r'class="nav-item"><a href="/index\.php/vod/type/id/(\d+)\.html"[^>]*>(?:<i[^>]*></i>\s*)?([^<]{1,12})</a>', html):
                if tid in seen:
                    continue
                seen.add(tid)
                out.append((tid, name.strip()))
        if not out:
            out = list(self._fallback_cats)
        self._cats_cache = out
        return out

    def _items(self, html):
        out = []
        seen = set()
        if not html:
            return out
        for bm in re.finditer(r'<a href="/index\.php/vod/play/id/(\d+)/sid/\d+/nid/\d+\.html" class="video-item">([\s\S]{0,1200}?)</a>', html):
            vid = bm.group(1)
            block = bm.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            pm = re.search(r"background-image:\s*url\('([^']+)'\)", block)
            tm = re.search(r'<div class="video-title">([^<]+)</div>', block)
            im = re.search(r'<div class="video-info">([\s\S]*?)</div>', block)
            remarks = ""
            if im:
                remarks = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", im.group(1))).strip()
            out.append({
                "vod_id": vid,
                "vod_name": tm.group(1).strip() if tm else "",
                "vod_pic": self._u(pm.group(1)) if pm else "",
                "vod_remarks": remarks,
            })
        return out

    def _pagecount(self, html, pg, items):
        if re.search(r'<a href="[^"]*page/\d+[^"]*"[^>]*>下一页</a>', html or ""):
            return pg + 1
        if not items:
            return max(1, pg - 1) if pg > 1 else 1
        return pg

    _cat_limit = {"1": 40, "2": 40, "6": 25, "7": 20, "8": 20, "9": 20, "10": 20}

    def _cat_url(self, tid, pg):
        tid = str(tid)
        if pg <= 1:
            return self.site + "/index.php/vod/type/id/%s.html" % tid
        return self.site + "/index.php/vod/type/id/%s/page/%d.html" % (tid, pg)

    def _search_url(self, key, pg):
        try:
            from urllib.parse import quote
            kw = quote(str(key))
        except Exception:
            kw = str(key)
        if pg <= 1:
            return self.site + "/index.php/vod/search.html?wd=" + kw
        return self.site + "/index.php/vod/search/page/%d/wd/%s.html" % (pg, kw)

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
        if self._home is None:
            self._home = self._get(self.site + "/")
        cats = [{"type_id": tid, "type_name": name} for tid, name in self._cats()]
        return {"class": cats, "filters": {}, "list": self._items(self._home)}

    def homeVideoContent(self):
        if self._home is None:
            self._home = self._get(self.site + "/")
        return {"list": self._items(self._home)}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        html = self._get(self._cat_url(tid, pg))
        items = self._items(html)
        pc = self._pagecount(html, pg, items)
        limit = self._cat_limit.get(str(tid), len(items) if items else 40)
        return {"list": items, "page": pg, "pagecount": pc, "limit": limit, "total": pc * limit}

    def detailContent(self, ids):
        vid = ids
        if isinstance(ids, (list, tuple)):
            vid = ids[0] if ids else ""
        vid = str(vid).strip()
        m = re.search(r"(\d+)", vid)
        if not m:
            return {"list": []}
        vid = m.group(1)
        url = self.site + "/index.php/vod/detail/id/%s.html" % vid
        html = self._get(url)
        if not html:
            return {"list": []}
        title = ""
        tm = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        if tm:
            title = tm.group(1).strip()
        pic = ""
        pm = re.search(r'<div class="detail-pic[^>]*><img[^>]+src="([^"]+)"', html)
        if pm:
            pic = self._u(pm.group(1))
        desc = ""
        dm = re.search(r'<dl class="juqing">[\s\S]*?<dd>([\s\S]*?)</dd>', html)
        if dm:
            desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", dm.group(1))).strip()
            desc = desc.replace("详细剧情", "").strip()
        if not desc:
            desc = title
        eps = []
        seen = set()
        for pm in re.finditer(r'<a href="(/index\.php/vod/play/id/\d+/sid/\d+/nid/\d+\.html)"[^>]*>([^<]{1,15})</a>', html):
            href, name = pm.group(1), pm.group(2).strip()
            if href in seen:
                continue
            seen.add(href)
            eps.append("%s$%s" % (name or "HD", self._u(href)))
        return {"list": [{"vod_id": vid, "vod_name": title, "vod_pic": pic,
                          "vod_content": desc, "vod_play_from": self.name,
                          "vod_play_url": "#".join(eps)}]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if not str(key or "").strip():
            return {"list": []}
        html = self._get(self._search_url(key, pg))
        items = self._items(html)
        pc = self._pagecount(html, pg, items)
        return {"list": items, "page": pg, "pagecount": pc, "limit": 30, "total": pc * 30}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids
        if isinstance(ids, (list, tuple)):
            url = ids[0] if ids else ""
        url = str(url or "").strip()
        if not url:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        if not url.startswith("http"):
            if re.match(r"^\d+$", url):
                url = self.site + "/index.php/vod/play/id/%s/sid/1/nid/1.html" % url
            else:
                url = self._u(url)
        html = self._get(url, referer=self.site + "/")
        found = ""
        if html:
            m = re.search(r"player_aaaa\s*=\s*(\{.+?\})\s*;?\s*<", html, re.S)
            if not m:
                m = re.search(r"player_aaaa\s*=\s*(\{.+?\})", html, re.S)
            if m:
                try:
                    d = json.loads(m.group(1))
                    if isinstance(d, dict) and d.get("url"):
                        found = d["url"]
                except Exception:
                    pass
            if not found:
                m2 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
                if m2:
                    found = m2.group(1)
        if not found:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        found = found.strip()
        if found.startswith("//"):
            found = "https:" + found
        elif not found.startswith("http"):
            found = self._u(found)
        hdr = dict(self.header)
        hdr["Referer"] = url
        return {"parse": 0, "url": found, "header": hdr}
