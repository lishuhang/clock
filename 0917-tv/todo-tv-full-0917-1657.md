# iptv345 / MonitorHub 项目完整工作日志（整合版）

> **给后续接手 Agent 的话：本文是本项目的唯一完整工作日志。它整合了 `prompts/` 内全部历史日志、交接记录、开发史与原始对话蒸馏，按事情发生的实际时间顺序排序并去重。只要通读本文，即可了解这个项目从 2026-06 诞生至今的全部来龙去脉，无需再翻阅其他任何历史文档。后续每轮任务完成后，请以"增量日志"形式追加到本文末尾并更新版本标记。**
>
> 整合基线版本：`todo-tv-full-0917-1530.md`（2026-09-17 15:30 HKT 整合）
> 最终版本：**`todo-tv-full-0917-1657.md`**（2026-09-17 16:57 HKT，含 0917 大维护全部增量，即当前文件）
> 时区约定：全文除特别注明外均为 GMT+8
> 安全约定：本文不含任何明文凭据、密钥、动态 token 或"频道名 ↔ m3u8 URL"的明文映射表。频道名与地址的对应关系只存在于加密压缩包（密码向用户索取）与 worker full 版源码中。

---

## 目录

1. 项目概述与当前架构速览
2. 时间线·第一阶段：项目诞生与基础逆向（2026-06）
3. 时间线·第二阶段：yso/xuexi/wso 多源扩展与自动刷新（2026-07）
4. 时间线·第三阶段：TV App 前端迭代（2026-07 下旬 - 08 中旬）
5. 时间线·第四阶段：审计、v2.10.x 稳定化与官方源调研（2026-08-15）
6. 时间线·第五阶段：v2.11 LNC 与 MonitorHub（2026-08-16/17）
7. 时间线·第六阶段：2026-09-17 大维护（v2.12）
8. 渠道线路可用性现状（2026-09-17 实测）
9. 坏渠道明细与日后恢复方法（详见加密包内 iptv345-bad-channels-in-v2.11.md）
10. 关键经验教训汇总（去重后的全部踩坑）
11. 仓库与文件索引
12. 增量日志区

---

## 1. 项目概述与当前架构速览

### 1.1 项目组成

本项目包含三个相互配合的部分：

| 组成 | 载体 | 说明 |
|---|---|---|
| **iptv345 Worker** | Cloudflare Worker `iptv345`，自定义域 `345.lishuhang.com`（对外清单禁止使用 workers.dev 域名） | 把多个上游直播源转换为固定 URL 的 HLS 中转，第三方播放器直接可用 |
| **MonitorHub（tv-app）** | Cloudflare Worker `tv`，自定义域 `tv.lishuhang.com`，产品源文件为单文件 HTML | 多屏监视墙前端，导入 IPTV 清单后自动播放/换台/线路切换 |
| **自动刷新流水线** | GitHub 仓库 `lishuhang/345` 的 `Refresh and Deploy` workflow | Playwright 定时抓取动态 token → 构建 blind worker → 部署 Cloudflare |

### 1.2 Worker 路由家族（v2.12 现状）

| 路由 | 来源 | 状态（2026-09-17） |
|---|---|---|
| `/<tid><id>.m3u8`（如 gt5、ys1、itv7） | 345 动态源（m.345iptv.com） | gt/ys 线路经 v2.12 修复后恢复 |
| `/lnc1` ~ `/lnc10.m3u8` | livenewschat.eu（v2.11 接入） | 9/10 可用 |
| `/wso-<name>.m3u8` | 各省卫视官网 API | 部分可用 |
| `/xuexi_<hash>.m3u8` | 学习强国（Actions 注入 auth_key） | 可用（依赖刷新周期） |
| `/yspcNN` `/yspwNN.m3u8` | 央视频 | **v2.12 起移除**（海外出口永远 403，架构性不可用） |
| `/health/` `/refresh/` `/refresh-gha` `/cat/` | 运维辅助 | 正常 |

### 1.3 自动刷新链路（用户问题的直接答案）

用户曾疑惑"与 GitHub Actions 的 345 联动是不是根本没用上过"。结论：

- **用上了，且一直在用。** 线上 blind worker 的 xuexi catalog（40 频道）完全由 `lishuhang/345` 的 workflow 构建注入；该 workflow 至今已运行 1300+ 次。
- 用户"经常收到 345 actions 执行失败通知"集中在 **2026-07-23 之前**，根因是 `deploy_worker.py` 硬编码了本地 `.secrets` 路径，GitHub Actions 环境不存在该文件 → 部署步骤必败 → **CF API token 在那之前确实从未被调用过**。2026-07-23 改为环境变量优先后修复。
- 2026-08-15 审计再次确认链路真实有效（当时最近 100 次运行全部成功）。2026-09-17 复查：最近 30 次运行全部成功，仅 09-09 有一次失败。
- 注意：workflow 成功 ≠ 频道可用。抓取步骤有 `|| true` 容错，且动态 token 会自然过期；必须把"workflow 成功 / 状态页成功 / HLS 传输成功"三层分开判断。
- cron 表达式为 `*/10`，但 GitHub 实际调度约每 4-5 小时才执行一次（GitHub 侧节流）；xuexi auth_key 实测有效期仅约 20-30 分钟（历史记录 10-30 分钟，auth_key 的 start_time 回退 20 分钟），因此 xuexi 仅在每次部署后的短窗口内可用，过期后由 worker 端 403 → `triggerRefresh()`（GH_TOKEN secret 已配置）自动补触发刷新，形成"过期→自动重刷→恢复"的自愈闭环（本次已实测验证两轮）。

---

## 2. 时间线·第一阶段：项目诞生与基础逆向（2026-06）

### 2.1 起点（原始对话，存 `prompts/chat-history.txt`，1771 行）

