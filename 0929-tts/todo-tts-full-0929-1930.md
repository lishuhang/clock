# TTS 项目全量开发日志（单一事实源）

> 文件名时间戳：0929-1930（GMT+8，任务完成时刻）
> 本文档合并并取代以下已删除的历史文档：`For_Agents/Todos/260523-indextts-todo.md`、`For_Agents/Todos/260523-tts-voice-lab-readme.md`、`For_Agents/Todos/260701-nicevoice-readme.md`
> 此后所有开发日志增量写入本文件（合并同类项，不另开新文档）。
> 最后更新：2026-09-29 19:30（GMT+8）

---

## 1. 一分钟读懂当前事态

- **生产环境**：`tts.lishuhang.com`（workers.dev: `tts.lishuhang.workers.dev`），Cloudflare Worker 服务名 `tts`。
- **线上实际版本**：v2.21.1（2026-09-29 19:19 GMT+8 部署，当日热修版）。v2.20.1 历史源文件已通过 CF API 取回存档；自 v2.20.2 起每次发版均归档脱敏副本至 `For_Agents/backups/`。
- **文件头注释陷阱**：线上源码头注释写的是 "v2.18"，changelog 缺失 v2.15~v2.18、v2.20、v2.20.1 条目，均系热更新时未同步维护所致，本次发版一并修正。
- **备用 worker**：`tts2`（tts2.lishuhang.com）为 v2.19.0 快照（2026-08-04），可视为 staging；`nicevoice` worker（v1.16.6，2026-06-24）是旧的多通道实验品，已停止迭代。
- **渠道现状**（2026-09-29 实测）：
  | 渠道 | 上游 | 状态 | 决定 |
  |---|---|---|---|
  | NiceVoice | api.turbovoice.online | ✅ 存活（返回合法业务错误） | 唯一保留 |
  | IndexTTS | kozzzq-indextts2api.hf.space | ❌ 已死亡（连接超时，HF Space 下线） | v2.21 移除 |
  | KikiVoice | kikivoice.ai | ⚠️ 403 + Geetest 积分制 | v2.21 移除 |
- **客户重大投诉**（宋宋，2026-09-23）：断句错误、重音错误、字幕半句残留、字幕间距过近。读音 bug 清单已用 Node 测试台架在 2.20.1 线上逻辑上**逐条复现**，根因定位完成（见 §6）。
- **版本路线**：v2.20.2（文档修正）→ v2.21.0（渠道清理 + NiceVoice 输入层修复）→ v2.21.1（当日热修：模板转义致前端正则全面失效 + README 双副本同步）。
- **v2.21.1 当日热修要点**：v2.21.0 构建把前端代码嵌入模板字面量时正则反斜杠未双写，浏览器端 16 处正则损坏（1 处致命语法错误致全部按钮失效，15 处静默失效含 2 颗"合法但危险"的运行时地雷）；以浏览器实际下发页面为基准重建，发版门禁新增"字节级回译比对 + 真实下发脚本回归"两道关；应用内 README（前端 base64 副本）从陈旧 v2.17 同步至当前。

---

## 2. 项目与架构（当前状态）

### 2.1 主力：TTS Voice Lab（tts worker）

