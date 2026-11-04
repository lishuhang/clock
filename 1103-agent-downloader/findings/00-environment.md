# findings/00 — 沙盒环境与网络实测事实

> 全部为 2026-11-03 实测，原始输出在 `../logs/`。本文件是"环境边界"的唯一事实来源。

## 1. 算力与运行时

| 项 | 值 |
|---|---|
| 内核/系统 | Linux 5.10.134-013.15.kangaroo.al8.x86_64 / Debian 13 (trixie) |
| CPU/内存 | 2 核 / 4.1GiB（free 可用 ~3.6GiB） |
| 磁盘 | 9.9G 总量，~9.3G 可用 |
| Python | 3.12.16，venv 位于 `/home/z/.venv`（`python3` 即指向它，pip 直装可用） |
| Node | v24.22.2 |
| git / curl | 2.47.3 / 8.14.1 |
| ffmpeg | **7.1.5 预装**（合并 DASH 流无需另装） |
| Playwright | **1.57.0 + chromium-1200 预装**（真浏览器兜底通路现成） |
| 无代理 | 环境变量无任何 proxy 设置 |

## 2. 网络出口（双源确认）

- ipinfo.io：`"ip": "8.212.10.159", "city": "Hong Kong", "org": "AS45102 Alibaba (US) Technology Co., Ltd."`
- B站 zone API：`"addr":"47.57.232.232","country":"香港","isp":"阿里云"`

**含义**：非大陆出口 → YouTube/Google/Instagram/X/Threads 无 GFW 阻碍；同时国内平台（微博/抖音/小红书/B站）对香港 IP 不做区域封锁（HTTP 200/301/302 全通）。**网络不是本任务的约束项**，约束项只剩各平台反爬签名与风控。

## 3. 16 域名连通矩阵（HTTP 状态码 / 耗时）

| 域名 | 状态 | 备注 |
|---|---|---|
| github.com | 200 | |
| api.github.com | **403(无token)** | 带用户 token 后正常（rate 4999/5000）；**访问必须带 token** |
| raw.githubusercontent.com | 301 | 正常重定向 |
| google.com / youtube.com | 200 / 200 | 无 GFW |
| instagram.com | 200 | 网络通；内容层登录墙是另一回事 |
| x.com | 200 | |
| threads.net | 301 | 正常（www 跳转） |
| weibo.com / m.weibo.cn | 302 / 302 | 正常跳转 |
| douyin.com | 200 | |
| xiaohongshu.com | 302 | |
| bilibili.com / api.bilibili.com | 302 / 301 | **网络通 ≠ API 可直调**（数据中心 IP 会 412 风控，见 03-pitfalls 坑7） |
| pypi.org | 200 | pip 安装无忧 |

## 4. GitHub 协作参数

- token 位置：`/home/z/my-project/.secrets/github_token`（login=lishuhang，对 clock 有 admin/push）
- 仓库 `lishuhang/clock`：public，main 分支，**size 5,945,251 KB ≈ 5.8GB → 只能 sparse clone**
- 工作约定：本任务的一切产物放 `1103-agent-downloader/` 子目录；根 `worklog.md` 是用户级日志（追加条目遵守其 Task ID/Agent/Task/Work Log/Stage Summary 格式）
- `.gitignore` 已含 `.secrets`、`.state`——密钥绝不入库

## 5. 与"已知报告"的差异修正（重要）

| 传闻/上轮报告 | 本轮实测 |
|---|---|
| "沙盒里 yt-dlp 无法访问使用" | 本环境 yt-dlp 未预装（现已装 2026.10.26）；**网络到 YouTube 完全通**。上轮失败真因是 Google 对数据中心 IP 的 bot check（见 03-pitfalls 坑11），不是沙盒断网 |
| "python 脚本无法运行" | venv 完好、pip 通畅、playwright+chromium 现成，脚本可正常跑 |
| "web 检索看不到围墙花园内容" | 属实。小红书/抖音/微博站内内容确实搜不到，只能靠站内 URL 直攻（本任务正是这么规划的） |