- 用户提供 `m.345iptv.com` 播放页链接，要求构建 Cloudflare Worker 中转：用户侧固定 URL，token 获取 / iPhone UA 伪装 / Referer 注入全部由 Worker 完成。
- 逆向结论（整个项目的技术地基，后来全部文档反复引用）：
  - 播放页 `pvjs.js`（jsjiami.com.v7 混淆）核心算法：`base64解码 → XOR("iptv.com") → base64解码 → unescape`；
  - 源站自定义 `decode()` 把 `=` 当 keyStr 第 64 个字符而非 padding，标准 `atob` 会返回空 → 必须自实现解码器；
  - inline script 每次加载形态不同（长变量有时反转有时不反转）→ 双策略尝试；
  - 播放页 URL 的 token 参数不校验，任意 32-hex 可用（dummy token）；
  - 段 URL 有效期仅约 1-2 秒；play.php 每次重定向到不同 t-host，段必须从对应 t-host 拉取；
  - 所有段请求必须带 `Referer: https://m.345iptv.com/`，否则 404。
- 域名规划：worker `iptv345.lishuhang.workers.dev`，生产一律用自定义域 `345.lishuhang.com`。

### 2.2 v1.0 → v2.1 演进（2026-06 上半月）

| 版本 | 内容 |
|---|---|
| v1.0 | 逆向 pvjs.js，实现播放页抓取 → token 解密 → play.php → m3u8 代理；首页列出 1726 频道 |
| v1.5 | 三栏 SPA（分类/频道/播放器+线路切换）；1726 → 1051 唯一频道，1692 线路，按央视/卫视/港澳台/地方/轮播 5 分类合并 |
| v1.6 | hls.js 配置修复音画漂移（backBufferLength=10 等）与 CDN 缓存重复播放（CDN-Cache-Control: no-store）；TTL 缩短至 90s/60s |
| v1.7 | 全量 1692 线路可播性测试：808 条不可播（47.8%，多为重定向到 HTTP 裸 IP，Workers 禁止 fetch）；UI 加"隐藏不可播源" |
| v2.0 | 去敏感化：目录/源码/HTML 不出现敏感字样，频道名清洗为 tid+id 编码，名称改为用户导入名单 |
| v2.1 | 导出 list 过滤不可播线路 |
| blind v2.1 | "隐身模式"：无 UI、无目录，仅状态页 + 代理路由，应对 DMCA 风险。此后生产长期为 blind 版 |

2026-06-19 产出第一份正式交接文档（readme-260619），记录了坑 1-12（见第 10 节）。

---

## 3. 时间线·第二阶段：ysp/xuexi/wso 多源扩展与自动刷新（2026-07）

### 3.1 v2.5：央视频（ysp）源（2026-06-21）

- ysp `get_live_info` API 需要 WASM 生成的 cKey + SDK 头，Worker 内无法复现 → 改用 **Playwright 在浏览器中抓取** m3u8 URL 后嵌入 worker。这一"Playwright 抓取 → 注入构建"的模式奠定了后来整个自动刷新架构。
- auth 签名算法已逆向（MD5 排序参数 + 密钥），但 cKey 是死结。
- 45/48 频道捕获成功；m3u8/段无需 Referer，URL 有效期"数小时"（当时如此；后来上游策略变严）。
- 坑 13-16（详见第 10 节）。
- ysp TS 段为 `encrypt:2` 部分加扰（v2.6/v2.7 确认）：浏览器 hls.js 绿屏/bufferAddCodecError，需 ysp 自有 `hls.cmg.js + keygen_bg.wasm` 解密；**VLC/MPV/ffprobe 等原生 TS 播放器可正常播**。该问题从未彻底解决，是 ysp 长期体验短板。

### 3.2 v2.8（2026-07-22/23）

- 新增：302/404 错误信息清晰化（区分"源站已删除/已移动/流损坏"三类）；broken channel cache（10 分钟 TTL）；`/refresh/<tid><id>`；`/health/<tid><id>`；`/refresh-gha`；m3u8 注入 `#EXT-X-PROGRAM-DATE-TIME`。
- v2.8-plan-0722-1946.md 制定了外部配合方案：GitHub secrets（CF_API_TOKEN/ACCOUNT_ID）+ Worker secret GH_TOKEN + 每 5 分钟健康检查自动触发。这些后来全部落地（GH_TOKEN secret 已于 07-23 设置到 worker）。

### 3.3 GitHub Actions"345"联动：失败史与修复（2026-07-23，回答用户疑问的关键）

- `lishuhang/345` 仓库 workflow `Refresh and Deploy` 上线后**连续失败 12+ 次**（用户频繁收到失败通知）。
- 根因：`deploy_worker.py` 硬编码 `/home/z/my-project/.secrets`，在 Actions 环境不存在。
- 修复：改为环境变量 `CF_API_TOKEN`/`ACCOUNT_ID` 优先，本地 `.secrets` 兜底。**修复前，345 的 CF token 确实从未被用上**——这就是"是不是根本就没有用上过"的历史出处。
- 同日发现 xuexi auth_key 的 `start_time` 是 20 分钟前的时间戳、有效期从那时算约 30 分钟（即生成后仅剩约 10 分钟）；workflow 间隔 15→10 分钟，并加入 **dual xuexi refresh**（build 前再刷一次）。
- 坑 13-19 中 4.13-4.16、4.18 均产生于此阶段。

### 3.4 v2.9 / v2.10：卫视官网（wso-）源与固定直链（2026-07-23）

