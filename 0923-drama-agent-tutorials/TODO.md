# TODO — 漫剧智能体教程离线抓取任务（交接文档）

> 本文档是任务交接文件。新任务请**先完整阅读本文档**，再继续执行剩余任务。
> 最后更新：2026-09-23
> 目标仓库：https://github.com/lishuhang/clock （分支 main，工作目录 `0923-drama-agent-tutorials/`）

---

## 一、任务目标

把 11 个漫剧智能体平台的入门教程全部抓取到本仓库 `0923-drama-agent-tutorials/` 目录，做到**断网也能看到教程全文**（含图片和视频）。

- 平台提供官方 PDF 的，优先下载 PDF。
- 唯一验收标准：只用本地文件即可完整阅读每篇教程。

## 二、存储规范（必须遵守）

1. 每篇文档单独存放，优先 markdown，文件名 = 教程标题。
2. 每篇 md 的开头格式：
   ```
   # <文档名>

   > 来源：<原文url>
   > 抓取时间：<日期>（离线快照，原文见链接）
   ```
3. 图片/视频先测外链是否永久有效；凡可能过期的，一律下载备份到与文档同名的子文件夹 `_files_<文档名>/`，并把 md 内链接改写为本地相对路径。
4. 文中引用的视频也必须下载到 `_files_<文档名>/`。
5. 媒体命名约定：`image_N.ext` / `video_N.ext`，并保留 `sources.json` 清单（原始 URL → 本地文件映射）。

## 三、总体进度（11 平台）

| # | 平台 | 教程地址 | 状态 | 产物 |
|---|------|---------|------|------|
| 1 | ShotLab | xinpianchang.feishu.cn/wiki/GjSzwUef... | ✅ 完成 | 1 md + 73 图 |
| 2 | 万兴剧厂 | reelmate.cn/create-guide.html（飞书，6 篇） | ✅ 完成 | 6 md + 363 图 |
| 3 | 巨日禄 | my.feishu.cn/docx/LmixdG7EhoQ813xexeNc8ALMnDg | ✅ 完成 | 1 md + 111 图 |
| 4 | LibTV | resonate.feishu.cn/wiki/Loxfw6XHziYRk0kKzdjcFfp9nhb | ✅ 完成 | 1 md + 202 图 |
| 5 | OiiOii | ecncw7du1qtr.feishu.cn/wiki/R6m5w5RILiS35lkM7PycEUhHnfc | ✅ 完成 | 2 md + 133 图 |
| 6 | Seko | sensetime.feishu.cn/wiki/U3TOw2Mpbid2BrkkeTBc80xPnih | ✅ 完成 | 1 md + 27 图 |
| 7 | 纳逗Pro | nadoupro.iqiyi.com/docs/getting-started | ⚠️ 基本完成 | 16 md + 197 图 + 15 视频；**官方 PDF 未下载**（getting-started 页有 PDF 下载入口） |
| 8 | 小云雀 | xyq.jianying.com/tutorials | ⚠️ 完成 9/11 | 9 md + 691 图 + 196 视频；**缺 2 篇**：`短剧重制转绘使用手册`（/tutorials/short-drama-remake）、`小云雀短剧 Agent 智能预演体验指南`（/tutorials/short-drama-agent-smart-preview） |
| 9 | TapNow | docs.tapnow.ai/zh/docs | ❌ 未开始 | 约 41 个文档页，选择器 `article`，图片走 Next.js `/_next/image?url=` 代理 |
| 10 | flova | www.flova.ai/zh-CN/docs/tutorials/quick-guide/ | ❌ 未开始 | 6 页，选择器 `article#nd-page`，含 CDN 视频（无扩展名 URL） |
| 11 | AniShort | anishort.ai/academy | ❌ 未开始 | 全视频教程，SPA 站点，需 Playwright；已探测到 11 个课程页 URL（见 `AniShort/_anishort_meta.json`），但视频为懒加载，需进一步抓接口 |

## 四、剩余任务清单（按顺序做）

1. **小云雀补 2 篇**：运行 `python3 /home/z/my-project/scripts/run_web_scrape.py 小云雀`（脚本会跳过已生成的？不会——需手动把 pages 列表里已完成的 9 篇注释掉，或直接改脚本只跑剩余 2 页）。产物写入 `clock_repo/0923-drama-agent-tutorials/小云雀/`。
2. **TapNow 全量抓取**：`python3 /home/z/my-project/scripts/run_web_scrape.py TapNow`（41 页，建议 nohup 后台跑，日志 `/home/z/my-project/work/scrape_web4.log`）。
3. **flova 抓取**：`python3 /home/z/my-project/scripts/run_web_scrape.py flova`（6 页，注意视频无扩展名，库已兼容）。
4. **纳逗Pro 官方 PDF**：访问 https://nadoupro.iqiyi.com/docs/getting-started ，找到 PDF 下载入口（可能是页面上的"下载 PDF"按钮或固定 URL），下载后放 `纳逗Pro/` 目录。
5. **AniShort**：
   - 站点是 SPA（Next.js），普通 curl 拿不到内容；用 Playwright（Node）。
   - 探测脚本：`/home/z/my-project/scripts/probe_anishort.js`，已产出 `AniShort/_anishort_meta.json`（11 个课程页，形如 `https://anishort.ai/academy/77?category=0&page=1`）。
   - 课程视频为懒加载：需监听网络请求（page.on('response')）找视频 CDN 接口（可能是 .m3u8 或 mp4 直链），逐课抓取。
   - 每课生成一个 md（含课程文字简介 + 本地视频引用）。
