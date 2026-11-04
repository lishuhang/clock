# findings/01 — 8 平台可行性总矩阵

> 图例：可达性=沙盒网络层实测；通路=下轮实抓的首选+回退；风险=反爬/登录复杂度。
> 元数据获取：所有 yt-dlp 通路用 `--dump-json`（webpage_url/uploader/title/description 一把抓）；脚本通路各自有 JSON。

| 平台 | 网络可达 | 主通路 | 回退通路 | 需要登录/Cookie | 元数据 | 风险 | 预判 |
|---|---|---|---|---|---|---|---|
| **微博** | ✅ 302 | yt-dlp `Weibo` extractor（自动游客 cookie，公开视频免登录，最高 2160p60） | gallery-dl weibo(32 extractors)；WeiboVideoDL 式 DASH+会员cookie | 公开内容**免登录** | yt-dlp --dump-json | **低** | 最有把握，下轮第一个打 |
| **B站** | ✅ 302 | yt-dlp BiliBili(19 extractors)；免登录 480p；+SESSDATA → 720p+ | 上一轮验证过的 agent-browser + `__playinfo__` + curl DASH 管线（22/22 成功，含极验验证码解法） | SESSDATA（可选，仅提画质） | --dump-json / 页面 __INITIAL_STATE__ | 中（数据中心 IP 有 412 风控前科） | 480p 免登录应直通 |
| **YouTube** | ✅ 200 | yt-dlp 2026.10.26 + `player_client=ios,web_safari` | ①`player_client=web,android_vr,tv_downgraded`(SABR 修复) ②bgutil-ytdlp-pot-provider(★889,活跃) ③burner cookies | 免登录（数据中心 IP 可能要 PO token 或 cookies） | --dump-json | 中 | 上轮死于 bot check，本轮有 POT provider 这张新牌 |
| **X** | ✅ 200 | yt-dlp `twitter`（公开推文多数免 cookie） | gallery-dl twitter（需 auth_token） | 公开免；部分推文需 auth_token（**burner 号**，有封号风险） | --dump-json | 中 | 直测公开推文即可 |
| **Threads** | ✅ 301 | **tribixbite/yt-dlp-threads 插件**（Googlebot UA 拿 SSR 全量 post，绕登录墙；仅公开帖） | curl Googlebot UA 手工解析 og:video/内嵌 JSON；`/share/<code>/` 短链 | **免登录** | 插件抽取（author/title；duration 从 CDN efg 参数解码） | 中（官方无支持，绕法天生脆弱） | 8 平台唯一无主流支持，但插件方案明确 |
| **小红书** | ✅ 302 | yt-dlp `XiaoHongShu` extractor（实测存在）+ **带 xsec_token 的 App 分享链接** | JoeanAmier/XHS-Downloader(★13.2k 活跃)；MediaCrawler(★70k,重) | 匿名可下 720p；+匿名 `web_session` cookie → 4K | --dump-json | 中高 | extractor 在，卡点是链接必须带 xsec_token（需用户提供） |
| **Instagram** | ✅ 200 | gallery-dl(72 extractors)/yt-dlp + `sessionid` cookie | instaloader(★13.8k 活跃) | **基本必须 sessionid**（匿名重墙） | gallery-dl --dump-json / instaloader | 中高 | 等 cookie，到货即测 |
| **抖音** | ✅ 200 | **iesdouyin 分享页 SSR**：aweme_id → `https://www.iesdouyin.com/share/video/<id>/`(iOS UA) → 解析 play_addr → `playwm→play` + `ratio=default` → 无水印原片 4K60，**免登录免签名** | ①TikTokDownloader(★17.3k 当日更新, a_bogus 内置, 扫码登录) ②playwright 真浏览器 | 主通路免登录 | 分享页内嵌 JSON（desc/author/统计） | **高**（a_bogus 签名体系，接口常变） | yt-dlp 内置 extractor 已失效，走分享页旁路 |

## 选型红线（来自仓库维护状态核查 W007）

- **已归档勿选**：BBDown(2026-05)、BiliTools(2026-07)、bilibili-API-collect(2026-01)、junhoyeo/threads-api(2023-09)
- ReaJason/xhs 16 个月未更新，视同停更
- `yt-dlp/yt-dlp-get-pot` 仓库已不存在（框架并入 yt-dlp 主程序）；bgutil 插件正确路径是 `Brainicism/bgutil-ytdlp-pot-provider`（大写 B）

## 需用户补给清单（阻塞项）

1. **Instagram sessionid cookie**（burner 账号）——高优先
2. **小红书 App 分享链接**（带 xsec_token）——高优先
3. X auth_token cookie（burner）——中（先测免 cookie）
4. B站 SESSDATA——低（可选提画质）
5. YouTube burner cookies——低（PO token 可替代）