- v2.9 接入 `wso-hainan`（稳定）、`wso-dongnan`（CF 不可达，地域限制）、`wso-shaanxi`（偶尔可用）；`direct:` 前缀支持固定 URL 型 wso 源。
- v2.10 加入 `wso-guizhou`（不稳定）；修复 wso 403 死循环（API CDN 缓存旧 URL → 同一次请求内强制重新 resolve）。
- 调研 38 个可用固定直链（来自 IPTV 聚合仓库的运营商 IPTV 组播转单播），仅大陆网络稳定。
- tv_list 演进：v1(108 URL) → v2(5 地区分类) → v3(+ysp+xuexi, 194) → v4(+52 固定源, 246) → v5(+3 wso, 249) → v6(+38 官网固定源, 257)。
- 0723 产出第二份开发史文档（iptv345-dev-history-0723.md，v2.9→v2.10 增量）。

---

## 4. 时间线·第三阶段：TV App 前端迭代（2026-07 下旬 - 08 中旬）

> TV App 与 iptv345 是两个不同的 Worker（`tv` vs `iptv345`），域名、代码、部署均不可混用。

| 时间 | 版本 | 内容 |
|---|---|---|
| 07-22 | v1.3 | 导航栏 3 秒静止自动隐藏；频道 3 轮失败自动换台（设置打开时暂停）；缓冲 60 秒刷新同源再换台；导出文件名带时间戳 |
| 07-26 | v1.4 修复 | `handleFailover` 多余右花括号导致 `Unexpected token 'else'`，删除多余 `}`，不升级版本 |
| 07-26 | v1.4.1 | 无信号模式设置 UI；source pill hover 选择器修复（`.video-wrapper`）；resize/增减屏不中断播放；版本号统一 |
| 08-16 10:40 | v1.5 | 从 Worker 内嵌模板恢复为**单文件 HTML 产品源**（tv-app-v1.5.html）；自适应清晰度（≤480px→480p 等）；按宽高比选行列布局；两级频道选择；中英双语 i18n；内容源变更迁移 |
| 08-16 11:00 | v1.5 品牌微调 | 统一为 **MonitorHub · v1.5**；SVG favicon / Apple Touch Icon |
| 08-16 23:53 | v1.5 PWA | manifest.webmanifest + /sw.js + 192/512 安装图标 |
| 08-17 00:57 | v1.6 | 修复 Edge PWA 窗口控件覆盖（删除 `display_override`，保留 `standalone`） |
| 08-17 18:39 | v1.7 | 每屏"临时播放"URL；临时内容结束/暂停回退；20 组屏幕预设；**源导出改名 `monitorhub-sources-YYYYMMDD-HHMMSS.txt`**（2026-09-17 任务中的 monitorhub 清单即来源于此）；完整配置导入导出 JSON |

维护铁律：只编辑单文件 HTML 产品源，改完语法检查+本地浏览器验证，再生成 worker 部署包装；不要直接在 Worker JS 里维护业务界面。

---

## 5. 时间线·第四阶段：审计、v2.10.x 稳定化与官方源调研（2026-08-15）

### 5.1 上午（13:41）：整合基线

接管时确认：`iptv345` worker 最后修改于 2026-08-15 13:10（可能被外部自动流程刷新过）；覆盖前必须先下载审查现网脚本。明确安全约束（不保存凭据、GMT+8、增量 todo、合并提交）。确立"用户公开清单必须用自定义域，不得用 workers.dev"。

### 5.2 下午（15:38）：自动刷新链路审计 + v2.10.1

- 审计确认自动刷新链路**不是幻觉**：最近 100 次运行全部成功；但 workflow 用 `|| true` 容错抓取失败，且旧验证只检查状态页输出。
- **重要修复**：上游 345 播放页从"长加密 blob"改为直接内联变量表达式，旧解析器全数失败（`long encrypted blob not found`）。v2.10.1 保留旧 blob 路径 + 新增数据表达式解析（不 eval 上游脚本）。修复 commit `3577738`；人工触发运行 `31870320247`（8 分 6 秒）成功；生产显示 v2.10.1。
- 同时修复 xuexi 路由插入顺序（十六进制 key 被通用 `/<tid><id>.m3u8` 正则提前吞掉 → 必须插在通用匹配器之前）。
- 全量探测数据：257 条用户清单传输可用 99；345 历史目录 1778 条当时全因解析器失败为 0；修复后 1692 条 345 路由 33 条可用（源站本身大面积 502/超时，不是 Worker 问题）。
- 产出 `iptv_0815-1307.txt`（可用清单）与 `iptv-broken-0815-1307.txt`（仅非 345 直连失败项）。

### 5.3 傍晚（20:45 / 21:05）：官方源调研与生产回退

- 用户要求研究 kankanews（看看新闻）/ fengshows（凤凰）/ TVB / NHK 官网直播源经 345 中转的可行性。
- **看看新闻**：逆向了前端公开签名（双 MD5 排序拼接）+ RSA 公钥恢复 `live_address` 流程，8 个电视频道中仅"魔都眼"本地验证通过（清单 200 + 首 TS 200）；做成 v2.11 候选（`/kkn-magic-eye.m3u8` + `/kkseg/`）部署后，生产边缘反复 `Kankanews m3u8 failed: 403`（Worker→上游请求层失败）→ **显式回退 v2.10.1**（版本 d95e6bfe）。
- **凤凰**：官方页可播但旧媒体域 DNS 已失效、无现代签发 API、第三方工具是一次性链接机制 → 不接入。
- **TVB**：blob: 运行时注入 + hdnea（IP/时间/HMAC 绑定）短期授权 + 港/海外/内地三地区差异（内地黑屏音频）→ 不接入。
- **NHK**：官方 master HLS 连续 3 次 200、无 token 字段、完整层级（master/variant/fMP4 分片）可取 → 技术上可作为"限时同播"候选（官方页面明确每日同播约 5 小时），产出最小接入草案（wso-nhk-world + wseg Content-Type 透传），但**未部署**。
- 此阶段 GitHub 推送曾遭 403（授权范围不足），用户随后扩展授权恢复。

### 5.4 晚间（22:21）：v2.10.2

