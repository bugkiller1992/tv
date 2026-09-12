// ==UserScript==
// @name         Supjav
// @namespace    gmspider
// @version      2026.04.18.fullfix2
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

        let cf_clearance = null;
        let cf_cookie_loading = false;

        function updateCfClearance(callback) {
            if (cf_cookie_loading) {
                if (typeof callback === "function") callback();
                return;
            }
            cf_cookie_loading = true;
            GM_cookie.list({ name: "cf_clearance" }, function (cookies, error) {
                cf_cookie_loading = false;
                if (!error && cookies && cookies.length > 0) {
                    cf_clearance = cookies[0].value;
                    localStorage.setItem("cf_clearance", cf_clearance);
                    console.log("SupJav: cf_clearance loaded from cookie");
                } else {
                    let cache = localStorage.getItem("cf_clearance");
                    if (cache && cache.length > 0) {
                        cf_clearance = cache;
                        console.log("SupJav: cf_clearance loaded from localStorage");
                    }
                }
                if (typeof callback === "function") callback();
            });
        }

        function isCloudflarePage() {
            const title = ($("title").text() || "").toLowerCase();
            const bodyText = (document.body?.innerText || "");

            return (
                $(".loading-verifying").length > 0 ||
                $("#challenge-running").length > 0 ||
                $("form#challenge-form").length > 0 ||
                $("div.cf-browser-verification").length > 0 ||
                $("iframe[src*='challenges.cloudflare']").length > 0 ||
                title.includes("just a moment") ||
                title.includes("attention required") ||
                bodyText.includes("verify you are human") ||
                bodyText.includes("checking if the site connection is secure") ||
                bodyText.includes("验证您是否是真人") ||
                bodyText.includes("检查站点连接是否安全")
            );
        }

        function formatImgUrl(url) {
            if (!url) return "";
            if (cf_clearance !== null) {
                url = url + "@User-Agent=" + window.navigator.userAgent + "@Cookie=cf_clearance=" + cf_clearance;
            }
            return url;
        }

        function getPageCount() {
            if ($(".pagination li").length > 0) {
                return $(".pagination li").not(".next-page").last().text().trim() || 1;
            }
            return 1;
        }

        function listVideos() {
            let itemList = [];
            $(".post").each(function () {
                const href = $(this).find(".img").attr("href");
                if (!href) return;

                const url = new URL(href);
                const img =
                    $(this).find("img").data("original") ||
                    $(this).find("img").attr("data-original") ||
                    $(this).find("img").attr("src") ||
                    "";

                itemList.push({
                    vod_id: url.pathname.split('/').at(2),
                    vod_name: $(this).find(".img").attr("title") || "",
                    vod_pic: formatImgUrl(img),
                    vod_remarks: $(this).find(".date").text() || "",
                    vod_year: $(this).find(".meta").children().remove().end().text() || ""
                });
            });
            return itemList;
        }

        return {
            homeContent: function () {
                const videoFilter = [{
                    key: "sort",
                    name: "sort",
                    value: [
                        { n: "views", v: "views" },
                        { n: "latest", v: "" }
                    ]
                }];

                // 目录页排序：默认 date，并支持 name / quantity / date / views
                const folderFilter = [{
                    key: "sort",
                    name: "sort",
                    value: [
                        { n: "date", v: "date" },
                        { n: "views", v: "views" },
                        { n: "name", v: "name" },
                        { n: "quantity", v: "quantity" }
                    ]
                }];

                let result = {
                    class: [
                        { type_id: "popular", type_name: "热门" },
                        { type_id: "category/censored-jav", type_name: "有码" },
                        { type_id: "category/uncensored-jav", type_name: "无码" },
                        { type_id: "category/amateur", type_name: "素人" },
                        { type_id: "category/chinese-subtitles", type_name: "中文字幕" },
                        { type_id: "category/reducing-mosaic", type_name: "无码破解" },
                        { type_id: "category/english-subtitles", type_name: "英文字幕" },
                        { type_id: "tag", type_name: "类别" },
                        { type_id: "maker", type_name: "厂牌" },
                        { type_id: "cast", type_name: "演员" }
                    ],
                    filters: {
                        popular: [{
                            key: "sort",
                            name: "time",
                            value: [
                                { n: "month", v: "month" },
                                { n: "week", v: "week" },
                                { n: "today", v: "" }
                            ]
                        }]
                    },
                    list: []
                };

                result.class.forEach((item) => {
                    if (typeof result.filters[item.type_id] === "undefined") {
                        if (["tag", "maker", "cast"].includes(item.type_id)) {
                            result.filters[item.type_id] = folderFilter;
                        } else {
                            result.filters[item.type_id] = videoFilter;
                        }
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

                if (["tag", "maker", "cast"].includes(tid)) {
                    $(".categorys .child").each(function () {
                        const href = $(this).find("a").attr("href");
                        if (!href) return;

                        const url = new URL(href);
                        const text = $(this).text().trim().split("(");

                        const id = url.pathname
                            .replace(/^\/zh\//, "")
                            .replace(/^\/|\/$/g, "");

                        result.list.push({
                            vod_id: id,
                            vod_name: (text[0] || "").trim(),
                            vod_remarks: text[1] ? text[1].replace(")", "").trim() : "",
                            vod_tag: "folder",
                            style: {
                                type: "rect",
                                ratio: 1
                            }
                        });
                    });

                    result.pagecount = getPageCount();
                } else {
                    result.pagecount = getPageCount();
                    result.list = listVideos();
                }

                return result;
            },

            detailContent: function (ids) {
                $("#vserver").click();

                let vodActor = [], tags = [];

                $(".post-meta .cats a").each(function () {
                    const href = $(this).attr("href");
                    if (!href) return;
                    const id = new URL(href).pathname.replace("/zh/", "");
                    const name = $(this).text().trim();
                    vodActor.unshift(`[a=cr:{"id":"${id}","name":"${name}"}/]${name}[/a]`);
                });

                $(".post-meta .tags a").each(function () {
                    const href = $(this).attr("href");
                    if (!href) return;
                    const id = new URL(href).pathname.replace("/zh/", "");
                    const name = $(this).text().trim();
                    tags.push(`[a=cr:{"id":"${id}","name":"${name}"}/]#${name}[/a]`);
                });

                let vodContent = ($(".post-meta .img").attr("alt") || "").trim();
                let vodName = vodContent.replace("[无码破解]", "");
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
                let btnServers;
                if ($(".video-wrap .cd-server").length > 0) {
                    btnServers = $(".video-wrap .cd-server:first .btn-server");
                } else {
                    btnServers = $(".video-wrap .btn-server");
                }

                btnServers.each(function (i) {
                    vodPlayData.push({
                        from: $(this).text().trim(),
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

                return {
                    list: [{
                        vod_id: ids[0],
                        vod_name: vodName,
                        vod_pic: formatImgUrl($(".post-meta .img").attr("src") || ""),
                        vod_actor: vodActor.join(" "),
                        vod_remarks: tags.join(" "),
                        vod_content: vodContent,
                        vod_play_data: vodPlayData
                    }]
                };
            },

            playerContent: function (flag, id, vipFlags) {
                const link = window.location.hash.split("#").at(1);
                const btns = document.querySelectorAll(`.video-wrap .btn-server`);
                if (btns[link]) {
                    btns[link].dispatchEvent(new Event("click"));
                }
                return {
                    type: "match"
                };
            },

            searchContent: function (key, quick, pg) {
                return {
                    list: listVideos(),
                    pagecount: getPageCount()
                };
            },

            updateCfClearance: updateCfClearance,
            isCloudflarePage: isCloudflarePage
        };
    })();

    function showCF() {
        if (typeof GmSpiderInject !== "undefined") {
            GmSpiderInject.ShowWebview();
        }
    }

    $(document).ready(function () {
        if (GmSpider.isCloudflarePage()) {
            showCF();
        }
    });

    $(unsafeWindow).on("load", function () {
        if (GmSpider.isCloudflarePage()) {
            showCF();
            return;
        }

        GmSpider.updateCfClearance(function () {
            if (GmSpider.isCloudflarePage()) {
                showCF();
                return;
            }

            const result = GmSpider[GMSpiderArgs.fName](...GMSpiderArgs.fArgs);
            console.log(result);

            if (typeof GmSpiderInject !== 'undefined') {
                GmSpiderInject.HideWebview();
                GmSpiderInject.SetSpiderResult(JSON.stringify(result));
            }
        });
    });

})();