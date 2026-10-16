# Android Pad 微信桥（推荐实现）+ W365 角色

## 为什么 pad 是微信桥首选

| 维度 | Android pad（通知监听） | W365（wxauto UI 自动化） |
|---|---|---|
| 机制 | **系统级 API**（NotificationListenerService） | 模拟点击微信窗口 |
| 微信升级影响 | 基本无 | 大版本更新即失效 |
| 登录保活 | 微信手机+平板**官方支持共存**，长期在线 | 用户反馈可能 24h 需重新扫码（微信风控，无法绕过） |
| 实现成本 | AutoX.js 脚本已写好 | Python 脚本+常驻+窗口管理 |
| 结论 | **首选** | 备选/当 pad 不可用时 |

微信在船上不可用，所以 pad 桥的定位仍是**信息供给侧**：把家人/老公的微信消息中转上船，
以及反向让你从 WhatsApp 指挥发微信。

## Pad 部署（10 分钟）

1. **AutoX.js**：GitHub 搜 AutoX/AutoX.js Releases 下载 apk 安装（开源免费）
2. pad 上登录**老婆的微信**（保持 WiFi + 充电 + 屏幕常亮建议）
3. 授权链：设置 → 通知使用权 → 给 AutoX.js；电池 → 不限制/后台允许
4. 把 `wechat_notify.js` 传进 pad（AutoX.js 目录），编辑顶部两处：
   - `AGENT_KEY`（部署 Worker 时生成的那串）
   - `FORWARD_KEYWORDS`（建议填 ["爸","妈","家"] 之类过滤，或 null 全转）
5. 运行脚本 → 从你的微信给老婆的微信发条测试 → 你的 WhatsApp 应收到 `💬 Pad微信 […]`
6. AutoX.js 里设置开机自启（若有系统权限则配合"最近任务锁定"）

## 反向通道（WhatsApp → 微信）

已内置：你从 WhatsApp 发「回微信 @联系人 内容」→ Worker 写 KV 队列 →
pad 端如需执行回复，可用 AutoX.js 再加一个轮询脚本（读 Worker `/state?key=wx_outbox`
后用 AutoInput 模拟点击发送——脆弱，可选；大多数时候你直接用自己手机微信发更省事）。

## 心跳监控

脚本每 10 分钟写 KV `pad_bridge_heartbeat`。查询存活：

```bash
curl -s "https://cruise-bot.lishuhang.workers.dev/state?key=pad_bridge_heartbeat" \
  -H "x-agent-key: $AGENT_KEY"
```

## W365 的新角色（Mac 移出关键路径后）

W365 是你**唯一常驻的通用计算节点**，定位"重活执行器"而非消息通道：

| 任务 | 说明 | 优先级 |
|---|---|---|
| wxauto 微信桥 | 若 pad 方案不畅（如通知被折叠严重）再启用；接受 24h 扫码风险 | 备选 |
| Playwright 定时抓取 | 需要 JS 渲染的站点（公众号文章列表、某些新闻源）→ 抓完 POST /send 或 /state | 可选增强 |
| RSSHub 自建 | 想追小红书博主/话题时：W365 跑 Docker RSSHub + 导出老婆小红书 cookie；feed 变更触发推送 | 可选增强 |
| 备用出口/手动救火 | 任何链路挂了，RDP 上去手动跑脚本 | 应急 |

注意：**定时任务不需要 W365**——GitHub Actions 免费额度完全够（已配好），W365 只在
"需要常驻软件/长会话/微信生态"时才上场。
