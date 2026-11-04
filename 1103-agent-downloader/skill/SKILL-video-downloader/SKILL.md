---
name: video-downloader
description: 从 YouTube/X(推特)/Threads/微博/抖音/小红书/B站搜索并下载视频，提取来源URL、作者、标题等元信息；含围墙花园平台的内容自发现策略（微博/小红书搜索链路已实测跑通）。当用户要求"搜索并下载某平台视频/下载这个视频/抓视频元数据/批量转存群聊或社媒视频"，或问"哪些平台你能自己搜到内容"时使用。
---

# 多平台视频搜索与下载（2026-11 实测版）

沙盒环境：香港/海外数据中心 IP、无 GFW、有 /home/z/.venv（yt-dlp 2026.10.26 + gallery-dl）、ffmpeg/ffprobe 预装、agent-browser CLI 预装。
本技能所有结论均为 2026-11-03/04 实测，完整证据链见 GitHub lishuhang/clock `1103-agent-downloader/`（REPORT.md / worklog W009-W023+R2 / scripts/）。

## 执行步骤

### 1. 环境自检（30 秒）
```bash
/home/z/.venv/bin/yt-dlp --version   # 必须 ≥ 2026.09，旧版 YouTube 必挂（nsig）；沙盒重置后重装: /home/z/.venv/bin/pip install yt-dlp
ffprobe -version | head -1           # 合并与体检用
agent-browser --help | head -1       # 微博/小红书搜索链路依赖（预装）
```
Threads 需先装插件：`/home/z/.venv/bin/pip install git+https://github.com/tribixbite/yt-dlp-threads`，验证 `yt-dlp --verbose <url> 2>&1 | grep "Extractor Plugins"` 出现 `ThreadsIE`。

### 2. 按平台选通路（优先级从上到下，每平台失败最多换法 1 次）

| 平台 | 首选（实测✅） | 换法重试 | 仍失败则停 |
|------|--------------|---------|-----------|
| X | `yt-dlp "https://x.com/<user>/status/<id>"` 游客免cookie | api.fxtwitter.com/<user>/status/<id> 拿元数据 + video.twimg.com 直链拿文件 | 列为待用户提供 auth_token |
| B站 | 免登录 `api.bilibili.com/x/player/playurl?bvid=&cid=&qn=80&platform=html5&high_quality=1` → durl[0].url 直接是 720p 档 mp4（带 Referer:https://www.bilibili.com/ 下载） | `yt-dlp` 免登录 480p | 1080p+ 必须用户给 SESSDATA，不要硬闯 |
| Threads | `yt-dlp "https://www.threads.com/@<user>/post/<code>"`（插件, Googlebot SSR） | curl -A "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" 抓帖子页, 正则 `"video_versions":(\[.*?\])` | 仅公开帖可下 |
| 小红书 | 必须用户给**带 xsec_token 的分享链**（App 或 PC 网页分享按钮复制），`yt-dlp "<链接>"` 匿名档 720p；**搜索见 §3c（需 cookie）** | 解析页面 `window.__INITIAL_STATE__`（replace undefined→null）递归找 masterUrl | 地址栏 URL 永远不可用 |
| 微博 | `yt-dlp "https://weibo.com/<uid>/<bid>"` 单视频游客通路畅通（自动游客cookie, 最高4K）；**搜索见 §3b** | m.weibo.cn API stream_url_hd 直下 | "列用户时间线"类需求见坑1 |
| YouTube | `yt-dlp --extractor-args "youtube:player_client=ios,web_safari"` | 换 client=web,android_vr,tv_downgraded（大概率同样失败） | bot-check=IP级, 对症解是 bgutil POT provider(node版) 或 burner cookies, 部署前先问用户 |
| 抖音 | （2026-11 起两条免登录通路均已死）yt-dlp 报 Fresh cookies needed | 构造 ttwid: POST ttwid.bytedance.com/ttwid/union/register/ 后带 cookie 重试 | TikTokDownloader 扫码登录 / playwright 真浏览器 / 用户给cookie |

