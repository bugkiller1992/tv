# -*- coding: utf-8 -*-
"""
BDSM.DO TVBox Python 爬虫接口 (Type 3) - 修复重写版
================================================================
数据源: https://bdsm.do/
说明: 增强了卡片与分类的解析容错，确保在 TVBox 中能正常加载列表。
"""
import re
import json
import urllib.parse
import urllib.request
import ssl

try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = object

try:
    import requests
except Exception:
    requests = None

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
HOST = 'https://bdsm.do'


class Spider(BaseSpider):
    def __init__(self):
        if hasattr(BaseSpider, '__init__'):
            try:
                super().__init__()
            except Exception:
                pass
        self.name = 'BDSM.DO'
        self._sess = None
        if requests is not None:
            try:
                self._sess = requests.Session()
                self._sess.headers.update({'User-Agent': UA, 'Referer': HOST + '/'})
            except Exception:
                pass

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

    # ---------------- 网络请求层 ----------------
    def _get(self, url, timeout=30):
        if self._sess is not None:
            try:
                r = self._sess.get(url, timeout=timeout, verify=False)
                if r.status_code == 200:
                    return r.text
            except Exception:
                pass
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': HOST + '/'})
            return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'replace')
        except Exception:
            return ''

    # ---------------- TVBox 接口实现 ----------------
    def homeContent(self, filter):
        classes = [
            {'type_id': 'latest-updates', 'type_name': '最新更新'},
            {'type_id': 'most-popular', 'type_name': '热门视频'},
            {'type_id': 'top-rated', 'type_name': '高分评价'},
            {'type_id': 'categories', 'type_name': '频道分类'}
        ]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self._get(HOST + '/')
        return {'list': self._cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        if tid == 'categories':
            url = HOST + '/categories/'
        else:
            url = f"{HOST}/{tid}/" if page == 1 else f"{HOST}/{tid}/{page}/"

        html = self._get(url)
        items = self._cards(html)
        return {
            'page': page,
            'pagecount': 50,
            'limit': len(items) or 24,
            'total': len(items),
            'list': items,
        }

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        kw = urllib.parse.quote(str(key))
        url = f"{HOST}/search/{kw}/" if page == 1 else f"{HOST}/search/{kw}/{page}/"
        html = self._get(url)
        items = self._cards(html)
        return {
            'page': page,
            'pagecount': 20,
            'limit': len(items) or 24,
            'total': len(items),
            'list': items,
        }

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids)
        durl = HOST + '/' + vid.lstrip('/') if not vid.startswith('http') else vid
        html = self._get(durl)

        title = ''
        tm = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if tm:
            title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()

        pic = ''
        pm = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if pm:
            pic = pm.group(1)

        # 提取播放地址 (m3u8 / mp4 / embed)
        play_url = ''
        vm = re.search(r'contentUrl["\']?\s*:\s*["\'](https?://[^\s"\']+)', html)
        if vm:
            play_url = vm.group(1)
        else:
            um = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html)
            if um:
                play_url = um.group(1)

        vod = {
            'vod_id': vid,
            'vod_name': title or 'BDSM Video',
            'vod_pic': pic,
            'vod_remarks': '',
            'vod_content': title,
            'vod_play_from': 'BDSM.DO',
            'vod_play_url': f'播放正片${play_url or durl}',
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        url = str(id)
        if not self.isVideoFormat(url):
            html = self._get(url)
            um = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html)
            if um:
                url = um.group(1)
        return {
            'parse': 0,
            'playUrl': '',
            'url': url,
            'jx': 0,
            'header': {'User-Agent': UA, 'Referer': HOST + '/'}
        }

    # ---------------- 强兼容卡片解析引擎 ----------------
    @staticmethod
    def _cards(html):
        out, seen = [], set()
        
        # 多重策略切片：兼容 article、div.item、div.thumb 等各种主流布局
        blocks = []
        for pat in [r'<article[^>]*>.*?</article>', r'<div[^>]*class="[^"]*item[^"]*"[^>]*>.*?</div>\s*</div>', r'<div[^>]*class="[^"]*thumb[^"]*"[^>]*>.*?</div>']:
            found = re.findall(pat, html, re.S)
            if found:
                blocks = found
                break
        
        # 如果常规标签没切出来，退化为按行或按链接块匹配
        if not blocks:
            blocks = re.split(r'<div[^>]*class="[^"]*col[^"]*"[^>]*>', html)

        for b in blocks:
            # 提取详情链接
            m = re.search(r'href="([^"]*/video/[^"]+|[^"]*/\d+/[^"]+|[^"]+\.html)"', b)
            if not m:
                m = re.search(r'href="([^"]+)"', b)
            if not m:
                continue
            
            link = m.group(1)
            if 'http' in link:
                if HOST not in link:
                    continue
                link_path = link.replace(HOST + '/', '').lstrip('/')
            else:
                link_path = link.lstrip('/')

            if not link_path or link_path in seen or 'tag' in link_path or 'category' in link_path and len(link_path) < 10:
                continue
            seen.add(link_path)

            # 提取标题
            t = re.search(r'title="([^"]+)"', b) or re.search(r'alt="([^"]+)"', b) or re.search(r'<img[^>]*alt="([^"]+)"', b)
            title = t.group(1).strip() if t else ''
            if not title:
                tm = re.search(r'class="[^"]*title[^"]*">([^<]+)<', b)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                title = 'BDSM Video'

            # 提取封面图 (支持 data-original 懒加载或 src)
            pic = ''
            for pm_pat in [r'data-original="([^"]+)"', r'data-src="([^"]+)"', r'src="([^"]+)"']:
                pm = re.search(pm_pat, b)
                if pm:
                    pic = pm.group(1)
                    if 'http' in pic or pic.startswith('//'):
                        break
            if pic.startswith('//'):
                pic = 'https:' + pic
            elif pic and not pic.startswith('http'):
                pic = HOST + '/' + pic.lstrip('/')

            # 提取时长等备注
            dur = ''
            dm = re.search(r'class="[^"]*duration[^"]*"[^>]*>([^<]+)<', b) or re.search(r'class="[^"]*time[^"]*"[^>]*>([^<]+)<', b)
            if dm:
                dur = dm.group(1).strip()

            out.append({
                'vod_id': link_path,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': dur,
            })
        return out
        
