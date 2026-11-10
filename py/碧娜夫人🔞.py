# -*- coding: utf-8 -*-
# TG交流群 https://t.me/hshsjk9

import re
import json
import base64
import html as _html
try:
    import requests as _rq
except Exception:
    _rq = None


class Spider:
    def __init__(self):
        self.site = "https://xn--tfr240n8eb.bnbrightgammac.xyz"
        self.name = "碧娜夫人"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.site + "/",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.s = self.session = self.sess = _rq.Session() if _rq else None
        self._cats = [
            ("43", "国产精品"),
            ("33", "日本女优"),
            ("35", "中文字幕"),
            ("39", "欧美视频"),
            ("53", "传媒拍摄"),
            ("29", "人妖视频"),
            ("23", "女同性爱"),
            ("31", "捆绑调教"),
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

    def _data(self, html):
        m = re.search(r"atob\('([^']+)'\)", html)
        if not m:
            return None
        try:
            raw = base64.b64decode(m.group(1)).decode("utf-8")
            return json.loads(raw)
        except Exception:
            return None

    def _items(self, html):
        from urllib.parse import quote as _q
        d = self._data(html)
        if not d:
            return [], 0
        rd = d.get("request_data", {}) or {}
        total = int(rd.get("total") or 0)
        out = []
        for it in rd.get("list", []) or []:
            vid = str(it.get("vod_id", ""))
            if not vid:
                continue
            play = str(it.get("vod_play_url", "") or "")
            purl = play.split("$", 1)[1].strip() if "$" in play else play.strip()
            name = _html.unescape(str(it.get("vod_name", "") or "")).strip() or vid
            pic = self._u(str(it.get("vod_pic", "") or ""))
            cid = vid + "@@" + purl + "@@" + _q(name, safe="") + "@@" + _q(pic, safe="")
            out.append({
                "vod_id": cid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": str(it.get("vod_duration", "") or ""),
            })
        return out, total

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
        url = self.site + "/vodlist/type/%s/keyword/all/orderby/default/page/%d.html" % (tid, pg)
        html = self._get(url)
        items, total = self._items(html)
        pc = (total + 19) // 20 if total else 1
        return {"list": items, "page": pg, "pagecount": pc, "limit": 20, "total": total}

    def detailContent(self, ids):
        from urllib.parse import unquote as _uq
        vid = ids[0] if isinstance(ids, (list, tuple)) else ids
        vid = str(vid or "")
        parts = vid.split("@@")
        name = parts[0]
        play = ""
        pic = ""
        if len(parts) >= 4:
            play = parts[1]
            name = _uq(parts[2])
            pic = _uq(parts[3])
        elif len(parts) >= 2:
            play = parts[1]
        eps = []
        if play:
            eps.append("正片$%s" % play)
        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_play_from": "碧娜夫人" if eps else "",
            "vod_play_url": "#".join(eps),
        }]}

    def searchContent(self, key, quick=False, pg="1"):
        from urllib.parse import quote
        url = self.site + "/vodlist/type/all/keyword/" + quote(str(key)) + "/orderby/default/page/1.html"
        html = self._get(url)
        items, total = self._items(html)
        return {"list": items, "page": 1, "pagecount": (total + 19) // 20 if total else 1}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids[0] if isinstance(ids, (list, tuple)) else ids
        url = str(url or "").strip()
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        if url.startswith("http"):
            return {"parse": 0, "url": url, "header": dict(self.header)}
        return {"parse": 0, "url": self._u(url), "header": dict(self.header)}
