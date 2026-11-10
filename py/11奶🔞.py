# -*- coding: utf-8 -*-
# TG交流群 https://t.me/hshsjk9

import re
import html as _html
try:
    import requests as _rq
except Exception:
    _rq = None


class Spider:
    def __init__(self):
        self.site = "https://hc2.34nai.sbs"
        self.name = "11奶"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _rq.Session() if _rq else None
        self._cats = [
            ("5", "国产自拍"),
            ("11", "传媒影片"),
            ("16", "主播自拍"),
            ("17", "足交视频"),
            ("18", "中文字幕"),
            ("21", "国语解说"),
            ("6", "亚洲激情"),
            ("7", "欧美激情"),
            ("8", "成人动漫"),
            ("9", "sm另类"),
            ("10", "伦理三级"),
            ("19", "ts人妖"),
            ("20", "强奸乱伦"),
        ]

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

    def init(self, extend=""):
        pass

    def _get(self, url):
        h = dict(self.header)
        if self.s is not None:
            try:
                r = self.s.get(url, headers=h, timeout=12, allow_redirects=True)
                if r.status_code < 400:
                    return r.text
            except Exception:
                pass
        try:
            import urllib.request
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=12) as resp:
                return resp.read().decode("utf-8", "ignore")
        except Exception:
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
            return self.site + u
        return self.site + "/" + u.lstrip("/")

    def _items(self, html):
        out = []
        seen = set()
        for m in re.finditer(r'href="(/vod/(\d+)/)"', html):
            vid = m.group(2)
            if vid in seen:
                continue
            seg = html[m.start():m.start() + 1200]
            im = re.search(r'<img[^>]+src="([^"]+)"', seg)
            tm = re.search(r'<p>([^<]{1,80})</p>', seg)
            if not im:
                continue
            pic = im.group(1)
            title = tm.group(1).strip() if tm else vid
            seen.add(vid)
            out.append({
                "vod_id": vid,
                "vod_name": _html.unescape(title).strip() or vid,
                "vod_pic": self._u(pic),
                "vod_remarks": "",
            })
        return out

    def homeContent(self, filter=None):
        cats = [{"type_id": t, "type_name": n} for t, n in self._cats]
        return {"class": cats, "filters": {}, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        tid = str(tid)
        url = self.site + "/f/%s/%d/" % (tid, pg)
        html = self._get(url)
        pc = 1
        pages = [int(n) for n in re.findall(r'/f/%s/(\d+)/' % tid, html)]
        if pages:
            pc = max(pages)
        return {"list": self._items(html), "page": pg, "pagecount": pc, "limit": 20, "total": 20 * pc}

    def detailContent(self, ids):
        import urllib.parse
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid or "")
        html = self._get(self.site + "/vod/%s/" % vid)
        name = ""
        nm = re.search(r'<title>([^<,]+)', html)
        if nm:
            name = _html.unescape(nm.group(1)).strip()
        pic = ""
        pm = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if pm:
            pic = pm.group(1)
        eps = []
        phtml = self._get(self.site + "/play/%s/1/1/" % vid)
        mu = re.search(r"mac_url=unescape\('([^']+)'\)", phtml)
        if mu:
            raw = mu.group(1)
            dec = re.sub(r'%u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), raw)
            dec = urllib.parse.unquote(dec)
            fm = re.search(r"mac_from='([^']+)'", phtml)
            froms = fm.group(1).split("$$$") if fm else []
            urls = [u for u in dec.split("$$$") if u]
            for i, u in enumerate(urls):
                if "$" in u:
                    ename, purl = u.split("$", 1)
                else:
                    ename, purl = "正片", u
                fname = froms[i] if i < len(froms) else ""
                label = fname if fname else ename
                eps.append("%s$%s" % (label.replace("$", "").replace("#", ""), purl.strip()))
        if not eps:
            mm = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
            if mm:
                eps.append("正片$%s" % mm.group(1))
        if not eps:
            mm2 = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', html)
            if mm2:
                eps.append("正片$%s" % mm2.group(1))
        return {"list": [{
            "vod_id": vid,
            "vod_name": name or vid,
            "vod_pic": self._u(pic),
            "vod_play_from": "11奶" if eps else "",
            "vod_play_url": "#".join(eps),
        }]}

    def searchContent(self, key, quick=False, pg="1"):
        from urllib.parse import quote
        url = self.site + "/index.php?m=vod-search-pg-1-wd-" + quote(str(key)) + ".html"
        html = self._get(url)
        return {"list": self._items(html), "page": 1, "pagecount": 1}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids[0] if isinstance(ids, (list, tuple)) else ids
        url = str(url or "").strip()
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        if url.startswith("http"):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        return {"parse": 0, "url": self._u(url), "header": dict(self.header)}
