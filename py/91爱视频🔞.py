import re
import html as _html
try:
    import requests as _rq
except Exception:
    _rq = None


class Spider:
    def __init__(self):
        self.site = "https://a2d.91aimf.fun"
        self.name = "91爱视频"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _rq.Session() if _rq else None
        self._cats = [
            ("1", "国产自拍"), ("2", "主播诱惑"), ("3", "探花约炮"), ("4", "偷拍偷窥"),
            ("5", "网曝吃瓜"), ("6", "抖阴短片"), ("7", "传媒剧情"), ("8", "日韩主播"),
            ("9", "日韩无码"), ("10", "中文字幕"), ("11", "AV解说"), ("12", "换脸明星"),
            ("13", "强奸乱伦"), ("14", "女优明星"), ("15", "欧美激情"), ("16", "重口激情"),
            ("17", "三级伦理"), ("18", "动漫"), ("20", "SM调教"), ("21", "女同性恋"),
            ("22", "VR视角"),
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
        for m in re.finditer(r'href="(/play/(\d+)-1-1\.html)"', html):
            vid = m.group(2)
            if vid in seen:
                continue
            seg = html[m.start():m.start() + 800]
            im = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', seg)
            if not im:
                im = re.search(r'<img[^>]+alt="([^"]*)"[^>]*src="([^"]+)"', seg)
                if im:
                    title, pic = im.group(1), im.group(2)
                else:
                    continue
            else:
                pic, title = im.group(1), im.group(2)
            rk = re.search(r'<p>([^<]{1,30})</p>', seg)
            seen.add(vid)
            out.append({
                "vod_id": vid,
                "vod_name": _html.unescape(title).strip() or vid,
                "vod_pic": self._u(pic),
                "vod_remarks": rk.group(1).strip() if rk else "",
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
        if pg > 1:
            url = self.site + "/type/%s-%d.html" % (tid, pg)
        else:
            url = self.site + "/type/%s-.html" % tid
        html = self._get(url)
        pc = 1
        pages = [int(n) for n in re.findall(r'/type/%s-(\d+)\.html' % tid, html)]
        if pages:
            pc = max(pages)
        return {"list": self._items(html), "page": pg, "pagecount": pc, "limit": 24, "total": 24 * pc}

    def detailContent(self, ids):
        import json
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid or "")
        html = self._get(self.site + "/play/%s-1-1.html" % vid)
        name = ""
        nm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if nm:
            name = _html.unescape(nm.group(1)).strip()
        pic = ""
        pm = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if pm:
            pic = pm.group(1)
        play_url = ""
        pm2 = re.search(r'player_aaaa\s*=\s*(\{.*?\})</script>', html, re.S)
        if pm2:
            try:
                d = json.loads(pm2.group(1))
                play_url = d.get("url", "")
            except Exception:
                pass
        if not play_url:
            mm = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
            if mm:
                play_url = mm.group(1)
        eps = []
        if play_url:
            eps.append("正片$%s" % play_url)
        return {"list": [{
            "vod_id": vid,
            "vod_name": name or vid,
            "vod_pic": self._u(pic),
            "vod_play_from": "91爱视频" if eps else "",
            "vod_play_url": "#".join(eps),
        }]}

    def searchContent(self, key, quick=False, pg="1"):
        from urllib.parse import quote
        url = self.site + "/vodsearch/-------------.html?wd=" + quote(str(key))
        html = self._get(url)
        return {"list": self._items(html), "page": 1, "pagecount": 1}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids[0] if isinstance(ids, (list, tuple)) else ids
        url = str(url or "").strip()
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        return {"parse": 0, "url": self._u(url), "header": dict(self.header)}
