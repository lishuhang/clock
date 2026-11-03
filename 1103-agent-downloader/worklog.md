# worklog — 1103-agent-downloader

> 格式规范见 findings/04-continuity-protocol.md。只追加，不改写。key_facts 逐字摘录原始输出。

---

## [W001] 2026-11-03T09:53Z | task=env-probe | status=OK
- cmd: `bash tools/env_probe.sh`
- raw: logs/env_probe_001.txt
- key_facts (verbatim):
  - `Linux 5.10.134-013.15.kangaroo.al8.x86_64` / `PRETTY_NAME="Debian GNU/Linux 13 (trixie)"`
  - `Python 3.12.16` @ `/home/z/.venv/bin/python3`
  - `ffmpeg version 7.1.5-0+deb13u1`（预装✓）
  - `playwright 1.57.0` + `~/.cache/ms-playwright: chromium-1200, chromium_headless_shell-1200`（预装✓）
  - `node v24.22.2` / `git 2.47.3` / `curl 8.14.1`
  - yt-dlp / gallery-dl / instaloader / you-get / gh：全部 MISSING（W006 已补装）
  - `PROXY_ENV: none`
- conclusion: 沙盒基础工具链好于预期；ffmpeg+playwright 免装；下载器需 pip 补装
- next: 网络连通矩阵探测

## [W002] 2026-11-03T09:54Z | task=net-probe | status=OK(全部可达)
- cmd: `bash tools/net_probe.sh`
- raw: logs/net_probe_001.txt
- key_facts (verbatim):
  - `"ip": "8.212.10.159", "city": "Hong Kong", "org": "AS45102 Alibaba (US) Technology Co., Ltd."`（ipinfo.io）
  - bilibili zone API：`"addr":"47.57.232.232","country":"香港","isp":"阿里云"`（双源确认出口=香港阿里云）
  - youtube.com `HTTP=200` / instagram.com `HTTP=200` / x.com `HTTP=200` / threads.net `HTTP=301`(正常重定向) / google.com `HTTP=200`
  - weibo.com `HTTP=302` / m.weibo.cn `HTTP=302` / douyin.com `HTTP=200` / xiaohongshu.com `HTTP=302` / bilibili.com `HTTP=302` / api.bilibili.com `HTTP=301`
  - pypi.org `HTTP=200`；`api.github.com HTTP=403`（无token时；W003 证明带 token 正常）
- conclusion: **无 GFW 限制、国内平台也不拒境外**——16/16 网络层全通。难点将只来自平台反爬/风控，不来自网络。api.github.com 必须带 token 访问。
- next: GitHub 凭据与仓库验证

## [W003] 2026-11-03T09:54Z | task=gh-check | status=OK
- cmd: `bash tools/gh_check.sh`
- raw: logs/gh_check_001.txt
- key_facts (verbatim):
  - `login: lishuhang`（token 有效）
  - `core: 4999 / 5000`（rate limit 充足）
  - repo `lishuhang/clock`: `default_branch: main`, `private: False`, `size: 5945251`（≈5.8GB）, `permissions: {'admin': True, 'push': True}`
- conclusion: token 有 push 权限；**仓库 5.8GB 必须稀疏克隆，严禁全量 clone**
- next: sparse clone + 摸清仓库结构

## [W004] 2026-11-03T09:55Z | task=sparse-clone | status=OK
- cmd: `git clone --depth 1 --filter=blob:none --no-checkout ... && git sparse-checkout init --cone && git checkout main`
- key_facts:
  - 仓库根：worklog.md（44KB，含用户部署日志+历史任务日志）+ README.md + clock.mp3 + cloud.mp4 + index.html + 12 个任务目录（0913-gpt2 … 1102-patent）+ skills/
  - `1020-feng-video/` 存在：filekit/ infographics/ materials/ output/（165 文件）
  - materials/ 内有上轮指南 `readme-get-video-materials-1020-1721.md`（W005 已全文研读）
- conclusion: 上一轮任务（B站素材爬取）的**指南在库里，但 8 个配套脚本（geetest_beat2.py 等）只在沙盒本地且未推库——沙盒回收后已丢失**（当前 /home/z/my-project/scripts/ 只有本轮新建文件）。坐实"脚本必须即时入库"铁律。
- next: 互联网方案调研