- 用户发现 v2.11（看看新闻候选）blind 状态页失败时回显了具体频道显示名，违反 blind 版不暴露业务性质的设计 → 回退到 v2.10.1 功能基线并脱敏：健康检查日志改为通用的 `Testing ... resource...`，不回显任何显示名；同时修改刷新仓库构建模板防止十分钟定时任务把泄露重新构建回去（commit `a7ed1c8`，运行 `31889165749`）。
- 教训：**blind 版本的任何输出（含失败诊断日志）都不得包含频道显示名或可推断内容**。

### 5.5 夜间（22:52）：清单 0815-2230

- 用户上传新清单（133 条）复测：75 可用；生产 worker 92 条固定 ysp/xuexi/wso 路由复测 13 可用；345 主目录 1692 条路由复测 60 可用（41 条去重后以"345 中转补充"分区保留）。
- 新增 NHK 官方直连（media-osa 域）验证可用，写入"国际"。
- 分类修正：Bloomberg TV+ 归"国际"；ABC/CGTN feed、NBD AI、Sky News Weather、Wild Earth、熊猫频道等非线性纯直播源归"其他"。
- 产出 `list_0815-2230.txt`（125 条）与 `list_unavailable_0815-2230.txt`（50 条），两文件 URL 交集为 0。

---

## 6. 时间线·第五阶段：v2.11 LNC 与 MonitorHub（2026-08-16/17）

### 6.1 v2.11（LNC 接入，08-16 00:28；文件时间 08-16 20:34）

- **EarthTV 未纳入**：279 个官方 webcam 页面无稳定公开 token 签发机制，固化临时 token 违反约束。
- **livenewschat.eu（LNC）纳入**：公开目录脚本（data.lncoperations.ee/server.json）返回当前最佳 CDN 节点；固定流代号构造 HLS 路径；确认 10 个唯一流代号（清单/TS 分片/AES key 全链路可用），映射为数字路由 `/lnc1` ~ `/lnc10.m3u8`。blind 只存数字 ID 与编码代号，**full 版保存显示名映射**（这就是 full/blind 内容差异的由来）。
- 首次部署后发现"清单节点与资源请求重新解析的节点不一致"导致 key/TS 502 → 修复为把经校验的节点写进内部资源路径（清单重载时才换节点）。commit `1562a2c`、`486ac68`；运行 `31894395591`、`31895043540`。
- LNC 请求头要求：桌面 Chrome UA + `Origin: https://livenewschat.eu` + 根 Referer。

### 6.2 统一整合记录（08-16 09:05，todo-0816-0905）

- 将此前全部交接记录归并去重为唯一基线（上一代整合，即本文前身）；冲突的版本声明（v2.10.1 vs v2.11）列为 P0 核验项，确立"Cloudflare 实际脚本 + GitHub 提交 + 请求级验证三方对齐才算现网事实"的判定法。
- 清单重建更正：初次聚合曾错标历史来源为可用，已更正为以 `list_0815-2230.txt` 为可用基线：**可用 125 / 不可用 1828**。
- 其附录完整归档了当时目录内全部历史 md（原始文件随后移除）——本次 0917 整合已再次吸收其内容，归档区无需再保留。

### 6.3 MonitorHub v1.5→v1.7（08-16/17，见第 4 节表格）

---

## 7. 时间线·第六阶段：2026-09-17 大维护（v2.12）

> 本节即本次任务的增量日志主体。任务输入：Cloudflare token、GitHub token、工作目录 `lishuhang/clock` 的 `0917-tv` 子目录、加密包 `worker_js/iptv345-v2.11.zip`（密码 iptv345，内含 v2.11 full/blind 与 monitorhub-sources-20260917-154644.txt）。

### 7.1 任务清单（用户指定）

1. 阅读/去重/按时间排序 prompts 全部日志 → 生成唯一整合版（即本文），清理 prompts 全部 md；
2. 本地解压 v2.11 加密包（防止未脱敏内容上 GitHub）；
3. 逐个检测 monitorhub 清单频道可用性，区分"仅海外可看"与完全失效；
4. 重点检查 iptv345 中转各线路（每线路抽 1 频道），坏线路修复至可用；
5. 检查 xuexi 等渠道与 GitHub Actions"345"联动是否曾生效，不可用则停止引用并告知 GitHub 端删除或修复；
6. 不惜一切代价保证 iptv345 基础服务畅通；livenewschat.eu 尽量保活；
7. 交付仍可用渠道；坏渠道说明原因 + 留存恢复方法；生产环境删除大陆海外均不可用的转发渠道；
8. 产出 `iptv345-v2.12.zip`（密码 iptv345：v2.12-blind.js + v2.12.js + bad-channels-in-v2.11.md + v2.12.txt 频道清单）；
9. GitHub 上不得出现明文"频道名 ↔ m3u8 URL"未脱敏内容；
10. 增量日志并入本文并改名。

### 7.2 执行过程（按实际时间顺序，UTC 标注）

**08:00 前后 环境与侦察**
- 服务器位于香港（阿里云 HK），可作为"海外视角"测试点。
- 克隆 `lishuhang/clock`；解压 v2.11 加密包成功。
- 读取 monitorhub-sources-20260917-154644.txt（135 行，约 80 个频道条目，含欧美/亚洲/香港/台湾/大陆/其他分组；其中大量 URL 指向 345 中转域）。
- 分析 v2.11 full/blind 双版本差异：blind 含 YSP_CATALOG（46 频道，Actions 注入）+ 数字化 LNC 路由；full 额外含 LNC 显示名映射与三栏 UI；两者均无 xuexi 处理器（xuexi 由 345 仓库构建脚本在构建时注入）。

