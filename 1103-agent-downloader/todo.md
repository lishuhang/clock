# todo — 下轮实抓执行计划

> 前提：工具已装好（yt-dlp 2026.10.26 / gallery-dl 1.32.19 @ /home/z/.venv/bin）。
> 原则：**每平台 = 一个独立脚本 + 结构化结果行**；先 `--simulate`/`--dump-json` 验证元数据通路，再实下；单平台失败不阻塞其他平台；每完成一步 commit+push。

## Phase 0 — 准备（约 10 分钟）

- [ ] T0.1 装 Threads 插件：`/home/z/.venv/bin/pip install git+https://github.com/tribixbite/yt-dlp-threads`，验证：`/home/z/.venv/bin/yt-dlp --verbose "https://www.threads.net/@x/post/xxx" 2>&1 | grep "Extractor Plugins"`（预期出现 `ThreadsIE`）
- [ ] T0.2 建密钥目录：`mkdir -p /home/z/my-project/.secrets/cookies`（不入库）
- [ ] T0.3 选定 8 个测试视频 URL（各平台挑一条**公开、带视频、内容无害**的；微博/B站/抖音/小红书选中文热门内容即可），写入 `tools/test_urls.json`
- [ ] T0.4 写通用元数据落盘脚本 `tools/fetch_meta.sh <platform> <url>`：`yt-dlp --dump-json --no-warnings` → 存 `results/<platform>/meta.json`（含 webpage_url/uploader/title/description）

## Phase 1 — 按风险从低到高逐平台实抓（每平台 ≤15 分钟，超时换回退）

### T1.1 微博（最低风险，先拿首胜）
- [ ] `tools/fetch_meta.sh weibo "<微博视频URL>"`（yt-dlp Weibo extractor 自动游客 cookie）
- [ ] 下载：`yt-dlp -o "results/weibo/video.%(ext)s" "<URL>"`
- [ ] 校验：`ffprobe` 时长>0 + meta.json 有 webpage_url/author/title/description
- 回退：m.weibo.cn 移动端 URL 格式重试；gallery-dl weibo extractor

### T1.2 B站
- [ ] 免登录 480p：`yt-dlp -o "results/bilibili/video.%(ext)s" "https://www.bilibili.com/video/BVxxx"`
- [ ] 若触发 412/风控 → 回退 A：`--add-headers "Referer:https://www.bilibili.com/"` + 游客 buvid cookie 重试
- [ ] 再失败 → 回退 B：重建上轮 agent-browser + `__playinfo__` 管线（设计要点见 findings/03 坑7-9；含极验验证码处理，预期工作量最大）
- [ ] 若用户提供了 SESSDATA：`--cookies` 走 720p+

### T1.3 YouTube
- [ ] 直测：`yt-dlp --simulate -v "<URL>"`；成功则直接下
- [ ] 报 `Sign in to confirm you're not a bot` / 403 / Only images → 依次尝试：
  1. `--extractor-args "youtube:player_client=ios,web_safari"`
  2. `--extractor-args "youtube:player_client=web,android_vr,tv_downgraded"`（SABR 360p 修复）
  3. 装 bgutil-ytdlp-pot-provider（node 版本地起服务，pip 装插件端）：`pip install bgutil-ytdlp-pot-provider` + 跑其 node server
  4. 用户给 burner cookies → `--cookies`
- [ ] 注意：nsig 报错=yt-dlp 版本旧（先 `-U`）；下载中途 403=URL 过期（删 .part 重下，勿断点续传）

### T1.4 X
- [ ] 直测公开推文：`yt-dlp --dump-json "https://x.com/<user>/status/<id>"`
- [ ] 失败/需登录 → 用户提供 auth_token cookie（burner 号）→ `--cookies`
- 回退：gallery-dl twitter extractor（`--cookies` 同一份）

### T1.5 Threads
- [ ] `yt-dlp -o "results/threads/video.%(ext)s" "https://www.threads.net/@<user>/post/<id>"`
- [ ] 插件原理是 Googlebot UA 拿 SSR 页面（仅公开帖，无登录）；若失效：curl Googlebot UA 手工解析 og:video / 内嵌 JSON；或 /share/<code>/ 短链格式

### T1.6 小红书
- [ ] 前置：等用户提供带 `xsec_token` 的 App 分享链接
- [ ] `yt-dlp --dump-json "<带xsec_token的链接>"` → 匿名档 720p
- [ ] 4K 档：用户再给匿名 `web_session` cookie（Chrome 访问过一次小红书即有）→ `--cookies`
- [ ] 回退：JoeanAmier/XHS-Downloader（★13.2k 活跃）

### T1.7 Instagram
- [ ] 前置：等用户提供 sessionid cookie → `/home/z/my-project/.secrets/cookies/instagram.txt`（Netscape 格式）
- [ ] `gallery-dl --cookies <file> -d results/instagram "https://www.instagram.com/p/<code>/"` 或 `yt-dlp --cookies <file>`
- [ ] 回退：instaloader（★13.8k 活跃）

### T1.8 抖音（签名最复杂，压轴）
- [ ] 主通路（免登录免签名）：解析 aweme_id → `curl -A "<iOS UA>" "https://www.iesdouyin.com/share/video/<aweme_id>/"` → 正则抽 `play_addr` JSON → 把 URL 中 `playwm` 换 `play`、改写 `ratio=default` → 直下（可拿无水印原片 4K60）
  - URL 提取规则与三档画质参数详见 findings/02 抖音节
- [ ] 回退 A：TikTokDownloader（pip/git 运行，支持扫码登录，a_bogus 签名内置）
- [ ] 回退 B：playwright 起真浏览器访问分享页截 JSON

## Phase 2 — 汇总交付

- [ ] T2.1 `results/summary.md` + `results/summary.json`：8 平台 × {source_url, author, title, description, local_file, file_size, duration, fetch_method, notes}
- [ ] T2.2 每个视频 `ffprobe` 体检 + 抽 1 帧确认非空画面
- [ ] T2.3 失败平台如实记录失败原因（引用 verbatim 报错）+ 建议补充条件
- [ ] T2.4 根 worklog.md 追加本轮条目 + push

## 需用户提供（已在 state.json blocked_on 同步）

| 平台 | 需要 | 优先级 |
|------|------|--------|
| Instagram | burner 账号 sessionid cookie | 高（无它基本无法过匿名墙） |
| 小红书 | 任意公开视频笔记的 App 分享链接（带 xsec_token） | 高 |
| X | auth_token cookie（burner） | 中（先测免 cookie 通路） |
| B站 | SESSDATA | 低（可选，提画质） |
| YouTube | burner cookies | 低（可选，PO token 可替代） |
