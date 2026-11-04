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
`2026-11-03T18:47:01+08:00` **[youtube][discover]** ytsearch10:AI agent 命中 Zqno_vux6d8 dur=509s title=AI agents explained: Build your first agent in 8 minutes
`2026-11-03T18:47:04+08:00` **[youtube][fail]** yt-dlp -J 失败: ERROR: [youtube] Zqno_vux6d8: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extract

## [W013] 2026-11-03T18:47:04+08:00 | task=youtube-download | status=FAIL
- cmd: `python3 tools/dl_youtube.py`
- raw: logs/youtube_001.txt
- key_facts (verbatim):
  - `target=https://www.youtube.com/watch?v=Zqno_vux6d8`
  - `extractor_args=youtube:player_client=ios,web_safari`
  - `yt-dlp -J 失败: ERROR: [youtube] Zqno_vux6d8: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass `
- conclusion: yt-dlp 提取失败(疑似bot-check)
- next: 重试: --planb; 未探索: bgutil POT provider(node) / burner cookies
`2026-11-03T18:47:19+08:00` **[youtube][discover]** ytsearch10:AI agent 命中 EkdIZXDnRK8 dur=394s title=Context-Aware Coding: Give AI Agents the Right Context
`2026-11-03T18:47:21+08:00` **[youtube][fail]** yt-dlp -J 失败: ERROR: [youtube] EkdIZXDnRK8: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extract

## [W014] 2026-11-03T18:47:21+08:00 | task=youtube-download | status=FAIL
- cmd: `python3 tools/dl_youtube.py --planb`
- raw: logs/youtube_001.txt
- key_facts (verbatim):
  - `target=https://www.youtube.com/watch?v=EkdIZXDnRK8`
  - `extractor_args=youtube:player_client=web,android_vr,tv_downgraded`
  - `yt-dlp -J 失败: ERROR: [youtube] EkdIZXDnRK8: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass `
- conclusion: yt-dlp 提取失败(疑似bot-check)
- next: 重试: --planb; 未探索: bgutil POT provider(node) / burner cookies
`2026-11-03T18:47:38+08:00` **[x][extract]** yt-dlp formats=11 选定=best 高度=0

## [W015] 2026-11-03T18:47:41+08:00 | task=x-download | status=OK
- cmd: `python3 tools/dl_x.py`
- raw: logs/x_001.txt
- key_facts (verbatim):
  - `target=https://x.com/SpaceX/status/1806444569107865825`
  - `author=SpaceX (@SpaceX)`
  - `file=x_1806444569107865825.mp4 size=4331139 res=1920x1080`
  - `method=yt-dlp twitter extractor(游客) fmt=best`
- conclusion: X视频下载成功
- next: 下一平台: threads
`2026-11-03T18:48:59+08:00` **[threads][extract]** 插件 formats=4 选定=dash-17997862818103670v+dash-17997862773103670a 高度=1280 时长=95

## [W016] 2026-11-03T18:49:02+08:00 | task=threads-download | status=OK
- cmd: `python3 tools/dl_threads.py https://www.threads.com/@mosseri/post/De90Pbuk52l`
- raw: logs/threads_001.txt
- key_facts (verbatim):
  - `target=https://www.threads.com/@mosseri/post/De90Pbuk52l`
  - `author=Colin and Samir`
  - `file=threads_De90Pbuk52l.mp4 size=11940105 res=720x1280`
  - `method=yt-dlp-threads 插件(Googlebot SSR) fmt=dash-17997862818103670v+dash-17997862773103670a`
- conclusion: Threads视频下载成功
- next: 收尾: REPORT.md
`2026-11-03T18:49:20+08:00` **[douyin][resolve]** https://v.douyin.com/kcvMpuN/ -> https://www.iesdouyin.com/share/video/6915675899241450760/?region=CN&mid=6911453067020585735&u_code=j8a5173b&d
`2026-11-03T18:49:21+08:00` **[douyin][fail]** _ROUTER_DATA无item(删除/风控?) loaderData keys=['video_layout', 'video_(id)/page']