### 3. 内容自发现（"自己去搜"时的策略）
- **脚本化可搜索（已固化，零token）**：
  - B站：wbi 签名搜索（`x/web-interface/wbi/search/type`，素材轮已固化）或热门榜 `x/web-interface/popular`
  - **微博：§3b 链路，免登录**
  - **小红书：§3c 链路，需用户 cookie（一次性给，长期有效）**
  - YouTube：`yt-dlp "ytsearch10:<关键词>"`（发现可用≠能下载）
  - Threads：Googlebot UA 抓 `threads.com/@<user>` 主页 SSR → 正则 `"code":"([A-Za-z0-9_-]{6,25})"` 抽帖子 code → 插件 --simulate 逐个验证带视频（本技能原创方法）
- **搜索引擎转引**：X 用 WebSearch 查 `"x.com/<user>/status"`，新闻/论坛/Lemmy/豆瓣帖常原文转贴链接，甚至附 video.twimg.com CDN 直链
- **必须用户给料**：抖音（转引收录极差+站内搜索要 a_bogus 签名+分享页 SSR 已收壳）

### 3b. 微博「搜索→下载」链路（免登录/免cookie/零token，2026-11-04 实测✅）
```bash
python3 scripts/weibo_search_download.py "<关键词>"   # 产出 weibo_<mid>.mp4 + meta.json
```
链路：agent-browser `open https://m.weibo.cn/` → 浏览器自动走完"新浪访客系统"JS护照（纯HTTP永远拿不到这层cookie）→ 页面内 `eval` fetch 容器搜索API `/api/container/getIndex?containerid=100103type%3D1%26q%3D<kw>&page_type=searchall` → mblog 列表（page_info.media_info 判视频）→ `/statuses/show?id=<mid>` 拿 playback_list 直链 → curl 带 `Referer: https://m.weibo.cn/` 下载。实测：`孩之宝 万智牌` → 睢卡潮玩赛事混剪 1280x720 13.8MB。
附带：纯HTTP `passport.weibo.com/visitor/genvisitor2`（POST cb/tid/from=weibo/webdriver=false，教程tid可复用）拿访客SUB → 可通 `weibo.com/ajax/feed/hottimeline`（热门流）与 `/ajax/side/hotSearch`（热搜榜），但搜索仅浏览器内可行。

### 3c. 小红书「搜索→下载」链路（需全量cookie，2026-11-04 实测✅）
```bash
python3 scripts/xhs_search_download_v3.py "<关键词>"   # 产出 xhs_<note_id>.mp4 + meta.json
```
前置：用户给 Netscape 格式全量 cookie（至少 `web_session`+`a1`，导出：浏览器登录 xiaohongshu.com → F12 → Application → Cookies → 复制关键项），存 `/home/z/my-project/.secrets/cookies/xiaohongshu_cookies.txt`。
链路：Netscape → Playwright storage state 转换 → `agent-browser state load`（**web_session 是 httpOnly，document.cookie 种不进，必须 state load**）→ open 搜索页 `search_result?keyword=<kw>` → **点UI「筛选→视频」**（纯点击不碰签名，比 API 直调稳）→ 抽 `a[href*=search_result]` 的 xsec_token 链接 → `yt-dlp --cookies <文件>` 下载。实测：`万智牌`/`孩之宝` 双关键词均通，720x1280。
⚠ 游客搜索不可行（三层实测全灭：RedCrack纯Python=shield 471 / 页面=300012 IP风险或登录墙 / _webmsxyw签名直调=HTTP200但-101无登录信息）；⚠ eval 直调 v1 search API 会触发 `300011 Account abnormal`（页面自身走 so.xiaohongshu.com v2 API 且带全套头），别直调，用UI筛选。

### 4. 产出规范
- 每视频落盘 meta.json：source_url / author / title / summary(≤500字) / publish_time / duration / resolution / size / method / discover
- 下载后必检：`ffprobe -v error -show_entries format=duration,size -of csv <file>`（尺寸时长正常、文件非空）
- 格式选择：优先 ≤1080p 且 ≤90MB（GitHub 100MB 硬限制）；用 yt-dlp -J 先取 formats 再程序化选（filesize 缺失时用 tbr×duration/8 估算）

### 5. 工作延续（长任务防崩）
- 结构化留痕：worklog.md 追加 W 条目（报错**逐字**摘录，禁止概括失真）；原始输出进 logs/
- 每完成一个平台立即 commit+push（脚本 gh_sync.sh）
- 大仓库（GB级）只许 `git clone --depth 1 --filter=blob:none --sparse`

