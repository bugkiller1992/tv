// ==UserScript==
// @name         MissAV GMSpider Final Stable
// @namespace    gmspider.missav
// @version      2026.03.15.v3
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

    // 提取高清封面地址
    function extractImgUrl(element) {
        if (!element) return "";

        let imgUrl = "";
        const img = element.tagName === "IMG" ? element : element.querySelector("img");
        
        if (img) {
            const srcset = img.getAttribute("data-srcset") || img.getAttribute("srcset");
            if (srcset) {
                const candidates = srcset.split(",").map(s => s.trim().split(" ")[0]);
                imgUrl = candidates.pop() || "";
            }

            if (!imgUrl || imgUrl.startsWith("data:image")) {
                imgUrl = img.getAttribute("data-src") || 
                         img.getAttribute("data-lazy-src") || 
                         img.getAttribute("data-original") || 
                         img.getAttribute("src") || "";
            }
        }

        if (!imgUrl || imgUrl.startsWith("data:image")) {
            const style = element.getAttribute("style") || "";
            const bgMatch = style.match(/url\(['"]?(.*?)['"]?\)/);
            if (bgMatch && bgMatch[1]) {
                imgUrl = bgMatch[1];
            }
        }

        if (imgUrl.startsWith("data:image")) {
            imgUrl = "";
        }

        if (imgUrl) {
            if (imgUrl.startsWith("//")) {
                imgUrl = "https:" + imgUrl;
            } else if (imgUrl.startsWith("/")) {
                imgUrl = "https://missav.ws" + imgUrl;
            }
        }

        return imgUrl;
    }

    function parseList(html) {
        const doc = new DOMParser().parseFromString(html, "text/html");
        let list = [];

        doc.querySelectorAll("div.thumbnail, a.group, div.my-2").forEach(el => {
            const a = el.tagName === "A" ? el : el.querySelector("a");
            if (!a) return;

            const href = a.getAttribute("href") || a.href || "";
            if (!href || href.startsWith("javascript") || href.includes("/tags/")) return;

            const imgSrc = extractImgUrl(el);
            const imgNode = el.querySelector("img");
            const title = imgNode?.getAttribute("alt") || el.querySelector(".title, h2, h3, a.text-secondary")?.innerText.trim() || "";

            try {
                const url = new URL(href, "https://missav.ws");
                const vodId = url.pathname.replace(/^\/|\/$/g, '').split("/").pop();

                if (vodId && !list.some(item => item.vod_id === vodId)) {
                    list.push({
                        vod_id: vodId,
                        vod_name: title,
                        vod_pic: imgSrc,
                        vod_remarks: el.querySelector(".duration, .bg-gray-800, .absolute.bottom-1")?.innerText.trim() || ""
                    });
                }
            } catch (e) {
                // 忽略非合法 URL
            }
        });

        return list;
    }

    function parsePageCount(doc) {
        let maxPage = 1;
        doc.querySelectorAll("a.page-link, nav a, .pagination a").forEach(el => {
            const num = parseInt(el.innerText.trim());
            if (!isNaN(num) && num > maxPage) {
                maxPage = num;
            }
        });
        return maxPage;
    }

    const MissAV = {

        // 补全主页的分类导航与默认影片列表
        async homeContent(pg = 1) {
            const url = `https://missav.ws/cn/new?page=${pg}`;
            const html = await fetchHtml(url);
            const doc = new DOMParser().parseFromString(html, "text/html");

            return {
                class: [
                    { type_id: "new", type_name: "最新上市" },
                    { type_id: "release", type_name: "新作发布" },
                    { type_id: "chinese-subtitle", type_name: "中文字幕" },
                    { type_id: "uncensored-leak", type_name: "无码破解" },
                    { type_id: "uncensored", type_name: "无码流出" },
                    { type_id: "amateur", type_name: "素人" },
                    { type_id: "today-hot", type_name: "今日热门" },
                    { type_id: "weekly-hot", type_name: "本周热门" },
                    { type_id: "monthly-hot", type_name: "本月热门" }
                ],
                list: parseList(html),
                pagecount: parsePageCount(doc) || 999
            };
        },

        async categoryContent(tid, pg = 1) {
            let path = tid;
            if (tid === "today-hot") path = "today-hot";
            else if (tid === "weekly-hot") path = "weekly-hot";
            else if (tid === "monthly-hot") path = "monthly-hot";

            let url = `https://missav.ws/cn/${path}?page=${pg}`;
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
            const pageUrl = targetId.startsWith("http") ? targetId : `https://missav.ws/cn/${targetId}`;
            const html = await fetchHtml(pageUrl);

            const doc = new DOMParser().parseFromString(html, "text/html");

            let title = doc.querySelector("h1")?.innerText.trim() || "";
            let pic = doc.querySelector("video")?.getAttribute("poster") || 
                      doc.querySelector("meta[property='og:image']")?.content || "";

            if (pic) {
                if (pic.startsWith("//")) pic = "https:" + pic;
                else if (pic.startsWith("/")) pic = "https://missav.ws" + pic;
            }

            let playList = [];

            // 1. 深度匹配 M3U8 直链接（涵盖各种 CDN pattern）
            const m3u8Matches = html.match(/https?:\/\/[^'"]+\.m3u8[^'"]*/g);
            if (m3u8Matches && m3u8Matches.length > 0) {
                // 去重
                const uniqueUrls = [...new Set(m3u8Matches)];
                uniqueUrls.forEach((mUrl, index) => {
                    playList.push({
                        from: `线路 ${index + 1} (直连)`,
                        media: [{
                            name: title,
                            type: "m3u8",
                            ext: {
                                url: mUrl,
                                header: {
                                    "User-Agent": navigator.userAgent,
                                    "Referer": "https://missav.ws/"
                                }
                            }
                        }]
                    });
                });
            }

            // 2. 尝试从 video 节点解析
            if (playList.length === 0) {
                doc.querySelectorAll("video source, video").forEach((v, i) => {
                    const videoSrc = v.src || v.getAttribute("src");
                    if (videoSrc) {
                        playList.push({
                            from: `线路 ${i + 1}`,
                            media: [{
                                name: title,
                                type: videoSrc.includes(".m3u8") ? "m3u8" : "webview",
                                ext: {
                                    url: videoSrc,
                                    header: {
                                        "Referer": "https://missav.ws/"
                                    }
                                }
                            }]
                        });
                    }
                });
            }

            // 3. Webview 兜底（加载完整网页）
            if (playList.length === 0) {
                playList.push({
                    from: "网页播放 (Webview)",
                    media: [{
                        name: title,
                        type: "webview",
                        ext: {
                            url: pageUrl
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