## [W017] 2026-11-03T18:49:21+08:00 | task=douyin-download | status=FAIL
- cmd: `python3 tools/dl_douyin.py https://v.douyin.com/kcvMpuN/`
- raw: logs/douyin_001.txt
- key_facts (verbatim):
  - `target=https://v.douyin.com/kcvMpuN/`
  - `_ROUTER_DATA无item(删除/风控?) loaderData keys=['video_layout', 'video_(id)/page']`
- conclusion: 失败
- next: 重试: --planb (yt-dlp)
`2026-11-03T18:50:02+08:00` **[douyin][fail]** yt-dlp -J 失败: ERROR: [Douyin] 7557764222948478251: Fresh cookies (not necessarily logged in) are needed

## [W018] 2026-11-03T18:50:02+08:00 | task=douyin-download | status=FAIL
- cmd: `python3 tools/dl_douyin.py https://www.douyin.com/video/7557764222948478251 --planb`
- raw: logs/douyin_001.txt
- key_facts (verbatim):
  - `target=https://www.douyin.com/video/7557764222948478251`
  - `yt-dlp -J 失败: ERROR: [Douyin] 7557764222948478251: Fresh cookies (not necessarily logged in) are needed`
- conclusion: 失败
- next: 未探索: TikTokDownloader(扫码) / playwright真浏览器
`2026-11-03T18:50:17+08:00` **[xiaohongshu][extract]** yt-dlp formats=4 选定=0 高度=1364

## [W019] 2026-11-03T18:50:21+08:00 | task=xiaohongshu-download | status=OK
- cmd: `python3 tools/dl_xhs.py`
- raw: logs/xiaohongshu_001.txt
- key_facts (verbatim):
  - `target=https://www.xiaohongshu.com/explore/6ae70cc2000000000602374d`
  - `author=None`
  - `file=xhs_6ae70cc2000000000602374d.mp4 size=7234489 res=720x1364`
  - `method=yt-dlp XiaoHongShu extractor(匿名) fmt=0`
