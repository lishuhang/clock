#!/usr/bin/env python3
# 汇总 downloads/*/meta.json → REPORT.md (最终交付文档)
import json, os

WORK = "/home/z/my-project/clock/1103-agent-downloader"
ORDER = ["youtube", "x", "threads", "weibo", "douyin", "xiaohongshu", "bilibili"]
CN = {"youtube": "YouTube", "x": "X (推特)", "threads": "Threads", "weibo": "微博",
      "douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "哔哩哔哩"}

def load(p):
    f = f"{WORK}/downloads/{p}/meta.json"
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else None

metas = {p: load(p) for p in ORDER}

R = []
R.append("# REPORT — 多平台视频下载实抓报告")
R.append("")
R.append("> 任务时间: 2026-11-03 (Asia/Hong_Kong) | 执行环境: 香港阿里云沙盒 (Debian 13, Python 3.12.16, yt-dlp 2026.10.26, ffmpeg 7.1.5)")
R.append("> 任务规则(用户指定): 每平台 1 条、尽可能高清晰度; **失败后最多换方式重试 1 次**, 未探索路径只记录不穷尽; 过程忠实留痕 (worklog.md W009-W021, logs/)")
R.append("> 本轮范围: 除 Instagram 外的 7 平台 (Instagram 用户已豁免)")
R.append("")
R.append("## 1. 结果总表")
R.append("")
R.append("| # | 平台 | 状态 | 文件 | 分辨率 | 时长 | 大小 | 作者 | 方法 |")
R.append("|---|------|------|------|--------|------|------|------|------|")
for i, p in enumerate(ORDER, 1):
    m = metas[p]
    if m:
        sz = m["size_bytes"] / 1e6
        R.append(f"| {i} | {CN[p]} | ✅ | `{m['file']}` | {m['resolution']} | {m.get('duration_sec') or '-'}s | {sz:.1f}MB | {str(m.get('author'))[:24]} | {m['method'].split(' fmt')[0][:44]} |")
    else:
        R.append(f"| {i} | {CN[p]} | ❌ | - | - | - | - | - | 两法用尽, 见§3/§4 |")
R.append("")
R.append("**成绩: 5/7 平台成功** (YouTube、抖音失败, 均为平台侧反爬, 非网络问题——16/16 域名网络层全通, 见 W002)。")
R.append("所有文件 ffprobe 体检通过 (h264+aac, 尺寸/时长/大小正常, 见 W021)。")
R.append("")
R.append("## 2. 各平台视频详情 (元信息)")
R.append("")
for p in ORDER:
    m = metas[p]
    R.append(f"### 2.{ORDER.index(p)+1} {CN[p]} {'✅' if m else '❌'}")
    R.append("")
    if not m:
        R.append("下载未成功, 失败详情见 §3, 未探索路径见 §4。")
        R.append("")
        continue
    R.append(f"- **来源 URL**: {m.get('source_url')}")
    if m.get("source_url_canonical"):
        R.append(f"- **规范 URL**: {m.get('source_url_canonical')}")
    if m.get("source_url_share"):
        R.append(f"- **分享短链**: {m.get('source_url_share')}")
    R.append(f"- **作者**: {m.get('author')}")
    R.append(f"- **标题**: {m.get('title')}")
    summary = str(m.get("summary") or "(无)")
    R.append(f"- **摘要**: {summary[:300]}{'…' if len(summary) > 300 else ''}")
    if m.get("publish_time"):
        R.append(f"- **发布时间**: {m.get('publish_time')}")
    if m.get("duration_sec"):
        R.append(f"- **时长**: {m.get('duration_sec')}s")
    R.append(f"- **分辨率**: {m.get('resolution')} | **大小**: {m['size_bytes']:,} B ({m['size_bytes']/1e6:.1f}MB)")
    if m.get("stats"):
        st = {k: v for k, v in m["stats"].items() if v is not None}
        if st:
            R.append(f"- **互动数据**: {st}")
    if m.get("view_count") or m.get("like_count"):
        R.append(f"- **播放/点赞**: view={m.get('view_count')} like={m.get('like_count')}")
    R.append(f"- **下载方法**: {m.get('method')}")
    R.append(f"- **内容发现方式**: {m.get('discover')}")
    if m.get("note"):
        R.append(f"- **备注**: {m.get('note')}")
    R.append("")
R.append("## 3. 遇到的问题 (忠实记录, 报错逐字摘录)")
R.append("")
R.append("### 3.1 微博 — 自发现两连败, 下载通路一次过")
R.append("- **方案A失败**: `m.weibo.cn/api/container/getIndex` 四次请求(央视新闻/人民日报×2页)全部返回 `ok=-100` (HTTP 200)。该 API 现在要求 JS 级访客 cookie, 纯 requests 拿不到。")
R.append("- **方案B首败**: yt-dlp `WeiboUser` extractor 列用户视频返回 **0 条**, 重定向链落在 `passport.weibo.cn/visitor/visitor?entry=sinawap&...` (访客护照流程, 无 JS 无法走通)。")
R.append("- **破局**: 改从搜索引擎拿到具体视频 URL (央视新闻 2026 马年春晚周深祝福微博), yt-dlp `Weibo` extractor(游客) 一次成功 → 说明**单视频提取没有风控墙, 墙在'列用户时间线'这一步**。")
R.append("- 画质 540x960 为该竖屏视频游客档最高可用档。")
R.append("")
R.append("### 3.2 哔哩哔哩 — html5 探针超预期 (修正上轮调研结论)")
R.append("- 免登录 `playurl?platform=html5&high_quality=1` 直接返回 **qn=64 (720p 档) mp4 单文件**, 无需合并。")
R.append("- **修正 findings/02 §8 结论**: 上轮调研(zhipeng 笔记)称免登录仅 480x640; 实测 html5 参数仍可拿 720p 档(本视频为 2.39:1 电影宽幅, 故 1280x536)。yt-dlp 免登录路径未再启用(html5 已够)。")
R.append("- 未用 SESSDATA, 1080p 档未尝试(见 §4)。")
R.append("")
R.append("### 3.3 YouTube — 两法均死于数据中心 IP bot-check")
R.append("- 发现环节 `ytsearch10:AI agent` 正常(证明搜索可用), 但播放器提取两次失败, 报错逐字:")
R.append("  - 方案A `player_client=ios,web_safari`: `ERROR: [youtube] Zqno_vux6d8: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.`")
R.append("  - 方案B(换法重试) `player_client=web,android_vr,tv_downgraded`: 同样报错(视频不同: EkdIZXDnRK8)。")
R.append("- 与 findings/03 B1 预判完全一致: 本沙盒出口=香港阿里云(数据中心 IP), bot-check 类失败换 client 重试基本无效(bigiron 分诊法明示), 按'最多重试1次'规则止损。")
R.append("")
R.append("### 3.4 抖音 — 两条通路 2026 年均已被收紧")
R.append("- **方案A失败(结构性)**: iesdouyin 分享页 `window._ROUTER_DATA` 现在只回**壳数据**(loaderData 里仅页面元信息: ua/isSpider/webId/renderInSSR), `aweme_id`/`desc`/`play_addr` 出现次数=0。上轮调研时该通路(zhipeng 笔记)可免登录拿 4K60——**已被字节收紧**。逐字: `_ROUTER_DATA无item(删除/风控?) loaderData keys=['video_layout', 'video_(id)/page']`")
R.append("  - 三个目标交叉验证排除'目标已删'解释: 2021 示例视频(6915675899241450760)、2024 示例(7604129988555574538)、央视新闻 2025 中秋MV(7557764222948478251, 短链 302 正常)三者的分享页 SSR 全部无 item 数据。")
R.append("- **方案B失败(如预判)**: yt-dlp 内置 Douyin extractor 报 `Fresh cookies (not necessarily logged in) are needed` (findings/03 B13 原文复现, a_bogus 签名墙)。")
R.append("- 结论: 抖音反爬为本轮唯一**结构性失败**平台, 与用户既往经验(WorkBuddy 案例)一致。")
R.append("")
R.append("### 3.5 X / Threads / 小红书 — 一次过, 各有一个可复用新知")
R.append("- **X**: yt-dlp twitter extractor 游客免 cookie 直接拿下 SpaceX 官方推文 1920x1080。新知: **搜索引擎结果页里常留有 video.twimg.com 的 CDN 直链**(本次 Lemmy 帖留档了 1080p 直链), 是现成的 B 方案备份(未启用)。")
R.append("- **Threads**: 官方搜索/主页对游客有登录墙, 但 **Googlebot UA 抓 `threads.com/@user` 主页会 SSR 出近期帖子的 code 列表**(本次从 @mosseri 主页抽到 8 个 code, 逐一用插件 --simulate 验证哪个带视频)。这是本轮原创的可复用发现, 补上了插件 README 没写的'内容发现'环节。")
R.append("- **小红书**: 用户给定的 xsec_token 分享链 + yt-dlp 匿名档一次过(720x1364)。yt-dlp 未返回 uploader 字段, 作者名以用户分享文案补全(已在 meta.json 标注来源)。")
R.append("")
R.append("### 3.6 其他过程问题")
R.append("- curl `-w` 参数写 `@xxx` 开头会被解析为'读文件', 探测脚本首次运行报错(`curl: option -w: error encountered when reading a file`), 已修复为 `[xxx]` 前缀。")
R.append("- ffmpeg 全量解码体检单次 bash 调用超时(>300s), 改用 ffprobe 快速体检完成(W021)。")
R.append("- WebSearch 对 v.douyin.com/threads.net 帖子级 URL 的收录极差(5 轮搜索无一条直接结果), 印证'围墙花园检索不到'痛点; 实际靠**第三方转引**(Lemmy 帖/豆瓣帖/文档示例)拿到目标。")
R.append("")
R.append("## 4. 未探索路径 (想走但按规则没走的)")
R.append("")
R.append("| 平台 | 未探索路径 | 预期收益 | 为何没走 |")
R.append("|------|-----------|---------|---------|")
R.append("| YouTube | ① bgutil-ytdlp-pot-provider (Brainicism, node 版本地起 4416 服务 + pip 插件) ② burner 账号 cookies | POT token 是数据中心 IP bot-check 的对症解法, 大概率能通 | 需 clone+node server+插件三步部署, 超出'换方式重试1次'预算 |")
R.append("| 抖音 | ① ttwid 注入 (POST ttwid.bytedance.com/ttwid/union/register 取 cookie 后喂给 yt-dlp) ② TikTokDownloader (★17.3k, 扫码登录) ③ playwright 真浏览器截 JSON | ttwid 是 yt-dlp 报错点名要的'fresh cookies', 成功率最高的下一步 | 同上; 且扫码登录需要用户手机参与 |")
R.append("| B站 | SESSDATA cookie → 1080p+ | 画质提升 | 用户未提供 cookie |")
R.append("| 小红书 | 匿名 web_session cookie → 4K HEVC 档 | 画质提升 (findings B18) | 用户未提供 cookie |")
R.append("| 微博 | ① 补 XSRF-TOKEN 头走容器 API ② gallery-dl weibo (32 extractors) | 恢复'列时间线'自发现能力 | 已有替代方案(搜索引擎给URL), 边际价值低 |")
R.append("| Threads | ① `/share/<code>` 短链形态 ② threads 官方 API | 备用通路 | 本轮已成功, 无需 |")
R.append("")
R.append("## 5. 如果下一步要我'自行搜索'内容, 怎么办?")
R.append("")
R.append("本轮实测把'发现'和'下载'拆开验证了一遍, 结论分三档:")
R.append("")
R.append("**① 沙盒内可自发现(已实测, 脚本化)**")
R.append("- B站: `api.bilibili.com/x/web-interface/popular` 热门榜免登录, 拿 bvid/cid/标题/UP (dl_bilibili.py 内置)")
R.append("- YouTube: `yt-dlp ytsearch10:<关键词>` 可搜索可过滤时长 (dl_youtube.py 内置; 注意发现可用≠能下载, 见 §3.3)")
R.append("- Threads: **Googlebot UA 抓主页 → 抽帖子 code → 插件 --simulate 验证带视频** (本轮新方法, tools/probe_threads.sh + tools/find_threads_video.sh)")
R.append("- X: 平台内搜索需登录; 但搜索引擎查 `\"x.com/<user>/status\"` 常能命中新闻/论坛转引, 且转引页常附 video.twimg.com 直链")
R.append("")
R.append("**② 需要转引/第三方 (半自动)**")
R.append("- 抖音: 站内搜索(a_bogus 签名)不可行; 可走 ① 搜索引擎找 `v.douyin.com` 短链转引(本轮 5 轮搜索 0 命中, 收录差) ② tophub/新抖等热榜站 ③ **用户给分享链接最稳**(短链 302 解析仍正常)")
R.append("- 微博: 列时间线被访客墙挡; 搜索引擎查 `weibo.com/<uid>/<bid>` 转引可命中(本轮即此法), 或用户给 status URL")
R.append("")
R.append("**③ 基本必须用户给料**")
R.append("- 小红书: 站内搜索需登录+签名(a1/x-s); 浏览器地址栏 URL 不带 xsec_token 无法解析(findings B17)。**给 App 分享链接是唯一稳定入口**。")
R.append("")
R.append("**可复用结论: '下载器解决下载, 发现靠组合拳(平台API+搜索引擎转引+用户给链)'** —— 对围墙花园, 搜索引擎的索引缺口是常态, 转引页(新闻/豆瓣/Lemmy/工具文档示例)是主要突破口。")
R.append("")
R.append("## 6. 可复用资产")
R.append("")
R.append("- **脚本** (`tools/`, 与本地 `~/my-project/scripts` 同源): `dl_{weibo,bilibili,youtube,xhs,douyin,x,threads}.py`(每平台独立, 统一 RESULT 行输出, 失败自动写 W 条目), `lib_media.py`(日志/元数据/格式选择/下载), `gh_sync.sh`(增量推送), `probe_targets.sh`/`probe_threads.sh`/`find_threads_video.sh`/`extract_threads_profile.py`(目标发现)")
R.append("- **skill**: `skills/video-downloader/` (SKILL.md + 全套脚本, 含本轮全部踩坑要点)")
R.append("- **协议**: worklog W 条目 + state.json + 每步 push (findings/04, 本轮全程执行)")
R.append("")
R.append("## 7. 校验")
R.append("- 文件完整性: 5/5 ffprobe 通过 (h264+aac, 尺寸/时长/大小正常, W021)")
R.append("- GitHub 推送: 每平台完成即 push (commit 链 f16c4e0→HEAD, 本目录全量入库)")
R.append("- 本报告由 `tools/build_report.py` 从 meta.json 自动生成, 手写章节为 §3-§6。")

open(f"{WORK}/REPORT.md", "w", encoding="utf-8").write("\n".join(R) + "\n")
print(f"REPORT.md written: {len(R)} lines")
