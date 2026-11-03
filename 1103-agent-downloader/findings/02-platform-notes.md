# findings/02 — 分平台方案细节与来源

> 每节含：通路原理 / 关键参数 / 元数据获取 / 来源。全部来源均实际打开核对过。
> 上轮会话（1020-feng-video，B站）的一手经验单独标注 `[上轮]`。

## 1. YouTube

- **工具**：yt-dlp 2026.10.26（已装）。1755 extractors 中 YouTube 系 21 个。
- **限速/风控分层**（来源：bigiron.cc《yt-dlp Breakage Triage: nsig, 403s, and Sign In to Confirm》，2026）：
  - `nsig extraction failed` → 纯版本问题，`pip install -U yt-dlp` 解决，加 cookie 无用
  - `Sign in to confirm you're not a bot` → 数据中心 IP（本沙盒就是）或缺 PO token。两条正路：**burner 账号 cookies**（勿用主号）或 **PO token provider**
  - 403 分两种：**开始就 403** = token/客户端不匹配（换 player_client）；**下载中途 403** = googlevideo 签名 URL 过期 → 删 `.part` 重下，**勿断点续传**；限速过低会加剧
  - `Only images are available for download` = 伪装成格式问题的认证失败，按 bot check 处理
  - **重试策略警告**：bot check 类失败重试必然同样失败（指纹没变），禁止盲目 backoff——这是 token 狂烧的典型来源
- **客户端参数**：
  - `--extractor-args "youtube:player_client=ios,web_safari"`（来源：zyipeng platform-notes，绕 throttle）
  - `--extractor-args "youtube:player_client=web,android_vr,tv_downgraded"`（来源：CRtheHILLS/yt-dlp-rescue v2.2，2026-03，修 SABR 强制 360p）
- **PO token provider**：`Brainicism/bgutil-ytdlp-pot-provider`（★889，2026-10-07 仍在更新）。docker 版监听 4416；**沙盒无 docker，用其 node 版本地起服务**（node v24 现成）。pip 端插件 + node server 两件套。
- **元数据**：`yt-dlp --dump-json` → webpage_url/uploader/title/description/view_count/upload_date 全有。
- `[上轮]` yt-dlp 直连 YouTube 触发 Google 验证码，无解（当时未尝试 POT provider）；snapany 网页中转第一次解析后弹登录墙。

## 2. Instagram

- **工具**：gallery-dl 1.32.19（72 个 instagram extractors）为主，yt-dlp（5 个）备用；instaloader（★13.8k，2026-11-01 更新）为重型备选。
- **现实**：匿名访问重度受限（登录墙/401）。**sessionid cookie 基本是硬门槛**。
- **cookie 格式**：Netscape cookies.txt（含 `sessionid` 字段），从登录浏览器导出，或 gallery-dl `--cookies-from-browser`（沙盒无真浏览器 profile，需用户给文件）。
- **命令草案**：
  - `gallery-dl --cookies /home/z/my-project/.secrets/cookies/instagram.txt -d results/instagram "https://www.instagram.com/p/<code>/"`
  - `gallery-dl --dump-json "<URL>"` 拿元数据
- **风控**：Instagram 对数据中心 IP + 高频请求会触发 checkpoint，控制单次请求量。

## 3. X / Twitter

- **工具**：yt-dlp `twitter` extractor（6 个）；gallery-dl twitter（61 个，需 auth_token）。
- **免 cookie 面**：多数公开推文视频 yt-dlp 直接可下（来源：zyipeng notes："大部分公开推文不需要 cookies"）。
- **需要 cookie 的场景**：敏感内容/部分私密推文/高频繁取。
- **cookie**：`auth_token`（F12 → Application → Cookies）。**警告（来源：afkarxyz/Twitter-X-Media-Batch-Downloader 文档）：使用 auth_token 有封号风险，建议 burner 账号；获取后不要登出账号（登出会刷新 token）**。
- **元数据**：`yt-dlp --dump-json`（uploader/title=推文全文/description）。

## 4. Threads（唯一无主流支持的平台）

