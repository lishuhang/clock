# 1103-agent-downloader — 8 平台视频下载任务

> 任务目标：从 **YouTube / Instagram / X / Threads / 微博 / 抖音 / 小红书 / 哔哩哔哩** 各成功下载 1 个视频，并获取准确的来源 URL、作者、标题、摘要。
> 本轮（2026-11-03）已完成**可行性调研，未实抓**。全部结论以实测数据为准，写在 findings/。

## 文件地图

| 文件 | 用途 |
|------|------|
| `RESUME.md` | **新会话恢复协议** —— 任何接手 agent 第一件事读它 |
| `state.json` | 机器可读当前状态（phase / next_task / blocked_on），单一事实来源 |
| `todo.md` | 下轮实抓的分阶段执行计划（含精确命令与回退路径） |
| `worklog.md` | 结构化追加式工作日志（本轮 W001–W008） |
| `findings/00-environment.md` | 沙盒环境与网络实测事实 |
| `findings/01-feasibility-matrix.md` | 8 平台可行性总矩阵 |
| `findings/02-platform-notes.md` | 分平台方案细节 + 来源引用 |
| `findings/03-pitfalls.md` | 已知坑总清单（含上一轮会话的血脉传承） |
| `findings/04-continuity-protocol.md` | worklog/state 设计规范：防上下文崩溃、防概括丢细节、防 token 狂烧 |
| `tools/` | 探针/检查脚本（可复跑） |
| `logs/` | 原始输出（worklog 只存指针，全文在此） |

## 一句话现状

环境意外地好（香港出口、16/16 域名网络层全通、ffmpeg+playwright 预装），难点不在网络而在**各平台反爬签名/风控**；8 平台中 7 个有明确主通路，Threads 靠 `tribixbite/yt-dlp-threads` 插件（Googlebot UA SSR 绕过）。详见矩阵。