## 质量标准
- 每平台脚本最后一行输出 `RESULT[平台] OK/FAIL: <文件> <大小> <分辨率> <作者>`，对话只看这一行
- 失败先 `tail -30` 原始日志、对照踩坑表，再决定换法；**bot-check 类错误换 client 重试基本无效，不要连试**
- 用户规定重试预算（如"最多换法1次"）时严格执行，未走通的路径写入报告"未探索"节，不穷尽尝试

## 踩坑记录（全部实测踩过）
1. **微博"列时间线"已上访客墙**：m.weibo.cn 容器 API 返回 `ok=-100`（HTTP 200 假成功）；yt-dlp WeiboUser 重定向 `passport.weibo.cn/visitor/visitor?entry=sinawap` 拿 0 条。但**单视频 URL 提取不受影响**——用搜索引擎转引拿具体 URL 即可绕过。
2. **B站免登录不止 480p**：`platform=html5&high_quality=1` 的 playurl 仍给 720p 档（qn=64）mp4 单文件；"免登录仅480p"的旧结论已过时。
3. **YouTube 数据中心 IP = bot-check**：`Sign in to confirm you're not a bot` 在 ios/web_safari 和 web/android_vr/tv_downgraded 两组合下同样出现；ytsearch（发现）不受影响。对症解是 PO token（bgutil）或 cookies，不是换 client。
4. **抖音 iesdouyin 分享页 SSR 已收壳（2026-11 实测）**：`_ROUTER_DATA` 只剩 loaderData 页面元信息（ua/isSpider/webId），aweme_id/desc/play_addr 出现 0 次——旧教程的"分享页免登录拿 play_addr"全部失效；`playwm→play`、`ratio=default` 参数仍有效但前提是先拿到 item 数据。
5. **小红书 yt-dlp 不返回 uploader**，作者名要从用户分享文案补全并标注来源；地址栏 URL 不带 xsec_token，必死。
6. **Threads 主页 SSR 的 `video_versions` 是空壳**（width/height/url 全 null），只能用来定位帖子 code，视频数据要进帖子页拿。
7. **curl -w 格式串不能以 @ 开头**（会被当文件路径），用 `[xxx]` 前缀。
8. **ffmpeg 全量解码体检（-f null）对多文件会超时**，日常用 ffprobe 快检，全量解码留给单文件排障。
9. **WebSearch 对 v.douyin.com / threads.net 帖子级 URL 收录≈0**，别在"搜短链"上浪费轮次，直接想转引源（Lemmy/豆瓣/工具文档示例/新闻稿引注）。
10. **yt-dlp 选格式时 filesize 常为 null**，必须用 tbr×duration/8 兜底估算，否则大文件（微博4K/B站长视频）会撑爆 GitHub 100MB 限制。
11. **小红书 httpOnly cookie（web_session/id_token）用 document.cookie 种不进**，必须转 Playwright storage state 后 `agent-browser state load`；全量 cookie（含 a1 设备指纹）比单 web_session 成功率高。
12. **小红书 eval 直调 v1 搜索 API（edith.../api/sns/web/v1/search/notes）即使签名正确也会 300011 Account abnormal**；页面自身走 so.xiaohongshu.com v2 API。要视频筛选就用 UI「筛选→视频」，不要碰 API。
13. **小红书游客搜索是死路**（三层实测：RedCrack 471 / 页面 300012+登录墙 / API -101），别再试免登录方案；海外 IP 打开 xiaohongshu.com 会重定向 rednote.com（国际版），其页面 `window._webmsxyw` 签名函数与国内版同源可用。
14. **微博 m.weibo.cn 容器 API 的 "JS级访客cookie" 必须真浏览器**：agent-browser open 后自动完成访客护照，之后页面内 fetch 全通；纯 HTTP（genvisitor2 SUB）只通 weibo.com 域的热门流/热搜，不通搜索。
15. **agent-browser eval 返回 JSON 字符串是双层引号包裹**，解析循环两次 json.loads（见 weibo_search_download.py 的 ab_eval）；eval 里的 IIFE 注意 JSON.stringify(...) 整体括号闭合。
16. **沙盒重置会丢 /home/z/.venv 里的包**，脚本启动前检查 yt-dlp 存在性，缺则 `pip install yt-dlp`（版本要 ≥2026.09）。