- conclusion: 小红书视频下载成功
- next: 下一平台: douyin
`2026-11-03T20:07:40+08:00` **[material-search][warmup]** www.bilibili.com http=200 cookies=['buvid3', 'b_nut']
`2026-11-03T20:07:40+08:00` **[material-search][wbi]** key_len=32(前6=ea1db1…)
`2026-11-03T20:07:40+08:00` **[material-search][ok]** [万智牌 开卡] n=0 top3=
`2026-11-03T20:07:41+08:00` **[material-search][ok]** [万智牌 霍比特人] n=0 top3=
`2026-11-03T20:07:43+08:00` **[material-search][ok]** [孩之宝] n=20 top3=20年前第一部变形金刚电影的周边玩具(11:52s) | 终于等到他漫画造型的电影版了～Mar(3:21s) | 【搬运】英皇电影/孩之宝娱乐/华策影(1:8s)
`2026-11-03T20:07:44+08:00` **[material-search][ok]** [小猪佩奇 玩具] n=0 top3=
`2026-11-03T20:07:46+08:00` **[material-search][ok]** [变形金刚 玩具] n=20 top3=9.9块！机器恐龙大合体！金属变体红(3:6s) | 20年前第一部变形金刚电影的周边玩具(11:52s) | 变形金刚玩具动画：时空战记·机械英雄(s)
`2026-11-03T20:07:47+08:00` **[material-search][ok]** [万智牌 至尊魔戒] n=0 top3=
`2026-11-03T20:07:49+08:00` **[material-search][ok]** [小马宝莉] n=20 top3=【中配1080P】小马宝莉短片大合集(33:20s) | 【中文配音】小马宝莉特辑：彩虹之旅(59:5s) | 【小马宝莉】小马的故事就此开始了～（(20:17s)
`2026-11-03T20:07:50+08:00` **[material-search][ok]** [地产大亨 桌游] n=0 top3=
`2026-11-03T20:07:51+08:00` **[material-search][ok]** [万智牌 店赛] n=0 top3=
`2026-11-03T20:07:53+08:00` **[material-search][ok]** [万智牌 印刷] n=20 top3=【万智牌萌新指北】如何精准辨别日印(8:53s) | 体验独弈引擎的万智牌RPG，收集，组(20:7s) | 万智牌 万智牌美版印刷和日版印刷的区(7:41s)
`2026-11-03T20:07:54+08:00` **[material-search][ok]** [集装箱 港口] n=0 top3=
`2026-11-03T20:07:55+08:00` **[material-search][ok]** [特朗普 关税] n=0 top3=
`2026-11-03T20:07:57+08:00` **[material-search][done]** 落盘 /home/z/my-project/clock/1103-agent-downloader/materials/search_raw.json OK 12/12; fails=none
`2026-11-03T20:08:35+08:00` **[material-search][warmup]** www.bilibili.com http=200 cookies=['buvid3', 'b_nut']
`2026-11-03T20:08:35+08:00` **[material-search][wbi]** key_len=32(前6=ea1db1…)
`2026-11-03T20:08:36+08:00` **[material-search][ok]** [万智牌开卡] n=20 top3=万智牌北京聚光灯系列赛正赛直播回顾(826:27s) | 这不是so easy嘛！#万智牌 #(0:12s) | 拆卡实验3.0｜一盒万智牌最新最强最(33:39s)
`2026-11-03T20:08:39+08:00` **[material-search][ok]** [小猪佩奇] n=20 top3=佩奇的膝盖摔伤了！小猪佩奇故事全集(18:7s) | 小猪佩奇 全集合集 🎄圣诞特辑🎄下雪(26:58s) | （带动画版）小猪佩奇英文台词逐句影子(s)
`2026-11-03T20:08:41+08:00` **[material-search][ok]** [万智牌 魔戒] n=0 top3=
`2026-11-03T20:08:44+08:00` **[material-search][ok]** [万智牌 中土] n=0 top3=
`2026-11-03T20:08:46+08:00` **[material-search][ok]** [大富翁 桌游] n=0 top3=
`2026-11-03T20:08:49+08:00` **[material-search][ok]** [万智牌 比赛] n=0 top3=
`2026-11-03T20:08:52+08:00` **[material-search][ok]** [集装箱] n=0 top3=
`2026-11-03T20:08:54+08:00` **[material-search][ok]** [港口 吊装] n=0 top3=
`2026-11-03T20:08:57+08:00` **[material-search][ok]** [关税] n=20 top3=零关税，仅仅是药品名表便宜了吗？中国(3:50s) | 一口气了解关税(28:20s) | 6.8.2关税(46:22s)
`2026-11-03T20:09:00+08:00` **[material-search][ok]** [孩之宝 财报] n=0 top3=
`2026-11-03T20:09:02+08:00` **[material-search][done]** 落盘 /home/z/my-project/clock/1103-agent-downloader/materials/search_raw.json OK 10/10; fails=none
`2026-11-03T20:11:36+08:00` **[material-dl][fail]** S001 BV1oQdSY2EsV primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:36+08:00` **[material-dl][fail]** S002 BV1Wm421376H primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:38+08:00` **[material-dl][fail]** S002 fallback也失败: view code=-412 msg=request was banned
`2026-11-03T20:11:38+08:00` **[material-dl][fail]** S003 BV13rja6pEm2 primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:38+08:00` **[material-dl][fail]** S004 BV1Gd4y1Y7zt primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:38+08:00` **[material-dl][fail]** S005 BV11r4y1K7vo primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:38+08:00` **[material-dl][fail]** S006 BV1qJAGebEuX primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:40+08:00` **[material-dl][fail]** S006 fallback也失败: view code=-412 msg=request was banned
`2026-11-03T20:11:40+08:00` **[material-dl][fail]** S007 BV1NqL6z5EE1 primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:40+08:00` **[material-dl][fail]** S008 BV1jFCdYYELA primary失败: view code=-412 msg=request was banned
`2026-11-03T20:11:40+08:00` **[material-dl][fail]** S009 BV1NZxx6SEuH primary失败: view code=-412 msg=request was banned

## [W020] 2026-11-03T20:11:40+08:00 | task=material-download | status=PARTIAL
- cmd: `dl_materials.py (plan.json驱动)`
- raw: materials/materials.json
- key_facts (verbatim):
  - `001 BV1oQdSY2EsV fail -MB - primary`
  - `002 BV1Wm421376H fail -MB - primary`
  - `003 BV13rja6pEm2 fail -MB - primary`
  - `004 BV1Gd4y1Y7zt fail -MB - primary`
  - `005 BV11r4y1K7vo fail -MB - primary`
  - `006 BV1qJAGebEuX fail -MB - primary`
  - `007 BV1NqL6z5EE1 fail -MB - primary`
  - `008 BV1jFCdYYELA fail -MB - primary`
  - `009 BV1NZxx6SEuH fail -MB - primary`
- conclusion: 素材下载 0/9 ok, total 0MB
- next: 抽帧九宫格 → 大模型切题复判 → 分镜表
`2026-11-03T20:12:23+08:00` **[material-dl][playurl]** S001 BV1oQdSY2EsV parts=1 qn=64 预估5MB
`2026-11-03T20:12:43+08:00` **[material-dl][playurl]** S002 BV1Wm421376H parts=1 qn=64 预估285MB
`2026-11-03T20:15:06+08:00` **[material-dl][fail]** S002 BV1Wm421376H primary失败: ('Connection broken: IncompleteRead(13372920 bytes read, 271581383 more expected)', IncompleteRead(13372920 bytes read, 271581383 more expected))
`2026-11-03T20:15:09+08:00` **[material-dl][playurl]** S002 BV1ETnZ6jEhj parts=1 qn=64 预估34MB
`2026-11-03T20:17:24+08:00` **[material-dl][badpack]** S002 attempt1 Enter command: <target>|all <time>|-1 <command>[ <argument>] 
`2026-11-03T20:17:38+08:00` **[material-dl][badpack]** S002 attempt2 Enter command: <target>|all <time>|-1 <command>[ <argument>] 
`2026-11-03T20:17:38+08:00` **[material-dl][fail]** S002 fallback也失败: 两次体检均坏包
`2026-11-03T20:17:38+08:00` **[material-dl][playurl]** S003 BV13rja6pEm2 parts=1 qn=64 预估103MB
`2026-11-03T20:20:13+08:00` **[material-dl][badpack]** S003 attempt1 [null @ 0x5616328d5e80] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 1199 >= 1199 [null @ 0x5616328d5e80] Appl
`2026-11-03T20:20:50+08:00` **[material-dl][badpack]** S003 attempt2 [null @ 0x55a63bc34e80] Application provided invalid, non monotonically increasing dts to muxer in stream 0: 1199 >= 1199 [null @ 0x55a63bc34e80] Appl
`2026-11-03T20:20:50+08:00` **[material-dl][fail]** S003 BV13rja6pEm2 primary失败: 两次体检均坏包
`2026-11-03T20:20:50+08:00` **[material-dl][playurl]** S004 BV1Gd4y1Y7zt parts=1 qn=80 预估455MB
`2026-11-03T20:23:54+08:00` **[material-dl][fail]** S002 BV1Wm421376H primary失败: too many values to unpack (expected 2)
`2026-11-03T20:24:04+08:00` **[material-dl][clean]** 删除残留 S002_bili_BV1Wm421376H.mp4
`2026-11-03T20:24:39+08:00` **[material-dl][fail]** S004 BV1Gd4y1Y7zt primary失败: too many values to unpack (expected 2)
`2026-11-03T20:24:39+08:00` **[material-dl][fail]** S005 BV11r4y1K7vo primary失败: too many values to unpack (expected 2)
`2026-11-03T20:24:39+08:00` **[material-dl][fail]** S006 BV1qJAGebEuX primary失败: too many values to unpack (expected 2)
`2026-11-03T20:24:41+08:00` **[material-dl][fail]** S006 fallback也失败: too many values to unpack (expected 2)
`2026-11-03T20:24:41+08:00` **[material-dl][fail]** S007 BV1NqL6z5EE1 primary失败: too many values to unpack (expected 2)
`2026-11-03T20:24:41+08:00` **[material-dl][fail]** S008 BV1jFCdYYELA primary失败: too many values to unpack (expected 2)
`2026-11-03T20:24:41+08:00` **[material-dl][fail]** S009 BV1NZxx6SEuH primary失败: too many values to unpack (expected 2)
`2026-11-03T20:35:31+08:00` **[material-dl][playurl]** S002 BV1Wm421376H parts=1 qn=16 预估87MB 期望时长2019s
`2026-11-03T20:40:42+08:00` **[material-dl][clean]** 删除残留 S002_bili_BV1ETnZ6jEhj.mp4
`2026-11-03T20:40:43+08:00` **[material-dl][grid]** S002 重做九宫格(文件更新)
`2026-11-03T20:41:15+08:00` **[material-dl][playurl]** S004 BV1Gd4y1Y7zt parts=1 qn=16 预估71MB 期望时长485s
`2026-11-03T20:43:04+08:00` **[material-dl][badpack]** S004 attempt1: 时长残缺 1906s≠485s
`2026-11-03T20:43:10+08:00` **[material-dl][badpack]** S004 attempt2: 时长残缺 1906s≠485s
`2026-11-03T20:43:10+08:00` **[material-dl][fail]** S004 BV1Gd4y1Y7zt primary失败: 两次体检均失败: 时长残缺 1906s≠485s
`2026-11-03T20:43:10+08:00` **[material-dl][playurl]** S005 BV11r4y1K7vo parts=1 qn=80 预估170MB 期望时长461s
`2026-11-03T20:47:43+08:00` **[material-dl][playurl]** S005 BV11r4y1K7vo parts=1 qn=80 预估170MB 分P时长461s(plan记461s)
`2026-11-03T20:51:33+08:00` **[material-dl][playurl]** S006 BV1qJAGebEuX parts=1 qn=64 预估174MB 分P时长1700s(plan记1700s)
`2026-11-03T20:53:48+08:00` **[material-dl][playurl]** S007 BV1NqL6z5EE1 parts=1 qn=64 预估15MB 分P时长151s(plan记1217s)
`2026-11-03T20:55:01+08:00` **[material-dl][fail]** S007 BV1NqL6z5EE1 primary失败: ('Connection broken: IncompleteRead(6954487 bytes read, 7784991 more expected)', IncompleteRead(6954487 bytes read, 7784991 more expected))
`2026-11-03T20:55:01+08:00` **[material-dl][playurl]** S008 BV1jFCdYYELA parts=1 qn=32 预估9MB 分P时长1087s(plan记1087s)
`2026-11-03T20:55:04+08:00` **[material-dl][badpack]** S008 attempt1: 时长残缺 180s≠1087s
`2026-11-03T20:55:05+08:00` **[material-dl][badpack]** S008 attempt2: 时长残缺 180s≠1087s
`2026-11-03T20:55:05+08:00` **[material-dl][fail]** S008 BV1jFCdYYELA primary失败: 两次体检均失败: 时长残缺 180s≠1087s
`2026-11-03T20:55:05+08:00` **[material-dl][playurl]** S009 BV1NZxx6SEuH parts=1 qn=64 预估92MB 分P时长712s(plan记712s)
`2026-11-03T21:00:17+08:00` **[material-dl][playurl]** S007 BV1NqL6z5EE1 parts=1 qn=64 预估15MB 分P时长151s(plan记1217s)
`2026-11-03T21:00:49+08:00` **[material-dl][playurl]** S008 BV1jFCdYYELA parts=1 qn=32 预估9MB 分P时长1087s(plan记1087s)
`2026-11-03T21:00:50+08:00` **[material-dl][badpack]** S008 attempt1: 时长残缺 180s≠1087s
`2026-11-03T21:00:52+08:00` **[material-dl][badpack]** S008 attempt2: 时长残缺 180s≠1087s
`2026-11-03T21:00:52+08:00` **[material-dl][fail]** S008 BV1jFCdYYELA primary失败: 两次体检均失败: 时长残缺 180s≠1087s
`2026-11-03T21:00:54+08:00` **[material-dl][fail]** S008 yt-dlp兕底也失败: [Errno 2] No such file or directory: '/home/z/.venv/bin/yt-dlp'
`2026-11-03T21:00:54+08:00` **[material-dl][playurl]** S009 BV1NZxx6SEuH parts=1 qn=64 预估92MB 分P时长712s(plan记712s)
`2026-11-03T21:10:55+08:00` **[material-dl][playurl]** S008 BV1jFCdYYELA parts=1 qn=32 预估9MB 分P时长1087s(plan记1087s)
`2026-11-03T21:10:56+08:00` **[material-dl][badpack]** S008 attempt1: 时长残缺 180s≠1087s
`2026-11-03T21:10:57+08:00` **[material-dl][badpack]** S008 attempt2: 时长残缺 180s≠1087s
`2026-11-03T21:10:57+08:00` **[material-dl][fail]** S008 BV1jFCdYYELA primary失败: 两次体检均失败: 时长残缺 180s≠1087s
`2026-11-03T21:11:00+08:00` **[material-dl][fail]** S008 yt-dlp兕底也失败: yt-dlp -J 失败: ERROR: [BiliBili] 1jFCdYYELA: Unable to download webpage: HTTP Error 412: Precondition Failed (caused by <HTTPError 412: Precondition Fa

## [W021] 2026-11-03T21:21:47+08:00 | task=material-search | status=OK
- cmd: `search_bilibili.py 两轮12+10词`
- raw: materials/search_raw.json
- key_facts (verbatim):
  - `首轮: 孩之宝/变形金刚 玩具/小马宝莉/万智牌 印刷 命中; 8词空result(code=0)`
  - `重试词面(仅此一次换法): 万智牌开卡/小猪佩奇/关税 命中; 万智牌 魔戒/中土、大富翁 桌游、集装箱、港口 吊装、孩之宝 财报 仍空(长尾软拦截)`
  - `通路: 游客wbi search(bilibili.com预热buvid3+nav取wbi_img+md5签名), 间隔1.2/2.5s`
- conclusion: 素材搜索通路固化: B站唯一可自搜平台; 7/22词面命中
- next: 大模型按标题/播放量切题选定9条+2fallback

## [W022] 2026-11-03T21:21:47+08:00 | task=material-download | status=OK(8ok+1partial)
- cmd: `dl_materials.py(plan.json驱动, 幂等续跑5段)`
- raw: materials/materials.json
- key_facts (verbatim):
  - `9条落位: S001 4.6MB/S002 86.7MB(qn16降档)/S003 103.1MB/S004 71.2MB/S005 170.5MB/S006 174.0MB/S007 14.7MB/S008 partial(试看钳制180s)/S009 91.6MB, 共724MB`
  - `管线修复3次: view412→pagelist取cid(B29); 搜索duration失真→pagelist分P时长(B30); IncompleteRead纳入attempt重试`
  - `B31实测: S008 durl声称1087s/9MB实际前180s, yt-dlp对B站412(坑B6原文命中); B32实测: 沙盒重启venv丢yt-dlp, 重装恢复`
  - `>100MB三条(S003/S005/S006) split 90m 分卷+md5.txt(B33)`
- conclusion: 素材轮下载完成, 编号S001-S009存档materials/clips/
- next: VLM九宫格复判

## [W023] 2026-11-03T21:21:47+08:00 | task=material-vlm | status=OK
- cmd: `vlm_grids.py(z-ai vision CLI) × 9宫格`
- raw: materials/vlm/S00x.json
- key_facts (verbatim):
  - `S001-S006/S009 给出CLIP推荐秒段; S007/S008 判NONE(动画画面与财经B-roll语境不符)但保留为IP主题展示画面`
  - `S006 内含港口/货运画面(510-680s/850-1019s), 覆盖文案13供应链空缺`
- conclusion: 分镜表14镜头定稿(materials/materials.md §三), 素材未切割仅标用法
- next: 文档/materials.md/findings/03追加/worklog/state更新→单次push

---
## Round 2 — 2026-11-04 微博+小红书「搜索→下载」链路攻坚
任务: 跑通两家搜索到下载单条视频持续链路, 固化为不烧token方案。免费优先 > 本地浏览器cookies/MCP浏览器 > 付费。CF Worker/GH Actions 免费中转为期望最佳形态(但无详细外部指南不自行摸索)。CF token 已存 .secrets/cf_token。
上轮已知: 微博容器API ok=-100(要JS级访客cookie), 单视频下载畅通; 小红书搜索需登录+签名, 单视频(xsec_token链接)下载畅通, agent-browser未试过。

### Round 2 工作记录 (W101-W112)
- **W101 微博genvisitor2探针✅**: passport.weibo.com/visitor/genvisitor2 纯HTTP POST(cb/tid/from=weibo/webdriver=false, 教程原参数) → retcode=20000000 拿到访客SUB(94字符, 教程写死tid竟可复用); 带SUB调 weibo.com/ajax/feed/hottimeline → ok:1真实statuses! **微博"发现"层解锁** (logs/wb_search_probe.json)
- **W102 m.weibo.cn纯HTTP死路确认**: 首页GET只种WEIBOCN_FROM不种SUB, 容器API仍ok=-100 — 上轮结论"JS级访客cookie"复核成立, 不再重试
- **W103 weibo.com域搜索404×2**: /ajax/search/all、/ajax/statuses/searchall 均404(猜测路径不存在); s.weibo.com/ajax/statuses/search 返回{code,msg,data}非ok结构未细究; **热搜榜 weibo.com/ajax/side/hotSearch 游客可用(ok:1)** (logs/wb_search_probe3.json)
- **W104 微博搜索攻破🎉**: agent-browser真浏览器 open m.weibo.cn → 自动完成"新浪访客系统"护照(visitor.passport.weibo.cn/visitor/visitor?entry=sinawap, JS级) → 页面内eval fetch容器搜索API → **15条真实结果含视频标记**, 马保国本人视频在内; 游客cookie(SUBP/MLOGIN/_T_WM/XSRF-TOKEN)自动种下 (scripts/wb_browser_search.sh)
- **W105 小红书RedCrack游客471**: mankezhou/RedCrack(MIT, 纯Python逆向全参数) guest session创建时 as.xiaohongshu.com/api/sec/v1/shield/webprofile 返回471 → 461异常 — **数据中心IP+游客指纹被安全接口拦**, 与其skill文档预警一致; 注意: RedCrack的config.py用相对路径, 必须cwd=仓库根目录运行
- **W106 小红书页面级IP风控**: agent-browser开 www.xiaohongshu.com 直接重定向 www.rednote.com(国际版, 香港IP判定); 搜索页被拦到 /website-login/error **error_code=300012 "IP at risk"**; 但 edith.xiaohongshu.com/api/sns/web/v1/search/recommend XHR 200(API层未全封)
- **W107 rednote国际版登录墙**: rednote.com/search_result?keyword=页面正常打开(title=关键词-rednote search, 无IP风控页)但渲染 "Log in to view search results" 登录墙, 游客0结果
- **W108 小红书游客搜索终判**: rednote.com页面 eval window._webmsxyw(存在,function)签名 + fetch POST edith.../search/notes → **HTTP200签名有效但 code:-101 "无登录信息，或登录信息为空"** → 搜索API硬性要求登录态。至此游客三路(RedCrack纯Python/页面级/API签名直调)全灭, **web_session cookie是唯一钥匙**, 与XHS-Downloader/MediaCrawler文档一致
- **W109 微博全链路固化实测✅**: scripts/weibo_search_download.py "孩之宝 万智牌" → 搜索命中睿卡潮玩万智牌王者之战赛事混剪(视频标记) → statuses/show拿直链 → curl下载 **1280x720 13.8MB**, ffprobe体检通过, meta.json含完整来源信息 → downloads/weibo/search_孩之宝 万智牌/
- **W110 小红书固化脚本就绪(待cookie)**: scripts/xhs_search_download.py — 读.secrets/cookies/xiaohongshu_web_session.txt → 搜索URL被300012拦到website-login/error页(恰好保持xiaohongshu.com域, 正好种cookie) → 重新open搜索页 → 抽explore链接(note_id+xsec_token) → yt-dlp下载(上轮已通通路); 无cookie时打印获取指引退出
- **W111 CF Worker决策**: 调研(web search×7)未发现"小红书/微博搜索下载中转"的**指南级**开源项目(只有泛CF-Worker代理教程) — 按用户规则"没有详细外部指南就不自行摸索"→ **未部署**; cf token已存.secrets/cf_token备用(600权限)
- **W112 中转形态评估**: ①GitHub Actions runner=Azure数据中心IP, 对小红书IP风控无解, 仅cookie可存Secrets(沙盒.secrets等效); ②CF Worker出口同为数据中心IP同理; ③微博沙盒直连已通无需中转 → **中转边际价值=仅'服务常驻'(沙盒重置不丢), 但脚本已全部入库GitHub, 重建=git clone, 中转非必需** → 记录不实施
