# -*- coding: utf-8 -*-

import sys, re, json, time, base64, hashlib, threading, http.server, socket, struct
from urllib.parse import urljoin, quote, unquote
from concurrent.futures import ThreadPoolExecutor
import requests

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = requests.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

def _wdir(name, legacy=''):
    import os, tempfile
    for d in (tempfile.gettempdir(), '/data/local/tmp', '/sdcard/.cache'):
        try:
            if d and os.path.isdir(d):
                p = os.path.join(d, name)
                os.makedirs(p, exist_ok=True)
                return p
        except Exception:
            pass
    return legacy or os.path.join(tempfile.gettempdir(), name)


# ============ ★ CONFIG ============
HOSTS = ['https://5xsq.com']
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
CLASSES = [('0', '全部视频'), ('1', '国产AV'), ('2', '日本无码'), ('3', '无码破解'), ('4', '主播福利'), ('5', '探花大神'), ('6', '日本有码'), ('7', '欧美'), ('8', '加勒比'), ('9', '小格式综合'), ('10', '本道'), ('11', '成人动漫'), ('12', '天然素人'), ('13', 'Paco'), ('14', '丝袜诱惑'), ('15', '东京热'), ('16', '器具自慰'), ('17', '中文字幕'), ('18', '韩国综合'), ('19', '三级片'), ('20', '高清'), ('21', 'SM性虐'), ('22', '户外公众'), ('23', '口爆颜射'), ('24', '会员原创'), ('25', '韩国女主播'), ('26', '性party'), ('27', '李宗瑞全集'), ('28', '潮吹'), ('29', '女同'), ('30', '肛交')]
CATEGORIES = dict(CLASSES)
SLUG = {'0': '', '1': 'homemade-selfie', '2': 'Japan Uncensored', '3': 'reducing-mosaic', '4': 'chinese-anchor', '5': 'tanhua-god', '6': 'Japan Coded', '7': 'Europe and America', '8': 'Caribbeancom', '9': 'Small format synthesis', '10': 'pondo', '11': 'Adult Anime', '12': '10musume', '13': 'Pacopacomama', '14': 'Pantyhose temptation', '15': 'Tokyo Hot', '16': 'Masturbation', '17': 'Chinese subtitle', '18': 'Korea General', '19': 'Tertiary film', '20': 'HD', '21': 'sm', '22': 'Public places and outdoors', '23': 'Cumshot', '24': '5XSQ members original works', '25': 'Korean female anchor series', '26': 'Sex party', '27': 'The Complete Works of Li Zongrui', '28': 'Squirting', '29': 'Lesbian', '30': 'Anal sex'}
SORTS = [('mr', '最新'), ('mv', '最受欢迎'), ('bw', '被观看'), ('tr', '最高评分'), ('md', '最多评论'), ('tf', '最爱'), ('lg', '最长')]
TIMES = [('a', '全部时间'), ('t', '今天'), ('w', '本周'), ('m', '本月')]
PAGE_SIZE = 30
CDN = 'https://cdnmm1.m3uu.cc'
TTL_HTML = 600
DET_TTL = 600
STALE_MAX = 1800
PK = ''
REFERER = 'https://5xsq.com/'
PIC_REFERER = ''
FD_ZONE = 0
PROBE = 1
SITE_KEY = '5xsq'
VIDEO_EXTS = 'm3u8|mp4|ts'
CF_GUARD = 0
CF_HOST = ''
CF_COOKIE_DIR = _wdir('5xsq')
CARD_ON = 1
CARD_TYPE = 'rect'
CARD_LAND = 1
HOME_VIDEO_ON = 1
CARD_RATIO = 1.78
CARD = {'type': CARD_TYPE, 'ratio': CARD_RATIO}
CARD_SRC = '5X社区'
LP_MODE = 'list'


# ============ AES 纯Python引擎(Crypto不可用时降级) ============
SBOX = [99, 124, 119, 123, 242, 107, 111, 197, 48, 1, 103, 43, 254, 215, 171, 118, 202, 130, 201, 125, 250, 89, 71, 240, 173, 212, 162, 175, 156, 164, 114, 192, 183, 253, 147, 38, 54, 63, 247, 204, 52, 165, 229, 241, 113, 216, 49, 21, 4, 199, 35, 195, 24, 150, 5, 154, 7, 18, 128, 226, 235, 39, 178, 117, 9, 131, 44, 26, 27, 110, 90, 160, 82, 59, 214, 179, 41, 227, 47, 132, 83, 209, 0, 237, 32, 252, 177, 91, 106, 203, 190, 57, 74, 76, 88, 207, 208, 239, 170, 251, 67, 77, 51, 133, 69, 249, 2, 127, 80, 60, 159, 168, 81, 163, 64, 143, 146, 157, 56, 245, 188, 182, 218, 33, 16, 255, 243, 210, 205, 12, 19, 236, 95, 151, 68, 23, 196, 167, 126, 61, 100, 93, 25, 115, 96, 129, 79, 220, 34, 42, 144, 136, 70, 238, 184, 20, 222, 94, 11, 219, 224, 50, 58, 10, 73, 6, 36, 92, 194, 211, 172, 98, 145, 149, 228, 121, 231, 200, 55, 109, 141, 213, 78, 169, 108, 86, 244, 234, 101, 122, 174, 8, 186, 120, 37, 46, 28, 166, 180, 198, 232, 221, 116, 31, 75, 189, 139, 138, 112, 62, 181, 102, 72, 3, 246, 14, 97, 53, 87, 185, 134, 193, 29, 158, 225, 248, 152, 17, 105, 217, 142, 148, 155, 30, 135, 233, 206, 85, 40, 223, 140, 161, 137, 13, 191, 230, 66, 104, 65, 153, 45, 15, 176, 84, 187, 22]
IS = [0] * 256
for _i, _v in enumerate(SBOX):
    IS[_v] = _i
RCON = [1, 2, 4, 8, 16, 32, 64, 128, 27, 54, 108, 216, 171, 77]
G2 = [0] * 256
G3 = [0] * 256
for _i in range(256):
    _t = _i << 1
    if _i & 128:
        _t ^= 0x11b
    G2[_i] = _t
    G3[_i] = G2[_i] ^ _i