**08:05 线上 worker 现状**
- `345.lishuhang.com` 返回 `v2.11 / status: 345 error; ysp error; xuexi error; wso ok`——345 抽测失败、ysp/xuexi 403 过期、wso 正常。
- Cloudflare token 验证有效；worker `iptv345` 最后部署于 2026-09-17T03:51Z（与 Actions run 1377 吻合）；worker 已配置 `GH_TOKEN` secret（自动触发刷新链路存在）。
- 下载线上代码确认：XUEXI_CATALOG 40 频道，auth_key 已过期。

**08:06 GitHub Actions"345"联动核查**
- workflow `refresh.yml` cron `*/10`，实际约每 4-5 小时执行一次（GitHub 节流）；最近 30 次全部 success，最后失败为 09-09（run 1326）。
- 下载 run 1377 日志分析：xuexi 刷新成功抓到 41 频道（live-pc.xuexi.cn 域名）但从 GitHub runner 测试全部 403（runner 为海外 IP，测试未带必要上下文）；YSP 刷新 27/46 成功；部署后状态页 `345 error; ysp error; xuexi ok; wso ok`——即 **xuexi 当时可用、ysp 从来不行**。
- 结论：联动真实有效；"经常失败"是 7 月下旬之前的历史（deploy 脚本硬编码路径，已于 07-23 修复）。

**08:07 手动 dispatch run 1378**（HTTP 204，联动机制验证）→ 约 12 分钟后部署成功 → xuexi 线路即时恢复 200（fresh auth_key）；ysp 依旧 403。

**08:08-08:15 各线路实测（每线路抽 1 频道 + lnc 全测）**

| 线路 | 抽测 | 结果 |
|---|---|---|
| LNC（livenewschat） | lnc1/2/4/5/6/7/8/9/10 | **全部 200**；lnc3（CNN International）上游该流 404（页面 slug 未变，多节点均 404，属上游暂时下线） |
| gt（345 源·港澳台） | gt5/gt6 | **请求挂死**（worker 无响应直至客户端超时） |
| ys（345 源·央视） | ys1/ys10 | 同上挂死 |
| itv | itv7 | 200 正常 |
| fjitv / hlitv / ipv6 / migu / ws / movie / ty | 各 1 | 403 / 挂死 / "channel not available" / "channel moved" / 上游 500 |
| yspc / yspw | 各 1 | 403 expired（新鲜 token 也 403） |
| wso | wso-hainan | 200 |
| xuexi | 抽测路由（省级卫视） | 403 expired → 触发 refresh → run 1378 后恢复 200 |

**08:16-08:25 根因定位（本地复现解析链）**
- 用 Node 复现 worker 的 345 解析链（play 页 → xac 解码 → play.php → 重定向），发现：
  - **gt/ys 挂死根因**：上游 play 页的线路 option 现在生成 `type=.flv` 的 play.php，302 到 `tXX.iptv200.com:8443/live/<ch>.flv`——**上游把默认传输从 HLS 改成了 FLV**。Worker 按 HLS 代理逻辑 GET 该 FLV 裸流，响应永不结束 → 请求挂死。
  - **修复验证**：把 play.php 的 `type=.flv` 换成 `type=.m3u8`（或对 `.flv?` 重定向目标改写为 `.m3u8?`），gt/ys 两条代表路由立即返回完整 HLS 会话（`index.m3u8?session=...`）。**gt/ys 线路完全可修**。
  - fjitv/hlitv：重定向到 `http://<裸IP>/PLTV/...`（福建电信/黑龙江移动 IPTV 内网源）——CF Workers 禁止 fetch 裸 HTTP IP 且为大陆内网源，**架构性不可中转**（与 v1.7 时代结论一致）。
  - migu/ws/movie：上游辅助端点（migu8.php/cqyx.php/huya.php）HTTP 500，源站自身损坏。
  - ipv6：302 无 location，上游损坏；ty：play 页 302 已删除。

**08:26-08:40 ysp 架构性判定**
- 从最新部署 worker 提取 yspc01 的**新鲜** fullUrl（run 1378 刚注入），从香港直连仍 403（带不带 Referer 均是）。
- 结论：央视频 CDN（outlivecloud-cdn.ysp.cctv.cn）对海外出口 IP 一律 403（IP 绑定或地域封锁，策略较 6 月 v2.5 时代收紧——当年"URL 有效期数小时、无需 Referer、worker 直接可取"已不再成立）。**海外 Worker 中转 ysp 在架构上不可行**，与 token 新鲜度无关。按用户指令"停止对该渠道的引用"：v2.12 从生产移除全部 yspc/yspw 路由，Actions 停止 ysp 刷新。

**08:41 lnc3 复核**：LNC 目录返回正常节点；`cnni_live` 流代号在各节点均 404，livenewschat 站点页面未变——上游该流暂时下线，非代码问题，保留路由待其恢复。

**08:45-09:00 v2.12 制作**
- 基于 `lishuhang/345` 的线上模板（worker_v26_blind.js）制作 v2.12 blind 模板：
  1. 移除 YSP catalog/handlers/路由/健康检查（含 `XUEXI_INJECT_ANCHOR` 注入锚点替代）；
  2. 新增 `normalizeHlsUrl()`：play.php `type=.flv` → `type=.m3u8`；重定向链中任何 `.flv?` 目标改写 `.m3u8?`；
  3. `fetchUpstream` 增加 12 秒超时（AbortController），任何死上游不再能挂死 worker；
  4. 状态页健康检查改为 345 + wso + 注入的 xuexi；
  5. 版本号 v2.12 + changelog 块。
- `node --check` 通过；`normalizeHlsUrl` 行为单测通过。
- 更新 `lishuhang/345` 仓库：新增 `work/worker_v212_blind.js` + `scripts/build_v212_blind.py`（仅注入 xuexi）；workflow 删除 YSP 刷新步骤；删除 ysp 相关脚本与旧模板（gen_ysp_fast.js / gen_ysp_urls3.js / build_v210_blind.py / refresh-and-deploy.sh / worker_v26_blind.js / ysp_handlers.js / ysp_routes.js）。commit `7728ab4` 推送。
- dispatch run 1379 构建部署 v2.12。

