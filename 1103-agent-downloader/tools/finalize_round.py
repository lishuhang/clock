#!/usr/bin/env python3
# 实抓轮收尾: 更新 todo.md / state.json / RESUME.md / 仓库根 worklog.md
import json, datetime, zoneinfo

WORK = "/home/z/my-project/clock/1103-agent-downloader"
def now():
    return datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Hong_Kong")).isoformat(timespec="seconds")

# ---- 1. state.json ----
st = json.load(open(f"{WORK}/state.json", encoding="utf-8"))
st["phase"] = "download_round_complete"
st["updated"] = now()
st["next_task"] = ("实抓轮已完成 5/7 (微博/B站/X/Threads/小红书✅, YouTube/抖音❌两法用尽). "
                   "下一步可选: ①YouTube bgutil POT provider 部署 ②抖音 ttwid 注入或 TikTokDownloader ③REPORT.md 已交付, skill 已固化(skills/video-downloader)")
ps = st.setdefault("platform_status", {})
ps.setdefault("youtube", {})["result_1103"] = {"ok": False, "reason": "两client组合均 Sign in bot-check(数据中心IP), 见REPORT §3.3/§4"}
ps.setdefault("douyin", {})["result_1103"] = {"ok": False, "reason": "iesdouyin SSR 已收壳+yt-dlp 要 fresh cookies, 见REPORT §3.4/§4"}
ps["weibo"]["result_1103"]["note"] = "容器API与WeiboUser列时间线均被访客墙挡; 单视频yt-dlp游客通路畅通"
json.dump(st, open(f"{WORK}/state.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---- 2. todo.md ----
todo = """# todo — 实抓轮 (2026-11-03) 完成状态

> 规则: 每平台失败最多换法重试 1 次; 未探索路径只记录。**实抓轮已完成, 5/7 平台成功。**

## Phase 0 — 准备 ✅
- [x] T0.1 Threads 插件安装验证 (`Extractor Plugins: ThreadsIE` ✓)
- [x] T0.2 密钥目录 (token 走 /home/z/my-project/scripts/.ghtoken, 未入库)
- [x] T0.3 测试目标选定 (B站热门API/微博搜索引擎转引/X Lemmy留档/抖音示例短链/Threads主页SSR抽code/小红书用户链接/YouTube ytsearch)
- [x] T0.4 通用脚本 lib_media.py + 每平台 dl_*.py

## Phase 1 — 实抓
- [x] T1.1 微博 ✅ 540x960 4.1MB (方案A/B发现失败 → 搜索引擎转引URL + yt-dlp游客)
- [x] T1.2 B站 ✅ 1280x536 29.2MB (html5 playurl 免登录720p档, 修正调研结论)
- [x] T1.3 YouTube ❌ 两 client 组合均 bot-check (未探索: bgutil POT / burner cookies)
- [x] T1.4 X ✅ 1920x1080 4.3MB (SpaceX 官方, 游客免cookie)
- [x] T1.5 Threads ✅ 720x1280 11.9MB (主页Googlebot SSR抽code → 插件下载, 原创发现)
- [x] T1.6 小红书 ✅ 720x1364 7.2MB (用户 xsec_token 链接 + yt-dlp 匿名档)
- [x] T1.7 Instagram — 用户豁免
- [x] T1.8 抖音 ❌ SSR 已收壳 + yt-dlp 要 cookies (未探索: ttwid注入/TikTokDownloader/playwright)

## Phase 2 — 汇总交付
- [x] T2.1 REPORT.md (自动生成 §1/§2 + 手写 §3-§6)
- [x] T2.2 ffprobe 体检 5/5 通过 (W021)
- [x] T2.3 失败平台如实记录 (报错逐字, REPORT §3)
- [x] T2.4 根 worklog 追加 + push
- [x] skill 固化 (skills/video-downloader)
"""
open(f"{WORK}/todo.md", "w", encoding="utf-8").write(todo)

# ---- 3. RESUME.md 增量提示(前插一段) ----
res = open(f"{WORK}/RESUME.md", encoding="utf-8").read()
banner = ("> **[实抓轮已完成 2026-11-03]** 5/7 平台成功(微博/B站/X/Threads/小红书), YouTube/抖音失败但根因清楚。"
          "结果看 `REPORT.md`; 失败平台的下一步看其 §4 未探索路径表; 全部脚本在 `tools/`。本文件以下内容为调研轮遗产, 仍然有效。\n\n")
if "实抓轮已完成" not in res:
    lines = res.split("\n")
    # 插在第一段标题之后
    for i, l in enumerate(lines):
        if l.startswith("> 你是接手"):
            lines.insert(i, banner.rstrip())
            lines.insert(i, "")
            break
    open(f"{WORK}/RESUME.md", "w", encoding="utf-8").write("\n".join(lines))

# ---- 4. 根 worklog 追加 ----
entry = f"""

Agent: Super Z (main)
Task: 8平台视频下载实抓轮（除Instagram外7平台各1条高清视频+元信息→GitHub; 用户规则: 失败最多换法重试1次）

Work Log:
- 成绩 5/7：微博540x960/B站1280x536(免登录html5 playurl 720p档,修正调研"仅480p"结论)/X 1920x1080(SpaceX官方推文,游客免cookie)/Threads 720x1280(原创方法:Googlebot UA抓threads.com主页SSR抽帖子code→插件--simulate验证带视频→下载)/小红书720x1364(用户xsec_token链+yt-dlp匿名档)
- 微波级发现：微博"列时间线"已被访客墙挡(m.weibo.cn容器API ok=-100 + yt-dlp WeiboUser重定向passport访客流程),但"单视频提取"畅通——搜索引擎转引拿具体URL即可绕过
- YouTube❌：ytsearch发现正常,但ios,web_safari与web,android_vr,tv_downgraded两client组合均死于同一IP级bot-check("Sign in to confirm you're not a bot"),与上轮调研B1预判一致;未探索:bgutil POT provider(node版)/burner cookies
- 抖音❌：iesdouyin分享页SSR对匿名已只回壳数据(loaderData仅页面元信息,aweme_id出现0次,三目标交叉验证排除"目标已删"),yt-dlp报"Fresh cookies needed"如B13预判;未探索:ttwid注入/TikTokDownloader扫码/playwright
- 全部脚本化入库(tools/dl_*.py + lib_media.py + gh_sync.sh增量推送×7次commit),ffprobe体检5/5通过,过程留痕worklog W009-W021+logs/
- 交付物：REPORT.md(元信息总表+忠实问题记录+未探索路径表+自行检索策略三档矩阵) + skills/video-downloader(固化)

Stage Summary:
- 平台难度重排序(实测定论)：X<B站<Threads<小红书<微博<YouTube(数据中心IP)<抖音(结构性收紧)
- "自行搜索"结论：B站热门API/YouTube ytsearch/Threads主页SSR可沙盒内自发现;X/微博靠搜索引擎转引;抖音转引收录差需热榜站或用户给链;小红书必须用户给App分享链接——详见REPORT §5
- 下一步若续做：YouTube装bgutil POT、抖音ttwid注入是各自失败的对症解,预算各约半小时
- 工作目录: 1103-agent-downloader/ (REPORT.md 为总入口)
"""
with open("/home/z/my-project/clock/worklog.md", "a", encoding="utf-8") as f:
    f.write(entry)

print("state/todo/RESUME/根worklog 全部更新完成 @", now())