单文件 Cloudflare Worker（ES Module），无构建步骤。前端 SPA 以模板字面量嵌在 `getHTML()` 内（**注意：前端代码里所有 `\` 必须双写 `\\`，这是本项目历史上最高频的 bug 来源**），后端代理 NiceVoice API。

- 域名：tts.lishuhang.com（Custom Domains 绑定 service `tts` production，重新上传脚本不受影响）
- 账户 ID：`ec44dddde866c789a9dd26f5d0cdb248`
- 部署方式：CF API `PUT /accounts/{acc}/workers/services/tts/environments/production/scripts`（multipart，`main_module=worker.js`），或 wrangler
- 核心链路：文本输入 → 说话人检测 → 分段（NiceVoice 150 字/段）→ 数字/符号预处理（正则 + 可选 GLM-4-Flash）→ 逐段 TTS（段间 16 秒限流等待，串行）→ Web Audio 解码拼接 → 峰值归一化/说话人 RMS 拉平 → BGM ducking 混音 → 片头片尾 → 输出 WAV + SRT + 剪映工程 ZIP
- Worker 代理端点（NiceVoice，v2.19 起）：`/clone/tts` 与 `/clone/getItemByTaskSn` **不签名**直转；`getUploadUrl / saveRefAudio2 / getSyncRefStatus` 保持 HMAC-SHA256 签名；`/api/nv-upload` 预签名 PUT 代理（Content-Type: audio/mpeg）；`/api/audio-proxy` 音频下载；`/api/glm/chat` GLM 代理（Key 不落前端）

### 2.2 旁支系统（历史，均已冻结）

- **tts2 worker（v2.19.0）**：主力 worker 的旧快照，占用了 tts2.lishuhang.com。建议后续与主力保持同版本或下线。
- **nicevoice worker（v1.16.6）**：2026-05~06 的多通道实验（NiceVoice/KikiVoice/本地 F5-TTS ONNX 浏览器推理）。LocalEngine 通道 Preprocess 阶段 tensor shape 问题始终未跑通，项目整体已被 TTS Voice Lab 取代，worker 仍在线但不再迭代。
- **indextts worker（v0.11）**：Kaggle GPU + cloudflared tunnel + HF 双后端的 IndexTTS-2 工具。因 Kaggle 依赖冲突（transformers 版本）v79 未确认跑通、HF ZeroGPU 配额问题、且 IndexTTS 公共 API 已死，整个路线冻结。其 KV（indextts-kaggle）、Kaggle notebook（lishuhang1/indextts2server，~v79）保留但不维护。

### 2.3 下游工作流：剪映工程（For_Agents/0-剪映工程agent提示词.txt，保留不删）

该 txt 是给剪映 agent 的操作提示词，非开发日志，故保留。要点：文案换行 = 字幕分行依据；TTS 用剪映 SAMI 引擎（娱乐扒妹II 音色）是**另一条独立产线**；本工具产出的 WAV/SRT/剪映 ZIP 直接进剪映草稿 `com.lveditor.draft`。**重要经验：声音克隆时不要在 TTS 侧变速（1.2x/1.3x），因为音源本身已是变速后的声音。**

---

## 3. 版本历史（合并去重后的完整时间线）

### 3.1 TTS Voice Lab 主线（tts worker）

#### v1.3（2026-05-19）
- 三面板布局（模型/声音/文本），9 模型集成：6 开源（Edge-TTS 323 语音、F5-TTS 克隆、IndexTTS-2 八维情感、Kokoro-82M、Orpheus 情感标记、SparkTTS）+ 3 闭源（OpenAI/ElevenLabs/MiniMax）
- 多 HF Token 轮换、播放互斥、历史记录、记忆功能、设置页自包含 README/Changelog
- 已知缺陷（当时记录，现已随多引擎一并移除）：SparkTTS gender 硬编码为 5、Blob URL 跨刷新失效、localStorage 容量风险（参考音频 base64 2-4MB 逼近 5MB 上限）、select onchange 多余 `=""`、停止生成不取消 Worker 端请求

#### v2.0（2026-05-23）— 重构
- 全面重构转向"克隆 TTS + 字幕 + 剪映导出"：kozzzq/indextts2api REST API、剪映 ZIP、SRT 字幕、音源管理、并发生成、历史 IndexedDB、docx 导入、配置导入导出

#### v2.1 ~ v2.7（2026-05-24 ~ 05-25）
- v2.1：NiceVoice 成为主引擎，双引擎切换，Worker 端 HMAC-SHA256 签名代理，克隆全流程（上传→训练→TTS），音源关联 referenceId
- v2.2：修复分段（短句不再各自成段）、分段逻辑重构、控制台日志
- v2.3：音色复用（保存音源关联 NV 服务器 referenceId + 有效性验证 + 自动重克隆）
- v2.4：文件名规范化 yyyymmdd-hhmmss、SRT 每行 ≤15 字、剪映字幕样式（思源黑体/白字黑边/10 号）
- v2.5：剪映字幕类型改 subtitle、stroke 对齐 pyJianYingDraft、字幕 y=-0.8
- v2.6：SRT 时间轴修复（字符数累加法取代位置追踪）、docx 文件名一致、ZIP 结构规范
- v2.7：SRT 时间轴根本性修复 + 剪映字幕同步

#### v2.8 ~ v2.13（2026-05-25 ~ 06-12）
- v2.8：JSZip 懒加载、去调试日志、DOM 缓存、HTTP 缓存头
- v2.9：KikiVoice 渠道（三模型、Geetest 代理验证保 IP 一致、积分监控、Log 控制台）
- v2.11：多人旁白模式（说话人标记检测、换行续接、台词量失衡警告、自定义说话人正则、多人 SRT/剪映字幕）
- v2.12：文本优先工作流（先文本再分配音源）、音源互斥、数字/符号预处理 v1、音源双引擎音色 ID、克隆自动重采样 24kHz/截 15s
- v2.13：GLM-4-Flash 智能预处理（关闭/回退/始终三模式 + 安全检查 + Worker 代理）、音色复用修复

#### v2.14（2026-06-17）— 输入管线大版本
- GLM 系统提示词可编辑；Before/After 双栏预览可手改；说话人交替校验 + 自动交替
- BGM 混音（双音量、5s 试听、sidechain ducking -6dB、配置导入导出）；片头片尾（淡入淡出/直接）；人声归一化（peak -3dB + RMS 拉平 + 女声轻压缩）；标题/Shownotes/Tags 自动生成；设置变更 toast
- 正则预处理回退规则（顿号/书名号/破折号/竖线→逗号）；README/changelog 提至文件头 `README_CONTENT`
- 实测：2 音色 2509 字早报文案 29 段 0 失败 6:35；ASR 抽检通过
- 修复：esbuild 反斜杠丢失、`</script>` 转义 `<\/script>`、模板字面量提前终止、metadataCard null

#### v2.15 ~ v2.17（changelog 曾缺失，本次补记）
- v2.17（2026-06-18 部署）：修复生成完成后分段编辑不可点击（`S.isGenerating=false` 后未重渲染 `renderSegmentTable()`）

#### v2.18（2026-06-18 后热更新）
- 修复 NV 克隆上传 Content-Type：audio/wav → audio/mpeg（匹配实际 MP3）
- 新增克隆后验证 `nvValidateClone`（用克隆音色发测试 TTS 确认可用，含 16s 限流重试）
- 克隆成功但 TTS 不可用时明确提示上游故障

#### v2.19（2026-07-24）
- **修复 NV TTS 始终 400 的根本原因：上游 /clone/tts 拒绝 HMAC 签名请求** → `/clone/tts`、`/clone/getItemByTaskSn` 改不签名直转，克隆管理端点保持签名
- 调查结论：上游存储 COS→R2 迁移，训练后端同步约 20s 延迟（COS 报错为瞬态）；上游网站自身 TTS 不签名；任务状态端点是 getItemByTaskSn（getTaskStatus 已 404）

#### v2.20（2026-08-04）
- 拖拽上传修复 `initUploadZoneDragDrop`（阻止浏览器默认导航，音频文件才能落进上传区）
- 分段编辑三连修：孤单元格防护（不再触发整表重渲染导致点击丢失）、静默提交 `commitSegmentEditSilent`、blur 用 requestAnimationFrame 避免竞态
- 说话人交替警告加"忽略"按钮（一次性 dismiss，生成时重置）
- 音源下拉允许改选（不再置禁用，改为显示"（被谁占用）"）

#### v2.20.1（2026-08-04 热更新，本次从生产取回）
- 仅版本号递进与少量修正，无独立功能记录（头注释与 changelog 均漏更）

#### v2.20.2（本次，2026-09-29）
- 与 v2.20.1 行为一致的**文档修正版**：头注释、内嵌 README、Changelog 全面对齐到真实状态；补记 v2.15~v2.20.1 缺失条目；JS 源文件首次归档备份

#### v2.21.0（本次，2026-09-29）
- 渠道清理：移除 IndexTTS（上游已死）与 KikiVoice（Geetest 积分制、弃用）前后端全部代码与入口，readme 无痕清理
- NiceVoice 四大问题输入层修复（详见 §6/§7）
- ⚠️ 事后发现：本版构建存在模板转义缺陷与 README 漏更新（前端副本），由 v2.21.1 当日热修

#### v2.21.1（本次，2026-09-29 当日热修）
- 修复模板字面量转义缺陷：v2.21.0 构建写入前端代码时正则反斜杠未双写，浏览器端 16 处正则损坏——`/+/g` 为非法正则致整个脚本解析失败（设置/历史/引擎切换/README 等全部按钮失效）；其余 15 处静默失效（数字数位/日期/万/亿/百分号/货币/手机号读音全灭），其中 `/|/g`（每字符插逗号）与 `/.{3,}/g`（任意 3+ 字替换为"等等"）损坏后仍合法，属运行时地雷
- 修复方式：以线上实际下发 HTML 为基准逐处还原正则 → 按"模板字面量内反斜杠双写"规则重新嵌入 → Node 按真实语义 cooked 模板与期望页面**逐字节比对一致** → 下发脚本 `node --check` 零错误 → 36 项回归跑在真实下发脚本全部通过（反向验证：同台架跑旧脚本正确崩溃于 `/+/g`）
- 应用内 README（前端 base64 副本）从陈旧的 v2.17 更新到当前版本，与 worker 顶部副本内容同步；补 v2.21.1 changelog 条目
- 发版门禁制度化：回归测试今后必须跑在"浏览器真实收到的 cooked 脚本"上（旧台架跑在未 cooked 文本上是本次漏测根因）

### 3.2 nicevoice worker 线（v1.0 → v1.16.6，已冻结）

- v1.0（05-23）：NiceVoice 克隆 + 150 字自动分段（贪心打包，711 字→5 段）+ 16s 限流 + WAV 拼接
- v1.1（05-24）：分段算法改进
- v1.4~v1.6（05-25~26）：KikiVoice 渠道 + Geetest CF 验证传导机制（把人机验证从浏览器 IP 转移到 Worker IP，核心创新）；SoundTools/Fish Audio
- v1.7~v1.10（05-26~29）：Fish Audio 因 402 余额问题移除，定版 3-tab
- v1.11~v1.16.6（05-30~07-01）：F5-TTS ONNX 浏览器推理长征。**教训清单**（依然适用于本项目）：
  1. 模板字面量里嵌 JS，所有 `\` 必须写 `\\`（v1.12/v1.16.1 两次踩坑：`split('\n')` 变真实换行导致 SyntaxError）
  2. ORT Web 的 WebGPU 后端无法接收 float16 输入张量，只有 WASM 能
  3. protobuf 字节级替换会破坏结构（v1.16.3 教训）
  4. tensor shape/type 错误信息里的 `Expected` 就是模型要的答案
  5. LocalEngine 最终卡在 max_duration shape（v1.16.6 自动尝试 scalar/[1,1]/[1] × int64/int32），随项目冻结未解

### 3.3 indextts worker 线（v0.8 → v0.11，已冻结）

- v0.8（05-23 前）：m4a 转码、双重量计数、时区修复；HF 后端验证成功（157s 输出、97% ASR 覆盖）
- v0.9~v0.10：JSZip + docx 表格提取、SSE 解析修复
- v0.11：Token 多实例轮询（round-robin）、高级设置折叠、音源管理、README 模态、下载文件名格式、Kaggle gRPC SaveKernel（真触发执行，REST push 只存不跑）
- 冻结原因：Kaggle 预装 transformers>4.52.1 与 IndexTTS2 冲突（v65~v79 未根治）、HF ZeroGPU 把 CF 共享 IP 标记滥用、上游公共 API 最终下线（§1 实测超时）
- 遗产：KV `indextts-kaggle`、notebook `lishuhang1/indextts2server`、凭证均未写入仓库（按凭据政策保管）

---

## 4. 凭据与安全政策（不可 push 清单）

以下凭据**只存在于会话内存与 CF/本地环境，严禁进入 Git 仓库**（本仓库 0929-tts 及其历史均不应出现；`For_Agents/tts-voice-lab-v2.17.js` 历史提交中已含 NiceVoice HMAC Key，本次已在工作副本中脱敏为占位符，git 历史无法改写但请知悉）：

1. Cloudflare API Token（cfat_…）——本会话使用，用于 worker 取回/部署
2. GitHub Token（ghp_…）——本会话使用，用于 clone/push
3. **NiceVoice 签名密钥**：`const NV_HMAC_KEY = '9BSG…'(32 字符)` ——worker.js 内嵌、部署到 CF 属正常需要；**任何写入 GitHub 的副本必须脱敏**（占位符 `__NV_HMAC_KEY_REDACTED__`）。该 Key 是上游 App 内嵌密钥（逆向所得），非我们自有凭据，无法"轮换"，泄露面=上游自身 App。
4. GLM API Key：用户浏览器 localStorage，不经过仓库
5. 各类 HF/Kaggle Token：localStorage/会话，不进仓库

**Push 纪律**：不频繁 push 冲击服务器；按里程碑成批提交（本次计划：合并文档+备份 1 次，v2.21 收尾 1 次）。

---

## 5. 客户投诉与问题定位（2026-09-23 宋宋反馈）

### 5.1 原始反馈摘录

> - 好多地方的断句和跟下一句的衔接都好奇怪 / 这里也是断句很奇怪 / 还有好几处断了半句的
> - 从"的"开始半句在屏幕上 / 这里也是 最后一个道士 2胜者无双 / 这一部分配音断句完全错误
> - 这里跟上一句完全连着了 / 整个配音都非常糟糕
> - 断句基本都不行；其次是一些重音也错误，一句话说完都不知道重点在哪里
> - 另一部演员，这 5 个字还是贴的特别近

### 5.2 读音错误清单（用户实测）

| 文案 | 错误读法 | 期望 |
|---|---|---|
| 正值618大促 | 六百一十八大促 ❌ | 六一八大促（品牌词） |
| 24小时销量7000套 | 七零零零套 ❌ | 七千套 |
| 两天累计售出1.2万套 | 一。二万套 ❌ | 一点二万套/一万二 |
| 在1000元以下 | 一零零零元 ❌ | 一千元 |
| 官宣后2.2亿曝光 | 二，二亿 ❌ | 二点二亿 |
| 吴添豪、李柯以不火天理难容 | 吴添豪、李柯，以不火 ❌（顿号处乱停顿） | 停顿在顿号处 ✔ |

### 5.3 Node 测试台架复现结果（对线上 2.20.1 前端逻辑原样执行）

| 输入 | 2.20.1 输出 | 根因 |
|---|---|---|
| 24小时销量7000套 | 二十四小时销量**七零零零**套 | 规则7把**所有4位数字**走"逐字读"（本意只给年份用），规则3已单独处理"数字+年"，规则7属重复误伤 |
| 在1000元以下 | 在**一零零零**元以下 | 同上 |
| 这款手机卖4999元 | **四九九九**元 | 同上 |
| 正值618大促 | 六百一**十八**大促 | 无品牌词表；618 应读"六一八" |
| 两天累计售出1.2万套 | 一点二万套（现版正则已正确） | 用户样本出自旧版；但**编辑过的分段会绕过预处理**（`previewEdits` 直用），存在回归路径 |
| 官宣后2.2亿曝光 | 二点二亿（现版已正确） | 同上 |
| 吴添豪、李柯以… | 顿号→逗号已转换 | 转换正确；乱停顿属模型韵律，需靠后续标点策略缓解 |
| 多句拼接 | `很好。 我们要…` | **ASCII 空格拼接**（行合并与句合并两处 `' '`），中文 TTS 读出诡异顿挫 |
| 段间拼接 | 段与段零静音直拼 | "跟上一句完全连着了"的来源 |
| 冒号文案 | 行首 `xx：` 一律判为说话人 | 说话人检测正则 `^([^\s：:]{1,8})[：:]` 过宽，普通文案冒号被当多说话人 |

### 5.4 "作为 LLM 如何定位问题"的思路（本次实际执行链）

1. **不复原现场也能量化**：TTS 音质问题看似主观，但输入层 bug 客观可测 → 从生产环境取回 2.20.1 源码，把前端预处理函数原样放进 Node 台架，用用户给的真实案例逐条跑，**全部复现**，把"感受问题"变成"确定性 bug 清单"。
2. **公开经验检索**：业界做法（ElevenLabs/Azure/Supertonic 等）都是在**输入层做文本规范化（TN）**——数字/符号/货币/百分比转读法，标点驱动韵律短语切分；ChatTTS 用显式停顿 token，Fish/CosyVoice 用文本前端。共同点：**模型不动，治理输入**。这与"不能改远端模型、只能 input harness"的约束完全一致。
3. **断句半句/字幕残留**：对照 SRT 生成代码逐行审，定位到 `mapOriginalLinesToSegments` 跨段行映射 + 字符比例分配的固有误差；音频"连着了"定位到拼接零静音。
4. **闭环链路**：自带测试文案 → 台架断言 → 修复 → 台架回归 →（可选）GLM 预处理交叉验证 → 生产小样实测。无需人工听每一条，台架先拦住确定性错误，人耳只复核韵律。

---

## 6. v2.21 修复方案（输入层 harness，不动远端模型）

1. **数字读法重写**：4 位及以上数字一律走数位转换（1000→一千、7000→七千、4999→四千九百九十九）；"数字+年"保留逐字读；电话号保留逐字读；新增品牌词表（618→六一八、双11→双十一、双12→双十二等，可配置）
2. **拼接去空格**：分段合并时中文句子间不再插 ASCII 空格（行合并、句合并两处）
3. **段间静音**：拼接时插入可配置静音（默认 ~150ms），治"完全连着了"
4. **冒号治理**：
   - 说话人检测收紧：仅当**≥2 个不同前缀**命中才进多人模式；单一前缀视为普通文案（提示但不拦截）；纯数字/时间前缀（如 `12:30`）排除
   - 发送给 TTS 的文本中，非说话人场景的全角冒号转逗号（说话人标记在分段时已剥离，不受影响）
5. **编辑旁路修复**：手改分段（previewEdits）后仍执行数字/符号预处理（手改内容以用户输入优先，但读音转换层必须兜底）
6. **SRT 字幕**：跨段行按字符比例**切分文本**归属各段（治"从'的'开始半句在屏幕上"）；字幕最短时长 0.6s 下限（治"贴得特别近"）
7. GLM 默认系统提示词同步更新（新数字规则 + 冒号规则）

---

## 7. 增量工作日志

### 2026-09-29（GMT+8）

**会话 A（上午）**
1. 稀疏克隆 `lishuhang/clock` 的 `0929-tts`；通读 For_Agents/Todos 三份文档 + 剪映提示词
2. 经 CF API 从生产取回 `tts`（v2.20.1）、`tts2`（v2.19.0）、`nicevoice`（v1.16.6）三个 worker 源码，multipart 解包成功
3. diff 2.17 ↔ 2.20.1（182 行变更），重建 v2.18/v2.19/v2.20 changelog；确认文件头注释与 changelog 缺口
4. 构建前端提取管线（模板字面量反转义）+ Node 测试台架，**逐条复现**用户读音 bug；确认根因（见 §5.3）
5. 三渠道上游实测：NiceVoice 存活、IndexTTS 已死、KikiVoice 403；域名绑定确认为 Custom Domains（部署不影响）
6. 检索业界 TN/韵律实践（ElevenLabs、ChatTTS、CosyVoice、Supertonic 等），确认输入层治理路线
7. 生成本合并文档；准备 v2.20.2 发版

**会话 A（下午，续）**
8. **v2.20.2 发版**：基于生产取回的 2.20.1，仅修文档（头注释/内嵌 README/changelog 补记 v2.15~v2.20.1）；CF API multipart 上传（注意 curl 必须带 `filename=worker.js`，否则 main_module 校验失败 10021）；生产核实 VERSION=2.20.2
9. **v2.21 阶段 A（渠道移除，-54KB）**：删除 IndexTTS/KikiVoice 的后端路由（含 Geetest 代理）、前端卡片/设置组/引擎选择器、生成派发分支、约 20 个 JS 函数；音源数据结构中的 kkVoiceId 字段保留（兼容旧配置导入）
10. **v2.21 阶段 B（NiceVoice 输入层修复）**：
    - 数字预处理重写：数位读法（1000→一千/7000→七千/4999→四千九百九十九），年份/届级保留逐字读，电话逐字读
    - 品牌词表（上下文锚定）：618大促→六一八大促、双11→双十一、双12→双十二；"价格618元"不受影响
    - 分段合并去 ASCII 空格；拼接插入 150ms 段间静音（segGapMs 可配）
    - 冒号治理：isMetaSpeakerName 过滤（纯数字/时间/元信息词）；【】括号豁免；多人模式要求每个冒号称呼 ≥2 次行首出现（真实对话必交替）；TTS 文本中全角冒号→逗号
    - previewEdits 旁路修复（手改分段同样过读音预处理）
    - SRT：跨段行按标点切分归属各段 + 0.6s 最短字幕时长（rebalanceSrtDurations 从最长同段借时）
    - GLM 默认提示词同步更新；顺带删除 worker 作用域死代码 DEFAULT_GLM_PROMPT
11. **v2.21 阶段 C**：VERSION=2.21.0、头注释、README（单引擎说明/新预处理规则/渠道移除说明/用法）、changelog v2.21 条目
12. **验证**：worker 模块语法 ✓；前端提取语法 ✓；单元台架 **36/36 通过**（19 项读音用例含全部用户报告案例、4 项分段、9 项说话人检测、3 项字幕时长）；跨段行切分专项测试通过（全覆盖、标点处切分）
13. **v2.21 发版**：生产部署成功，线上核实 VERSION=2.21.0、页面标题 v2.21.0、HTML 中渠道痕迹 0 处、NV 代理正常（getSyncRefStatus 返回上游业务响应）、kiki 路由正确 404
14. **归档**：For_Agents/backups/ 新增 v2.20.1-recovered（生产取回）、v2.20.2、v2.21.0 三份源码备份；全部副本 NiceVoice HMAC Key 已脱敏为占位符（v2.17 旧文件一并脱敏；git 历史中的旧值无法改写，该 Key 为上游 App 内嵌密钥，非我方凭据）
15. 旧 Todo 文档（260523-indextts-todo / 260523-tts-voice-lab-readme / 260701-nicevoice-readme）已由本文档取代并删除；剪映提示词 txt 为操作模板非开发日志，移至 For_Agents/ 根目录保留

**会话 B（晚间，v2.21.1 当日热修）**
16. 用户报告：右上角设置不可点，F12 报 `Invalid regular expression: /+/g: Nothing to repeat` + `toggleSettings/openHistory/switchEngine is not defined`
17. 定位：`/+/g` 只是唯一语法报错点；全面排查发现 v2.21.0 模板字面量内 **16 处正则反斜杠被减半**（`\\d`→`\d`），cooked 下发后变 `/d/`、`/(d{4})s*年/g` 等——数字/日期/万/亿/百分号/货币/手机号读音全部静默失效；`/|/g` 与 `/.{3,}/g` 损坏后仍合法属运行时地雷；同时发现应用内 README（前端 b64 副本）仍是 v2.17 三引擎旧版——阶段 C 只更新了 worker 顶部无引用的死代码副本，工作日志记录与实际不符，本条更正
18. 漏测根因：旧台架把"模板字面量原始文本"当被测代码（其中 `\\d` 是合法正则），从未测过"浏览器实际收到的 cooked 输出"；36/36 通过系假阳性
19. 修复（scripts/build_v2211.py）：以浏览器实际收到的 HTML 为基准，修 16 处正则 + 还原 5 处 `${VERSION}` 占位符 + 重建 README 双副本 → 反斜杠双写重新嵌入 → Node eval cooked 模板与期望页面**逐字节一致** → node --check 零错误 → 36 项回归在 cooked 脚本 36/36 → 反向验证：同台架跑旧脚本正确崩溃于 `/+/g`
20. 发版 v2.21.1（19:19 GMT+8）：线上核实 VERSION=2.21.1、下发脚本零语法错误、16 处正则正确形态、按钮函数齐备、README 弹窗标题 v2.21.1、`/api/nv/getSyncRefStatus` 返回上游业务响应、`/api/nv/tts` 真实创建任务（返回 taskSn）、kiki 路由 404——全部通过
21. 归档 For_Agents/backups/tts-voice-lab-v2.21.1.js（NV HMAC Key 脱敏）；本文档更新并重命名时间戳为 0929-1930

### 经验教训（本次新增）

1. **热更新不留档是重大运维风险**：2.20.1 源码仅存于 CF 生产环境，靠 API 取回才恢复。今后每次部署必须归档 JS 到本仓库（脱敏副本）。
2. **curl 上传模块 worker**：`-F "worker.js=@file"` 的 module 名取自文件名字段，必须显式 `filename=worker.js` 与 metadata.main_module 一致，否则 10021。
3. **模板字面量转义**：在本文件内嵌前端代码时，文件级 `\\d` 才是浏览器里的 `/\d/`；Python 做补丁时匹配串也要用 raw string，否则 `\\n` 被折叠导致 assert 失败（本次两次踩到，均已快速定位）。
4. **冒号检测无法靠枚举标签词根治**：改为"对话频率"判别（≥2 次行首出现）后，泛化能力大幅提升。
5. **测试台架先行**：把用户主观投诉转成确定性断言（36 项），修复后有回归保障，此后任何输入层改动都可机器验证。
6. **（v2.21.1 新增）被测对象必须是浏览器真实收到的代码**：模板字面量 cooked 前后是两个世界（源码 `\\d` 合法，cooked 后变 `d`）。"提取出来能跑通"≠"线上能跑通"；发版门禁必须以 cooked 输出为准做字节级回译比对 + 在 cooked 脚本上跑回归（本轮 36/36 假阳性教训，旧台架测的是未 cooked 文本）。
7. **（v2.21.1 新增）同名变量多副本是腐化温床**：worker 顶部 README_CONTENT 与前端 base64 README_CONTENT 同名不同值，更新时极易只改其一（v2.21.0 即栽在此）；本次起两份副本由构建脚本同源生成、同步校验。
8. **（v2.21.1 新增）损坏后的正则可能仍然合法**：`/|/g`、`/.{3,}/g` 这类损坏不报错但会运行时大范围误替换，比直接报错的 `/+/g` 更危险；排查不能只找语法报错点，要对全部正则字面量做逐个审校。

（后续增量按时间续写；最近更新：2026-09-29 会话 B，生产版本 v2.21.1）
