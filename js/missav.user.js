// ==UserScript==
// @name         MissAV GMSpider Final Stable
// @namespace    gmspider.missav
// @version      2026.03.15.v6
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

    // JS Packer 混淆解包
    function unpackJs(packedCode) {
        try {
            if (!packedCode || !packedCode.includes("eval(function(p,a,c,k,e,d)")) return packedCode;
            const evalFunc = new Function("return " + packedCode.replace(/^eval/, ""));
            return evalFunc() || packedCode;
        } catch (e) {
            return packedCode;
        }
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

            // 1. 番号与标题解析
            let title = doc.querySelector("h1")?.innerText.trim() || targetId;
            let pic = doc.querySelector("video")?.getAttribute("poster") || 
                      doc.querySelector("meta[property='og:image']")?.content || "";

            if (pic) {
                if (pic.startsWith("//")) pic = "https:" + pic;
                else if (pic.startsWith("/")) pic = "https://missav.ws" + pic;
            }

            // 2. 演员提取 (规范超链接，高亮可点击过滤)
            let vodActorList = [];
            doc.querySelectorAll("a[href*='/actresses/']").forEach(a => {
                const name = a.innerText.trim();
                const href = a.getAttribute("href") || "";
                if (name && href) {
                    try {
                        const actId = "actresses/" + new URL(href, "https://missav.ws").pathname.replace(/^\/|\/$/g, '').split("/").pop();
                        const formatted = `[a=cr:{"id":"${actId}","name":"${name}"}/]${name}[/a]`;
                        if (!vodActorList.includes(formatted)) vodActorList.push(formatted);
                    } catch (e) {}
                }
            });

            // 3. 片商 / 制作商 (规范超链接)
            let vodDirectorList = [];
            doc.querySelectorAll("a[href*='/makers/'], a[href*='/studios/']").forEach(a => {
                const name = a.innerText.trim();
                const href = a.getAttribute("href") || "";
                if (name && href) {
                    try {
                        const makerId = new URL(href, "https://missav.ws").pathname.replace(/^\/|\/$/g, '');
                        const formatted = `[a=cr:{"id":"${makerId}","name":"${name}"}/]${name}[/a]`;
                        if (!vodDirectorList.includes(formatted)) vodDirectorList.push(formatted);
                    } catch (e) {}
                }
            });

            // 4. 分类 & 标签
            let categories = [];
            doc.querySelectorAll("a[href*='/genres/']").forEach(a => {
                const txt = a.innerText.trim();
                if (txt && !categories.includes(txt)) categories.push(txt);
            });

            let tags = [];
            doc.querySelectorAll("a[href*='/tags/']").forEach(a => {
                const txt = a.innerText.trim();
                if (txt && !tags.includes(txt)) tags.push("#" + txt);
            });

            // 发行时间
            let releaseDate = "";
            doc.querySelectorAll("div, p, span").forEach(el => {
                if (el.innerText && el.innerText.includes("发行日期:")) {
                    releaseDate = el.innerText.replace("发行日期:", "").trim();
                }
            });

            // 简介
            let description = doc.querySelector("meta[name='description']")?.content || 
                              doc.querySelector(".text-gray-400.line-clamp-4")?.innerText.trim() || title;

            // 5. 播放线路构建 (支持 Direct M3U8 与 WebView 双重透传)
            let playList = [];
            let m3u8Set = new Set();

            // 5.1 从 Script 脚本及 unpack 中抓取 M3U8
            doc.querySelectorAll("script").forEach(scriptNode => {
                let sContent = scriptNode.textContent || "";
                if (sContent.includes("eval(function")) {
                    sContent = unpackJs(sContent);
                }
                const matches = sContent.match(/(https?:\/\/[^\s"'<>\\]+?\.m3u8[^\s"'<>\\]*)/g);
                if (matches) {
                    matches.forEach(m => m3u8Set.add(m.replace(/\\/g, '')));
                }
            });

            // 5.2 全局正则备选匹配
            if (m3u8Set.size === 0) {
                const globalMatches = html.match(/(https?:\/\/[^\s"'<>\\]+?\.m3u8[^\s"'<>\\]*)/g);
                if (globalMatches) {
                    globalMatches.forEach(m => m3u8Set.add(m.replace(/\\/g, '')));
                }
            }

            // 5.3 组装 Direct 线路
            if (m3u8Set.size > 0) {
                let idx = 1;
                m3u8Set.forEach(mUrl => {
                    playList.push({
                        from: `Direct 线路 ${idx++}`,
                        media: [{
                            name: title,
                            type: "m3u8",
                            ext: {
                                url: mUrl,
                                header: {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                                    "Referer": "https://missav.ws/"
                                }
                            }
                        }]
                    });
                });
            }

            // 5.4 WebView 线路强效兜底（保证点击能够正常播放画面）
            playList.push({
                from: "MissAV 站源 (Webview)",
                media: [{
                    name: title,
                    type: "webview",
                    ext: {
                        url: pageUrl
                    }
                }]
            });

            return {
                list: [{
                    vod_id: targetId,
                    vod_name: title,
                    vod_pic: pic,
                    vod_type: categories.join(" / "),
                    vod_actor: vodActorList.join(" "),
                    vod_director: vodDirectorList.join(" "),
                    vod_remarks: tags.length > 0 ? tags.join(" ") : (releaseDate || "MissAV"),
                    vod_year: releaseDate,
                    vod_content: description,
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
