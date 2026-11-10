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
        self.site = "https://91wz4.life"
        self.name = "91网址"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _rq.Session() if _rq else None
        self._cats = [
            ("36", "AI短剧"), ("37", "明星脸"), ("50", "AI换脸"),
            ("11", "国产自拍"), ("12", "吃瓜黑料"), ("13", "探花现场"), ("14", "乱伦系列"),
            ("15", "国产av"), ("16", "福利姬"), ("18", "成人主播"),
            ("19", "无码中字"), ("20", "JAV自拍"), ("21", "中文字幕"), ("22", "jav无码"),
            ("24", "欧美大片"), ("25", "黑人专区"), ("26", "留学生"),
            ("27", "港台三级"), ("28", "日韩三级"), ("29", "欧美三级"), ("51", "东南亚三级"),
            ("30", "3D动漫"), ("31", "次元动漫"),
            ("32", "男同GAY"), ("33", "女同百合"), ("34", "伪娘"),
            ("short39", "高燃混剪短视频"), ("short40", "网红达人短视频"), ("short41", "素人自拍短视频"),
            ("short42", "明星大瓜短视频"), ("short43", "反差系列短视频"), ("short44", "原创自拍短视频"),
        ]
        self._sub_ids = {"11", "12", "13", "14", "15", "16", "18", "19", "20", "21", "22", "23",
                         "24", "25", "26", "27", "28", "29", "51", "30", "31", "32", "33", "34",
                         "36", "37", "50"}

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

    def _unesc(self, s):
        return _html.unescape(s or "")

    def _items(self, html):
        out = []
        seen = set()
        for m in re.finditer(r'href="(/video/play/(\d+)-1-1\.html)"', html):
            vid = m.group(2)
            if vid in seen:
                continue
            seg = html[m.start():m.start() + 1200]
            im = re.search(r'data-src="([^"]+)"[^>]*alt="([^"]*)"', seg)
            if not im:
                im = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', seg)
                if not im or "poster_loading" in im.group(1):
                    continue
                pic, title = im.group(1), im.group(2)
            else:
                pic, title = im.group(1), im.group(2)
            du = re.search(r'<div class="dur[^"]*">([^<]+)</div>', seg)
            seen.add(vid)
            out.append({
                "vod_id": vid,
                "vod_name": self._unesc(title).strip() or vid,
                "vod_pic": self._u(pic),
                "vod_remarks": du.group(1).strip() if du else "",
            })
        for m in re.finditer(r'href="(/short/video/id/(\d+)\.html)"', html):
            vid = "s" + m.group(2)
            if vid in seen:
                continue
            seg = html[m.start():m.start() + 1200]
            im = re.search(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', seg)
            if not im:
                continue
            pic, title = im.group(1), im.group(2)
            du = re.search(r'<span class="scard-dur">([^<]+)</span>', seg)
            seen.add(vid)
            out.append({
                "vod_id": vid,
                "vod_name": self._unesc(title).strip() or vid,
                "vod_pic": self._u(pic),
                "vod_remarks": du.group(1).strip() if du else "",
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
        if tid == "short":
            if pg > 1:
                url = self.site + "/short/index/page/%d.html" % pg
            else:
                url = self.site + "/short/index.html"
            page_pat = r'/short/index/page/(\d+)\.html'
        elif tid.startswith("short"):
            sid = tid[5:]
            if pg > 1:
                url = self.site + "/short/type/id/%s/page/%d.html" % (sid, pg)
            else:
                url = self.site + "/short/type/id/%s.html" % sid
            page_pat = r'/short/type/id/%s/page/(\d+)\.html' % sid
        elif tid in self._sub_ids:
            if pg > 1:
                url = self.site + "/video/filtering/%s-%d.html" % (tid, pg)
            else:
                url = self.site + "/video/filtering/%s-.html" % tid
            page_pat = r'/video/filtering/%s-(\d+)\.html' % tid
        else:
            if pg > 1:
                url = self.site + "/video/Categories/%s-%d.html" % (tid, pg)
            else:
                url = self.site + "/video/Categories/%s.html" % tid
            page_pat = r'/video/Categories/%s-(\d+)\.html' % tid
        html = self._get(url)
        pc = 1
        pages = [int(n) for n in re.findall(page_pat, html)]
        if pages:
            pc = max(pages)
        return {"list": self._items(html), "page": pg, "pagecount": pc, "limit": 40, "total": 40 * pc}

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid or "")
        if vid.startswith("s"):
            html = self._get(self.site + "/short/video/id/%s.html" % vid[1:])
        else:
            html = self._get(self.site + "/video/play/%s-1-1.html" % vid)
        name = ""
        nm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if nm:
            name = self._unesc(nm.group(1)).strip()
        pic = ""
        pm = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        if pm:
            pic = pm.group(1)
        if not pic:
            pm2 = re.search(r'data-src="([^"]+poster[^"]*)"', html)
            if pm2:
                pic = pm2.group(1)
        play_url = ""
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
            "vod_play_from": "91网址" if eps else "",
            "vod_play_url": "#".join(eps),
        }]}

    def searchContent(self, key, quick=False, pg="1"):
        from urllib.parse import quote
        url = self.site + "/search/keyword/wd/" + quote(str(key)) + ".html"
        html = self._get(url)
        return {"list": self._items(html), "page": 1, "pagecount": 1}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids[0] if isinstance(ids, (list, tuple)) else ids
        url = str(url or "").strip()
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        return {"parse": 0, "url": self._u(url), "header": dict(self.header)}
