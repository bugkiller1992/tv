#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==================================================
@Spider Name : SupJav (Final Polish v5)
@Description : TVBox/CatVod SupJav Spider Plugin
==================================================
"""
import re
import json
import time
import base64
import codecs
import urllib.parse

try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = object

try:
    import requests
except Exception:
    requests = None

import urllib.request
import ssl

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

HOST = 'https://supjav.com'
PROXY_BASE = 'https://py.fzcrym.link:1314'
PAGE_API = PROXY_BASE + '/page?u='
FS_PAGE_API = PROXY_BASE + '/fs?u='
STREAM_API = PROXY_BASE + '/stream?u='
SJ_HLS_API = PROXY_BASE + '/sj_hls?u='
SJ_IMG_API = PROXY_BASE + '/sj_img?u='
LK_BASE = 'https://lk1.supremejav.com/supjav.php'

CATS = [
    ('__home', '最新'),
    ('__popular', '热门'),
    ('censored-jav', '有码 Censored'),
    ('uncensored-jav', '无码 Uncensored'),
    ('amateur', '素人 Amateur'),
    ('chinese-subtitles', '中文字幕 Chn Sub'),
    ('reducing-mosaic', '破解 Reducing Mosaic'),
    ('maker', '厂牌 Maker'),
    ('tag', '分类 Tag'),
]

LINE_ORDER = {
    'VOE': 0,
    'FST': 10,
    'ST': 20,
    'TV': 90,
}

SORTS = [
    {'key': 'sort', 'name': '排序',
     'value': [{'n': '最新', 'v': ''}, {'n': '最多观看', 'v': 'views'}]},
]


class Spider(BaseSpider):

    def __init__(self):
        if hasattr(BaseSpider, '__init__'):
            try:
                super().__init__()
            except Exception:
                pass
        self.name = 'SupJav'
        self._sess = None
        if requests is not None:
            try:
                self._sess = requests.Session()
                self._sess.headers.update({'User-Agent': UA})
            except Exception:
                self._sess = None

    def getName(self):
        return self.name

    def init(self, extend=""):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        return [404, 'text/plain', '']

    def isVideoFormat(self, url):
        return bool(url and re.search(r'\.(m3u8|mp4|ts)(\?|$)', url, re.I))

    # ---------------- 网络层 ----------------
    def _get(self, url, referer='', timeout=30):
        headers = {'User-Agent': UA}
        if referer:
            headers['Referer'] = referer

        if self._sess is not None:
            try:
                r = self._sess.get(url, headers=headers, timeout=timeout, verify=False)
                if r.status_code == 200:
                    return r.text
            except Exception:
                pass
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers)
            return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'replace')
        except Exception:
            return ''

    def _page(self, url, retries=2):
        api = FS_PAGE_API + urllib.parse.quote(url, safe='')
        for _ in range(max(1, retries)):
            html = self._get(api, timeout=20)
            if html and 'Just a moment' not in html and len(html) > 1000:
                return html
        api2 = PAGE_API + urllib.parse.quote(url, safe='')
        html = self._get(api2, timeout=30)
        if html and 'Just a moment' not in html and len(html) > 1000:
            return html
        return self._get(url, referer=HOST + '/', timeout=15)

    def _stream(self, url, referer='', timeout=30):
        api = STREAM_API + urllib.parse.quote(url, safe='')
        if referer:
            api += '&r=' + urllib.parse.quote(referer, safe='')
        res = self._get(api, timeout=timeout)
        if not res:
            res = self._get(url, referer=referer, timeout=timeout)
        return res

    _PLAY_CACHE = {}
    _PLAY_TTL = 300

    @classmethod
    def _play_cache_get(cls, key):
        v = cls._PLAY_CACHE.get(key)
        if not v:
            return None
        if time.time() - v[0] > cls._PLAY_TTL:
            cls._PLAY_CACHE.pop(key, None)
            return None
        return v[1]

    @classmethod
    def _play_cache_put(cls, key, val):
        cls._PLAY_CACHE[key] = (time.time(), val)

    # ---------------- 解析层 ----------------
    @staticmethod
    def _cards(html):
        out, seen = [], set()
        blocks = re.split(r'<div class="post">', html)[1:]
        if not blocks:
            blocks = re.split(r'<div class="item">', html)[1:]
        for b in blocks:
            m = re.search(r'href="' + re.escape(HOST) + r'/(\d+)\.html"', b)
            if not m:
                m = re.search(r'href="' + re.escape(HOST) + r'/(?:tag|maker|category|actress)/([^"/]+)/?"', b)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            t = re.search(r'title="([^"]+)"', b)
            if not t:
                t = re.search(r'>([^<]+)</a>', b)
            title = t.group(1) if t else vid
            title = (title.replace('&amp;', '&').replace('&#8217;', "'")
                     .replace('&quot;', '"').replace('&#8211;', '-')).strip()
            if not title:
                continue
            seen.add(vid)
            pic = ''
            for pat in (r'<img[^>]+data-original="([^"]+)"',
                        r'<img[^>]+data-src="([^"]+)"',
                        r'<img[^>]+src="(https?://[^"]+)"'):
                pm = re.search(pat, b)
                if pm:
                    pic = pm.group(1)
                    break
            if pic.startswith('//'):
                pic = 'https:' + pic
            if pic.startswith('http'):
                pic = SJ_IMG_API + urllib.parse.quote(pic, safe='')
            
            code = ''
            cm = re.search(r'\b([A-Z]{2,6}-?\d{2,6}|FC2PPV[\s-]?\d{5,8})\b', title)
            if cm:
                code = cm.group(1)
            out.append({
                'vod_id': vid,
                'vod_name': title[:90],
                'vod_pic': pic,
                'vod_remarks': code,
            })
        return out

    @staticmethod
    def _pagecount(html, cur):
        nums = [int(x) for x in re.findall(r'/page/(\d+)', html)]
        if not nums:
            return cur
        mx = max(nums)
        return mx if 0 < mx <= 5000 else cur

    @staticmethod
    def _unpack(text):
        m = re.search(r"}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)", text, re.S)
        if not m:
            return ''
        payload, base, count, keys = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split('|')
        try:
            payload = payload.encode().decode('unicode_escape')
        except Exception:
            pass
        digits = '0123456789abcdefghijklmnopqrstuvwxyz'

        def enc(num):
            out = ''
            while num > 0:
                out = digits[num % base] + out
                num //= base
            return out or '0'

        table = {}
        for i in range(count):
            if i < len(keys) and keys[i]:
                table[enc(i)] = keys[i]
        return re.sub(r'\b\w+\b', lambda mm: table.get(mm.group(0), mm.group(0)), payload)

    # ---------------- TVBox 接口 ----------------
    def homeContent(self, filter):
        classes = [{'type_id': cid, 'type_name': cname} for cid, cname in CATS]
        filters = {}
        for cid, _ in CATS:
            if not cid.startswith('__'):
                filters[cid] = SORTS
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        html = self._page(HOST + '/')
        return {'list': self._cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        tid = str(tid).strip()
        ext = extend if isinstance(extend, dict) else {}
        sort = str(ext.get('sort') or '').strip()

        if tid == '__home':
            url = HOST + '/' if page == 1 else HOST + '/page/%d/' % page
        elif tid == '__popular':
            url = (HOST + '/popular/' if page == 1
                   else HOST + '/popular/page/%d/' % page)
        else:
            if tid in ['tag', 'maker']:
                base = HOST + '/' + tid
            else:
                base = HOST + '/category/' + tid
            url = base + ('/' if page == 1 else '/page/%d/' % page)
            if sort:
                url += '?sort=' + urllib.parse.quote(sort)

        html = self._page(url)
        items = self._cards(html)
        return {
            'page': page,
            'pagecount': self._pagecount(html, page),
            'limit': len(items) or 24,
            'total': len(items),
            'list': items,
        }

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        kw = urllib.parse.quote(str(key))
        url = (HOST + '/?s=' + kw) if page == 1 else (HOST + '/page/%d/?s=%s' % (page, kw))
        html = self._page(url)
        items = self._cards(html)
        return {
            'page': page,
            'pagecount': self._pagecount(html, page),
            'limit': len(items) or 24,
            'total': len(items),
            'list': items,
        }

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids)
        vid = re.sub(r'\D', '', vid.split('/')[-1].replace('.html', '')) or vid
        durl = HOST + '/' + vid + '.html'
        html = self._page(durl)

        title = ''
        tm = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if tm:
            title = re.sub(r'<[^>]+>', '', tm.group(1))
            title = (title.replace('&amp;', '&').replace('&#8217;', "'")
                     .replace('&quot;', '"').replace('&#8211;', '-')).strip()

        # 提取番号
        code = ''
        cm = re.search(r'\b([A-Z]{2,6}-?\d{2,6}|FC2PPV[\s-]?\d{5,8})\b', title, re.I)
        if cm:
            code = cm.group(1).upper()

        pic = ''
        pm = re.search(r'background-image:\s*url\((https://img\.supjav\.com/[^)]+)\)', html)
        if pm:
            pic = pm.group(1)
        if not pic:
            im = re.search(r'(https://img\.supjav\.com/[^\s"\'<>)]+\.(?:jpg|jpeg|png|webp)[^\s"\'<>)]*)',
                           html, re.I)
            if im:
                pic = im.group(1)
        if pic.startswith('//'):
            pic = 'https:' + pic
        if pic.startswith('http'):
            pic = SJ_IMG_API + urllib.parse.quote(pic, safe='')

        # 精准匹配 Maker (厂牌)
        maker = ''
        mm_match = re.search(r'href="[^"]*/maker/([^"/]+)[^"]*"[^>]*>([^<]+)</a>', html)
        if not mm_match:
            mm_match = re.search(r'href="[^"]*/category/maker/([^"/]+)[^"]*"[^>]*>([^<]+)</a>', html)
        if mm_match:
            maker = mm_match.group(2).strip()

        # 精准匹配 Cast (演员)
        actors = []
        for _, name in re.findall(r'href="[^"]*/actress/([^"/]+)[^"]*"[^>]*>([^<]+)</a>', html):
            clean_name = name.strip()
            if clean_name and clean_name not in actors:
                actors.append(clean_name)

        # 精准匹配 Tag (分类)
        tags = []
        for _, name in re.findall(r'href="[^"]*/tag/([^"/]+)[^"]*"[^>]*>([^<]+)</a>', html):
            clean_tag = name.strip()
            if clean_tag and clean_tag not in tags and clean_tag not in actors:
                tags.append(clean_tag)

        links = re.findall(r'data-link="([0-9a-f]{40,})"', html)
        names = re.findall(r'data-link="[0-9a-f]{40,}"[^>]*>([^<]+)<', html)
        pairs = []
        for i, lk in enumerate(links):
            nm = names[i].strip() if i < len(names) and names[i].strip() else ('线路%d' % (i + 1))
            pairs.append((nm, '正片$%s|%s' % (vid, lk)))

        def _rank(nm):
            u = nm.strip().upper()
            return LINE_ORDER.get(u, 50)

        pairs.sort(key=lambda x: _rank(x[0]))
        froms = [p[0] for p in pairs]
        urls = [p[1] for p in pairs]

        # 组装简介：充分利用版面，展示 title, maker, cast, tag, code
        content_lines = [f"Title: {title}"]
        if maker:
            content_lines.append(f"maker: {maker}")
        if actors:
            content_lines.append(f"cast: {', '.join(actors)}")
        if tags:
            content_lines.append(f"tag: {', '.join(tags[:15])}")
        if code:
            content_lines.append(f"search code: {code}")
        content = '\n'.join(content_lines)

        vod = {
            'vod_id': vid,
            'vod_name': code if code else (title or ('SupJav ' + vid)),
            'vod_pic': pic,
            'vod_actor': ' / '.join(actors) if actors else '未知',
            'vod_remarks': '',  # 不显示 views
            'vod_content': content[:800],
            'vod_play_from': '$$$'.join(froms) if froms else 'SupJav',
            'vod_play_url': '$$$'.join(urls) if urls else ('正片$%s|' % vid),
        }
        return {'list': [vod]}

    @staticmethod
    def _voe_decode(html):
        m = re.search(
            r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
            html or '', re.S)
        if not m:
            return {}
        blk = m.group(1).strip()
        try:
            j = json.loads(blk)
            raw = j[0] if isinstance(j, list) and j else blk
        except Exception:
            raw = blk

        s = str(raw)
        for k in ('@$', '^^', '~@', '%?', '*~', '!!', '#&'):
            s = s.replace(k, '_')
        s = s.replace('_', '')

        def b64d(x):
            x = re.sub(r'[^A-Za-z0-9+/=]', '', x)
            x += '=' * (-len(x) % 4)
            return base64.b64decode(x).decode('utf-8', 'replace')

        try:
            t = b64d(codecs.encode(s, 'rot13'))
            t = ''.join(chr(ord(c) - 3) for c in t)
            t = b64d(t[::-1])
            cfg = json.loads(t)
            return cfg if isinstance(cfg, dict) else {}
        except Exception:
            return {}

    def _extract_stream(self, s2, ref):
        if not s2:
            return '', ''

        hits = re.findall(r'https?://[^\s"\'<>\\]+?\.m3u8[^\s"\'<>\\]*', s2)
        if hits:
            return hits[0].replace('\\/', '/'), ''

        if 'eval(function(p,a,c,k,e' in s2:
            dec = self._unpack(s2)
            hits = re.findall(r'https?://[^\s"\'<>\\]+?\.m3u8[^\s"\'<>\\]*', dec)
            if hits:
                return hits[0].replace('\\/', '/'), ''

        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', s2, re.I)
        for ifr in iframes:
            if ifr.startswith('//'):
                ifr = 'https:' + ifr
            if ifr.startswith('http'):
                iframe_html = self._stream(ifr, referer=ref)
                m3, mp4 = self._extract_stream(iframe_html, ifr)
                if m3 or mp4:
                    return m3, mp4

        em = re.search(r'https?://streamtape\.com/e/([A-Za-z0-9]+)', s2)
        if em:
            eurl = 'https://streamtape.com/e/%s/' % em.group(1)
            page = self._stream(eurl, referer=HOST + '/')
            for pat in (r"innerHTML\s*=\s*'([^']+)'\s*\+\s*\('([^']+)'\)"
                        r"\.substring\((\d+)\)",
                        r'innerHTML\s*=\s*"([^"]+)"\s*\+\s*\("([^"]+)"\)'
                        r'\.substring\((\d+)\)'):
                mm = re.search(pat, page or '')
                if not mm:
                    continue
                link = mm.group(1) + mm.group(2)[int(mm.group(3)):]
                if link.startswith('//'):
                    link = 'https:' + link
                if 'dl=' not in link:
                    link += ('&dl=1' if '?' in link else '?dl=1')
                return '', link

        tgt = re.findall(r"window\.location\.href\s*=\s*'([^']+)'", s2)
        tgt += re.findall(r'https?://[a-z0-9.-]+/e/[a-z0-9]{8,}', s2)
        if tgt:
            page = self._stream(tgt[0], referer=ref)
            cfg = self._voe_decode(page)
            src = str(cfg.get('source') or '')
            if '.m3u8' in src:
                return src, ''
            dau = str(cfg.get('direct_access_url') or '')
            if dau.startswith('http'):
                return '', dau
            if src.startswith('http'):
                return '', src

        return '', ''

    def playerContent(self, flag, id, vipFlags):
        raw = str(id)
        vid, _, lk = raw.partition('|')
        vid = re.sub(r'\D', '', vid) or vid
        detail = HOST + '/' + vid + '.html'
        fail = {'parse': 0, 'playUrl': '', 'url': '', 'jx': 0}

        if not lk:
            return fail

        cached = self._play_cache_get(lk)
        if cached:
            return cached

        s1_url = LK_BASE + '?l=' + lk
        s1 = self._stream(s1_url, referer=detail)
        
        om = re.search(r"var\s+OLID\s*=\s*'([0-9a-f]{40,})'", s1 or '')
        if om:
            olid = om.group(1)[::-1]
        else:
            olid = lk[::-1]

        s2 = self._stream(LK_BASE + '?c=' + olid, referer=s1_url)
        if not s2:
            return fail

        m3u8, direct = self._extract_stream(s2, s1_url)

        if not m3u8 and not direct:
            return fail

        if direct:
            res = {
                'parse': 0,
                'playUrl': '',
                'url': direct,
                'jx': 0,
                'header': {'User-Agent': UA, 'Referer': HOST + '/'},
            }
            self._play_cache_put(lk, res)
            return res

        m3u8 = m3u8.replace('\\/', '/').replace('&amp;', '&')

        low = m3u8.lower()
        if 'turbosplayer' in low or 'turboviplay' in low:
            play = SJ_HLS_API + urllib.parse.quote(m3u8, safe='')
        else:
            play = STREAM_API + urllib.parse.quote(m3u8, safe='')

        res = {
            'parse': 0,
            'playUrl': '',
            'url': play,
            'jx': 0,
            'header': {'User-Agent': UA, 'Referer': HOST + '/'},
        }
        self._play_cache_put(lk, res)
        return res
        