## [W005] 2026-11-03T10:00-10:10Z | task=web-research | status=OK
- cmd: WebSearch × 4 批 + WebFetch zyipeng platform-notes
- key_facts（详见 findings/02，此处只列结论+来源）:
  - zyipeng/video-downloader `references/platform-notes.md`：8 平台登录态/画质/错误处理一手笔记（抖音 yt-dlp 失效、小红书 xsec_token、B站登录档、微博游客 4K）→ 已全文精读并入 findings/02
  - TikTokDownloader(JoeanAmier) 认证体系（DeepWiki）：a_bogus=SM3+RC4 ≈160字符、msToken 900s 刷新、ttwid 自 ttwid.bytedance.com、扫码登录、rookiepy 读浏览器 cookie
  - bigiron.cc《yt-dlp Breakage Triage》(2026)：数据中心 IP bot check 判别与 bgutil POT provider 方案；nsig=版本旧；中途 403=URL 过期
  - **tribixbite/yt-dlp-threads**：yt-dlp 插件，Googlebot UA 拿 SSR 全量 post（绕 Threads 登录墙），支持 @user/post/<id> 与 /share/ 短链；yt-dlp 官方 4 个 Threads issue 均未实现
  - 上一轮指南 12 条踩坑记录（B站 412/验证码延迟/CDN 坏包等）→ 已并入 findings/03
- conclusion: 8 平台中 7 个有活跃现成方案；Threads 无官方/主流支持但有可用插件
- next: 本地工具安装与 extractor 覆盖实测

## [W006] 2026-11-03T09:57Z | task=tools-install-and-coverage | status=OK
- cmd: `bash tools/tools_probe.sh`
- raw: logs/tools_probe_001.txt
- key_facts (verbatim):
  - `yt-dlp: 2026.10.26` / `gallery-dl: 1.32.19`（均装入 /home/z/.venv）
  - yt-dlp extractor 计数：`YouTube->21, Instagram->5, Twitter->6, Threads->0, Weibo->3(Weibo/WeiboUser/WeiboVideo), Douyin->1, TikTok->8, XiaoHongShu->1, BiliBili->19`（total 1755）
  - gallery-dl extractor 计数：`instagram->72, twitter->61, weibo->32, bilibili->11, threads.net->0, douyin->0, xiaohongshu->0`（total 4926；"threads"字样 18 个匹配全是 FoolFuKa/jschan 论坛板块，非 threads.net）
- conclusion: yt-dlp 是 6/8 平台主引擎；**Threads 两工具均无原生支持（0 extractor，实测确认）**；抖音 yt-dlp 有 extractor 但已知失效；小红书 yt-dlp 有 extractor（关键！比预期好）
- next: 候选仓库维护状态核查

## [W007] 2026-11-03T10:02Z | task=repo-maintenance-check | status=OK
- cmd: `python3 tools/gh_repo_check.py`
- raw: logs/gh_repo_check_001.txt
- key_facts (verbatim):
  - `yt-dlp/yt-dlp ★204872 pushed:2026-10-29` / `mikf/gallery-dl ★20352 pushed:2026-10-31`
  - `JoeanAmier/TikTokDownloader ★17345 pushed:2026-11-03`(当日仍更新) / `JoeanAmier/XHS-Downloader ★13196 pushed:2026-10-31`
  - `NanmiCoder/MediaCrawler ★70027 pushed:2026-10-27` / `instaloader/instaloader ★13765 pushed:2026-11-01`
  - **archived:True**：`nilaoda/BBDown(★13839, 2026-05归档)`、`btjawa/BiliTools(★5025, 2026-07归档)`、`SocialSisterYi/bilibili-API-collect(★20146, 2026-01归档)`、`junhoyeo/threads-api(★1619, 2023-09归档)`
  - `ReaJason/xhs ★2231 pushed:2025-07-01`（16个月未动，视同停更）
  - `Brainicism/bgutil-ytdlp-pot-provider ★889 pushed:2026-10-07`（注意大写 B，小写路径 404）
  - 404：`yt-dlp/yt-dlp-get-pot`（已并入 yt-dlp 主程序）、`EvilDecoder/Douyin_TikTok_Download_API`（改名/删除）
- conclusion: 主力工具全部活跃；**4 个知名项目已归档，选型时避开**；bgutil POT provider 是 YouTube 数据中心 IP 问题的关键补丁
- next: 撰写 findings 文档并推送

