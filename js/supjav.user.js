// ==UserScript==
// @name         Supjav
// @namespace    gmspider
// @version      2026.03.15
// @description  Supjav GMSpider
// @author       Luomo
// @match        https://supjav.com/*
// @require      https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.slim.min.js
// @grant        GM_cookie
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

    const GmSpider = (function () {
        function listVideos() {
            let itemList = [];
            $(".post").each(function () {
                const $a = $(this).find(".img a, a.img").first();
                const $img = $(this).find("img").first();
                const rawUrl = $a.attr("href") || "";
                
                if (!rawUrl) return;

                // 优先读取 data-original，备选 data-src 或 src
                const rawImg = $img.attr("data-original") || $img.attr("data-src") || $img.attr("src") || "";

                let vodId = "";
                try {
                    const urlObj = new URL(rawUrl, window.location.origin);
                    vodId = urlObj.pathname.replace(/^\/|\/$/g, '').split('/').pop();
                } catch(e) {
                    vodId = rawUrl;
                }

                itemList.push({
                    vod_id: vodId,
                    vod_name: $a.attr("title") || $img.attr("alt") || $(this).find("h2").text().trim(),
                    vod_pic: formatImgUrl(rawImg),
                    vod_remarks: $(this).find(".date").text().trim(),
                    vod_year: $(this).find(".meta").clone().children().remove().end().text().trim()
                });
            });
            return itemList;
        }

        let cf_clearance = null;

        function formatImgUrl(url) {
            if (!url) return "";
            if (cf_clearance === null) {
                GM_cookie.list({name: "cf_clearance"}, function (cookies, error) {
                    if (!error && cookies.length > 0) {
                        cf_clearance = cookies[0].value;
                        localStorage.setItem("cf_clearance", cf_clearance);
                    } else {
                        let cache_cf_clearance = localStorage.getItem("cf_clearance");
                        if (typeof cache_cf_clearance !== "undefined" && cache_cf_clearance !== null && cache_cf_clearance.length > 0) {
                            cf_clearance = cache_cf_clearance;
                        }
                    }
                });
            }
            if (cf_clearance !== null) {
                url = url + "@User-Agent=" + window.navigator.userAgent + "@Cookie=cf_clearance=" + cf_clearance;
            }
            return url;
        }

        return {
            homeContent: function (filter) {
                const defaultFilter = [{
                    key: "sort",
                    name: "排序",
                    value: [
                        { n: "观看数", v: "views" },
                        { n: "更新时间", v: "" }
                    ]
                }];
                let result = {
                    class: [
                        {type_id: "popular", type_name: "热门"},
                        {type_id: "category/censored-jav", type_name: "有码"},
                        {type_id: "category/uncensored-jav", type_name: "无码"},
                        {type_id: "category/amateur", type_name: "素人"},
                        {type_id: "category/chinese-subtitles", type_name: "中文字幕"},
                        {type_id: "category/reducing-mosaic", type_name: "无码破解"},
                        {type_id: "category/english-subtitles", type_name: "英文字幕"},
                        {type_id: "tag", type_name: "类别"},
                    ],
                    filters: {
                        popular: [{
                            key: "sort",
                            name: "时间",
                            value: [
                                { n: "本月热门", v: "month" },
                                { n: "本周热门", v: "week" },
                                { n: "今日热门", v: "" }
                            ]
                        }]
                    },
                    list: []
                };
                result.class.forEach((item) => {
                    if (typeof result.filters[item.type_id] === "undefined") {
                        result.filters[item.type_id] = defaultFilter;
                    }
                });
                result.list = listVideos();
                return result;
            },
            categoryContent: function (tid, pg, filter, extend) {
                let result = {
                    list: [],
                    pagecount: 1
                };
                if (tid === "tag") {
                    $(".categorys .child").each(function () {
                        const $a = $(this).find("a");
                        const href = $a.attr("href");
                        if (!href) return;
                        
                        const urlParts = new URL(href, window.location.origin).pathname.replace(/^\/|\/$/g, '').split('/');
                        const text = $(this).text().trim().split("(");
                        result.list.push({
                            vod_id: urlParts.slice(-2).join('/'),
                            vod_name: text[0].trim(),
                            vod_remarks: (text[1] ? parseInt(text[1]) : 0) + " 部影片",
                            vod_tag: "folder",
                            style: {
                                "type": "rect",
                                "ratio": 1
                            }
                        });
                    });
                    const $lastPage = $(".pagination li").not(".next-page, .next").last();
                    if ($lastPage.length > 0) {
                        result.pagecount = parseInt($lastPage.text().trim()) || 1;
                    }
                } else {
                    const $lastPage = $(".pagination li").not(".next-page, .next").last();
                    if ($lastPage.length > 0) {
                        result.pagecount = parseInt($lastPage.text().trim()) || 1;
                    }
                    result.list = listVideos();
                }
                return result;
            },
            detailContent: function (ids) {
                // 如果存在自动选择线路的按钮，尝试唤醒
                if ($("#vserver").length > 0) $("#vserver").click();

                let vodActor = [], tags = [];
                $(".post-meta .cats a").each(function () {
                    const href = $(this).attr("href");
                    if (!href) return;
                    const id = new URL(href, window.location.origin).pathname.replace("/zh/", "");
                    const name = $(this).text().trim();
                    vodActor.unshift(`[a=cr:{"id":"${id}","name":"${name}"}/]${name}[/a]`);
                });
                $(".post-meta .tags a").each(function () {
                    const href = $(this).attr("href");
                    if (!href) return;
                    const id = new URL(href, window.location.origin).pathname.replace("/zh/", "");
                    const name = $(this).text().trim();
                    tags.push(`[a=cr:{"id":"${id}","name":"${name}"}/]#${name}[/a]`);
                });

                const $img = $(".post-meta .img, .post-meta img").first();
                let vodContent = $img.attr("alt") || $(".post-title, h1").first().text().trim();
                let vodName = vodContent.replace("[无码破解]", '').trim();
                
                let match = vodName.match(/^[\w|-]+/g);
                if (match) {
                    if (match[0].includes("-")) {
                        vodName = match[0];
                    } else {
                        match = vodContent.match(/^[\w]+\s[\w]+/g);
                        if (match) {
                            vodName = match[0].replace(" ", "-");
                        }
                    }
                }

                let vodPlayData = [];
                // 全局获取所有的播放服务器按钮
                const $btnServers = $(".video-wrap .btn-server, .btn-server");

                $btnServers.each(function (i) {
                    const serverName = $(this).text().trim() || `线路 ${i + 1}`;
                    vodPlayData.push({
                        from: serverName,
                        media: [{
                            name: vodName,
                            type: "webview",
                            ext: {
                                replace: {
                                    pathname: ids[0],
                                    link: i
                                }
                            }
                        }]
                    });
                });

                const rawImgUrl = $img.attr("src") || $img.attr("data-original") || $img.attr("data-src") || "";

                return {
                    list: [{
                        vod_id: ids[0],
                        vod_name: vodName,
                        vod_pic: formatImgUrl(rawImgUrl),
                        vod_actor: vodActor.join(" "),
                        vod_remarks: tags.join(" "),
                        vod_content: vodContent,
                        vod_play_data: vodPlayData
                    }]
                };
            },
            playerContent: function (flag, id, vipFlags) {
                // 从 hash 读取选中的服务器按钮 index，并模拟触发点击事件加载 iframe
                const hash = window.location.hash;
                let linkIndex = 0;
                if (hash.includes("#")) {
                    const idx = parseInt(hash.split("#").pop());
                    if (!isNaN(idx)) linkIndex = idx;
                }

                const servers = document.querySelectorAll(`.video-wrap .btn-server, .btn-server`);
                if (servers.length > linkIndex) {
                    servers[linkIndex].dispatchEvent(new Event("click", { bubbles: true }));
                }

                return {
                    type: "match"
                };
            },
            searchContent: function (key, quick, pg) {
                const result = {
                    list: [],
                    pagecount: 1
                };
                result.list = listVideos();
                const $lastPage = $(".pagination li").not(".next-page, .next").last();
                if ($lastPage.length > 0) {
                    result.pagecount = parseInt($lastPage.text().trim()) || 1;
                }
                return result;
            }
        };
    })();

    $(document).ready(function () {
        if ($(".loading-verifying").length > 0 && typeof GmSpiderInject !== 'undefined') {
            GmSpiderInject.ShowWebview();
        }
    });

    $(unsafeWindow).on("load", function () {
        const result = GmSpider[GMSpiderArgs.fName](...GMSpiderArgs.fArgs);
        console.log(result);
        if (typeof GmSpiderInject !== 'undefined') {
            GmSpiderInject.HideWebview();
            GmSpiderInject.SetSpiderResult(JSON.stringify(result));
        }
    });
})();