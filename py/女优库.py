import re, json, requests
from base.spider import Spider
class Spider(Spider):
    def __init__(self):
        self.host = "https://nvku-8m2c.web.zaka.live"
        self.vhost = "https://v.hersav.me"
        self.headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Mobile Safari/537.36", "Referer": "https://nvku-8m2c.web.zaka.live/"}
        self.session = requests.Session()
        self._meta_obj = None
        self._shards = {}
        self.page = 30
        self.search_shards = 8
        self.search_hits = 30
    def init(self, extend=""):
        return True
    def getName(self):
        return "女优库"
    def _get(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=15)
            return r.text if r.status_code == 200 else ""
        except Exception:
            return ""
    def _balanced(self, txt, prefix, op, cl):
        i = txt.find(prefix)
        if i < 0:
            return ""
        k = i + len(prefix)
        depth = 0
        start = -1
        instr = False
        esc = False
        while k < len(txt):
            c = txt[k]
            if instr:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    instr = False
                k += 1
                continue
            if c == '"':
                instr = True
            elif c == op:
                if depth == 0:
                    start = k
                depth += 1
            elif c == cl:
                depth -= 1
                if depth == 0:
                    return txt[start:k + 1]
            k += 1
        return ""
    def _fallback_cats(self):
        defs = [(0, "有码", 222969, 45, 2969), (1, "无码", 75088, 16, 88), (2, "4K", 24456, 5, 4456), (7, "其它", 51, 1, 51)]
        cats = []
        for d in defs:
            shards = [5000] * (d[3] - 1) + [d[4]]
            cats.append({"id": d[0], "name": d[1], "n": d[2], "shards": shards})
        return cats
    def _meta(self):
        if self._meta_obj is not None:
            return self._meta_obj
        m = {"cats": self._fallback_cats(), "an": []}
        try:
            t = self._get(self.host + "/meta.js")
            s = self._balanced(t, "window.META=", "{", "}")
            if s:
                o = json.loads(s)
                if o.get("cats"):
                    m["cats"] = o["cats"]
                if o.get("an") is not None:
                    m["an"] = o["an"]
        except Exception:
            pass
        self._meta_obj = m
        return m
    def _shard(self, key):
        if key in self._shards:
            return self._shards[key]
        arr = None
        try:
            t = self._get(self.host + "/d/" + key + ".js")
            s = self._balanced(t, 'window.SH("' + key + '",', "[", "]")
            if s:
                a = json.loads(s)
                if isinstance(a, list):
                    arr = a
        except Exception:
            arr = None
        if len(self._shards) >= 8:
            self._shards.pop(next(iter(self._shards)))
        self._shards[key] = arr
        return arr
    def _cat_name(self, key):
        return {"new": "最新上架"}.get(key, "") or ({"c0_": "有码", "c1_": "无码", "c2_": "4K", "c7_": "其它"}.get(key[:3], ""))
    def _play_url(self, h):
        if not h:
            return ""
        if h.startswith("u:"):
            return h[2:]
        return self.vhost + "/" + h + "/" + h + ".m3u8"
    def _cover(self, r):
        h = r[1] if len(r) > 1 else ""
        if len(r) < 6 or not r[5] or h.startswith("u:"):
            return ""
        return self.vhost + "/images/av/" + h + ".jpg"
    def _act_names(self, r, an):
        idx = r[4] if len(r) > 4 else ""
        if not idx or not an:
            return ""
        names = []
        for p in idx.split(","):
            try:
                n = int(p)
            except Exception:
                continue
            if 0 <= n < len(an) and an[n]:
                names.append(an[n])
        return "、".join(names)
    def _year(self, r):
        y = r[3] if len(r) > 3 else ""
        return ("20" + y) if y else ""
    def _title(self, r):
        return str(r[2] if len(r) > 2 and r[2] else (r[0] if r else ""))
    def _vod(self, key, idx, r, an):
        acts = self._act_names(r, an)
        yr = self._year(r)
        remark = yr
        if acts:
            first = acts.split("、")[0]
            remark = (remark + " " + first) if remark else first
        return {"vod_id": key + ":" + str(idx), "vod_name": self._title(r), "vod_pic": self._cover(r), "vod_remarks": remark, "vod_year": yr, "vod_play_from": "女优库", "vod_play_url": "正片$" + (r[1] if len(r) > 1 else "")}
    def _segments(self, cat, pg):
        total = cat["n"]
        pagecount = (total + self.page - 1) // self.page
        pg = max(1, min(pg, pagecount))
        off = (pg - 1) * self.page
        need = self.page
        segs = []
        cum = 0
        for i, s in enumerate(cat["shards"]):
            if off >= cum + s:
                cum += s
                continue
            start = off - cum
            take = min(s - start, need)
            segs.append({"key": "c" + str(cat["id"]) + "_" + str(i), "start": start, "count": take})
            need -= take
            off = cum + s
            cum += s
            if need <= 0:
                break
        return segs, pagecount, pg
    def homeContent(self, filter):
        try:
            meta = self._meta()
            classes = [{"type_id": "new", "type_name": "最新上架"}]
            for c in meta["cats"]:
                classes.append({"type_id": str(c["id"]), "type_name": c["name"]})
            lst = []
            arr = self._shard("new")
            if arr:
                for i in range(min(20, len(arr))):
                    lst.append(self._vod("new", i, arr[i], meta["an"]))
            return {"class": classes, "list": lst}
        except Exception:
            return {"class": [], "list": []}
    def homeVideoContent(self):
        try:
            meta = self._meta()
            lst = []
            arr = self._shard("new")
            if arr:
                for i in range(min(20, len(arr))):
                    lst.append(self._vod("new", i, arr[i], meta["an"]))
            return {"list": lst}
        except Exception:
            return {"list": []}
    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
            if pg < 1:
                pg = 1
        except Exception:
            pg = 1
        try:
            meta = self._meta()
            if str(tid) == "new":
                arr = self._shard("new")
                if not arr:
                    return {"list": [], "page": pg, "pagecount": 1}
                pc = (len(arr) + self.page - 1) // self.page
                pg = max(1, min(pg, pc))
                st = (pg - 1) * self.page
                lst = [self._vod("new", i, arr[i], meta["an"]) for i in range(st, min(st + self.page, len(arr)))]
                return {"list": lst, "page": pg, "pagecount": pc}
            cat = None
            for c in meta["cats"]:
                if str(c["id"]) == str(tid):
                    cat = c
            if not cat:
                return {"list": [], "page": pg, "pagecount": pg}
            segs, pc, pg = self._segments(cat, pg)
            lst = []
            for g in segs:
                a = self._shard(g["key"])
                if not a:
                    continue
                for j in range(g["start"], min(g["start"] + g["count"], len(a))):
                    lst.append(self._vod(g["key"], j, a[j], meta["an"]))
            return {"list": lst, "page": pg, "pagecount": pc}
        except Exception:
            return {"list": [], "page": pg, "pagecount": pg}
    def detailContent(self, ids):
        try:
            id = ids[0] if ids else ""
            p = id.split(":")
            if len(p) != 2:
                return {"list": []}
            key = p[0]
            idx = int(p[1])
            arr = self._shard(key)
            if not arr or idx < 0 or idx >= len(arr):
                return {"list": []}
            r = arr[idx]
            meta = self._meta()
            v = self._vod(key, idx, r, meta["an"])
            acts = self._act_names(r, meta["an"])
            yr = self._year(r)
            parts = []
            if r[0]:
                parts.append("番号：" + r[0])
            if yr:
                parts.append("年份：" + yr)
            if acts:
                parts.append("女优：" + acts)
            parts.append("分类：" + self._cat_name(key))
            v["vod_content"] = "\n".join(parts)
            return {"list": [v]}
        except Exception:
            return {"list": []}
    def _norm_code(self, s):
        return s.replace("-", "").replace("_", "").replace(" ", "")
    def _is_code(self, q):
        i = 0
        letters = 0
        digits = 0
        while i < len(q) and q[i].isalpha() and q[i].isascii():
            i += 1
            letters += 1
        if letters < 2 or letters > 6:
            return False
        if i < len(q) and q[i] in "-_ ":
            i += 1
        while i < len(q) and q[i].isdigit():
            i += 1
            digits += 1
        return 2 <= digits <= 6 and i == len(q)
    def _search_keys(self, meta):
        counts = {0: 45, 1: 16, 2: 5}
        for c in meta["cats"]:
            counts[c["id"]] = len(c["shards"])
        keys = ["new", "c7_0"]
        for r in range(45):
            for cat in (0, 1, 2):
                if r < counts[cat]:
                    keys.append("c" + str(cat) + "_" + str(r))
        return keys
    def _match(self, r, ql, qcode, act_idxs):
        code = str(r[0] if r else "").lower()
        if qcode and (self._norm_code(code).find(qcode) >= 0 or code.find(ql) >= 0):
            return True
        title = str(r[2] if len(r) > 2 and r[2] else "").lower()
        if title.find(ql) >= 0:
            return True
        if act_idxs:
            a = r[4] if len(r) > 4 else ""
            if a:
                padded = "," + a + ","
                for x in act_idxs:
                    if padded.find("," + str(x) + ",") >= 0:
                        return True
        return False
    def searchContent(self, key, quick, pg):
        try:
            q = (key or "").strip()
            if not q:
                return {"list": []}
            try:
                pg = int(pg)
                if pg < 1:
                    pg = 1
            except Exception:
                pg = 1
            meta = self._meta()
            ql = q.lower()
            qcode = self._norm_code(ql) if self._is_code(q) else ""
            act_idxs = []
            for i, n in enumerate(meta["an"]):
                if n and n.lower().find(ql) >= 0:
                    act_idxs.append(i)
            keys = self._search_keys(meta)
            start = (pg - 1) * self.search_shards
            pagecount = (len(keys) + self.search_shards - 1) // self.search_shards
            lst = []
            for k in range(start, min(start + self.search_shards, len(keys))):
                if len(lst) >= self.search_hits:
                    break
                arr = self._shard(keys[k])
                if not arr:
                    continue
                for j, r in enumerate(arr):
                    if len(lst) >= self.search_hits:
                        break
                    if self._match(r, ql, qcode, act_idxs):
                        lst.append(self._vod(keys[k], j, r, meta["an"]))
            return {"list": lst, "page": pg, "pagecount": pagecount}
        except Exception:
            return {"list": []}
    def playerContent(self, flag, id, vipFlags):
        try:
            h = str(id or "")
            if not h:
                return {"parse": 1, "url": ""}
            url = self._play_url(h)
            header = dict(self.headers)
            if h.startswith("u:"):
                if ".m3u8" in url or ".mp4" in url:
                    return {"parse": 0, "url": url, "header": header}
                return {"parse": 1, "url": url}
            return {"parse": 0, "url": url, "header": header}
        except Exception:
            return {"parse": 1, "url": ""}
    def isVideoFormat(self, url):
        return bool(url) and (".m3u8" in url or ".mp4" in url)
    def manualVideoCheck(self):
        return False