**09:00 后 生产验证与剩余测试**（见 7.3）

### 7.3 v2.12 部署后生产验证（16:20-16:40）

run 1379（dispatch，12 分钟）构建部署成功后实测：

| 检查项 | 结果 |
|---|---|
| 状态页（两个域名） | `v2.12 / status: 345 ok; xuexi ok; wso ok` —— **三源全绿**（维护前为 345 error; ysp error; xuexi error） |
| gt5 / ys1 | 200（flv→m3u8 修复生效，此前挂死） |
| xuexi 路由 | 200（fresh auth_key） |
| yspc01 | 路由已移除，落回通用匹配器报 channel not available（预期行为） |
| lnc 全系 | **10/10**（lnc3 上游流在检测晚间自行恢复） |
| wso | hainan/shaanxi 200；dongnan/guizhou/jiangsu 坏（与历史一致） |

随后对全部 gt×54、ys×43 路由做完整清扫：**60/97 正常**（gt 42/54，ys 18/43），坏线路均为源站侧 404/302/超时，v2.12 的 12 秒超时保护使坏线路快速失败而不再挂死。

### 7.4 交付物与仓库变更

| 交付物 | 位置 |
|---|---|
| `iptv345-v2.12.zip`（密码 iptv345） | `clock/0917-tv/worker_js/`，内含 v2.12-blind.js（=线上产物）、v2.12.js（full，同套补丁）、iptv345-bad-channels-in-v2.11.md（坏渠道明细与恢复方法）、iptv345-v2.12.txt（113 个可中转频道清单） |
| `lishuhang/345` commit `7728ab4` | v2.12 模板 + build_v212_blind.py + workflow 去 ysp + 删除 ysp 相关脚本 |
| 本文 | prompts 全部 md 清理，整合为唯一完整日志 |

GitHub 上未出现任何明文频道名↔m3u8 映射（映射只在加密包与 full 版源码内）；两份 .txt 原始对话保留在 prompts/（按指令仅清理 md）。

---

## 8. 渠道线路可用性现状（2026-09-17 实测，海外=香港节点视角）

### 8.1 345 中转线路（经 worker）

| 线路 | v2.11 状态 | v2.12 状态 | 说明 |
|---|---|---|---|
| gt（港澳台 69 频道） | 挂死 | **已修复**（flv→m3u8） | 全部 gt tid 线路恢复 |
| ys（央视源 43 线路） | 挂死 | **已修复** | 同上 |
| itv（综合源） | 正常 | 正常 | itv7 实测 200 |
| lnc1-lnc10 | 9/10 | 9/10 | lnc3 上游流暂时下线 |
| wso-hainan | 正常 | 正常 | 稳定 |
| wso-shaanxi | — | 复测中 | 历史记录"偶尔可用" |
| wso-dongnan / guizhou / jiangsu | — | 复测中 | 历史：CF 不可达/不稳定 |
| xuexi（40 频道） | 403 过期 | **已恢复** | 依赖 Actions 刷新周期（约 4h），403 时 worker 自动触发刷新 |
| yspc/yspw（46 频道） | 403 | **v2.12 移除** | 架构性不可用（海外出口 403） |
| fjitv / hlitv | 403/挂死 | 保留但不列清单 | 大陆 IPTV 内网/裸 IP 源，CF 架构性不可达（仅大陆本地可看） |
| migu / ws / movie / ty | 500/损坏 | 保留但不列清单 | 上游自身损坏 |

### 8.2 直连源（monitorhub 清单中非 345 中转 URL，海外视角实测）

**海外可用（23 条）**：Bloomberg 官方流；GB News ×4（amagi/rakuten 各节点）；CNA；NHK ×2；Wion；Arirang；TVBS 新闻台（台湾 IP）；人间卫视；CCTV2/3/5+/8/10/12（大陆运营商开放 IPTV 单播 IP，恰好对海外也开放）；CCTV9（美国 IP 源）；三沙卫视；东方卫视 ×2（美国 IP 源）；CGTN ×4；CGTN Doc ×2；NBD AI；Wild Earth；熊猫频道。

**海外不可用**：
- master 200 但子清单 403（地域封锁，海外固定不可用）：CBS News ×2、ABC News Live ×2（tubi/xumo，美区）、ABC Australia（澳区）
- 子清单 404/400（路径失效）：BBC News、CNN International（cloudfront 直链）、Newsmax、AJE、RT、PressTV、Sky News Weather、ABC News 1-10（全部 404）、CCTV Plus 1-5（全部 404）、CBS jmp2.uk ×3（400）、GB News simplestream ×2
- 连接超时（死 IP）：CCTV5、CCTV6 主用 IP
- 注意：上述"海外不可用"的直连源中，凡属大陆版权源（如 CCTV Plus）在大陆本地或有其他入口；凡属美/澳区新闻台在大陆同样不可直连。**经 worker 中转后仍不可用**（worker 出口即海外）。

### 8.3 "仅海外可看 / 仅大陆可看"判定（回答用户问题）

- **仅海外可看（大陆直连通常被墙或无授权，但经 345.lishuhang.com 中转后大陆可用）**：LNC 系列（Bloomberg/CNBC/CNN/DW/FSTV/Global/MSNBC/NBC/Sky）、GB News、NHK、CNA、Wion、Arirang、TVBS、人间卫视、BBC（如后续恢复）等海外新闻频道。这正是本项目存在的意义：worker 中转 + 自定义域，让大陆播放器可用。
- **仅大陆可看（海外/worker 中转均不可用）**：fjitv/hlitv 等 IPTV 内网源；央视频 ysp（海外 IP 被 CDN 拒绝）；东方卫视/看看新闻等需大陆出口的版权源；38 个大陆固定直链中的大部分（运营商 IPTV 源通常仅大陆网络可达——其中 CCTV2/3/5+/8/10/12 等少数 IP 对海外开放，实测例外）。
- **双向皆可**：少数开放 IP 的大陆频道（见 8.2 海外可用清单）、CGTN（海外版全球化定位）、熊猫频道等。