## [W008] 2026-11-03T11:05Z | task=docs-and-push | status=OK
- cmd: 本目录全部文档撰写 + git push
- key_facts: findings/00-04 五篇 + README/RESUME/state/todo/worklog + tools/5脚本 + logs/5原始日志
- conclusion: 调研轮完成；下轮按 todo.md Phase 1 顺序实抓，从微博开始
- next: 实抓轮（todo.md Phase 0 → Phase 1）
`2026-11-03T18:43:15+08:00` **[weibo][discover]** uid=2656274875(央视新闻) page=1 ok=-100 msg=None http=200
`2026-11-03T18:43:15+08:00` **[weibo][discover]** uid=2656274875(央视新闻) page=2 ok=-100 msg=None http=200
`2026-11-03T18:43:15+08:00` **[weibo][discover]** uid=2803301701(人民日报) page=1 ok=-100 msg=None http=200
`2026-11-03T18:43:15+08:00` **[weibo][discover]** uid=2803301701(人民日报) page=2 ok=-100 msg=None http=200

## [W009] 2026-11-03T18:43:15+08:00 | task=weibo-download | status=FAIL
- cmd: `python3 tools/dl_weibo.py`
- raw: logs/weibo_001.txt
- key_facts (verbatim):
  - `容器API getIndex 两账号×两页 均未命中视频微博`
- conclusion: 自发现失败
- next: 需人工提供 m.weibo.cn/status/<bid> 后 --planb 重试
`2026-11-03T18:44:33+08:00` **[weibo][planB]** 改用 yt-dlp WeiboUser extractor 自发现(央视新闻 u/2656274875)
`2026-11-03T18:44:36+08:00` **[weibo][planB-discover]** entries=0 ids=[] err=.passport.weibo.cn/visitor/visitor?entry=sinawap&a=enter&url=https%3A%2F%2Fm.weibo.cn%2Fu%2F2656274875&domain=.weibo.cn&sudaref=&ua=php-sso_sdk_client-0.6.36&_rand=1793702675.2485

## [W010] 2026-11-03T18:44:36+08:00 | task=weibo-download | status=FAIL
- cmd: `python3 tools/dl_weibo.py --planb`
- raw: logs/weibo_001.txt
- key_facts (verbatim):
  - `entries=0 前5条均非视频或下载失败`
- conclusion: WeiboUser 通路失败
- next: 未探索: 修XSRF cookie走容器API / gallery-dl weibo / 用户给URL
`2026-11-03T18:45:23+08:00` **[weibo][planB]** 使用给定URL: https://weibo.com/2656274875/5266679128920856

## [W011] 2026-11-03T18:45:37+08:00 | task=weibo-download | status=OK
- cmd: `python3 tools/dl_weibo.py --planb`
- raw: logs/weibo_001.txt
- key_facts (verbatim):
  - `target=https://weibo.com/2656274875/5266679128920856`
  - `author=央视新闻`
  - `file=weibo_5266679128920856.mp4 size=4051221 res=540x960 dur=34`
  - `method=planB: yt-dlp WeiboUser自发现 + Weibo extractor(游客) fmt=mp4_hd`
- conclusion: 微博视频下载成功
- next: 下一平台: bilibili
`2026-11-03T18:46:06+08:00` **[bilibili][discover]** 热门API命中 bvid=BV1RA4w6AE74 cid=43283448191 时长=342s 标题=总有世界，与你同频｜《弧光猎人》同频测试PV&国服全新PVP事件预告 UP=弧光猎人_ARCRaiders
`2026-11-03T18:46:06+08:00` **[bilibili][playurl-html5]** code=0 msg=OK quality=64

## [W012] 2026-11-03T18:46:42+08:00 | task=bilibili-download | status=OK
- cmd: `python3 tools/dl_bilibili.py`
- raw: logs/bilibili_001.txt
- key_facts (verbatim):
  - `target=https://www.bilibili.com/video/BV1RA4w6AE74`
  - `author=弧光猎人_ARCRaiders (mid=3546964469746014)`
  - `file=bilibili_BV1RA4w6AE74.mp4 size=29157708 res=1280x536`
  - `method=guest playurl(platform=html5,high_quality=1, qn=64)`
- conclusion: B站视频下载成功
- next: 下一平台: youtube