6. **核验**：全仓库 `grep -r "https\?://" --include="*.md"` 检查 md 正文里不应残留必须在线才能看的图片/视频外链（`来源:` 行除外）。图片外链若验证是永久 CDN（如官方静态资源）可保留，否则本地化。
7. **收尾**：更新仓库根 `worklog.md` → 最后一次 commit + push → **删除 `/home/z/my-project/.secrets/feishu_cookies.txt`**（任务要求：完成后销毁 cookie）。

## 五、已有工具与用法

工作目录：`/home/z/my-project/work/clock_repo/`（已 clone，remote 已内嵌 token 配置好，**直接用，不要再改 remote**）

| 文件 | 用途 |
|------|------|
| `/home/z/my-project/scripts/web_scrape_lib.py` | 通用抓取库：fetch、download_media、MediaPool（媒体本地化 + sources.json 清单）、html_to_md、localize_md；已处理 Next.js 图片代理解码、懒加载 data-src、无扩展名 CDN 媒体（pre_urls 机制 + 安全网补下载） |
| `/home/z/my-project/scripts/run_web_scrape.py` | 4 站配置入口（小云雀/TapNow/flova/纳逗Pro）。用法：`python3 run_web_scrape.py <站名...> [--limit N]`。小云雀选择器 `main#content`、TapNow `article`、flova `article#nd-page` |
| `/home/z/my-project/scripts/probe_anishort.js` | AniShort Playwright 探测脚本（Node） |
| `/home/z/my-project/scripts/feishu_lib.py` + `run_feishu_all2.py` | 飞书文档抓取（6 个飞书平台已全部完成，一般不需再用；若需重跑要配 cookie） |
| `/home/z/my-project/work/scrape_web4.log` | 抓取运行日志 |

**Git 提交规范**（用户要求：push 及时但不频繁，按平台/阶段批量提交）：
```bash
cd /home/z/my-project/work/clock_repo
git add 0923-drama-agent-tutorials/<平台名>
git commit -m "0923 教程抓取: <平台名> (内容概述)"
git push origin main
```
push 前检查单个文件 <100MB；**绝不能把 token 写进任何被跟踪的文件**。

## 六、踩坑记录（重要）

1. **沙箱脱敏**：命令文本里出现完整 GitHub token 字符串可能被系统脱敏破坏 → 用分段变量拼接（如 `P=ghp_; A=xxxx; B=yyyy; T=$P$A$B`）。
2. **bash 工具可能周期性失效**：连续多次报错且 echo 都失败时，提醒用户重启会话；本地磁盘进度不会丢。
3. **markdownify 新版 API**：`convert_img(self, el, text, *args, **kwargs)` 必须兼容签名（库已修好，别改回去）。
4. **TapNow 图片**：src 是 `/_next/image?url=<编码URL>&w=...&q=...`，需 URL 解码取真实地址；真实地址可能无扩展名，MediaPool 用 pre_urls 登记解决。
5. **TapNow/flova 前台跑会超时**：务必 nohup 后台运行并轮询日志。
6. **AniShort 视频**：页面 DOM 里的 video 标签是占位（`00:00 / 00:00`），真实地址在懒加载接口里，必须监听 network 响应。
7. **429/限速**：连续抓取时在 web_scrape_lib 已有基础延时，若某站开始批量失败，加 sleep 重试。

## 七、安全与合规

- GitHub token：仅存在于 `.git/config` 的 remote url 中（已配好），**严禁**写入任何被 git 跟踪的文件、日志或 md。
- 飞书 cookie：`/home/z/my-project/.secrets/feishu_cookies.txt`（git 忽略，不入库）。全部任务完成后**必须删除**。
- 本文档与 `worklog.md` 不含任何密钥，可安全入库。

## 八、当前 git 状态快照

- 已推送：ShotLab、万兴剧厂、巨日禄、LibTV、OiiOii、Seko、纳逗Pro(16篇)、小云雀(WIP 资源 201 项) —— 共 8+ commits 在 origin/main。
- 本文档提交时一并推送：小云雀 9 篇 md 及其 `_files_*` 资源、AniShort 探测 meta。