- **官方现状**：yt-dlp 4 个 issue（#7523/#10133/#12021/#17606）请求 Threads 支持，均未实现/关闭；gallery-dl 无 threads.net extractor（本地 0 匹配实测确认）；junhoyeo/threads-api 2023-09 归档死亡。
- **解法：tribixbite/yt-dlp-threads 插件**（来源：GitHub README，2026 检索可见）：
  - 原理：**Meta 给链接预览爬虫（Googlebot UA）服务端渲染完整 post 含 CDN 媒体 URL** → 插件用 Googlebot UA 请求，绕过匿名客户端的 JS 登录墙
  - 支持：`@user/post/<id>` 规范链、`/share/<code>/` 短链、多视频轮播
  - 安装：`pip install git+https://github.com/tribixbite/yt-dlp-threads`；验证 `yt-dlp --verbose <url>` 输出含 `Extractor Plugins: ThreadsIE`
  - 已知限制：仅公开帖；无 cookie/认证支持；**绕法天生脆弱**（Meta 收紧爬虫待遇即失效）；duration 从 CDN URL `efg` 参数解码（post 无 video_duration 字段）
- **回退**：`curl -A "Googlebot..."` 手工解析 og:video meta / 内嵌 JSON；备选 aditya76-git/threadscrape-threads-net-web-api。
- **下轮先查该插件仓库 stars/最近提交（本轮未及核查其活跃度）**。

## 5. 微博

- **工具**：yt-dlp `Weibo` / `WeiboUser` / `WeiboVideo` 三 extractor。
- **关键事实（来源：zyipeng notes）**：yt-dlp 内置 extractor **能自动获取游客 cookie，公开微博无需登录，最高可拿 4K (2160p60)**——"全 skill 里画质上限最高的之一"；仅粉丝可见/仅自己可见需登录 cookies。
- **URL 形态**：`weibo.com/<uid>/<bid>`、`m.weibo.cn/status/<id>`、`video.weibo.com/show?fid=<fid>`。
- **注意**：quality 模式可能下到 300MB+ 大文件（4K 长视频），下轮限 `--format` 或选短视频测试。
- **备选**：gallery-dl weibo（32 extractors，相册/用户媒体流）；chopper-go/WeiboVideoDL 思路（DASH 音视频分离 + 会员 cookie 4K）；dataabc/weibo-crawler（★4.7k 活跃，偏帖子文本）。
- **元数据**：`--dump-json`。

## 6. 抖音（反爬最重）

- **官方 extractor 已死**：yt-dlp 内置 `Douyin` extractor 自 2025 起失效（需 a_bogus 风控签名；典型报错 `Fresh cookies (not necessarily logged in) are needed`）。来源：zyipeng notes。
- **主通路：移动端分享页 SSR（免登录免签名）**（来源：zyipeng notes，其 skill 实测可拿 4K60）：
  1. 任意用户 URL（短链 `v.douyin.com/xxx` 或长链 `douyin.com/video/<id>`）→ 提取 `aweme_id`
  2. 以 **iOS UA** 请求 `https://www.iesdouyin.com/share/video/<aweme_id>/`
  3. 解析 HTML 内嵌 `play_addr` JSON；优先 `play`（无水印）回退 `playwm`（带水印 720p）
  4. **画质由隐藏参数 `ratio` 控制**：`/play/?ratio=default` = 原始 master（上传者给的什么就是什么，唯一 4K 路径）；`ratio=1080p`/`ratio=720p` = 转码档
  5. 关键机制：**`/playwm/` 端点完全忽略 ratio 参数**（只返 720p 水印版），必须用 `/play/`；分享 URL 默认写死 `ratio=720p` 需改写
- **回退 A：TikTokDownloader（JoeanAmier，★17.3k，2026-11-03 当日仍在更新）**：
  - 认证体系（来源：DeepWiki 文档）：a_bogus=SM3 hash+RC4（gmssl 库，≈160 字符）；msToken 每 **900s** 后台线程自动刷新（mssdk.bytedance.com）；ttwid 自 ttwid.bytedance.com；web_id 自 mcs.zijieapi.com
  - Cookie：抖音支持**扫码登录**自动写入；TikTok 需手动粘贴；rookiepy 可读本机浏览器（沙盒不适用）
  - 运行：Python 3.12+（本沙盒正好 3.12.16）源码跑或 docker 镜像 `joeanamier/tiktok-downloader`
  - 已知问题（issue #689）：合集批量下载部分条目 403 反复重试失败（风控），单视频下载不受影响
