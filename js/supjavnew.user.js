// ==UserScript==
// @name         Supjav (TVBox Node Optimized)
// @namespace    gmspider
// @version      2026.10.06
// @description  Supjav GMSpider For TVBox / Google TV
// @author       Luomo
// @match        https://supjav.com/*
// @require      https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.slim.min.js
// @grant        GM_cookie
// @grant        GM_xmlhttpRequest
// @grant        unsafeWindow
// ==/UserScript==

console.log(JSON.stringify(GM_info));
(function () {
    const GMSpiderArgs = {};
    if (typeof GmSpiderInject !== 'undefined') {
        let args = JSON.parse(GmSpiderInject.GetSpiderArgs());
        GMSpiderArgs.fName = args.shift();
        GMSpiderArgs.fArgs = args;
    } else {
        GMSpiderArgs.fName = "homeContent";
        GMSpiderArgs.fArgs = ["tag"];
    }
    Object.freeze(GMSpiderArgs);

    const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";
    const HOST = 'https://supjav.com';
    const PROXY_BASE = 'https://py.fzcrym.link:1314';
    const STREAM_API = PROXY_BASE + '/stream?u=';
    const SJ_HLS_API = PROXY_BASE + '/sj_hls?u=';
    const LK_BASE = 'https://lk1.supremejav.com/supjav.php';

    // 解包器 (Packer) 还原逻辑
    function unpack(text) {
        const m = text.match(/}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\Vert{}'\)/);
        if (!m) return '';
        let [_, payload, baseStr, countStr, keysStr] = m;
        let base = parseInt(baseStr), count = parseInt(countStr), keys = keysStr.split('|');
        const digits = '0123456789abcdefghijklmnopqrstuvwxyz';

        function enc(num) {
            let out = '';
            while (num > 0) {
                out = digits[num % base] + out;
                num = Math.floor(num / base);
            }
            return out || '0';
        }

        const table = {};
        for (let i = 0; i < count; i++) {
            if (i < keys.length && keys[i]) table[enc(i)] = keys[i];
        }
        return payload.replace(/\b\w+\b/g, (match) => table[match] || match);
    }

    // VOE 加密数据还原
    function voeDecode(html) {
        const m = html.match(/<script[^>]*type=["']application\/json["'][^>]*>(.*?)<\/script>/s);
        if (!m) return {};
        let raw = m[1].trim();
        try {
            let j = JSON.parse(raw);
            if (Array.isArray(j) && j.length > 0) raw = j[0];
        } catch (e) {}

        let s = String(raw);
        ['@$', '^^', '~@', '%?', '*~', '!!', '#&'].forEach(k => { s = s.split(k).join('_'); });
        s = s.split('_').join('');

        function b64d(x) {
            x = x.replace(/[^A-Za-z0-9+/=]/g, '');
            x += '='.repeat((4 - x.length % 4) % 4);
            return window.atob(x);
        }

        try {
            // ROT13
            let rot = s.replace(/[a-zA-Z]/g, c => {
                return String.fromCharCode((c <= 'Z' ? 90 : 122) >= (c = c.charCodeAt(0) + 13) ? c : c - 26);
            });
            let t1 = b64d(rot);
            let t2 = '';
            for (let i = 0; i < t1.length; i++) {
                t2 += String.fromCharCode(t1.charCodeAt(i) - 3);
            }
            let t3 = b64d(t2.split('').reverse().join(''));
            return JSON.parse(t3);
        } catch (e) {
            return {};
        }
    }

    // 同步/异步 HTTP 请求包装
    function httpRequest(url, referer) {
        return new Promise((resolve) => {
            if (typeof GM_xmlhttpRequest !== 'undefined') {
                GM_xmlhttpRequest({
                    method: 'GET',
                    url: url,
                    headers: { 'User-Agent': UA, 'Referer': referer || HOST + '/' },
                    onload: (res) => resolve(res.responseText || ''),
                    onerror: () => resolve('')
                });
            } else {
                $.ajax({
                    url: url,
                    type: 'GET',
                    headers: { 'Referer': referer || HOST + '/' },
                    success: (data) => resolve(data),
                    error: () => resolve('')
                });
            }
        });
    }

    async function extractStream(s2, ref) {
        if (!s2) return { m3u8: '', direct: '' };

        // 1. 直取 M3U8
        let hits = s2.match(/https?:\/\/[^\s"'<>\\]+?\.m3u8[^\s"'<>\\]*/g);
        if (hits && hits.length > 0) return { m3u8: hits[0].replace(/\\/g, ''), direct: '' };

        // 2. Packer
        if (s2.includes('eval(function(p,a,c,k,e')) {
            let dec = unpack(s2);
            let dhits = dec.match(/https?:\/\/[^\s"'<>\\]+?\.m3u8[^\s"'<>\\]*/g);
            if (dhits && dhits.length > 0) return { m3u8: dhits[0].replace(/\\/g, ''), direct: '' };
        }

        // 3. Iframe 嵌套处理
        let iframes = [...s2.matchAll(/<iframe[^>]+src=["']([^"']+)["']/gi)];
        for (let ifr of iframes) {
            let src = ifr[1];
            if (src.startsWith('//')) src = 'https:' + src;
            if (src.startsWith('http')) {
                let iframeHtml = await httpRequest(STREAM_API + encodeURIComponent(src) + '&r=' + encodeURIComponent(ref));
                let res = await extractStream(iframeHtml, src);
                if (res.m3u8 || res.direct) return res;
            }
        }

        // 4. Streamtape
        let em = s2.match(/https?:\/\/streamtape\.com\/e\/([A-Za-z0-9]+)/);
        if (em) {
            let eurl = 'https://streamtape.com/e/' + em[1] + '/';
            let page = await httpRequest(STREAM_API + encodeURIComponent(eurl) + '&r=' + encodeURIComponent(HOST + '/'));
            let mm = page.match(/innerHTML\s*=\s*['"]([^'"]+)['"]\s*\+\s*\(['"]([^'"]+)['"]\)\.substring\((\d+)\)/);
            if (mm) {
                let link = mm[1] + mm[2].substring(parseInt(mm[3]));
                if (link.startsWith('//')) link = 'https:' + link;
                if (!link.includes('dl=')) link += (link.includes('?') ? '&dl=1' : '?dl=1');
                return { m3u8: '', direct: link };
            }
        }

        // 5. VOE
        let tgt = [...s2.matchAll(/window\.location\.href\s*=\s*'([^']+)'/g)].map(x => x[1]);
        if (tgt.length === 0) tgt = [...s2.matchAll(/https?:\/\/[a-z0-9.-]+\/e\/[a-z0-9]{8,}/g)].map(x => x[0]);
        if (tgt.length > 0) {
            let page = await httpRequest(STREAM_API + encodeURIComponent(tgt[0]) + '&r=' + encodeURIComponent(ref));
            let cfg = voeDecode(page);
            let src = String(cfg.source || '');
            if (src.includes('.m3u8')) return { m3u8: src, direct: '' };
            let dau = String(cfg.direct_access_url || '');
            if (dau.startsWith('http')) return { m3u8: '', direct: dau };
            if (src.startsWith('http')) return { m3u8: '', direct: src };
        }

        return { m3u8: '', direct: '' };
    }

    const GmSpider = (function () {
        function listVideos() {
            let itemList = [];
            $(".post").each(function () {
                const $a =$(this).find(".img a, a.img").first();
                const $img =$(this).find("img").first();
                const rawUrl = $a.attr("href") || "";
                if (!rawUrl) return;

                const rawImg = $img.attr("data-original") || $img.attr("data-src") \vert{}\vert{} $img.attr("src") || "";
                let vodId = "";
                try {
                    const urlObj = new URL(rawUrl, window.location.origin);
                    vodId = urlObj.pathname.replace(/^\/|\/$/g, '').split('/').pop();
                } catch(e) {
                    vodId = rawUrl;
                }

                itemList.push({
                    vod_id: vodId,
                    vod_name: $a.attr("title") || $img.attr("alt") \vert{}\vert{} $(this).find("h2").text().trim(),
                    vod_pic: rawImg,
                    vod_remarks: $(this).find(".date").text().trim(),
                    vod_year: $(this).find(".meta").clone().children().remove().end().text().trim()
                });
            });
            return itemList;
        }

        return {
            homeContent: function (filter) {
                const defaultFilter = [{
                    key: "sort",
                    name: "排序",
                    value: [{ n: "最新", v: "" }, { n: "最多观看", v: "views" }]
                }];
                let result = {
                    class: [
                        {type_id: "popular", type_name: "热门"},
                        {type_id: "category/censored-jav", type_name: "有码"},
                        {type_id: "category/uncensored-jav", type_name: "无码"},
                        {type_id: "category/amateur", type_name: "素人"},
                        {type_id: "category/chinese-subtitles", type_name: "中文字幕"},
                        {type_id: "category/reducing-mosaic", type_name: "破解"},
                        {type_id: "category/english-subtitles", type_name: "英字幕"}
                    ],
                    filters: {},
                    list: listVideos()
                };
                result.class.forEach((item) => { result.filters[item.type_id] = defaultFilter; });
                return result;
            },
            categoryContent: function (tid, pg, filter, extend) {
                let result = { list: listVideos(), pagecount: 1 };
                const $lastPage =$(".pagination li").not(".next-page, .next").last();
                if ($lastPage.length > 0) result.pagecount = parseInt($lastPage.text().trim()) || 1;
                return result;
            },
            detailContent: function (ids) {
                let vid = String(ids[0]).replace(/\D/g, '');
                let vodActor = [], tags = [];

                $(".post-meta .cats a").each(function () {
                    tags.push($(this).text().trim());
                });

                const $img =$(".post-meta .img, .post-meta img").first();
                let vodName = $(".post-title, h1").first().text().trim() || vid;
                let rawImgUrl = $img.attr("src") || $img.attr("data-original") \vert{}\vert{} $img.attr("data-src") || "";

                // 获取 SupJav 的核心 data-link (Hex) 播放节点列表
                let vodPlayFrom = [];
                let vodPlayUrl = [];

                const links = [];
                $("[data-link]").each(function () {
                    let lk = $(this).attr("data-link");
                    if (lk && lk.length >= 40) links.push(lk);
                });

                const names = [];
                $("[data-link]").each(function () {
                    let text = $(this).text().trim();
                    if (text && text.length <= 12) names.push(text);
                });

                if (links.length > 0) {
                    links.forEach((lk, idx) => {
                        let name = names[idx] || `线路 ${idx + 1}`;
                        vodPlayFrom.push(name);
                        // 将 vid 和 lk (data-link) 组合传递给 playerContent
                        vodPlayUrl.push(`正片$${vid}|${lk}`);
                    });
                } else {
                    vodPlayFrom.push("SupJav");
                    vodPlayUrl.push(`正片$${vid}|`);
                }

                return {
                    list: [{
                        vod_id: vid,
                        vod_name: vodName,
                        vod_pic: rawImgUrl,
                        vod_remarks: tags.join(" "),
                        vod_content: vodName,
                        vod_play_from: vodPlayFrom.join("$$$"),                         vod_play_url: vodPlayUrl.join("$$$")
                    }]
                };
            },
            playerContent: async function (flag, id, vipFlags) {
                // 彻底抛弃 Webview 渲染，改用纯 API 异步解密，输出原生直链
                let [vid, lk] = String(id).split('|');
                if (!lk) return { parse: 0, url: '' };

                let detailUrl = HOST + '/' + vid + '.html';
                let s1_url = LK_BASE + '?l=' + lk;
                let s1 = await httpRequest(STREAM_API + encodeURIComponent(s1_url) + '&r=' + encodeURIComponent(detailUrl));

                let om = s1.match(/var\s+OLID\s*=\s*'([0-9a-f]{40,})'/);
                let olid = om ? om[1].split('').reverse().join('') : lk.split('').reverse().join('');

                let s2_url = LK_BASE + '?c=' + olid;
                let s2 = await httpRequest(STREAM_API + encodeURIComponent(s2_url) + '&r=' + encodeURIComponent(s1_url));

                let stream = await extractStream(s2, s1_url);
                if (!stream.m3u8 && !stream.direct) return { parse: 0, url: '' };

                if (stream.direct) {
                    return {
                        parse: 0,
                        url: stream.direct,
                        header: { 'User-Agent': UA, 'Referer': HOST + '/' }
                    };
                }

                let m3u8 = stream.m3u8.replace(/\\/g, '');
                let playUrl = '';

                // 区分并使用代理接口透传，防止 ExoPlayer 403 / 无法识别 PNG 视频头
                if (m3u8.toLowerCase().includes('turboviplay') || m3u8.toLowerCase().includes('turbosplayer')) {
                    playUrl = SJ_HLS_API + encodeURIComponent(m3u8);
                } else {
                    playUrl = STREAM_API + encodeURIComponent(m3u8);
                }

                return {
                    parse: 0,
                    url: playUrl,
                    header: {
                        'User-Agent': UA,
                        'Referer': HOST + '/'
                    }
                };
            },
            searchContent: function (key, quick, pg) {
                let result = { list: listVideos(), pagecount: 1 };
                const $lastPage =$(".pagination li").not(".next-page, .next").last();
                if ($lastPage.length > 0) result.pagecount = parseInt($lastPage.text().trim()) || 1;
                return result;
            }
        };
    })();

    $(document).ready(function () {
        if ($(".loading-verifying").length > 0 && typeof GmSpiderInject !== 'undefined') {
            GmSpiderInject.ShowWebview();
        }
    });

    $(unsafeWindow).on("load", async function () {
        let result = GmSpider[GMSpiderArgs.fName](...GMSpiderArgs.fArgs);
        if (result instanceof Promise) {
            result = await result;
        }
        console.log(result);
        if (typeof GmSpiderInject !== 'undefined') {
            GmSpiderInject.HideWebview();
            GmSpiderInject.SetSpiderResult(JSON.stringify(result));
        }
    });
})();