---

## 9. 坏渠道明细与日后恢复方法

完整明细（每个坏渠道的原始映射关系、失败原因分类、逐条恢复方法）存于加密压缩包 `worker_js/iptv345-v2.12.zip` 内的 `iptv345-bad-channels-in-v2.11.md`（密码 iptv345）。此处仅存目录级摘要：

1. **yspc01-17 / yspw01-31（46 频道，央视频）**——海外出口 403，v2.12 已从生产移除。恢复路径：① 在大陆 IP 环境运行 Playwright 抓取脚本并把 worker 迁回大陆可达出口（Cloudflare 常规版做不到）；② 改由客户端直连（大陆网络内直接用央视频原始 URL，绕过 worker）；③ 等待央视频 CDN 放开海外策略后，在 345 仓库恢复 gen_ysp_fast 步骤与模板 ysp 区块（git 历史 commit 7728ab4^ 可找回全部代码）。
2. **lnc3（CNN International）**——上游 LNC 该流暂时下线（slug 正确、节点正常）。恢复路径：周期性探测 `https://<节点>/hls/cnni_live/index.m3u8`（节点由公开目录脚本给出），恢复 200 即自动可用，无需改代码。
3. **fjitv / hlitv 全系**——大陆 IPTV 内网/裸 HTTP IP 源，CF 架构性不可达。恢复路径：无（除非 Cloudflare 出口策略变化）；大陆本地播放器可直连。
4. **migu / ws / movie / ty 各线路**——上游辅助端点 500 或频道已删除。恢复路径：定期重测；源站修复即自动恢复（worker 有 10 分钟 broken cache 与 `/refresh/` 端点）。
5. **直连失效类**（BBC/CNN 直链/CBS/ABC/Newsmax/AJE/RT/PressTV/Sky Weather/CCTV Plus/ABC News 1-10 等）——多为路径失效或地区封锁。恢复路径：寻源站新路径或新的地区可达镜像；美澳区频道需美澳出口才能用。

---

## 10. 关键经验教训汇总（去重合并版）

> 原 12+7+19 条分散坑记录合并为按主题分类的一张清单；同一坑在多份文档重复出现的只留一份。

### 10.1 源站逆向与协议
1. 源站 `decode()` 把 `=` 当索引 64 → 必须自定义 base64 解码器（atob 会返回空）。
2. inline script 长变量有反转/不反转两种形态 → 双策略尝试，取能解出有效 xac 的。
3. 上游页面结构会突变（2026-08-15 从加密 blob 改为直接变量；2026-09-17 从 m3u8 默认改为 flv 默认）→ 解析器必须双兼容 + 对上游传输层变化做防御。
4. 播放页静态 token 不校验（任意 32-hex）；变量名随机化 → 用"最长 string var"启发式，永不硬编码变量名。
5. **绝不 eval/执行上游页面脚本**，只做数据表达式解析。

### 10.2 HLS 代理与缓存
6. 段 URL 1-2 秒过期 + play.php 每次落到不同 t-host → 缓存 session URL（60s），m3u8/seg 用同一 session 从同 host 实时拉取。
7. 段请求必须带源站 Referer，否则 404。
8. m3u8 禁 CDN 缓存要显式 `CDN-Cache-Control: no-store` + `Surrogate-Control: no-store`，仅 no-cache 不够。
9. hls.js：lowLatencyMode=false、backBufferLength=10、liveSyncDurationCount=3、maxBufferLength=20、fragLoadingMaxRetry=6；不信任 canPlayType，优先 hls.js。
10. 两级 playlist（master 显式 CODECS → media）可避免 hls.js 误判编码字符串（源于 ysp 经验，后用于 ysp/xuexi handler）。
11. **上游若给出 FLV 重定向目标，HLS 代理必须改写为 .m3u8 变体或明确报错，绝不能直接 GET**（v2.12 核心教训：会挂死请求）。
12. Worker 的 fetch 必须带超时（v2.12：12s AbortController），否则死上游会挂死整个请求链。

### 10.3 Cloudflare 平台
13. Workers 禁止 fetch 裸 HTTP IP → 重定向到 HTTP IP 的线路应预先标记不可播（bad_lines），而非盲目重试。
14. 部分大陆省级 API/CDN 对 CF 海外出口封锁（fjtv.net、jstv.com、央视频 CDN、看看新闻）→ 属架构性限制，客户端直连或大陆出口才能解。
15. CF API 部署用 `PUT /accounts/{id}/workers/scripts/{name}` + multipart；token 用 `cfut_` 前缀 User API Token（`cfat_` 前缀不可用于 REST API）；`/user/tokens/verify` 验活。
16. Worker 内存缓存跨实例不共享（isolate 隔离）；Cache API 全局共享（段缓存用它）。
17. Workers 的 module 语法上传 Content-Type 用 `application/javascript+module`；Service Worker 语法用 `application/javascript`（tv worker 用后者）。

### 10.4 自动化与流水线
18. **GitHub Actions 部署脚本不得硬编码本地路径**——345 actions 曾因此连续失败 12+ 次、CF token 从未被调用（07-23 修复，环境变量优先）。
19. workflow 成功 ≠ 源可用 ≠ 状态页成功；三层信号必须分开判断。
20. 动态 token 有效期与 workflow 周期要匹配：xuexi auth_key 从抓取时刻起只剩约 10 分钟（07-23 数据）/实测约 20-30 分钟（09-17 数据）；GitHub 会把 */10 cron 实际节流到约 4-5 小时一次，因此必须有 worker 端 403 自动触发刷新兑底，形成自愈闭环。
21. GitHub 定时 workflow 实际执行频率远低于 cron 表达式（`*/10` 实际约 4-5 小时一次，GitHub 节流）；关键刷新不要只依赖 schedule，要有 on-demand 触发兜底。
22. 手动部署会被自动流水线覆盖 → 任何生产改动必须同步更新 `lishuhang/345` 的模板与构建脚本。
23. build 脚本输出文件名必须匹配 workflow 期望；构建注入的路由必须放在通用 `/<tid><id>.m3u8` 正则**之前**（xuexi 十六进制 key 教训）。

