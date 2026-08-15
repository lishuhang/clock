# 345 自动刷新链路审计（2026-08-15，GMT+8）

## 结论

既有 `lishuhang/345` 仓库的 **Refresh and Deploy** 工作流不是幻觉，也不是从未运行成功：审计时最近 100 次记录均为 GitHub 标记的成功完成。该结论不等于所有频道均可播放，因为原工作流用 `|| true` 容错 URL 抓取失败，且其旧验证只检查状态页输出；但它确实完成了“Playwright 抓取 → 构建 → Cloudflare 上传 → Workers 子域名启用”的真实发布闭环。

| 项目 | 外部可核验证据 | 观察 |
|---|---|---|
| 既有工作流 | `https://github.com/lishuhang/345/actions/workflows/refresh.yml` | 定时表达式为每 10 分钟；工作流会安装 Playwright，分别刷新 xuexi、YSP、再次刷新 xuexi，再构建、部署和验证。 |
| 历史运行 | `https://github.com/lishuhang/345/actions/runs/31868269172` | 日志显示构建时保留 46 个 YSP 频道，其中 32 个拿到新 URL；加载 40 个 xuexi 频道；上传 Worker 返回 HTTP 200。旧状态页仍显示 `345 error; ysp error; xuexi ok; wso ok`，证明“工作流成功”不足以表示全源可播。 |
| 本轮修复提交 | `https://github.com/lishuhang/345/commit/3577738` | 修复 345 页面从旧加密 blob 改为直接变量表达式后导致的解析失败；同时将 xuexi 路由移至通用 345 URL 匹配器之前，避免误路由。没有新建 Worker、工作流、域名或其他云实体。 |
| 本轮人工触发 | `https://github.com/lishuhang/345/actions/runs/31870320247` | 通过既有 `workflow_dispatch` 运行，完整 8 分 6 秒并成功完成抓取、构建、部署与验证。 |

## 生产验证

在运行 `31870320247` 成功后，`https://345.lishuhang.com/` 显示版本 **v2.10.1**。代表性验证显示：

| 路由 | 结果 | 说明 |
|---|---|---|
| `https://345.lishuhang.com/gt5.m3u8` | 200，返回 HLS 媒体清单 | 旧“long encrypted blob not found”已消失；连续两段测试中 1 段成功、1 段 502，说明源站段稳定性仍需按线路评估。 |
| `https://345.lishuhang.com/xuexi_416c4a41.m3u8` | 200，连续 2 段均成功 | 已证实 xuexi 由通用 345 路由误处理的问题得到修复。 |
| `https://345.lishuhang.com/yspc16.m3u8` | 200 | 央视频仍是动态部分可用：一个已过期的 CCTV 路由可返回 502，而其他刷新成功的频道可用。 |
| `https://345.lishuhang.com/wso-shaanxi.m3u8` | 本轮曾 200，后一次超时 | 卫视官网源具有源站波动，应只作为备用，不应覆盖更稳定线路。 |

## 工作流的实际局限

1. YSP 抓取脚本本轮日志只刷新 32/46 个频道，剩余频道保留旧动态 URL，故旧 URL 可能很快 403。
2. xuexi 授权 URL 是短期动态数据；工作流的双刷新策略可以缩小空窗，但不能把它变成永久链接。
3. 原工作流以 `|| true` 继续执行各抓取步骤，因此应把抓取数、部署成功和最终源传输测试分开判断。
4. GitHub Actions 当前提示依赖的 Node.js 20 已弃用、运行器强制以 Node 24 执行。这是警告而非本轮失败原因；为遵循最小变更原则，本轮未升级无关动作版本。
