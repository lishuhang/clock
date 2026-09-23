# TODO — 漫剧智能体教程离线抓取任务（✅ 已全部完成）

> 本文档原为任务交接文件。**2026-09-23 全部任务已完成**，本文保留作为进度总账与决策记录。
> 目标仓库：https://github.com/lishuhang/clock （分支 main，工作目录 `0923-drama-agent-tutorials/`）

---

## 一、任务目标（已达成）

11 个漫剧智能体平台的入门教程全部抓取到本仓库 `0923-drama-agent-tutorials/` 目录，**断网可看全文**（含图片和视频）。平台提供官方 PDF 的优先下载 PDF。唯一验收标准：只用本地文件即可完整阅读每篇教程。

## 二、总体进度（11 平台，全部 ✅）

| # | 平台 | 状态 | 产物 |
|---|------|------|------|
| 1 | ShotLab | ✅ 完成 | 1 md + 73 图 |
| 2 | 万兴剧厂 | ✅ 完成 | 6 md + 363 图 |
| 3 | 巨日禄 | ✅ 完成 | 1 md + 111 图 |
| 4 | LibTV | ✅ 完成 | 1 md + 202 图 |
| 5 | OiiOii | ✅ 完成 | 2 md + 133 图 |
| 6 | Seko | ✅ 完成 | 1 md + 27 图 |
| 7 | 纳逗Pro | ✅ 完成 | 16 md + 197 图 + 15 视频 + **官方 PDF**（getting-started 客户端导出版，`纳逗Pro 使用手册.pdf`） |
| 8 | 小云雀 | ✅ 完成 11/11 | 11 md + 702 图 + 198 视频 |
| 9 | TapNow | ✅ 完成 45/45 | 45 md + 96 媒体（Next.js 图片代理解码） |
| 10 | flova | ✅ 完成 7/7 | 7 md + 9 段 CDN 视频（无扩展名 URL 已本地化） |
| 11 | AniShort | ✅ 完成 11/11 课程 | 11 md（3 多集课程 31 集索引 + 8 单集课程）+ 29 视频/48 海报本地化 |

## 三、2026-09-23 本轮完成事项

1. **小云雀补 2 篇**：`短剧重制转绘使用手册.md`（断点续用既有 `_files_` 8 项资源）、`小云雀短剧 Agent 智能预演体验指南.md`（5 图）。
2. **TapNow 全量 45 页**：选择器 `article`；标题取 h1（og:title 是站点名）；`/gitbook-assets/` 根相对路径经 origin 拼接修复后正常下载；发票页 1 张 larksuite 图源站本身失效（400），md 内以占位符注明。
3. **flova 全量 7 页**：选择器 `article#nd-page`；无扩展名 CDN 视频经内容魔数嗅探命名 `.mp4`。
4. **纳逗Pro 官方 PDF**：页面按钮为客户端实时生成（`data-pdf-generator="client"`），Playwright 点击 + 捕获 download 事件获取（1.9MB）。
5. **AniShort 全视频教程**（SPA，Playwright 网络监听）：
   - 真实结构：3 个多集课程（77=Anishort 全流程教学 6 集、119=3D导演台 14 集、104=全环节实战精讲 11 集）+ 8 个单集课程（速转整部剧、3D世界新玩法等）。
   - 坑：多集课程的 16 行侧栏在部分课程页是「全目录推荐位」，点击会跳转其他课程——按面包屑标题 + 播放器时长判定为单集课程；视频直链靠监听 `bdbcdn propertyvideo` mp4 响应 + 等 src 变化（修复了竞态）。
   - 159 集去重后 48 个唯一视频；**受 GitHub 单文件 100MB 硬限制**，29 个（≤99MB，约 1.07G）已本地化到共享池 `_anishort_videos/`（跨课程去重、`sources.json` 清单）；17 个大视频在 md 中保留在线链接并注明原因。
6. **历史 md 断链修复**：小云雀/纳逗Pro 早期 md 中 1958 个裸 `](image_N.png)` 链接改写为 `_files_<文档名>/` 相对路径。
7. **站内导航链接规范化**：228 个 `/xxx` 站根相对链接改写为完整 URL；TapNow 文内 `.md` 相对链接映射到在线页面。全仓库 md 相对链接核验 **0 断链**（2366 个全部可解析）。

## 四、关键决策与约束记录

- **磁盘预算**：媒体入库成本≈2×（工作树 + git pack）。沙箱 9.9G 盘在 AniShort 阶段仅剩 ~2.5G。采用「blobless 浅克隆 + 工作树搬迁 + `--no-filter` 回填」完成 git 手术（详见仓库根 `worklog.md` 2026-09-23 条目），最终以 GitHub 100MB 限制为 AniShort 大视频的取舍边界。
- **媒体池命名**：AniShort 采用跨课程去重共享池 `_anishort_videos/`（文件名=CDN 原始 UUID 文件名），与其它平台 `_files_<文档名>/` 约定不同，原因：同一视频被最多 7 门课程引用，按课程复制会翻倍占用。清单见 `AniShort/_anishort_videos/sources.json`。
- **安全**：GitHub token 仅存在于 `.git/config` remote url；`/home/z/my-project/.secrets/feishu_cookies.txt` 在本轮会话中已不存在（此前已销毁），无需再删。

## 五、验收状态

- [x] 11 平台教程 md 全部生成，开头含「来源/抓取时间」两行
- [x] 图片/视频本地化 + sources.json 清单（除注明保留在线的 AniShort >100MB 视频与 1 张源站已失效图片）
- [x] 全仓 md 相对链接 0 断链；正文无必须在线才能看的媒体外链（保留项均有注明）
- [x] 全部 commit 已推送 origin/main
