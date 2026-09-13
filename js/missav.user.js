// ==UserScript==
// @name         MissAV GMSpider Final Stable
// @namespace    gmspider.missav
// @version      2026.03.15.v2
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

    // 严谨的图片 URL 提取函数
    function extractImgUrl(element) {
        if (!element) return "";

        let imgUrl = "";

        // 1. 从 <img> 标签及其各种懒加载属性解析
        const img = element.tagName === "IMG" ? element : element.querySelector("img");
        if (img) {
            // 优先处理 srcset / data-srcset (经常包含完整的高清地址)
            const srcset = img.getAttribute("data-srcset") || img.getAttribute("srcset");
            if (srcset) {
                const candidates = srcset.split(",").map(s => s.trim().split(" ")[0]);
                imgUrl = candidates.pop() || "";
            }

            // 备选各种懒加载属性
            if (!imgUrl || imgUrl.startsWith("data:image")) {
                imgUrl = img.getAttribute("data-src") || 
                         img.getAttribute("data-lazy-src") || 
                         img.getAttribute("data-original") || 
                         img.getAttribute("src") || "";
            }
        }

        // 2. 如果 img 没拿到，尝试从节点的 style (background-image) 中正则获取
        if (!imgUrl || imgUrl.startsWith("data:image")) {
            const style = element.getAttribute("style") || "";
            const bgMatch = style.match(/url\(['"]?(.*?)['"]?\)/);
            if (bgMatch && bgMatch[1]) {
                imgUrl = bgMatch[1];
            }
        }

        // 避免返回占位 Base64
        if (imgUrl.startsWith("data:image")) {
            imgUrl = "";
        }

        // 补全相对路径与协议前缀
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

        // MissAV 卡片容器选择器
        doc.querySelectorAll("div.thumbnail, a.group, div.my-2").forEach(el => {
            const a = el.tagName === "A" ? el : el.querySelector("a");
            if (!a) return;

            const href = a.getAttribute("href") || a.href || "";
            if (!href || href.startsWith("javascript") || href.includes("/tags/")) return;

            // 调用强化后的图片解析方法
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
                // 忽略非法 URL
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
            
            // 详情页封面提取
            let pic = doc.querySelector("video")?.getAttribute("poster") || 
                      doc.querySelector("meta[property='og:image']")?.content || "";

            if (pic) {
                if (pic.startsWith("//")) pic = "https:" + pic;
                else if (pic.startsWith("/")) pic = "https://missav.ws" + pic;
            }

            let playList = [];

            // 1. 正则检索 .m3u8 直链
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

            // 2. 节点回退提取
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

            // 3. Webview 兜底
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