- **回退 B**：playwright 起真浏览器加载分享页，截获响应 JSON。
- **元数据**：分享页 SSR JSON 含 desc/作者昵称/统计；TikTokDownloader 有完整数据采集模式。

## 7. 小红书

- **关键事实（来源：zyipeng notes）**：
  - **URL 必须带 `xsec_token`**（从 **App 分享按钮**复制；浏览器地址栏 URL 不带，无法用）
  - 画质两档：裸 yt-dlp（无 cookie）→ 720p H.264；**+ 匿名 `web_session` cookie**（非登录！Chrome 访问过一次小红书即有）→ 最高 4K (3840×2160) HEVC 多档
  - 登录态自检 API：`edith.xiaohongshu.com/api/sns/web/v2/user/me` → `"guest":true` 匿名 / `"guest":false`+nickname 真登录
  - 私密笔记才需要真登录
- **工具**：yt-dlp `XiaoHongShu` extractor（本地实测存在，1 个）；批量备选 JoeanAmier/**XHS-Downloader**（★13.2k，2026-10-31 更新）；MediaCrawler（★70k，playwright+扫码，重型爬虫场景）。
- **元数据**：`--dump-json`（title/uploader/description）。
- **注意**：ReaJason/xhs 库已 16 个月未更新，勿作为主依赖。

## 8. 哔哩哔哩

- **工具现状**：yt-dlp BiliBili 系 19 extractors（视频/番剧/音频/课程自动识别）。BBDown、BiliTools 均已归档。
- **登录态（来源：zyipeng notes）**：**720P/1080P/4K 必须登录**（SESSDATA），否则 480x640；报错 `Format(s) 720P 准高清 are missing; you have to become a premium member` **不是真要会员，是要登录态**。HEVC(hev1.*) 是主推编码。
- **`[上轮]` 免登录 480p 管线（22/22 成功，代价最小）**：
  1. agent-browser 真浏览器开 `bilibili.com/video/<BV>/`，轮询 `window.__playinfo__`（2-20s 不定，别固定等待）
  2. 取 `data.dash.video[0].baseUrl` + `data.dash.audio[0].baseUrl`
  3. `curl -H "Referer: https://www.bilibili.com/" -H "Cookie: <浏览器全部cookie>"` 分别拉 m4s
  4. `ffmpeg -i v.m4s -i a.m4s -c copy out.mp4`
- **`[上轮]` 元数据**：视频页 `__INITIAL_STATE__`（有时缺失，勿依赖）；或 B站 search API 同源 fetch（`wbi/search/type` 宽松、`x/web-interface/view` 有 wbi 签名墙）。
- **CDN 坑**：同批下载约 1/3 `Invalid NAL unit size` 坏包（upos CDN），下完必须 `ffmpeg -v error -i f -f null` 全量体检，坏的重下即愈。

---

## 调研覆盖说明（用户点名的信息源）

- **GitHub**：仓库维护状态 16 个逐一 API 核查（logs/gh_repo_check_001.txt）；TikTokDownloader 认证体系经 DeepWiki 深读；zyipeng platform-notes 全文精读；yt-dlp-threads 插件 README 全文精读
- **Hacker News**：检索 yt-dlp 相关讨论（本轮无增量价值条目）
- **Stack Overflow**：沙盒内 yt-dlp 网络受限类问题检索（结论：与本项目相关的失败模式是平台侧而非网络侧，已并入坑清单）
- **LinuxDo / V2EX / 知乎 / 即刻 / 小红书讨论**：检索视频下载工具讨论；有效产出为 zyipeng notes（技能社区）与 xiaoer-videolab README（其对微博/知乎 SPA 结构的判断与 zyipeng 相反——以 zyipeng 的实测笔记为准，下轮用真实 URL 验证仲裁）
- **skill 市场**：`[上轮]` 已排查 dsh-plugin.org(15512 插件,DSH 专用不兼容)、skills.pub(6400+,无视频下载类)、lobehub(前端向)——无现成 skill，不重复排查