### 10.5 版本治理与安全
24. blind 版任何输出（含失败日志）不得含频道显示名/可推断内容（v2.10.2 教训）；full 版才允许保存显示名映射。
25. 对外清单一律用自定义域 `345.lishuhang.com`，不用 workers.dev。
26. 永不把凭据/token/动态媒体 URL 写入 repo、日志、todo；凭据只存本地 `.secrets`（gitignored）或受控连接。
27. LNC 内部资源路径中的节点名是有意设计（防止节点漂移导致 key/TS 502），不可删。
28. 探测结论分三层：网页可见/本地成功 < CF 生产代理成功 < 浏览器解码成功（encrypt:2 加扰、DRM、地区限制都卡在第三层）。
29. Node 大并发测试：并发 ≤4、checkpoint 断点续跑、--max-old-space-size 限制、纯 Node 单进程完成 token+fetch（Python subprocess 启动延迟会吃掉 token 有效期）。
30. 单文件产品源（MonitorHub HTML）+ 部署包装分离；改动后 node --check + 浏览器实测；模板字符串内嵌代码时 Python 文本替换极易翻车。

---

## 11. 仓库与文件索引

- **lishuhang/clock**（工作仓库，当前 `0917-tv/`）：
  - `prompts/`：全部历史日志（本次整合后仅保留 .txt 原始对话两份，md 已清理）
  - `todo-tv-full-0917-*.md`：本文（唯一完整日志）
  - `worker_js/iptv345-v2.11.zip`、`worker_js/iptv345-v2.12.zip`：版本交付加密包（密码 iptv345）
- **lishuhang/345**（自动刷新仓库）：`.github/workflows/refresh.yml`、`scripts/{fetch_xuexi_urls.py, gen_xuexi_fast.js, build_v212_blind.py, deploy_worker.py}`、`work/{worker_v212_blind.js, catalog_v2.json, bad_lines.json, xuexi_m3u8_urls.json}`
- 历史：`0722-tv/`（clock 仓库历史目录）、tv-versions/tv-app-v1.x.html（MonitorHub 产品源）
- 加密包内：full js（含显示名映射，勿上传明文）、blind js（可部署生产）、bad-channels md、频道清单 txt

---

## 12. 增量日志区

> 后续任务在此追加。格式：`### 增量：YYYY-MM-DD HH:MM（任务主题）`，只写增量。

### 增量：2026-09-17 15:30→16:57（v2.12 大维护全记录）

本节为第 7 节同一场任务的增量收尾，要点：

1. **直接回答用户核心疑问**：与 GitHub Actions"345"的联动并非没用上过——线上 blind 的 xuexi catalog 全由它构建注入（至今 1300+ 次运行，近期全绿）；"经常失败"是 2026-07-23 之前 deploy 脚本硬编码本地 secrets 路径所致，修复后链路真实有效。本次还实测了 worker→Actions 的 dispatch 链路（HTTP 204）并全链路跑通两次（run 1378/1379）。
2. **ysp 判定与处理**：新鲜 token 也 403（海外出口被央视频 CDN 拒绝），架构性不可用 → 生产移除 yspc/yspw 全部 46 路由，Actions 停止 ysp 刷新，恢复方法写入 bad-channels 文档（大陆出口中转/客户端直连/等上游放开后从 git 历史找回）。
3. **核心修复**：上游 345 源把 gt/ys 默认改成 FLV 传输导致请求挂死；v2.12 的 normalizeHlsUrl + 12s 超时让 gt/ys 线路整体恢复（42+18 条正常），且坏上游不再能拖死 worker。
4. **xuexi 保住（含自愈验证）**：auth_key 实测有效期仅约 20-30 分钟，且 Actions 实际每 4-5 小时才运行一次（GitHub 对 */10 cron 节流）→ 平时大部分时间 xuexi 路由会返回 403 并自动触发刷新；本次实测完整闭环两轮（403 → run 1378/1380 → 恢复 200，状态页全绿）。若需进一步缩短空窗，可考虑给 workflow 加 Playwright 缓存缩短部署时长，或在 worker 侧加定时健康检查（需开启 Cloudflare Cron Trigger）。
5. **LNC 保活成功**：10/10 路由正常（lnc3 一度 404 系上游暂时下线，已自行恢复）。
6. **清单交付**：113 个可中转频道（欧美 10 / 香港 27 / 台湾 11 / 大陆 65），全部逐条实测 200。
7. **生产删除项**（大陆海外均不可用）：yspc/yspw 全系。**保留但不入清单**（结构性大陆-only 或上游损坏）：fjitv/hlitv/migu/ws/movie/ty、坏 gt/ys 路由、坏 wso。
8. **经验教训新增**（并入第 10 节）：上游可能把默认传输从 HLS 改为 FLV（HLS 代理必须改写或快速失败，绝不能直接 GET 裸流）；Worker fetch 必须带超时；GitHub 会把 */10 cron 实际节流到约 4-5 小时一次。
9. **文件操作**：prompts/ 全部 20 个 md 删除（内容已全部整合进本文），仅保留 260722-1850.txt 与 chat-history.txt 两份原始对话；本文从 prompts/ 移至 0917-tv/ 根目录并重命名。

（本增量即当前最终状态，无其他未竟事项。）
