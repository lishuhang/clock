# 在其他 Agent 中使用 TapNow

> 来源：https://docs.tapnow.ai/zh/docs/mcp/use-tapnow-in-other-agents
> 抓取时间：2026-09-23 11:41（离线快照，原文见链接）

# 在其他 Agent 中使用 TapNow

把 TapNow 的生成能力接到你习惯使用的 Agent 里，直接在对话中出图出片，成品自动进入你的 TapNow 画布。

你正在 Claude 里写一份产品方案，写到一半需要配图。不用切回 TapNow、不用重新描述需求，直接在同一段对话里说「给这三个章节各配一张图」，图就生成好了，并且自动出现在你的 TapNow 画布里。

你正在某个 Agent 里写一份产品方案，写到一半需要配图。不用切回 TapNow、不用重新描述需求，直接在同一段对话里说「给这三个章节各配一张图」，图就生成好了，并且自动出现在你的 TapNow 画布里。

这是通过 MCP 连接实现的。MCP 是一种让 Agent 调用外部服务的公开协议，TapNow 提供了自己的 MCP 服务，任何支持该协议的 Agent 都可以连上。

## 连上之后能做什么

| 你可以让 Agent 做的事 | 结果 | 是否消耗 Tapies |
| --- | --- | --- |
| 生成一张成品图 | 一句描述出一张高质量图片 | 是 |
| 生成一条短视频 | 一句描述出一条短视频，也可以让一张静态图动起来 | 是 |
| 做一套电商组图 | 一张产品图出白底、场景、多角度、细节全套 | 是 |
| 做一套演示配图 | 一份大纲出整套风格统一的章节配图 | 是 |
| 改成各平台尺寸 | 把一张图改成小红书、公众号等平台规格 | 否 |
| 检索素材库 | 按关键词或文件夹找出你已有的素材 | 否 |
| 存进素材库 | 把生成结果保存到指定文件夹，长期复用 | 否 |
| 查看画布列表 | 列出你最近的画布，确认在哪张画布里工作 | 否 |

生成消耗的 Tapies 与你直接在 TapNow 里生成一致。

生成前先确认数量和类型

Agent 可以连续提交多个生成任务。如果你不确定这次要花多少，先让它把计划说清楚再执行，例如「先告诉我要生成几张、用什么比例，等我确认再开始」。

## 成品去哪里

所有生成结果都会进入你自己的 TapNow 画布，和你在 TapNow 里直接生成的内容放在一起。Agent 会在回复里附上画布链接，点开就能回 TapNow 继续精修、排版或导出。

素材库也是同一份。Agent 能找到的素材，就是你在 TapNow 里看到的素材。

## 开始之前需要什么

- 一个 TapNow 账户，生成会使用这个账户的 Tapies。
- 一个支持 MCP 的 Agent。
- 连接时用浏览器登录一次 TapNow 完成授权，之后不需要重复登录。

## 下一步

如果你用的是 Claude 或 ChatGPT，从[添加自定义连接器](https://docs.tapnow.ai/zh/docs/mcp/add-a-custom-connector) 开始。如果你在 WorkBuddy、千问办公或豆包工作里工作，从[通过官方插件添加](https://docs.tapnow.ai/zh/docs/mcp/add-through-an-official-plugin) 开始。

其他支持 MCP 的客户端也可以用同样的地址连接，步骤与 Claude 一致。

如果你的 Agent 支持自己填写 MCP 连接器，从[添加自定义连接器](https://docs.tapnow.ai/zh/docs/mcp/add-a-custom-connector) 开始。如果你在 WorkBuddy、千问办公或豆包工作里工作，从[通过官方插件添加](https://docs.tapnow.ai/zh/docs/mcp/add-through-an-official-plugin) 开始。

[上一页参加 Arena 比赛](https://docs.tapnow.ai/zh/docs/publish/join-an-arena-event)

[下一页添加自定义连接器](https://docs.tapnow.ai/zh/docs/mcp/add-a-custom-connector)
