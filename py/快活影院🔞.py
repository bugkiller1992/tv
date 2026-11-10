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
        self.site = "https://tbryy.ksdlcme.cn"
        self.name = "快活影院"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _rq.Session() if _rq else None
        self._totals = {}
        self._cats = [
            ("sanjijingdian", "三级经典"),
            ("yazhouav", "亚洲AV"),
            ("yazhouxingai", "亚洲性爱"),
            ("oumeixingai", "欧美性爱"),
            ("oumeiav", "欧美AV"),
            ("zipaitoupai", "自拍偷拍"),
            ("toupaizipai", "偷拍自拍"),
            ("zhubozhibo", "主播直播"),
            ("3ddonghua", "3D动画"),
            ("chengrenkatong", "成人卡通"),
            ("luanlunshunv", "乱伦熟女"),
            ("shunvrenqi", "熟女人妻"),
            ("siwazhifu", "丝袜制服"),
            ("zhifusiwa", "制服丝袜"),
            ("smlinglei", "SM另类"),
            ("lingleibiantai", "另类变态"),
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

    def _total(self, html):
        nums = [int(n) for n in re.findall(r'list_(\d+)\.html', html)]
        return max(nums) + 1 if nums else 1

    def _items(self, html):
        out = []
        seen = set()
        for m in re.finditer(r'href="(/htm/[^"]+)"[^>]*title="([^"]+)"', html):
            path = m.group(1)
            if path in seen:
                continue
            seg = html[m.start():m.start() + 900]
            im = re.search(r'data-original="([^"]+)"', seg)
            title = _html.unescape(m.group(2)).strip()
            if not im or not title:
                continue
            seen.add(path)
            out.append({
                "vod_id": path,
                "vod_name": title,
                "vod_pic": self._u(im.group(1)),
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
        if pg <= 1:
            url = self.site + "/%s/index.html" % tid
            html = self._get(url)
            self._totals[tid] = self._total(html)
            pc = self._totals[tid]
            return {"list": self._items(html), "page": 1, "pagecount": pc, "limit": 40, "total": 40 * pc}
        total = self._totals.get(tid)
        if not total:
            idx = self._get(self.site + "/%s/index.html" % tid)
            total = self._total(idx)
            self._totals[tid] = total
        url = self.site + "/%s/list_%d.html" % (tid, total + 1 - pg)
        html = self._get(url)
        return {"list": self._items(html), "page": pg, "pagecount": total, "limit": 40, "total": 40 * total}

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid or "")
        html = self._get(self._u(vid))
        name = ""
        nm = re.search(r'<title>([^<]+)', html)
        if nm:
            name = _html.unescape(nm.group(1)).replace(" - 快活影院", "").strip()
        pic = ""
        pm = re.search(r'var posterImg="([^"]+)"', html)
        if pm:
            pic = pm.group(1)
        play = ""
        mm = re.search(r'var playUrl="([^"]+)"', html)
        if mm:
            play = mm.group(1).replace("+@movivecom@+", "stream1.kkodjj.com")
        eps = []
        if play:
            eps.append("正片$%s" % play)
        return {"list": [{
            "vod_id": vid,
            "vod_name": name or vid,
            "vod_pic": self._u(pic),
            "vod_play_from": "快活影院" if eps else "",
            "vod_play_url": "#".join(eps),
        }]}

    def searchContent(self, key, quick=False, pg="1"):
        import json as _json
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        key = str(key or "").strip()
        if not key:
            return {"list": [], "page": 1, "pagecount": 0}
        body = {
            "_source": ["id", "data_name", "data_intro", "data_actor", "class_dir", "data_picbig", "year", "month", "day"],
            "query": {"bool": {"must": [{"multi_match": {"query": key, "fields": ["data_name", "data_intro", "data_actor"]}}]}},
            "size": 20,
            "from": (pg - 1) * 20,
        }
        data = None
        payload = _json.dumps(body, ensure_ascii=False)
        if self.s is not None:
            try:
                r = self.s.post("https://ser.m3u8111222333.com/.netlify/functions/search",
                                data=payload.encode("utf-8"),
                                headers={"Content-Type": "application/json", "User-Agent": self.header["User-Agent"]},
                                timeout=15)
                if r.status_code < 400:
                    data = r.json()
            except Exception:
                data = None
        if data is None:
            try:
                import urllib.request
                req = urllib.request.Request("https://ser.m3u8111222333.com/.netlify/functions/search",
                                            data=payload.encode("utf-8"),
                                            headers={"Content-Type": "application/json", "User-Agent": self.header["User-Agent"]})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = _json.loads(resp.read().decode("utf-8", "ignore"))
            except Exception:
                return {"list": [], "page": pg, "pagecount": 0}
        video_slugs = set(t for t, _n in self._cats)
        out = []
        total = 0
        try:
            hits = data.get("hits", {}) or {}
            tot = hits.get("total", {}) or {}
            total = int(tot.get("value") or 0)
            for h in hits.get("hits", []) or []:
                s = h.get("_source", {}) or {}
                slug = str(s.get("class_dir", "") or "")
                if slug not in video_slugs:
                    continue
                vid = str(s.get("id", "") or "")
                if not vid:
                    continue
                path = "/htm/%s/%s/%s/%s/%s.html" % (s.get("year", ""), s.get("month", ""), s.get("day", ""), slug, vid)
                pic = str(s.get("data_picbig", "") or "")
                out.append({
                    "vod_id": path,
                    "vod_name": _html.unescape(str(s.get("data_name", "") or "")).strip() or vid,
                    "vod_pic": "https://res1.kkodjj.com" + pic if pic.startswith("/") else self._u(pic),
                    "vod_remarks": "",
                })
        except Exception:
            return {"list": [], "page": pg, "pagecount": 0}
        pc = (total + 19) // 20 if total else 1
        return {"list": out, "page": pg, "pagecount": pc}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids[0] if isinstance(ids, (list, tuple)) else ids
        url = str(url or "").strip()
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        if url.startswith("http"):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        return {"parse": 0, "url": self._u(url), "header": dict(self.header)}