def _ke(k):
    nk = len(k) // 4
    nr = nk + 6
    w = [list(k[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        t = w[i - 1][:]
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            t = [SBOX[b] for b in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return w


def _enc(b, w):
    s = [[b[r + 4 * c] for c in range(4)] for r in range(4)]
    def add(r):
        for i in range(4):
            for j in range(4):
                s[i][j] ^= w[r * 4 + j][i]
    def sub():
        for i in range(4):
            for j in range(4):
                s[i][j] = SBOX[s[i][j]]
    def sh():
        for r in range(1, 4):
            s[r] = s[r][r:] + s[r][:r]
    def mx():
        for c in range(4):
            a = [s[r][c] for r in range(4)]
            s[0][c] = G2[a[0]] ^ G3[a[1]] ^ a[2] ^ a[3]
            s[1][c] = a[0] ^ G2[a[1]] ^ G3[a[2]] ^ a[3]
            s[2][c] = a[0] ^ a[1] ^ G2[a[2]] ^ G3[a[3]]
            s[3][c] = G3[a[0]] ^ a[1] ^ a[2] ^ G2[a[3]]
    add(0)
    nr = len(w) // 4 - 1
    for rnd in range(1, nr):
        sub()
        sh()
        mx()
        add(rnd)
    sub()
    sh()
    add(nr)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def _gm(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        a = (a << 1) ^ 0x11b if a & 0x80 else a << 1
        b >>= 1
    return p & 0xff


def _dec(b, w):
    s = [[b[r + 4 * c] for c in range(4)] for r in range(4)]
    def add(r):
        for i in range(4):
            for j in range(4):
                s[i][j] ^= w[r * 4 + j][i]
    def isub():
        for i in range(4):
            for j in range(4):
                s[i][j] = IS[s[i][j]]
    def ish():
        for r in range(1, 4):
            s[r] = s[r][-r:] + s[r][:-r]
    def imx():
        for c in range(4):
            a = [s[r][c] for r in range(4)]
            s[0][c] = _gm(a[0], 14) ^ _gm(a[1], 11) ^ _gm(a[2], 13) ^ _gm(a[3], 9)
            s[1][c] = _gm(a[0], 9) ^ _gm(a[1], 14) ^ _gm(a[2], 11) ^ _gm(a[3], 13)
            s[2][c] = _gm(a[0], 13) ^ _gm(a[1], 9) ^ _gm(a[2], 14) ^ _gm(a[3], 11)
            s[3][c] = _gm(a[0], 11) ^ _gm(a[1], 13) ^ _gm(a[2], 9) ^ _gm(a[3], 14)
    nr = len(w) // 4 - 1
    add(nr)
    for rnd in range(nr - 1, 0, -1):
        ish()
        isub()
        add(rnd)
        imx()
    ish()
    isub()
    add(0)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def aes_ecb(data, key, mode=1):
    w = _ke(key)
    out = b''
    if mode:
        pad = 16 - len(data) % 16
        data += bytes([pad]) * pad
        for i in range(0, len(data), 16):
            out += _enc(data[i:i + 16], w)
    else:
        for i in range(0, len(data), 16):
            out += _dec(data[i:i + 16], w)
        if out and 0 < out[-1] <= 16:
            out = out[:-out[-1]]
    return out


def aes_cbc(data, key, iv, enc=1):
    w = _ke(key)
    out = b''
    prev = iv
    if enc:
        pad = 16 - len(data) % 16
        data += bytes([pad]) * pad
        for i in range(0, len(data), 16):
            blk = bytes(data[i + j] ^ prev[j] for j in range(16))
            ct = _enc(blk, w)
            out += ct
            prev = ct
    else:
        for i in range(0, len(data), 16):
            blk = _dec(data[i:i + 16], w)
            out += bytes(blk[j] ^ prev[j] for j in range(16))
            prev = data[i:i + 16]
        if out and 0 < out[-1] <= 16:
            out = out[:-out[-1]]
    return out


# ============ ★88-8 CFGuard过盾引擎（站点无关·整段可替换；来源 cf_guard.py 2026-09-13） ============
import os, urllib.parse

try:
    from java import jclass, dynamic_proxy
except ImportError:
    jclass = None
    dynamic_proxy = None




class CFGuard(object):

    UA_DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    CF_MARKS = ('just a moment', 'checking your browser', 'cf-mitigated', 'challenge-platform',
                'enable javascript and cookies to continue', 'attention required! | cloudflare',
                'verify you are human')
    COOKIE_DIR = _wdir('123')
    POLL_GAP = 1.5
    POLL_START = 2.0
    MAX_REFS = 60
    _cls_cache = {}

    def __init__(self, host='', cookie_dir=None, log=None, images=False):
        h = str(host or '').strip().rstrip('/')
        if h and '://' not in h:
            h = 'https://' + h
        self.host = h
        self.domain = urllib.parse.urlparse(h).netloc or h or 'default'
        self.cookie_dir = cookie_dir or self.COOKIE_DIR
        self.on_log = log
        self.images = images
        self.last_wv_ua = ''
        self.cf_marks = tuple(self.CF_MARKS)
        self._refs = []

    def available(self):
        return not (jclass is None or dynamic_proxy is None)

    def set_log(self, fn):
        self.on_log = fn

    def _log(self, msg):
        try:
            if self.on_log:
                self.on_log(msg)
                return
        except Exception:
            pass
        print('[CFGuard] ' + str(msg))

    def _keep(self, *objs):
        for o in objs:
            if o is not None:
                self._refs.append(o)
        if len(self._refs) > self.MAX_REFS:
            del self._refs[:len(self._refs) - self.MAX_REFS]

    def _cls_vc(self):
        c = CFGuard._cls_cache.get('vc')
        if c is None:
            base = dynamic_proxy(jclass('android.webkit.ValueCallback'))

            class _VC(base):
                def onReceiveValue(self, value):
                    fn = getattr(self, '_fn', None)
                    if fn:
                        fn(value)
            c = CFGuard._cls_cache['vc'] = _VC
        return c

    def _cls_run(self):
        c = CFGuard._cls_cache.get('run')
        if c is None:
            base = dynamic_proxy(jclass('java.lang.Runnable'))

            class _Run(base):
                def run(self):
                    fn = getattr(self, '_fn', None)
                    if fn:
                        fn()
            c = CFGuard._cls_cache['run'] = _Run
        return c

    def _cls_click(self):
        c = CFGuard._cls_cache.get('click')
        if c is None:
            base = dynamic_proxy(jclass('android.content.DialogInterface').OnClickListener)

            class _Click(base):
                def onClick(self, dialog, which):
                    fn = getattr(self, '_fn', None)
                    if fn:
                        fn(dialog, which)
            c = CFGuard._cls_cache['click'] = _Click
        return c

    def _activity(self):
        try:
            AT = jclass("java.lang.Class").forName("android.app.ActivityThread")
            cur = AT.getMethod("currentActivityThread").invoke(None)
            f = AT.getDeclaredField("mActivities")
            f.setAccessible(True)
            map_obj = f.get(cur)
            values = map_obj.values().toArray() if hasattr(map_obj, "values") else map_obj.toArray()
            for r in values:
                rc = r.getClass()
                pf = rc.getDeclaredField("paused")
                pf.setAccessible(True)
                if not pf.getBoolean(r):
                    af = rc.getDeclaredField("activity")
                    af.setAccessible(True)
                    a = af.get(r)
                    if a:
                        return a
        except Exception:
            pass
        return None

    def _ui(self, fn):
        if not self.available():
            return False
        act = self._activity()
        if not act:
            return False
        try:
            r = self._cls_run()()
            r._fn = lambda: fn(act)
            self._keep(r)
            act.getWindow().getDecorView().post(r)
        except Exception:
            try:
                r2 = self._cls_run()()
                r2._fn = lambda: fn(act)
                self._keep(r2)
                jclass('android.os.Handler')(jclass('android.os.Looper').getMainLooper()).post(r2)
            except Exception:
                return False
        return True

    def _click(self, fn):
        c = self._cls_click()()
        c._fn = fn
        self._keep(c)
        return c

    def is_cf(self, text):
        if not text:
            return True
        low = str(text).lower()
        return any(m in low for m in self.cf_marks)

    def _domain(self, url):
        return urllib.parse.urlparse(str(url or '')).netloc or self.domain

    def _cookie_path(self, domain):
        return os.path.join(self.cookie_dir, str(domain or self.domain) + '.json')

    def cookies_data(self, domain=None):
        domain = str(domain or self.domain)
        p = self._cookie_path(domain)
        if not os.path.exists(p) and domain != self.domain:
            p = self._cookie_path(self.domain)
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if d.get('cookies'):
                    return d
        except Exception as e:
            self._log('读取CF cookie缓存失败: ' + str(e))
        return None

    def cookies(self, domain=None):
        d = self.cookies_data(domain)
        return dict(d.get('cookies') or {}) if d else {}

    def cookie_header(self, domain=None):
        return '; '.join('%s=%s' % (k, v) for k, v in self.cookies(domain).items())

    def ua(self, domain=None, fallback=None):
        d = self.cookies_data(domain)
        return str((d.get('ua') if d else '') or self.last_wv_ua or fallback or self.UA_DESKTOP)

    def save(self, domain, cookies, ua=''):
        try:
            os.makedirs(self.cookie_dir, exist_ok=True)
            with open(self._cookie_path(domain), 'w', encoding='utf-8') as f:
                json.dump({'cookies': cookies, 'ua': ua, 'ts': int(time.time())}, f,
                          ensure_ascii=False, indent=2)
            self._log('已保存CF cookie -> ' + self._cookie_path(domain))
        except Exception as e:
            self._log('保存CF cookie失败: ' + str(e))

    def restore(self):
        try:
            d = self.cookies_data(self.domain)
            if not (d and d.get('cookies')) or jclass is None:
                return False
            cm = jclass('android.webkit.CookieManager').getInstance()
            cm.setAcceptCookie(True)
            site = self.host or ('https://' + self.domain)
            for k, v in d['cookies'].items():
                cm.setCookie(site, '%s=%s' % (k, v))
            cm.flush()
            self._log('[恢复] CookieManager写入完成')
            return True
        except Exception as e:
            self._log('[恢复] 写回CookieManager失败: ' + str(e))
            return False

    def wv_html(self, url, timeout=15, ua=None):
        if not self.available():
            return None
        cached = self.cookies_data(self._domain(url))
        target_ua = ua or (cached or {}).get('ua') or self.last_wv_ua or self.UA_MOBILE
        evt = threading.Event()
        store = {'html': None}

        def on_ui(act):
            try:
                WebView = jclass('android.webkit.WebView')
                WebViewClient = jclass('android.webkit.WebViewClient')
                wv = WebView(act)
                st = wv.getSettings()
                st.setJavaScriptEnabled(True)
                st.setDomStorageEnabled(True)
                st.setUserAgentString(str(target_ua))
                if not self.images:
                    try:
                        st.setLoadsImagesAutomatically(False)
                    except Exception:
                        pass
                wv.setWebViewClient(WebViewClient())
                wv.loadUrl(url)

                def cleanup():
                    try:
                        wv.stopLoading()
                        wv.loadUrl('about:blank')
                        wv.clearHistory()
                        wv.removeAllViews()
                        wv.destroy()
                    except Exception:
                        pass

                vc = self._cls_vc()()

                def _on_val(value):
                    try:
                        html = json.loads(value) if isinstance(value, str) else str(value)
                    except Exception:
                        html = str(value) if value is not None else ''
                    if html and not self.is_cf(html):
                        store['html'] = html
                        evt.set()
                        cleanup()

                vc._fn = _on_val
                self._keep(vc)
                handler = jclass('android.os.Handler')(jclass('android.os.Looper').getMainLooper())
                start = time.time()

                def loop():
                    if evt.is_set():
                        return
                    if time.time() - start > timeout:
                        evt.set()
                        cleanup()
                        return
                    try:
                        wv.evaluateJavascript('document.documentElement.outerHTML', vc)
                    except Exception:
                        evt.set()
                        cleanup()
                        return
                    r = self._cls_run()()
                    r._fn = loop
                    self._keep(r)
                    handler.postDelayed(r, int(self.POLL_GAP * 1000))

                r0 = self._cls_run()()
                r0._fn = loop
                self._keep(r0)
                handler.postDelayed(r0, int(self.POLL_START * 1000))
            except Exception as e:
                self._log('[wv] 初始化失败: ' + str(e))
                evt.set()

        if not self._ui(on_ui):
            return None
        evt.wait(timeout=timeout + 2)
        return store['html']

    def verify(self, url=None):
        url = url or ((self.host or '') + '/')
        ua = self.ua()
        headers = {'User-Agent': ua, 'Referer': (self.host or '') + '/'}

        def on_cookies(cks):
            self._log('验证完成: ' + (', '.join(cks.keys()) if cks else '无cookie'))
            if cks:
                self.save(self._domain(url), cks, self.last_wv_ua or ua)
                self.restore()
                self.toast('Cookie 验证成功并保存！')

        self._verify_dialog(url, headers, on_cookies)

    def _verify_dialog(self, url, base_headers, on_cookies):
        if not self.available():
            on_cookies({})
            return

        def on_ui(act):
            try:
                WebView = jclass('android.webkit.WebView')
                WebViewClient = jclass('android.webkit.WebViewClient')
                LinearLayout = jclass('android.widget.LinearLayout')
                TextView = jclass('android.widget.TextView')
                Builder = jclass('android.app.AlertDialog$Builder')
                CookieManager = jclass('android.webkit.CookieManager')
                TypedValue = jclass('android.util.TypedValue')
                pad = int(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 8.0,
                                                    act.getResources().getDisplayMetrics()))
                container = LinearLayout(act)
                container.setOrientation(LinearLayout.VERTICAL)
                tip = TextView(act)
                tip.setText('请完成验证（勾选/点击/输入验证码），成功后点「完成」')
                tip.setPadding(pad, pad, pad, pad)
                wv = WebView(act)
                wv.getSettings().setJavaScriptEnabled(True)
                wv.getSettings().setDomStorageEnabled(True)
                hm = jclass('java.util.HashMap')()
                for k, v in base_headers.items():
                    hm.put(str(k), str(v))
                wv.setWebViewClient(WebViewClient())
                wv.loadUrl(url, hm)
                container.addView(tip)
                container.addView(wv)
                try:
                    self.last_wv_ua = str(wv.getSettings().getUserAgentString())
                except Exception:
                    self.last_wv_ua = ''
                result = {'cookies': {}}

                def _collect():
                    raw = CookieManager.getInstance().getCookie(url) or ''
                    out = {}
                    for part in raw.split(';'):
                        part = part.strip()
                        if '=' in part:
                            k, v = part.split('=', 1)
                            out[k.strip()] = v
                    result['cookies'] = out

                def _finish(d, w):
                    _collect()
                    try:
                        if dialog is not None:
                            dialog.dismiss()
                    except Exception:
                        pass
                    on_cookies(result['cookies'])

                builder = Builder(act)
                builder.setTitle('手动过验证')
                builder.setView(container)
                builder.setPositiveButton('完成', self._click(_finish))
                builder.setNegativeButton('取消', self._click(lambda d, w: on_cookies({})))
                dialog = builder.create()
                dialog.show()
            except Exception as e:
                self._log('[verify] 弹窗失败: ' + str(e))
                on_cookies({})

        self._ui(on_ui)

    def show_log(self, lines=None, title='信息', text=''):
        body = text or ''
        if lines:
            body = (body + '\n' if body else '') + '\n'.join(str(x) for x in lines)

        def on_ui(act):
            try:
                Builder = jclass('android.app.AlertDialog$Builder')
                TextView = jclass('android.widget.TextView')
                ScrollView = jclass('android.widget.ScrollView')
                Color = jclass('android.graphics.Color')
                TypedValue = jclass('android.util.TypedValue')
                tv = TextView(act)
                tv.setText(body or '(空)')
                tv.setTextIsSelectable(True)
                tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13.0)
                tv.setTextColor(Color.parseColor('#334155'))
                pad = int(TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, 12.0,
                                                    act.getResources().getDisplayMetrics()))
                tv.setPadding(pad, pad, pad, pad)
                scroll = ScrollView(act)
                scroll.addView(tv)
                builder = Builder(act)
                builder.setTitle(str(title))
                builder.setView(scroll)
                builder.setPositiveButton('关闭', self._click(lambda d, w: d.dismiss() if d else None))
                dialog = builder.create()
                self._keep(dialog, tv, scroll)
                dialog.show()
            except Exception as e:
                self._log('[show_log] 失败: ' + str(e))

        return self._ui(on_ui)

    def toast(self, msg, duration=1):
        def on_ui(act):
            try:
                jclass('android.widget.Toast').makeText(act, str(msg), int(duration)).show()
            except Exception:
                pass
        return self._ui(on_ui)



class Spider(Spider):
    def init(self, extend=''):
        self.base = HOSTS[0].rstrip('/')
        self.ua = UA
        self.pk = PK
        self.ref = REFERER or (self.base + '/')
        self.types = dict(CATEGORIES)
        self.filters = self._mkf()
        self._pc = {}
        self._mu = {}
        self._ss = None
        self._gc = {}
        self._cc = {}
        self._dc = {}
        self._bgq = {}
        self._warmed = False
        self._srv = None
        self._port = 0
        self._lock = threading.Lock()
        self._siteKey = SITE_KEY
        self._vflags = {}
        self.cf = None

    def _mkf(self):
        f = {'%s' % k: [{'key': 'o', 'name': '排序', 'value': [{'n': n, 'v': v} for v, n in SORTS]},
                        {'key': 't', 'name': '时间', 'value': [{'n': n, 'v': v} for v, n in TIMES]}]
             for k in CATEGORIES.keys()}
        return f

    def _hd(self):
        return {'User-Agent': self.ua, 'Referer': self.ref, 'Accept-Language': 'zh-CN,zh;q=0.9'}

    def _sess(self):
        ss = self._ss
        if ss is None:
            ss = requests.Session()
            ad = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=24, max_retries=0, pool_block=False)
            ss.mount('https://', ad)
            ss.mount('http://', ad)
            self._ss = ss
        return ss

    def _raww(self, url, hd, timeout, box):
        try:
            r = self._sess().get(url, headers=hd, timeout=(5, timeout), allow_redirects=True)
            r.encoding = 'utf-8'
            t = r.text if r.status_code == 200 else ''
            if t and len(t) > 2000 and not box[0]:
                box[0] = t
        except Exception:
            pass

    # ★必检①(方法级) 取页：会话复用 + 对冲hedge(1.5s后追二路) + 过期可用 + 后台刷新
    def _fetch(self, url, timeout=15):
        hd = self._hd()
        box = ['']
        pool = ThreadPoolExecutor(2)
        pool.submit(self._raww, url, hd, timeout, box)
        t0 = time.time()
        d2 = False
        while time.time() - t0 < timeout and not box[0]:
            if not d2 and time.time() - t0 >= 1.5:
                d2 = True
                pool.submit(self._raww, url, hd, timeout, box)
            time.sleep(0.08)
        pool.shutdown(wait=False)
        return box[0]

    def _bg(self, url, timeout=15):
        if url in self._bgq:
            return
        self._bgq[url] = 1

        def _r():
            try:
                t = self._fetch(url, timeout)
                if t:
                    self._gc[url] = (time.time(), t)
                    if len(self._gc) > 24:
                        for k in list(self._gc)[:8]:
                            self._gc.pop(k, None)
            except Exception:
                pass
            finally:
                self._bgq.pop(url, None)
        try:
            th = threading.Thread(target=_r)
            th.daemon = True
            th.start()
        except Exception:
            self._bgq.pop(url, None)

    def _get(self, url, headers=None, timeout=15):
        c = self._gc.get(url)
        now = time.time()
        if c:
            age = now - c[0]
            if age < TTL_HTML:
                return c[1]
            if age < STALE_MAX:
                self._bg(url, timeout)
                return c[1]
        t = self._fetch(url, timeout)
        if t:
            self._gc[url] = (time.time(), t)
            if len(self._gc) > 24:
                for k in list(self._gc)[:8]:
                    self._gc.pop(k, None)
            return t
        return c[1] if c else ''

    # ★必检②(方法级) 冷启动预热：首屏之后后台预取前3个分类，点开即命中缓存
    def _warm(self, tids):
        if self._warmed:
            return
        self._warmed = True

        def _one(t):
            try:
                u = self._cat_url(t, 1, {})
                if u in self._gc:
                    return
                self._get(u, timeout=15)
            except Exception:
                pass

        def _run():
            for t in tids:
                _one(t)
        try:
            th = threading.Thread(target=_run)
            th.daemon = True
            th.start()
        except Exception:
            pass

    def _bget(self, url, timeout=25):
        try:
            r = requests.get(url, headers=self._hd(), timeout=timeout, allow_redirects=True)
            return r.status_code, r.content, r.headers.get('Content-Type', 'application/octet-stream')
        except Exception:
            return 0, b'', 'application/octet-stream'

    def _pic(self, u):
        u = (u or '').strip()
        if not u:
            return ''
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith('/'):
            return self.base + u
        return u

    def _un(self, s):
        s = str(s or '')
        A = chr(38)
        for a, b in ((A + 'lt;', '<'), (A + 'gt;', '>'), (A + 'quot;', chr(34)), (A + '#39;', chr(39)), (A + 'nbsp;', ' '), (A + 'amp;', '&')):
            s = s.replace(a, b)
        return s

    def _cw(self, d):
        if CARD_ON and isinstance(d, dict):
            d['style'] = dict(CARD)
            if 'land' not in d:
                d['land'] = CARD_LAND
            if 'ratio' not in d:
                d['ratio'] = CARD_RATIO
            if 'type_name' not in d:
                d['type_name'] = CARD_SRC
        return d

    def _ct(self, tid, nm):
        c = {'type_id': str(tid), 'type_name': nm}
        if CARD_ON:
            c['land'] = CARD_LAND
            c['ratio'] = CARD_RATIO
        return c

    def _pagecount(self, h, cur=1):
        pm = [int(x) for x in re.findall(r'[?&]page=(\d+)', h or '')]
        pc = max(pm) if pm else int(cur)
        return max(pc, int(cur))

    # ★必检④(方法级) 分类 30 项全覆盖 + filters 排序/时间双维
    def homeContent(self, filter=False):
        r = {'class': [self._ct(k, v) for k, v in self.types.items()]}
        if filter and self.filters:
            r['filters'] = self.filters
        r['list'] = self.homeVideoContent().get('list', [])
        return r

    # ★必加①(方法级) 大图卡片四件套经 _cw 注入；首页推荐 /videos 30 条
    def homeVideoContent(self):
        if not HOME_VIDEO_ON:
            return {'list': []}
        self._warm([k for k in CATEGORIES.keys() if k != '0'][:6])
        l = self._rss_items()
        if not l:
            h = self._get(self.base + '/videos')
            l = self._items(h) if h else []
        return {'list': l}

    # ★必检①(方法级) 翻页四件齐全 + pagecount 真解析
    def categoryContent(self, tid, pg=1, filter=False, extend=''):
        try:
            pn = max(int(str(pg)), 1)
        except Exception:
            pn = 1
        ex = {}
        if extend:
            try:
                ex = json.loads(extend) if isinstance(extend, str) else dict(extend)
            except Exception:
                ex = {}
        ck = '%s|%s|%s' % (tid, pn, json.dumps(ex, sort_keys=True, ensure_ascii=False))
        cc = self._cc.get(ck)
        now = time.time()
        if cc and now - cc[0] < 120:
            return cc[1]
        lim = self._pc.get('pc|%s' % str(tid))
        if lim and pn > int(lim[0]) + 2:
            return {'page': pn, 'pagecount': int(lim[0]), 'limit': PAGE_SIZE, 'total': int(lim[0]) * PAGE_SIZE, 'list': []}
        h = self._get(self._cat_url(tid, pn, ex), timeout=15)
        if not h:
            if cc:
                return cc[1]
            return {'page': pn, 'pagecount': max(pn, 1), 'limit': PAGE_SIZE, 'total': PAGE_SIZE, 'list': []}
        items = self._items(h)
        pc = self._pagecount(h, pn)
        self._pc['pc|%s' % str(tid)] = (pc, now)
        r = {'page': pn, 'pagecount': pc, 'limit': PAGE_SIZE, 'total': max(pc * PAGE_SIZE, len(items)), 'list': items}
        self._cc[ck] = (time.time(), r)
        try:
            self._bg(self._cat_url(tid, pn + 1, ex), 15)
        except Exception:
            pass
        if len(self._cc) > 60:
            for k in list(self._cc)[:20]:
                self._cc.pop(k, None)
        return r

    def _cat_url(self, t, pn, ex=None):
        e = ex or {}
        slug = SLUG.get(str(t), '')
        o = str(e.get('o') or 'mr').strip()
        tm = str(e.get('t') or 'a').strip()
        if slug:
            base_u = self.base + '/videos/' + quote(slug, safe='')
        else:
            base_u = self.base + '/videos'
        qs = []
        if o and o not in ('mr', 'default', '全部', '默认'):
            qs.append('o=' + quote(o, safe=''))
        if tm and tm not in ('a', '', '全部'):
            qs.append('t=' + quote(tm, safe=''))
        if int(pn) > 1:
            qs.append('page=%d' % int(pn))
        return base_u + ('?' + '&'.join(qs) if qs else '')

    def _probe_lines(self, froms, urls):
        key = hashlib.md5(('|'.join(froms) + '#' + '|'.join(urls)).encode()).hexdigest()
        c = self._pc.get(key)
        if c and time.time() - c[0] < 300:
            return c[1], c[2]

        def _probe(i):
            u = urls[i].split('#')[0].split('$')[-1]
            try:
                if '.m3u8' in u:
                    code, body, ct = self._bget(u, 6)
                    return 0 if code == 200 and b'#EXTM3U' in (body or b'') else 1
                h = self._get(u, timeout=6)
                mu = self._pick_m3u8(h) if h else ''
                if mu:
                    code, body, ct = self._bget(mu, 6)
                    if code == 200 and b'#EXTM3U' in (body or b''):
                        self._mu[str(re.search(r'(\d{4,})', u).group(1)) if re.search(r'(\d{4,})', u) else ''] = mu
                        return 0
                return 1
            except Exception:
                return 1

        try:
            with ThreadPoolExecutor(max_workers=max(1, min(len(froms), 4))) as ex:
                res = list(ex.map(_probe, range(len(froms))))
        except Exception:
            res = [0] * len(froms)
        pairs = sorted(zip(froms, urls, res), key=lambda x: x[2])
        out = ([p[0] for p in pairs], [p[1] for p in pairs])
        self._pc[key] = [time.time(), out[0], out[1]]
        return out

    # ★必检②(方法级) 双线路解析，死线排后不剔除
    def detailContent(self, ids, quick='1'):
        vid = str(ids[0] if isinstance(ids, list) and ids else (ids or ''))
        m = re.search(r'(\d{4,})', vid)
        vid = m.group(1) if m else ''
        if not vid:
            return {'list': []}
        c0 = self._dc.get(vid)
        if c0 and time.time() - c0[0] < DET_TTL:
            return {'list': [c0[1]]}
        page_u = '%s/video/%s/x' % (self.base, vid)
        h = self._get(page_u, timeout=18)
        if not h:
            return {'list': [self._mk_min(vid)]}
        d = {'vod_id': vid, 'vod_name': '', 'vod_pic': '', 'vod_year': '', 'vod_area': '', 'vod_class': '',
             'vod_director': '', 'vod_actor': '', 'vod_content': '', 'vod_remarks': '',
             'vod_play_from': '', 'vod_play_url': ''}
        nm = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        if nm:
            d['vod_name'] = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', nm.group(1))).strip()[:120]
        if not d['vod_name']:
            m2 = re.search(r'property="og:title"\s+content="([^"]+)"', h)
            if m2:
                d['vod_name'] = re.sub(r'\s*-\s*5XSQ\.COM\s*$', '', m2.group(1)).strip()[:120]
        pic = re.search(r'property="og:image"\s+content="([^"]+)"', h)
        d['vod_pic'] = self._pic(pic.group(1)) if pic else ''
        if not d['vod_pic']:
            d['vod_pic'] = 'https://imgos.cctvm.xyz/media/videos/tmb5/%s/1.jpg' % vid
        dsc = re.search(r'property="og:description"\s+content="([^"]*)"', h)
        if dsc:
            d['vod_content'] = re.sub(r'\s+', ' ', dsc.group(1)).strip()[:600]
        dur = re.search(r'class="item duration">.*?(\d{1,3}:\d{2}(?::\d{2})?)', h, re.S)
        cidx = h.find('categories-row')
        cblk = h[cidx:cidx + 3000] if cidx > 0 else ''
        cats = re.findall(r'<a href="/videos/[^"]*"[^>]*title="([^"]+)"', cblk)
        if not cats:
            cats = re.findall(r'<span>([^<]{2,16})</span>', cblk)
        cats = [self._un(re.sub(r'\s+', ' ', c)).strip() for c in cats if c]
        cats = [c for c in cats if 1 < len(c) < 16]
        d['vod_class'] = ','.join(cats[:4])
        d['vod_remarks'] = (' '.join(x for x in [(dur.group(1) if dur else ''), cats[0] if cats else ''] if x))[:40]
        mu = self._pick_m3u8(h)
        if mu:
            self._mu[vid] = mu
        froms, urls = ['5X直连'], ['%s$%s' % ('正片', page_u)]
        if mu:
            froms.append('5X备用直链')
            urls.append('%s$%s' % ('正片', mu))
        if PROBE and len(froms) > 1:
            froms, urls = self._probe_lines(froms, urls)
        d['vod_play_from'] = '$$$'.join(froms)
        d['vod_play_url'] = '$$$'.join(urls)
        for k in ('vod_name', 'vod_content', 'vod_remarks', 'vod_class'):
            d[k] = self._un(d[k])
        self._dc[vid] = (time.time(), d)
        if len(self._dc) > 60:
            for k in list(self._dc)[:20]:
                self._dc.pop(k, None)
        return {'list': [d]}

    # ★必检③(方法级) 详情页抖动兜底：CDN 无签名直链可推导，名称封面从列表缓存回捞
    def _cdn_m3u8(self, vid):
        return '%s/url/%s/index.m3u8' % (CDN, str(vid))

    def _cache_find(self, vid):
        pat = '/video/%s/' % str(vid)
        for v in list(self._gc.values()):
            h = v[1] if isinstance(v, tuple) and len(v) > 1 else ''
            i = h.find(pat)
            if i < 0:
                continue
            blk = h[max(0, i - 400):i + 800]
            nm = re.search(r'alt="([^"]{2,200})"', blk) or re.search(r'title="([^"]{2,200})"', blk)
            pic = re.search(r'<img src="([^"]+)"', blk) or re.search(r'(https?://[^"\s]+\.(?:jpg|jpeg|png|webp))', blk)
            return (self._un(re.sub(r'\s+', ' ', nm.group(1)).strip())[:120] if nm else '',
                    self._pic(pic.group(1)) if pic else '')
        return ('', '')

    def _mk_min(self, vid):
        nm, pic = self._cache_find(vid)
        mu = self._cdn_m3u8(vid)
        return {'vod_id': str(vid), 'vod_name': nm or ('视频 %s' % vid),
                'vod_pic': pic or ('https://imgos.cctvm.xyz/media/videos/tmb5/%s/1.jpg' % vid),
                'vod_year': '', 'vod_area': '', 'vod_class': '', 'vod_director': '', 'vod_actor': '',
                'vod_content': '', 'vod_remarks': '直链',
                'vod_play_from': '5X直连', 'vod_play_url': '正片$%s' % mu}

    def _pick_m3u8(self, h):
        h = h or ''
        m = re.search(r'property="og:video:url"\s+content="([^"]+)"', h)
        if m and '.m3u8' in m.group(1):
            return m.group(1)
        m = re.search(r'content="(https?://[^"]+\.m3u8[^"]*)"', h)
        if m:
            return m.group(1)
        m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', h)
        return m.group(1) if m else ''

    # ★必加③(方法级) 关键词 quote + 搜索四件
    def searchContent(self, key, quick=False, pg='1'):
        try:
            pn = max(int(str(pg)), 1)
        except Exception:
            pn = 1
        kw = quote(str(key or '').strip(), safe='')
        if not kw:
            return {'page': pn, 'pagecount': 1, 'limit': PAGE_SIZE, 'total': 0, 'list': []}
        u = '%s/search/videos/%s/' % (self.base, kw)
        if pn > 1:
            u += '?page=%d' % pn
        h = self._get(u)
        items = self._items(h) if h else []
        pc = self._pagecount(h, pn) if h else 1
        return {'page': pn, 'pagecount': pc, 'limit': PAGE_SIZE, 'total': max(pc * PAGE_SIZE, len(items)), 'list': items}

    # ★必检③(方法级) PNG马甲剥壳代理，只回 parse/url/header
    def playerContent(self, flag, id, vipFlags=None):
        u = str(id or flag or '')
        if '$' in u:
            u = u.split('$', 1)[-1]
        mu = ''
        if '.m3u8' in u:
            code, body, ct = self._bget(u, 15)
            if code == 200 and b'#EXTM3U' in (body or b''):
                mu = u
        if not mu and u.startswith('http') and '.m3u8' not in u:
            h = self._get(u)
            mu = self._pick_m3u8(h) if h else ''
        if not mu:
            m2 = re.search(r'(\d{4,})', u)
            vid = m2.group(1) if m2 else ''
            mu = self._mu.get(vid, '')
            if not mu and vid:
                mu = self._pick_m3u8(self._get('%s/video/%s/x' % (self.base, vid)))
                if mu:
                    self._mu[vid] = mu
        if not mu:
            m3 = re.search(r'(\d{4,})', u)
            vid3 = m3.group(1) if m3 else ''
            if vid3:
                cand = self._cdn_m3u8(vid3)
                code3, body3, _ct3 = self._bget(cand, 12)
                if code3 == 200 and b'#EXTM3U' in (body3 or b''):
                    mu = cand
                    self._mu[vid3] = mu
        if not mu:
            return {'parse': 1, 'url': u}
        hd = dict(self._hd())
        p = self._srv_start()
        if p:
            return {'parse': 0, 'url': 'http://127.0.0.1:%d/m3u8?u=%s' % (p, quote(mu, safe='')), 'header': dict(hd), 'headers': dict(hd)}
        return {'parse': 0, 'url': 'proxy://do=py&type=m3u8&url=' + quote(mu, safe=''), 'header': dict(hd), 'headers': dict(hd)}

    def _srv_start(self):
        with self._lock:
            if self._srv and self._port:
                return self._port
            for p in range(9978, 9999):
                try:
                    srv = http.server.ThreadingHTTPServer(('127.0.0.1', p), self._mk_h())
                    srv.daemon_threads = True
                    threading.Thread(target=srv.serve_forever, daemon=True).start()
                    self._srv, self._port = srv, p
                    return p
                except Exception:
                    continue
            return 0

    def _mk_h(self):
        sp = self

        class _Proxy(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *a):
                pass

            def do_GET(self):
                try:
                    sp._serve(self)
                except Exception:
                    pass

            def do_HEAD(self):
                try:
                    sp._serve(self)
                except Exception:
                    pass

        return _Proxy

    def _serve(self, h):
        from urllib.parse import urlparse, parse_qs
        q = urlparse(h.path)
        u = (parse_qs(q.query).get('u') or [''])[0]
        if not u or not u.startswith('http'):
            return self._send(h, 404, b'', 'text/plain')
        if q.path.rstrip('/').endswith('m3u8'):
            code, body, ct = self._rw_raw(u)
        else:
            code, body, ct = self._seg_raw(u)
        self._send(h, code, body, ct)

    def _send(self, h, code, body, ct):
        try:
            if isinstance(body, str):
                body = body.encode('utf-8')
            n = len(body)
            st, en = 0, n - 1
            rng = h.headers.get('Range') or ''
            if rng and code == 200:
                m = re.match(r'bytes=(\d+)-(\d*)', rng)
                if m:
                    st = int(m.group(1))
                    en = int(m.group(2)) if m.group(2) else n - 1
                    if st <= en < n:
                        body = body[st:en + 1]
                        code = 206
            h.send_response(code)
            h.send_header('Content-Type', ct)
            h.send_header('Accept-Ranges', 'bytes')
            h.send_header('Content-Length', str(len(body)))
            if code == 206:
                h.send_header('Content-Range', 'bytes %d-%d/%d' % (st, st + len(body) - 1, n))
            h.send_header('Connection', 'close')
            h.end_headers()
            if h.command != 'HEAD':
                h.wfile.write(body)
        except Exception:
            pass

    def _pu(self, u, t):
        if self._port:
            return 'http://127.0.0.1:%d/%s?u=%s' % (self._port, t, quote(u, safe=''))
        return 'proxy://do=py&type=%s&url=%s' % (t, quote(u, safe=''))

    def _rw_raw(self, u):
        code, body, ct = self._bget(u, 20)
        if code != 200 or not body:
            return 404, b'', 'text/plain'
        try:
            txt = body.decode('utf-8', 'ignore')
        except Exception:
            txt = ''
        if '#EXTM3U' not in txt:
            return code, body, ct or 'text/plain'
        base = u.rsplit('/', 1)[0] + '/'
        out = []
        for ln in txt.splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith('#EXT-X-KEY'):
                m = re.search(r'URI="([^"]+)"', s)
                if m:
                    ku = urljoin(base, m.group(1))
                    s = s.replace('URI="%s"' % m.group(1), 'URI="%s"' % self._pu(ku, 'seg'))
            elif not s.startswith('#'):
                fu = s if s.startswith('http') else urljoin(base, s)
                s = self._pu(fu, 'seg')
            out.append(s)
        return 200, '\n'.join(out).encode('utf-8'), 'application/vnd.apple.mpegurl'

    # ★必检③(方法级) 动态定位 TS 同步字节(0x47 x188 对齐)剥 PNG 头
    def _strip(self, b):
        n = len(b)
        lim = min(n - 376, 16384)
        for i in range(max(lim, 0)):
            if b[i] == 0x47 and b[i + 188] == 0x47 and b[i + 376] == 0x47:
                return b[i:]
        return b

    def _seg_raw(self, u):
        code, body, ct = self._bget(u, 25)
        if code != 200 or not body:
            return code or 404, b'', 'text/plain'
        if body[:4] == b'\x89PNG' or 'image' in str(ct or ''):
            body = self._strip(body)
            ct = 'video/mp2t'
        if 'mpegurl' in str(ct or ''):
            return 200, body, 'application/vnd.apple.mpegurl'
        return 200, body, ct or 'video/mp2t'

    def localProxy(self, param):
        p, t = '', 'm3u8'
        if isinstance(param, dict):
            p = str(param.get('url') or param.get('u') or '')
            t = str(param.get('type') or param.get('t') or 'm3u8')
        else:
            s = str(param or '')
            m = re.search(r'(?:^|[?&])(?:type|t)=([A-Za-z0-9_]+)', s)
            if m:
                t = m.group(1)
            m = re.search(r'(?:^|[?&])(?:url|u)=(.+)$', s)
            p = m.group(1) if m else (s if s.startswith('http') else '')
        p = unquote(p) if '%' in p else p
        if not p.startswith('http'):
            return [404, 'text/plain', '']
        if t == 'seg':
            code, body, ct = self._seg_raw(p)
        elif t == 'img':
            code, body, ct = self._img_raw(p)
        else:
            code, body, ct = self._rw_raw(p)
        res = {'code': code, 'content': body, 'headers': {'Content-Type': ct}}
        if LP_MODE == 'dict':
            return res
        if LP_MODE == 'tuple':
            return (code, {'Content-Type': ct}, body)
        return [code, ct, body]

    def _img_raw(self, u):
        try:
            r = requests.get(u, headers={'User-Agent': self.ua, 'Referer': PIC_REFERER or self.ref}, timeout=15)
            return 200, r.content, r.headers.get('Content-Type', 'image/jpeg')
        except Exception:
            return 404, b'', 'text/plain'

    # ★必加①(方法级) 首页走 RSS 快路径 3KB/0.7s，失败回退 /videos 列表页
    def _rss_items(self):
        h = self._get(self.base + '/rss/', timeout=8)
        if not h or '<item>' not in h:
            return []
        out, seen = [], set()
        for b in re.findall(r'<item>(.*?)</item>', h, re.S)[:30]:
            mk = re.search(r'/video/(\d+)', b)
            if not mk:
                continue
            vid = mk.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            mt = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', b, re.S)
            nm = re.sub(r'\s+', ' ', (mt.group(1) if mt else '')).strip()
            note = ''
            mc = re.match(r'\[([^\]]+)\]\s*(.*)', nm)
            if mc:
                note = mc.group(1).strip()
                nm = mc.group(2).strip()
            mp = re.search(r'(https?://[^"\'<>\s]+\.(?:jpg|jpeg|png|webp))', b)
            out.append(self._cw({'vod_id': vid,
                                 'vod_name': self._un(nm)[:80],
                                 'vod_pic': self._pic(mp.group(1)) if mp else 'https://imgos.cctvm.xyz/media/videos/tmb5/%s/1.jpg' % vid,
                                 'vod_remarks': self._un(note)}))
        return out

    def _items(self, h):
        out, seen = [], set()
        for b in (h or '').split('<div class="thumb">')[1:]:
            m = re.search(r'href="/video/(\d+)/[^"]*"', b)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            nm = re.search(r'alt="([^"]*)"', b) or re.search(r'title="([^"]*)"', b)
            pic = re.search(r'<img src="([^"]+)"', b)
            dur = re.search(r'<span class="duration">(\d{1,3}:\d{2}(?::\d{2})?)</span>', b)
            ctg = re.search(r'icon-channel"></i>([^<]+)</a>', b)
            note = self._un(' '.join(x for x in [(ctg.group(1).strip() if ctg else ''), (dur.group(1) if dur else '')] if x))
            out.append(self._cw({'vod_id': vid,
                                 'vod_name': self._un(re.sub(r'\s+', ' ', nm.group(1)).strip())[:80] if nm else '',
                                 'vod_pic': self._pic(pic.group(1)) if pic else 'https://imgos.cctvm.xyz/media/videos/tmb5/%s/1.jpg' % vid,
                                 'vod_remarks': note}))
        return out

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(?:' + VIDEO_EXTS + r')(?:\?|$)', str(url or ''), re.I))

    def manualVideoCheck(self):
        return False

    def getDependence(self):
        return []

    def destroy(self):
        try:
            if self._srv:
                self._srv.shutdown()
                self._srv.server_close()
        except Exception:
            pass
        self._srv = None
        self._port = 0

    def progressVideo(self, speed, time_, end):
        return {}

    def setVideoFlags(self, siteKey, flags):
        try:
            self._siteKey = siteKey or SITE_KEY
            self._vflags = flags or {}
        except Exception:
            pass
