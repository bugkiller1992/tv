# -*- coding: utf-8 -*-
# TG交流群 https://t.me/hshsjk9

import re, json, time
try:
    import requests as _requests
except Exception:
    _requests = None


class Spider:
    CATS = [
        ("54", "主播网红"), ("52", "黑料不打烊"), ("51", "淫乱学生妹"), ("50", "嫖妓全过程"),
        ("49", "乱伦毁三观"), ("48", "国产大制作"), ("47", "偷拍自拍"), ("59", "少女破处"),
        ("35", "高清无码"), ("36", "中文字幕"), ("41", "巨乳"), ("46", "AI短剧"),
        ("55", "3D动漫"), ("56", "剧情故事"), ("58", "激情中字"),
    ]
    CAT_IDS = {c[0] for c in CATS}
    LIMIT = 32

    def __init__(self):
        self.site = "https://5h6i7j8.waimaiyuans.sbs"
        self.name = "外卖媛AV"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _requests.Session() if _requests else None
        self._extend = {}
        self._home = None

    def getName(self):
        return self.name

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

    def _get(self, url, referer=None):
        h = dict(self.header)
        if referer:
            h["Referer"] = referer
        for _ in range(3):
            if self.s is not None:
                try:
                    r = self.s.get(url, headers=h, timeout=12, allow_redirects=True)
                    if r.status_code < 400 and r.text:
                        return r.text
                except Exception:
                    pass
            try:
                import urllib.request
                req = urllib.request.Request(url, headers=h)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    txt = resp.read().decode("utf-8", "ignore")
                    if txt:
                        return txt
            except Exception:
                pass
            time.sleep(1)
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
        return [{"type_id": tid, "type_name": name} for tid, name in self.CATS]

    def _items(self, html):
        out = []
        seen = set()
        pat = re.compile(
            r'<div class="item">\s*<a href="(/index\.php/vod/play/id/(\d+)/sid/\d+/nid/\d+\.html)" title="([^"]*)"([\s\S]{0,1500}?)</a>',
            re.S,
        )
        for m in pat.finditer(html or ""):
            href, vid, title, seg = m.group(1), m.group(2), m.group(3), m.group(4)
            if vid in seen:
                continue
            seen.add(vid)
            im = re.search(r'data-original="([^"]+)"', seg)
            pic = self._u(im.group(1)) if im else ""
            dm = re.search(r'<em>(\d{2}-\d{2}-\d{2})</em>', seg)
            play_url = self._u(href)
            out.append({
                "vod_id": play_url + "@@" + pic,
                "vod_name": title.strip(),
                "vod_pic": pic,
                "vod_remarks": dm.group(1) if dm else "",
            })
        return out

    def _pagecount(self, html, pat):
        try:
            nums = [int(x) for x in re.findall(pat, html or "")]
            return max(nums) if nums else 1
        except Exception:
            return 1

    def _cat_url(self, tid, pg):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg <= 1:
            return "%s/index.php/vod/type/id/%s.html" % (self.site, tid)
        return "%s/index.php/vod/type/id/%s/page/%d.html" % (self.site, tid, pg)

    def _eff_tid(self, tid, extend):
        if isinstance(extend, dict):
            v = str(extend.get("class", "") or "").strip()
            if v in self.CAT_IDS:
                return v
        return str(tid)

    def _play_json(self, html):
        i = html.find("var player_aaaa=")
        if i < 0:
            return None
        j = html.find("{", i)
        if j < 0:
            return None
        depth = 0
        k = j
        instr = False
        esc = False
        while k < len(html):
            c = html[k]
            if instr:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    instr = False
            else:
                if c == '"':
                    instr = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
            k += 1
        try:
            d = json.loads(html[j:k + 1])
            return d if isinstance(d, dict) else None
        except Exception:
            return None

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
            self._home = self._get(self.site)
        return {"class": self._cats(), "filters": {}, "list": self._items(self._home)}

    def homeVideoContent(self):
        if self._home is None:
            self._home = self._get(self.site)
        return {"list": self._items(self._home)}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        etid = self._eff_tid(tid, extend if extend is not None else self._extend)
        html = self._get(self._cat_url(etid, pg))
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": self.LIMIT, "total": 1}
        vod_list = self._items(html)
        pagecount = self._pagecount(html, r"/index\.php/vod/type/id/%s/page/(\d+)\.html" % re.escape(etid))
        return {"list": vod_list, "page": pg, "pagecount": pagecount, "limit": self.LIMIT, "total": pagecount * self.LIMIT}

    def detailContent(self, ids):
        vid = ids
        if isinstance(ids, (list, tuple)):
            vid = ids[0] if ids else ""
        vid = str(vid or "").strip()
        if not vid:
            return {"list": []}
        pic = ""
        if "@@" in vid:
            vid, pic = vid.split("@@", 1)
        url = self._u(vid)
        html = self._get(url, referer=self.site)
        if not html:
            return {"list": [{"vod_id": vid, "vod_name": "", "vod_pic": pic, "vod_content": "", "vod_play_from": "", "vod_play_url": ""}]}
        title = ""
        tm = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if tm:
            title = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
        m3u8 = ""
        cls = ""
        d = self._play_json(html)
        if d:
            m3u8 = (d.get("url") or "").replace("\\/", "/")
            vd = d.get("vod_data") or {}
            cls = vd.get("vod_class") or ""
            if not title:
                title = vd.get("vod_name") or ""
        if not m3u8:
            m = re.search(r"(https?://[^\s\"']+\.m3u8[^\s\"']*)", html)
            if m:
                m3u8 = m.group(1).replace("\\/", "/")
        play_url = "播放$" + (m3u8 if m3u8 else url)
        return {"list": [{"vod_id": vid, "vod_name": title, "vod_pic": pic,
                          "vod_type": cls, "vod_content": "", "vod_play_from": self.name,
                          "vod_play_url": play_url}]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        from urllib.parse import quote
        kw = quote(str(key))
        if pg <= 1:
            url = "%s/index.php/vod/search/wd/%s.html" % (self.site, kw)
        else:
            url = "%s/index.php/vod/search/page/%d/wd/%s.html" % (self.site, pg, kw)
        html = self._get(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": self.LIMIT, "total": 1}
        vod_list = self._items(html)
        pagecount = self._pagecount(html, r"/index\.php/vod/search/page/(\d+)/wd/")
        return {"list": vod_list, "page": pg, "pagecount": pagecount, "limit": self.LIMIT, "total": pagecount * self.LIMIT}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids
        if isinstance(ids, (list, tuple)):
            url = ids[0] if ids else ""
        url = str(url or "").strip()
        if not url:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        if "@@" in url:
            url = url.split("@@", 1)[0]
        if not url.startswith("http"):
            url = self._u(url)
        u = url.lower()
        if u.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi")) or "m3u8" in u:
            return {"parse": 0, "url": url, "header": dict(self.header)}
        html = self._get(url, referer=self.site)
        if not html:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        found = ""
        d = self._play_json(html)
        if d and d.get("url"):
            found = d["url"].replace("\\/", "/")
        if not found:
            m = re.search(r"(https?://[^\s\"']+\.m3u8[^\s\"']*)", html)
            if m:
                found = m.group(1).replace("\\/", "/")
        if not found:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        found = found.strip()
        if found.startswith("//"):
            found = "https:" + found
        elif not found.startswith("http"):
            found = self._u(found)
        return {"parse": 0, "url": found, "header": dict(self.header)}

    def localProxy(self, param):
        u = param.get("url", "") if isinstance(param, dict) else ""
        if not u:
            return [403, "text/plain", b"", None]
        h = dict(self.header)
        if self.s is not None:
            try:
                r = self.s.get(u, headers=h, timeout=15)
                return [200, r.headers.get("Content-Type", "application/octet-stream"), r.content, None]
            except Exception:
                pass
        try:
            import urllib.request
            req = urllib.request.Request(u, headers=h)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return [200, resp.headers.get("Content-Type", "application/octet-stream"), resp.read(), None]
        except Exception:
            return [403, "text/plain", b"", None]
