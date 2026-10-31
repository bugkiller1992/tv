# -*- coding: utf-8 -*-
"""
BDSM.DO TVBox Python 爬虫接口 (Type 3) - 完美终极修复版
================================================================
数据源: https://bdsm.do/
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
            {'type_id': 'most-popular', 'type_name': '最热视频'},
            {'type_id': 'categories', 'type_name': '频道分类'}
        ]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self._get(HOST + '/')
        return {'list': self._cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        
        # 精准匹配站点的真实路由路径
        if tid == 'categories':
            url = HOST + '/categories/' if page == 1 else f"{HOST}/categories/{page}/"
        elif tid == 'latest-updates':
            url = HOST + '/' if page == 1 else f"{HOST}/latest-updates/{page}/"
        elif tid == 'most-popular':
            url = HOST + '/most-popular/' if page == 1 else f"{HOST}/most-popular/{page}/"
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

        vod = {
            'vod_id': vid,
            'vod_name': title or 'BDSM Video',
            'vod_pic': pic,
            'vod_remarks': '',
            'vod_content': title,
            'vod_play_from': 'BDSM.DO',
            'vod_play_url': f'播放正片${durl}',
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        url = str(id)
        final_url = url
        
        # 递归抓取播放源逻辑：处理详情页 -> 提取 iframe 或 视频直链
        html = self._get(url)
        if html:
            # 1. 尝试直接从网页中抓取 m3u8 或 mp4 直链
            um = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html)
            if um:
                final_url = um.group(1)
            else:
                # 2. 尝试从 json 或 contentUrl 中提取
                vm = re.search(r'contentUrl["\']?\s*:\s*["\'](https?://[^\s"\']+)', html)
                if vm:
                    final_url = vm.group(1)
                else:
                    # 3. 尝试跟进 iframe 嵌套播放页
                    im = re.search(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', html)
                    if im:
                        iframe_url = im.group(1)
                        sub_html = self._get(iframe_url)
                        sub_um = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', sub_html)
                        if sub_um:
                            final_url = sub_um.group(1)
                        else:
                            final_url = iframe_url

        return {
            'parse': 0,
            'playUrl': '',
            'url': final_url,
            'jx': 0,
            'header': {'User-Agent': UA, 'Referer': HOST + '/'}
        }

    # ---------------- 强兼容卡片解析引擎 ----------------
    @staticmethod
    def _cards(html):
        out, seen = [], set()
        blocks = []
        for pat in [r'<article[^>]*>.*?</article>', r'<div[^>]*class="[^"]*item[^"]*"[^>]*>.*?</div>\s*</div>', r'<div[^>]*class="[^"]*thumb[^"]*"[^>]*>.*?</div>', r'<div[^>]*class="[^"]*video[^"]*"[^>]*>.*?</div>']:
            found = re.findall(pat, html, re.S)
            if found:
                blocks = found
                break
        
        if not blocks:
            blocks = re.split(r'<div[^>]*class="[^"]*col[^"]*"[^>]*>', html)

        for b in blocks:
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

            if not link_path or link_path in seen or 'tag' in link_path or ('category' in link_path and len(link_path) < 10):
                continue
            seen.add(link_path)

            t = re.search(r'title="([^"]+)"', b) or re.search(r'alt="([^"]+)"', b) or re.search(r'<img[^>]*alt="([^"]+)"', b)
            title = t.group(1).strip() if t else ''
            if not title:
                tm = re.search(r'class="[^"]*title[^"]*">([^<]+)<', b)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                title = 'BDSM Video'

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
        
