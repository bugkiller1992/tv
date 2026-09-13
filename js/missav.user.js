// ==UserScript==
// @name         MissAV GMSpider Final Stable
// @namespace    gmspider.missav
// @version      2026.03.15
// @match        https://missav.ws/*
// @grant        GM_xmlhttpRequest
// @grant        unsafeWindow
// ==/UserScript==

(function () {

    const GMSpiderArgs = {};

    if (typeof GmSpiderInject !== "undefined") {
        let args = JSON.parse(GmSpiderInject.GetSpiderArgs());
        GMSpiderArgs.fName = args.shift();
        GMSpiderArgs.fArgs = args;
    } else {
        GMSpiderArgs.fName = "homeContent";
        GMSpiderArgs.fArgs = [];
    }

    function fetchHtml(url) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: "GET",
                url: url,
                onload: res => resolve(res.responseText),
                onerror: err => reject(err)
            });
        });
    }

    function parseList(html) {
        const doc = new DOMParser().parseFromString(html, "text/html");
        let list = [];

        // MissAV 常用链接为选择器 a 或包含图片/卡片的容器
        doc.querySelectorAll("div.thumbnail, a.group, div.my-2").forEach(el => {
            const a = el.tagName === "A" ? el : el.querySelector("a");
            if (!a) return;

            const href = a.getAttribute("href") || a.href || "";
            if (!href || href.startsWith("javascript")) return;

            const img = el.querySelector("img");
            // 优先读取 data-src / data-srcset 防止懒加载导致图片为空
            let imgSrc = img ? (img.getAttribute("data-src") || img.getAttribute("src") || "") : "";
            if (imgSrc.includes("data:image")) {
                imgSrc = img.getAttribute("data-src") || "";
            }

            const title = img?.getAttribute("alt") || el.querySelector(".title, h2, h3")?.innerText.trim() || "";

            try {
                const url = new URL(href, "https://missav.ws");
                const vodId = url.pathname.replace(/^\/|\/$/g, '').split("/").pop();

                if (vodId && !list.some(item => item.vod_id === vodId)) {
                    list.push({
                        vod_id: vodId,
                        vod_name: title,
                        vod_pic: imgSrc,
                        vod_remarks: el.querySelector(".duration, .bg-gray-800")?.innerText.trim() || ""
                    });
                }
            } catch (e) {
                // 忽略解析失败的 URL
            }
        });

        return list;
    }

    function parsePageCount(doc) {
        let maxPage = 1;
        doc.querySelectorAll("a.page-link, nav a").forEach(el => {
            const num = parseInt(el.innerText.trim());
            if (!isNaN(num) && num > maxPage) {
                maxPage = num;
            }
        });
        return maxPage;
    }

    const MissAV = {

        async homeContent(pg = 1) {
            const url = `https://missav.ws/cn?page=${pg}`;
            const html = await fetchHtml(url);
            const doc = new DOMParser().parseFromString(html, "text/html");

            return {
                list: parseList(html),
                pagecount: parsePageCount(doc) || 999
            };
        },

        async categoryContent(tid, pg = 1) {
            let url = `https://missav.ws/cn/${tid}?page=${pg}`;
            const html = await fetchHtml(url);
            const doc = new DOMParser().parseFromString(html, "text/html");

            return {
                list: parseList(html),
                pagecount: parsePageCount(doc) || 999
            };
        },

        async searchContent(key, pg = 1) {
            let url = `https://missav.ws/cn/search/${encodeURIComponent(key)}?page=${pg}`;
            const html = await fetchHtml(url);
            const doc = new DOMParser().parseFromString(html, "text/html");

            return {
                list: parseList(html),
                pagecount: parsePageCount(doc) || 999
            };
        },

        async detailContent(ids) {
            const targetId = ids[0];
            const url = `https://missav.ws/cn/${targetId}`;
            const html = await fetchHtml(url);

            const doc = new DOMParser().parseFromString(html, "text/html");

            let title = doc.querySelector("h1")?.innerText.trim() || "";
            let pic = doc.querySelector("video")?.getAttribute("poster") || doc.querySelector("meta[property='og:image']")?.content || "";

            let playList = [];

            // 1. 尝试使用正则直接寻找 JS 动态加载的 .m3u8 播放地址
            const m3u8Match = html.match(/https?:\/\/[^'"]+\.m3u8[^'"]*/);
            if (m3u8Match) {
                playList.push({
                    from: "MissAV Direct",
                    media: [{
                        name: title,
                        type: "m3u8",
                        ext: {
                            url: m3u8Match[0]
                        }
                    }]
                });
            }

            // 2. 传统 video 节点提取回退方案
            doc.querySelectorAll("video source, video").forEach((v, i) => {
                const videoSrc = v.src || v.getAttribute("src");
                if (videoSrc) {
                    playList.push({
                        from: `Server ${i + 1}`,
                        media: [{
                            name: title,
                            type: videoSrc.includes(".m3u8") ? "m3u8" : "webview",
                            ext: {
                                url: videoSrc,
                                link: i
                            }
                        }]
                    });
                }
            });

            // 3. 兜底策略：如果未抓取到媒体地址，采用 Webview 页面内加载
            if (playList.length === 0) {
                playList.push({
                    from: "Webview Player",
                    media: [{
                        name: title,
                        type: "webview",
                        ext: {
                            url: url
                        }
                    }]
                });
            }

            return {
                list: [{
                    vod_id: targetId,
                    vod_name: title,
                    vod_pic: pic,
                    vod_play_data: playList
                }]
            };
        }
    };

    function run() {
        const fn = GMSpiderArgs.fName;
        const args = GMSpiderArgs.fArgs;

        let result;

        if (MissAV[fn]) {
            result = MissAV[fn](...args);
        } else {
            result = { list: [] };
        }

        Promise.resolve(result).then(res => {
            if (typeof GmSpiderInject !== "undefined") {
                GmSpiderInject.HideWebview();
                GmSpiderInject.SetSpiderResult(JSON.stringify(res));
            }
        });
    }

    run();

})();
