# TapNow 更新日志

> 来源：https://docs.tapnow.ai/zh/docs/changelog
> 抓取时间：2026-09-23 11:41（离线快照，原文见链接）

# TapNow 更新日志

了解 TapNow 最新的功能、重要改动、修复与公告。

v2.17.0

2026年9月12日

## 把画布节点收成一叠

在画布上选中两个以上的图片、视频、音频或文字节点，点击选区工具栏中的****堆叠****，它们会收拢成一叠，只占一个节点的位置。单击这一叠可以展开查看全部内容，把其中一个节点拖回画布即可单独使用。一叠最多放 50 个节点；删除一叠会同时删除里面的节点。

[查看堆叠节点教程 →](https://docs.tapnow.ai/zh/docs/canvas/stack-nodes)

## 选择批量生成结果的排列方式

打开****画布设置****，在****批量生成结果****中选择****堆叠****或****铺开****，决定一次生成多个结果时它们在画布上的默认排列。该设置只影响之后的批量生成，已经在画布上的节点不会被重新排列。

[查看堆叠节点教程 →](https://docs.tapnow.ai/zh/docs/canvas/stack-nodes)

## 重新生成不再覆盖原结果

在已经有结果的图片、视频或文字节点上再次点击生成，原来的结果会留在画布上，新结果放进新建的节点，按****批量生成结果****选择的方式摆放。新节点沿用原节点的输入连线，生成次数默认为一次，方便对比几次尝试的差别。音频节点仍然直接在原节点上更新。

[查看堆叠节点教程 →](https://docs.tapnow.ai/zh/docs/canvas/stack-nodes)

v2.16.1

2026年9月9日

## 应用市场上线分镜预演

在****应用市场****中打开****分镜预演****，可以在开拍前把剧本拆成可预演的镜头、动作、节奏和转场。打开详情后选择****在对话中试用****，示例指令会带入 Agent；也可以选择****添加到对话****，再补上自己的剧本或场景文字、时长与镜头数限制，以及参考图或参考视频。剧本越完整，拆出的镜头方案越贴近实际拍摄。

[查看 Apps 使用方法 →](https://docs.tapnow.ai/zh/docs/agent/apps)

v2.15.14

2026年9月9日

## 为 Seed audio 1.0 添加图片参考

在音频节点选择 ****Seed audio 1.0**** 后，可以在参考区添加 1 张 JPG、PNG 或 WebP 图片（最大 10MB），也可以添加最多 3 段参考音频。图片和音频不能同时使用，生成前请检查页面提示和预计消耗。

[查看音频生成教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-audio)

v2.15.11

2026年9月8日

## Creative OS 应用商城上线

打开侧边栏中的****应用市场****，可以按****应用****、****官方技能****或具体用例查找工具。当前目录提供白模视频预演、图片3D建模、电商设计室、角色工坊和分镜预演等用例；打开详情后选择****在对话中试用****，对应 Prompt 会带入 Agent，也可以选择****添加到对话****后补充自己的素材和要求。

[查看 Apps 使用方法 →](https://docs.tapnow.ai/zh/docs/agent/apps)

v2.15.10

2026年9月8日

## 查看 Agent 任务进度和历史

Agent 执行较长任务时，对话会显示当前步骤和进度；完成后可以展开任务历史，查看已完成的动作和结果。这样可以在同一段对话中继续补充要求，也能回看任务过程。

[查看 Agent 对话教程 →](https://docs.tapnow.ai/zh/docs/agent/chat-with-agent)

v2.15.3

2026年9月3日

## TapTV 创作者主页显示新徽章

打开 TapTV 创作者主页，可以看到创作者获得的本地化身份徽章，例如****视觉大使****、****TapTV 签约工作室****、****TapNow 优质创作者****和****先锋创作者****。这些徽章也会显示在创作者身份信息中；不同创作者主页显示的徽章可能不同。

[查看 TapTV 教程 →](https://docs.tapnow.ai/zh/docs/publish/publish-to-taptv)

v2.15.0

2026年9月2日

## 批量下载画布中的媒体

在画布中选中多个图片、视频或音频节点，点击选区工具栏中的****批量下载****。Creative OS 会把可下载的源文件打包后下载；文字、空节点和仍在生成的节点会自动跳过。

[查看批量下载教程 →](https://docs.tapnow.ai/zh/docs/canvas/download-in-batches)

v2.13.33

2026年9月2日

## 使用 MiniMax H3 Max 高速生成视频

MiniMax H3 Max 是 H3 系列的高速版本，适合快速试片和反复调整方向。它支持文生视频和图生视频，可生成 5–15 秒、480P 或 768P 的原生音频视频。你可以在视频生成节点或 Agent 的确认卡片中选择该模型。

[查看视频生成教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-video)

v2.13.23

2026年8月27日

## Agent 可整理桌面文件夹

在 TapNow Desktop 中，把一个本地文件夹授权给 Agent，再说明要创建哪些子文件夹、移动或重命名哪些文件。Agent 会先显示整批操作供你确认；确认后只在该文件夹内执行，任一步失败都会撤回已经完成的更改。

[查看 Agent 对话教程 →](https://docs.tapnow.ai/zh/docs/agent/chat-with-agent)

v2.13.18

2026年8月25日

## 从 App 示例开始任务

打开 App 详情，可以查看图片或视频示例，并把示例指令放入 Agent 输入框。通过输入框的 ****+**** 添加 App 后，也可以点击显示的示例，再按当前任务修改内容。

[查看 Apps 教程 →](https://docs.tapnow.ai/zh/docs/agent/apps)

## 调整 Agent 的思考等级

开始新对话前，打开模型菜单可以查看模型说明，并为支持的模型选择 ****Off****、****Light****、****Standard**** 或 ****Heavy****。发送第一条消息后模型会锁定，但仍可从旁边的思考控件调整等级。

[查看 Agent 对话教程 →](https://docs.tapnow.ai/zh/docs/agent/chat-with-agent)

## 生成音频前调整设置

使用手动确认模式让 Agent 生成音频时，可以先在确认卡片中检查或修改模型、时长、音色和当前模型支持的其他设置。点击****生成****后才会调用模型并消耗 Tapies，结果会出现在画布上。

[查看生成模式教程 →](https://docs.tapnow.ai/zh/docs/agent/choose-a-generation-mode)

v2.13.17

2026年8月25日

## 下载 Windows 版 TapNow Desktop

在 Windows 64 位电脑上打开 TapNow 全球站下载页，选择****下载 Windows 版****即可获取安装包。macOS 仍提供 Apple 芯片版本；中国区桌面版仍在准备中。

[查看下载与更新说明 →](https://docs.tapnow.ai/zh/docs/account/troubleshooting)

## 让 Agent 解读共享画布

在电脑上打开只读画布分享页并选择****解读创作思路****，TapNow 会先克隆画布，再打开可编辑副本并让 Agent 根据节点和连线开始讲解。原画布不会改变；需要登录，预计消耗 40–150 Tapies，手机端暂不显示该入口。

[查看分享与克隆教程 →](https://docs.tapnow.ai/zh/docs/projects/share-and-clone)

v2.13.16

2026年8月24日

## 手动检查 TapNow Desktop 更新

在已安装的 TapNow Desktop 中打开设置并点击****点击检查更新****，应用会检查并下载可用更新。准备完成后，按页面提示选择****立即更新****或****重启并更新****；更新前先确认当前画布已经保存。

[查看下载与更新说明 →](https://docs.tapnow.ai/zh/docs/account/troubleshooting)

v2.13.15

2026年8月24日

## Wan 3.0 上线视频生成

在视频生成节点中选择 Wan 3.0，可以使用文字、首帧或 1–10 张参考图生成带声音的视频。支持 480P、720P 和 1080P，可选择 2–30 秒或自动时长；能否看到该模型取决于当前账户的模型权限。

[查看视频生成教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-video)

v2.13.14

2026年8月22日

## Agent 可直接完成 App 授权

当任务需要连接外部服务时，Agent 会在对话中显示授权入口。完成授权后回到同一段对话，即可继续原来的任务。

[查看 Apps 教程 →](https://docs.tapnow.ai/zh/docs/agent/apps)

v2.13.12

2026年8月20日

## 企业团队支持 SSO 登录

已开通企业 SSO 的团队成员可以在登录页选择 ****使用 SSO 继续****，输入公司域名并完成组织登录。SSO 账户与个人账户相互独立；入口仅对已配置的企业开放。

[查看团队与权限教程 →](https://docs.tapnow.ai/zh/docs/account/manage-teams-and-permissions)

## 切换和重命名画布更直接

进入画布后，点击左上角画布名称旁的箭头，可以搜索、切换或新建画布；点击画布名称即可直接重命名。点击 TapNow 标志会返回画布首页。

[查看画布管理教程 →](https://docs.tapnow.ai/zh/docs/projects/manage-canvases)

v2.13.11

2026年8月20日

## Agent 可引用更多画布内容

在 Agent 输入框中输入 ****@****，可以把画布节点、素材库资产、主体和文件夹加入任务。发送前仍可检查并移除不需要的引用。

[查看 Agent 对话教程 →](https://docs.tapnow.ai/zh/docs/agent/chat-with-agent)

## 节点标记更清楚

画布节点的标记入口和选中状态更容易辨认，整理大量素材时可以更快确认节点是否已经标记。

v2.13.9

2026年8月19日

## 优化画布分享与克隆

通过分享链接打开和克隆画布时，流程更顺畅，继续使用他人分享的内容更稳定。

v2.13.8

2026年8月19日

## 平板支持完整画布

现在可以在 iPad 和 Android 平板上进入完整画布，查看节点、与 Agent 对话并继续创作。手机仍使用适合小屏幕的访问方式。

[查看画布入门教程 →](https://docs.tapnow.ai/zh/docs/canvas/explore-the-canvas)

v2.13.7

2026年8月19日

## 素材库操作更直接

点击素材内容即可把图片、视频或音频加入画布；点击文件夹会展开或收起内容，主体会打开编辑页。通过预览仍可先查看素材再应用。

[查看素材库教程 →](https://docs.tapnow.ai/zh/docs/canvas/use-library-and-templates)

v2.13.6

2026年8月18日

## 优化 Agent 联网搜索

Agent 联网搜索的整体体验更顺畅，查找公开资料、事实和创作参考时更好用。

v2.13.5

2026年8月18日

## 页面浏览与登录更顺畅

打开 Creative OS、浏览页面和完成登录时更顺畅，日常使用更稳定。

v2.13.4

2026年8月17日

## 运行整组前查看预计 Tapies

对一组节点选择 ****整组执行**** 后，确认窗口会尝试显示预计 Tapies。你可以确认或取消；最终消耗以任务完成后的实际结算为准。

[查看节点组教程 →](https://docs.tapnow.ai/zh/docs/canvas/use-library-and-templates)

## 优化 Agent 效果

Agent 处理创作任务时效果更稳定，任务衔接和结果呈现更顺畅。

v2.13.3

2026年8月15日

## Seedance 2.5 支持 1080p

在画布中选择 Seedance 2.5 生成视频时，可以打开 ****清晰度****，选择 ****1080p****。****首尾帧****、****全能参考****和****视频编辑****均支持这一选项；新任务仍默认使用 720p。

[查看视频生成教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-video)

v2.13.1

2026年8月14日

## Agent 可以一次确认多个问题

当 Agent 需要补充多项信息时，问题会显示在输入框上方。你可以逐题回答最多 4 个问题，提交后仍能在对话中查看回答摘要。

[查看 Agent 对话教程 →](https://docs.tapnow.ai/zh/docs/agent/chat-with-agent)

v2.12.29

2026年8月12日

## 3D 内容支持先预览，再进入片场

打开 3D 资产、全景图或 3D 场景时，可以先旋转或环视查看内容。点击 ****打开取景器****，再点击 ****拍摄****，照片会直接添加到画布；需要继续布景时，选择 ****在 3D 片场中使用****。

[查看 3D 教程 →](https://docs.tapnow.ai/zh/docs/canvas/create-text-and-3d)

## MiniMax H3 支持主体库引用

在视频节点中选择 MiniMax H3 的 ****参考****模式后，可以点击 ****添加主体****，从主体库选择视觉参考并用于生成。该入口不适用于多镜头模式；一次最多可使用 9 张图片、3 段视频和 3 段音频，音频需要与图片或视频一起使用。

[查看主体教程 →](https://docs.tapnow.ai/zh/docs/canvas/create-and-use-elements)

v2.12.28

2026年8月12日

## 让 Agent 解读 TapTV 项目的创作思路

在桌面端打开 TapTV 项目预览后，点击 ****解读创作思路****，TapNow 会克隆项目、打开可编辑画布，并让 Agent 结合节点与连线开始讲解。原公开项目不会改变；该功能需要登录，预计消耗 40–150 Tapies，手机端暂不显示此入口。

[查看 TapTV 教程 →](https://docs.tapnow.ai/zh/docs/publish/publish-to-taptv)

v2.12.19

2026年8月7日

## 视频支持延长镜头和分段重拍

选中视频节点后，可以使用 ****延长镜头****，为片头或片尾补充 4–30 秒内容；也可以使用 ****视频重拍****，按时间段重新设置机位、景别和运镜。两项功能均为 Beta，结果会作为相连的新节点加入画布，原视频仍然保留。

[查看视频编辑教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-video)

v2.12.18

2026年8月7日

## Seedance 2.5 上线画布与 Agent

在视频节点或 Agent 的生成确认卡中，可以选择 Seedance 2.5，设置生成模式、参考素材、4–30 秒时长和输出规格，再把结果生成到画布。参考模式最多可加入 30 张图片、10 段视频和 10 段音频；是否显示该模型，以当前账户可用选项为准。

[查看 Seedance 2.5 教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-video)

## MiniMax H3 支持 768P、4 秒和 9 张参考图

在视频节点中选择 MiniMax H3 后，可以把 ****清晰度****设为 768P 或 2K，把时长设为 4–15 秒，并在参考模式中加入最多 9 张图片。新任务仍默认使用 2K、5 秒；生成前可以查看更新后的预计 Tapies。

[查看 MiniMax H3 教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-video)

v2.12.13

2026年8月5日

## Seed audio 1.0 支持参考音频生成

在音频节点中选择 Seed audio 1.0，输入提示词并添加最多 3 段参考音频，即可设置格式、字幕和高级参数后开始生成。结果会显示为可播放的音频波形；开启字幕时，画布还会创建相连的音频字幕文本节点。当前暂不支持图片参考。

[查看音频生成教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-audio)

v2.12.10

2026年7月31日

## 历史记录支持搜索和批量放回画布

打开画布左侧的 ****历史**** 后，可以搜索生成过的图片、视频、音频和 3D 内容；展开面板后，还能在 ****所有项目**** 与 ****当前项目**** 之间切换范围。点击 ****选择**** 后，可以一次把多项内容应用到画布或下载。历史保存的是生成结果，不是整张画布的快照。

[查看历史记录教程 →](https://docs.tapnow.ai/zh/docs/canvas/organize-your-canvas)

v2.12.9

2026年7月31日

## MiniMax H3 上线视频生成

在视频节点中选择 MiniMax H3，可以通过 ****首尾帧**** 或 ****参考****生成带原生音频的视频。首发支持 2K、5–15 秒，参考模式最多可加入 5 张图片；后续规格扩展见上方版本。

[查看 MiniMax H3 教程 →](https://docs.tapnow.ai/zh/docs/canvas/generate-and-edit-video)

v2.12.5

2026年7月29日

## 主体库支持复用人物、产品和角色

在画布左侧打开 ****素材库**** 与 ****主体库****，可以从画布或本地文件新建主体，并保存到个人或团队空间。之后在支持的模型中选择 ****参考**** 模式，通过 ****添加主体**** 或 `@` 再次使用同一人物、产品或角色。

[查看主体库教程 →](https://docs.tapnow.ai/zh/docs/canvas/create-and-use-elements)

按月份浏览

[2026年9月](#month-2026-09)[2026年8月](#month-2026-08)[2026年7月](#month-2026-07)
