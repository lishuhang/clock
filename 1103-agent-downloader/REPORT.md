# REPORT — 多平台视频下载实抓报告

> 任务时间: 2026-11-03 (Asia/Hong_Kong) | 执行环境: 香港阿里云沙盒 (Debian 13, Python 3.12.16, yt-dlp 2026.10.26, ffmpeg 7.1.5)
> 任务规则(用户指定): 每平台 1 条、尽可能高清晰度; **失败后最多换方式重试 1 次**, 未探索路径只记录不穷尽; 过程忠实留痕 (worklog.md W009-W021, logs/)
> 本轮范围: 除 Instagram 外的 7 平台 (Instagram 用户已豁免)

## 1. 结果总表

| # | 平台 | 状态 | 文件 | 分辨率 | 时长 | 大小 | 作者 | 方法 |
|---|------|------|------|--------|------|------|------|------|
| 1 | YouTube | ❌ | - | - | - | - | - | 两法用尽, 见§3/§4 |
| 2 | X (推特) | ✅ | `x_1806444569107865825.mp4` | 1920x1080 | 27.293s | 4.3MB | SpaceX (@SpaceX) | yt-dlp twitter extractor(游客) |
| 3 | Threads | ✅ | `threads_De90Pbuk52l.mp4` | 720x1280 | 95s | 11.9MB | Colin and Samir | yt-dlp-threads 插件(Googlebot SSR) |
| 4 | 微博 | ✅ | `weibo_5266679128920856.mp4` | 540x960 | 34s | 4.1MB | 央视新闻 | planB: 搜索引擎转引URL + Weibo extractor(游客) |
| 5 | 抖音 | ❌ | - | - | - | - | - | 两法用尽, 见§3/§4 |
| 6 | 小红书 | ✅ | `xhs_6ae70cc2000000000602374d.mp4` | 720x1364 | 41.17s | 7.2MB | 🐶还是那个Fiona (来自用户分享文案; yt | yt-dlp XiaoHongShu extractor(匿名) |
| 7 | 哔哩哔哩 | ✅ | `bilibili_BV1RA4w6AE74.mp4` | 1280x536 | 342s | 29.2MB | 弧光猎人_ARCRaiders (mid=354 | guest playurl(platform=html5,high_quality=1, |

**成绩: 5/7 平台成功** (YouTube、抖音失败, 均为平台侧反爬, 非网络问题——16/16 域名网络层全通, 见 W002)。
所有文件 ffprobe 体检通过 (h264+aac, 尺寸/时长/大小正常, 见 W021)。

## 2. 各平台视频详情 (元信息)

### 2.1 YouTube ❌

下载未成功, 失败详情见 §3, 未探索路径见 §4。

### 2.2 X (推特) ✅

- **来源 URL**: https://x.com/SpaceX/status/1806444569107865825
- **作者**: SpaceX (@SpaceX)
- **标题**: SpaceX - Starbase team testing the tower chopsticks for the upcoming catch of ...
- **摘要**: Starbase team testing the tower chopsticks for the upcoming catch of a Super Heavy booster https://t.co/mwkefizmwO
- **发布时间**: 20240627
- **时长**: 27.293s
- **分辨率**: 1920x1080 | **大小**: 4,331,139 B (4.3MB)
- **播放/点赞**: view=18446838 like=13448
- **下载方法**: yt-dlp twitter extractor(游客) fmt=best
- **内容发现方式**: WebSearch(Lemmy帖留档: SpaceX 官方筷子臂测试推文)

### 2.3 Threads ✅

- **来源 URL**: https://www.threads.com/@mosseri/post/De90Pbuk52l
- **作者**: Colin and Samir
- **标题**: Instagram launches longform content called “Features” per @mosseri
- **摘要**: Instagram launches longform content called “Features” per @mosseri
- **时长**: 95s
- **分辨率**: 720x1280 | **大小**: 11,940,105 B (11.9MB)
- **播放/点赞**: view=None like=101
- **下载方法**: yt-dlp-threads 插件(Googlebot SSR) fmt=dash-17997862818103670v+dash-17997862773103670a
- **内容发现方式**: 搜索提供URL

### 2.4 微博 ✅

- **来源 URL**: https://weibo.com/2656274875/5266679128920856
- **作者**: 央视新闻
- **标题**: 周深的祝福张口就来
- **摘要**: 【#周深的祝福张口就来#[哈哈]】今年是#周深第5次上央视春晚#，他希望有更多机会陪伴大家过年。@卡布叻_周深 解锁“马上红火”徽章，送出马年祝福：“祝大家马年生活越来越红火，红红火火过大年！”#马年春晚等着你# http://t.cn/AXt6IXPx ​​​
- **时长**: 34s
- **分辨率**: 540x960 | **大小**: 4,051,221 B (4.1MB)
- **播放/点赞**: view=816375 like=47996
- **下载方法**: planB: 搜索引擎转引URL + Weibo extractor(游客) fmt=mp4_hd
- **内容发现方式**: yt-dlp WeiboUser extractor (m.weibo.cn/u/2656274875, 免登录)

### 2.5 抖音 ❌

下载未成功, 失败详情见 §3, 未探索路径见 §4。

### 2.6 小红书 ✅

- **来源 URL**: https://www.xiaohongshu.com/discovery/item/6ae70cc2000000000602374d?source=webshare&xhsshare=pc_web&xsec_token=ABkoBqM9GMVdo1NVmw_Y6JKBLjknYMEg4LoEXLOXOsQJ0=&xsec_source=pc_share
- **规范 URL**: https://www.xiaohongshu.com/explore/6ae70cc2000000000602374d
- **作者**: 🐶还是那个Fiona (来自用户分享文案; yt-dlp未返回uploader字段)
- **标题**: 谢却山这眼神谁能接的住啊🥹
- **摘要**: 不管了，不能我一个人哭[哭惹R]#檀健次[话题]# #谢却山[话题]# #路透[话题]# #破碎感男主[话题]# #颜值和演技并存[话题]# #每一个眼神都是戏[话题]# #何不同舟渡[话题]# #古装剧[话题]# #一眼沦陷[话题]#
- **时长**: 41.17s
- **分辨率**: 720x1364 | **大小**: 7,234,489 B (7.2MB)
- **下载方法**: yt-dlp XiaoHongShu extractor(匿名) fmt=0
- **内容发现方式**: 用户提供分享链接(带xsec_token)
- **备注**: 匿名档720p; 4K档需匿名web_session cookie(未提供, 见findings B18)

### 2.7 哔哩哔哩 ✅

- **来源 URL**: https://www.bilibili.com/video/BV1RA4w6AE74
- **作者**: 弧光猎人_ARCRaiders (mid=3546964469746014)
- **标题**: 总有世界，与你同频｜《弧光猎人》同频测试PV&国服全新PVP事件预告
- **摘要**: 《弧光猎人》（英文名：ARC Raiders）是一款由Embark Studios和腾讯联合开发、腾讯代理发行的第三人称PvEvP撤离射击冒险游戏。
狭路相逢，是针锋相对、做匹独狼，还是合作抵抗？不一样的选择，会打开不一样的世界。
你，想要怎样的冒险，想成为怎样的奇袭者？

「数据猎取」——国服专属PVP事件介绍：
目标区域通讯已中断，奇袭者可在此搜集用以恢复通信的讯号数据，带回斯佩兰扎换取名望与财富。
相互劫掠在所难免，带得回去，才算你的。
奇袭者们！我们地表见！

弧光猎人【同频测试】现已开放招募，1
- **发布时间**: 2026-11-03
- **时长**: 342s
- **分辨率**: 1280x536 | **大小**: 29,157,708 B (29.2MB)
- **下载方法**: guest playurl(platform=html5,high_quality=1, qn=64)
- **内容发现方式**: api.bilibili.com/x/web-interface/popular 热门榜(免登录)
- **备注**: 免登录最高480p(B11); 720p+需SESSDATA cookie(用户未提供, 记录为未探索路径)

## 3. 遇到的问题 (忠实记录, 报错逐字摘录)

### 3.1 微博 — 自发现两连败, 下载通路一次过
- **方案A失败**: `m.weibo.cn/api/container/getIndex` 四次请求(央视新闻/人民日报×2页)全部返回 `ok=-100` (HTTP 200)。该 API 现在要求 JS 级访客 cookie, 纯 requests 拿不到。
- **方案B首败**: yt-dlp `WeiboUser` extractor 列用户视频返回 **0 条**, 重定向链落在 `passport.weibo.cn/visitor/visitor?entry=sinawap&...` (访客护照流程, 无 JS 无法走通)。
- **破局**: 改从搜索引擎拿到具体视频 URL (央视新闻 2026 马年春晚周深祝福微博), yt-dlp `Weibo` extractor(游客) 一次成功 → 说明**单视频提取没有风控墙, 墙在'列用户时间线'这一步**。
- 画质 540x960 为该竖屏视频游客档最高可用档。

### 3.2 哔哩哔哩 — html5 探针超预期 (修正上轮调研结论)
- 免登录 `playurl?platform=html5&high_quality=1` 直接返回 **qn=64 (720p 档) mp4 单文件**, 无需合并。
- **修正 findings/02 §8 结论**: 上轮调研(zhipeng 笔记)称免登录仅 480x640; 实测 html5 参数仍可拿 720p 档(本视频为 2.39:1 电影宽幅, 故 1280x536)。yt-dlp 免登录路径未再启用(html5 已够)。
- 未用 SESSDATA, 1080p 档未尝试(见 §4)。

### 3.3 YouTube — 两法均死于数据中心 IP bot-check
- 发现环节 `ytsearch10:AI agent` 正常(证明搜索可用), 但播放器提取两次失败, 报错逐字:
  - 方案A `player_client=ios,web_safari`: `ERROR: [youtube] Zqno_vux6d8: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.`
  - 方案B(换法重试) `player_client=web,android_vr,tv_downgraded`: 同样报错(视频不同: EkdIZXDnRK8)。
- 与 findings/03 B1 预判完全一致: 本沙盒出口=香港阿里云(数据中心 IP), bot-check 类失败换 client 重试基本无效(bigiron 分诊法明示), 按'最多重试1次'规则止损。

### 3.4 抖音 — 两条通路 2026 年均已被收紧
- **方案A失败(结构性)**: iesdouyin 分享页 `window._ROUTER_DATA` 现在只回**壳数据**(loaderData 里仅页面元信息: ua/isSpider/webId/renderInSSR), `aweme_id`/`desc`/`play_addr` 出现次数=0。上轮调研时该通路(zhipeng 笔记)可免登录拿 4K60——**已被字节收紧**。逐字: `_ROUTER_DATA无item(删除/风控?) loaderData keys=['video_layout', 'video_(id)/page']`
  - 三个目标交叉验证排除'目标已删'解释: 2021 示例视频(6915675899241450760)、2024 示例(7604129988555574538)、央视新闻 2025 中秋MV(7557764222948478251, 短链 302 正常)三者的分享页 SSR 全部无 item 数据。
- **方案B失败(如预判)**: yt-dlp 内置 Douyin extractor 报 `Fresh cookies (not necessarily logged in) are needed` (findings/03 B13 原文复现, a_bogus 签名墙)。
- 结论: 抖音反爬为本轮唯一**结构性失败**平台, 与用户既往经验(WorkBuddy 案例)一致。

### 3.5 X / Threads / 小红书 — 一次过, 各有一个可复用新知
- **X**: yt-dlp twitter extractor 游客免 cookie 直接拿下 SpaceX 官方推文 1920x1080。新知: **搜索引擎结果页里常留有 video.twimg.com 的 CDN 直链**(本次 Lemmy 帖留档了 1080p 直链), 是现成的 B 方案备份(未启用)。
- **Threads**: 官方搜索/主页对游客有登录墙, 但 **Googlebot UA 抓 `threads.com/@user` 主页会 SSR 出近期帖子的 code 列表**(本次从 @mosseri 主页抽到 8 个 code, 逐一用插件 --simulate 验证哪个带视频)。这是本轮原创的可复用发现, 补上了插件 README 没写的'内容发现'环节。
- **小红书**: 用户给定的 xsec_token 分享链 + yt-dlp 匿名档一次过(720x1364)。yt-dlp 未返回 uploader 字段, 作者名以用户分享文案补全(已在 meta.json 标注来源)。

### 3.6 其他过程问题
- curl `-w` 参数写 `@xxx` 开头会被解析为'读文件', 探测脚本首次运行报错(`curl: option -w: error encountered when reading a file`), 已修复为 `[xxx]` 前缀。
- ffmpeg 全量解码体检单次 bash 调用超时(>300s), 改用 ffprobe 快速体检完成(W021)。
- WebSearch 对 v.douyin.com/threads.net 帖子级 URL 的收录极差(5 轮搜索无一条直接结果), 印证'围墙花园检索不到'痛点; 实际靠**第三方转引**(Lemmy 帖/豆瓣帖/文档示例)拿到目标。

## 4. 未探索路径 (想走但按规则没走的)

| 平台 | 未探索路径 | 预期收益 | 为何没走 |
|------|-----------|---------|---------|
| YouTube | ① bgutil-ytdlp-pot-provider (Brainicism, node 版本地起 4416 服务 + pip 插件) ② burner 账号 cookies | POT token 是数据中心 IP bot-check 的对症解法, 大概率能通 | 需 clone+node server+插件三步部署, 超出'换方式重试1次'预算 |
| 抖音 | ① ttwid 注入 (POST ttwid.bytedance.com/ttwid/union/register 取 cookie 后喂给 yt-dlp) ② TikTokDownloader (★17.3k, 扫码登录) ③ playwright 真浏览器截 JSON | ttwid 是 yt-dlp 报错点名要的'fresh cookies', 成功率最高的下一步 | 同上; 且扫码登录需要用户手机参与 |
| B站 | SESSDATA cookie → 1080p+ | 画质提升 | 用户未提供 cookie |
| 小红书 | 匿名 web_session cookie → 4K HEVC 档 | 画质提升 (findings B18) | 用户未提供 cookie |
| 微博 | ① 补 XSRF-TOKEN 头走容器 API ② gallery-dl weibo (32 extractors) | 恢复'列时间线'自发现能力 | 已有替代方案(搜索引擎给URL), 边际价值低 |
| Threads | ① `/share/<code>` 短链形态 ② threads 官方 API | 备用通路 | 本轮已成功, 无需 |

## 5. 如果下一步要我'自行搜索'内容, 怎么办?

本轮实测把'发现'和'下载'拆开验证了一遍, 结论分三档:

**① 沙盒内可自发现(已实测, 脚本化)**
- B站: `api.bilibili.com/x/web-interface/popular` 热门榜免登录, 拿 bvid/cid/标题/UP (dl_bilibili.py 内置)
- YouTube: `yt-dlp ytsearch10:<关键词>` 可搜索可过滤时长 (dl_youtube.py 内置; 注意发现可用≠能下载, 见 §3.3)
- Threads: **Googlebot UA 抓主页 → 抽帖子 code → 插件 --simulate 验证带视频** (本轮新方法, tools/probe_threads.sh + tools/find_threads_video.sh)
- X: 平台内搜索需登录; 但搜索引擎查 `"x.com/<user>/status"` 常能命中新闻/论坛转引, 且转引页常附 video.twimg.com 直链

**② 需要转引/第三方 (半自动)**
- 抖音: 站内搜索(a_bogus 签名)不可行; 可走 ① 搜索引擎找 `v.douyin.com` 短链转引(本轮 5 轮搜索 0 命中, 收录差) ② tophub/新抖等热榜站 ③ **用户给分享链接最稳**(短链 302 解析仍正常)
- 微博: 列时间线被访客墙挡; 搜索引擎查 `weibo.com/<uid>/<bid>` 转引可命中(本轮即此法), 或用户给 status URL

**③ 基本必须用户给料**
- 小红书: 站内搜索需登录+签名(a1/x-s); 浏览器地址栏 URL 不带 xsec_token 无法解析(findings B17)。**给 App 分享链接是唯一稳定入口**。

**可复用结论: '下载器解决下载, 发现靠组合拳(平台API+搜索引擎转引+用户给链)'** —— 对围墙花园, 搜索引擎的索引缺口是常态, 转引页(新闻/豆瓣/Lemmy/工具文档示例)是主要突破口。

## 6. 可复用资产

- **脚本** (`tools/`, 与本地 `~/my-project/scripts` 同源): `dl_{weibo,bilibili,youtube,xhs,douyin,x,threads}.py`(每平台独立, 统一 RESULT 行输出, 失败自动写 W 条目), `lib_media.py`(日志/元数据/格式选择/下载), `gh_sync.sh`(增量推送), `probe_targets.sh`/`probe_threads.sh`/`find_threads_video.sh`/`extract_threads_profile.py`(目标发现)
- **skill**: `skills/video-downloader/` (SKILL.md + 全套脚本, 含本轮全部踩坑要点)
- **协议**: worklog W 条目 + state.json + 每步 push (findings/04, 本轮全程执行)

## 7. 校验
- 文件完整性: 5/5 ffprobe 通过 (h264+aac, 尺寸/时长/大小正常, W021)
- GitHub 推送: 每平台完成即 push (commit 链 f16c4e0→HEAD, 本目录全量入库)
- 本报告由 `tools/build_report.py` 从 meta.json 自动生成, 手写章节为 §3-§6。
