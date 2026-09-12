// ==UserScript==
// @name         MissAV GMSpider Final Stable
// @namespace    gmspider.missav
// @version      2026.final
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

        doc.querySelectorAll("a.group").forEach(el => {

            const href = el.href;
            const img = el.querySelector("img")?.src || "";
            const title = el.querySelector("img")?.alt || "";

            if (!href) return;

            const url = new URL(href);

            list.push({
                vod_id: url.pathname.split("/").pop(),
                vod_name: title,
                vod_pic: img,
                vod_remarks: ""
            });
        });

        return list;
    }

    const MissAV = {

        async homeContent(pg = 1) {
            const url = `https://missav.ws/cn?page=${pg}`;
            const html = await fetchHtml(url);

            return {
                list: parseList(html),
                pagecount: 999
            };
        },

        async categoryContent(tid, pg = 1) {

            let url = `https://missav.ws/cn/${tid}?page=${pg}`;

            const html = await fetchHtml(url);

            return {
                list: parseList(html),
                pagecount: 999
            };
        },

        async searchContent(key, pg = 1) {

            let url = `https://missav.ws/cn/search/${key}?page=${pg}`;

            const html = await fetchHtml(url);

            return {
                list: parseList(html),
                pagecount: 999
            };
        },

        async detailContent(ids) {

            const url = `https://missav.ws/cn/${ids[0]}`;
            const html = await fetchHtml(url);

            const doc = new DOMParser().parseFromString(html, "text/html");

            let title = doc.querySelector("h1")?.innerText || "";

            let playList = [];

            doc.querySelectorAll("video source").forEach((v, i) => {
                playList.push({
                    from: "default",
                    media: [{
                        name: title,
                        type: "webview",
                        ext: {
                            url: v.src,
                            link: i
                        }
                    }]
                });
            });

            return {
                list: [{
                    vod_id: ids[0],
                    vod_name: title,
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
