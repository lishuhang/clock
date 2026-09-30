// ============================================================
// TTS Voice Lab v2.22.2 — Cloudflare Worker
// NiceVoice single engine (v2.21: IndexTTS & KikiVoice channels removed —
//   IndexTTS upstream (kozzzq-indextts2api.hf.space) is offline; KikiVoice was
//   Geetest/credit-gated and unused. Only NiceVoice remains.)
// Voice cloning TTS with subtitle generation & JianYing export
// v2.20.2: documentation-only release, behaviour identical to 2.20.1.
//          Source recovered from production via CF API (2026-09-29):
//          header comment + README + changelog now reflect the real
//          v2.18~v2.20.1 hot-update history. Full log: todo-tts-full.
// v2.21: input-layer overhaul for NiceVoice quality (customer-reported bugs):
//        (1) numbers: place-value reading for 4+ digits (7000->七千, not 七零零零)
//        (2) brand terms: 618大促->六一八大促, 双11->双十一
//        (3) segment joining without ASCII spaces; 150ms inter-segment silence
//        (4) colon governance: >=2 valid prefixes required for multi-speaker;
//            full-width colon converted to comma in TTS-bound text
//        (5) edited segments (previewEdits) no longer bypass preprocessing
//        (6) SRT: partial-line split across segments + 0.6s min subtitle
// v2.22.2: user-reported UI hotfix —
//        (1) settings panel never appeared (only the dim overlay): v2.22.1
//            moved panel hiding from right:-440px to transform:translateX(105%)
//            but the open state kept ".settings-panel.open{right:0}" — right
//            was already 0 and the transform reset was missing, so the panel
//            stayed parked off-screen; open now also sets
//            transform:translateX(0) (same pattern the toast uses)
//        (2) the "gear" glyph was a sun (centre circle + radiating ticks);
//            replaced with a real cog outline in the sprite (single symbol,
//            every <use href="#i-gear"> picks it up)
// v2.22.1: user-feedback hotfix — rules UI unified & About-page fix:
//        (1) getReadmeContent() searched for the interpolated '2.22.0'
//            instead of the literal ${VERSION} marker inside the base64
//            README, so the About tab showed a raw ${VERSION} headline;
//            search string now built as '$' + '{VERSION}' (never
//            interpolated by the worker template)
//        (2) builtin & custom rules share one row model (name / content /
//            type / switch); every field click-to-edit, blur-to-save;
//            builtin data rules (quote-comma / colon-comma / sentence-space)
//            carry live editable pattern/replacement
//        (3) restore-default button + JSON import/export for rules
//        (4) GLM-semantic rules show a "未生效" badge when no key/off mode
//        (5) "试跑预处理" removed (duplicate of Before/After preview)
//        (6) settings panel: plain-flow header/tabs, transform animation,
//            bottom close button (WeChat WebView fixed-glitch workaround)
//        (7) every emoji icon replaced by monochrome stroke SVG sprite icons
// v2.22: sentence-boundary overhaul + user-configurable text rules:
//        (1) quotes -> comma (upstream dropped “”, words inside got split)
//        (2) line-aware segments: newlines kept, line-end punctuation
//            finalized, sentence-final marks followed by a half-width space
//            (live-probed: bare CJK period glued to text produced NO pause)
//        (3) punctuation collapse (consecutive marks, tail upgrades)
//        (4) all conversions exposed as toggleable rules; user rules support
//            text/wildcard/regex/GLM-semantic with per-rule switches
//        (5) settings panel rebuilt into 设置/历史/关于 tabs; README &
//            changelog rendered inline (no modal); header buttons cleaned
//        Ground truth method: real-TTS probes + ASR transcription + silence
//        detection (pause localization) — scripts archived in repo.
// v2.21.1: HOTFIX (same-day) — v2.21.0 wrote the frontend into the template
//        literal with single backslashes, breaking 16 browser-side regexes:
//        /+/g was a fatal SyntaxError (whole script dead => header buttons
//        toggleSettings/openHistory/switchEngine undefined), the other 15
//        silently disabled every number/date/percent/currency rule; /|/g and
//        /.{3,}/g stayed VALID and were runtime time-bombs. Page rebuilt from
//        served-HTML ground truth with proper \\ escaping; release gate added
//        (byte-identical round-trip + unit tests run on the truly served
//        script); in-app README (both copies) synced to v2.21.1.
// v2.19: fix NV TTS 400 — TTS/task-status proxied WITHOUT HMAC signing
// v2.20: drag-drop upload fix, segment editing fixes, alternation dismiss
// ============================================================

const VERSION = '2.22.2';

// NiceVoice API constants
const NV_API_BASE = 'https://api.turbovoice.online';
const NV_HMAC_KEY = '__NV_HMAC_KEY_REDACTED__';
const NV_APP_ID = '10';
const NV_APP_CODE = '110';
const NV_WAIT_MS = 16000; // 16s between TTS requests
const NV_MAX_POLL = 60;
const NV_MAX_CHARS = 150;


// ============================================================
// README_CONTENT — Single source of truth for in-app README modal.
// Stored at the head of the file so it is the first thing readers see
// when opening the source. getReadmeContent() renders this verbatim.
// ============================================================
const README_CONTENT = `
# TTS Voice Lab v${VERSION}

> 基于 Cloudflare Worker 的浏览器端语音克隆 TTS 工具，NiceVoice 单引擎 + 长文本分段合成 + 字幕生成 + 剪映工程导出。

## 简介

TTS Voice Lab 是一个基于浏览器的语音克隆 TTS 工具，支持长文本分段合成、字幕生成和剪映工程导出。

v2.22 系统化修复断句边界：引号转停顿、换行保留句界、句末空格强化边界，并把全部文本转换规则开放为可配置的“读音替换规则”（内置规则可启停，支持自定义正则/通配符/GLM 语义规则）。设置面板重构为 设置/历史/关于 三页。
v2.21 专注 NiceVoice 唯一渠道的合成质量：数字按数位读（7000→七千）、营销词连读（618大促→六一八大促）、句间不再插入多余空格、段间加入自然停顿、冒号不再误判说话人、字幕与音频对齐优化。此前 v2.19 修复 TTS 400（上游拒绝签名请求）；v2.20 修复拖拽上传与分段编辑；v2.14 引入 GLM 预处理、Before/After 预览、BGM 混音、人声归一化、片头片尾等。v2.21.1 为当日热修：修复构建转义缺陷导致的前端正则全面失效与设置等按钮不可点，并同步两份 README 至当前状态。

## 功能特性

- **单引擎专注（v2.21）**：仅保留 NiceVoice 唯一稳定渠道。IndexTTS（上游 HF Space 已下线）与 KikiVoice（Geetest 积分制，未使用）渠道已整体移除
- **NiceVoice**：免费无限制语音克隆，无需登录，API 代理自动签名（TTS 请求不签名直转，v2.18 增加克隆后验证）
- **文本优先工作流**：先输入文本，自动检测说话人，再为每人分配音源
- **音源管理**：新建、重命名、预览、删除、导入/导出音源，音源可关联克隆 ID
- **数字/符号预处理（v2.21 重写）**：正则 + 可选 GLM 双层兜底，默认处理：
  - 数位读法：1000 → 一千、7000 → 七千、4999 → 四千九百九十九（v2.21 起不再逐字读）
  - 年份/届级逐字读：2026年 → 二零二六年、2026届 → 二零二六届
  - 营销词连读：618大促 → 六一八大促、双11 → 双十一、双12 → 双十二
  - 百分比 50% → 百分之五十；小数 1.2万 → 一点二万；¥1000 → 1000元
  - 顿号/书名号/破折号/省略号 → 逗号等；全角冒号 ： → 逗号（防止误判说话人）
- **读音替换规则（v2.22 新增）**：全部文本转换规则可视化，内置规则可单独停用；自定义规则支持文本直替、通配符（* / ?）、正则与 GLM 语义改写，每条独立开关，设置面板可试跑预览
- **断句边界修复（v2.22）**：引号转停顿防拆词；分段保留换行边界、行尾补句号；句末标点后补半角空格强化句子边界（全部经真实生成 + 静音检测验证）
- **设置面板三页签（v2.22）**：设置 / 历史 / 关于；README 与更新日志内嵌“关于”页，历史记录内嵌“历史”页
- **段间自然停顿（v2.21 新增）**：拼接时插入 150ms 静音（可通过配置 segGapMs 调整），治"句句粘连"
- **字幕对齐优化（v2.21 新增）**：跨段行按标点智能切分归属各段（治"半句残留"）；短字幕 0.6 秒最短时长兜底（治"贴得太近"）
- **说话人检测收紧（v2.21）**：仅当出现 ≥2 个不同有效称呼才进入多人模式；纯数字/时间/元信息前缀（"标题："、"备注："等）不再误判
- **Before/After 双栏预览（v2.14 新增）**：合成前可看到 GLM 处理结果，并可手动编辑后再提交
- **说话人交替校验（v2.14 新增）**：检测连续两段同一说话人，高亮告警并提供"自动交替"按钮
- **BGM 混音（v2.14 新增）**：上传 BGM、人声/BGM 双音量拉杆、5 秒片段实时试听、sidechain ducking（人声段 BGM 自动降 6dB）、配置可保存/导入/导出
- **片头片尾拼接（v2.14 新增）**：参考 podmerge.html 实现，支持淡入淡出/直接拼接
- **人声音量归一化（v2.14 新增）**：peak normalize 到 -3dB；按说话人 RMS 分组拉平；可选女声轻量压缩
- **标题/Shownotes/Tags 生成（v2.14 新增）**：合成完成后调用 GLM 自动生成播客元数据
- **长文本分段**：NiceVoice 150 字/段（智能合并短句；v2.21 起句间无空格拼接）
- **换行保留**：原始换行用于字幕分行
- **Word 文档导入**：支持拖拽或上传 .docx 文件
- **SRT 字幕**：按时间比例分配字幕，多人模式自动标注说话人
- **剪映工程导出**：生成可直接导入剪映的工程 ZIP
- **生成历史**：自动保存生成记录，标注使用引擎
- **配置导入/导出**：备份和恢复所有设置和音源
- **设置变更 toast（v2.14 新增）**：任何设置项变更即时提示"设置已保存"，不遮挡功能区

## 使用方法

1. 输入或导入要合成的文本（引擎已固定为 NiceVoice）
2. 在说话人分配卡片中为每位说话人选择或新建音源
3. 点击"预览处理"查看转换前后的文本，可手动编辑 After 文本（编辑内容同样会做读音预处理）
4. 点击"开始合成"，等待生成完成
5. （可选）在结果区点击"生成标题/摘要/标签"
6. 下载 WAV 音频（含/不含 BGM 两个版本）、SRT 字幕或剪映工程

## 合成渠道说明

- 当前仅提供 NiceVoice 一个渠道：免费无限、无需登录、150 字/段、段间 16 秒限流（上游 API 限制）
- 长文本按段串行生成，受限流影响总耗时与段数成正比，请参考进度条耐心等待
- 曾经的 IndexTTS / KikiVoice 渠道因上游不可用或未被使用，已在 v2.21 整体移除

## 关于参考音频

参考音频的质量直接影响克隆效果。建议：

- 时长 5-15 秒，清晰无噪音
- 避免背景音乐或多人说话
- 可以保存多个音源并随时切换
- 如需变速效果，请预先处理参考音频，本工具不做变速

## 关于剪映工程

导出的 ZIP 解压后包含以项目名命名的文件夹，内含 draft_content.json、draft_meta_info.json、audio_main.wav 和 audio_main.srt。将文件夹复制到剪映草稿目录 com.lveditor.draft 下即可打开。画布比例：9:16，字幕使用思源黑体（白字黑边，字号 10），位于画面下方。音频为完整单段文件。

## 关于 BGM 混音（v2.14 新增）

- BGM 默认音量 -18dB（约 0.126 增益），可在设置中调节
- 人声段开始时 BGM 自动 ducking 至 -24dB（再降 6dB），人声结束 0.3 秒后恢复
- ducking 算法使用 OfflineAudioContext + GainNode 自动化曲线，参考 podmerge.html 的 sidechain 实现
- 输出包含 BGM 的最终混音 WAV，同时保留纯人声 WAV 作为备份

## 关于音量归一化（v2.14 新增）

- **peak normalize**：所有段归一到 -3dB（可配置 -6 ~ 0dB）
- **说话人 RMS 拉平**：按说话人分组计算 RMS，自动增益让所有说话人响度一致（误差 ±1dB）
- **女声轻量压缩（可选）**：阈值 -20dB、比例 2:1、攻击 5ms、释放 50ms，治女声忽大忽小

## 更新日志

### v2.22.2 (2026-09-30)

- 修复：点击"设置"只出现半透明遮罩、面板不显示——v2.22.1 将面板隐藏方式改为 transform 位移，但展开状态漏写 transform 复位，面板始终停在屏幕外；已补上，恢复滑入动画
- 修复：设置按钮图标画成了"太阳"（圆点+放射线），已改为标准齿轮线条图标（sprite 单处定义，所有引用处一并生效）
- 说明：文字/通配/正则类规则为本地处理，无需 GLM Key 即生效；仅"GLM 语义"类规则需要 Key，未配置时列表会标注"未生效"

### v2.22.1（2026-09-30）

**规则系统统一 + 界面细节修复（用户反馈驱动）**

- 修复"关于"页首行显示 v${VERSION} 字面量的问题：部署时模板插值误伤了 README 渲染函数的 replace 搜索串，导致版本号永远替换不上去
- 读音规则结构统一：内置与自定义规则均为"规则名称 + 匹配内容 → 替换内容 + 类型 + 启用开关"；点击任意规则的名称或内容即可就地编辑，焦点移开自动保存（Enter 保存、Esc 取消）；内置规则同样可编辑
- 内置规则数据化：引号转停顿、冒号转逗号、句末空格三条规则开放"匹配/替换"编辑，改完立即生效；其余行为型规则可改名称与说明
- 新增"复原默认"按钮一键恢复内置规则出厂设置；新增规则导入/导出（JSON，位于规则区底部）
- 新增自定义规则时增加"规则名称"输入框，与内置规则字段对齐
- GLM 语义规则状态透明化：未配置 Key 或智能预处理关闭时，在列表中标注"未生效"（文本/通配/正则规则为本地规则，本就无需 GLM Key）
- 移除"试跑预处理"按钮（与主面板 Before/After 预览功能重复）
- 设置面板：标题与页签回归普通文档流（不再悬浮）；面板底部新增"关闭面板"按钮，滚动后无需回到顶部即可关闭；滑出动画改用 transform，规避部分 WebView（微信内置浏览器）fixed 渲染错位
- 全部 emoji 图标替换为单色 SVG 线条图标：统一在页面内 sprite 定义（symbol+use），一处定义、处处引用

### v2.22 (2026-09-30)

**断句边界系统化修复 + 用户自定义读音规则 + 设置面板重构**
- 修复引号断句错误：中文引号“…”在上游引擎中被静默忽略，边界消失导致引号内词语被拆读（“了不起的老祖宗”→“了 不起”）；引号现转为逗号停顿（线上实测停顿位置正确）
- 修复换行句界丢失：多行文案分段合并时换行信息被丢弃，无标点行首尾相连成整串；实测上游对裸连的中文句号几乎零停顿响应（模型随机断句）。现分段保留换行边界、行尾自动补句号、句末标点后补半角空格，三重边界信号全部经线上实测验证（停顿精确落在标点处）
- 连续标点清理：转换残留的“，。”“，，”自动去重，句尾弱标点升级句号
- **读音替换规则系统**：内置规则（引号/品牌词/数字/符号/冒号/标点清理/句末空格）在设置面板全部可见，可单独停用；用户可自定义规则，支持文本直替、通配符（* 任意串、? 单字）、正则、GLM 语义改写四种方式，每条规则独立开关，并可“试跑预处理”即时预览
- **设置面板重构**：改为 设置 / 历史 / 关于 三个标签页。README 与更新日志移入“关于”页（不再弹窗）；生成历史移入“历史”页（顶栏按钮移除）；设置项按 合成参数 → 音源 → 文本处理 → 音频后处理 → 历史与数据 重排
- 顶栏清理：移除单引擎残留的渠道切换按钮与历史按钮，顶栏仅保留设置入口
- 附：读音边界验证方法（真实生成 + ASR 转写 + 静音检测定位停顿）沉淀为可复用测试链路

### v2.21.1 (2026-09-29 当日热修)

**修复（v2.21.0 发布数小时后用户报告：右上角设置/历史等按钮全部不可点）**
- 根因：v2.21 构建把前端代码嵌入 worker 模板字面量时，正则里的反斜杠少写一层，浏览器端共 16 处正则损坏
- 致命一处：符号 + 转读法的正则损坏为非法正则 /+/g，整个前端脚本解析失败，设置/历史/引擎切换/README 等全部按钮失效（控制台报 toggleSettings/openHistory/switchEngine is not defined）
- 其余 15 处静默失效：数字数位、日期、万/亿、百分号、货币、手机号等读音正则全部失灵；其中竖线转逗号与省略号转"等等"两条损坏后仍是合法正则，一旦脚本可解析就会在运行时大面积误替换（每个字符间插逗号 / 任意 3 字以上替换为"等等"）
- 修复方式：以浏览器实际收到的页面为基准逐处还原正则，再按"模板字面量内反斜杠双写"规则重新嵌入；发版前新增两道校验：模板 cooked 输出与期望页面逐字节比对 + 36 项读音/分段/说话人回归测试全部跑在真实下发脚本上（旧测试跑在未 cooked 的文本上，是本次漏测的根因）
- 附带修复：应用内 README 弹窗此前一直显示 v2.17 旧内容（v2.21 构建只更新了 worker 顶部的死代码副本，漏更新前端 base64 副本）；本版起两份 README 同步为同一内容

### v2.21.0 (2026-09-29)

**渠道清理**
- 移除 IndexTTS 渠道：上游 kozzzq-indextts2api.hf.space 已下线（2026-09-29 实测超时）
- 移除 KikiVoice 渠道：Geetest 积分制、未被使用；连同 CF 验证面板与全部代理端点一并移除
- 引擎选择器简化：NiceVoice 成为唯一引擎，设置页引擎分组移除

**修复（客户反馈的四大问题，输入层 harness，不改远端模型）**
- 数字读法：4 位数以上按数位读（7000→七千、1000→一千、4999→四千九百九十九），此前一律逐字读；年份/届级保留逐字读
- 营销词：618大促→六一八大促、双11→双十一、双12→双十二（上下文锚定，避免"价格618元"误伤）
- 断句：分段合并不再插入 ASCII 空格（中文 TTS 会把空格读成诡异停顿）
- 段间粘连：拼接时插入 150ms 静音（默认，可配 segGapMs）
- 冒号误判说话人：需 ≥2 个不同有效称呼才进多人模式；"标题：/备注：/12:30"等不再误判；TTS 文本中全角冒号转逗号
- 编辑旁路：手动编辑过的分段（预览 After 文本）此前完全绕过读音预处理，现已统一兜底
- 字幕：跨段行按标点切分归属各段（治"从'的'开始半句在屏幕上"）；短字幕 0.6s 最短时长（治"贴得特别近"）
- GLM 默认提示词同步更新（数位读法/营销词/全角冒号规则）

### v2.20.2 (2026-09-29)

**文档修正（行为与 v2.20.1 完全一致）**
- 源文件通过 Cloudflare API 从生产环境完整取回，结束"在线热更新无存档"状态
- 修正文件头注释（此前停留在 v2.19）、补记 v2.15~v2.20.1 缺失的 changelog
- 内嵌 README 用法对齐当前版本

### v2.20.1 (2026-08-04)

- 常规小修与版本递进（热更新，未留变更记录）

### v2.20.0 (2026-08-04)

**新增**
- 说话人交替警告新增"忽略"按钮（一次性 dismiss，重新生成时自动重置）

**修复**
- 修复拖拽上传：阻止浏览器默认打开文件的行为（initUploadZoneDragDrop），音频文件可正确落入上传区
- 修复分段编辑点击丢失：编辑单元格被孤儿化时自动重渲染分段表
- 修复编辑框 blur 竞态：用 requestAnimationFrame 延迟提交，避免与点击事件冲突
- 音源下拉不再禁用已被占用的音源，改为显示占用者并允许改选

### v2.18.0 (2026-06-18 后热更新)

**修复**
- NV 克隆上传 Content-Type 修正：audio/wav → audio/mpeg（匹配实际 MP3 文件）

**新增**
- 克隆后自动验证：用克隆音色发送测试 TTS 请求，确认音色真正可用（含 16s 限流重试）
- 克隆成功但 TTS 不可用时，给出明确的上游故障提示

### v2.15 ~ v2.17 (2026-06)

- v2.17（2026-06-18 部署）：修复生成完成后分段编辑不可点击（isGenerating 置 false 后未重渲染分段表）

### v2.19.0 (2026-07-24)

**修复**
- 修复 NiceVoice TTS 始终返回 400 的根本原因：上游 /clone/tts 端点拒绝 HMAC 签名请求
- TTS 和 getItemByTaskSn 两个端点改为不签名代理，其余克隆管理端点（getUploadUrl/saveRefAudio2/getSyncRefStatus）保持签名

**调查发现**
- 上游 NiceVoice 已将存储从 COS 迁移至 R2，训练后端同步有约 20 秒延迟（COS 错误为瞬态，轮询会自动恢复）
- 上游网站自身对 TTS 请求不使用 HMAC 签名
- 任务状态查询端点为 getItemByTaskSn（非 getTaskStatus，后者已 404）

### v2.14.0 (2026-06-17)

**新增**
- GLM 系统提示词可在设置中编辑、保存到 localStorage、随配置导入导出
- 默认系统提示词新增规则：顿号/书名号/破折号统一转逗号；小数点读"点"汉字；年份/日期/金额/百分比的中文读法
- Before/After 双栏预览面板：合成前可看到 GLM 处理前后对比，After 文本框可手动编辑覆盖
- 说话人交替校验：扫描分段结果检测连续两段同一说话人，高亮告警 + "自动交替"按钮
- BGM 集成：上传/选择、双音量拉杆、5 秒片段实时试听、sidechain ducking、配置可保存/导入/导出
- 片头片尾拼接：参考 podmerge.html 实现，支持淡入淡出/直接拼接两种模式
- 人声音量归一化：peak normalize + 说话人 RMS 拉平 + 可选女声轻量压缩
- 标题/Shownotes/Tags 自动生成：合成完成后调用 GLM 生成播客元数据
- 设置项变更即时 toast 提示，不遮挡功能区（toast 移至右下角）
- 正则预处理新增书名号/顿号/破折号/竖线转逗号规则（无需 GLM 即可工作）
- 下载按钮新增"下载 WAV（纯人声）"选项，含 BGM 时同时保留两份

**修复**
- 保留 v2.13 源码中的 /\\\\.docx$/ 正则字面量（避免 esbuild 打包后丢失反斜杠的潜在问题）
- 修复部署版中 NEW_FUNCTIONS 未注入的问题（</script> 在模板字符串中需写作 <\\\\/script>）
- 修复 generateMetadata 中三反引号代码块标记导致模板字符串提前终止的语法错误
- 修复 alert('原文：\\\\n') 等字符串中 \\\\n 被模板字符串解释为实际换行的语法错误
- 修复 metadataCard 元素未注入 DOM 导致 E.metadataCard 为 null 的问题（用正则替换代替字面匹配）

**重构**
- README 与 changelog 提至文件头部 README_CONTENT 常量，getReadmeContent() 直接引用，避免源码与 UI 显示不一致

**实测验证（2026-06-17）**
- 用 2 个真实音色（小娱音色 + 乐乐-播客音色2）+ 2509 字早报文案测试
- 29 段全部生成成功，0 失败，总时长 6:35
- 数字/日期正则预处理正确（2026→二零二六、6月17日→六月十七日、第38届→第三十八届等）
- ASR 抽样验证 4 段，内容完整可识别，无段落丢失
- 书名号/顿号/破折号在本次测试中未处理（因 GLM 未配置），随后已添加正则回退规则

### v2.13.0 (2026-06-12)

- 修复 NV 克隆上传 Content-Type 错误：audio/wav -> audio/mpeg（匹配实际 MP3 文件）
- 新增克隆后 TTS 验证：自动用克隆音色发送测试请求，确认音色真正可用
- 优化 NV 克隆错误提示：克隆成功但 TTS 不可用时给出明确的上游故障提示
- GLM 智能预处理：支持 GLM-4-Flash API 进行中文数字、符号、多音字智能预处理
- GLM API Key 管理：设置中新增 API Key 输入和测试按钮，支持导入导出
- 预处理模式选择：关闭/回退模式（正则失败时用 GLM）/始终使用 GLM
- 预处理安全检查：如果预处理结果异常（过短），自动回退到原文
- GLM API 代理：通过 Worker 代理调用 GLM API，API Key 不暴露到客户端
- TTS 请求日志：记录发送到 TTS 引擎的文本内容和长度，便于调试

### v2.12.0 (2026-06-12)

- 移除顶部参考音频卡：采用"文本优先→再分配音源"工作流
- 说话人分配卡重构：单人模式也显示"默认"音源槽
- 音源互斥：已被一位说话人选择的音源，在其他说话人的下拉中置灰
- 音源管理 2.0：设置面板新增预览、重命名、同步状态指示
- 数字/符号预处理：自动将数字转中文读法，符号转文字
- 年份/日期/电话识别
- 音源数据结构升级：支持 NV/KK 双引擎音色 ID
- 音频压缩：新建音源时自动重采样 24kHz、截取 15 秒

### v2.11.0 (2026-06-11)

- 多人旁白模式：自动检测说话人标记
- 换行续接：没有说话人标记的行自动归属上一个说话人
- 防呆检测：当说话人台词量严重不均衡时警告
- 自定义说话人模式：支持添加自定义正则表达式
- 多人 SRT 字幕：字幕自动标注说话人姓名
- 多人剪映导出：剪映工程也支持多人字幕标签

### v2.9.0 (2026-05-25)

- 新增 KikiVoice 渠道：备选 TTS 引擎，三种免费模型
- Geetest 人机验证：通过 Worker 代理确保 IP 一致
- 积分余量查询：实时显示剩余积分、已用积分和重置时间
- Log 控制台：新增事件记录控制台

### v2.8.0 (2026-05-26)

- JSZip 懒加载：仅在需要时加载
- 移除调试日志：减少执行开销
- 简化字幕算法：优化自动换行算法
- DOM 元素缓存：减少重复查询
- HTTP 缓存：添加页面缓存头

### v2.7.0 (2026-05-25)

- 修复 SRT 时间轴根本问题：弃用位置追踪法，改用字符数累加法
- 修复剪映字幕同步

### v2.6.0 (2026-05-25)

- 修复 SRT 时间轴：修正字幕与音频不同步
- 修复 WAV 下载：直接下载已有文件
- 文件名规则：导入 docx 时文件名与 docx 一致
- 剪映 ZIP 结构规范化
- 生成历史升级：使用 IndexedDB 保存

### v2.5.0 (2026-05-25)

- 修复剪映字幕显示：字幕类型改为 subtitle
- 修复字幕样式格式：stroke 格式对齐 pyJianYingDraft 规范
- 补全字幕素材字段
- 修复字幕坐标：transform 使用归一化坐标 y:-0.8

### v2.4.0 (2026-05-25)

- 规范化文件名：yyyymmdd-hhmmss
- SRT 自动换行：每行不超过 15 字
- 剪映字幕样式：思源黑体、白字黑边、字号 10
- 同次生成时间戳一致

### v2.3.0 (2026-05-24)

- 音色复用优化：保存的音源关联 NiceVoice 服务器端 referenceId
- 智能验证：使用已保存音色时检查服务器端有效性
- 自动重新克隆：服务器端失效时自动重新克隆

### v2.2.0 (2026-05-24)

- 修复文字分段：NiceVoice 模式下短句不再各自成段
- 完整控制台日志：方便 F12 调试
- 分段逻辑重构

### v2.1.0 (2026-05-24)

- 新增 NiceVoice 作为主要 TTS 引擎
- 新增双引擎切换器
- 新增 NiceVoice API 代理（服务端 HMAC-SHA256 签名）
- 新增声音克隆流程：上传 → 训练 → TTS
- 新增音源关联克隆 ID

### v2.0.0 (2026-05-23)

- 全新重构，基于 kozzzq/indextts2api REST API
- 新增剪映工程 ZIP 导出功能
- 新增 SRT 字幕生成
- 新增音源管理、并发 TTS 生成、生成历史记录
- 新增 Word 文档导入、配置导入/导出
`;

// v2.14 default GLM system prompt (user-editable in settings)

function uuidv4() { return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0;return(c==='x'?r:(r&0x3|0x8)).toString(16);}); }

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, x-appid, x-code, x-os, x-ts, x-account, x-sign, x-token',
  };
}

// ==================== NiceVoice HMAC Signing ====================
// Hex-decode the HMAC key (non-hex chars produce 0 bytes, matching NiceVoice's Ff() function)
function hexDecodeKey(hexStr) {
  const bytes = new Uint8Array(hexStr.length / 2);
  for (let i = 0; i < hexStr.length; i += 2) {
    const val = parseInt(hexStr.substring(i, i + 2), 16);
    bytes[i / 2] = isNaN(val) ? 0 : val;
  }
  return bytes;
}

async function nvSign(bodyObj, ts, account) {
  const dataStr = (ts + account + JSON.stringify(bodyObj)).toLowerCase();
  const keyData = hexDecodeKey(NV_HMAC_KEY);
  const key = await crypto.subtle.importKey('raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(dataStr));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function nvHeaders(bodyObj, account) {
  const ts = Date.now().toString();
  const sign = await nvSign(bodyObj, ts, account || '');
  return {
    'Content-Type': 'application/json',
    'x-os': 'web',
    'x-appid': NV_APP_ID,
    'x-code': NV_APP_CODE,
    'x-ts': ts,
    'x-account': account || '',
    'x-sign': sign,
    'x-token': 'token',
  };
}

// ==================== NiceVoice API Proxy ====================
async function nvProxy(path, bodyObj, account) {
  const headers = await nvHeaders(bodyObj, account);
  const resp = await fetch(NV_API_BASE + path, {
    method: 'POST',
    headers,
    body: JSON.stringify(bodyObj),
  });
  const text = await resp.text();
  let data;
  try { data = JSON.parse(text); } catch(e) { data = { code: resp.status, raw: text }; }
  return new Response(JSON.stringify(data), {
    status: resp.status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders() },
  });
}


// ==================== Worker Handler ====================
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    // Serve main page
    if (path === '/' && request.method === 'GET') {
      return new Response(getHTML(), {
        headers: { 'Content-Type': 'text/html;charset=UTF-8', 'Cache-Control': 'public, max-age=300', ...corsHeaders() },
      });
    }

    // NiceVoice API proxy endpoints
    if (path.startsWith('/api/nv/')) {
      try {
        const nvPath = '/clone' + path.substring(7); // /api/nv/getUploadUrl -> /clone/getUploadUrl
        const bodyText = await request.text();
        const bodyObj = bodyText ? JSON.parse(bodyText) : {};
        // Log TTS requests for debugging
        if (nvPath === '/clone/tts' && bodyObj.text) {
          console.log('[NV-PROXY] TTS text="' + String(bodyObj.text).substring(0, 100) + '" (len=' + String(bodyObj.text).length + ') refId=' + bodyObj.referenceId);
        }
        // v2.19: TTS and getItemByTaskSn must NOT be HMAC-signed (upstream rejects signed TTS with 400)
        if (nvPath === '/clone/tts' || nvPath === '/clone/getItemByTaskSn') {
          const resp = await fetch(NV_API_BASE + nvPath, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(bodyObj),
          });
          const text = await resp.text();
          let data;
          try { data = JSON.parse(text); } catch(e) { data = { code: resp.status, raw: text }; }
          return new Response(JSON.stringify(data), {
            status: resp.status,
            headers: { 'Content-Type': 'application/json', ...corsHeaders() },
          });
        }
        // All other NV endpoints: use HMAC-signed proxy
        return await nvProxy(nvPath, bodyObj, '');
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
          status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() },
        });
      }
    }

    // NiceVoice upload proxy (PUT to presigned URL)
    if (path === '/api/nv-upload' && request.method === 'POST') {
      try {
        const { uploadUrl, audioBase64 } = await request.json();
        const audioBytes = Uint8Array.from(atob(audioBase64), c => c.charCodeAt(0));
        const resp = await fetch(uploadUrl, {
          method: 'PUT',
          headers: { 'Content-Type': 'audio/mpeg' },
          body: audioBytes,
        });
        return new Response(JSON.stringify({ ok: resp.ok, status: resp.status }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders() },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
          status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() },
        });
      }
    }

    // Audio download proxy
    if (path === '/api/audio-proxy' && request.method === 'GET') {
      try {
        const audioUrl = url.searchParams.get('url');
        if (!audioUrl) return new Response('Missing url', { status: 400 });
        const resp = await fetch(audioUrl);
        const headers = new Headers();
        headers.set('Content-Type', resp.headers.get('Content-Type') || 'audio/mpeg');
        headers.set('Access-Control-Allow-Origin', '*');
        return new Response(resp.body, { status: resp.status, headers });
      } catch (e) {
        return new Response(e.message, { status: 500, headers: corsHeaders() });
      }
    }

    // GLM API proxy for text preprocessing
    if (path === '/api/glm/chat' && request.method === 'POST') {
      try {
        const { apiKey, messages } = await request.json();
        if (!apiKey) return new Response(JSON.stringify({ error: 'Missing apiKey' }), { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
        const resp = await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
          body: JSON.stringify({ model: 'glm-4-flash', messages: messages, temperature: 0.1, max_tokens: 2048 }),
        });
        const data = await resp.text();
        return new Response(data, { status: resp.status, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      }
    }


    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders() },
    });
  }
};

// ==================== HTML Page Generator ====================
function getHTML() {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TTS Voice Lab v${VERSION}</title>
<style>
:root{--bg:#0f0f0f;--surface:#1a1a1a;--surface2:#242424;--surface3:#2e2e2e;--border:#333;--text:#e0e0e0;--text2:#999;--primary:#6c5ce7;--primary-hover:#7d6ff0;--green:#00b894;--orange:#fdcb6e;--red:#e17055;--blue:#74b9ff;--nv-color:#e17055;--idx-color:#74b9ff;--kk-color:#10b981}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--surface)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.header{background:var(--surface);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;flex-shrink:0}
.header-left{display:flex;align-items:center;gap:12px}
.header h1{font-size:18px;font-weight:700;background:linear-gradient(135deg,var(--primary),var(--blue));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .ver{font-size:11px;color:var(--text2);background:var(--surface2);padding:2px 8px;border-radius:10px}
.api-status{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text2)}
.api-status .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.api-status .dot.online{background:var(--green)}
.api-status .dot.offline{background:var(--red)}
.api-status .dot.checking{background:var(--orange)}
.header-right{display:flex;gap:8px}
.hdr-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text2);padding:6px 14px;border-radius:8px;cursor:pointer;font-size:13px;transition:all .2s}
.hdr-btn:hover{background:var(--primary);color:#fff;border-color:var(--primary)}
.main{flex:1;max-width:1600px;margin:0 auto;padding:20px;width:100%}
.main-grid{display:grid;grid-template-columns:1fr;gap:16px}
.main-content{min-width:0}
.main-log{min-width:0}
.main-log .log-console{max-height:none;height:calc(100vh - 140px);position:sticky;top:80px}
.layout-tabs{display:none}
@media(min-width:1024px){.main-grid{grid-template-columns:1fr 1fr}.layout-tabs{display:none}.main-content{max-height:calc(100vh - 140px);overflow-y:auto;padding-right:8px}}
@media(max-width:1023px){.main-grid{grid-template-columns:1fr}.layout-tabs{display:flex;gap:0;margin-bottom:12px;background:var(--surface2);border-radius:8px;border:1px solid var(--border);overflow:hidden}.layout-tab{flex:1;padding:10px 16px;font-size:13px;font-weight:600;cursor:pointer;border:none;background:transparent;color:var(--text2);transition:all .2s}.layout-tab.active{background:var(--primary);color:#fff}.main-content.hidden-tab{display:none}.main-log.hidden-tab{display:none}.main-log .log-console{max-height:400px;position:static;height:auto}}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}
.card-title{font-size:15px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.engine-badge{font-size:10px;padding:2px 8px;border-radius:10px;font-weight:600;text-transform:uppercase}
.engine-badge.nv{background:var(--nv-color);color:#fff}
.engine-badge.idx{background:var(--idx-color);color:#fff}
.upload-zone{border:2px dashed var(--border);border-radius:8px;padding:28px;text-align:center;cursor:pointer;transition:all .2s;position:relative}
.upload-zone:hover{border-color:var(--primary);background:rgba(108,92,231,0.05)}
.upload-zone.has-file{border-color:var(--green);background:rgba(0,184,148,0.05);border-style:solid}
.upload-zone .uz-icon{font-size:32px;margin-bottom:8px}
.upload-zone .uz-text{color:var(--text2);font-size:13px}
.upload-zone .uz-hint{color:var(--text2);font-size:11px;margin-top:4px;opacity:0.7}
.upload-zone .uz-filename{color:var(--green);font-weight:500;font-size:13px}
.audio-preview{margin-top:12px;display:flex;align-items:center;gap:8px}
.audio-preview audio{flex:1;height:32px}
.clear-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text2);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:12px}
.clear-btn:hover{border-color:var(--red);color:var(--red)}
.source-section{margin-top:14px;padding-top:14px;border-top:1px solid var(--surface2)}
.source-row{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.source-row label{font-size:12px;color:var(--text2);white-space:nowrap}
.source-select{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px;min-width:120px}
.save-source-row{display:flex;gap:6px}
.save-source-row input{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px}
.save-source-row button{background:var(--primary);border:none;color:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;white-space:nowrap}
.source-list{margin-top:8px;max-height:160px;overflow-y:auto}
.source-item{display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:var(--surface2);border-radius:6px;margin-bottom:4px;font-size:12px;cursor:pointer;transition:background .15s;border:1px solid transparent}
.source-item:hover{background:var(--surface3)}
.source-item.active{border-color:var(--primary);background:rgba(108,92,231,0.1)}
.source-item .s-name{font-weight:500}
.source-item .s-actions{display:flex;gap:4px}
.source-item .s-actions button{background:var(--surface3);border:none;color:var(--text);padding:2px 6px;border-radius:4px;cursor:pointer;font-size:11px}
.text-area{width:100%;min-height:140px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;color:var(--text);font-size:14px;resize:vertical;font-family:inherit;line-height:1.7}
.text-area:focus{outline:none;border-color:var(--primary)}
.text-stats{display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:var(--text2)}
.docx-actions{display:flex;gap:8px;margin-top:10px;align-items:center;flex-wrap:wrap}
.docx-btn{display:flex;align-items:center;gap:6px;padding:7px 14px;border-radius:6px;font-size:13px;cursor:pointer;border:1px solid var(--border);background:var(--surface2);color:var(--text);transition:background .2s}
.docx-btn:hover{background:var(--surface3)}
.docx-info{font-size:12px;color:var(--text2)}
.text-card{position:relative}
.docx-drop-overlay{position:absolute;top:0;left:0;right:0;bottom:0;background:rgba(108,92,231,0.12);border:2px dashed var(--primary);border-radius:12px;display:flex;align-items:center;justify-content:center;z-index:10;pointer-events:none;opacity:0;transition:opacity .2s}
.docx-drop-overlay.active{opacity:1}
.docx-drop-overlay p{color:var(--primary);font-size:15px;font-weight:600;padding:20px}
.gen-btn{width:100%;padding:14px;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:8px}
.gen-btn:hover{background:var(--primary-hover)}
.gen-btn:active{opacity:0.9}
.gen-btn:disabled{opacity:0.5;cursor:not-allowed;transform:none}
.gen-btn.nv-active{background:var(--nv-color)}
.gen-btn.idx-active{background:var(--idx-color)}
.cancel-btn{width:100%;padding:10px;background:var(--surface2);border:1px solid var(--border);color:var(--text2);border-radius:8px;font-size:13px;cursor:pointer;margin-top:8px;transition:all .2s}
.cancel-btn:hover{border-color:var(--red);color:var(--red)}
.progress-bar{width:100%;height:6px;background:var(--surface3);border-radius:3px;margin-top:12px;overflow:hidden;display:none}
.progress-bar.active{display:block}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--primary),var(--blue));border-radius:3px;transition:width .3s}
.elapsed{font-size:13px;color:var(--text2);margin-top:8px;text-align:center}
.seg-table{width:100%;border-collapse:collapse;margin-top:12px;font-size:12px}
.seg-table th{text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:500;font-size:11px}
.seg-table td{padding:6px 10px;border-bottom:1px solid var(--surface2)}
.seg-table .seg-text{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.seg-table .seg-status{display:flex;align-items:center;gap:5px}
.seg-table .sd{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.seg-table .sd.pending{background:var(--text2)}
.seg-table .sd.cloning{background:var(--orange)}
.seg-table .sd.submitting{background:var(--orange)}
.seg-table .sd.processing{background:var(--blue)}
.seg-table .sd.done{background:var(--green)}
.seg-table .sd.error{background:var(--red)}
.seg-table .sd.cancelled{background:var(--text2);opacity:0.4}
.result-section{display:none}
.result-section.active{display:block}
.result-audio{width:100%;margin-top:12px}
.dl-btns{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.dl-btn{padding:9px 18px;border-radius:8px;font-size:13px;cursor:pointer;border:1px solid var(--border);background:var(--surface2);color:var(--text);transition:all .2s;display:flex;align-items:center;gap:6px}
.dl-btn:hover{background:var(--surface3)}
.dl-btn.primary{background:var(--primary);border-color:var(--primary);color:#fff}
.dl-btn.primary:hover{background:var(--primary-hover)}
.settings-panel{position:fixed;top:0;right:0;width:420px;height:100vh;background:var(--surface);border-left:1px solid var(--border);z-index:200;transform:translateX(105%);transition:transform .3s;overflow-y:auto;padding:20px;-webkit-overflow-scrolling:touch}
.settings-panel.open{right:0;transform:translateX(0)}
.settings-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:199;display:none}
.settings-overlay.open{display:block}
.settings-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}/* v2.22.1: header & tabs are plain flow (no sticky/fixed) */
.settings-header h2{font-size:18px;font-weight:600}
.close-btn{background:none;border:none;color:var(--text2);font-size:22px;cursor:pointer;padding:4px}
.close-btn:hover{color:var(--text)}
.settings-group{margin-bottom:20px}
.settings-group h3{font-size:13px;font-weight:600;color:var(--text2);margin-bottom:10px;text-transform:uppercase;letter-spacing:0.5px}
.s-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--surface2)}
.s-item label{font-size:13px;color:var(--text)}
.s-item input[type="number"],.s-item input[type="text"],.s-item select{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:13px;width:130px}
.s-item select{cursor:pointer}
.s-item .wide{width:220px}
.ie-btns{display:flex;gap:8px;margin-top:12px}
.ie-btns button{flex:1;padding:9px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer;font-size:13px;transition:all .2s}
.ie-btns button:hover{background:var(--surface3)}
.readme-btn{width:100%;padding:10px;background:var(--surface2);border:1px solid var(--border);color:var(--text2);border-radius:8px;cursor:pointer;font-size:13px;transition:all .2s;text-align:center;margin-top:12px}
.readme-btn:hover{background:var(--surface3);color:var(--text)}
.modal-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:500;display:none;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal-content{background:var(--surface);border:1px solid var(--border);border-radius:12px;width:90%;max-width:700px;max-height:80vh;overflow-y:auto;padding:24px;position:relative}
.modal-content h2{font-size:18px;font-weight:600;margin-bottom:16px;color:var(--primary)}
.modal-content h3{font-size:15px;font-weight:600;margin-top:16px;margin-bottom:8px;color:var(--text)}
.modal-content p,.modal-content li{font-size:13px;line-height:1.7;color:var(--text)}
.modal-content ul{padding-left:20px;margin-bottom:12px}
.modal-content code{background:var(--surface2);padding:1px 5px;border-radius:3px;font-size:12px;color:var(--orange)}
.modal-close{position:absolute;top:12px;right:16px;background:none;border:none;color:var(--text2);font-size:22px;cursor:pointer}
.modal-close:hover{color:var(--text)}
.history-list{max-height:65vh;overflow-y:auto}
.history-item{background:var(--surface2);border-radius:8px;padding:12px;margin-bottom:8px}
.history-item .hi-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.history-item .hi-text{font-size:14px;font-weight:500}
.history-item .hi-date{font-size:11px;color:var(--text2)}
.history-item .hi-detail{font-size:12px;color:var(--text2);line-height:1.5;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.toast{position:fixed;bottom:20px;right:20px;padding:10px 16px;border-radius:8px;font-size:12px;z-index:600;transform:translateX(120%);transition:transform .3s;max-width:300px;box-shadow:0 4px 12px rgba(0,0,0,0.3)}
.toast.show{transform:translateX(0)}
.toast.success{background:var(--green);color:#000}
.toast.error{background:var(--red);color:#fff}
.toast.info{background:var(--blue);color:#000}
.spinner{width:16px;height:16px;border:2px solid rgba(255,255,255,0.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;display:inline-block;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.changelog-version{font-weight:600;color:var(--primary);margin-top:14px;margin-bottom:4px;font-size:14px}
.changelog-date{font-size:11px;color:var(--text2);margin-left:8px}
.clone-status{margin-top:8px;padding:8px 12px;background:var(--surface2);border-radius:6px;font-size:12px;color:var(--text2);display:none}
.clone-status.active{display:block}

.engine-btn.active-kk{background:var(--kk-color);color:#fff}
.engine-badge.kk{background:var(--kk-color);color:#fff}
.gen-btn.kk-active{background:var(--kk-color)}
.kk-cfg-card{display:none}.kk-cfg-card.visible{display:block}
.kk-info-box{background:var(--bg);border-radius:8px;padding:14px;margin-bottom:12px;border:1px solid var(--border);font-size:.85rem;color:var(--text2);line-height:1.8}
.kk-info-box b{color:var(--text)}.kk-info-box code{background:var(--surface2);padding:1px 6px;border-radius:4px;font-size:.8rem;color:var(--orange)}
.kk-conn-status{display:inline-flex;align-items:center;gap:6px;font-size:.85rem;font-weight:500;padding:4px 12px;border-radius:6px}
.kk-conn-status.ok{background:rgba(0,184,148,.15);color:var(--green)}.kk-conn-status.fail{background:rgba(225,112,85,.15);color:var(--red)}.kk-conn-status.pen{background:rgba(253,203,110,.15);color:var(--orange)}
.kk-conn-dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.kk-conn-status.ok .kk-conn-dot{background:var(--green)}.kk-conn-status.fail .kk-conn-dot{background:var(--red)}.kk-conn-status.pen .kk-conn-dot{background:var(--orange)}
.kk-models{display:flex;gap:8px;margin-top:8px}
.kk-model{flex:1;padding:10px 12px;border-radius:8px;border:2px solid var(--border);background:var(--bg);color:var(--text);cursor:pointer;text-align:center;transition:all .2s;font-size:.85rem}
.kk-model:hover{border-color:var(--kk-color)}.kk-model.sel{border-color:var(--kk-color);background:rgba(16,185,129,.15)}
.kk-model .mn{font-weight:600;display:block}.kk-model .md{font-size:.75rem;color:var(--text2);margin-top:2px}.kk-model .mc{font-size:.7rem;color:var(--orange);margin-top:4px}
.kk-params{background:var(--bg);border-radius:8px;padding:14px;margin-top:12px;border:1px solid var(--border)}
.kk-params .pt{font-size:.9rem;font-weight:600;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.kk-param-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.kk-param-row label{min-width:70px;margin-bottom:0;font-size:.85rem;flex-shrink:0}
.kk-param-row input[type=range]{flex:1;min-width:120px;accent-color:var(--kk-color);height:6px}
.kk-param-row .pv{min-width:40px;text-align:right;font-size:.85rem;color:var(--kk-color);font-weight:600;font-family:monospace}
.kk-param-row select{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:4px 8px;color:var(--text);font-size:.85rem}
.kk-param-row select:focus{outline:none;border-color:var(--kk-color)}
.kk-param-hint{font-size:.75rem;color:var(--text2);margin-left:8px}
.kk-pro-only{opacity:.4;pointer-events:none;transition:opacity .3s}
.kk-pro-only.active{opacity:1;pointer-events:auto}
.kk-quota{background:var(--bg);border-radius:8px;padding:12px 16px;margin-top:12px;border:1px solid var(--border)}
.kk-qbg{height:6px;background:var(--surface3);border-radius:3px;overflow:hidden;margin-top:8px}
.kk-qb{height:100%;border-radius:3px;transition:width .5s}
.kk-qb.g{background:linear-gradient(to right,#34d399,#22c55e)}.kk-qb.y{background:linear-gradient(to right,#fbbf24,#f59e0b)}.kk-qb.r{background:linear-gradient(to right,#f87171,#ef4444)}
.kk-qt{font-size:.8rem;color:var(--text2);margin-top:6px;display:flex;justify-content:space-between}
.cf-panel{border:2px solid var(--orange)!important;background:linear-gradient(135deg,rgba(253,203,110,.05),var(--surface))!important}
.cf-step{display:flex;gap:12px;align-items:flex-start;margin:10px 0;padding:10px;background:var(--bg);border-radius:8px}
.cf-num{min-width:28px;height:28px;border-radius:50%;background:var(--orange);color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;flex-shrink:0}
.cf-body{flex:1}.cf-body p{margin:2px 0;font-size:.88rem}.cf-body a{color:var(--kk-color);word-break:break-all}
.cf-url-box{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 12px;margin:8px 0;word-break:break-all;font-family:'Courier New',monospace;font-size:.82rem;color:var(--kk-color)}
.cf-actions{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}
.iframe-wrap{margin-top:16px;border:1px solid var(--border);border-radius:8px;overflow:hidden;background:white;position:relative}
.iframe-wrap iframe{width:100%;height:420px;border:none}
.iframe-overlay{position:absolute;top:0;left:0;right:0;bottom:0;background:rgba(15,15,15,.8);display:flex;align-items:center;justify-content:center;z-index:10}
.iframe-overlay .inner{text-align:center;color:var(--text)}
.iframe-overlay .inner p{margin:8px 0;font-size:.9rem}
.log-console{max-height:400px;overflow-y:auto;background:var(--bg);border-radius:8px;padding:12px;font-family:'Courier New',monospace;font-size:.78rem;line-height:1.5;margin-top:12px}
.log-entry{padding:2px 0;word-break:break-all}.log-entry.i{color:var(--text2)}.log-entry.s{color:var(--green)}.log-entry.e{color:var(--red)}.log-entry.w{color:var(--orange)}

/* Speaker Assignment Styles */
.speaker-card.visible{display:block}
.speaker-warning{background:rgba(253,203,110,0.1);border:1px solid var(--orange);border-radius:8px;padding:12px 16px;margin-bottom:14px;display:flex;align-items:flex-start;gap:10px;font-size:13px;color:var(--orange)}
.speaker-warning .sw-icon{font-size:18px;flex-shrink:0;margin-top:1px}
.speaker-warning .sw-text{flex:1;line-height:1.6}
.speaker-warning .sw-text b{color:#fff}
.speaker-warning .sw-actions{display:flex;gap:6px;margin-top:6px}
.speaker-warning .sw-actions button{padding:4px 12px;border-radius:6px;border:1px solid var(--orange);background:transparent;color:var(--orange);cursor:pointer;font-size:12px;transition:all .2s}
.speaker-warning .sw-actions button:hover{background:var(--orange);color:#000}
.speaker-list{display:flex;flex-direction:column;gap:10px}
.speaker-row{display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg);border-radius:8px;border:1px solid var(--border)}
.speaker-row .sp-color{width:12px;height:12px;border-radius:50%;flex-shrink:0}
.speaker-row .sp-name{font-weight:600;font-size:14px;min-width:60px;flex-shrink:0}
.speaker-row .sp-stats{font-size:11px;color:var(--text2);margin-left:4px}
.speaker-row .sp-select{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:13px;min-width:140px}
.speaker-row .sp-upload{display:flex;align-items:center;gap:6px}
.speaker-row .sp-upload-btn{background:var(--primary);border:none;color:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;white-space:nowrap;transition:all .2s}
.speaker-row .sp-upload-btn:hover{background:var(--primary-hover)}
.speaker-row .sp-upload-filename{font-size:11px;color:var(--green);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sp-preview{font-size:11px;color:var(--text2);margin-left:4px}
.seg-speaker{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-right:4px}
.seg-speaker.sp0{background:rgba(108,92,231,0.3);color:#a29bfe}
.seg-speaker.sp1{background:rgba(0,184,148,0.3);color:#55efc4}
.seg-speaker.sp2{background:rgba(116,185,255,0.3);color:#74b9ff}
.seg-speaker.sp3{background:rgba(253,203,110,0.3);color:#fdcb6e}
.seg-speaker.sp4{background:rgba(225,112,85,0.3);color:#e17055}
.speaker-pattern-row{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.speaker-pattern-row input{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:12px;font-family:monospace}
.speaker-pattern-row .sp-del{background:none;border:none;color:var(--red);cursor:pointer;font-size:16px;padding:2px 6px}
.speaker-pattern-row .sp-del:hover{opacity:0.7}

.settings-tabs{display:flex;gap:4px;margin-bottom:16px;border-bottom:1px solid var(--border)}
.st-tab{flex:1;padding:10px 6px;background:none;border:none;border-bottom:2px solid transparent;color:var(--text2);font-size:13px;cursor:pointer;transition:all .2s}
.st-tab:hover{color:var(--text)}
.st-tab.active{color:var(--primary);border-bottom-color:var(--primary);font-weight:600}
.rule-row{display:flex;gap:6px;align-items:center;padding:6px 0;border-bottom:1px solid var(--surface2);font-size:12px}
.rule-row .rr-name{min-width:82px;color:var(--text);flex-shrink:0}
.rule-row .rr-pat{flex:1;font-family:monospace;color:var(--orange);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:96px}
.rule-row .rr-type{font-size:10px;background:var(--surface2);padding:2px 6px;border-radius:3px;color:var(--text2);flex-shrink:0}
.rule-row .rr-on{flex-shrink:0;cursor:pointer}
.rule-row .rr-del{background:none;border:none;color:var(--red);cursor:pointer;font-size:14px;padding:0 4px;flex-shrink:0}
.ic{width:1em;height:1em;display:inline-block;vertical-align:-0.12em;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex-shrink:0}.ic.sm{width:12px;height:12px}.rule-row .rr-name,.rule-row .rr-pat{cursor:pointer}.rule-row .rr-name:hover,.rule-row .rr-pat:hover{color:var(--primary)}.rule-row .rr-edit{width:100%;background:var(--surface2);border:1px solid var(--primary);color:var(--text);padding:3px 6px;border-radius:4px;font-size:12px;font-family:inherit}.rule-row .rr-edit.mono{font-family:monospace}.rule-row .rr-warn{font-size:10px;color:var(--orange);flex-shrink:0}.rule-edit-wrap{display:flex;flex-direction:column;gap:4px;flex:1}.rule-edit-row{display:flex;gap:4px;align-items:center}.rule-hint{font-size:11px;color:var(--text2)}.panel-footer{margin-top:20px;padding-top:12px;border-top:1px solid var(--border)}
@media(max-width:640px){.main{padding:12px}.header{padding:8px 12px;flex-wrap:wrap;gap:8px}.settings-panel{width:100%}.card{padding:14px}.modal-content{width:95%;padding:16px}.speaker-row{flex-wrap:wrap}.speaker-row .sp-name{min-width:50px}}}
</style>
</head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true"><defs>
<symbol id="i-gear" viewBox="0 0 24 24"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></symbol>
<symbol id="i-history" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></symbol>
<symbol id="i-book" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></symbol>
<symbol id="i-mic" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/></symbol>
<symbol id="i-music" viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></symbol>
<symbol id="i-term" viewBox="0 0 24 24"><path d="M4 17l6-6-6-6M12 19h8"/></symbol>
<symbol id="i-file" viewBox="0 0 24 24"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M13 2v7h7"/></symbol>
<symbol id="i-filetext" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></symbol>
<symbol id="i-upload" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/></symbol>
<symbol id="i-download" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></symbol>
<symbol id="i-zap" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></symbol>
<symbol id="i-warn" viewBox="0 0 24 24"><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></symbol>
<symbol id="i-refresh" viewBox="0 0 24 24"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></symbol>
<symbol id="i-wrench" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></symbol>
<symbol id="i-folder" viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></symbol>
<symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></symbol>
<symbol id="i-play" viewBox="0 0 24 24"><path d="M7 4l13 8-13 8z"/></symbol>
<symbol id="i-pause" viewBox="0 0 24 24"><path d="M9 5v14M15 5v14"/></symbol>
<symbol id="i-stop" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></symbol>
<symbol id="i-pen" viewBox="0 0 24 24"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></symbol>
<symbol id="i-spark" viewBox="0 0 24 24"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"/></symbol>
<symbol id="i-clip" viewBox="0 0 24 24"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></symbol>
</defs></svg>

<div class="header">
  <div class="header-left">
    <h1>TTS Voice Lab</h1>
    <span class="ver">v${VERSION}</span>
    <div class="api-status">
      <span class="dot checking" id="apiDot"></span>
      <span id="apiText">检测中...</span>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px">
    <button class="hdr-btn" onclick="toggleSettings()"><svg class="ic" aria-hidden="true"><use href="#i-gear"></use></svg> 设置</button>
  </div>
</div>

<div class="main">
  <div class="layout-tabs">
    <button class="layout-tab active" onclick="switchLayoutTab('content')"><svg class="ic" aria-hidden="true"><use href="#i-file"></use></svg> 参数设定</button>
    <button class="layout-tab" onclick="switchLayoutTab('log')"><svg class="ic" aria-hidden="true"><use href="#i-term"></use></svg> 控制台</button>
  </div>
  <div class="main-grid">
  <div class="main-content">
  <!-- Card 1: Text Input -->
  <div class="card text-card" id="textCard">
    <div class="card-title"><span class="icon"><svg class="ic" aria-hidden="true"><use href="#i-filetext"></use></svg></span> 合成文本</div>
    <div class="docx-drop-overlay" id="docxDropOverlay"><p><svg class="ic" aria-hidden="true"><use href="#i-file"></use></svg> 释放 Word 文档，自动读取文本</p></div>
    <textarea class="text-area" id="textInput" placeholder="输入要合成的文本...&#10;支持长文本自动分段处理，也可拖入 Word 文档&#10;换行将保留用于字幕分行" oninput="updateTextStats()"></textarea>
    <div class="docx-actions">
      <button class="docx-btn" onclick="document.getElementById('docxFileInput').click()"><svg class="ic" aria-hidden="true"><use href="#i-file"></use></svg> 上传 Word 文档</button>
      <span class="docx-info" id="docxInfo"></span>
    </div>
    <input type="file" id="docxFileInput" accept=".docx" style="display:none" onchange="handleDocxUpload(event)">
    <div class="text-stats">
      <span>字数: <b id="charCount">0</b></span>
      <span>行数: <b id="lineCount">0</b></span>
      <span>预计分段: <b id="segCount">0</b></span>
    </div>
  </div>

  <!-- Card 2: Speaker Assignment -->
  <div class="card speaker-card" id="speakerCard">
    <div class="card-title"><span class="icon"><svg class="ic" aria-hidden="true"><use href="#i-mic"></use></svg></span> 说话人分配 <span style="font-size:11px;color:var(--text2)" id="speakerModeLabel">单人模式</span></div>
    <div class="speaker-warning" id="speakerWarning" style="display:none">
      <span class="sw-icon"><svg class="ic" aria-hidden="true"><use href="#i-warn"></use></svg></span>
      <div class="sw-text" id="speakerWarningText"></div>
    </div>
    <div class="speaker-list" id="speakerList"></div>
  </div>

  <!-- v2.14 Card: Before/After Preview -->
  <div class="card" id="previewCard" style="display:none">
    <div class="card-title"><span class="icon"><svg class="ic" aria-hidden="true"><use href="#i-search"></use></svg></span> GLM 预处理预览 (Before / After)</div>
    <p style="font-size:12px;color:var(--text2);margin-bottom:10px">点击"预览 GLM 处理"查看转换前后对比。After 文本框可手动编辑，编辑后将以此文本提交 TTS。</p>
    <div id="previewBody" style="max-height:400px;overflow-y:auto;font-size:12px"></div>
    <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
      <button class="dl-btn" id="previewBtn" onclick="loadPreview()"><svg class="ic" aria-hidden="true"><use href="#i-search"></use></svg> 预览 GLM 处理</button>
      <button class="dl-btn" id="regenGlmBtn" onclick="loadPreview()" style="display:none"><svg class="ic" aria-hidden="true"><use href="#i-refresh"></use></svg> 重新调用 GLM</button>
      <button class="dl-btn primary" id="applyPreviewBtn" onclick="applyPreviewAndGenerate()" style="display:none"><svg class="ic" aria-hidden="true"><use href="#i-check"></use></svg> 应用并开始合成</button>
      <button class="dl-btn" onclick="document.getElementById('previewCard').style.display='none'">关闭预览</button>
    </div>
  </div>

  <!-- v2.14 Card: Speaker Alternation Warning -->
  <div class="card" id="alternationWarning" style="display:none;border-color:var(--orange);background:rgba(253,203,110,0.05)">
    <div class="card-title" style="color:var(--orange)"><span class="icon"><svg class="ic" aria-hidden="true"><use href="#i-warn"></use></svg></span> 说话人交替异常</div>
    <p style="font-size:12px;color:var(--text2);margin-bottom:10px" id="alternationWarningText"></p>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <button class="dl-btn" id="alternationFixBtn" onclick="autoFixAlternation()" style="background:var(--orange);color:#000;border-color:var(--orange)"><svg class="ic" aria-hidden="true"><use href="#i-wrench"></use></svg> 自动交替</button>
      <button class="dl-btn" id="alternationDismissBtn" onclick="dismissAlternationWarning()" style="background:transparent;color:var(--text2);border:1px solid var(--border);font-size:11px;padding:4px 10px;cursor:pointer;border-radius:4px;opacity:0.7" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">忽略</button>
    </div>
  </div>

  <!-- Card 3: Generate -->
  <div class="card">
    <button class="gen-btn nv-active" id="generateBtn" onclick="onGenerateClick()">
      <span id="genBtnText"><svg class="ic" aria-hidden="true"><use href="#i-zap"></use></svg> 开始合成 (NiceVoice)</span>
    </button>
    <button class="cancel-btn" id="cancelBtn" onclick="cancelGenerate()" style="display:none"><svg class="ic" aria-hidden="true"><use href="#i-stop"></use></svg> 取消生成</button>
    <div class="progress-bar" id="progressBar">
      <div class="progress-fill" id="progressFill" style="width:0%"></div>
    </div>
    <div class="elapsed" id="elapsed" style="display:none">已用时: 0s</div>
    <table class="seg-table" id="segTable" style="display:none">
      <thead><tr><th>#</th><th>文本</th><th>状态</th><th>时长</th><th>试听</th></tr></thead>
      <tbody id="segBody"></tbody>
    </table>
  </div>

  <!-- Card 4: Results -->
  <div class="card result-section" id="resultSection">
    <div class="card-title"><span class="icon"><svg class="ic" aria-hidden="true"><use href="#i-music"></use></svg></span> 合成结果</div>
    <audio class="result-audio" id="resultAudio" controls></audio>
    <div class="dl-btns">
      <button class="dl-btn primary" onclick="downloadWav()"><svg class="ic" aria-hidden="true"><use href="#i-download"></use></svg> 下载 WAV（含 BGM）</button>
      <button class="dl-btn" onclick="downloadWavVoiceOnly()"><svg class="ic" aria-hidden="true"><use href="#i-download"></use></svg> 下载 WAV（纯人声）</button>
      <button class="dl-btn" onclick="downloadSrt()"><svg class="ic" aria-hidden="true"><use href="#i-download"></use></svg> 下载 SRT</button>
      <button class="dl-btn" onclick="downloadJianYing()"><svg class="ic" aria-hidden="true"><use href="#i-download"></use></svg> 下载剪映工程</button>
    </div>
  </div>

  <!-- v2.15 Card: Podcast Metadata Generation -->
  <div class="card" id="metadataCard" style="display:none">
    <div class="card-title"><span class="icon"><svg class="ic" aria-hidden="true"><use href="#i-filetext"></use></svg></span> 播客元数据生成</div>
    <p style="font-size:12px;color:var(--text2);margin-bottom:10px">基于合成文本调用 GLM 生成播客标题、Shownotes、Tags，方便上传小宇宙等平台。</p>
    <div style="margin-bottom:10px">
      <label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">原始新闻要点（可选，作为提示词一部分发送给 GLM）</label>
      <textarea id="metadataRawNews" rows="6" placeholder="粘贴原始 10 条新闻要点，例如：&#10;1.TikTok发布5月短剧分账战报...&#10;2.哔哩哔哩直播姬移动端App停止开播...&#10;..." style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px;line-height:1.5;resize:vertical;font-family:inherit"></textarea>
    </div>
    <button class="dl-btn primary" id="genMetadataBtn" onclick="generateMetadata()"><svg class="ic" aria-hidden="true"><use href="#i-spark"></use></svg> 生成标题/摘要/标签</button>
    <div style="margin-top:12px;display:none" id="metadataResult">
      <div style="margin-bottom:8px"><label style="font-size:12px;color:var(--text2)">标题</label><input type="text" id="metadataTitle" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>
      <div style="margin-bottom:8px"><label style="font-size:12px;color:var(--text2)">Shownotes</label><textarea id="metadataShownotes" rows="14" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px;line-height:1.5;resize:vertical;font-family:inherit"></textarea></div>
      <div style="margin-bottom:8px"><label style="font-size:12px;color:var(--text2)">Tags（逗号分隔）</label><input type="text" id="metadataTags" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>
      <button class="dl-btn" onclick="copyMetadata()"><svg class="ic" aria-hidden="true"><use href="#i-clip"></use></svg> 一键复制全部</button>
    </div>
  </div>
  </div>
  <div class="main-log hidden-tab">
    <div class="card">
      <div class="card-title"><span class="icon"><svg class="ic" aria-hidden="true"><use href="#i-term"></use></svg></span> 控制台 Log</div>
      <div class="log-console" id="logBox"></div>
    </div>
  </div>
  </div>
</div>

<!-- Settings Panel -->
<div class="settings-overlay" id="settingsOverlay" onclick="toggleSettings()"></div>
<div class="settings-panel" id="settingsPanel">
  <div class="settings-header">
    <h2><svg class="ic" aria-hidden="true"><use href="#i-gear"></use></svg> 设置</h2>
    <button class="close-btn" onclick="toggleSettings()"><svg class="ic" aria-hidden="true"><use href="#i-x"></use></svg></button>
  </div>
  <div class="settings-tabs">
    <button class="st-tab active" data-tab="settings" onclick="switchSettingsTab('settings')"><svg class="ic" aria-hidden="true"><use href="#i-gear"></use></svg> 设置</button>
    <button class="st-tab" data-tab="history" onclick="switchSettingsTab('history')"><svg class="ic" aria-hidden="true"><use href="#i-history"></use></svg> 历史</button>
    <button class="st-tab" data-tab="about" onclick="switchSettingsTab('about')"><svg class="ic" aria-hidden="true"><use href="#i-book"></use></svg> 关于</button>
  </div>
  <div id="stabSettings">
  <div class="settings-group" id="nvSettings">
    <h3>NiceVoice 设置</h3>
    <div class="s-item"><label>请求间隔 (秒)</label><input type="number" id="cfgNvWait" min="10" max="30" step="1"></div>
    <div class="s-item"><label>最大字数/段</label><input type="number" id="cfgNvMaxChars" min="50" max="150"></div>
    <div class="s-item"><label>最大轮询次数</label><input type="number" id="cfgNvMaxPoll" min="20" max="120"></div>
  </div>
  <div class="settings-group">
    <h3>音源管理</h3>
    <div style="margin-bottom:8px;display:flex;gap:8px;flex-wrap:wrap">
      <button class="clear-btn" onclick="showNewVoiceForm()" style="background:var(--primary);color:#fff;border-color:var(--primary)"><svg class="ic" aria-hidden="true"><use href="#i-plus"></use></svg> 新建音源</button>
      <button class="clear-btn" onclick="exportVoices()"><svg class="ic" aria-hidden="true"><use href="#i-upload"></use></svg> 导出音源</button>
      <button class="clear-btn" onclick="document.getElementById('importVoicesFile').click()"><svg class="ic" aria-hidden="true"><use href="#i-download"></use></svg> 导入音源</button>
      <input type="file" id="importVoicesFile" accept=".json" style="display:none" onchange="importVoices(event)">
    </div>
    <div id="newVoiceForm" style="display:none;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px">
      <div style="font-weight:600;margin-bottom:8px;font-size:.9rem">新建音源</div>
      <div style="display:flex;gap:8px;margin-bottom:8px"><input type="text" id="newVoiceName" placeholder="音源名称" style="flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>
      <div class="upload-zone" id="settingsUploadZone" onclick="document.getElementById('settingsVoiceFile').click()" style="padding:16px">
        <div class="uz-icon" style="font-size:20px"><svg class="ic" aria-hidden="true"><use href="#i-mic"></use></svg></div>
        <div class="uz-text" id="settingsUploadText">点击上传参考音频</div>
      </div>
      <input type="file" id="settingsVoiceFile" accept="audio/*" style="display:none" onchange="handleSettingsVoiceUpload(event)">
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="clear-btn" onclick="submitNewVoice()" style="background:var(--green);color:#000;border-color:var(--green)"><svg class="ic" aria-hidden="true"><use href="#i-check"></use></svg> 提交</button>
        <button class="clear-btn" onclick="hideNewVoiceForm()">取消</button>
      </div>
    </div>
    <div id="settingsVoiceList"></div>
  </div>
  <div class="settings-group">
    <h3>读音替换规则</h3>
    <p style="font-size:11px;color:var(--text2);margin-bottom:8px">发送给 TTS 前按顺序执行。内置与自定义规则结构一致：规则名称、匹配内容 → 替换内容、类型、启用开关。点击名称或内容即可修改（焦点移开自动保存，Enter 保存、Esc 取消）。文本/通配/正则为本地规则，无需 GLM Key；GLM 语义规则需配置 Key 并开启智能预处理。通配符：* 任意串、? 单字。</p>
    <div style="font-size:11px;color:var(--text2);margin:2px 0 4px">内置规则（可编辑、可停用，改坏可一键复原）</div>
    <div id="builtinRulesList"></div>
    <div style="font-size:11px;color:var(--text2);margin:10px 0 4px">自定义规则</div>
    <div id="customRulesList"></div>
    <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">
      <input type="text" id="newRuleName" placeholder="规则名称" style="width:110px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px">
      <input type="text" id="newRulePattern" placeholder="匹配内容（GLM 规则填指令）" style="flex:1;min-width:120px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px">
      <input type="text" id="newRuleReplacement" placeholder="替换为（GLM 可留空）" style="flex:1;min-width:100px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px">
      <select id="newRuleType" style="width:76px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 4px;border-radius:6px;font-size:12px">
        <option value="text">文本</option>
        <option value="wildcard">通配</option>
        <option value="regex">正则</option>
        <option value="llm">GLM</option>
      </select>
      <button onclick="addUserTtsRule()" style="padding:6px 12px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer;font-size:12px">添加</button>
    </div>
    <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
      <button onclick="resetBuiltinRules()" style="padding:5px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--orange);cursor:pointer">复原默认</button>
      <button onclick="exportRules()" style="padding:5px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">导出规则</button>
      <button onclick="document.getElementById('importRulesFile').click()" style="padding:5px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">导入规则</button>
      <input type="file" id="importRulesFile" accept=".json" style="display:none" onchange="importRules(event)">
    </div>
  </div>
  <div class="settings-group">
    <h3>说话人识别模式</h3>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:8px">
      <label style="font-size:12px;color:var(--text2)">内置模式（无需配置）</label>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="checkbox" id="cfgSpBracket" checked> 【姓名】格式</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="checkbox" id="cfgSpColon" checked> 姓名：格式</label>
      </div>
    </div>
    <div style="margin-top:10px">
      <label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">自定义说话人正则模式 <span style="font-size:11px;opacity:0.7">（匹配后的第一个捕获组为说话人名）</span></label>
      <div id="speakerPatternsList"></div>
      <div class="save-source-row" style="margin-top:6px">
        <input type="text" id="newSpeakerPattern" placeholder="如: ^(\\\\S+?)\\\\s*>>>\\\\s*">
        <button onclick="addSpeakerPattern()">添加模式</button>
      </div>
    </div>
    <div class="s-item" style="margin-top:8px"><label>防呆阈值（比例）</label><input type="number" id="cfgSpBalance" min="2" max="10" step="1" style="width:80px"></div>
  </div>
  <div class="settings-group">
    <h3>GLM 文本预处理</h3>
    <div class="s-item">
      <label>API Key</label>
      <input type="password" id="cfgGlmApiKey" placeholder="输入 GLM API Key（可选）" style="flex:1">
      <button onclick="testGlmApiKey()" style="margin-left:6px;padding:4px 10px;font-size:12px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">测试</button>
    </div>
    <div class="s-item">
      <label>启用智能预处理</label>
      <select id="cfgGlmPreprocess" style="flex:0 0 auto">
        <option value="off">关闭（仅正则）</option>
        <option value="fallback">回退模式（正则失败时用GLM）</option>
        <option value="always">始终使用GLM</option>
      </select>
    </div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">使用 GLM-Flash-4 进行中文数字、符号、多音字智能预处理，需 API Key。回退模式下仅正则无法处理时调用。</p>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>系统提示词（高级，留空使用默认）</label>
      <textarea id="cfgGlmSystemPrompt" rows="8" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:6px;font-size:12px;font-family:monospace;line-height:1.5;resize:vertical" placeholder="留空使用默认提示词。可在此自定义数字/标点/符号处理规则..."></textarea>
      <div style="display:flex;gap:6px">
        <button onclick="resetGlmPrompt()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">恢复默认</button>
        <button onclick="previewGlmProcess()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">试一下</button>
      </div>
    </div>
  </div>

  <div class="settings-group">
    <h3>BGM 混音</h3>
    <div class="s-item"><label>启用 BGM</label><input type="checkbox" id="cfgBgmEnabled"></div>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>BGM 文件</label>
      <div style="display:flex;gap:6px;width:100%;align-items:center">
        <button onclick="document.getElementById('bgmFileInput').click()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer"><svg class="ic" aria-hidden="true"><use href="#i-folder"></use></svg> 选择 BGM</button>
        <span id="bgmFileName" style="font-size:11px;color:var(--text2);flex:1"></span>
        <button onclick="previewBgm()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer"><svg class="ic" aria-hidden="true"><use href="#i-play"></use></svg> 试听</button>
        <button onclick="clearBgm()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--red);cursor:pointer"><svg class="ic" aria-hidden="true"><use href="#i-x"></use></svg></button>
      </div>
      <input type="file" id="bgmFileInput" accept="audio/*" style="display:none" onchange="handleBgmUpload(event)">
      <audio id="bgmPreviewAudio" style="display:none"></audio>
    </div>
    <div class="s-item"><label>BGM 音量</label><input type="range" id="cfgBgmVolume" min="0" max="100" step="1" style="flex:1;max-width:200px"><span id="cfgBgmVolumeVal" style="font-size:11px;color:var(--text2);min-width:36px;text-align:right">35%</span></div>
    <div class="s-item"><label>人声段 BGM 衰减</label><input type="range" id="cfgBgmDuckDepth" min="0" max="100" step="5" style="flex:1;max-width:200px"><span id="cfgBgmDuckDepthVal" style="font-size:11px;color:var(--text2);min-width:36px;text-align:right">50%</span></div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">BGM 音量按 sqrt 刻度（35% ≈ -18dB）。人声段 BGM 自动衰减（50% ≈ -6dB 进一步降低）。试听请先选择 BGM。</p>
  </div>

  <div class="settings-group">
    <h3>人声音量归一化</h3>
    <div class="s-item"><label>启用 peak normalize</label><input type="checkbox" id="cfgVoiceNormalize"></div>
    <div class="s-item"><label>目标峰值 (dB)</label><input type="number" id="cfgVoiceTargetPeak" min="-12" max="0" step="1" style="width:80px"></div>
    <div class="s-item"><label>说话人 RMS 拉平</label><input type="checkbox" id="cfgSpeakerRms"></div>
    <div class="s-item"><label>女声轻量压缩</label><input type="checkbox" id="cfgFemaleCompress"></div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">peak normalize 将所有段峰值归一到目标 dB；RMS 拉平让所有说话人响度一致；女声压缩治忽大忽小。</p>
  </div>

  <div class="settings-group">
    <h3>片头片尾拼接</h3>
    <div class="s-item"><label>启用片头片尾</label><input type="checkbox" id="cfgIntroOutroEnabled"></div>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>片头文件</label>
      <div style="display:flex;gap:6px;width:100%;align-items:center">
        <button onclick="document.getElementById('introFileInput').click()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer"><svg class="ic" aria-hidden="true"><use href="#i-folder"></use></svg> 选择片头</button>
        <span id="introFileName" style="font-size:11px;color:var(--text2);flex:1"></span>
        <button onclick="clearIntro()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--red);cursor:pointer"><svg class="ic" aria-hidden="true"><use href="#i-x"></use></svg></button>
      </div>
      <input type="file" id="introFileInput" accept="audio/*" style="display:none" onchange="handleIntroUpload(event)">
    </div>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>片尾文件</label>
      <div style="display:flex;gap:6px;width:100%;align-items:center">
        <button onclick="document.getElementById('outroFileInput').click()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer"><svg class="ic" aria-hidden="true"><use href="#i-folder"></use></svg> 选择片尾</button>
        <span id="outroFileName" style="font-size:11px;color:var(--text2);flex:1"></span>
        <button onclick="clearOutro()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--red);cursor:pointer"><svg class="ic" aria-hidden="true"><use href="#i-x"></use></svg></button>
      </div>
      <input type="file" id="outroFileInput" accept="audio/*" style="display:none" onchange="handleOutroUpload(event)">
    </div>
    <div class="s-item"><label>拼接模式</label>
      <select id="cfgIntroOutroMode" style="flex:0 0 auto">
        <option value="fade">淡入淡出（推荐）</option>
        <option value="direct">直接拼接</option>
      </select>
    </div>
    <div class="s-item"><label>淡入淡出时长 (ms)</label><input type="number" id="cfgIntroOutroFade" min="0" max="3000" step="100" style="width:100px"></div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">参考 podmerge.html 实现。淡入淡出模式下片头与主音频叠化 500ms。</p>
  </div>

  <div class="settings-group">
    <h3>历史与数据</h3>
    <div class="s-item"><label>最大保存条数</label><input type="number" id="cfgMaxHistory" min="1" max="50"></div>
  </div>

  <div class="settings-group">
    <h3>导入/导出</h3>
    <div class="ie-btns">
      <button onclick="exportConfig()"><svg class="ic" aria-hidden="true"><use href="#i-upload"></use></svg> 导出配置</button>
      <button onclick="document.getElementById('importFile').click()"><svg class="ic" aria-hidden="true"><use href="#i-download"></use></svg> 导入配置</button>
    </div>
    <input type="file" id="importFile" accept=".json" style="display:none" onchange="importConfig(event)">
  </div>
  </div><!-- /stabSettings -->

  <div id="stabHistory" style="display:none">
    <p style="font-size:11px;color:var(--text2);margin-bottom:10px">生成记录保留文本与分段信息，可恢复到编辑区重新生成或下载。</p>
    <div class="history-list" id="historyList"></div>
  </div>

  <div id="stabAbout" style="display:none">
    <div id="readmeBody"></div>
  </div>

  <div class="panel-footer"><button class="cancel-btn" onclick="toggleSettings()">关闭面板</button></div>
</div>

<div class="toast" id="toast"></div>

<script>
// ==================== Constants & State ====================
var APP_VERSION = '${VERSION}';
// v2.14: Client-side README_CONTENT (base64-decoded to avoid template literal escaping issues)
var README_CONTENT = (function() {
  var b64 = 'IyBUVFMgVm9pY2UgTGFiIHYke1ZFUlNJT059Cgo+IOWfuuS6jiBDbG91ZGZsYXJlIFdvcmtlciDnmoTmtY/op4jlmajnq6/or63pn7PlhYvpmoYgVFRTIOW3peWFt++8jE5pY2VWb2ljZSDljZXlvJXmk44gKyDplb/mlofmnKzliIbmrrXlkIjmiJAgKyDlrZfluZXnlJ/miJAgKyDliarmmKDlt6XnqIvlr7zlh7rjgIIKCiMjIOeugOS7iwoKVFRTIFZvaWNlIExhYiDmmK/kuIDkuKrln7rkuo7mtY/op4jlmajnmoTor63pn7PlhYvpmoYgVFRTIOW3peWFt++8jOaUr+aMgemVv+aWh+acrOWIhuauteWQiOaIkOOAgeWtl+W5leeUn+aIkOWSjOWJquaYoOW3peeoi+WvvOWHuuOAggoKdjIuMjIg57O757uf5YyW5L+u5aSN5pat5Y+l6L6555WM77ya5byV5Y+36L2s5YGc6aG/44CB5o2i6KGM5L+d55WZ5Y+l55WM44CB5Y+l5pyr56m65qC85by65YyW6L6555WM77yM5bm25oqK5YWo6YOo5paH5pys6L2s5o2i6KeE5YiZ5byA5pS+5Li65Y+v6YWN572u55qE4oCc6K+76Z+z5pu/5o2i6KeE5YiZ4oCd77yI5YaF572u6KeE5YiZ5Y+v5ZCv5YGc77yM5pSv5oyB6Ieq5a6a5LmJ5q2j5YiZL+mAmumFjeespi9HTE0g6K+t5LmJ6KeE5YiZ77yJ44CC6K6+572u6Z2i5p2/6YeN5p6E5Li6IOiuvue9ri/ljoblj7Iv5YWz5LqOIOS4iemhteOAggp2Mi4yMSDkuJPms6ggTmljZVZvaWNlIOWUr+S4gOa4oOmBk+eahOWQiOaIkOi0qOmHj++8muaVsOWtl+aMieaVsOS9jeivu++8iDcwMDDihpLkuIPljYPvvInjgIHokKXplIDor43ov57or7vvvIg2MTjlpKfkv4PihpLlha3kuIDlhavlpKfkv4PvvInjgIHlj6Xpl7TkuI3lho3mj5LlhaXlpJrkvZnnqbrmoLzjgIHmrrXpl7TliqDlhaXoh6rnhLblgZzpob/jgIHlhpLlj7fkuI3lho3or6/liKTor7Tor53kurrjgIHlrZfluZXkuI7pn7PpopHlr7npvZDkvJjljJbjgILmraTliY0gdjIuMTkg5L+u5aSNIFRUUyA0MDDvvIjkuIrmuLjmi5Lnu53nrb7lkI3or7fmsYLvvInvvJt2Mi4yMCDkv67lpI3mi5bmi73kuIrkvKDkuI7liIbmrrXnvJbovpHvvJt2Mi4xNCDlvJXlhaUgR0xNIOmihOWkhOeQhuOAgUJlZm9yZS9BZnRlciDpooTop4jjgIFCR00g5re36Z+z44CB5Lq65aOw5b2S5LiA5YyW44CB54mH5aS054mH5bC+562J44CCdjIuMjEuMSDkuLrlvZPml6Xng63kv67vvJrkv67lpI3mnoTlu7rovazkuYnnvLrpmbflr7zoh7TnmoTliY3nq6/mraPliJnlhajpnaLlpLHmlYjkuI7orr7nva7nrYnmjInpkq7kuI3lj6/ngrnvvIzlubblkIzmraXkuKTku70gUkVBRE1FIOiHs+W9k+WJjeeKtuaAgeOAggoKIyMg5Yqf6IO954m55oCnCgotICoq5Y2V5byV5pOO5LiT5rOo77yIdjIuMjHvvIkqKu+8muS7heS/neeVmSBOaWNlVm9pY2Ug5ZSv5LiA56iz5a6a5rig6YGT44CCSW5kZXhUVFPvvIjkuIrmuLggSEYgU3BhY2Ug5bey5LiL57q/77yJ5LiOIEtpa2lWb2ljZe+8iEdlZXRlc3Qg56ev5YiG5Yi277yM5pyq5L2/55So77yJ5rig6YGT5bey5pW05L2T56e76ZmkCi0gKipOaWNlVm9pY2UqKu+8muWFjei0ueaXoOmZkOWItuivremfs+WFi+mahu+8jOaXoOmcgOeZu+W9le+8jEFQSSDku6PnkIboh6rliqjnrb7lkI3vvIhUVFMg6K+35rGC5LiN562+5ZCN55u06L2s77yMdjIuMTgg5aKe5Yqg5YWL6ZqG5ZCO6aqM6K+B77yJCi0gKirmlofmnKzkvJjlhYjlt6XkvZzmtYEqKu+8muWFiOi+k+WFpeaWh+acrO+8jOiHquWKqOajgOa1i+ivtOivneS6uu+8jOWGjeS4uuavj+S6uuWIhumFjemfs+a6kAotICoq6Z+z5rqQ566h55CGKirvvJrmlrDlu7rjgIHph43lkb3lkI3jgIHpooTop4jjgIHliKDpmaTjgIHlr7zlhaUv5a+85Ye66Z+z5rqQ77yM6Z+z5rqQ5Y+v5YWz6IGU5YWL6ZqGIElECi0gKirmlbDlrZcv56ym5Y+36aKE5aSE55CG77yIdjIuMjEg6YeN5YaZ77yJKirvvJrmraPliJkgKyDlj6/pgIkgR0xNIOWPjOWxguWFnOW6le+8jOm7mOiupOWkhOeQhu+8mgogIC0g5pWw5L2N6K+75rOV77yaMTAwMCDihpIg5LiA5Y2D44CBNzAwMCDihpIg5LiD5Y2D44CBNDk5OSDihpIg5Zub5Y2D5Lmd55m+5Lmd5Y2B5Lmd77yIdjIuMjEg6LW35LiN5YaN6YCQ5a2X6K+777yJCiAgLSDlubTku70v5bGK57qn6YCQ5a2X6K+777yaMjAyNuW5tCDihpIg5LqM6Zu25LqM5YWt5bm044CBMjAyNuWxiiDihpIg5LqM6Zu25LqM5YWt5bGKCiAgLSDokKXplIDor43ov57or7vvvJo2MTjlpKfkv4Mg4oaSIOWFreS4gOWFq+Wkp+S/g+OAgeWPjDExIOKGkiDlj4zljYHkuIDjgIHlj4wxMiDihpIg5Y+M5Y2B5LqMCiAgLSDnmb7liIbmr5QgNTAlIOKGkiDnmb7liIbkuYvkupTljYHvvJvlsI/mlbAgMS4y5LiHIOKGkiDkuIDngrnkuozkuIfvvJvCpTEwMDAg4oaSIDEwMDDlhYMKICAtIOmhv+WPty/kuablkI3lj7cv56C05oqY5Y+3L+ecgeeVpeWPtyDihpIg6YCX5Y+3562J77yb5YWo6KeS5YaS5Y+3IO+8miDihpIg6YCX5Y+377yI6Ziy5q2i6K+v5Yik6K+06K+d5Lq677yJCi0gKiror7vpn7Pmm7/mjaLop4TliJnvvIh2Mi4yMiDmlrDlop7vvIkqKu+8muWFqOmDqOaWh+acrOi9rOaNouinhOWImeWPr+inhuWMlu+8jOWGhee9ruinhOWImeWPr+WNleeLrOWBnOeUqO+8m+iHquWumuS5ieinhOWImeaUr+aMgeaWh+acrOebtOabv+OAgemAmumFjeespu+8iCogLyA/77yJ44CB5q2j5YiZ5LiOIEdMTSDor63kuYnmlLnlhpnvvIzmr4/mnaHni6znq4vlvIDlhbPvvIzorr7nva7pnaLmnb/lj6/or5Xot5HpooTop4gKLSAqKuaWreWPpei+ueeVjOS/ruWkje+8iHYyLjIy77yJKirvvJrlvJXlj7fovazlgZzpob/pmLLmi4bor43vvJvliIbmrrXkv53nlZnmjaLooYzovrnnlYzjgIHooYzlsL7ooaXlj6Xlj7fvvJvlj6XmnKvmoIfngrnlkI7ooaXljYrop5LnqbrmoLzlvLrljJblj6XlrZDovrnnlYzvvIjlhajpg6jnu4/nnJ/lrp7nlJ/miJAgKyDpnZnpn7Pmo4DmtYvpqozor4HvvIkKLSAqKuiuvue9rumdouadv+S4iemhteetvu+8iHYyLjIy77yJKirvvJrorr7nva4gLyDljoblj7IgLyDlhbPkuo7vvJtSRUFETUUg5LiO5pu05paw5pel5b+X5YaF5bWM4oCc5YWz5LqO4oCd6aG177yM5Y6G5Y+y6K6w5b2V5YaF5bWM4oCc5Y6G5Y+y4oCd6aG1Ci0gKirmrrXpl7Toh6rnhLblgZzpob/vvIh2Mi4yMSDmlrDlop7vvIkqKu+8muaLvOaOpeaXtuaPkuWFpSAxNTBtcyDpnZnpn7PvvIjlj6/pgJrov4fphY3nva4gc2VnR2FwTXMg6LCD5pW077yJ77yM5rK7IuWPpeWPpeeymOi/niIKLSAqKuWtl+W5leWvuem9kOS8mOWMlu+8iHYyLjIxIOaWsOWinu+8iSoq77ya6Leo5q616KGM5oyJ5qCH54K55pm66IO95YiH5YiG5b2S5bGe5ZCE5q6177yI5rK7IuWNiuWPpeaui+eVmSLvvInvvJvnn63lrZfluZUgMC42IOenkuacgOefreaXtumVv+WFnOW6le+8iOayuyLotLTlvpflpKrov5Ei77yJCi0gKiror7Tor53kurrmo4DmtYvmlLbntKfvvIh2Mi4yMe+8iSoq77ya5LuF5b2T5Ye6546wIOKJpTIg5Liq5LiN5ZCM5pyJ5pWI56ew5ZG85omN6L+b5YWl5aSa5Lq65qih5byP77yb57qv5pWw5a2XL+aXtumXtC/lhYPkv6Hmga/liY3nvIDvvIgi5qCH6aKY77yaIuOAgSLlpIfms6jvvJoi562J77yJ5LiN5YaN6K+v5YikCi0gKipCZWZvcmUvQWZ0ZXIg5Y+M5qCP6aKE6KeI77yIdjIuMTQg5paw5aKe77yJKirvvJrlkIjmiJDliY3lj6/nnIvliLAgR0xNIOWkhOeQhue7k+aenO+8jOW5tuWPr+aJi+WKqOe8lui+keWQjuWGjeaPkOS6pAotICoq6K+06K+d5Lq65Lqk5pu/5qCh6aqM77yIdjIuMTQg5paw5aKe77yJKirvvJrmo4DmtYvov57nu63kuKTmrrXlkIzkuIDor7Tor53kurrvvIzpq5jkuq7lkYrorablubbmj5Dkvpsi6Ieq5Yqo5Lqk5pu/IuaMiemSrgotICoqQkdNIOa3t+mfs++8iHYyLjE0IOaWsOWinu+8iSoq77ya5LiK5LygIEJHTeOAgeS6uuWjsC9CR00g5Y+M6Z+z6YeP5ouJ5p2G44CBNSDnp5LniYfmrrXlrp7ml7bor5XlkKzjgIFzaWRlY2hhaW4gZHVja2luZ++8iOS6uuWjsOautSBCR00g6Ieq5Yqo6ZmNIDZkQu+8ieOAgemFjee9ruWPr+S/neWtmC/lr7zlhaUv5a+85Ye6Ci0gKirniYflpLTniYflsL7mi7zmjqXvvIh2Mi4xNCDmlrDlop7vvIkqKu+8muWPguiAgyBwb2RtZXJnZS5odG1sIOWunueOsO+8jOaUr+aMgea3oeWFpea3oeWHui/nm7TmjqXmi7zmjqUKLSAqKuS6uuWjsOmfs+mHj+W9kuS4gOWMlu+8iHYyLjE0IOaWsOWinu+8iSoq77yacGVhayBub3JtYWxpemUg5YiwIC0zZELvvJvmjInor7Tor53kurogUk1TIOWIhue7hOaLieW5s++8m+WPr+mAieWls+WjsOi9u+mHj+WOi+e8qQotICoq5qCH6aKYL1Nob3dub3Rlcy9UYWdzIOeUn+aIkO+8iHYyLjE0IOaWsOWinu+8iSoq77ya5ZCI5oiQ5a6M5oiQ5ZCO6LCD55SoIEdMTSDoh6rliqjnlJ/miJDmkq3lrqLlhYPmlbDmja4KLSAqKumVv+aWh+acrOWIhuautSoq77yaTmljZVZvaWNlIDE1MCDlrZcv5q6177yI5pm66IO95ZCI5bm255+t5Y+l77ybdjIuMjEg6LW35Y+l6Ze05peg56m65qC85ou85o6l77yJCi0gKirmjaLooYzkv53nlZkqKu+8muWOn+Wni+aNouihjOeUqOS6juWtl+W5leWIhuihjAotICoqV29yZCDmlofmoaPlr7zlhaUqKu+8muaUr+aMgeaLluaLveaIluS4iuS8oCAuZG9jeCDmlofku7YKLSAqKlNSVCDlrZfluZUqKu+8muaMieaXtumXtOavlOS+i+WIhumFjeWtl+W5le+8jOWkmuS6uuaooeW8j+iHquWKqOagh+azqOivtOivneS6ugotICoq5Ymq5pig5bel56iL5a+85Ye6KirvvJrnlJ/miJDlj6/nm7TmjqXlr7zlhaXliarmmKDnmoTlt6XnqIsgWklQCi0gKirnlJ/miJDljoblj7IqKu+8muiHquWKqOS/neWtmOeUn+aIkOiusOW9le+8jOagh+azqOS9v+eUqOW8leaTjgotICoq6YWN572u5a+85YWlL+WvvOWHuioq77ya5aSH5Lu95ZKM5oGi5aSN5omA5pyJ6K6+572u5ZKM6Z+z5rqQCi0gKirorr7nva7lj5jmm7QgdG9hc3TvvIh2Mi4xNCDmlrDlop7vvIkqKu+8muS7u+S9leiuvue9rumhueWPmOabtOWNs+aXtuaPkOekuiLorr7nva7lt7Lkv53lrZgi77yM5LiN6YGu5oyh5Yqf6IO95Yy6CgojIyDkvb/nlKjmlrnms5UKCjEuIOi+k+WFpeaIluWvvOWFpeimgeWQiOaIkOeahOaWh+acrO+8iOW8leaTjuW3suWbuuWumuS4uiBOaWNlVm9pY2XvvIkKMi4g5Zyo6K+06K+d5Lq65YiG6YWN5Y2h54mH5Lit5Li65q+P5L2N6K+06K+d5Lq66YCJ5oup5oiW5paw5bu66Z+z5rqQCjMuIOeCueWHuyLpooTop4jlpITnkIYi5p+l55yL6L2s5o2i5YmN5ZCO55qE5paH5pys77yM5Y+v5omL5Yqo57yW6L6RIEFmdGVyIOaWh+acrO+8iOe8lui+keWGheWuueWQjOagt+S8muWBmuivu+mfs+mihOWkhOeQhu+8iQo0LiDngrnlh7si5byA5aeL5ZCI5oiQIu+8jOetieW+heeUn+aIkOWujOaIkAo1LiDvvIjlj6/pgInvvInlnKjnu5PmnpzljLrngrnlh7si55Sf5oiQ5qCH6aKYL+aRmOimgS/moIfnrb4iCjYuIOS4i+i9vSBXQVYg6Z+z6aKR77yI5ZCrL+S4jeWQqyBCR00g5Lik5Liq54mI5pys77yJ44CBU1JUIOWtl+W5leaIluWJquaYoOW3peeoiwoKIyMg5ZCI5oiQ5rig6YGT6K+05piOCgotIOW9k+WJjeS7heaPkOS+myBOaWNlVm9pY2Ug5LiA5Liq5rig6YGT77ya5YWN6LS55peg6ZmQ44CB5peg6ZyA55m75b2V44CBMTUwIOWtly/mrrXjgIHmrrXpl7QgMTYg56eS6ZmQ5rWB77yI5LiK5ri4IEFQSSDpmZDliLbvvIkKLSDplb/mlofmnKzmjInmrrXkuLLooYznlJ/miJDvvIzlj5fpmZDmtYHlvbHlk43mgLvogJfml7bkuI7mrrXmlbDmiJDmraPmr5TvvIzor7flj4LogIPov5vluqbmnaHogJDlv4PnrYnlvoUKLSDmm77nu4/nmoQgSW5kZXhUVFMgLyBLaWtpVm9pY2Ug5rig6YGT5Zug5LiK5ri45LiN5Y+v55So5oiW5pyq6KKr5L2/55So77yM5bey5ZyoIHYyLjIxIOaVtOS9k+enu+mZpAoKIyMg5YWz5LqO5Y+C6ICD6Z+z6aKRCgrlj4LogIPpn7PpopHnmoTotKjph4/nm7TmjqXlvbHlk43lhYvpmobmlYjmnpzjgILlu7rorq7vvJoKCi0g5pe26ZW/IDUtMTUg56eS77yM5riF5pmw5peg5Zmq6Z+zCi0g6YG/5YWN6IOM5pmv6Z+z5LmQ5oiW5aSa5Lq66K+06K+dCi0g5Y+v5Lul5L+d5a2Y5aSa5Liq6Z+z5rqQ5bm26ZqP5pe25YiH5o2iCi0g5aaC6ZyA5Y+Y6YCf5pWI5p6c77yM6K+36aKE5YWI5aSE55CG5Y+C6ICD6Z+z6aKR77yM5pys5bel5YW35LiN5YGa5Y+Y6YCfCgojIyDlhbPkuo7liarmmKDlt6XnqIsKCuWvvOWHuueahCBaSVAg6Kej5Y6L5ZCO5YyF5ZCr5Lul6aG555uu5ZCN5ZG95ZCN55qE5paH5Lu25aS577yM5YaF5ZCrIGRyYWZ0X2NvbnRlbnQuanNvbuOAgWRyYWZ0X21ldGFfaW5mby5qc29u44CBYXVkaW9fbWFpbi53YXYg5ZKMIGF1ZGlvX21haW4uc3J044CC5bCG5paH5Lu25aS55aSN5Yi25Yiw5Ymq5pig6I2J56i/55uu5b2VIGNvbS5sdmVkaXRvci5kcmFmdCDkuIvljbPlj6/miZPlvIDjgILnlLvluIPmr5TkvovvvJo5OjE277yM5a2X5bmV5L2/55So5oCd5rqQ6buR5L2T77yI55m95a2X6buR6L6577yM5a2X5Y+3IDEw77yJ77yM5L2N5LqO55S76Z2i5LiL5pa544CC6Z+z6aKR5Li65a6M5pW05Y2V5q615paH5Lu244CCCgojIyDlhbPkuo4gQkdNIOa3t+mfs++8iHYyLjE0IOaWsOWinu+8iQoKLSBCR00g6buY6K6k6Z+z6YePIC0xOGRC77yI57qmIDAuMTI2IOWinuebiu+8ie+8jOWPr+WcqOiuvue9ruS4reiwg+iKggotIOS6uuWjsOauteW8gOWni+aXtiBCR00g6Ieq5YqoIGR1Y2tpbmcg6IezIC0yNGRC77yI5YaN6ZmNIDZkQu+8ie+8jOS6uuWjsOe7k+adnyAwLjMg56eS5ZCO5oGi5aSNCi0gZHVja2luZyDnrpfms5Xkvb/nlKggT2ZmbGluZUF1ZGlvQ29udGV4dCArIEdhaW5Ob2RlIOiHquWKqOWMluabsue6v++8jOWPguiAgyBwb2RtZXJnZS5odG1sIOeahCBzaWRlY2hhaW4g5a6e546wCi0g6L6T5Ye65YyF5ZCrIEJHTSDnmoTmnIDnu4jmt7fpn7MgV0FW77yM5ZCM5pe25L+d55WZ57qv5Lq65aOwIFdBViDkvZzkuLrlpIfku70KCiMjIOWFs+S6jumfs+mHj+W9kuS4gOWMlu+8iHYyLjE0IOaWsOWinu+8iQoKLSAqKnBlYWsgbm9ybWFsaXplKirvvJrmiYDmnInmrrXlvZLkuIDliLAgLTNkQu+8iOWPr+mFjee9riAtNiB+IDBkQu+8iQotICoq6K+06K+d5Lq6IFJNUyDmi4nlubMqKu+8muaMieivtOivneS6uuWIhue7hOiuoeeulyBSTVPvvIzoh6rliqjlop7nm4rorqnmiYDmnInor7Tor53kurrlk43luqbkuIDoh7TvvIjor6/lt64gwrExZELvvIkKLSAqKuWls+WjsOi9u+mHj+WOi+e8qe+8iOWPr+mAie+8iSoq77ya6ZiI5YC8IC0yMGRC44CB5q+U5L6LIDI6MeOAgeaUu+WHuyA1bXPjgIHph4rmlL4gNTBtc++8jOayu+Wls+WjsOW/veWkp+W/veWwjwoKIyMg5pu05paw5pel5b+XCgojIyMgdjIuMjIuMiAoMjAyNi0wOS0zMCkKCi0g5L+u5aSN77ya54K55Ye7Iuiuvue9riLlj6rlh7rnjrDljYrpgI/mmI7pga7nvanjgIHpnaLmnb/kuI3mmL7npLrigJTigJR2Mi4yMi4xIOWwhumdouadv+makOiXj+aWueW8j+aUueS4uiB0cmFuc2Zvcm0g5L2N56e777yM5L2G5bGV5byA54q25oCB5ryP5YaZIHRyYW5zZm9ybSDlpI3kvY3vvIzpnaLmnb/lp4vnu4jlgZzlnKjlsY/luZXlpJbvvJvlt7LooaXkuIrvvIzmgaLlpI3mu5HlhaXliqjnlLsKLSDkv67lpI3vvJrorr7nva7mjInpkq7lm77moIfnlLvmiJDkuoYi5aSq6ZizIu+8iOWchueCuSvmlL7lsITnur/vvInvvIzlt7LmlLnkuLrmoIflh4bpvb/ova7nur/mnaHlm77moIfvvIhzcHJpdGUg5Y2V5aSE5a6a5LmJ77yM5omA5pyJ5byV55So5aSE5LiA5bm255Sf5pWI77yJCi0g6K+05piO77ya5paH5a2XL+mAmumFjS/mraPliJnnsbvop4TliJnkuLrmnKzlnLDlpITnkIbvvIzml6DpnIAgR0xNIEtleSDljbPnlJ/mlYjvvJvku4UiR0xNIOivreS5iSLnsbvop4TliJnpnIDopoEgS2V577yM5pyq6YWN572u5pe25YiX6KGo5Lya5qCH5rOoIuacqueUn+aViCIKCiMjIyB2Mi4yMi4x77yIMjAyNi0wOS0zMO+8iQoKKirop4TliJnns7vnu5/nu5/kuIAgKyDnlYzpnaLnu4boioLkv67lpI3vvIjnlKjmiLflj43ppojpqbHliqjvvIkqKgoKLSDkv67lpI0i5YWz5LqOIumhtemmluihjOaYvuekuiB2JHtWRVJTSU9OfSDlrZfpnaLph4/nmoTpl67popjvvJrpg6jnvbLml7bmqKHmnb/mj5LlgLzor6/kvKTkuoYgUkVBRE1FIOa4suafk+WHveaVsOeahCByZXBsYWNlIOaQnOe0ouS4su+8jOWvvOiHtOeJiOacrOWPt+awuOi/nOabv+aNouS4jeS4iuWOuwotIOivu+mfs+inhOWImee7k+aehOe7n+S4gO+8muWGhee9ruS4juiHquWumuS5ieinhOWImeWdh+S4uiLop4TliJnlkI3np7AgKyDljLnphY3lhoXlrrkg4oaSIOabv+aNouWGheWuuSArIOexu+WeiyArIOWQr+eUqOW8gOWFsyLvvJvngrnlh7vku7vmhI/op4TliJnnmoTlkI3np7DmiJblhoXlrrnljbPlj6/lsLHlnLDnvJbovpHvvIznhKbngrnnp7vlvIDoh6rliqjkv53lrZjvvIhFbnRlciDkv53lrZjjgIFFc2Mg5Y+W5raI77yJ77yb5YaF572u6KeE5YiZ5ZCM5qC35Y+v57yW6L6RCi0g5YaF572u6KeE5YiZ5pWw5o2u5YyW77ya5byV5Y+36L2s5YGc6aG/44CB5YaS5Y+36L2s6YCX5Y+344CB5Y+l5pyr56m65qC85LiJ5p2h6KeE5YiZ5byA5pS+IuWMuemFjS/mm7/mjaIi57yW6L6R77yM5pS55a6M56uL5Y2z55Sf5pWI77yb5YW25L2Z6KGM5Li65Z6L6KeE5YiZ5Y+v5pS55ZCN56ew5LiO6K+05piOCi0g5paw5aKeIuWkjeWOn+m7mOiupCLmjInpkq7kuIDplK7mgaLlpI3lhoXnva7op4TliJnlh7rljoLorr7nva7vvJvmlrDlop7op4TliJnlr7zlhaUv5a+85Ye677yISlNPTu+8jOS9jeS6juinhOWImeWMuuW6lemDqO+8iQotIOaWsOWinuiHquWumuS5ieinhOWImeaXtuWinuWKoCLop4TliJnlkI3np7Ai6L6T5YWl5qGG77yM5LiO5YaF572u6KeE5YiZ5a2X5q615a+56b2QCi0gR0xNIOivreS5ieinhOWImeeKtuaAgemAj+aYjuWMlu+8muacqumFjee9riBLZXkg5oiW5pm66IO96aKE5aSE55CG5YWz6Zet5pe277yM5Zyo5YiX6KGo5Lit5qCH5rOoIuacqueUn+aViCLvvIjmlofmnKwv6YCa6YWNL+ato+WImeinhOWImeS4uuacrOWcsOinhOWIme+8jOacrOWwseaXoOmcgCBHTE0gS2V577yJCi0g56e76ZmkIuivlei3kemihOWkhOeQhiLmjInpkq7vvIjkuI7kuLvpnaLmnb8gQmVmb3JlL0FmdGVyIOmihOiniOWKn+iDvemHjeWkje+8iQotIOiuvue9rumdouadv++8muagh+mimOS4jumhteetvuWbnuW9kuaZrumAmuaWh+aho+a1ge+8iOS4jeWGjeaCrOa1ru+8ie+8m+mdouadv+W6lemDqOaWsOWiniLlhbPpl63pnaLmnb8i5oyJ6ZKu77yM5rua5Yqo5ZCO5peg6ZyA5Zue5Yiw6aG26YOo5Y2z5Y+v5YWz6Zet77yb5ruR5Ye65Yqo55S75pS555SoIHRyYW5zZm9ybe+8jOinhOmBv+mDqOWIhiBXZWJWaWV377yI5b6u5L+h5YaF572u5rWP6KeI5Zmo77yJZml4ZWQg5riy5p+T6ZSZ5L2NCi0g5YWo6YOoIGVtb2ppIOWbvuagh+abv+aNouS4uuWNleiJsiBTVkcg57q/5p2h5Zu+5qCH77ya57uf5LiA5Zyo6aG16Z2i5YaFIHNwcml0ZSDlrprkuYnvvIhzeW1ib2wrdXNl77yJ77yM5LiA5aSE5a6a5LmJ44CB5aSE5aSE5byV55SoCgojIyMgdjIuMjIgKDIwMjYtMDktMzApCgoqKuaWreWPpei+ueeVjOezu+e7n+WMluS/ruWkjSArIOeUqOaIt+iHquWumuS5ieivu+mfs+inhOWImSArIOiuvue9rumdouadv+mHjeaehCoqCi0g5L+u5aSN5byV5Y+35pat5Y+l6ZSZ6K+v77ya5Lit5paH5byV5Y+34oCc4oCm4oCd5Zyo5LiK5ri45byV5pOO5Lit6KKr6Z2Z6buY5b+955Wl77yM6L6555WM5raI5aSx5a+86Ie05byV5Y+35YaF6K+N6K+t6KKr5ouG6K+777yI4oCc5LqG5LiN6LW355qE6ICB56WW5a6X4oCd4oaS4oCc5LqGIOS4jei1t+KAne+8ie+8m+W8leWPt+eOsOi9rOS4uumAl+WPt+WBnOmhv++8iOe6v+S4iuWunua1i+WBnOmhv+S9jee9ruato+ehru+8iQotIOS/ruWkjeaNouihjOWPpeeVjOS4ouWkse+8muWkmuihjOaWh+ahiOWIhuauteWQiOW5tuaXtuaNouihjOS/oeaBr+iiq+S4ouW8g++8jOaXoOagh+eCueihjOmmluWwvuebuOi/nuaIkOaVtOS4su+8m+Wunua1i+S4iua4uOWvueijuOi/nueahOS4reaWh+WPpeWPt+WHoOS5jumbtuWBnOmhv+WTjeW6lO+8iOaooeWei+maj+acuuaWreWPpe+8ieOAgueOsOWIhuauteS/neeVmeaNouihjOi+ueeVjOOAgeihjOWwvuiHquWKqOihpeWPpeWPt+OAgeWPpeacq+agh+eCueWQjuihpeWNiuinkuepuuagvO+8jOS4iemHjei+ueeVjOS/oeWPt+WFqOmDqOe7j+e6v+S4iuWunua1i+mqjOivge+8iOWBnOmhv+eyvuehruiQveWcqOagh+eCueWkhO+8iQotIOi/nue7reagh+eCuea4heeQhu+8mui9rOaNouaui+eVmeeahOKAnO+8jOOAguKAneKAnO+8jO+8jOKAneiHquWKqOWOu+mHje+8jOWPpeWwvuW8seagh+eCueWNh+e6p+WPpeWPtwotICoq6K+76Z+z5pu/5o2i6KeE5YiZ57O757ufKirvvJrlhoXnva7op4TliJnvvIjlvJXlj7cv5ZOB54mM6K+NL+aVsOWtly/nrKblj7cv5YaS5Y+3L+agh+eCuea4heeQhi/lj6XmnKvnqbrmoLzvvInlnKjorr7nva7pnaLmnb/lhajpg6jlj6/op4HvvIzlj6/ljZXni6zlgZznlKjvvJvnlKjmiLflj6/oh6rlrprkuYnop4TliJnvvIzmlK/mjIHmlofmnKznm7Tmm7/jgIHpgJrphY3nrKbvvIgqIOS7u+aEj+S4suOAgT8g5Y2V5a2X77yJ44CB5q2j5YiZ44CBR0xNIOivreS5ieaUueWGmeWbm+enjeaWueW8j++8jOavj+adoeinhOWImeeLrOeri+W8gOWFs++8jOW5tuWPr+KAnOivlei3kemihOWkhOeQhuKAneWNs+aXtumihOiniAotICoq6K6+572u6Z2i5p2/6YeN5p6EKirvvJrmlLnkuLog6K6+572uIC8g5Y6G5Y+yIC8g5YWz5LqOIOS4ieS4quagh+etvumhteOAglJFQURNRSDkuI7mm7TmlrDml6Xlv5fnp7vlhaXigJzlhbPkuo7igJ3pobXvvIjkuI3lho3lvLnnqpfvvInvvJvnlJ/miJDljoblj7Lnp7vlhaXigJzljoblj7LigJ3pobXvvIjpobbmoI/mjInpkq7np7vpmaTvvInvvJvorr7nva7pobnmjIkg5ZCI5oiQ5Y+C5pWwIOKGkiDpn7PmupAg4oaSIOaWh+acrOWkhOeQhiDihpIg6Z+z6aKR5ZCO5aSE55CGIOKGkiDljoblj7LkuI7mlbDmja4g6YeN5o6SCi0g6aG25qCP5riF55CG77ya56e76Zmk5Y2V5byV5pOO5q6L55WZ55qE5rig6YGT5YiH5o2i5oyJ6ZKu5LiO5Y6G5Y+y5oyJ6ZKu77yM6aG25qCP5LuF5L+d55WZ6K6+572u5YWl5Y+jCi0g6ZmE77ya6K+76Z+z6L6555WM6aqM6K+B5pa55rOV77yI55yf5a6e55Sf5oiQICsgQVNSIOi9rOWGmSArIOmdmemfs+ajgOa1i+WumuS9jeWBnOmhv++8ieayiea3gOS4uuWPr+WkjeeUqOa1i+ivlemTvui3rwoKIyMjIHYyLjIxLjEgKDIwMjYtMDktMjkg5b2T5pel54Ot5L+uKQoKKirkv67lpI3vvIh2Mi4yMS4wIOWPkeW4g+aVsOWwj+aXtuWQjueUqOaIt+aKpeWRiu+8muWPs+S4iuinkuiuvue9ri/ljoblj7LnrYnmjInpkq7lhajpg6jkuI3lj6/ngrnvvIkqKgotIOagueWboO+8mnYyLjIxIOaehOW7uuaKiuWJjeerr+S7o+eggeW1jOWFpSB3b3JrZXIg5qih5p2/5a2X6Z2i6YeP5pe277yM5q2j5YiZ6YeM55qE5Y+N5pac5p2g5bCR5YaZ5LiA5bGC77yM5rWP6KeI5Zmo56uv5YWxIDE2IOWkhOato+WImeaNn+WdjwotIOiHtOWRveS4gOWkhO+8muespuWPtyArIOi9rOivu+azleeahOato+WImeaNn+Wdj+S4uumdnuazleato+WImSAvKy9n77yM5pW05Liq5YmN56uv6ISa5pys6Kej5p6Q5aSx6LSl77yM6K6+572uL+WOhuWPsi/lvJXmk47liIfmjaIvUkVBRE1FIOetieWFqOmDqOaMiemSruWkseaViO+8iOaOp+WItuWPsOaKpSB0b2dnbGVTZXR0aW5ncy9vcGVuSGlzdG9yeS9zd2l0Y2hFbmdpbmUgaXMgbm90IGRlZmluZWTvvIkKLSDlhbbkvZkgMTUg5aSE6Z2Z6buY5aSx5pWI77ya5pWw5a2X5pWw5L2N44CB5pel5pyf44CB5LiHL+S6v+OAgeeZvuWIhuWPt+OAgei0p+W4geOAgeaJi+acuuWPt+etieivu+mfs+ato+WImeWFqOmDqOWkseeBte+8m+WFtuS4reerlue6v+i9rOmAl+WPt+S4juecgeeVpeWPt+i9rCLnrYnnrYki5Lik5p2h5o2f5Z2P5ZCO5LuN5piv5ZCI5rOV5q2j5YiZ77yM5LiA5pem6ISa5pys5Y+v6Kej5p6Q5bCx5Lya5Zyo6L+Q6KGM5pe25aSn6Z2i56ev6K+v5pu/5o2i77yI5q+P5Liq5a2X56ym6Ze05o+S6YCX5Y+3IC8g5Lu75oSPIDMg5a2X5Lul5LiK5pu/5o2i5Li6IuetieetiSLvvIkKLSDkv67lpI3mlrnlvI/vvJrku6XmtY/op4jlmajlrp7pmYXmlLbliLDnmoTpobXpnaLkuLrln7rlh4bpgJDlpITov5jljp/mraPliJnvvIzlho3mjIki5qih5p2/5a2X6Z2i6YeP5YaF5Y+N5pac5p2g5Y+M5YaZIuinhOWImemHjeaWsOW1jOWFpe+8m+WPkeeJiOWJjeaWsOWinuS4pOmBk+agoemqjO+8muaooeadvyBjb29rZWQg6L6T5Ye65LiO5pyf5pyb6aG16Z2i6YCQ5a2X6IqC5q+U5a+5ICsgMzYg6aG56K+76Z+zL+WIhuautS/or7Tor53kurrlm57lvZLmtYvor5Xlhajpg6jot5HlnKjnnJ/lrp7kuIvlj5HohJrmnKzkuIrvvIjml6fmtYvor5Xot5HlnKjmnKogY29va2VkIOeahOaWh+acrOS4iu+8jOaYr+acrOasoea8j+a1i+eahOagueWboO+8iQotIOmZhOW4puS/ruWkje+8muW6lOeUqOWGhSBSRUFETUUg5by556qX5q2k5YmN5LiA55u05pi+56S6IHYyLjE3IOaXp+WGheWuue+8iHYyLjIxIOaehOW7uuWPquabtOaWsOS6hiB3b3JrZXIg6aG26YOo55qE5q275Luj56CB5Ymv5pys77yM5ryP5pu05paw5YmN56uvIGJhc2U2NCDlia/mnKzvvInvvJvmnKzniYjotbfkuKTku70gUkVBRE1FIOWQjOatpeS4uuWQjOS4gOWGheWuuQoKIyMjIHYyLjIxLjAgKDIwMjYtMDktMjkpCgoqKua4oOmBk+a4heeQhioqCi0g56e76ZmkIEluZGV4VFRTIOa4oOmBk++8muS4iua4uCBrb3p6enEtaW5kZXh0dHMyYXBpLmhmLnNwYWNlIOW3suS4i+e6v++8iDIwMjYtMDktMjkg5a6e5rWL6LaF5pe277yJCi0g56e76ZmkIEtpa2lWb2ljZSDmuKDpgZPvvJpHZWV0ZXN0IOenr+WIhuWItuOAgeacquiiq+S9v+eUqO+8m+i/nuWQjCBDRiDpqozor4HpnaLmnb/kuI7lhajpg6jku6PnkIbnq6/ngrnkuIDlubbnp7vpmaQKLSDlvJXmk47pgInmi6nlmajnroDljJbvvJpOaWNlVm9pY2Ug5oiQ5Li65ZSv5LiA5byV5pOO77yM6K6+572u6aG15byV5pOO5YiG57uE56e76ZmkCgoqKuS/ruWkje+8iOWuouaIt+WPjemmiOeahOWbm+Wkp+mXrumimO+8jOi+k+WFpeWxgiBoYXJuZXNz77yM5LiN5pS56L+c56uv5qih5Z6L77yJKioKLSDmlbDlrZfor7vms5XvvJo0IOS9jeaVsOS7peS4iuaMieaVsOS9jeivu++8iDcwMDDihpLkuIPljYPjgIExMDAw4oaS5LiA5Y2D44CBNDk5OeKGkuWbm+WNg+S5neeZvuS5neWNgeS5ne+8ie+8jOatpOWJjeS4gOW+i+mAkOWtl+ivu++8m+W5tOS7vS/lsYrnuqfkv53nlZnpgJDlrZfor7sKLSDokKXplIDor43vvJo2MTjlpKfkv4PihpLlha3kuIDlhavlpKfkv4PjgIHlj4wxMeKGkuWPjOWNgeS4gOOAgeWPjDEy4oaS5Y+M5Y2B5LqM77yI5LiK5LiL5paH6ZSa5a6a77yM6YG/5YWNIuS7t+agvDYxOOWFgyLor6/kvKTvvIkKLSDmlq3lj6XvvJrliIbmrrXlkIjlubbkuI3lho3mj5LlhaUgQVNDSUkg56m65qC877yI5Lit5paHIFRUUyDkvJrmiornqbrmoLzor7vmiJDor6HlvILlgZzpob/vvIkKLSDmrrXpl7Tnspjov57vvJrmi7zmjqXml7bmj5LlhaUgMTUwbXMg6Z2Z6Z+z77yI6buY6K6k77yM5Y+v6YWNIHNlZ0dhcE1z77yJCi0g5YaS5Y+36K+v5Yik6K+06K+d5Lq677ya6ZyAIOKJpTIg5Liq5LiN5ZCM5pyJ5pWI56ew5ZG85omN6L+b5aSa5Lq65qih5byP77ybIuagh+mimO+8mi/lpIfms6jvvJovMTI6MzAi562J5LiN5YaN6K+v5Yik77ybVFRTIOaWh+acrOS4reWFqOinkuWGkuWPt+i9rOmAl+WPtwotIOe8lui+keaXgei3r++8muaJi+WKqOe8lui+kei/h+eahOWIhuaute+8iOmihOiniCBBZnRlciDmlofmnKzvvInmraTliY3lrozlhajnu5Xov4for7vpn7PpooTlpITnkIbvvIznjrDlt7Lnu5/kuIDlhZzlupUKLSDlrZfluZXvvJrot6jmrrXooYzmjInmoIfngrnliIfliIblvZLlsZ7lkITmrrXvvIjmsrsi5LuOJ+eahCflvIDlp4vljYrlj6XlnKjlsY/luZXkuIoi77yJ77yb55+t5a2X5bmVIDAuNnMg5pyA55+t5pe26ZW/77yI5rK7Iui0tOW+l+eJueWIq+i/kSLvvIkKLSBHTE0g6buY6K6k5o+Q56S66K+N5ZCM5q2l5pu05paw77yI5pWw5L2N6K+75rOVL+iQpemUgOivjS/lhajop5LlhpLlj7fop4TliJnvvIkKCiMjIyB2Mi4yMC4yICgyMDI2LTA5LTI5KQoKKirmlofmoaPkv67mraPvvIjooYzkuLrkuI4gdjIuMjAuMSDlrozlhajkuIDoh7TvvIkqKgotIOa6kOaWh+S7tumAmui/hyBDbG91ZGZsYXJlIEFQSSDku47nlJ/kuqfnjq/looPlrozmlbTlj5blm57vvIznu5PmnZ8i5Zyo57q/54Ot5pu05paw5peg5a2Y5qGjIueKtuaAgQotIOS/ruato+aWh+S7tuWktOazqOmHiu+8iOatpOWJjeWBnOeVmeWcqCB2Mi4xOe+8ieOAgeihpeiusCB2Mi4xNX52Mi4yMC4xIOe8uuWkseeahCBjaGFuZ2Vsb2cKLSDlhoXltYwgUkVBRE1FIOeUqOazleWvuem9kOW9k+WJjeeJiOacrAoKIyMjIHYyLjIwLjEgKDIwMjYtMDgtMDQpCgotIOW4uOinhOWwj+S/ruS4jueJiOacrOmAkui/m++8iOeDreabtOaWsO+8jOacqueVmeWPmOabtOiusOW9le+8iQoKIyMjIHYyLjIwLjAgKDIwMjYtMDgtMDQpCgoqKuaWsOWinioqCi0g6K+06K+d5Lq65Lqk5pu/6K2m5ZGK5paw5aKeIuW/veeVpSLmjInpkq7vvIjkuIDmrKHmgKcgZGlzbWlzc++8jOmHjeaWsOeUn+aIkOaXtuiHquWKqOmHjee9ru+8iQoKKirkv67lpI0qKgotIOS/ruWkjeaLluaLveS4iuS8oO+8mumYu+atoua1j+iniOWZqOm7mOiupOaJk+W8gOaWh+S7tueahOihjOS4uu+8iGluaXRVcGxvYWRab25lRHJhZ0Ryb3DvvInvvIzpn7PpopHmlofku7blj6/mraPnoa7okL3lhaXkuIrkvKDljLoKLSDkv67lpI3liIbmrrXnvJbovpHngrnlh7vkuKLlpLHvvJrnvJbovpHljZXlhYPmoLzooqvlraTlhL/ljJbml7boh6rliqjph43muLLmn5PliIbmrrXooagKLSDkv67lpI3nvJbovpHmoYYgYmx1ciDnq57mgIHvvJrnlKggcmVxdWVzdEFuaW1hdGlvbkZyYW1lIOW7tui/n+aPkOS6pO+8jOmBv+WFjeS4jueCueWHu+S6i+S7tuWGsueqgQotIOmfs+a6kOS4i+aLieS4jeWGjeemgeeUqOW3suiiq+WNoOeUqOeahOmfs+a6kO+8jOaUueS4uuaYvuekuuWNoOeUqOiAheW5tuWFgeiuuOaUuemAiQoKIyMjIHYyLjE4LjAgKDIwMjYtMDYtMTgg5ZCO54Ot5pu05pawKQoKKirkv67lpI0qKgotIE5WIOWFi+mahuS4iuS8oCBDb250ZW50LVR5cGUg5L+u5q2j77yaYXVkaW8vd2F2IOKGkiBhdWRpby9tcGVn77yI5Yy56YWN5a6e6ZmFIE1QMyDmlofku7bvvIkKCioq5paw5aKeKioKLSDlhYvpmoblkI7oh6rliqjpqozor4HvvJrnlKjlhYvpmobpn7PoibLlj5HpgIHmtYvor5UgVFRTIOivt+axgu+8jOehruiupOmfs+iJsuecn+ato+WPr+eUqO+8iOWQqyAxNnMg6ZmQ5rWB6YeN6K+V77yJCi0g5YWL6ZqG5oiQ5Yqf5L2GIFRUUyDkuI3lj6/nlKjml7bvvIznu5nlh7rmmI7noa7nmoTkuIrmuLjmlYXpmpzmj5DnpLoKCiMjIyB2Mi4xNSB+IHYyLjE3ICgyMDI2LTA2KQoKLSB2Mi4xN++8iDIwMjYtMDYtMTgg6YOo572y77yJ77ya5L+u5aSN55Sf5oiQ5a6M5oiQ5ZCO5YiG5q6157yW6L6R5LiN5Y+v54K55Ye777yIaXNHZW5lcmF0aW5nIOe9riBmYWxzZSDlkI7mnKrph43muLLmn5PliIbmrrXooajvvIkKCiMjIyB2Mi4xOS4wICgyMDI2LTA3LTI0KQoKKirkv67lpI0qKgotIOS/ruWkjSBOaWNlVm9pY2UgVFRTIOWni+e7iOi/lOWbniA0MDAg55qE5qC55pys5Y6f5Zug77ya5LiK5ri4IC9jbG9uZS90dHMg56uv54K55ouS57udIEhNQUMg562+5ZCN6K+35rGCCi0gVFRTIOWSjCBnZXRJdGVtQnlUYXNrU24g5Lik5Liq56uv54K55pS55Li65LiN562+5ZCN5Luj55CG77yM5YW25L2Z5YWL6ZqG566h55CG56uv54K577yIZ2V0VXBsb2FkVXJsL3NhdmVSZWZBdWRpbzIvZ2V0U3luY1JlZlN0YXR1c++8ieS/neaMgeetvuWQjQoKKirosIPmn6Xlj5HnjrAqKgotIOS4iua4uCBOaWNlVm9pY2Ug5bey5bCG5a2Y5YKo5LuOIENPUyDov4Hnp7voh7MgUjLvvIzorq3nu4PlkI7nq6/lkIzmraXmnInnuqYgMjAg56eS5bu26L+f77yIQ09TIOmUmeivr+S4uueerOaAge+8jOi9ruivouS8muiHquWKqOaBouWkje+8iQotIOS4iua4uOe9keermeiHqui6q+WvuSBUVFMg6K+35rGC5LiN5L2/55SoIEhNQUMg562+5ZCNCi0g5Lu75Yqh54q25oCB5p+l6K+i56uv54K55Li6IGdldEl0ZW1CeVRhc2tTbu+8iOmdniBnZXRUYXNrU3RhdHVz77yM5ZCO6ICF5beyIDQwNO+8iQoKIyMjIHYyLjE0LjAgKDIwMjYtMDYtMTcpCgoqKuaWsOWinioqCi0gR0xNIOezu+e7n+aPkOekuuivjeWPr+WcqOiuvue9ruS4ree8lui+keOAgeS/neWtmOWIsCBsb2NhbFN0b3JhZ2XjgIHpmo/phY3nva7lr7zlhaXlr7zlh7oKLSDpu5jorqTns7vnu5/mj5DnpLror43mlrDlop7op4TliJnvvJrpob/lj7cv5Lmm5ZCN5Y+3L+egtOaKmOWPt+e7n+S4gOi9rOmAl+WPt++8m+Wwj+aVsOeCueivuyLngrki5rGJ5a2X77yb5bm05Lu9L+aXpeacny/ph5Hpop0v55m+5YiG5q+U55qE5Lit5paH6K+75rOVCi0gQmVmb3JlL0FmdGVyIOWPjOagj+mihOiniOmdouadv++8muWQiOaIkOWJjeWPr+eci+WIsCBHTE0g5aSE55CG5YmN5ZCO5a+55q+U77yMQWZ0ZXIg5paH5pys5qGG5Y+v5omL5Yqo57yW6L6R6KaG55uWCi0g6K+06K+d5Lq65Lqk5pu/5qCh6aqM77ya5omr5o+P5YiG5q6157uT5p6c5qOA5rWL6L+e57ut5Lik5q615ZCM5LiA6K+06K+d5Lq677yM6auY5Lqu5ZGK6K2mICsgIuiHquWKqOS6pOabvyLmjInpkq4KLSBCR00g6ZuG5oiQ77ya5LiK5LygL+mAieaLqeOAgeWPjOmfs+mHj+aLieadhuOAgTUg56eS54mH5q615a6e5pe26K+V5ZCs44CBc2lkZWNoYWluIGR1Y2tpbmfjgIHphY3nva7lj6/kv53lrZgv5a+85YWlL+WvvOWHugotIOeJh+WktOeJh+WwvuaLvOaOpe+8muWPguiAgyBwb2RtZXJnZS5odG1sIOWunueOsO+8jOaUr+aMgea3oeWFpea3oeWHui/nm7TmjqXmi7zmjqXkuKTnp43mqKHlvI8KLSDkurrlo7Dpn7Pph4/lvZLkuIDljJbvvJpwZWFrIG5vcm1hbGl6ZSArIOivtOivneS6uiBSTVMg5ouJ5bmzICsg5Y+v6YCJ5aWz5aOw6L276YeP5Y6L57ypCi0g5qCH6aKYL1Nob3dub3Rlcy9UYWdzIOiHquWKqOeUn+aIkO+8muWQiOaIkOWujOaIkOWQjuiwg+eUqCBHTE0g55Sf5oiQ5pKt5a6i5YWD5pWw5o2uCi0g6K6+572u6aG55Y+Y5pu05Y2z5pe2IHRvYXN0IOaPkOekuu+8jOS4jemBruaMoeWKn+iDveWMuu+8iHRvYXN0IOenu+iHs+WPs+S4i+inku+8iQotIOato+WImemihOWkhOeQhuaWsOWinuS5puWQjeWPty/pob/lj7cv56C05oqY5Y+3L+erlue6v+i9rOmAl+WPt+inhOWIme+8iOaXoOmcgCBHTE0g5Y2z5Y+v5bel5L2c77yJCi0g5LiL6L295oyJ6ZKu5paw5aKeIuS4i+i9vSBXQVbvvIjnuq/kurrlo7DvvIki6YCJ6aG577yM5ZCrIEJHTSDml7blkIzml7bkv53nlZnkuKTku70KCioq5L+u5aSNKioKLSDkv53nlZkgdjIuMTMg5rqQ56CB5Lit55qEIC9cXC5kb2N4JC8g5q2j5YiZ5a2X6Z2i6YeP77yI6YG/5YWNIGVzYnVpbGQg5omT5YyF5ZCO5Lii5aSx5Y+N5pac5p2g55qE5r2c5Zyo6Zeu6aKY77yJCi0g5L+u5aSN6YOo572y54mI5LitIE5FV19GVU5DVElPTlMg5pyq5rOo5YWl55qE6Zeu6aKY77yIPC9zY3JpcHQ+IOWcqOaooeadv+Wtl+espuS4suS4remcgOWGmeS9nCA8XFwvc2NyaXB0Pu+8iQotIOS/ruWkjSBnZW5lcmF0ZU1ldGFkYXRhIOS4reS4ieWPjeW8leWPt+S7o+eggeWdl+agh+iusOWvvOiHtOaooeadv+Wtl+espuS4suaPkOWJjee7iOatoueahOivreazlemUmeivrwotIOS/ruWkjSBhbGVydCgn5Y6f5paH77yaXFxuJykg562J5a2X56ym5Liy5LitIFxcbiDooqvmqKHmnb/lrZfnrKbkuLLop6Pph4rkuLrlrp7pmYXmjaLooYznmoTor63ms5XplJnor68KLSDkv67lpI0gbWV0YWRhdGFDYXJkIOWFg+e0oOacquazqOWFpSBET00g5a+86Ie0IEUubWV0YWRhdGFDYXJkIOS4uiBudWxsIOeahOmXrumimO+8iOeUqOato+WImeabv+aNouS7o+abv+Wtl+mdouWMuemFje+8iQoKKirph43mnoQqKgotIFJFQURNRSDkuI4gY2hhbmdlbG9nIOaPkOiHs+aWh+S7tuWktOmDqCBSRUFETUVfQ09OVEVOVCDluLjph4/vvIxnZXRSZWFkbWVDb250ZW50KCkg55u05o6l5byV55So77yM6YG/5YWN5rqQ56CB5LiOIFVJIOaYvuekuuS4jeS4gOiHtAoKKirlrp7mtYvpqozor4HvvIgyMDI2LTA2LTE377yJKioKLSDnlKggMiDkuKrnnJ/lrp7pn7PoibLvvIjlsI/lqLHpn7PoibIgKyDkuZDkuZAt5pKt5a6i6Z+z6ImyMu+8iSsgMjUwOSDlrZfml6nmiqXmlofmoYjmtYvor5UKLSAyOSDmrrXlhajpg6jnlJ/miJDmiJDlip/vvIwwIOWksei0pe+8jOaAu+aXtumVvyA2OjM1Ci0g5pWw5a2XL+aXpeacn+ato+WImemihOWkhOeQhuato+ehru+8iDIwMjbihpLkuozpm7bkuozlha3jgIE25pyIMTfml6XihpLlha3mnIjljYHkuIPml6XjgIHnrKwzOOWxiuKGkuesrOS4ieWNgeWFq+Wxiuetie+8iQotIEFTUiDmir3moLfpqozor4EgNCDmrrXvvIzlhoXlrrnlrozmlbTlj6/or4bliKvvvIzml6DmrrXokL3kuKLlpLEKLSDkuablkI3lj7cv6aG/5Y+3L+egtOaKmOWPt+WcqOacrOasoea1i+ivleS4reacquWkhOeQhu+8iOWboCBHTE0g5pyq6YWN572u77yJ77yM6ZqP5ZCO5bey5re75Yqg5q2j5YiZ5Zue6YCA6KeE5YiZCgojIyMgdjIuMTMuMCAoMjAyNi0wNi0xMikKCi0g5L+u5aSNIE5WIOWFi+mahuS4iuS8oCBDb250ZW50LVR5cGUg6ZSZ6K+v77yaYXVkaW8vd2F2IC0+IGF1ZGlvL21wZWfvvIjljLnphY3lrp7pmYUgTVAzIOaWh+S7tu+8iQotIOaWsOWinuWFi+mahuWQjiBUVFMg6aqM6K+B77ya6Ieq5Yqo55So5YWL6ZqG6Z+z6Imy5Y+R6YCB5rWL6K+V6K+35rGC77yM56Gu6K6k6Z+z6Imy55yf5q2j5Y+v55SoCi0g5LyY5YyWIE5WIOWFi+mahumUmeivr+aPkOekuu+8muWFi+mahuaIkOWKn+S9hiBUVFMg5LiN5Y+v55So5pe257uZ5Ye65piO56Gu55qE5LiK5ri45pWF6Zqc5o+Q56S6Ci0gR0xNIOaZuuiDvemihOWkhOeQhu+8muaUr+aMgSBHTE0tNC1GbGFzaCBBUEkg6L+b6KGM5Lit5paH5pWw5a2X44CB56ym5Y+344CB5aSa6Z+z5a2X5pm66IO96aKE5aSE55CGCi0gR0xNIEFQSSBLZXkg566h55CG77ya6K6+572u5Lit5paw5aKeIEFQSSBLZXkg6L6T5YWl5ZKM5rWL6K+V5oyJ6ZKu77yM5pSv5oyB5a+85YWl5a+85Ye6Ci0g6aKE5aSE55CG5qih5byP6YCJ5oup77ya5YWz6ZetL+WbnumAgOaooeW8j++8iOato+WImeWksei0peaXtueUqCBHTE3vvIkv5aeL57uI5L2/55SoIEdMTQotIOmihOWkhOeQhuWuieWFqOajgOafpe+8muWmguaenOmihOWkhOeQhue7k+aenOW8guW4uO+8iOi/h+efre+8ie+8jOiHquWKqOWbnumAgOWIsOWOn+aWhwotIEdMTSBBUEkg5Luj55CG77ya6YCa6L+HIFdvcmtlciDku6PnkIbosIPnlKggR0xNIEFQSe+8jEFQSSBLZXkg5LiN5pq06Zyy5Yiw5a6i5oi356uvCi0gVFRTIOivt+axguaXpeW/l++8muiusOW9leWPkemAgeWIsCBUVFMg5byV5pOO55qE5paH5pys5YaF5a655ZKM6ZW/5bqm77yM5L6/5LqO6LCD6K+VCgojIyMgdjIuMTIuMCAoMjAyNi0wNi0xMikKCi0g56e76Zmk6aG26YOo5Y+C6ICD6Z+z6aKR5Y2h77ya6YeH55SoIuaWh+acrOS8mOWFiOKGkuWGjeWIhumFjemfs+a6kCLlt6XkvZzmtYEKLSDor7Tor53kurrliIbphY3ljaHph43mnoTvvJrljZXkurrmqKHlvI/kuZ/mmL7npLoi6buY6K6kIumfs+a6kOanvQotIOmfs+a6kOS6kuaWpe+8muW3suiiq+S4gOS9jeivtOivneS6uumAieaLqeeahOmfs+a6kO+8jOWcqOWFtuS7luivtOivneS6uueahOS4i+aLieS4ree9rueBsAotIOmfs+a6kOeuoeeQhiAyLjDvvJrorr7nva7pnaLmnb/mlrDlop7pooTop4jjgIHph43lkb3lkI3jgIHlkIzmraXnirbmgIHmjIfnpLoKLSDmlbDlrZcv56ym5Y+36aKE5aSE55CG77ya6Ieq5Yqo5bCG5pWw5a2X6L2s5Lit5paH6K+75rOV77yM56ym5Y+36L2s5paH5a2XCi0g5bm05Lu9L+aXpeacny/nlLXor53or4bliKsKLSDpn7PmupDmlbDmja7nu5PmnoTljYfnuqfvvJrmlK/mjIEgTlYvS0sg5Y+M5byV5pOO6Z+z6ImyIElECi0g6Z+z6aKR5Y6L57yp77ya5paw5bu66Z+z5rqQ5pe26Ieq5Yqo6YeN6YeH5qC3IDI0a0h644CB5oiq5Y+WIDE1IOenkgoKIyMjIHYyLjExLjAgKDIwMjYtMDYtMTEpCgotIOWkmuS6uuaXgeeZveaooeW8j++8muiHquWKqOajgOa1i+ivtOivneS6uuagh+iusAotIOaNouihjOe7reaOpe+8muayoeacieivtOivneS6uuagh+iusOeahOihjOiHquWKqOW9kuWxnuS4iuS4gOS4quivtOivneS6ugotIOmYsuWRhuajgOa1i++8muW9k+ivtOivneS6uuWPsOivjemHj+S4pemHjeS4jeWdh+ihoeaXtuitpuWRigotIOiHquWumuS5ieivtOivneS6uuaooeW8j++8muaUr+aMgea3u+WKoOiHquWumuS5ieato+WImeihqOi+vuW8jwotIOWkmuS6uiBTUlQg5a2X5bmV77ya5a2X5bmV6Ieq5Yqo5qCH5rOo6K+06K+d5Lq65aeT5ZCNCi0g5aSa5Lq65Ymq5pig5a+85Ye677ya5Ymq5pig5bel56iL5Lmf5pSv5oyB5aSa5Lq65a2X5bmV5qCH562+CgojIyMgdjIuOS4wICgyMDI2LTA1LTI1KQoKLSDmlrDlop4gS2lraVZvaWNlIOa4oOmBk++8muWkh+mAiSBUVFMg5byV5pOO77yM5LiJ56eN5YWN6LS55qih5Z6LCi0gR2VldGVzdCDkurrmnLrpqozor4HvvJrpgJrov4cgV29ya2VyIOS7o+eQhuehruS/nSBJUCDkuIDoh7QKLSDnp6/liIbkvZnph4/mn6Xor6LvvJrlrp7ml7bmmL7npLrliankvZnnp6/liIbjgIHlt7LnlKjnp6/liIblkozph43nva7ml7bpl7QKLSBMb2cg5o6n5Yi25Y+w77ya5paw5aKe5LqL5Lu26K6w5b2V5o6n5Yi25Y+wCgojIyMgdjIuOC4wICgyMDI2LTA1LTI2KQoKLSBKU1ppcCDmh5LliqDovb3vvJrku4XlnKjpnIDopoHml7bliqDovb0KLSDnp7vpmaTosIPor5Xml6Xlv5fvvJrlh4/lsJHmiafooYzlvIDplIAKLSDnroDljJblrZfluZXnrpfms5XvvJrkvJjljJboh6rliqjmjaLooYznrpfms5UKLSBET00g5YWD57Sg57yT5a2Y77ya5YeP5bCR6YeN5aSN5p+l6K+iCi0gSFRUUCDnvJPlrZjvvJrmt7vliqDpobXpnaLnvJPlrZjlpLQKCiMjIyB2Mi43LjAgKDIwMjYtMDUtMjUpCgotIOS/ruWkjSBTUlQg5pe26Ze06L205qC55pys6Zeu6aKY77ya5byD55So5L2N572u6L+96Liq5rOV77yM5pS555So5a2X56ym5pWw57Sv5Yqg5rOVCi0g5L+u5aSN5Ymq5pig5a2X5bmV5ZCM5q2lCgojIyMgdjIuNi4wICgyMDI2LTA1LTI1KQoKLSDkv67lpI0gU1JUIOaXtumXtOi9tO+8muS/ruato+Wtl+W5leS4jumfs+mikeS4jeWQjOatpQotIOS/ruWkjSBXQVYg5LiL6L2977ya55u05o6l5LiL6L295bey5pyJ5paH5Lu2Ci0g5paH5Lu25ZCN6KeE5YiZ77ya5a+85YWlIGRvY3gg5pe25paH5Lu25ZCN5LiOIGRvY3gg5LiA6Ie0Ci0g5Ymq5pigIFpJUCDnu5PmnoTop4TojIPljJYKLSDnlJ/miJDljoblj7LljYfnuqfvvJrkvb/nlKggSW5kZXhlZERCIOS/neWtmAoKIyMjIHYyLjUuMCAoMjAyNi0wNS0yNSkKCi0g5L+u5aSN5Ymq5pig5a2X5bmV5pi+56S677ya5a2X5bmV57G75Z6L5pS55Li6IHN1YnRpdGxlCi0g5L+u5aSN5a2X5bmV5qC35byP5qC85byP77yac3Ryb2tlIOagvOW8j+Wvuem9kCBweUppYW5ZaW5nRHJhZnQg6KeE6IyDCi0g6KGl5YWo5a2X5bmV57Sg5p2Q5a2X5q61Ci0g5L+u5aSN5a2X5bmV5Z2Q5qCH77yadHJhbnNmb3JtIOS9v+eUqOW9kuS4gOWMluWdkOaghyB5Oi0wLjgKCiMjIyB2Mi40LjAgKDIwMjYtMDUtMjUpCgotIOinhOiMg+WMluaWh+S7tuWQje+8mnl5eXltbWRkLWhobW1zcwotIFNSVCDoh6rliqjmjaLooYzvvJrmr4/ooYzkuI3otoXov4cgMTUg5a2XCi0g5Ymq5pig5a2X5bmV5qC35byP77ya5oCd5rqQ6buR5L2T44CB55m95a2X6buR6L6544CB5a2X5Y+3IDEwCi0g5ZCM5qyh55Sf5oiQ5pe26Ze05oiz5LiA6Ie0CgojIyMgdjIuMy4wICgyMDI2LTA1LTI0KQoKLSDpn7PoibLlpI3nlKjkvJjljJbvvJrkv53lrZjnmoTpn7PmupDlhbPogZQgTmljZVZvaWNlIOacjeWKoeWZqOerryByZWZlcmVuY2VJZAotIOaZuuiDvemqjOivge+8muS9v+eUqOW3suS/neWtmOmfs+iJsuaXtuajgOafpeacjeWKoeWZqOerr+acieaViOaApwotIOiHquWKqOmHjeaWsOWFi+mahu+8muacjeWKoeWZqOerr+WkseaViOaXtuiHquWKqOmHjeaWsOWFi+mahgoKIyMjIHYyLjIuMCAoMjAyNi0wNS0yNCkKCi0g5L+u5aSN5paH5a2X5YiG5q6177yaTmljZVZvaWNlIOaooeW8j+S4i+efreWPpeS4jeWGjeWQhOiHquaIkOautQotIOWujOaVtOaOp+WItuWPsOaXpeW/l++8muaWueS+vyBGMTIg6LCD6K+VCi0g5YiG5q616YC76L6R6YeN5p6ECgojIyMgdjIuMS4wICgyMDI2LTA1LTI0KQoKLSDmlrDlop4gTmljZVZvaWNlIOS9nOS4uuS4u+imgSBUVFMg5byV5pOOCi0g5paw5aKe5Y+M5byV5pOO5YiH5o2i5ZmoCi0g5paw5aKeIE5pY2VWb2ljZSBBUEkg5Luj55CG77yI5pyN5Yqh56uvIEhNQUMtU0hBMjU2IOetvuWQje+8iQotIOaWsOWinuWjsOmfs+WFi+mahua1geeoi++8muS4iuS8oCDihpIg6K6t57uDIOKGkiBUVFMKLSDmlrDlop7pn7PmupDlhbPogZTlhYvpmoYgSUQKCiMjIyB2Mi4wLjAgKDIwMjYtMDUtMjMpCgotIOWFqOaWsOmHjeaehO+8jOWfuuS6jiBrb3p6enEvaW5kZXh0dHMyYXBpIFJFU1QgQVBJCi0g5paw5aKe5Ymq5pig5bel56iLIFpJUCDlr7zlh7rlip/og70KLSDmlrDlop4gU1JUIOWtl+W5leeUn+aIkAotIOaWsOWinumfs+a6kOeuoeeQhuOAgeW5tuWPkSBUVFMg55Sf5oiQ44CB55Sf5oiQ5Y6G5Y+y6K6w5b2VCi0g5paw5aKeIFdvcmQg5paH5qGj5a+85YWl44CB6YWN572u5a+85YWlL+WvvOWHug==';
  var binary = atob(b64);
  var bytes = new Uint8Array(binary.length);
  for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new TextDecoder('utf-8').decode(bytes);
})();
// v2.14: Default GLM system prompt (editable in settings)
var DEFAULT_GLM_PROMPT = '你是一个TTS文本预处理助手。将输入文本转换为适合语音合成朗读的中文。规则：\\n'
  + '1. 数字按数位转中文读法：403→四百零三，1000→一千，7000→七千，4999→四千九百九十九，126.5→一百二十六点五\\n'
  + '2. 年份和届级逐字读：2026年→二零二六年，2026届→二零二六届\\n'
  + '3. 营销词连读不改：618大促→六一八大促，双11→双十一，双12→双十二\\n'
  + '4. 百分号 → 百分之：80.3%→百分之八十点三，50%→百分之五十\\n'
  + '5. 标点中转（远端 TTS 无法识别这些标点）：\\n'
  + '   - 顿号、→ 逗号，\\n'
  + '   - 书名号《》→ 直接去除（保留书名内容，例如《飞驰人生3》→ 飞驰人生3）\\n'
  + '   - 破折号——→ 逗号，\\n'
  + '   - 省略号……→ 等等\\n'
  + '   - 全角冒号：→ 逗号，\\n'
  + '6. 符号转文字：≥→大于等于，℃→摄氏度，×→乘以，/→或，¥100→100元\\n'
  + '7. 保持原文意思不变，只调整朗读形式\\n'
  + '8. 不要添加解释、标注或前缀\\n'
  + '9. 直接输出转换结果';

var S = {
  engine: 'nicevoice',  // v2.21: NiceVoice is the only engine (IDX/KK removed)
  audioSources: [],       // saved voices: [{id, name, audioBase64, nvReferenceId, kkVoiceId, addedAt, lastSyncAt}]
  activeSourceId: '',
  segments: [],
  segmentBuffers: [],
  segmentDurations: [],
  resultWavBlob: null,
  resultSrt: '',
  resultWavUrl: null,     // Object URL for playback, reuse for download
  isGenerating: false,
  cancelRequested: false,
  elapsedTimer: null,
  elapsedStart: 0,
  downloadTimestamp: '',
  docxFileName: '',       // e.g. "0525 韩星见面会" (without .docx extension)
  projectName: '',        // for file naming: docxFileName or timestamp
  // NiceVoice state
  nvCloneBusy: false,
  // Speaker state
  speakerMode: 'single',  // 'single' | 'multi'
  detectedSpeakers: [],    // [{name, lineCount, charCount}]
  speakerAssignments: {},  // { '小娱': sourceId, '乐乐': sourceId }
  speakerVoiceData: {},    // { '小娱': { audioFile, nvReferenceId, kkVoiceId }, ... } - populated during generation
  // New voice form state
  newVoiceAudioData: null, // { dataUrl, base64, wavBlob } - temp data for new voice form
  // Config
  config: {
    engine: 'nicevoice',
    // NiceVoice
    nvWait: 16,
    nvMaxChars: 150,
    nvMaxPoll: 60,
    // History
    maxHistory: 10,
    // Speaker patterns
    spBracket: true,     // enable 【name】 pattern
    spColon: true,       // enable name: pattern
    spCustomPatterns: [], // custom regex patterns (strings)
    spBalanceThreshold: 5, // anti-fool ratio threshold
    // v2.14: GLM system prompt (editable in settings)
    glmSystemPrompt: '',  // empty = use DEFAULT_GLM_PROMPT
    // v2.14: BGM mixing
    bgmEnabled: false,
    bgmAudioBase64: '',  // BGM file as base64 data URL
    bgmVolume: 0.126,  // -18dB ≈ 0.126 linear gain
    bgmDuckDepth: 0.5,  // ducking multiplier (0.5 = -6dB further)
    bgmDuckFadeMs: 300,
    // v2.14: Voice normalization
    voiceNormalizeEnabled: true,
    voiceTargetPeakDb: -3,
    speakerRmsEqualize: true,
    femaleCompress: true,
    // v2.14: Intro/Outro
    introOutroEnabled: false,
    introAudioBase64: '',
    outroAudioBase64: '',
    introOutroFadeMs: 500,
    introOutroMode: 'fade',  // 'fade' | 'direct'
  }
};

// ==================== JSZip Async Loader ====================
var _jszipPromise = null;
function loadJSZip() {
  if (!_jszipPromise) {
    _jszipPromise = new Promise(function(resolve, reject) {
      var s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
      s.onload = resolve;
      s.onerror = function() { reject(new Error('Failed to load JSZip')); };
      document.head.appendChild(s);
    });
  }
  return _jszipPromise;
}

var E = {};
function cacheElements() {
  ['apiDot','apiText','generateBtn','genBtnText',
   'nvSettings','idxSettings','cfgEngine','settingsSourceList',
   'textInput','charCount','lineCount','segCount','docxInfo','docxDropOverlay',
   'textCard','cancelBtn','progressBar','progressFill','elapsed',
   'segTable','segBody','resultSection','resultAudio','settingsPanel','settingsOverlay',
   'historyList','readmeBody','toast','stabSettings','stabHistory','stabAbout',
   'cfgNvWait','cfgNvMaxChars','cfgNvMaxPoll','cfgApiBase','cfgLanguage','btnKK','kkCfgCard','kkConn','kkSettings','logBox','cfPanel','cfIP','cfUUID','cfUrl','cfIframe','cfIframeOverlay','cfRaw',
   'cfgMaxChars','cfgConcurrency','cfgRetry','cfgPollInterval','cfgMaxHistory',
   'speakerCard','speakerList','speakerWarning','speakerWarningText','speakerModeLabel',
   'cfgSpBracket','cfgSpColon','speakerPatternsList','cfgSpBalance',
   'previewCard','previewBody','previewBtn','regenGlmBtn','applyPreviewBtn',
   'cfgGlmSystemPrompt','cfgBgmEnabled','cfgBgmVolume','cfgBgmVolumeVal','cfgBgmDuckDepth','cfgBgmDuckDepthVal',
   'cfgVoiceNormalize','cfgVoiceTargetPeak','cfgSpeakerRms','cfgFemaleCompress',
   'cfgIntroOutroEnabled','cfgIntroOutroFade','cfgIntroOutroMode',
   'alternationWarning','alternationFixBtn','metadataCard','metadataTitle','metadataShownotes','metadataTags','genMetadataBtn'
  ].forEach(function(id) { E[id] = document.getElementById(id); });
}

// ==================== Init ====================
window.addEventListener('DOMContentLoaded', function() {
  cacheElements();
  loadConfig();
  loadAudioSources();
  checkApiStatus();
  initDocxDragDrop();
  initUploadZoneDragDrop(); // v2.20
  updateTextStats();
  applyConfigToUI();
  switchEngine(S.config.engine || 'nicevoice');
  // v2.14: Auto-save + toast on any settings change (debounced)
  var _saveTimer = null;
  document.getElementById('settingsPanel').addEventListener('change', function(e) {
    var tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') {
      saveConfig();
      showToast('设置已保存', 'success');
    }
  });
  document.getElementById('settingsPanel').addEventListener('input', function(e) {
    var tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') {
      if (e.target.type === 'number' || e.target.type === 'password' || tag === 'TEXTAREA') {
        clearTimeout(_saveTimer);
        _saveTimer = setTimeout(function() {
          saveConfig();
          showToast('设置已保存', 'success');
        }, 800);
      }
      // live-update slider labels
      if (e.target.id === 'cfgBgmVolume') {
        var v = document.getElementById('cfgBgmVolumeVal');
        if (v) v.textContent = e.target.value + '%';
      }
      if (e.target.id === 'cfgBgmDuckDepth') {
        var v2 = document.getElementById('cfgBgmDuckDepthVal');
        if (v2) v2.textContent = e.target.value + '%';
      }
    }
  });
});

// ==================== Engine Switching ====================
function switchEngine(eng) {
  // v2.21: NiceVoice is the only engine; kept for compatibility with old calls
  S.engine = 'nicevoice';
  S.config.engine = 'nicevoice';
  var btnNV = E.btnNV;
  var genBtn = E.generateBtn;
  var genBtnText = E.genBtnText;
  var nvSettings = E.nvSettings;
  if (btnNV) btnNV.className = 'engine-btn active-nv';
  if (genBtn) genBtn.className = 'gen-btn nv-active';
  if (genBtnText) genBtnText.innerHTML = svgIcon('zap') + ' 开始合成 (NiceVoice)';
  if (nvSettings) nvSettings.style.display = '';
  updateTextStats();
  checkApiStatus();
}

// ==================== API Status Check ====================
async function checkApiStatus() {
  var dot = E.apiDot;
  var txt = E.apiText;
  dot.className = 'dot checking';
  txt.textContent = '检测中...';

  if (S.engine === 'nicevoice') {
    // Check NiceVoice API
    try {
      var resp = await fetch('/api/nv/getUploadUrl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suffix: '.wav' })
      });
      if (resp.ok) {
        var data = await resp.json();
        if (data.data && (data.data.url || data.data.uploadUrl)) {
          dot.className = 'dot online';
          txt.textContent = 'NiceVoice 在线';
        } else if (data.code !== undefined) {
          dot.className = 'dot online';
          txt.textContent = 'NiceVoice 在线';
        } else {
          dot.className = 'dot offline';
          txt.textContent = 'NiceVoice 响应异常';
        }
      } else {
        dot.className = 'dot offline';
        txt.textContent = 'NiceVoice 不可达';
      }
    } catch(e) {
      dot.className = 'dot offline';
      txt.textContent = 'NiceVoice 不可达';
    }

  }
}

// ==================== DOCX Processing ====================
function initDocxDragDrop() {
  var card = E.textCard;
  var overlay = E.docxDropOverlay;
  var dragCounter = 0;
  card.addEventListener('dragenter', function(e) { e.preventDefault(); e.stopPropagation(); dragCounter++; overlay.classList.add('active'); });
  card.addEventListener('dragleave', function(e) { e.preventDefault(); e.stopPropagation(); dragCounter--; if (dragCounter <= 0) { dragCounter = 0; overlay.classList.remove('active'); } });
  card.addEventListener('dragover', function(e) { e.preventDefault(); e.stopPropagation(); });
  card.addEventListener('drop', function(e) {
    e.preventDefault(); e.stopPropagation(); dragCounter = 0; overlay.classList.remove('active');
    var files = e.dataTransfer.files;
    if (files.length > 0) {
      var file = files[0];
      if (file.name.endsWith('.docx')) { processDocxFile(file); }
      else if (file.type.startsWith('audio/')) { /* handled by audio zone */ }
      else { showToast('请拖入 .docx 格式的 Word 文档', 'error'); }
    }
  });
}

// v2.20: Prevent browser default navigation when dropping audio files on upload zones
function initUploadZoneDragDrop() {
  document.addEventListener('dragover', function(e) {
    var zone = e.target.closest('.upload-zone');
    if (zone) { e.preventDefault(); e.stopPropagation(); }
  });
  document.addEventListener('drop', function(e) {
    var zone = e.target.closest('.upload-zone');
    if (zone) {
      e.preventDefault(); e.stopPropagation();
      var fileInput = zone.querySelector('input[type="file"]');
      if (!fileInput) {
        var nextEl = zone.nextElementSibling;
        if (nextEl && nextEl.tagName === 'INPUT' && nextEl.type === 'file') fileInput = nextEl;
      }
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length > 0 && files[0].type.startsWith('audio/')) {
        if (fileInput) {
          var dt = new DataTransfer();
          dt.items.add(files[0]);
          fileInput.files = dt.files;
          fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
      } else if (files && files.length > 0) {
        showToast('请拖入音频文件', 'error');
      }
    }
  });
}

function handleDocxUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  if (!file.name.endsWith('.docx')) { showToast('请选择 .docx 格式的 Word 文档', 'error'); event.target.value = ''; return; }
  processDocxFile(file);
  event.target.value = '';
}

async function processDocxFile(file) {
  await loadJSZip();
  showToast('正在解析 Word 文档...', 'info');
  try {
    var arrayBuffer = await file.arrayBuffer();
    var zip = await JSZip.loadAsync(arrayBuffer);
    var docXml = await zip.file('word/document.xml').async('string');
    var parser = new DOMParser();
    var xmlDoc = parser.parseFromString(docXml, 'application/xml');
    var textParts = extractLeftColumnText(xmlDoc);
    if (textParts.length === 0) {
      var allText = extractAllParagraphText(xmlDoc);
      if (allText) {
        E.textInput.value = allText;
        updateTextStats();
        showToast('未找到表格，已提取全部文本', 'info');
      } else {
        showToast('文档中未找到可用文本', 'error'); return;
      }
    } else {
      var fullText = textParts.join('\\n');
      E.textInput.value = fullText;
      updateTextStats();
      showToast('已读取表格左列文本，共 ' + textParts.length + ' 段', 'success');
    }
    E.docxInfo.textContent = file.name;
    // Store docx filename (without .docx) for project naming
    S.docxFileName = file.name.replace(/\\.docx$/i, '');
  } catch(err) {
    showToast('解析 Word 文档失败: ' + err.message, 'error');
  }
}

function extractXmlText(element, ns) {
  var paragraphs = element.getElementsByTagNameNS(ns, 'p');
  var lines = [];
  for (var p = 0; p < paragraphs.length; p++) {
    var runs = paragraphs[p].getElementsByTagNameNS(ns, 'r');
    var lineText = '';
    for (var r = 0; r < runs.length; r++) {
      var texts = runs[r].getElementsByTagNameNS(ns, 't');
      for (var t = 0; t < texts.length; t++) lineText += texts[t].textContent || '';
    }
    lines.push(lineText);
  }
  return lines;
}

function extractLeftColumnText(xmlDoc) {
  var ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
  var parts = [];
  var tables = xmlDoc.getElementsByTagNameNS(ns, 'tbl');
  for (var t = 0; t < tables.length; t++) {
    var rows = tables[t].getElementsByTagNameNS(ns, 'tr');
    for (var r = 0; r < rows.length; r++) {
      var cells = rows[r].getElementsByTagNameNS(ns, 'tc');
      if (cells.length >= 1) {
        var cellText = getCellText(cells[0], ns);
        if (cellText.trim()) parts.push(cellText.trim());
      }
    }
  }
  return parts;
}

function getCellText(tcElement, ns) {
  return extractXmlText(tcElement, ns).join('\\n');
}

function extractAllParagraphText(xmlDoc) {
  var ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
  var lines = extractXmlText(xmlDoc, ns);
  var filtered = [];
  for (var i = 0; i < lines.length; i++) { if (lines[i].trim()) filtered.push(lines[i].trim()); }
  return filtered.join('\\n');
}

// ==================== Config Management ====================
function loadConfig() {
  try {
    var saved = localStorage.getItem('ttsvoicelab_config');
    if (saved) {
      var c = JSON.parse(saved);
      var loadableExtra = { ttsRules: 1, builtinRules: 1, ttsRuleFlags: 1 };
      Object.keys(c).forEach(function(k) { if (S.config[k] !== undefined || loadableExtra[k]) S.config[k] = c[k]; });
    }
  } catch(e) {}
  S.engine = S.config.engine || 'nicevoice';
}

function saveConfig() {
  readConfigFromUI();
  try { localStorage.setItem('ttsvoicelab_config', JSON.stringify(S.config)); } catch(e) {}
}

function applyConfigToUI() {
  var c = S.config;
  var el;
  el = E.cfgNvWait; if (el) el.value = c.nvWait || 16;
  el = E.cfgNvMaxChars; if (el) el.value = c.nvMaxChars || 150;
  el = E.cfgNvMaxPoll; if (el) el.value = c.nvMaxPoll || 60;
  el = E.cfgMaxHistory; if (el) el.value = c.maxHistory || 10;
  el = E.cfgSpBracket; if (el) el.checked = c.spBracket !== false;
  el = E.cfgSpColon; if (el) el.checked = c.spColon !== false;
  el = E.cfgSpBalance; if (el) el.value = c.spBalanceThreshold || 5;
  el = document.getElementById('cfgGlmApiKey'); if (el) el.value = c.glmApiKey || '';
  el = document.getElementById('cfgGlmPreprocess'); if (el) el.value = c.glmPreprocess || 'off';
  el = document.getElementById('cfgGlmSystemPrompt'); if (el) el.value = c.glmSystemPrompt || '';
  // v2.14: BGM
  el = document.getElementById('cfgBgmEnabled'); if (el) el.checked = c.bgmEnabled !== false && !!c.bgmAudioBase64;
  el = document.getElementById('cfgBgmVolume'); if (el) el.value = Math.round(Math.sqrt(c.bgmVolume || 0.126) * 100);
  el = document.getElementById('cfgBgmVolumeVal'); if (el) el.textContent = (Math.round(Math.sqrt(c.bgmVolume || 0.126) * 100)) + '%';
  el = document.getElementById('cfgBgmDuckDepth'); if (el) el.value = Math.round((c.bgmDuckDepth || 0.5) * 100);
  el = document.getElementById('cfgBgmDuckDepthVal'); if (el) el.textContent = Math.round((c.bgmDuckDepth || 0.5) * 100) + '%';
  // v2.14: Voice normalization
  el = document.getElementById('cfgVoiceNormalize'); if (el) el.checked = c.voiceNormalizeEnabled !== false;
  el = document.getElementById('cfgVoiceTargetPeak'); if (el) el.value = c.voiceTargetPeakDb || -3;
  el = document.getElementById('cfgSpeakerRms'); if (el) el.checked = c.speakerRmsEqualize !== false;
  el = document.getElementById('cfgFemaleCompress'); if (el) el.checked = c.femaleCompress !== false;
  // v2.14: Intro/Outro
  el = document.getElementById('cfgIntroOutroEnabled'); if (el) el.checked = c.introOutroEnabled !== false && (!!c.introAudioBase64 || !!c.outroAudioBase64);
  el = document.getElementById('cfgIntroOutroFade'); if (el) el.value = c.introOutroFadeMs || 500;
  el = document.getElementById('cfgIntroOutroMode'); if (el) el.value = c.introOutroMode || 'fade';
  renderBgmStatus();
  renderIntroOutroStatus();
  renderSpeakerPatterns();
  renderTtsRules();
}

function readConfigFromUI() {
  var c = S.config;
  c.engine = 'nicevoice'; // v2.21: single engine
  c.nvWait = parseInt(E.cfgNvWait.value) || 16;
  c.nvMaxChars = parseInt(E.cfgNvMaxChars.value) || 150;
  c.nvMaxPoll = parseInt(E.cfgNvMaxPoll.value) || 60;
  c.maxHistory = Math.max(1, parseInt(E.cfgMaxHistory.value) || 10);
  c.spBracket = E.cfgSpBracket ? E.cfgSpBracket.checked : true;
  c.spColon = E.cfgSpColon ? E.cfgSpColon.checked : true;
  c.spBalanceThreshold = parseInt(E.cfgSpBalance ? E.cfgSpBalance.value : 5) || 5;
  c.glmApiKey = (document.getElementById('cfgGlmApiKey') ? document.getElementById('cfgGlmApiKey').value : '').trim();
  c.glmPreprocess = document.getElementById('cfgGlmPreprocess') ? document.getElementById('cfgGlmPreprocess').value : 'off';
  c.glmSystemPrompt = document.getElementById('cfgGlmSystemPrompt') ? document.getElementById('cfgGlmSystemPrompt').value : '';
  // v2.14: BGM
  c.bgmEnabled = document.getElementById('cfgBgmEnabled') ? document.getElementById('cfgBgmEnabled').checked : false;
  var bgmVolPct = parseInt(document.getElementById('cfgBgmVolume') ? document.getElementById('cfgBgmVolume').value : 35) || 35;
  c.bgmVolume = Math.pow(bgmVolPct / 100, 2);  // slider is sqrt scale
  var duckPct = parseInt(document.getElementById('cfgBgmDuckDepth') ? document.getElementById('cfgBgmDuckDepth').value : 50) || 50;
  c.bgmDuckDepth = duckPct / 100;
  // v2.14: Voice normalization
  c.voiceNormalizeEnabled = document.getElementById('cfgVoiceNormalize') ? document.getElementById('cfgVoiceNormalize').checked : true;
  c.voiceTargetPeakDb = parseInt(document.getElementById('cfgVoiceTargetPeak') ? document.getElementById('cfgVoiceTargetPeak').value : -3) || -3;
  c.speakerRmsEqualize = document.getElementById('cfgSpeakerRms') ? document.getElementById('cfgSpeakerRms').checked : true;
  c.femaleCompress = document.getElementById('cfgFemaleCompress') ? document.getElementById('cfgFemaleCompress').checked : true;
  // v2.14: Intro/Outro
  c.introOutroEnabled = document.getElementById('cfgIntroOutroEnabled') ? document.getElementById('cfgIntroOutroEnabled').checked : false;
  c.introOutroFadeMs = parseInt(document.getElementById('cfgIntroOutroFade') ? document.getElementById('cfgIntroOutroFade').value : 500) || 500;
  c.introOutroMode = document.getElementById('cfgIntroOutroMode') ? document.getElementById('cfgIntroOutroMode').value : 'fade';
}

// ==================== Audio Source Management ====================
function loadAudioSources() {
  try {
    var saved = localStorage.getItem('ttsvoicelab_sources');
    if (saved) S.audioSources = JSON.parse(saved);
    // Migrate old format: dataUrl -> audioBase64
    S.audioSources.forEach(function(src) {
      if (src.dataUrl && !src.audioBase64) {
        src.audioBase64 = src.dataUrl;
        delete src.dataUrl;
      }
      if (!src.kkVoiceId) src.kkVoiceId = null;
      if (!src.lastSyncAt) src.lastSyncAt = null;
    });
    saveAudioSources();
  } catch(e) {}
  renderSettingsVoiceList();
}

function saveAudioSources() {
  try { localStorage.setItem('ttsvoicelab_sources', JSON.stringify(S.audioSources)); } catch(e) {}
}

function buildVoiceDataFromSource(src) {
  var audioBase64 = src.audioBase64 || src.dataUrl || '';
  var base64 = audioBase64.split(',')[1] || audioBase64;
  return {
    audioFile: { name: src.name + '.wav', dataUrl: audioBase64, base64: base64 },
    nvReferenceId: src.nvReferenceId || null,
    kkVoiceId: src.kkVoiceId || null
  };
}

// ==================== Settings Voice Management ====================
function renderSettingsVoiceList() {
  var container = document.getElementById('settingsVoiceList');
  if (!container) return;
  if (!S.audioSources.length) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:6px">暂无保存的音源</div>';
    return;
  }
  var html = '';
  S.audioSources.forEach(function(src) {
    var syncStatus = 'yellow';
    var syncTitle = '未验证';
    if (src.nvReferenceId) { syncStatus = 'green'; syncTitle = 'NV已同步'; }
    if (src.kkVoiceId) { syncStatus = 'green'; syncTitle += ' KK已同步'; }
    if (!src.nvReferenceId && !src.kkVoiceId) { syncStatus = 'yellow'; syncTitle = '未上传至引擎'; }
    html += '<div class="source-item">';
    html += '<span class="s-name" ondblclick="renameVoice(\\'' + src.id + '\\')" title="双击重命名" style="cursor:pointer">' + escHtml(src.name) + '</span>';
    html += '<span style="display:inline-flex;align-items:center;gap:4px;margin-left:6px" title="' + escHtml(syncTitle) + '"><span style="width:8px;height:8px;border-radius:50%;background:var(--' + (syncStatus === 'green' ? 'green' : 'orange') + ');display:inline-block"></span><span style="font-size:10px;color:var(--text2)">' + escHtml(syncTitle) + '</span></span>';
    html += '<span class="s-actions">';
    html += '<button onclick="event.stopPropagation();previewVoice(\\'' + src.id + '\\', this)" title="试听" style="color:var(--blue)">' + svgIcon('play') + '</button>';
    html += '<button onclick="event.stopPropagation();deleteVoiceConfirm(\\'' + src.id + '\\')" title="删除" style="color:var(--red)">' + svgIcon('x') + '</button>';
    html += '</span>';
    html += '</div>';
  });
  container.innerHTML = html;
}

var _voicePreviewAudio = null;
var _voicePreviewBtns = {};  // track buttons by voice id
function previewVoice(id, btnEl) {
  // If currently playing this voice, stop
  if (_voicePreviewAudio && _voicePreviewAudio._voiceId === id) {
    _voicePreviewAudio.pause();
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = svgIcon('play');
    return;
  }
  // Stop any other playing voice
  if (_voicePreviewAudio) {
    var oldId = _voicePreviewAudio._voiceId;
    _voicePreviewAudio.pause();
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[oldId]) _voicePreviewBtns[oldId].innerHTML = svgIcon('play');
  }
  var src = S.audioSources.find(function(s) { return s.id === id; });
  if (!src || !src.audioBase64) { showToast('无音频数据', 'error'); return; }
  if (btnEl) _voicePreviewBtns[id] = btnEl;
  _voicePreviewAudio = new Audio(src.audioBase64);
  _voicePreviewAudio._voiceId = id;
  _voicePreviewAudio.play().then(function() {
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = svgIcon('pause');
  }).catch(function() { showToast('播放失败', 'error'); });
  _voicePreviewAudio.onended = function() {
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = svgIcon('play');
  };
  _voicePreviewAudio.onerror = function() {
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = svgIcon('play');
    showToast('播放失败', 'error');
  };
}

function deleteVoiceConfirm(id) {
  var src = S.audioSources.find(function(s) { return s.id === id; });
  if (!src) return;
  if (confirm('确定删除音源 "' + src.name + '"？')) {
    S.audioSources = S.audioSources.filter(function(s) { return s.id !== id; });
    saveAudioSources();
    renderSettingsVoiceList();
    renderSpeakerAssignmentList();
    showToast('已删除音源', 'info');
  }
}

function renameVoice(id) {
  var src = S.audioSources.find(function(s) { return s.id === id; });
  if (!src) return;
  var newName = prompt('重命名音源:', src.name);
  if (newName && newName.trim()) {
    src.name = newName.trim();
    saveAudioSources();
    renderSettingsVoiceList();
    renderSpeakerAssignmentList();
  }
}

function showNewVoiceForm() {
  var form = document.getElementById('newVoiceForm');
  if (form) form.style.display = 'block';
}

function hideNewVoiceForm() {
  var form = document.getElementById('newVoiceForm');
  if (form) form.style.display = 'none';
  S.newVoiceAudioData = null;
  var nameInput = document.getElementById('newVoiceName');
  if (nameInput) nameInput.value = '';
  var uploadText = document.getElementById('settingsUploadText');
  if (uploadText) uploadText.textContent = '点击上传参考音频';
}

async function handleSettingsVoiceUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var uploadText = document.getElementById('settingsUploadText');
  if (uploadText) uploadText.textContent = '正在处理...';

  try {
    var dataUrl = await new Promise(function(resolve) {
      var reader = new FileReader();
      reader.onload = function(e) { resolve(e.target.result); };
      reader.readAsDataURL(file);
    });

    var base64 = dataUrl.split(',')[1];
    // Compress: resample to 24kHz, trim to 15s
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      var resp = await fetch(dataUrl);
      var arrayBuffer = await resp.arrayBuffer();
      var decoded = await ctx.decodeAudioData(arrayBuffer);
      var duration = Math.min(decoded.duration, 15);
      var trimSamples = Math.floor(duration * 24000);
      var channelData = decoded.getChannelData(0);
      if (trimSamples < channelData.length) channelData = channelData.slice(0, trimSamples);
      var trimBuffer = ctx.createBuffer(1, channelData.length, 24000);
      trimBuffer.copyToChannel(channelData, 0);
      var wavBlob = audioBufferToWav(trimBuffer);
      ctx.close();
      var optDataUrl = await new Promise(function(resolve) {
        var reader2 = new FileReader();
        reader2.onload = function(e) { resolve(e.target.result); };
        reader2.readAsDataURL(wavBlob);
      });
      S.newVoiceAudioData = { dataUrl: optDataUrl, base64: optDataUrl.split(',')[1], wavBlob: wavBlob };
    } catch(e) {
      S.newVoiceAudioData = { dataUrl: dataUrl, base64: base64, wavBlob: null };
    }
    if (uploadText) uploadText.textContent = svgIcon('check') + ' ' + file.name;
  } catch(e) {
    if (uploadText) uploadText.textContent = '处理失败';
  }
  event.target.value = '';
}

async function submitNewVoice() {
  if (!S.newVoiceAudioData) { showToast('请先上传音频', 'error'); return; }
  var nameInput = document.getElementById('newVoiceName');
  var name = nameInput ? nameInput.value.trim() : '';
  if (!name) { showToast('请输入音源名称', 'error'); return; }

  var newSource = {
    id: hexId(),
    name: name,
    audioBase64: S.newVoiceAudioData.dataUrl,
    nvReferenceId: null,
    kkVoiceId: null,
    addedAt: Date.now(),
    lastSyncAt: null
  };
  S.audioSources.push(newSource);
  saveAudioSources();
  hideNewVoiceForm();
  renderSettingsVoiceList();
  renderSpeakerAssignmentList();
  showToast('音源 "' + name + '" 已创建', 'success');
}

function exportVoices() {
  var exportData = {
    version: APP_VERSION,
    voices: S.audioSources.map(function(src) {
      return { id: src.id, name: src.name, audioBase64: src.audioBase64, nvReferenceId: src.nvReferenceId, kkVoiceId: src.kkVoiceId, addedAt: src.addedAt, lastSyncAt: src.lastSyncAt };
    })
  };
  downloadBlob(new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' }), 'tts-voice-lab-voices.json');
  showToast('音源已导出', 'success');
}

function importVoices(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    try {
      var data = JSON.parse(e.target.result);
      var voices = data.voices || [];
      var imported = 0;
      voices.forEach(function(v) {
        // Skip duplicates by name
        if (!S.audioSources.find(function(s) { return s.name === v.name; })) {
          S.audioSources.push({
            id: v.id || hexId(),
            name: v.name,
            audioBase64: v.audioBase64 || v.dataUrl,
            nvReferenceId: v.nvReferenceId || null,
            kkVoiceId: v.kkVoiceId || null,
            addedAt: v.addedAt || Date.now(),
            lastSyncAt: v.lastSyncAt || null
          });
          imported++;
        }
      });
      saveAudioSources();
      renderSettingsVoiceList();
      renderSpeakerAssignmentList();
      showToast('导入 ' + imported + ' 个音源（跳过 ' + (voices.length - imported) + ' 个重复）', 'success');
    } catch(err) { showToast('导入失败: ' + err.message, 'error'); }
  };
  reader.readAsText(file);
  event.target.value = '';
}

function deleteAudioSource(id) {
  S.audioSources = S.audioSources.filter(function(s) { return s.id !== id; });
  if (S.activeSourceId === id) S.activeSourceId = '';
  saveAudioSources();
  renderSettingsVoiceList();
  renderSpeakerAssignmentList();
  showToast('已删除音源', 'info');
}

// ==================== Audio Upload & Preview ====================
// These functions are kept for internal use by speaker voice handling
function handleFileUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  loadAudioFile(file);
  event.target.value = '';
}

function handleAudioDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  var files = event.dataTransfer.files;
  if (files.length > 0 && files[0].type.startsWith('audio/')) {
    loadAudioFile(files[0]);
  }
}

function loadAudioFile(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    var dataUrl = e.target.result;
    var base64 = dataUrl.split(',')[1];
    // Store as temporary data (used by internal functions)
    S.newVoiceAudioData = { dataUrl: dataUrl, base64: base64, wavBlob: null, fileName: file.name };
    showToast('已加载音频: ' + file.name + '，正在优化...', 'info');
    trimAndOptimizeAudio(dataUrl, file.name);
  };
  reader.readAsDataURL(file);
}

async function trimAndOptimizeAudio(dataUrl, fileName) {
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    var resp = await fetch(dataUrl);
    var arrayBuffer = await resp.arrayBuffer();
    var decoded = await ctx.decodeAudioData(arrayBuffer);
    var duration = decoded.duration;
    var trimDuration = Math.min(duration, 15);
    var trimSamples = Math.floor(trimDuration * 24000);
    var channelData = decoded.getChannelData(0);
    if (trimSamples < channelData.length) {
      channelData = channelData.slice(0, trimSamples);
    }
    var trimBuffer = ctx.createBuffer(1, channelData.length, 24000);
    trimBuffer.copyToChannel(channelData, 0);
    var wavBlob = audioBufferToWav(trimBuffer);
    ctx.close();

    var reader2 = new FileReader();
    reader2.onload = function(ev) {
      var optDataUrl = ev.target.result;
      var optBase64 = optDataUrl.split(',')[1];
      // Update the temp voice data
      if (S.newVoiceAudioData && S.newVoiceAudioData.fileName === fileName) {
        S.newVoiceAudioData = { dataUrl: optDataUrl, base64: optBase64, wavBlob: wavBlob, fileName: fileName };
      }
      var sizeMB = (wavBlob.size / 1024 / 1024).toFixed(1);
      showToast('音频已优化（' + trimDuration.toFixed(1) + '秒，' + sizeMB + 'MB）', 'success');
    };
    reader2.readAsDataURL(wavBlob);
  } catch(err) {
    showToast('音频优化失败，使用原始文件', 'info');
  }
}

// updateAudioUI, clearAudio, switchAudioSource removed - no longer needed without Card 1

// ==================== Text Processing ====================
function updateTextStats() {
  var text = E.textInput.value;
  var chars = text.length;
  var lines = text ? text.split('\\n').length : 0;
  E.charCount.textContent = chars;
  E.lineCount.textContent = lines;
  var maxChars = (S.config.nvMaxChars || 150);
  // Detect speakers first
  detectSpeakers(text);
  // Split text for segment count
  if (S.speakerMode === 'multi') {
    var totalSegs = 0;
    var spSegs = splitTextBySpeakers(text, maxChars);
    for (var si = 0; si < spSegs.length; si++) totalSegs += spSegs[si].segments.length;
    E.segCount.textContent = totalSegs;
  } else {
    var segs = splitTextForTTS(text, maxChars);
    E.segCount.textContent = segs.length;
  }
}

// ==================== Speaker Detection & Parsing ====================
// v2.21: prefixes that look like labels, not speakers ("标题：" etc.), plus
// pure numbers/times ("12：", "12:30"). Only >=2 DISTINCT valid prefixes
// trigger multi-speaker mode.
var SPEAKER_META_WORDS = ['标题','备注','链接','地址','时间','日期','地点','电话','价格','原价','现价','规格','品牌','型号','注意','提示','简介','摘要','关键词','标签','正文','参考','来源','时长','大小','名称','背景','重点','卖点','成分','产地','用法','功效','保质期'];
function isMetaSpeakerName(name) {
  if (!name) return true;
  var n = name.replace(/[\\s\\d.。:：,%%，、-]+/g, '');
  if (!n) return true; // pure digits / time-like ("12:30" -> "12")
  for (var i = 0; i < SPEAKER_META_WORDS.length; i++) {
    if (n === SPEAKER_META_WORDS[i]) return true;
  }
  return false;
}
var SPEAKER_COLORS = ['#a29bfe', '#55efc4', '#74b9ff', '#fdcb6e', '#e17055', '#fd79a8', '#6c5ce7', '#00b894'];

function getSpeakerPatterns() {
  var patterns = [];
  // Built-in 【name】 pattern
  if (S.config.spBracket !== false) {
    patterns.push({ regex: /^【(.+?)】\\s*/, name: '【姓名】' });
  }
  // Built-in name: pattern
  if (S.config.spColon !== false) {
    patterns.push({ regex: /^([^\\s：:]{1,8})[：:]\\s*/, name: '姓名：' });
  }
  // Custom patterns
  var customs = S.config.spCustomPatterns || [];
  for (var ci = 0; ci < customs.length; ci++) {
    try {
      patterns.push({ regex: new RegExp(customs[ci]), name: '自定义', custom: true });
    } catch(e) {}
  }
  return patterns;
}

function detectSpeakers(text) {
  if (!text || !text.trim()) {
    S.speakerMode = 'single';
    S.detectedSpeakers = [];
    updateSpeakerUI();
    return;
  }

  var patterns = getSpeakerPatterns();
  if (patterns.length === 0) {
    S.speakerMode = 'single';
    S.detectedSpeakers = [];
    updateSpeakerUI();
    return;
  }

  var lines = text.split('\\n');
  var speakerMap = {};
  var currentSpeaker = null;
  var firstSpeakerFound = false;

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var matched = false;

    for (var pi = 0; pi < patterns.length; pi++) {
      var match = line.match(patterns[pi].regex);
      if (match && match[1]) {
        var name = match[1].trim();
        if (name && name.length <= 8 && name.length > 0 && !isMetaSpeakerName(name)) {
          currentSpeaker = name;
          firstSpeakerFound = true;
          var content = line.replace(patterns[pi].regex, '').trim();
          if (!speakerMap[name]) speakerMap[name] = { name: name, lineCount: 0, charCount: 0, markedCount: 0, isBracket: patterns[pi].name === '【姓名】' };
          speakerMap[name].lineCount++;
          speakerMap[name].markedCount++;
          speakerMap[name].charCount += content.length;
          matched = true;
          break;
        }
      }
    }

    if (!matched && firstSpeakerFound && currentSpeaker) {
      // Line without speaker marker = continuation of previous speaker
      speakerMap[currentSpeaker].lineCount++;
      speakerMap[currentSpeaker].charCount += line.trim().length;
    }
  }

  // v2.21: colon-marked names must appear on >= 2 MARKED lines (real dialogue
  // alternates repeatedly). One-off colon prefixes are labels in normal copy
  // ("正值618大促：全场五折"), not speakers. 【bracket】names are explicit
  // intent and always qualify.
  var speakers = [];
  var allNames = Object.values(speakerMap);
  for (var qi = 0; qi < allNames.length; qi++) {
    var spq = allNames[qi];
    if (spq.isBracket || spq.markedCount >= 2) speakers.push(spq);
  }
  if (speakers.length >= 2) {
    // v2.21: >=2 distinct valid names -> genuine multi-speaker dialogue
    S.speakerMode = 'multi';
    S.detectedSpeakers = speakers;
    checkSpeakerBalance(speakers);
  } else {
    // v2.21: 0 or 1 valid names -> single mode. A single "xxx：" prefix is far
    // more likely a section label than a speaker; text stays intact and the
    // full-width colon is converted to a comma by preprocessing before TTS.
    S.speakerMode = 'single';
    S.detectedSpeakers = [];
    E.speakerWarning.style.display = 'none';
  }

  updateSpeakerUI();
}

function checkSpeakerBalance(speakers) {
  var threshold = S.config.spBalanceThreshold || 5;
  if (speakers.length < 2) return;

  // Find max and min char counts
  var maxChars = 0, minChars = Infinity, maxName = '', minName = '';
  for (var i = 0; i < speakers.length; i++) {
    if (speakers[i].charCount > maxChars) { maxChars = speakers[i].charCount; maxName = speakers[i].name; }
    if (speakers[i].charCount < minChars) { minChars = speakers[i].charCount; minName = speakers[i].name; }
  }

  if (minChars > 0 && (maxChars / minChars) > threshold) {
    E.speakerWarning.style.display = 'flex';
    E.speakerWarningText.innerHTML = '<b>' + escHtml(maxName) + '</b> 的内容量（' + maxChars + '字）远多于 <b>' + escHtml(minName) + '</b>（' + minChars + '字），比例约 ' + Math.round(maxChars / minChars) + ':1。是否忘记在后续段落中标注说话人？<div class="sw-actions"><button onclick="dismissSpeakerWarning()">我已确认，继续</button></div>';
  } else {
    E.speakerWarning.style.display = 'none';
  }
}

function dismissSpeakerWarning() {
  E.speakerWarning.style.display = 'none';
}

function updateSpeakerUI() {
  var card = E.speakerCard;
  var label = E.speakerModeLabel;

  // Always show speaker card when there's text
  card.classList.add('visible');

  if (S.speakerMode === 'multi') {
    label.textContent = '多人模式（' + S.detectedSpeakers.length + '位说话人）';
    label.style.color = 'var(--green)';
    renderSpeakerAssignmentList();
  } else if (S.detectedSpeakers.length === 1) {
    label.textContent = '单人模式（检测到1位说话人标记）';
    label.style.color = 'var(--orange)';
    renderSpeakerAssignmentList();
  } else {
    label.textContent = '单人模式';
    label.style.color = 'var(--text2)';
    renderSpeakerAssignmentList();
  }

  // Update generate button validation state
  updateGenerateBtnState();
}

function renderSpeakerAssignmentList() {
  var container = E.speakerList;
  if (!container) return;

  var html = '';
  var speakers = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认', charCount: E.textInput.value.length, lineCount: E.textInput.value.split('\\n').length }];

  // Track which voices are already selected by other speakers
  var usedSourceIds = {};
  Object.keys(S.speakerAssignments).forEach(function(spName) {
    if (S.speakerAssignments[spName]) usedSourceIds[S.speakerAssignments[spName]] = spName;
  });

  for (var i = 0; i < speakers.length; i++) {
    var sp = speakers[i];
    var color = SPEAKER_COLORS[i % SPEAKER_COLORS.length];
    var assignedSource = S.speakerAssignments[sp.name] || '';

    html += '<div class="speaker-row" id="speakerRow_' + i + '">';
    html += '<span class="sp-color" style="background:' + color + '"></span>';
    html += '<span class="sp-name">' + escHtml(sp.name) + '</span>';
    if (sp.charCount !== undefined) html += '<span class="sp-stats">' + sp.charCount + '字</span>';
    html += '<select class="sp-select" data-speaker="' + escHtml(sp.name) + '" onchange="assignSpeakerVoice(this)">';
    html += '<option value="">-- 选择音源 --</option>';

    // Add saved audio sources
    for (var j = 0; j < S.audioSources.length; j++) {
      var src = S.audioSources[j];
      var sel = assignedSource === src.id ? ' selected' : '';
      // v2.20: Show which speaker uses this source, but allow re-selection
      var usedBy = usedSourceIds[src.id] && usedSourceIds[src.id] !== sp.name ? ' (' + usedSourceIds[src.id] + ')' : '';
      html += '<option value="' + escHtml(src.id) + '"' + sel + '>' + escHtml(src.name) + usedBy + '</option>';
    }

    // Add "新建音源" option
    html += '<option value="__new__">新建音源...</option>';
    html += '</select>';

    // Show assigned voice info
    if (S.speakerVoiceData[sp.name]) {
      html += '<span class="sp-preview">' + svgIcon('check') + ' 已分配</span>';
    }

    html += '</div>';

    // Inline new voice form (hidden by default)
    html += '<div class="speaker-new-voice" id="spNewVoice_' + i + '" style="display:none;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;margin:4px 0 8px ' + (sp.name === '默认' ? '0' : '24') + 'px">';
    html += '<div style="display:flex;gap:8px;margin-bottom:8px"><input type="text" id="spVoiceName_' + i + '" placeholder="音源名称" style="flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>';
    html += '<div class="upload-zone" id="spUploadZone_' + i + '" onclick="document.getElementById(\\'spVoiceFile_' + i + '\\').click()" style="padding:12px;cursor:pointer">';
    html += '<div class="uz-text" id="spUploadText_' + i + '">点击上传参考音频</div>';
    html += '</div>';
    html += '<input type="file" id="spVoiceFile_' + i + '" accept="audio/*" style="display:none" onchange="handleSpVoiceFileUpload(event, ' + i + ', \\'' + escHtml(sp.name) + '\\')">';
    html += '<div style="display:flex;gap:8px;margin-top:8px">';
    html += '<button class="clear-btn" onclick="submitSpNewVoice(' + i + ', \\'' + escHtml(sp.name) + '\\')" style="background:var(--green);color:#000;border-color:var(--green)"><svg class="ic" aria-hidden="true"><use href="#i-check"></use></svg> 提交</button>';
    html += '<button class="clear-btn" onclick="cancelSpNewVoice(' + i + ')">取消</button>';
    html += '</div></div>';
  }

  container.innerHTML = html;
}

function assignSpeakerVoice(selectEl) {
  var speakerName = selectEl.getAttribute('data-speaker');
  var value = selectEl.value;

  if (value === '__new__') {
    // Show inline new voice form for this speaker
    var idx = (S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }]).findIndex(function(s) { return s.name === speakerName; });
    var form = document.getElementById('spNewVoice_' + idx);
    if (form) form.style.display = 'block';
    selectEl.value = S.speakerAssignments[speakerName] || '';
    return;
  }

  if (value) {
    S.speakerAssignments[speakerName] = value;
    // Load the audio source data for this speaker
    var src = S.audioSources.find(function(s) { return s.id === value; });
    if (src) {
      S.speakerVoiceData[speakerName] = buildVoiceDataFromSource(src);
    }
  } else {
    delete S.speakerAssignments[speakerName];
    delete S.speakerVoiceData[speakerName];
  }

  updateGenerateBtnState();
  // Re-render to update disabled states on other selects
  renderSpeakerAssignmentList();
}

// Temp storage for inline voice uploads per speaker
var _spVoiceTempData = {};

async function handleSpVoiceFileUpload(event, idx, speakerName) {
  var file = event.target.files[0];
  if (!file) return;
  var uploadText = document.getElementById('spUploadText_' + idx);
  if (uploadText) uploadText.textContent = '正在处理...';

  try {
    var dataUrl = await new Promise(function(resolve) {
      var reader = new FileReader();
      reader.onload = function(e) { resolve(e.target.result); };
      reader.readAsDataURL(file);
    });

    var base64 = dataUrl.split(',')[1];

    // Compress: resample to 24kHz, trim to 15s
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      var resp = await fetch(dataUrl);
      var arrayBuffer = await resp.arrayBuffer();
      var decoded = await ctx.decodeAudioData(arrayBuffer);
      var duration = Math.min(decoded.duration, 15);
      var trimSamples = Math.floor(duration * 24000);
      var channelData = decoded.getChannelData(0);
      if (trimSamples < channelData.length) channelData = channelData.slice(0, trimSamples);
      var trimBuffer = ctx.createBuffer(1, channelData.length, 24000);
      trimBuffer.copyToChannel(channelData, 0);
      var wavBlob = audioBufferToWav(trimBuffer);
      ctx.close();

      var optDataUrl = await new Promise(function(resolve) {
        var reader2 = new FileReader();
        reader2.onload = function(e) { resolve(e.target.result); };
        reader2.readAsDataURL(wavBlob);
      });

      _spVoiceTempData[idx] = { dataUrl: optDataUrl, base64: optDataUrl.split(',')[1], wavBlob: wavBlob, fileName: file.name };
    } catch(e) {
      _spVoiceTempData[idx] = { dataUrl: dataUrl, base64: base64, wavBlob: null, fileName: file.name };
    }

    if (uploadText) uploadText.textContent = svgIcon('check') + ' ' + file.name;
  } catch(e) {
    if (uploadText) uploadText.textContent = '处理失败，请重试';
  }
  event.target.value = '';
}

async function submitSpNewVoice(idx, speakerName) {
  var tempData = _spVoiceTempData[idx];
  if (!tempData) { showToast('请先上传音频', 'error'); return; }

  var voiceNameEl = document.getElementById('spVoiceName_' + idx);
  var voiceName = voiceNameEl ? voiceNameEl.value.trim() : '';
  if (!voiceName) voiceName = speakerName + '音色';

  // Save to audio sources
  var newSource = {
    id: hexId(),
    name: voiceName,
    audioBase64: tempData.dataUrl,
    nvReferenceId: null,
    kkVoiceId: null,
    addedAt: Date.now(),
    lastSyncAt: null
  };
  S.audioSources.push(newSource);
  saveAudioSources();

  // Assign to speaker
  S.speakerAssignments[speakerName] = newSource.id;
  S.speakerVoiceData[speakerName] = {
    audioFile: { name: voiceName + '.wav', dataUrl: tempData.dataUrl, base64: tempData.base64, wavBlob: tempData.wavBlob },
    nvReferenceId: null,
    kkVoiceId: null
  };

  delete _spVoiceTempData[idx];
  showToast('音源 "' + voiceName + '" 已创建并分配给 ' + speakerName, 'success');
  renderSpeakerAssignmentList();
  renderSettingsVoiceList();
  updateGenerateBtnState();
}

function cancelSpNewVoice(idx) {
  var form = document.getElementById('spNewVoice_' + idx);
  if (form) form.style.display = 'none';
  delete _spVoiceTempData[idx];
}

function updateGenerateBtnState() {
  var btn = E.generateBtn;
  // Check if all speakers (including 默认 in single mode) have voices assigned
  var speakersToCheck = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }];
  var allAssigned = true;
  for (var i = 0; i < speakersToCheck.length; i++) {
    var sp = speakersToCheck[i];
    if (!S.speakerVoiceData[sp.name] && !S.speakerAssignments[sp.name]) {
      allAssigned = false;
      break;
    }
  }
  if (!allAssigned) {
    btn.style.opacity = '0.6';
    btn.title = '请为所有说话人分配音源';
  } else {
    btn.style.opacity = '1';
    btn.title = '';
  }
}

// ==================== Speaker-Aware Text Splitting ====================
function splitTextBySpeakers(text, maxChars) {
  // Returns array of { speaker, segments: [{text, lines, segIndex}] }
  if (!text || !text.trim()) return [];

  var patterns = getSpeakerPatterns();
  // v2.21: only names qualified by detectSpeakers may start a speaker block
  var qualifiedNames = {};
  for (var qi2 = 0; qi2 < S.detectedSpeakers.length; qi2++) qualifiedNames[S.detectedSpeakers[qi2].name] = true;
  var lines = text.split('\\n');
  var currentSpeaker = null;
  var speakerBlocks = []; // { speaker, lines: [{text, isContinuation}] }

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var matched = false;

    for (var pi = 0; pi < patterns.length; pi++) {
      var match = line.match(patterns[pi].regex);
      if (match && match[1]) {
        var name = match[1].trim();
        if (name && name.length <= 8 && !isMetaSpeakerName(name) && qualifiedNames[name]) {
          currentSpeaker = name;
          var content = line.replace(patterns[pi].regex, '').trim();
          if (content) {
            speakerBlocks.push({ speaker: name, text: content });
          }
          matched = true;
          break;
        }
      }
    }

    if (!matched && line.trim()) {
      // Continuation of previous speaker
      if (currentSpeaker) {
        speakerBlocks.push({ speaker: currentSpeaker, text: line.trim() });
      } else {
        // No speaker context yet, treat as default
        speakerBlocks.push({ speaker: null, text: line.trim() });
      }
    }
  }

  // Group consecutive blocks of the same speaker and split by maxChars
  var result = [];
  var currentGroup = null;

  for (var bi = 0; bi < speakerBlocks.length; bi++) {
    var block = speakerBlocks[bi];
    if (!currentGroup || currentGroup.speaker !== block.speaker) {
      if (currentGroup) result.push(currentGroup);
      currentGroup = { speaker: block.speaker, rawText: block.text, lines: [block.text] };
    } else {
      currentGroup.rawText += '\\n' + block.text;
      currentGroup.lines.push(block.text);
    }
  }
  if (currentGroup) result.push(currentGroup);

  // Now split each group's text into TTS segments
  for (var gi = 0; gi < result.length; gi++) {
    var group = result[gi];
    var segs = splitTextForTTS(group.rawText, maxChars);
    group.segments = segs;
    // Tag each segment with the speaker
    for (var si = 0; si < segs.length; si++) {
      segs[si].speaker = group.speaker;
    }
  }

  return result;
}

// Speaker pattern management
function addSpeakerPattern() {
  var input = document.getElementById('newSpeakerPattern');
  var pattern = input.value.trim();
  if (!pattern) { showToast('请输入正则表达式', 'error'); return; }
  try {
    new RegExp(pattern); // validate
  } catch(e) {
    showToast('正则表达式无效: ' + e.message, 'error');
    return;
  }
  if (!S.config.spCustomPatterns) S.config.spCustomPatterns = [];
  S.config.spCustomPatterns.push(pattern);
  saveConfig();
  renderSpeakerPatterns();
  input.value = '';
  showToast('已添加自定义说话人模式', 'success');
}

function removeSpeakerPattern(idx) {
  if (S.config.spCustomPatterns) {
    S.config.spCustomPatterns.splice(idx, 1);
    saveConfig();
    renderSpeakerPatterns();
  }
}

// ==================== Number/Symbol Preprocessing ====================
function numberToChinese(numStr) {
  var num = parseInt(numStr, 10);
  if (isNaN(num)) return numStr;
  if (num === 0) return '零';
  var digits = ['零','一','二','三','四','五','六','七','八','九'];
  var units = ['','十','百','千'];

  if (num >= 100000000) {
    var yi = Math.floor(num / 100000000);
    var rem = num % 100000000;
    var result = numberToChinese(String(yi)) + '亿';
    if (rem > 0) {
      if (rem < 10000000) result += '零';
      result += numberToChinese(String(rem));
    }
    return result;
  }
  if (num >= 10000) {
    var wan = Math.floor(num / 10000);
    var rem = num % 10000;
    var result = numberToChinese(String(wan)) + '万';
    if (rem > 0) {
      if (rem < 1000) result += '零';
      result += numberToChinese(String(rem));
    }
    return result;
  }

  var result = '';
  var str = String(num);
  var len = str.length;
  var hasZero = false;
  for (var i = 0; i < len; i++) {
    var d = parseInt(str[i], 10);
    var unitIdx = len - 1 - i;
    if (d === 0) {
      hasZero = true;
    } else {
      if (hasZero) { result += '零'; hasZero = false; }
      result += digits[d] + units[unitIdx];
    }
  }
  // Special case: 10-19 should be 十... not 一十...
  if (num >= 10 && num < 20 && result.startsWith('一十')) {
    result = result.substring(1);
  }
  return result;
}

function numberToChineseYear(numStr) {
  // Read each digit individually for year-like numbers
  var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
  var result = '';
  for (var i = 0; i < numStr.length; i++) {
    var d = parseInt(numStr[i], 10);
    if (!isNaN(d)) result += digitMap[d];
    else result += numStr[i];
  }
  return result;
}

// v2.21: brand/marketing terms that must NOT be read as plain cardinal numbers.
// Applied before number rules; context-anchored to avoid false hits (e.g. 价格618元).
var NV_BRAND_TERMS = [
  [/618(大促|年中|狂欢|活动|好物节|开门红|晚会|预热|爆款|专场|盛典|购物节)/g, '六一八$1'],
  [/520(告白|大促|活动|专场|盛典|礼物节)/g, '五二零$1'],
  [/双11/g, '双十一'],
  [/双12/g, '双十二'],
  [/双旦/g, '双旦']
];

// ==================== v2.22: Toggleable TTS text rules ====================
// Built-in rules are listed in the settings panel (设置 -> 读音替换规则) and
// can each be switched off by the user. User rules run first (highest
// priority); built-in data rules follow in processing order.
// v2.22.1: builtin rules are DATA now. kind:'data' rules carry a live
// pattern/replacement the user may edit; kind:'action' rules are code
// behaviour and only expose name/desc/switch. DEFAULT_BUILTIN_RULES stays
// frozen for the 复原默认 button; the mutable copy lives in S.config.builtinRules.
var DEFAULT_BUILTIN_RULES = [
  { id: 'quote-comma',    kind: 'data',   type: 'regex', name: '引号转停顿', pattern: '[“”„‘’]', replacement: '，', desc: '引号转逗号，防止引号内容被拆词' },
  { id: 'brand-terms',    kind: 'action', name: '品牌词表', desc: '618大促→六一八大促、双11→双十一等' },
  { id: 'num-reading',    kind: 'action', name: '数字读法', desc: '数位转换(7000→七千)、年份/电话逐字读' },
  { id: 'symbol-transit', kind: 'action', name: '符号转读', desc: '顿号/书名号/破折号/加乘等转读法' },
  { id: 'colon-comma',    kind: 'data',   type: 'regex', name: '冒号转逗号', pattern: '：', replacement: '，', desc: '全角冒号转逗号，防止误判说话人' },
  { id: 'punct-collapse', kind: 'action', name: '标点清理', desc: '连续标点去重、句尾弱标点升级句号' },
  { id: 'sentence-space', kind: 'data',   type: 'regex', name: '句末空格', pattern: '([。！？])(?=[^\\\\s。，、；：！？…,;:!?"\\x27])', replacement: '$1 ', desc: '句号/问号/叹号后补空格强化句子边界' }
];
function ensureBuiltinRules() {
  if (!S.config.builtinRules || !S.config.builtinRules.length) {
    S.config.builtinRules = JSON.parse(JSON.stringify(DEFAULT_BUILTIN_RULES));
    var flags = S.config.ttsRuleFlags || {};
    for (var i = 0; i < S.config.builtinRules.length; i++) {
      if (flags[S.config.builtinRules[i].id] === false) S.config.builtinRules[i].enabled = false;
    }
  }
  for (var j = 0; j < S.config.builtinRules.length; j++) {
    if (S.config.builtinRules[j].enabled === undefined) S.config.builtinRules[j].enabled = true;
  }
}
function getBuiltinRule(id) {
  ensureBuiltinRules();
  for (var i = 0; i < S.config.builtinRules.length; i++) {
    if (S.config.builtinRules[i].id === id) return S.config.builtinRules[i];
  }
  return null;
}
function isRuleEnabled(id) {
  var r = getBuiltinRule(id);
  if (r) return r.enabled !== false;
  var flags = S.config.ttsRuleFlags;
  if (!flags) return true;
  return flags[id] !== false;
}
function applyDataRule(text, rule) {
  if (!rule || rule.enabled === false || !rule.pattern) return text;
  var pat;
  try {
    pat = rule.type === 'wildcard' ? wildcardToRegex(rule.pattern) : (rule.type === 'text' ? escapeRegExp(rule.pattern) : rule.pattern);
    return text.replace(new RegExp(pat, 'g'), rule.replacement || '');
  } catch(e) {
    console.warn('[RULE] invalid builtin rule skipped:', rule.id, e.message);
    return text;
  }
}
function escapeRegExp(s) {
  return String(s).replace(/[.*+?^\${}()|[\\]\\\\]/g, '\\\\$&');
}
function wildcardToRegex(wc) {
  var out = '';
  for (var i = 0; i < wc.length; i++) {
    var c = wc.charAt(i);
    if (c === '*') out += '[^，。！？；、,;.!?\\n]*';
    else if (c === '?') out += '[^\\n]';
    else out += escapeRegExp(c);
  }
  return out;
}
// v2.22: user-defined rules (type: text | wildcard | regex | llm).
// regex/wildcard/text run here; llm rules are injected into the GLM prompt.
function applyUserTtsRules(text) {
  var rules = S.config.ttsRules;
  if (!rules || !rules.length) return text;
  for (var i = 0; i < rules.length; i++) {
    var r = rules[i];
    if (r.enabled === false || r.type === 'llm') continue;
    try {
      var pat = r.type === 'wildcard' ? wildcardToRegex(r.pattern) : (r.type === 'text' ? escapeRegExp(r.pattern) : r.pattern);
      text = text.replace(new RegExp(pat, 'g'), r.replacement || '');
    } catch(e) {
      console.warn('[RULE] invalid rule skipped:', r.name, e.message);
    }
  }
  return text;
}
function hasEnabledLlmRules() {
  var rules = S.config.ttsRules;
  if (!rules) return false;
  for (var i = 0; i < rules.length; i++) {
    if (rules[i].type === 'llm' && rules[i].enabled !== false) return true;
  }
  return false;
}
function buildLlmRulesPrompt() {
  if (!hasEnabledLlmRules()) return '';
  var lines = [];
  var rules = S.config.ttsRules;
  for (var i = 0; i < rules.length; i++) {
    var r = rules[i];
    if (r.type !== 'llm' || r.enabled === false) continue;
    lines.push((lines.length + 1) + '. ' + r.pattern);
  }
  return '\\n\\n【用户自定义读音规则】以下规则由用户逐条定义，优先级最高，必须严格执行，除此之外不要改动原文：\\n' + lines.join('\\n');
}
function svgIcon(n) { return '<svg class="ic" aria-hidden="true"><use href="#i-' + n + '"></use></svg>'; }
function esc4html(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
// v2.22.1: unified rule rendering. builtin + custom share one row model
// (switch / name / content / type badge), every field click-to-edit with
// blur-to-save. ruleEditing tracks the row being edited.
var ruleEditing = null; // {kind:'builtin'|'user', idx, field:'name'|'content'}
function ruleByIdx(kind, idx) {
  if (kind === 'builtin') { ensureBuiltinRules(); return S.config.builtinRules[idx]; }
  return (S.config.ttsRules || [])[idx];
}
function beginRuleEdit(kind, idx, field, ev) {
  if (ev && ev.target) {
    var tg = ev.target.tagName;
    if (tg === 'INPUT' || tg === 'BUTTON' || tg === 'SELECT') return;
  }
  ruleEditing = { kind: kind, idx: idx, field: field };
  renderTtsRules();
  var z = document.getElementById('ruleEditZone');
  if (z) { var fi = z.querySelector('input'); if (fi) { fi.focus(); if (fi.select) fi.select(); } }
}
function ruleEditBlur() {
  setTimeout(function() {
    if (!ruleEditing) return;
    var ae = document.activeElement;
    if (ae && ae.tagName === 'INPUT') return; // focus still inside editor
    commitRuleEdit();
  }, 80);
}
// v2.22.1: click anywhere outside the open editor commits it (capture phase
// runs before the next row's own click handler, so switching rows saves first).
(function() {
  document.addEventListener('click', function(e) {
    if (!ruleEditing) return;
    var t = e.target;
    if (t.closest && (t.closest('.rule-edit-wrap') || t.closest('.rr-name') || t.closest('.rr-pat'))) return;
    commitRuleEdit();
  }, true);
})();
function ruleEditKey(e) {
  if (e.key === 'Enter') { e.preventDefault(); commitRuleEdit(); }
  else if (e.key === 'Escape') { ruleEditing = null; renderTtsRules(); }
}
function commitRuleEdit() {
  if (!ruleEditing) return;
  var r = ruleByIdx(ruleEditing.kind, ruleEditing.idx);
  var edit = document.getElementById('ruleEditZone');
  if (r && edit) {
    var bad = false;
    if (ruleEditing.field === 'name') {
      var ni = edit.querySelector('input[data-f="name"]');
      if (ni && ni.value.trim()) r.name = ni.value.trim();
    } else {
      var isData = (ruleEditing.kind === 'user') || (r.kind === 'data');
      if (isData) {
        var pi = edit.querySelector('input[data-f="pattern"]');
        var ri = edit.querySelector('input[data-f="replacement"]');
        var ptype = (ruleEditing.kind === 'user') ? (r.type || 'text') : (r.type || 'regex');
        if (pi && ptype === 'regex' && pi.value) {
          try { new RegExp(pi.value); } catch(e2) { showToast('正则无效，未保存: ' + e2.message, 'error'); bad = true; }
        }
        if (!bad && pi) r.pattern = pi.value;
        if (!bad && ri) r.replacement = ri.value;
      }
      if (!bad) {
        var di = edit.querySelector('input[data-f="desc"]');
        if (di && ruleEditing.kind === 'builtin') r.desc = di.value;
      }
    }
  }
  ruleEditing = null;
  if (!bad) { saveConfig(); renderTtsRules(); }
}
function renderRuleRow(kind, idx, r) {
  var on = r.enabled !== false;
  var editing = ruleEditing && ruleEditing.kind === kind && ruleEditing.idx === idx;
  var h = '<div class="rule-row">';
  h += '<input type="checkbox" class="rr-on" ' + (on ? 'checked' : '') + ' onchange="toggleRule(\\'' + kind + '\\',' + idx + ', this.checked)">';
  if (editing && ruleEditing.field === 'name') {
    h += '<span class="rule-edit-wrap" id="ruleEditZone"><input class="rr-edit" data-f="name" value="' + esc4html(r.name || '') + '" placeholder="规则名称" onblur="ruleEditBlur()" onkeydown="ruleEditKey(event)"></span>';
  } else {
    h += '<span class="rr-name" title="点击修改规则名称" onclick="beginRuleEdit(\\'' + kind + '\\',' + idx + ',\\'name\\', event)">' + esc4html(r.name || '规则' + (idx + 1)) + '</span>';
  }
  var isAction = (kind === 'builtin' && r.kind === 'action');
  if (editing && ruleEditing.field === 'content') {
    h += '<span class="rule-edit-wrap" id="ruleEditZone">';
    if (isAction) {
      h += '<input class="rr-edit" data-f="desc" value="' + esc4html(r.desc || '') + '" onblur="ruleEditBlur()" onkeydown="ruleEditKey(event)">';
      h += '<span class="rule-hint">程序行为规则：此处仅修改说明文字，停用开关立即生效</span>';
    } else if (r.type === 'llm') {
      h += '<input class="rr-edit" data-f="pattern" value="' + esc4html(r.pattern || '') + '" placeholder="GLM 改写指令" onblur="ruleEditBlur()" onkeydown="ruleEditKey(event)">';
    } else {
      h += '<span class="rule-edit-row"><input class="rr-edit mono" data-f="pattern" value="' + esc4html(r.pattern || '') + '" placeholder="匹配内容" onblur="ruleEditBlur()" onkeydown="ruleEditKey(event)"><span>→</span><input class="rr-edit mono" data-f="replacement" value="' + esc4html(r.replacement || '') + '" placeholder="替换为（可空）" onblur="ruleEditBlur()" onkeydown="ruleEditKey(event)"></span>';
    }
    h += '</span>';
  } else {
    var content, title;
    if (isAction) { content = r.desc || ''; title = '程序行为规则，点击修改说明文字'; }
    else if (r.type === 'llm') { content = r.pattern || ''; title = '点击修改 GLM 指令'; }
    else { content = (r.pattern || '') + ' → ' + (r.replacement || '(删除)'); title = '点击修改匹配内容与替换内容'; }
    h += '<span class="rr-pat" title="' + esc4html(title) + '" onclick="beginRuleEdit(\\'' + kind + '\\',' + idx + ',\\'content\\', event)">' + esc4html(content) + '</span>';
  }
  var typeLabel = kind === 'builtin'
    ? (r.kind === 'data' ? ({ text: '文本', wildcard: '通配', regex: '正则' }[r.type] || r.type) + '·内置' : '内置')
    : ({ text: '文本', wildcard: '通配', regex: '正则', llm: 'GLM' }[r.type] || r.type);
  h += '<span class="rr-type">' + typeLabel + '</span>';
  if (kind === 'user' && r.type === 'llm' && on && (!S.config.glmApiKey || (S.config.glmPreprocess || 'off') === 'off')) {
    h += '<span class="rr-warn" title="未生效：需在下方配置 GLM API Key，并将智能预处理设为 回退/始终">未生效</span>';
  }
  if (kind === 'user') h += '<button class="rr-del" title="删除此规则" onclick="removeUserTtsRule(' + idx + ')">' + svgIcon('x') + '</button>';
  h += '</div>';
  return h;
}
function renderTtsRules() {
  var bl = document.getElementById('builtinRulesList');
  var cl = document.getElementById('customRulesList');
  ensureBuiltinRules();
  if (bl) {
    var h = '';
    for (var i = 0; i < S.config.builtinRules.length; i++) h += renderRuleRow('builtin', i, S.config.builtinRules[i]);
    bl.innerHTML = h;
  }
  if (cl) {
    var rules = S.config.ttsRules || [];
    var h2 = rules.length ? '' : '<div style="font-size:11px;color:var(--text2);padding:4px 0">暂无自定义规则</div>';
    for (var j = 0; j < rules.length; j++) h2 += renderRuleRow('user', j, rules[j]);
    cl.innerHTML = h2;
  }
}
function toggleRule(kind, idx, on) {
  var r = ruleByIdx(kind, idx);
  if (r) { r.enabled = !!on; saveConfig(); }
}
function removeUserTtsRule(idx) {
  if (S.config.ttsRules) { S.config.ttsRules.splice(idx, 1); saveConfig(); renderTtsRules(); }
}
function addUserTtsRule() {
  var nEl = document.getElementById('newRuleName');
  var pEl = document.getElementById('newRulePattern');
  var rEl = document.getElementById('newRuleReplacement');
  var tEl = document.getElementById('newRuleType');
  var name = nEl ? nEl.value.trim() : '';
  var pattern = pEl ? pEl.value.trim() : '';
  var replacement = rEl ? rEl.value : '';
  var type = tEl ? tEl.value : 'text';
  if (!pattern) { showToast('请输入匹配内容或 GLM 指令', 'error'); return; }
  if (type === 'regex') {
    try { new RegExp(pattern); } catch(e) { showToast('正则无效: ' + e.message, 'error'); return; }
  }
  if (!S.config.ttsRules) S.config.ttsRules = [];
  S.config.ttsRules.push({ name: name || pattern.substring(0, 10), type: type, pattern: pattern, replacement: replacement, enabled: true });
  saveConfig();
  renderTtsRules();
  if (nEl) nEl.value = '';
  if (pEl) pEl.value = '';
  if (rEl) rEl.value = '';
  showToast(type === 'llm' ? 'GLM 规则已添加（需配置 Key 并开启智能预处理）' : '规则已添加', 'success');
}
function resetBuiltinRules() {
  if (!confirm('将内置规则恢复为默认（名称、开关、匹配与替换内容）？自定义规则不受影响。')) return;
  S.config.builtinRules = JSON.parse(JSON.stringify(DEFAULT_BUILTIN_RULES));
  S.config.ttsRuleFlags = {};
  saveConfig();
  renderTtsRules();
  showToast('内置规则已恢复默认', 'success');
}
function exportRules() {
  ensureBuiltinRules();
  var data = { type: 'tts-voice-lab-rules', version: APP_VERSION, exportedAt: new Date().toISOString(), builtinRules: S.config.builtinRules, userRules: S.config.ttsRules || [] };
  var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'tts-rules-' + new Date().toISOString().slice(0, 10) + '.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function() { URL.revokeObjectURL(a.href); }, 1000);
}
function importRules(ev) {
  var f = ev.target && ev.target.files && ev.target.files[0];
  if (!f) return;
  var reader = new FileReader();
  reader.onload = function() {
    try {
      var d = JSON.parse(reader.result);
      if (!d || d.type !== 'tts-voice-lab-rules') { showToast('文件格式不符（应为规则导出文件）', 'error'); return; }
      var merged = 0, uc = 0;
      if (Array.isArray(d.builtinRules)) {
        S.config.builtinRules = JSON.parse(JSON.stringify(DEFAULT_BUILTIN_RULES));
        for (var i = 0; i < S.config.builtinRules.length; i++) {
          for (var k = 0; k < d.builtinRules.length; k++) {
            if (d.builtinRules[k] && d.builtinRules[k].id === S.config.builtinRules[i].id) {
              var src = d.builtinRules[k];
              var fields = ['name', 'pattern', 'replacement', 'desc', 'type'];
              for (var fi = 0; fi < fields.length; fi++) {
                if (typeof src[fields[fi]] !== 'undefined') S.config.builtinRules[i][fields[fi]] = src[fields[fi]];
              }
              S.config.builtinRules[i].enabled = src.enabled !== false;
              merged++; break;
            }
          }
        }
      }
      if (Array.isArray(d.userRules)) {
        S.config.ttsRules = [];
        for (var u = 0; u < d.userRules.length; u++) {
          var ur = d.userRules[u];
          if (!ur || (!ur.pattern && ur.type !== 'llm')) continue;
          var t = ['text', 'wildcard', 'regex', 'llm'].indexOf(ur.type) >= 0 ? ur.type : 'text';
          if (t === 'regex' && ur.pattern) { try { new RegExp(ur.pattern); } catch(e3) { continue; } }
          S.config.ttsRules.push({ name: ur.name || '导入规则' + (u + 1), type: t, pattern: String(ur.pattern || ''), replacement: String(ur.replacement || ''), enabled: ur.enabled !== false });
          uc++;
        }
      }
      saveConfig();
      renderTtsRules();
      showToast('已导入：内置 ' + merged + ' 条，自定义 ' + uc + ' 条', 'success');
    } catch(e) { showToast('导入失败: ' + e.message, 'error'); }
  };
  reader.readAsText(f);
  ev.target.value = '';
}
function preprocessTextForTTS(text) {
  if (!text) return text;

  var result = text;
  var _origLen = text.length;

  // v2.22: user-defined rules run first (highest priority)
  result = applyUserTtsRules(result);

  // v2.22 rule quote-comma: CJK quotes -> comma. Live probes showed the
  // upstream engine silently drops “”, erasing the boundary; words inside
  // quotes then get re-segmented mid-word (“了不起”→“了 不起”).
  result = applyDataRule(result, getBuiltinRule('quote-comma'));

  // 0. v2.21: normalize look-alike symbols
  result = result.replace(/％/g, '%');
  result = result.replace(/[¥￥]\\s*(\\d+(?:\\.\\d+)?)/g, '$1元');

  // 0.5 v2.21: brand terms BEFORE number rules (618大促 -> 六一八大促)
  if (isRuleEnabled('brand-terms')) {
    for (var bi = 0; bi < NV_BRAND_TERMS.length; bi++) {
      result = result.replace(NV_BRAND_TERMS[bi][0], NV_BRAND_TERMS[bi][1]);
    }
  }

  if (isRuleEnabled('num-reading')) {
  // 1. Percentage patterns first: X% or X.X%
  result = result.replace(/(\\d+(?:\\.\\d+)?)\\s*%/g, function(m, num) {
    var parts = num.split('.');
    var intPart = numberToChinese(parts[0]);
    var decPart = '';
    if (parts[1]) {
      decPart = '点';
      var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
      for (var i = 0; i < parts[1].length; i++) {
        var d = parseInt(parts[1][i], 10);
        decPart += isNaN(d) ? parts[1][i] : digitMap[d];
      }
    }
    return '百分之' + intPart + decPart;
  });

  // 2. Date patterns: X月X日
  result = result.replace(/(\\d{1,2})\\s*月\\s*(\\d{1,2})\\s*[日号]/g, function(m, month, day) {
    return numberToChinese(month) + '月' + numberToChinese(day) + '日';
  });

  // 3. Year patterns: 4-digit numbers followed by 年 (digit-by-digit reading)
  result = result.replace(/(\\d{4})\\s*年/g, function(m, year) {
    return numberToChineseYear(year) + '年';
  });

  // 3.5 v2.21: year-like numbering (届/级/款/期/季/集) also read digit-by-digit
  result = result.replace(/(\\d{3,4})(?=\\s*(届|级|款|期|季|集))/g, function(m) {
    return numberToChineseYear(m);
  });

  // 4. Phone numbers: 11 digits starting with 1 (digit-by-digit)
  result = result.replace(/1[3-9]\\d{9}/g, function(m) {
    var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
    var r = '';
    for (var i = 0; i < m.length; i++) r += digitMap[parseInt(m[i], 10)];
    return r;
  });

  // 5. Decimal numbers: X.XX
  result = result.replace(/(\\d+)\\.(\\d+)/g, function(m, intPart, decPart) {
    var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
    var r = numberToChinese(intPart) + '点';
    for (var i = 0; i < decPart.length; i++) {
      var d = parseInt(decPart[i], 10);
      r += isNaN(d) ? decPart[i] : digitMap[d];
    }
    return r;
  });

  // 6. Numbers with 万/亿 (keep Chinese units, convert the number part)
  result = result.replace(/(\\d+)\\s*万/g, function(m, num) {
    return numberToChinese(num) + '万';
  });
  result = result.replace(/(\\d+)\\s*亿/g, function(m, num) {
    return numberToChinese(num) + '亿';
  });

  // 7. v2.21 FIX: all remaining multi-digit numbers -> place-value reading.
  //    (1000 -> 一千, 7000 -> 七千, 4999 -> 四千九百九十九)
  //    The old rule read ALL 4-digit numbers digit-by-digit, which broke
  //    prices/quantities ("7000套" -> "七零零零套"). Years/届级 are handled
  //    by rules 3/3.5 above; phone numbers by rule 4.
  result = result.replace(/\\d{2,}/g, function(m) {
    return numberToChinese(m);
  });

  // 8. Single digits
  result = result.replace(/\\d/g, function(m) {
    var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
    return digitMap[parseInt(m, 10)];
  });
  } // end num-reading

  if (isRuleEnabled('symbol-transit')) {
  // 9. Symbol disambiguation
  // Em dash: remove (pause)
  result = result.replace(/——/g, '');
  // Ellipsis
  result = result.replace(/……|……/g, '等等');
  // v2.14: Punctuation transit for TTS-unfriendly marks
  // 顿号 → 逗号
  result = result.replace(/、/g, '，');
  // 书名号《》→ 去除（保留书名内容）
  result = result.replace(/《/g, '').replace(/》/g, '');
  // 单个破折号 — → 逗号（双破折号 —— 已在上面处理）
  result = result.replace(/—/g, '，');
  // 竖线 | → 逗号
  result = result.replace(/\\|/g, '，');
  result = result.replace(/\\.{3,}/g, '等等');
  // v2.21: lone ellipsis char -> comma
  result = result.replace(/…/g, '，');
  // Tilde → 至/到
  result = result.replace(/～/g, '至');
  result = result.replace(/~/g, '至');
  // v2.21: full-width colon -> comma. (Speaker prefixes are stripped before
  // this point in multi mode; in single mode stray "label：" colons confuse
  // prosody and could be mistaken for speaker marks by the listener.)
  result = applyDataRule(result, getBuiltinRule('colon-comma'));
  // Hyphen/minus in range context: X-Y人, X-Y个
  result = result.replace(/([一二三四五六七八九十百千万零]+)-([一二三四五六七八九十百千万零]+)([人个条只本张架辆艘间场次块元角分])/g, function(m, a, b, unit) { return a + '到' + b + unit; });
  // Remaining hyphens in ranges with Chinese
  result = result.replace(/([一二三四五六七八九十百千万零]+)-([一二三四五六七八九十百千万零]+)/g, function(m, a, b) { return a + '到' + b; });
  // Hyphen used as dash/pause
  result = result.replace(/-/g, '');
  // Multiply
  result = result.replace(/×/g, '乘');
  // Plus
  result = result.replace(/\\+/g, '加');
  // Equals
  result = result.replace(/=/g, '等于');
  // Celsius
  result = result.replace(/℃/g, '度');
  // Degree
  result = result.replace(/°/g, '度');
  } // end symbol-transit

  // v2.22 rule punct-collapse: consecutive punctuation -> keep the strongest;
  // trailing weak punctuation at line end upgrades to a period.
  if (isRuleEnabled('punct-collapse')) {
    result = result.replace(/[，、；,;]+([。！？.!？?]+)/g, '$1');
    result = result.replace(/([。！？.!？?]+)[，、；,;]+/g, '$1');
    result = result.replace(/[，、；,;]{2,}/g, function(m2) { return m2.charAt(m2.length - 1); });
    result = result.replace(/[，、；,;]+[\\s]*$/g, '。');
  }
  // v2.22 rule sentence-space: half-width space after sentence-final marks.
  // Live probe: CJK period glued to the next word produced NO pause at all
  // (engine ignores it), then re-segmented at a random spot. A space restores
  // a hard boundary (probe C1: pause landed exactly at the period).
  // Lookahead excludes whitespace (no trailing space at line/text end) and
  // following punctuation (no space between ? and !).
  result = applyDataRule(result, getBuiltinRule('sentence-space'));

  // Safety check: if preprocessing produced an empty or suspiciously short result,
  // return the original text instead
  if (!result || (result.length < 2 && _origLen > 2)) {
    console.warn('[PREPROCESS] Suspicious output: "' + result + '" from input len=' + _origLen + ', using original text');
    return text;
  }

  if (result.length !== _origLen) {
    console.log('[PREPROCESS] len ' + _origLen + '→' + result.length + ' | "' + text.substring(0,60) + '" → "' + result.substring(0,60) + '"');
  }
  return result;
}

// GLM-powered smart text preprocessing for TTS
async function glmPreprocessText(text) {
  var apiKey = S.config.glmApiKey;
  var mode = S.config.glmPreprocess || 'off';
  if (mode === 'off' || !apiKey) return null;

  var systemPrompt = S.config.glmSystemPrompt || DEFAULT_GLM_PROMPT;
  // v2.22: inject user-defined GLM semantic rules (highest priority)
  var llmRulesBlock = buildLlmRulesPrompt();
  if (llmRulesBlock) systemPrompt = systemPrompt + llmRulesBlock;

  try {
    var resp = await fetch('/api/glm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        apiKey: apiKey,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: text }
        ]
      })
    });
    var data = await resp.json();
    if (data.choices && data.choices[0] && data.choices[0].message) {
      var result = data.choices[0].message.content.trim();
      // Safety: if result is too different from input, reject it
      if (result.length < text.length * 0.3) {
        console.warn('[GLM-PREPROCESS] Result too short, rejecting: "' + result.substring(0, 60) + '"');
        return null;
      }
      return result;
    }
    return null;
  } catch(e) {
    console.warn('[GLM-PREPROCESS] Error:', e.message);
    return null;
  }
}

async function testGlmApiKey() {
  var apiKey = document.getElementById('cfgGlmApiKey').value.trim();
  if (!apiKey) { showToast('请输入 GLM API Key', 'error'); return; }
  showToast('正在测试 API Key...', 'info');
  try {
    var resp = await fetch('/api/glm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        apiKey: apiKey,
        messages: [
          { role: 'user', content: '你好，请回复"连接成功"' }
        ]
      })
    });
    var data = await resp.json();
    if (data.choices && data.choices[0]) {
      showToast('GLM API Key 有效！', 'success');
    } else if (data.error) {
      showToast('API 错误: ' + (data.error.message || JSON.stringify(data.error)), 'error');
    } else {
      showToast('未知响应格式', 'error');
    }
  } catch(e) {
    showToast('连接失败: ' + e.message, 'error');
  }
}

// Enhanced preprocessTextForTTS with GLM support
async function preprocessTextForTTSSmart(text) {
  var mode = S.config.glmPreprocess || 'off';
  var apiKey = S.config.glmApiKey;

  // Always run regex-based preprocessing first
  var regexResult = preprocessTextForTTS(text);

  if (mode === 'off' || !apiKey) {
    return regexResult;
  }

  // v2.22: with enabled GLM-semantic rules, fallback mode must consult GLM
  // even when regex handled everything (the rules may target plain words).
  if (mode === 'fallback' && hasEnabledLlmRules()) {
    var glmForRules = await glmPreprocessText(text);
    if (glmForRules) return glmForRules;
  }

  if (mode === 'fallback') {
    // Use GLM only if regex result looks same as input (no numbers/symbols were converted)
    var hasDigits = /\\d/.test(text);
    var hasSpecialSymbols = /[≥≤≠×÷@℃°%]/.test(text);
    if (!hasDigits && !hasSpecialSymbols) {
      return regexResult;  // No need for GLM
    }
    // If regex already converted everything, check quality
    var stillHasDigits = /\\d/.test(regexResult);
    if (!stillHasDigits) {
      return regexResult;  // Regex did its job
    }
    // Regex couldn't handle it fully, try GLM
  }

  // mode === 'always' or 'fallback' with unhandled content
  var glmResult = await glmPreprocessText(text);
  if (glmResult) {
    appLog('[PREPROCESS] GLM result used for text len=' + text.length, 'i');
    return glmResult;
  }

  // GLM failed, fall back to regex result
  return regexResult;
}

function renderSpeakerPatterns() {
  var container = E.speakerPatternsList;
  if (!container) return;
  var patterns = S.config.spCustomPatterns || [];
  if (patterns.length === 0) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:4px">暂无自定义模式</div>';
    return;
  }
  var html = '';
  for (var i = 0; i < patterns.length; i++) {
    html += '<div class="speaker-pattern-row">';
    html += '<input type="text" value="' + escHtml(patterns[i]) + '" readonly>';
    html += '<button class="sp-del" onclick="removeSpeakerPattern(' + i + ')">' + svgIcon('x') + '</button>';
    html += '</div>';
  }
  container.innerHTML = html;
}

// v2.22: rebuild a segment's text preserving original line boundaries.
// Lines joined with \\n; a line that lacks sentence-final punctuation gets one
// appended (or its comma upgraded), so every line ends as a prosody unit the
// upstream engine respects. Falls back to plain text when slices disagree.
function buildLineAwareSegmentText(startPos, endPos, lineInfos, segTextPlain) {
  var parts = [];
  for (var i = 0; i < lineInfos.length; i++) {
    var li = lineInfos[i];
    if (li.endPos <= startPos || li.startPos >= endPos) continue;
    var s = Math.max(0, startPos - li.startPos);
    var e = Math.min(li.text.length, endPos - li.startPos);
    var piece = li.text.substring(s, e);
    if (piece) parts.push(piece);
  }
  if (parts.length === 0) parts.push(segTextPlain);
  var out = '';
  for (var p = 0; p < parts.length; p++) {
    var t = parts[p];
    var lastCh = t.charAt(t.length - 1);
    if (!/[。！？!?…”』」]/.test(lastCh)) {
      if (/[，,、；;：:]/.test(lastCh)) t = t.slice(0, -1) + '。';
      else t = t + '。';
    }
    out += t;
    if (p < parts.length - 1) out += '\\n';
  }
  return out;
}

function splitTextForTTS(text, maxChars) {
  if (!text || !text.trim()) return [];
  if (!maxChars) maxChars = 150;

  var originalLines = text.split('\\n');

  // Build merged text and track line positions
  var merged = '';
  var lineInfos = [];
  for (var i = 0; i < originalLines.length; i++) {
    var lineText = originalLines[i];
    // v2.21: no space inserted between lines (Chinese TTS turns stray spaces into odd pauses)
    var startPos = merged.length;
    merged += lineText;
    lineInfos.push({ text: lineText, startPos: startPos, endPos: merged.length });
  }

  // Step 1: Split into sentences at punctuation boundaries
  var sentenceEndRe = /[。！？.!?…]/g;
  var breakPoints = [];
  var match;
  while ((match = sentenceEndRe.exec(merged)) !== null) {
    breakPoints.push(match.index + 1);
  }
  // v2.22: a line end is a sentence boundary as well. Without this, an
  // unpunctuated line glued the next line into one endless "sentence" and the
  // upstream engine re-segmented it at random spots (user bug B).
  for (var lb = 0; lb < lineInfos.length; lb++) {
    var lbEnd = lineInfos[lb].endPos;
    if (lbEnd > 0 && lbEnd < merged.length) breakPoints.push(lbEnd);
  }
  breakPoints.sort(function(a, b) { return a - b; });
  var bpSeen = {};
  breakPoints = breakPoints.filter(function(bp) { if (bpSeen[bp]) return false; bpSeen[bp] = true; return true; });
  breakPoints.push(merged.length);

  var sentences = [];
  var sStart = 0;
  for (var b = 0; b < breakPoints.length; b++) {
    var bp = breakPoints[b];
    var sText = merged.substring(sStart, bp).trim();
    if (sText) {
      sentences.push({ text: sText, start: sStart, end: bp });
    }
    sStart = bp;
  }

  // Step 2: Merge sentences into segments up to maxChars
  var segments = [];
  var currentText = '';
  var currentStart = -1; // v2.22: -1 sentinel (0 is a VALID start; !0 is falsy and
                         // let the second sentence overwrite the segment start)

  for (var si = 0; si < sentences.length; si++) {
    var sent = sentences[si];
    var combinedLen = currentText.length + (currentText ? 1 : 0) + sent.text.length;

    if (currentText && combinedLen > maxChars) {
      // Current segment is full, push it
      var lines = getLinesInRange(currentStart, currentStart + currentText.length, lineInfos);
      // v2.22: keep newline boundaries inside the segment text — upstream TTS
      // was proven (live probe) to respond to \\n as a hard prosody break,
      // while dropped newlines made it re-segment at random places.
      segments.push({ text: buildLineAwareSegmentText(currentStart, currentStart + currentText.length, lineInfos, currentText), textPlain: currentText, lines: lines, segIndex: segments.length });
      currentText = sent.text;
      currentStart = sent.start;
    } else {
      // Add sentence to current segment
      currentText = currentText ? currentText + sent.text : sent.text; // v2.21: no space join
      if (currentStart < 0) currentStart = sent.start;
    }
  }

  // Push remaining
  if (currentText.trim()) {
    var lines = getLinesInRange(currentStart, currentStart + currentText.length, lineInfos);
    var trimmedText = currentText.trim();
    // v2.22: line-aware text + finalize line-end punctuation for the tail
    var tailAware = buildLineAwareSegmentText(currentStart, currentStart + currentText.length, lineInfos, trimmedText);
    segments.push({ text: tailAware, textPlain: trimmedText, lines: lines, segIndex: segments.length });
  }

  // Step 3: Handle any segments that still exceed maxChars (very long sentences with no punctuation)
  var finalSegments = [];
  for (var fi = 0; fi < segments.length; fi++) {
    var fpText = segments[fi].textPlain || segments[fi].text;
    if (fpText.length > maxChars) {
      var subSegs = splitLongSegment(fpText, maxChars, 0, [{ text: fpText, startPos: 0, endPos: fpText.length }]);
      for (var ss = 0; ss < subSegs.length; ss++) {
        if (!subSegs[ss].textPlain) subSegs[ss].textPlain = subSegs[ss].text;
        finalSegments.push(subSegs[ss]);
      }
    } else {
      if (!segments[fi].textPlain) segments[fi].textPlain = segments[fi].text;
      finalSegments.push(segments[fi]);
    }
  }

  for (var fi = 0; fi < finalSegments.length; fi++) finalSegments[fi].segIndex = fi;

  return finalSegments;
}

function splitLongSegment(text, maxChars, globalStart, lineInfos) {
  var result = [];
  var parts = text.split(/[,，;；、]/);
  var current = '';
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i];
    if (current.length + part.length + 1 > maxChars && current) {
      var cl = getLinesInRange(globalStart, globalStart + current.length, lineInfos);
      result.push({ text: current.trim(), lines: cl, segIndex: result.length });
      globalStart += current.length;
      current = part;
    } else {
      if (current) current += ',' + part;
      else current = part;
    }
  }
  if (current.trim()) {
    var cl = getLinesInRange(globalStart, globalStart + current.length, lineInfos);
    result.push({ text: current.trim(), lines: cl, segIndex: result.length });
  }
  return result;
}

function getLinesInRange(startPos, endPos, lineInfos) {
  var result = [];
  for (var i = 0; i < lineInfos.length; i++) {
    if (lineInfos[i].endPos > startPos && lineInfos[i].startPos < endPos) {
      result.push({ text: lineInfos[i].text, lineIndex: i });
    }
  }
  return result;
}

// ==================== NiceVoice TTS Generation ====================
async function nvCloneVoice(voiceDataOrFile) {
  // Accept either full voiceData object { audioFile, nvReferenceId, ... } or just audioFile
  var voiceData = voiceDataOrFile;
  var currentAudioFile = null;
  var currentNvRefId = null;

  // Detect if passed as voiceData (has .audioFile) or bare audioFile
  if (voiceData && voiceData.audioFile) {
    currentAudioFile = voiceData.audioFile;
    currentNvRefId = voiceData.nvReferenceId || voiceData.audioFile.nvReferenceId || null;
  } else {
    currentAudioFile = voiceDataOrFile;
    currentNvRefId = (voiceDataOrFile && voiceDataOrFile.nvReferenceId) || null;
  }

  if (!currentAudioFile || !currentAudioFile.base64) {
    // Even without base64, if we have a valid referenceId, try to reuse it
    if (currentNvRefId) {
      appLog('[NV] 无音频数据但有已保存的referenceId，尝试复用: ' + currentNvRefId, 'i');
      try {
        var verifyResp0 = await fetch('/api/nv/getSyncRefStatus', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ referenceId: currentNvRefId })
        });
        var verifyData0 = await verifyResp0.json();
        if (verifyData0.data && verifyData0.data.error === 0) {
          showToast('音色验证通过，复用已有音色', 'success');
          return currentNvRefId;
        }
      } catch(e) {}
    }
    showToast('请先分配参考音频', 'error');
    return null;
  }

  // ===== Check if we already have a referenceId =====
  if (currentNvRefId) {
    appLog('[NV] 正在验证已保存的音色...', 'i');

    try {
      var verifyResp = await fetch('/api/nv/getSyncRefStatus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ referenceId: currentNvRefId })
      });
      var verifyData = await verifyResp.json();

      if (verifyData.data && verifyData.data.error === 0) {
        // Reference still valid on server — reuse it!
        showToast('音色验证通过，无需重新克隆', 'success');
        return currentNvRefId;
      } else {
        // Reference expired/invalid on server — need to re-clone
        showToast('音色已失效，正在重新克隆...', 'info');
        currentNvRefId = null;
      }
    } catch(verifyErr) {
      currentNvRefId = null;
    }
  }

  // ===== Full clone flow =====
  appLog('[NV] 正在上传参考音频...', 'i');
  S.nvCloneBusy = true;

  try {
    // Calculate audio file size and duration
    var audioBlob = currentAudioFile.wavBlob;
    var fileSize = audioBlob ? audioBlob.size : 0;
    var audioDuration = 10; // default, will be refined
    if (audioBlob) {
      try {
        var tempCtx = new (window.AudioContext || window.webkitAudioContext)();
        var tempBuf = await tempCtx.decodeAudioData(await audioBlob.arrayBuffer());
        audioDuration = tempBuf.duration;
        tempCtx.close();
      } catch(e) {
      }
    }

    // Step 1: Get upload URL
    var resp1 = await fetch('/api/nv/getUploadUrl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suffix: '.wav', fileSize: fileSize, audioDuration: audioDuration })
    });
    var data1 = await resp1.json();
    appLog('[NV] getUploadUrl => ' + JSON.stringify(data1).substring(0, 500), 'i');
    if (!data1.data || (!data1.data.url && !data1.data.uploadUrl)) {
      throw new Error('获取上传地址失败: ' + JSON.stringify(data1));
    }
    var uploadUrl = data1.data.uploadUrl || data1.data.url;
    var referenceId = data1.data.referenceId || data1.data.refId;
    var filePath = data1.data.filePath || '';

    appLog('[NV] 正在上传音频文件...', 'i');

    // Step 2: Upload audio to presigned URL via proxy
    var resp2 = await fetch('/api/nv-upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uploadUrl: uploadUrl, audioBase64: currentAudioFile.base64 })
    });
    var data2 = await resp2.json();
    appLog('[NV] 上传结果 => ' + JSON.stringify(data2), 'i');
    if (!data2.ok) {
      throw new Error('上传音频失败: ' + data2.status);
    }

    appLog('[NV] 正在训练声音模型...', 'i');

    // Step 3: Save reference audio (trigger clone training)
    var resp3 = await fetch('/api/nv/saveRefAudio2', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audioPath: filePath,
        referenceId: referenceId,
        referenceName: currentAudioFile.name || 'ref_audio',
        text: '',
        fileSize: fileSize,
        audioDuration: audioDuration
      })
    });
    var data3 = await resp3.json();
    appLog('[NV] saveRefAudio2 => ' + JSON.stringify(data3).substring(0, 500), 'i');
    if (!data3.data || !data3.data.referenceId) {
      throw new Error('创建声音克隆失败: ' + JSON.stringify(data3));
    }
    referenceId = data3.data.referenceId;

    // Step 4: Poll clone status
    var maxPoll = S.config.nvMaxPoll || 60;
    for (var i = 0; i < maxPoll; i++) {
 if (S.cancelRequested) { S.nvCloneBusy = false; return null; }
      await sleep(2000);
      appLog('[NV] 训练声音模型中... (' + (i + 1) + '/' + maxPoll + ')', 'i');

      var resp4 = await fetch('/api/nv/getSyncRefStatus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ referenceId: referenceId })
      });
      var data4 = await resp4.json();
      if (i % 5 === 0 || (data4.data && data4.data.error === 0)) {
        appLog('[NV] getSyncRefStatus[' + (i+1) + '] => ' + JSON.stringify(data4).substring(0, 300), 'i');
      }
      if (data4.data && data4.data.error === 0) {
        appLog('[NV] 文件同步完成，正在验证音色...', 'i');
        var isValid = await nvValidateClone(referenceId);
        S.nvCloneBusy = false;
        if (isValid) {
          showToast('声音克隆完成并验证通过', 'success');
          appLog('[NV] 声音克隆完成 (已验证)', 's');
        } else {
          showToast('声音克隆失败: 上游 API 返回错误，请稍后重试或切换引操', 'error');
          appLog('[NV] 声音克隆失败 - 文件同步成功但 TTS 不可用', 'e');
        }
        return referenceId;
      }
    }
    throw new Error('声音克隆超时');
  } catch(e) {
    appLog('[NV] 克隆失败: ' + e.message, 'e');
    S.nvCloneBusy = false;
    showToast('声音克隆失败: ' + e.message, 'error');
    return null;
  }
}

// v2.18: Post-clone validation - test TTS with cloned voice to confirm it works
async function nvValidateClone(referenceId, testText) {
  try {
    var vt = testText || '测试';
    var vd = await fetch('/api/nv/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: vt, referenceId: referenceId })
    });
    var vdata = await vd.json();
    if (vdata.code === 70002006) {
      appLog('[NV] 验证被限流，等待16s后重试', 'w');
      await sleep(16000);
      vd = await fetch('/api/nv/tts', {
        method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: vt, referenceId: referenceId })
      });
      vdata = await vd.json();
    }
    if (vdata.code === 200 && vdata.data && vdata.data.taskSn) {
      appLog('[NV] 克验确认音色可用', 's');
      return true;
    }
    appLog('[NV] 克验失败: TTS code=' + vdata.code + '\\n' + JSON.stringify(vdata).substring(0, 200), 'w');
    return false;
  } catch(ve) {
    appLog('[NV] 克验异常: ' + ve.message, 'w');
    return false;
  }
}

async function nvGenerateSegment(text, referenceId, segIdx) {
  var maxPoll = S.config.nvMaxPoll || 60;
  var retries = 0;
  var maxRetries = 3;

  while (retries <= maxRetries) {
    if (S.cancelRequested) {
      return null;
    }
    try {
      // Submit TTS request (NiceVoice only needs text + referenceId)
      var reqBody = { text: text, referenceId: referenceId };
      appLog('[NV] TTS请求 text="' + text.substring(0, 80) + '" (len=' + text.length + ') refId=' + referenceId, 'i');
      var resp1 = await fetch('/api/nv/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      var data1 = await resp1.json();
      appLog('[NV] tts => ' + JSON.stringify(data1).substring(0, 500), 'i');
      // Handle rate limit by waiting and retrying
      if (data1.code === 70002006 || (data1.msg && data1.msg.toastZh && data1.msg.toastZh.indexOf('频繁') >= 0)) {
        if (retries < maxRetries) {
          retries++;
          await sleep(16000); // Wait 16s for rate limit
          continue;
        }
        throw new Error('请求过于频繁，请稍后重试');
      }
      if (!data1.data || !data1.data.taskSn) {
        throw new Error('TTS提交失败: ' + JSON.stringify(data1));
      }
      var taskSn = data1.data.taskSn;

      // Poll for result
      for (var p = 0; p < maxPoll; p++) {
        if (S.cancelRequested) {
          return null;
        }
        await sleep(2000);
        var resp2 = await fetch('/api/nv/getItemByTaskSn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ taskSn: taskSn })
        });
        var data2 = await resp2.json();
        if (p % 5 === 0 || (data2.data && data2.data.statusStr === 'success')) {
          appLog('[NV] getItemByTaskSn[' + (p+1) + '] => ' + JSON.stringify(data2).substring(0, 300), 'i');
        }
        if (data2.data && data2.data.statusStr === 'success' && data2.data.audioUrl) {
          // Download audio via proxy
          var audioUrl = data2.data.audioUrl;
          var audioResp = await fetch('/api/audio-proxy?url=' + encodeURIComponent(audioUrl));
          if (!audioResp.ok) throw new Error('下载音频失败');
          var audioArrayBuffer = await audioResp.arrayBuffer();
          return new Blob([audioArrayBuffer], { type: 'audio/mpeg' });
        }
        if (data2.data && data2.data.statusStr === 'failed') {
          throw new Error('TTS生成失败');
        }
      }
      throw new Error('TTS轮询超时');
    } catch(e) {
      retries++;
      if (retries > maxRetries) throw e;
      await sleep(2000 * retries);
    }
  }
}

async function nvGenerateAll(segments, referenceId) {
  var waitMs = (S.config.nvWait || 16) * 1000;
  var bufIdx = 0;

  for (var i = 0; i < segments.length; i++) {
    if (S.cancelRequested) {
      break;
    }

    var seg = S.segments[i];
    seg.status = 'submitting';
    renderSegmentTable();

    if (i > 0) {
      // Wait between requests for rate limiting
      seg.status = 'processing';
      renderSegmentTable();
      showToast('等待 ' + (waitMs / 1000) + '秒后继续...', 'info');
      var waitStart = Date.now();
      while (Date.now() - waitStart < waitMs && !S.cancelRequested) {
        await sleep(500);
      }
      if (S.cancelRequested) {
        break;
      }
    }

    try {
      appLog('[NV] 生成段' + (i+1) + '/' + S.segments.length, 'i');
      var audioBlob = await nvGenerateSegment(await preprocessTextForTTSSmart((S.previewEdits && S.previewEdits[i] !== undefined) ? S.previewEdits[i] : seg.text), referenceId, i);
      if (!audioBlob) {
        seg.status = 'cancelled';
        renderSegmentTable();
        continue;
      }

      seg.audioBlob = audioBlob;
      // Get duration
      try {
        var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        var audioBuffer = await audioCtx.decodeAudioData(await audioBlob.arrayBuffer());
        seg.duration = audioBuffer.duration;
        audioCtx.close();
      } catch(de) {
        seg.duration = audioBlob.size / (24000 * 2);
      }

      seg.status = 'done';
      bufIdx++;
      appLog('[NV] 段' + (i+1) + ' OK', 's');
    } catch(e) {
      seg.status = 'error';
      seg.error = e.message;
    }
    renderSegmentTable();
    updateProgress();
  }
}

// ==================== Log Console ====================
function appLog(msg, type) {
  type = type || 'i';
  var c = document.getElementById('logBox');
  if (!c) return;
  var e = document.createElement('div');
  e.className = 'log-entry ' + type;
  e.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
  c.appendChild(e);
  c.scrollTop = c.scrollHeight;
}

// ==================== Main Generation Entry ====================
async function startGenerate() {
  var text = E.textInput.value.trim();
  if (!text) { showToast('请输入要合成的文本', 'error'); return; }

  // Validate voice assignments for all speakers
  var speakersToValidate = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }];
  for (var vi = 0; vi < speakersToValidate.length; vi++) {
    var spName = speakersToValidate[vi].name;
    if (!S.speakerVoiceData[spName]) {
      // Try to load from assignment
      if (S.speakerAssignments[spName]) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[spName]; });
        if (src) {
          S.speakerVoiceData[spName] = buildVoiceDataFromSource(src);
        }
      }
      if (!S.speakerVoiceData[spName]) {
        showToast('请为说话人 "' + spName + '" 分配音源', 'error');
        return;
      }
    }
  }

  S.isGenerating = true;
  S.cancelRequested = false;
  // v2.14: previewEdits is set by applyPreviewAndGenerate, keep it through generation
  S.segments = [];
  S.segmentBuffers = [];
  S.segmentDurations = [];
  S.resultWavBlob = null;
  S.resultSrt = '';
  // Clean up previous Object URL
  if (S.resultWavUrl) { URL.revokeObjectURL(S.resultWavUrl); S.resultWavUrl = null; }
  S.downloadTimestamp = (function() {
    var now = new Date();
    return '' + now.getFullYear() + pad2(now.getMonth() + 1) + pad2(now.getDate()) + '-' + pad2(now.getHours()) + pad2(now.getMinutes()) + pad2(now.getSeconds());
  })();
  // Set project name: use docx filename if available, otherwise timestamp
  S.projectName = S.docxFileName || S.downloadTimestamp;

  var maxChars = (S.config.nvMaxChars || 150);

  // Build segments based on speaker mode
  if (S.speakerMode === 'multi') {
    var spGroups = splitTextBySpeakers(text, maxChars);
    // Flatten all segments from all groups, preserving speaker info
    var allSegs = [];
    for (var gi = 0; gi < spGroups.length; gi++) {
      for (var si = 0; si < spGroups[gi].segments.length; si++) {
        var seg = spGroups[gi].segments[si];
        seg.speaker = spGroups[gi].speaker;
        allSegs.push(seg);
      }
    }
    S.segments = allSegs.map(function(seg) {
      return { text: seg.text, textPlain: seg.textPlain || seg.text, lines: seg.lines, speaker: seg.speaker, status: 'pending', jobId: null, audioBlob: null, duration: 0, error: null };
    });
    if (S.segments.length === 0) { showToast('文本为空或无法分段', 'error'); S.isGenerating = false; return; }
    appLog('[GEN] 引擎=' + S.engine + ' maxChars=' + maxChars + ' 分段数=' + S.segments.length + ' 说话人数=' + S.detectedSpeakers.length, 'i');
    // v2.14: Check speaker alternation issues
    _alternationDismissed = false; // v2.20: reset
    checkSpeakerAlternation();
  } else {
    var segments = splitTextForTTS(text, maxChars);
    if (segments.length === 0) { showToast('文本为空或无法分段', 'error'); S.isGenerating = false; return; }
    S.segments = segments.map(function(seg) {
      return { text: seg.text, textPlain: seg.textPlain || seg.text, lines: seg.lines, speaker: null, status: 'pending', jobId: null, audioBlob: null, duration: 0, error: null };
    });
    appLog('[GEN] 引擎=' + S.engine + ' maxChars=' + maxChars + ' 分段数=' + segments.length, 'i');
  }

  // Update UI
  E.generateBtn.disabled = true;
  E.genBtnText.innerHTML = '<span class="spinner"></span> 合成中...';
  E.cancelBtn.style.display = 'block';
  E.progressBar.classList.add('active');
  E.progressFill.style.width = '0%';
  E.resultSection.classList.remove('active');
  renderSegmentTable();
  var logBox = document.getElementById('logBox'); if (logBox) logBox.innerHTML = '';
  S.elapsedStart = Date.now();
  updateElapsed();
  S.elapsedTimer = setInterval(updateElapsed, 1000);
  E.elapsed.style.display = 'block';

  {
    // v2.21: NiceVoice is the only engine
    if (S.speakerMode === 'multi') {
      await nvMultiSpeakerGenerate();
    } else {
      var defaultVoice = S.speakerVoiceData['默认'];
      var referenceId = await nvCloneVoice(defaultVoice);
      if (referenceId && !S.cancelRequested) {
        await nvGenerateAll(S.segments, referenceId);
      }
    }
  }

  // Done
  clearInterval(S.elapsedTimer);
  S.isGenerating = false;
  E.generateBtn.disabled = false;
  var btnLabel = svgIcon('zap') + ' 开始合成 (NiceVoice)';
  E.genBtnText.innerHTML = btnLabel;
  E.cancelBtn.style.display = 'none';
  // v2.17: Re-render segment table so cells become editable now that isGenerating=false
  renderSegmentTable();

  var successSegs = S.segments.filter(function(s) { return s.status === 'done'; });
  var failedSegs = S.segments.filter(function(s) { return s.status === 'error'; });

  if (successSegs.length === 0) {
    showToast('全部段生成失败' + (S.cancelRequested ? '（已取消）' : ''), 'error');
    return;
  }

  try { await concatenateAudio(); } catch(e) { showToast('音频拼接失败: ' + e.message, 'error'); return; }
  generateSrt();

  // Create Object URL for playback (also reused for download)
  S.resultWavUrl = URL.createObjectURL(S.resultWavBlob);
  E.resultAudio.src = S.resultWavUrl;
  E.resultSection.classList.add('active');
  // v2.14: Clear previewEdits after successful generation
  S.previewEdits = null;
  // v2.14: Show metadata generation card
  if (E.metadataCard) E.metadataCard.style.display = 'block';
  // v2.17: Final re-render to ensure all segments are editable
  renderSegmentTable();

  addHistory({
    text: text.substring(0, 200),
    engine: S.engine,
    segments: S.segments.length,
    success: successSegs.length,
    failed: failedSegs.length,
    date: new Date().toLocaleString('zh-CN'),
    timestamp: Date.now(),
    projectName: S.projectName
  });

  if (failedSegs.length > 0) {
    showToast('部分段生成失败 (' + failedSegs.length + '/' + S.segments.length + ')，已生成可用部分', 'error');
  } else {
    showToast('合成完成！共 ' + successSegs.length + ' 段' + (S.speakerMode === 'multi' ? '（' + S.detectedSpeakers.length + '位说话人）' : ''), 'success');
  }
}

// ==================== Multi-Speaker Generation Flows ====================
async function nvMultiSpeakerGenerate() {
  // Clone voices for each speaker first
  var speakerRefIds = {};
  for (var si = 0; si < S.detectedSpeakers.length; si++) {
    var sp = S.detectedSpeakers[si];
    var voiceData = S.speakerVoiceData[sp.name];
    if (!voiceData) { appLog('[NV] 说话人 ' + sp.name + ' 未分配音源', 'e'); continue; }

    appLog('[NV] 克隆说话人: ' + sp.name, 'i');
    var refId = await nvCloneVoice(voiceData);
    speakerRefIds[sp.name] = refId;

    // Save back the reference ID
    voiceData.nvReferenceId = refId;
    // Also update the saved source if any
    if (S.speakerAssignments[sp.name]) {
      var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[sp.name]; });
      if (src) { src.nvReferenceId = refId; saveAudioSources(); }
    }

    if (S.cancelRequested) return;
  }

  // Generate segments using the appropriate reference ID
  var waitMs = (S.config.nvWait || 16) * 1000;
  for (var i = 0; i < S.segments.length; i++) {
    if (S.cancelRequested) break;

    var seg = S.segments[i];
    var refId = speakerRefIds[seg.speaker];
    if (!refId) {
      seg.status = 'error';
      seg.error = '说话人 ' + seg.speaker + ' 克隆失败';
      renderSegmentTable();
      updateProgress();
      continue;
    }

    seg.status = 'submitting';
    renderSegmentTable();

    if (i > 0) {
      seg.status = 'processing';
      renderSegmentTable();
      showToast('等待 ' + (waitMs / 1000) + '秒后继续...', 'info');
      var waitStart = Date.now();
      while (Date.now() - waitStart < waitMs && !S.cancelRequested) {
        await sleep(500);
      }
      if (S.cancelRequested) break;
    }

    try {
      appLog('[NV] 生成段' + (i+1) + '/' + S.segments.length + ' (说话人: ' + (seg.speaker || '默认') + ')', 'i');
      var audioBlob = await nvGenerateSegment(await preprocessTextForTTSSmart((S.previewEdits && S.previewEdits[i] !== undefined) ? S.previewEdits[i] : seg.text), refId, i);
      if (!audioBlob) {
        seg.status = 'cancelled';
        renderSegmentTable();
        continue;
      }

      seg.audioBlob = audioBlob;
      try {
        var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        var audioBuffer = await audioCtx.decodeAudioData(await audioBlob.arrayBuffer());
        seg.duration = audioBuffer.duration;
        audioCtx.close();
      } catch(de) {
        seg.duration = audioBlob.size / (24000 * 2);
      }
      seg.status = 'done';
      appLog('[NV] 段' + (i+1) + ' OK (' + (seg.speaker || '默认') + ')', 's');
    } catch(e) {
      seg.status = 'error';
      seg.error = e.message;
    }
    renderSegmentTable();
    updateProgress();
  }
}

function cancelGenerate() {
  S.cancelRequested = true;
  showToast('正在取消...', 'info');
}

function updateProgress() {
  var total = S.segments.length;
  var done = S.segments.filter(function(s) { return s.status === 'done' || s.status === 'error' || s.status === 'cancelled'; }).length;
  var pct = total > 0 ? Math.round(done / total * 100) : 0;
  E.progressFill.style.width = pct + '%';
}

function updateElapsed() {
  var elapsed = Math.floor((Date.now() - S.elapsedStart) / 1000);
  var min = Math.floor(elapsed / 60);
  var sec = elapsed % 60;
  E.elapsed.textContent = '已用时: ' + (min > 0 ? min + 'm ' : '') + sec + 's';
}

// v2.15: Per-segment preview with play/stop toggle
var _segPreviewAudio = null;
var _segPreviewBtn = null;
function previewSegment(idx, btnEl) {
  // If currently playing this segment, stop
  if (_segPreviewAudio && _segPreviewAudio._segIdx === idx) {
    _segPreviewAudio.pause();
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = svgIcon('play');
    _segPreviewBtn = null;
    return;
  }
  // Stop any other playing segment
  if (_segPreviewAudio) {
    _segPreviewAudio.pause();
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = svgIcon('play');
  }
  var seg = S.segments[idx];
  if (!seg || !seg.audioBlob) { showToast('该段尚无音频', 'error'); return; }
  _segPreviewBtn = btnEl;
  _segPreviewAudio = new Audio(URL.createObjectURL(seg.audioBlob));
  _segPreviewAudio._segIdx = idx;
  _segPreviewAudio.play().then(function() {
    if (btnEl) btnEl.innerHTML = svgIcon('pause');
  }).catch(function() { showToast('播放失败', 'error'); });
  _segPreviewAudio.onended = function() {
    URL.revokeObjectURL(_segPreviewAudio.src);
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = svgIcon('play');
    _segPreviewBtn = null;
  };
  _segPreviewAudio.onerror = function() {
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = svgIcon('play');
    _segPreviewBtn = null;
    showToast('播放失败', 'error');
  };
}

function renderSegmentTable() {
  var table = E.segTable;
  var tbody = E.segBody;
  if (S.segments.length === 0) { table.style.display = 'none'; return; }
  table.style.display = 'table';
  // Build speaker index map for color coding
  var spIndexMap = {};
  for (var sdi = 0; sdi < S.detectedSpeakers.length; sdi++) {
    spIndexMap[S.detectedSpeakers[sdi].name] = sdi;
  }
  // v2.16: Check if any segments have been edited after generation completed
  var hasEditsAfterDone = S.segments.some(function(s) { return s.edited && s.status === 'done'; });
  if (hasEditsAfterDone && !S.isGenerating) {
    var genBtn = document.getElementById('generateBtn');
    var genBtnText = document.getElementById('genBtnText');
    if (genBtn && genBtnText) {
      genBtnText.innerHTML = svgIcon('pen') + ' 应用更改（重新生成改动段）';
      genBtn.style.opacity = '1';
      genBtn.disabled = false;
      genBtn.onclick = applySegmentEdits;
    }
  } else if (!S.isGenerating) {
    var genBtn2 = document.getElementById('generateBtn');
    var genBtnText2 = document.getElementById('genBtnText');
    if (genBtn2 && genBtnText2 && !genBtn2.onclick.toString().match('onGenerateClick')) {
      genBtnText2.innerHTML = svgIcon('zap') + ' 开始合成 (NiceVoice)';
      genBtn2.onclick = onGenerateClick;
    }
  }
  var html = '';
  S.segments.forEach(function(seg, i) {
    var statusLabel = { 'pending': '等待', 'cloning': '克隆', 'submitting': '提交', 'processing': '生成', 'done': '完成', 'error': '失败', 'cancelled': '取消' }[seg.status] || seg.status;
    var durText = seg.duration > 0 ? seg.duration.toFixed(1) + 's' : '-';
    var shortText = seg.text.length > 40 ? seg.text.substring(0, 40) + '...' : seg.text;
    var speakerBadge = '';
    if (seg.speaker && S.speakerMode === 'multi') {
      var spIdx = spIndexMap[seg.speaker];
      if (spIdx === undefined) spIdx = 0;
      speakerBadge = '<span class="seg-speaker sp' + (spIdx % 5) + '">' + escHtml(seg.speaker) + '</span>';
    }
    var previewBtn = '';
    if (seg.status === 'done' && seg.audioBlob) {
      previewBtn = '<button onclick="previewSegment(' + i + ', this)" title="试听" style="background:transparent;border:none;color:var(--blue);cursor:pointer;font-size:14px;padding:2px 6px">' + svgIcon('play') + '</button>';
    }
    // v2.16: Make seg-text clickable to edit (disabled during generation)
    var canEdit = !S.isGenerating;
    var editIndicator = seg.edited ? ' <span style="color:var(--orange);font-size:10px">' + svgIcon('pen') + '</span>' : '';
    var segTextCell = '';
    if (canEdit) {
      segTextCell = '<td class="seg-text" title="点击编辑文本" style="cursor:text" onclick="editSegmentText(' + i + ', this)">' + speakerBadge + escHtml(shortText) + editIndicator + '</td>';
    } else {
      segTextCell = '<td class="seg-text" title="' + escHtml(seg.text) + '">' + speakerBadge + escHtml(shortText) + editIndicator + '</td>';
    }
    html += '<tr>';
    html += '<td>' + (i + 1) + '</td>';
    html += segTextCell;
    html += '<td><div class="seg-status"><span class="sd ' + seg.status + '"></span>' + statusLabel + '</div></td>';
    html += '<td>' + durText + '</td>';
    html += '<td>' + previewBtn + '</td>';
    html += '</tr>';
  });
  tbody.innerHTML = html;
}

// ==================== v2.16: Segment Text Editing ====================
var _segEditingIdx = -1;
var _segEditingOriginal = '';

function editSegmentText(idx, cellEl) {
  if (S.isGenerating) {
    showToast('生成中无法编辑', 'error');
    return;
  }
  // v2.20: Defensive check — cellEl may be orphaned
  if (!cellEl || !cellEl.parentNode || !document.body.contains(cellEl)) {
    renderSegmentTable();
    return;
  }
  var seg = S.segments[idx];
  if (!seg) return;
  // If currently editing another cell, commit it first (but do NOT re-render)
  if (_segEditingIdx >= 0 && _segEditingIdx !== idx) {
    commitSegmentEditSilent(); // v2.20: silent commit without re-render
  }
  _segEditingIdx = idx;
  _segEditingOriginal = seg.text;
  // Replace cell content with a textarea
  var speakerBadge = '';
  if (seg.speaker && S.speakerMode === 'multi') {
    var spIdx = S.detectedSpeakers.findIndex(function(s) { return s.name === seg.speaker; });
    if (spIdx < 0) spIdx = 0;
    speakerBadge = '<span class="seg-speaker sp' + (spIdx % 5) + '">' + escHtml(seg.speaker) + '</span>';
  }
  cellEl.innerHTML = speakerBadge + '<textarea data-seg-idx="' + idx + '" style="width:100%;min-height:60px;background:var(--surface2);border:1px solid var(--primary);color:var(--text);padding:4px 6px;border-radius:4px;font-size:12px;font-family:inherit;resize:vertical">' + escHtml(seg.text) + '</textarea>';
  cellEl.onclick = null;
  cellEl.style.cursor = 'default';
  var ta = cellEl.querySelector('textarea');
  if (!ta) return; // v2.20: guard
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);
  // Auto-resize
  ta.style.height = ta.scrollHeight + 'px';
  ta.addEventListener('input', function() { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; });
  // v2.20: Commit on blur — use requestAnimationFrame to avoid race with click events
  ta.addEventListener('blur', function(e) {
    requestAnimationFrame(function() {
      if (_segEditingIdx === idx) { commitSegmentEdit(); }
    });
  });
  // Commit on Ctrl+Enter
  ta.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      ta.blur();
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      // Revert
      seg.text = _segEditingOriginal;
      _segEditingIdx = -1;
      _segEditingOriginal = '';
      renderSegmentTable();
    }
  });
}

// v2.20: Silent commit — saves text but does NOT re-render
function commitSegmentEditSilent() {
  if (_segEditingIdx < 0) return;
  var idx = _segEditingIdx;
  var seg = S.segments[idx];
  if (!seg) { _segEditingIdx = -1; return; }
  var ta = document.querySelector('textarea[data-seg-idx="' + idx + '"]');
  var newText = ta ? ta.value.trim() : _segEditingOriginal;
  _segEditingIdx = -1;
  var oldText = _segEditingOriginal;
  _segEditingOriginal = '';
  if (newText && newText !== oldText) {
    seg.text = newText;
    seg.edited = true;
    appLog('[EDIT-SILENT] 段 ' + (idx+1) + ' 已修改', 'i');
  }
}

function commitSegmentEdit() {
  if (_segEditingIdx < 0) return;
  var idx = _segEditingIdx;
  var seg = S.segments[idx];
  if (!seg) { _segEditingIdx = -1; return; }
  var ta = document.querySelector('textarea[data-seg-idx="' + idx + '"]');
  var newText = ta ? ta.value.trim() : _segEditingOriginal;
  _segEditingIdx = -1;
  var oldText = _segEditingOriginal;
  _segEditingOriginal = '';
  if (newText && newText !== oldText) {
    seg.text = newText;
    seg.edited = true;
    // Scenario logic:
    // a) seg.status === 'pending': just update text, will use new text when generated
    // b) generating (cloning/submitting/processing): shouldn't happen because we block editing, but guard anyway
    // c) seg.status === 'done' && S.isGenerating: mark for regen after current sequence
    // d) seg.status === 'done' && !S.isGenerating: mark for regen via "Apply Changes" button
    if (seg.status === 'done') {
      if (S.isGenerating) {
        // Scenario c: queue for regen after current sequence
        seg._pendingRegen = true;
        appLog('[EDIT] 段 ' + (idx+1) + ' 已修改，将在当前序列完成后重新生成', 'i');
        showToast('段 ' + (idx+1) + ' 修改已记录，将在当前序列完成后重新生成', 'info');
      } else {
        // Scenario d: change button to "Apply Changes"
        appLog('[EDIT] 段 ' + (idx+1) + ' 已修改，点击"应用更改"重新生成', 'i');
        showToast('段 ' + (idx+1) + ' 已修改，点击"应用更改"按钮重新生成', 'info');
      }
    } else if (seg.status === 'pending') {
      // Scenario a: will use new text when generated
      appLog('[EDIT] 段 ' + (idx+1) + ' 已修改，将使用新文本生成', 'i');
      showToast('段 ' + (idx+1) + ' 已修改', 'success');
    } else {
      // cloning/submitting/processing/error/cancelled - shouldn't normally happen
      appLog('[EDIT] 段 ' + (idx+1) + ' 状态为 ' + seg.status + '，修改已记录', 'w');
    }
  }
  renderSegmentTable();
}

async function applySegmentEdits() {
  // Scenario d: regenerate only edited segments, then re-concatenate
  var editedSegs = S.segments.filter(function(s) { return s.edited && s.status === 'done'; });
  if (editedSegs.length === 0) {
    showToast('没有需要重新生成的段落', 'info');
    return;
  }
  // Validate voice assignments
  var speakersToValidate = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }];
  for (var vi = 0; vi < speakersToValidate.length; vi++) {
    var spName = speakersToValidate[vi].name;
    if (!S.speakerVoiceData[spName]) {
      if (S.speakerAssignments[spName]) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[spName]; });
        if (src) S.speakerVoiceData[spName] = buildVoiceDataFromSource(src);
      }
      if (!S.speakerVoiceData[spName]) {
        showToast('请为说话人 "' + spName + '" 分配音源', 'error');
        return;
      }
    }
  }

  S.isGenerating = true;
  S.cancelRequested = false;
  E.generateBtn.disabled = true;
  E.genBtnText.innerHTML = '<span class="spinner"></span> 重新生成改动段...';
  E.cancelBtn.style.display = 'block';
  E.progressBar.classList.add('active');

  appLog('[REGEN] 开始重新生成 ' + editedSegs.length + ' 个改动段', 'i');
  var regenIndices = [];
  S.segments.forEach(function(s, i) { if (s.edited && s.status === 'done') regenIndices.push(i); });

  var successCount = 0;
  var failCount = 0;
  for (var ri = 0; ri < regenIndices.length; ri++) {
    if (S.cancelRequested) break;
    var idx = regenIndices[ri];
    var seg = S.segments[idx];
    appLog('[REGEN] 重新生成段 ' + (idx+1) + '/' + S.segments.length, 'i');
    try {
      // Get reference voice for this segment's speaker
      var spName = seg.speaker || '默认';
      var voiceData = S.speakerVoiceData[spName];
      if (!voiceData) { throw new Error('No voice data for ' + spName); }
      var referenceId = await nvCloneVoice(voiceData);
      if (!referenceId) throw new Error('Clone failed for ' + spName);
      // Apply preprocessing (previewEdits or smart preprocess)
      var textToUse = await preprocessTextForTTSSmart((S.previewEdits && S.previewEdits[idx] !== undefined) ? S.previewEdits[idx] : seg.text);
      var audioBlob = await nvGenerateSegment(textToUse, referenceId, idx);
      if (audioBlob) {
        seg.audioBlob = audioBlob;
        seg.edited = false;
        seg._pendingRegen = false;
        seg.status = 'done';
        successCount++;
        appLog('[REGEN] 段 ' + (idx+1) + ' 重新生成成功', 'i');
      } else {
        failCount++;
        seg.status = 'error';
        seg.error = '重新生成失败';
      }
    } catch(e) {
      failCount++;
      seg.status = 'error';
      seg.error = e.message;
      appLog('[REGEN] 段 ' + (idx+1) + ' 失败: ' + e.message, 'e');
    }
    renderSegmentTable();
    // NV wait between segments
    if (S.engine === 'nicevoice' && ri < regenIndices.length - 1) {
      await sleep((S.config.nvWait || 16) * 1000);
    }
  }

  S.isGenerating = false;
  E.cancelBtn.style.display = 'none';
  E.generateBtn.disabled = false;

  if (successCount > 0) {
    // Re-concatenate
    try {
      await concatenateAudio();
      // Refresh result audio
      if (S.resultWavUrl) { URL.revokeObjectURL(S.resultWavUrl); }
      S.resultWavUrl = URL.createObjectURL(S.resultWavBlob);
      E.resultAudio.src = S.resultWavUrl;
      E.resultSection.classList.add('active');
      // Regenerate SRT
      generateSrt();
      showToast('应用更改完成：' + successCount + ' 段重新生成' + (failCount > 0 ? '，' + failCount + ' 段失败' : ''), 'success');
    } catch(e) {
      showToast('重新拼合失败: ' + e.message, 'error');
    }
  } else {
    showToast('所有段重新生成失败', 'error');
  }
  renderSegmentTable();
}

// ==================== Audio Concatenation ====================
async function concatenateAudio() {
  var successSegs = S.segments.filter(function(s) { return s.status === 'done' && s.audioBlob; });
  if (successSegs.length === 0) throw new Error('No audio segments');

  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  S.segmentBuffers = [];
  S.segmentDurations = [];

  for (var i = 0; i < successSegs.length; i++) {
    var arrayBuffer = await successSegs[i].audioBlob.arrayBuffer();
    var audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
    S.segmentBuffers.push(audioBuffer);
    S.segmentDurations.push(audioBuffer.duration);
  }

  // v2.14: Voice normalization (peak + RMS) BEFORE concat
  if (S.config.voiceNormalizeEnabled !== false) {
    try {
      S.segmentBuffers = normalizeVoiceBuffers(S.segmentBuffers, S.detectedSpeakers, S.segments);
      appLog('[POST] Voice normalization applied', 'i');
    } catch(e) {
      appLog('[POST] Normalization failed: ' + e.message, 'e');
    }
  }

  var totalDuration = 0;
  var sampleRate = S.segmentBuffers[0].sampleRate;
  var numberOfChannels = S.segmentBuffers[0].numberOfChannels;
  for (var i = 0; i < S.segmentBuffers.length; i++) {
    totalDuration += S.segmentBuffers[i].duration;
    sampleRate = Math.max(sampleRate, S.segmentBuffers[i].sampleRate);
  }

  // v2.21: natural pause between segments (fixes "sentences glued together")
  var segGapMs = (S.config.segGapMs === undefined) ? 150 : parseInt(S.config.segGapMs, 10) || 0;
  var gapSamples = Math.round((segGapMs / 1000) * sampleRate);

  var totalSamples = Math.ceil(totalDuration * sampleRate) + gapSamples * Math.max(0, S.segmentBuffers.length - 1);
  var resultBuffer = audioCtx.createBuffer(numberOfChannels, totalSamples, sampleRate);

  var offset = 0;
  for (var i = 0; i < S.segmentBuffers.length; i++) {
    var buf = S.segmentBuffers[i];
    // Resample if needed (simple: copy directly assuming same sampleRate)
    for (var ch = 0; ch < numberOfChannels; ch++) {
      var sourceData = buf.getChannelData(Math.min(ch, buf.numberOfChannels - 1));
      resultBuffer.copyToChannel(sourceData, ch, offset);
    }
    offset += buf.length + gapSamples;
  }
  audioCtx.close();

  // v2.14: Splice intro/outro BEFORE BGM mixing
  if (S.config.introOutroEnabled && (S.config.introAudioBase64 || S.config.outroAudioBase64)) {
    try {
      resultBuffer = await spliceIntroOutro(resultBuffer);
      appLog('[POST] Intro/outro spliced', 'i');
    } catch(e) {
      appLog('[POST] Intro/outro splice failed: ' + e.message, 'e');
    }
  }

  // Save voice-only WAV
  S.resultWavBlobVoiceOnly = audioBufferToWav(resultBuffer);

  // v2.14: BGM mixing with sidechain ducking
  if (S.config.bgmEnabled && S.config.bgmAudioBase64) {
    try {
      resultBuffer = await mixBgmIntoVoice(resultBuffer);
      appLog('[POST] BGM mixed in', 'i');
    } catch(e) {
      appLog('[POST] BGM mix failed: ' + e.message, 'e');
    }
  }

  S.resultWavBlob = audioBufferToWav(resultBuffer);
}

// ==================== WAV Encoding ====================
function audioBufferToWav(buffer) {
  var numChannels = buffer.numberOfChannels;
  var sampleRate = buffer.sampleRate;
  var bitDepth = 16;
  var bytesPerSample = bitDepth / 8;
  var blockAlign = numChannels * bytesPerSample;
  var dataLength = buffer.length * blockAlign;
  var totalLength = 44 + dataLength;
  var arrayBuffer = new ArrayBuffer(totalLength);
  var view = new DataView(arrayBuffer);

  writeString(view, 0, 'RIFF');
  view.setUint32(4, totalLength - 8, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitDepth, true);
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  var channels = [];
  for (var ch = 0; ch < numChannels; ch++) channels.push(buffer.getChannelData(ch));
  var offset = 44;
  for (var i = 0; i < buffer.length; i++) {
    for (var ch = 0; ch < numChannels; ch++) {
      var sample = Math.max(-1, Math.min(1, channels[ch][i]));
      sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      view.setInt16(offset, sample | 0, true);
      offset += 2;
    }
  }
  return new Blob([arrayBuffer], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
  for (var i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i));
}

// ==================== SRT Generation ====================
function generateSrt() {
  if (S.speakerMode === 'multi') {
    generateSrtMultiSpeaker();
    return;
  }
  var srt = '';
  var subtitleIndex = 1;
  var timeOffset = 0;

  // Use the new reliable line-to-segment mapping
  var segMap = mapOriginalLinesToSegments();

  for (var mi = 0; mi < segMap.length; mi++) {
    var entry = segMap[mi];
    var segDuration = S.segmentDurations[entry.bufIdx] || S.segments[entry.segIdx].duration;

    // Calculate total chars for proportional timing within this segment
    var totalChars = 0;
    for (var li = 0; li < entry.lines.length; li++) totalChars += entry.lines[li].text.length;
    if (totalChars === 0) totalChars = 1;

    // v2.21: compute raw durations then enforce a minimum subtitle duration
    var rawDurs = [];
    for (var li = 0; li < entry.lines.length; li++) {
      rawDurs.push((entry.lines[li].text.length / totalChars) * segDuration);
    }
    rebalanceSrtDurations(rawDurs, 0.6);

    var lineOffset = timeOffset;
    for (var li = 0; li < entry.lines.length; li++) {
      var lineText = entry.lines[li].text;
      var lineDuration = rawDurs[li];
      var cleanText = cleanSubtitleText(lineText);
      if (cleanText) {
        srt += subtitleIndex + '\\n';
        srt += formatSrtTime(lineOffset) + ' --> ' + formatSrtTime(lineOffset + lineDuration) + '\\n';
        srt += cleanText + '\\n\\n';
        subtitleIndex++;
      }
      lineOffset += lineDuration;
    }
    timeOffset += segDuration;
  }
  S.resultSrt = srt;
}

// Multi-speaker SRT: uses segment's built-in lines & speaker info
// (avoids the buggy mapOriginalLinesToSegments which compares raw input with markers
//  against segment text that has markers stripped, causing character-count mismatch)
function generateSrtMultiSpeaker() {
  var srt = '';
  var subtitleIndex = 1;
  var timeOffset = 0;
  var bufIdx = 0;

  for (var si = 0; si < S.segments.length; si++) {
    var seg = S.segments[si];
    if (seg.status !== 'done') continue;

    var segDuration = S.segmentDurations[bufIdx] || seg.duration;
    bufIdx++;

    // Each segment has a 'lines' array from splitTextForTTS (content text without markers)
    var segLines = seg.lines || [];
    // If no lines tracked, auto-break the segment text
    if (segLines.length === 0) {
      segLines = autoBreakSubtitle(seg.text, 15, 5).map(function(t) { return { text: t }; });
    }

    // Calculate total chars for proportional timing
    var totalChars = 0;
    for (var li = 0; li < segLines.length; li++) totalChars += (segLines[li].text || '').length;
    if (totalChars === 0) totalChars = 1;

    // v2.21: compute raw durations then enforce a minimum subtitle duration
    var rawDurs = [];
    for (var li = 0; li < segLines.length; li++) {
      rawDurs.push(((segLines[li].text || '').length / totalChars) * segDuration);
    }
    rebalanceSrtDurations(rawDurs, 0.6);

    var lineOffset = timeOffset;
    for (var li = 0; li < segLines.length; li++) {
      var lineText = segLines[li].text || '';
      var lineDuration = rawDurs[li];
      var cleanText = cleanSubtitleText(lineText);
      if (cleanText) {
        srt += subtitleIndex + '\\n';
        srt += formatSrtTime(lineOffset) + ' --> ' + formatSrtTime(lineOffset + lineDuration) + '\\n';
        if (seg.speaker) {
          cleanText = seg.speaker + '：' + cleanText;
        }
        srt += cleanText + '\\n\\n';
        subtitleIndex++;
      }
      lineOffset += lineDuration;
    }
    timeOffset += segDuration;
  }
  S.resultSrt = srt;
}

// v2.21: rebalance per-line durations so no subtitle is shorter than minSec
// (fixes "这5个字还是贴的特别近"). Time is borrowed from the longest sibling
// within the same segment, so the segment total stays exact.
function rebalanceSrtDurations(durs, minSec) {
  minSec = minSec || 0.6;
  if (!durs || durs.length < 2) return durs;
  var total = 0;
  for (var i = 0; i < durs.length; i++) total += durs[i];
  if (total < minSec * durs.length) return durs; // cannot satisfy, leave as-is
  for (var pass = 0; pass < 3; pass++) {
    var deficit = 0, maxIdx = 0;
    for (var i = 0; i < durs.length; i++) {
      if (durs[i] < minSec) deficit += (minSec - durs[i]);
      if (durs[i] > durs[maxIdx]) maxIdx = i;
    }
    if (deficit <= 0.001) break;
    if (durs[maxIdx] - deficit < minSec) break;
    for (var i = 0; i < durs.length; i++) if (durs[i] < minSec) durs[i] = minSec;
    durs[maxIdx] -= deficit;
    break;
  }
  return durs;
}

// Auto-break text into subtitle lines
// maxLen: max chars per line (including punctuation), default 15
// minLen: min chars per line, default 5
function autoBreakSubtitle(text, maxLen, minLen) {
  if (!text || !text.trim()) return [];
  text = text.trim();
  if (!maxLen) maxLen = 15;
  if (!minLen) minLen = 5;
  if (text.length <= maxLen) return [text];

  // Step 1: Split at punctuation boundaries
  var chunks = [];
  var majorRe = /[，。！？；]/g;
  var last = 0, m;
  while ((m = majorRe.exec(text)) !== null) {
    var c = text.substring(last, m.index + 1);
    if (c) chunks.push(c);
    last = m.index + 1;
  }
  if (last < text.length) chunks.push(text.substring(last));

  // Sub-split chunks exceeding maxLen at minor punctuation
  var refined = [];
  for (var ci = 0; ci < chunks.length; ci++) {
    if (chunks[ci].length <= maxLen) { refined.push(chunks[ci]); continue; }
    var subRe = /[、：""''《》…—,\\s;:-]/g;
    var subLast = 0, sm;
    while ((sm = subRe.exec(chunks[ci])) !== null) {
      var sc = chunks[ci].substring(subLast, sm.index + 1);
      if (sc) refined.push(sc);
      subLast = sm.index + 1;
    }
    if (subLast < chunks[ci].length) refined.push(chunks[ci].substring(subLast));
    if (refined.length === 0) refined.push(chunks[ci]);
  }

  // Step 2: Merge chunks into lines up to maxLen
  var lines = [];
  var cur = '';
  for (var ri = 0; ri < refined.length; ri++) {
    if (cur.length + refined[ri].length <= maxLen) {
      cur += refined[ri];
    } else {
      if (cur) lines.push(cur);
      cur = refined[ri];
    }
  }
  if (cur) lines.push(cur);

  // Step 3: Force-split long lines + merge short lines + clean trailing punctuation
  var result = [];
  for (var li = 0; li < lines.length; li++) {
    var line = lines[li];
    while (line.length > maxLen) {
      var sp = maxLen;
      for (var off = 0; off <= 8 && sp - off > minLen; off++) {
        if (/[，。！？、；：""''《》…—,\\s;:-]/.test(line[sp - off])) { sp = sp - off + 1; break; }
      }
      result.push(line.substring(0, sp));
      line = line.substring(sp);
    }
    if (line) result.push(line);
  }

  // Merge short lines with neighbors
  var merged = [];
  for (var fi = 0; fi < result.length; fi++) {
    var cleaned = result[fi].replace(/[，,。.]+$/, '').trim();
    if (!cleaned) continue;
    if (cleaned.length < minLen && merged.length > 0) {
      var prevClean = merged[merged.length - 1].replace(/[，,。.]+$/, '').trim();
      if (prevClean.length + cleaned.length <= maxLen) {
        merged[merged.length - 1] += result[fi];
      } else {
        merged.push(result[fi]);
      }
    } else {
      merged.push(result[fi]);
    }
  }

  return merged;
}

// ==================== Line-to-Segment Mapping ====================
// Map original input lines to TTS segments using character count accumulation.
// This replaces the buggy getLinesInRange approach that caused:
//   - Duplicate lines (when a line spans two segments)
//   - Missing lines (when position tracking was off)
//   - Misaligned SRT timestamps
function mapOriginalLinesToSegments() {
  var inputText = E.textInput.value;
  var rawLines = inputText.split('\\n');
  var originalLines = [];
  for (var i = 0; i < rawLines.length; i++) {
    var trimmed = rawLines[i].trim();
    if (trimmed) originalLines.push(trimmed);
  }

  // Build the mapping: each segment gets its original lines
  var linePtr = 0; // current position in originalLines
  var result = [];  // array of { segIdx, bufIdx, lines: [{text, charStart, charEnd}] }

  var bufIdx = 0;
  for (var si = 0; si < S.segments.length; si++) {
    var seg = S.segments[si];
    if (seg.status !== 'done') continue;

    var segText = seg.textPlain || seg.text;
    var segTextLen = segText.length;
    var segLines = [];
    var accumulatedLen = 0;

    while (linePtr < originalLines.length) {
      var lineText = originalLines[linePtr];
      var newLen = accumulatedLen + lineText.length;

      // v2.21: no space joining anymore, so length accounting is exact.
      // Allow small tolerance (+3) for minor discrepancies from punctuation differences
      if (newLen <= segTextLen + 3) {
        var charStart = accumulatedLen; // position within the segment text
        segLines.push({ text: lineText, charStart: charStart, charEnd: charStart + lineText.length });
        accumulatedLen = newLen;
        linePtr++;
      } else if (accumulatedLen === 0 && segTextLen > 10 && lineText.length > 10) {
        // v2.21: this single line is longer than the WHOLE segment -> the line
        // was split across segments by the packer. Assign the spoken part to
        // THIS segment and keep the remainder for the next one, so subtitles
        // never show a whole line while only half of it is voiced (fixes
        // "从'的'开始半句在屏幕上"). Prefer splitting at punctuation.
        var limit = segTextLen + 3;
        var splitAt = -1;
        for (var p = limit; p > 5; p--) {
          if (/[，,。！？；、]/.test(lineText.charAt(p - 1))) { splitAt = p; break; }
        }
        if (splitAt < 0) splitAt = limit;
        var part1 = lineText.substring(0, splitAt);
        var rest = lineText.substring(splitAt);
        segLines.push({ text: part1, charStart: 0, charEnd: part1.length });
        originalLines[linePtr] = rest;
        break;
      } else {
        break;
      }
    }

    if (segLines.length === 0) {
      // Fallback: no lines mapped (shouldn't happen normally), use autoBreakSubtitle
      var autoLines = autoBreakSubtitle(segText, 15, 5);
      for (var ai = 0; ai < autoLines.length; ai++) {
        var aCharStart = ai === 0 ? 0 : segLines.length > 0 ? segLines[segLines.length - 1].charEnd : 0;
        segLines.push({ text: autoLines[ai], charStart: aCharStart, charEnd: aCharStart + autoLines[ai].length });
      }
    }

    result.push({ segIdx: si, bufIdx: bufIdx, lines: segLines });
    bufIdx++;
  }

  // Handle remaining original lines that weren't mapped to any segment
  // (e.g., if the last segments failed)
  while (linePtr < originalLines.length) {
    // Assign remaining lines to the last segment if possible, or create estimated entries
    if (result.length > 0) {
      var lastEntry = result[result.length - 1];
      lastEntry.lines.push({ text: originalLines[linePtr], charStart: -1, charEnd: -1 });
    }
    linePtr++;
  }

  return result;
}

function cleanSubtitleText(text) {
  if (!text) return '';
  text = text.trim();
  if (!text) return '';
  // Remove trailing commas and periods, but keep ！？""''《》…—
  text = text.replace(/[，,。.]+$/, '');
  return text;
}

function formatSrtTime(seconds) {
  var h = Math.floor(seconds / 3600);
  var m = Math.floor((seconds % 3600) / 60);
  var s = Math.floor(seconds % 60);
  var ms = Math.round((seconds % 1) * 1000);
  return pad2(h) + ':' + pad2(m) + ':' + pad2(s) + ',' + pad3(ms);
}

function pad2(n) { return n < 10 ? '0' + n : '' + n; }
function pad3(n) { return n < 10 ? '00' + n : (n < 100 ? '0' + n : '' + n); }

// ==================== JianYing Project ZIP ====================
async function downloadJianYing() {
  await loadJSZip();
  if (!S.resultWavBlob) { showToast('请先生成音频', 'error'); return; }
  showToast('正在生成剪映工程...', 'info');
  try {
    var zip = new JSZip();
    var successSegs = S.segments.filter(function(s) { return s.status === 'done'; });
    if (successSegs.length === 0) { showToast('无可用音频段', 'error'); return; }

    // Project folder inside ZIP
    var projectName = S.projectName || 'TTS_Voice_Lab';
    var projectFolder = zip.folder(projectName);

    var audioMaterials = [], audioSegments = [], textMaterials = [], textSegments = [], speedMaterials = [];

    // ===== Calculate total duration =====
    var totalDurationUs = 0;
    var bufIdx = 0;
    var segTimeOffsets = []; // track start time of each segment in microseconds
    var segDurationsUs = []; // track duration of each segment in microseconds
    for (var si = 0; si < S.segments.length; si++) {
      if (S.segments[si].status !== 'done') continue;
      var segDurationSec = S.segmentDurations[bufIdx] || S.segments[si].duration;
      var segDurationUs = Math.round(segDurationSec * 1000000);
      segTimeOffsets.push(totalDurationUs);
      segDurationsUs.push(segDurationUs);
      totalDurationUs += segDurationUs;
      bufIdx++;
    }

    // ===== Single complete audio file =====
    var audioFileName = 'audio_main.wav';
    var audioArrayBuffer = await S.resultWavBlob.arrayBuffer();
    projectFolder.file(audioFileName, audioArrayBuffer);

    // Also include SRT in the project folder
    if (S.resultSrt) {
      projectFolder.file('audio_main.srt', S.resultSrt);
    }

    var audioMatId = hexId(), audioSegId = hexId(), audioSpeedId = hexId();
    audioMaterials.push({
      id: audioMatId, local_material_id: audioMatId, music_id: audioMatId,
      name: audioFileName, path: './' + audioFileName,
      duration: totalDurationUs, type: 'extract_music', category_name: 'local',
      check_flag: 3, local_id: '', source_platform: 0, source: 0, text_id: '', text_source: 0
    });
    speedMaterials.push({ id: audioSpeedId, speed: 1.0, mode: 0, type: 'speed' });
    audioSegments.push({
      id: audioSegId, material_id: audioMatId,
      target_timerange: { start: 0, duration: totalDurationUs },
      source_timerange: { start: 0, duration: totalDurationUs },
      speed: 1.0, volume: 1.0, extra_material_refs: [audioSpeedId],
      is_tone_modify: false, clip: null, render_index: 0, role: 0,
      group_id: '', track_attribute: 0, uniform_scale: null, source: 0
    });

    // ===== Subtitle segments =====
    var subtitleIndex = 0;
    // For multi-speaker mode, use segment's built-in lines to avoid marker mismatch
    var jySubtitleEntries = [];
    if (S.speakerMode === 'multi') {
      var jyBufIdx = 0;
      for (var si2 = 0; si2 < S.segments.length; si2++) {
        var seg2 = S.segments[si2];
        if (seg2.status !== 'done') continue;
        var jyLines = seg2.lines || [];
        if (jyLines.length === 0) {
          jyLines = autoBreakSubtitle(seg2.text, 15, 5).map(function(t) { return { text: t }; });
        }
        jySubtitleEntries.push({ bufIdx: jyBufIdx, lines: jyLines, speaker: seg2.speaker });
        jyBufIdx++;
      }
    } else {
      var segMap = mapOriginalLinesToSegments();
      for (var mi2 = 0; mi2 < segMap.length; mi2++) {
        jySubtitleEntries.push({ bufIdx: segMap[mi2].bufIdx, lines: segMap[mi2].lines, speaker: null });
      }
    }

    for (var ji = 0; ji < jySubtitleEntries.length; ji++) {
      var jyEntry = jySubtitleEntries[ji];
      var segDurationUs2 = segDurationsUs[jyEntry.bufIdx];
      var timeOffsetUs = segTimeOffsets[jyEntry.bufIdx];

      // Calculate total chars for proportional timing
      var totalChars = 0;
      for (var li = 0; li < jyEntry.lines.length; li++) totalChars += (jyEntry.lines[li].text || '').length;
      if (totalChars === 0) totalChars = 1;

      var lineOffsetUs = timeOffsetUs;
      for (var li = 0; li < jyEntry.lines.length; li++) {
        var lineText = jyEntry.lines[li].text || '';
        var lineDurationUs = Math.round((lineText.length / totalChars) * segDurationUs2);
        var cleanText = cleanSubtitleText(lineText);
        // Add speaker label in multi-speaker mode
        if (S.speakerMode === 'multi' && jyEntry.speaker) {
          cleanText = jyEntry.speaker + '：' + cleanText;
        }
        if (cleanText) {
          var textMatId = hexId(), textSegId = hexId(), textSpeedId = hexId();
          var textContent = JSON.stringify({
            styles: [{
              fill: { alpha: 1.0, content: { render_type: 'solid', solid: { alpha: 1.0, color: [1.0, 1.0, 1.0] } } },
              range: [0, cleanText.length], size: 10.0,
              strokes: [{ content: { solid: { alpha: 1.0, color: [0.0, 0.0, 0.0] } }, width: 0.08 }],
              bold: false, italic: false, underline: false
            }],
            text: cleanText
          });
          textMaterials.push({
            id: textMatId, content: textContent, type: 'subtitle',
            typesetting: 0, alignment: 1,
            letter_spacing: 0.0, line_spacing: 0.02,
            line_feed: 1, line_max_width: 0.82, force_apply_line_max_width: false,
            check_flag: 15, global_alpha: 1.0,
            font_id: 'NotoSansSC', font_name: '思源黑体', font_size: 10.0,
            local_id: '', source: 0, text_id: '', text_source: 0,
            path: '', category_id: '', category_name: 'local'
          });
          speedMaterials.push({ id: textSpeedId, speed: 1.0, mode: 0, type: 'speed' });
          textSegments.push({
            id: textSegId, material_id: textMatId,
            target_timerange: { start: lineOffsetUs, duration: lineDurationUs },
            source_timerange: null, speed: 1.0, volume: 1.0,
            clip: { alpha: 1.0, flip: { horizontal: false, vertical: false }, rotation: 0.0, scale: { x: 1.0, y: 1.0 }, transform: { x: 0.0, y: -0.8 } },
            uniform_scale: { on: true, value: 1.0 }, extra_material_refs: [textSpeedId],
            common_keyframes: [], keyframe_refs: [],
            enable_adjust: true, enable_color_correct_adjust: false,
            enable_color_curves: true, enable_color_match_adjust: false,
            enable_color_wheels: true, enable_lut: true, enable_smart_color_adjust: false,
            is_tone_modify: false, last_nonzero_volume: 1.0,
            reverse: false, track_attribute: 0, track_render_index: 0, visible: true
          });
          subtitleIndex++;
        }
        lineOffsetUs += lineDurationUs;
      }
    }

    var draftId = hexId().toUpperCase();
    var draftIdDashed = draftId.substring(0, 8) + '-' + draftId.substring(8, 12) + '-' + draftId.substring(12, 16) + '-' + draftId.substring(16, 20) + '-' + draftId.substring(20, 32);

    var draftContent = {
      id: draftIdDashed,
      canvas_config: { width: 1080, height: 1920, ratio: '9:16' },
      duration: totalDurationUs,
      materials: {
        videos: [], audios: audioMaterials, texts: textMaterials, images: [],
        speeds: speedMaterials, transitions: [], digital_humans: [], material_animations: [],
        effects: [], filters: [], stickers: [], masks: [], ai_transcriptions: [], auto_captions: [],
        sound_channel_mappings: [], bezier_curves: [], clouds: [], flowers: [], frames: [],
        hands: [], head_animations: [], log_color_wheels: [], magic_colors: [], material_colors: [],
        multi_language_refs: [], placeholders: [], primary_color_wheels: [], realtime_denoises: [],
        shape_templates: [], smart_crops: [], sound_effect_metadatas: [], text_templates: [],
        track_groups: [], video_effects: [], video_track_animations: [], vocal_beautifys: [],
        vocal_falsettos: [], video_generators: [],
        crop: { lower_left_x: 0, lower_left_y: 1, upper_right_x: 1, upper_right_y: 0 },
        personality_speaker_infos: [], ocr_text_labels: [], smart_relights: [], materials_changers: [],
        group_res: [], chaos_contents: [], virtual_projections: [], audio_fades: [], audio_effects: [],
        color_curves: [], material_labels: []
      },
      tracks: [
        { id: hexId(), type: 'audio', attribute: 0, flag: 0, is_default: false, segments: audioSegments, track_duration: totalDurationUs },
        { id: hexId(), type: 'text', attribute: 0, flag: 0, is_default: false, segments: textSegments, track_duration: totalDurationUs }
      ],
      metadata: { app_id: 1, app_version: '5.0.0', create_time: Date.now(), draft_id: draftIdDashed, draft_name: projectName, platform: 'windows', source: 0, timeline_materials_size_: 0, timeline_size_: 0, version: 1 },
      last_modified_platform: 'windows', name: projectName, new_version: '',
      platform: { os: 'windows', device: '' }, relationships: [], retouch_cover: '', source: 'default',
      update_time: Date.now(), version: 1
    };

    projectFolder.file('draft_content.json', JSON.stringify(draftContent, null, 2));
    var metaInfo = {
      draft_id: draftIdDashed, draft_name: projectName, draft_deeplink: '', draft_cover: '',
      draft_materials_covers: [], timeline_materials_size_: 0, create_time: Date.now(), update_time: Date.now(),
      is_from_ugc_template: false, is_draft_removed: false, is_invisible: false, source: 'default',
      tm_draft_cloud_id: '', tm_draft_cloud_resource_id: '', draft_cloud_purchase_info: '',
      is_commercialize_music_licensed: false
    };
    projectFolder.file('draft_meta_info.json', JSON.stringify(metaInfo, null, 2));

    var zipBlob = await zip.generateAsync({ type: 'blob' });
    var filename = getDownloadFilename('zip');
    downloadBlob(zipBlob, filename);
    showToast('剪映工程已下载', 'success');
  } catch(e) {
    showToast('生成剪映工程失败: ' + e.message, 'error');
  }
}

// ==================== Downloads ====================
function downloadWav() {
  if (!S.resultWavBlob) { showToast('请先生成音频', 'error'); return; }
  // Direct download from existing blob - no re-synthesis
  downloadBlob(S.resultWavBlob, getDownloadFilename('wav'));
}

function downloadSrt() {
  if (!S.resultSrt) { showToast('请先生成音频', 'error'); return; }
  downloadBlob(new Blob([S.resultSrt], { type: 'text/plain;charset=utf-8' }), getDownloadFilename('srt'));
}

function getDownloadFilename(ext) {
  var name = S.projectName || S.downloadTimestamp || (function() {
    var now = new Date();
    return '' + now.getFullYear() + pad2(now.getMonth() + 1) + pad2(now.getDate()) + '-' + pad2(now.getHours()) + pad2(now.getMinutes()) + pad2(now.getSeconds());
  })();
  return name + '.' + ext;
}

function downloadBlob(blob, filename) {
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ==================== Import/Export ====================
function exportConfig() {
  saveConfig();
  var exportData = {
    version: APP_VERSION,
    config: S.config,
    audioSources: S.audioSources.map(function(src) {
      return { id: src.id, name: src.name, audioBase64: src.audioBase64, nvReferenceId: src.nvReferenceId, kkVoiceId: src.kkVoiceId, addedAt: src.addedAt, lastSyncAt: src.lastSyncAt };
    })
  };
  downloadBlob(new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' }), 'tts-voice-lab-config.json');
  showToast('配置已导出', 'success');
}

function importConfig(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    try {
      var data = JSON.parse(e.target.result);
      if (data.config) {
        Object.keys(data.config).forEach(function(k) { if (S.config[k] !== undefined) S.config[k] = data.config[k]; });
        saveConfig(); applyConfigToUI();
        switchEngine(S.config.engine || 'nicevoice');
      }
      if (data.audioSources && Array.isArray(data.audioSources)) {
        data.audioSources.forEach(function(src) {
          if (!S.audioSources.find(function(s) { return s.name === src.name; })) {
            // Migrate old format
            if (src.dataUrl && !src.audioBase64) src.audioBase64 = src.dataUrl;
            if (!src.kkVoiceId) src.kkVoiceId = null;
            if (!src.lastSyncAt) src.lastSyncAt = null;
            S.audioSources.push(src);
          }
        });
        saveAudioSources(); renderSettingsVoiceList(); renderSpeakerAssignmentList();
      }
      showToast('配置已导入', 'success');
      checkApiStatus();
    } catch(err) { showToast('导入失败: ' + err.message, 'error'); }
  };
  reader.readAsText(file);
  event.target.value = '';
}

// ==================== Settings Panel ====================
function toggleSettings() {
  var panel = E.settingsPanel;
  var overlay = E.settingsOverlay;
  if (panel.classList.contains('open')) {
    panel.classList.remove('open'); overlay.classList.remove('open');
    saveConfig(); checkApiStatus();
  } else {
    applyConfigToUI(); panel.classList.add('open'); overlay.classList.add('open');
  }
}

// v2.22: settings panel has three tabs — 设置 / 历史 / 关于 (README+changelog
// rendered inline; the old history/README modal popups are gone).
function switchSettingsTab(tab) {
  var ids = { settings: 'stabSettings', history: 'stabHistory', about: 'stabAbout' };
  for (var key in ids) {
    var el = document.getElementById(ids[key]);
    if (el) el.style.display = (key === tab) ? '' : 'none';
  }
  var btns = document.querySelectorAll('.st-tab');
  for (var b = 0; b < btns.length; b++) {
    if (btns[b].getAttribute('data-tab') === tab) btns[b].classList.add('active');
    else btns[b].classList.remove('active');
  }
  if (tab === 'history') renderHistoryList();
  if (tab === 'about') E.readmeBody.innerHTML = getReadmeContent();
}

// ==================== History ====================
var historyDB = null;

function openHistoryDB() {
  return new Promise(function(resolve, reject) {
    if (historyDB) { resolve(historyDB); return; }
    var req = indexedDB.open('ttsvoicelab_history', 2);
    req.onupgradeneeded = function(e) {
      var db = e.target.result;
      if (!db.objectStoreNames.contains('records')) {
        db.createObjectStore('records', { keyPath: 'id', autoIncrement: true });
      }
    };
    req.onsuccess = function(e) { historyDB = e.target.result; resolve(historyDB); };
    req.onerror = function(e) { reject(e.target.error); };
  });
}

function openHistory() { if (!E.settingsPanel.classList.contains('open')) toggleSettings(); switchSettingsTab('history'); }
function closeHistory() { switchSettingsTab('settings'); }

async function addHistory(entry) {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readwrite');
    var store = tx.objectStore('records');
    // Store audio blob reference and SRT text
    entry.wavBlob = S.resultWavBlob;
    entry.srtText = S.resultSrt;
    entry.projectName = S.projectName || S.downloadTimestamp || 'audio';
    // v2.16: Store per-segment audio blobs and texts for history edit/restore
    entry.segmentAudios = S.segments.filter(function(s) { return s.status === 'done' && s.audioBlob; }).map(function(s) { return s.audioBlob; });
    entry.segmentTexts = S.segments.map(function(s) { return { text: s.text, speaker: s.speaker, status: s.status, duration: s.duration }; });
    entry.segmentMode = S.speakerMode;
    entry.detectedSpeakers = S.detectedSpeakers.map(function(s) { return { name: s.name, lineCount: s.lineCount, charCount: s.charCount }; });
    entry.speakerAssignments = JSON.parse(JSON.stringify(S.speakerAssignments || {}));
    store.add(entry);

    // Trim to maxHistory
    var countReq = store.count();
    countReq.onsuccess = function() {
      var count = countReq.result;
      if (count > (S.config.maxHistory || 10)) {
        // Get all keys, delete oldest
        var allReq = store.getAllKeys();
        allReq.onsuccess = function() {
          var keys = allReq.result;
          var toDelete = count - (S.config.maxHistory || 10);
          for (var i = 0; i < toDelete; i++) {
            store.delete(keys[i]);
          }
        };
      }
    };
  } catch(e) {
  }
}

async function clearHistory() {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readwrite');
    tx.objectStore('records').clear();
    renderHistoryList();
    showToast('历史记录已清空', 'success');
  } catch(e) {
    showToast('清空历史失败', 'error');
  }
}

async function renderHistoryList() {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readonly');
    var store = tx.objectStore('records');
    var req = store.getAll();
    req.onsuccess = function() {
      var history = req.result.reverse(); // newest first
      var el = E.historyList;
      if (!history.length) { el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text2)">暂无历史记录</div>'; return; }
      var html = '<div style="text-align:right;margin-bottom:8px"><button class="clear-btn" onclick="clearHistory()">清空历史</button></div>';
      history.forEach(function(item) {
        var engLabel = 'NV';
        var hasAudio = !!item.wavBlob;
        // v2.16: Check if segment audios are available for edit/restore
        var hasSegmentAudios = !!(item.segmentAudios && item.segmentAudios.length > 0);
        html += '<div class="history-item">';
        html += '<div class="hi-top"><span class="hi-text">[' + engLabel + '] ' + escHtml(item.projectName || '未命名') + ' — ' + (item.success || 0) + '/' + (item.segments || 0) + ' 段</span><span class="hi-date">' + escHtml(item.date || '') + '</span></div>';
        html += '<div class="hi-detail">' + escHtml(item.text || '') + '</div>';
        if (hasAudio) {
          html += '<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">';
          html += '<button class="clear-btn" onclick="downloadHistoryItem(' + item.id + ',\\'wav\\')" style="color:var(--green);border-color:var(--green)">下载 WAV</button>';
          if (item.srtText) html += '<button class="clear-btn" onclick="downloadHistoryItem(' + item.id + ',\\'srt\\')" style="color:var(--blue);border-color:var(--blue)">下载 SRT</button>';
          // v2.16: Edit button - greyed out if no segment audios
          if (hasSegmentAudios) {
            html += '<button class="clear-btn" onclick="editHistoryItem(' + item.id + ')" style="color:var(--orange);border-color:var(--orange)">' + svgIcon('pen') + ' 编辑</button>';
          } else {
            html += '<button class="clear-btn" disabled style="opacity:0.4;cursor:not-allowed" title="分段音频已丢失，无法编辑">' + svgIcon('pen') + ' 编辑</button>';
          }
          html += '</div>';
        }
        html += '</div>';
      });
      el.innerHTML = html;
    };
  } catch(e) {
  }
}

async function downloadHistoryItem(id, type) {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readonly');
    var store = tx.objectStore('records');
    var req = store.get(id);
    req.onsuccess = function() {
      var item = req.result;
      if (!item) { showToast('记录不存在', 'error'); return; }
      if (type === 'wav' && item.wavBlob) {
        downloadBlob(item.wavBlob, (item.projectName || 'audio') + '.wav');
      } else if (type === 'srt' && item.srtText) {
        downloadBlob(new Blob([item.srtText], { type: 'text/plain;charset=utf-8' }), (item.projectName || 'audio') + '.srt');
      } else {
        showToast('该类型文件不存在', 'error');
      }
    };
  } catch(e) {
    showToast('下载失败', 'error');
  }
}

// v2.16: Edit history item - restore segments to main UI
async function editHistoryItem(id) {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readonly');
    var store = tx.objectStore('records');
    var req = store.get(id);
    req.onsuccess = function() {
      var item = req.result;
      if (!item) { showToast('记录不存在', 'error'); return; }
      if (!item.segmentAudios || item.segmentAudios.length === 0) {
        showToast('分段音频已丢失，无法编辑', 'error');
        return;
      }
      // Close history modal
      closeHistory();
      // Restore segments to S.segments
      S.segments = item.segmentTexts.map(function(t, i) {
        return {
          text: t.text,
          speaker: t.speaker,
          status: t.status === 'done' ? 'done' : 'pending',
          jobId: null,
          audioBlob: item.segmentAudios[i] || null,
          duration: t.duration || 0,
          error: null,
          edited: false
        };
      });
      // Restore speaker mode and detected speakers
      S.speakerMode = item.segmentMode || 'single';
      S.detectedSpeakers = item.detectedSpeakers || [];
      S.speakerAssignments = item.speakerAssignments || {};
      // Restore speaker voice data from current audio sources
      S.speakerVoiceData = {};
      Object.keys(S.speakerAssignments).forEach(function(spName) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[spName]; });
        if (src) S.speakerVoiceData[spName] = buildVoiceDataFromSource(src);
      });
      // Restore result blobs
      S.resultWavBlob = item.wavBlob;
      S.resultSrt = item.srtText || '';
      if (S.resultWavUrl) { URL.revokeObjectURL(S.resultWavUrl); }
      S.resultWavUrl = S.resultWavBlob ? URL.createObjectURL(S.resultWavBlob) : null;
      // Restore text in textarea
      if (item.segmentTexts && item.segmentTexts.length > 0) {
        var fullText = item.segmentTexts.map(function(t) {
          return (t.speaker ? t.speaker + '：' : '') + t.text;
        }).join('\\n\\n');
        E.textInput.value = fullText;
        updateTextStats();
      }
      // Update UI
      renderSegmentTable();
      renderSpeakerAssignmentList();
      if (S.resultWavUrl) {
        E.resultAudio.src = S.resultWavUrl;
        E.resultSection.classList.add('active');
      }
      if (E.metadataCard) E.metadataCard.style.display = 'block';
      showToast('已从历史记录恢复 ' + S.segments.length + ' 段，可点击任意段文本编辑', 'success');
      appLog('[HISTORY-EDIT] Restored ' + S.segments.length + ' segments from history #' + id, 'i');
    };
  } catch(e) {
    showToast('恢复历史记录失败: ' + e.message, 'error');
  }
}

// ==================== README ====================
function showReadme() { if (!E.settingsPanel.classList.contains('open')) toggleSettings(); switchSettingsTab('about'); }
function closeReadme() { switchSettingsTab('settings'); }

function getReadmeContent() {
  // v2.14: README stored as a top-of-file constant for single source of truth.
  // Render the markdown content as preformatted text for simplicity.
  return '<div style="white-space:pre-wrap;font-size:13px;line-height:1.6;font-family:system-ui,sans-serif">' + escHtml(README_CONTENT.replace('$' + '{VERSION}', APP_VERSION)) + '</div>';
}

// ==================== Toast & Helpers ====================
// v2.15: Layout tab switching (narrow screen only)
function switchLayoutTab(tab) {
  var content = document.querySelector('.main-content');
  var log = document.querySelector('.main-log');
  var tabs = document.querySelectorAll('.layout-tab');
  if (!content || !log) return;
  if (tab === 'content') {
    content.classList.remove('hidden-tab');
    log.classList.add('hidden-tab');
    if (tabs[0]) tabs[0].classList.add('active');
    if (tabs[1]) tabs[1].classList.remove('active');
  } else {
    content.classList.add('hidden-tab');
    log.classList.remove('hidden-tab');
    if (tabs[0]) tabs[0].classList.remove('active');
    if (tabs[1]) tabs[1].classList.add('active');
  }
}

function showToast(msg, type) {
  var toast = E.toast;
  toast.textContent = msg;
  toast.className = 'toast ' + (type || 'info');
  toast.offsetHeight;
  toast.classList.add('show');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(function() { toast.classList.remove('show'); }, 3000);
}

function hexId() {
  return 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'.replace(/x/g, function() { return (Math.random() * 16 | 0).toString(16); });
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function sleep(ms) { return new Promise(function(resolve) { setTimeout(resolve, ms); }); }


// ============================================================
// v2.14 New Functions
// ============================================================

// ---- GLM System Prompt Management ----
function resetGlmPrompt() {
  if (!confirm('恢复默认系统提示词？当前自定义内容将被清除。')) return;
  var el = document.getElementById('cfgGlmSystemPrompt');
  if (el) el.value = '';
  S.config.glmSystemPrompt = '';
  saveConfig();
  showToast('已恢复默认提示词', 'success');
}

async function previewGlmProcess() {
  var apiKey = (document.getElementById('cfgGlmApiKey').value || '').trim();
  if (!apiKey) { showToast('请先填写 GLM API Key', 'error'); return; }
  var sample = '测试文本：《飞驰人生3》票房15.08亿元，2026年6月17日上线，3.14、50%、×℃';
  showToast('正在测试...', 'info');
  var result = await glmPreprocessText(sample);
  if (result) {
    alert('原文：\\n' + sample + '\\n\\n处理后：\\n' + result);
  } else {
    showToast('GLM 调用失败，请检查 API Key', 'error');
  }
}

// ---- Before/After Preview ----
async function loadPreview() {
  var text = E.textInput.value.trim();
  if (!text) { showToast('请先输入文本', 'error'); return; }
  var apiKey = S.config.glmApiKey;
  var mode = S.config.glmPreprocess || 'off';
  if (mode === 'off' || !apiKey) {
    showToast('GLM 预处理未启用，跳过预览', 'info');
    return;
  }
  E.previewCard.style.display = 'block';
  E.previewBody.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2)">正在调用 GLM 处理...</div>';
  E.previewBtn.style.display = 'none';
  E.regenGlmBtn.style.display = 'inline-block';

  // Build segments first to know how many to preview
  var maxChars = (S.config.nvMaxChars || 150);
  var segs = [];
  if (S.speakerMode === 'multi') {
    var spGroups = splitTextBySpeakers(text, maxChars);
    for (var gi = 0; gi < spGroups.length; gi++) {
      for (var si = 0; si < spGroups[gi].segments.length; si++) {
        segs.push({ text: spGroups[gi].segments[si].text, speaker: spGroups[gi].speaker });
      }
    }
  } else {
    var plain = splitTextForTTS(text, maxChars);
    segs = plain.map(function(s) { return { text: s.text, speaker: '' }; });
  }

  // Process each segment
  var html = '<table style="width:100%;border-collapse:collapse"><thead><tr><th style="width:5%;padding:6px;border-bottom:1px solid var(--border);text-align:left">#</th><th style="width:42%;padding:6px;border-bottom:1px solid var(--border);text-align:left">Before (原始)</th><th style="width:53%;padding:6px;border-bottom:1px solid var(--border);text-align:left">After (GLM 处理后，可编辑)</th></tr></thead><tbody>';
  for (var i = 0; i < segs.length; i++) {
    var after = await preprocessTextForTTSSmart(segs[i].text);
    var spBadge = segs[i].speaker ? '<span class="seg-speaker sp0">' + escHtml(segs[i].speaker) + '</span> ' : '';
    html += '<tr>';
    html += '<td style="padding:6px;border-bottom:1px solid var(--surface2);vertical-align:top">' + (i+1) + '</td>';
    html += '<td style="padding:6px;border-bottom:1px solid var(--surface2);vertical-align:top;font-size:11px;color:var(--text2)">' + spBadge + escHtml(segs[i].text) + '</td>';
    html += '<td style="padding:4px;border-bottom:1px solid var(--surface2);vertical-align:top"><textarea data-seg-idx="' + i + '" style="width:100%;min-height:60px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical">' + escHtml(after) + '</textarea></td>';
    html += '</tr>';
  }
  html += '</tbody></table>';
  E.previewBody.innerHTML = html;
  E.applyPreviewBtn.style.display = 'inline-block';
  showToast('GLM 预处理完成，可编辑 After 文本', 'success');
}

function applyPreviewAndGenerate() {
  // Collect edited After texts and stash them so startGenerate uses them
  var edits = {};
  var textareas = E.previewBody.querySelectorAll('textarea[data-seg-idx]');
  for (var i = 0; i < textareas.length; i++) {
    edits[textareas[i].getAttribute('data-seg-idx')] = textareas[i].value;
  }
  S.previewEdits = edits;
  E.previewCard.style.display = 'none';
  startGenerate();
}

function onGenerateClick() {
  var mode = S.config.glmPreprocess || 'off';
  var apiKey = S.config.glmApiKey;
  if (mode !== 'off' && apiKey) {
    loadPreview();
  } else {
    startGenerate();
  }
}

// v2.20: One-time dismiss for alternation false positives
var _alternationDismissed = false;
function dismissAlternationWarning() {
  _alternationDismissed = true;
  E.alternationWarning.style.display = 'none';
  appLog('[ALT-DISMISS] 说话人交替警告已忽略', 'i');
}

// ---- Speaker Alternation Check ----
function checkSpeakerAlternation() {
  if (S.speakerMode !== 'multi' || S.segments.length < 2) {
    E.alternationWarning.style.display = 'none';
    return;
  }
  // v2.20: If user previously dismissed, skip check
  if (_alternationDismissed) {
    E.alternationWarning.style.display = 'none';
    return;
  }
  var issues = [];
  for (var i = 1; i < S.segments.length; i++) {
    if (S.segments[i].speaker === S.segments[i-1].speaker) {
      issues.push({ idx: i, speaker: S.segments[i].speaker });
    }
  }
  if (issues.length === 0) {
    E.alternationWarning.style.display = 'none';
    return;
  }
  // Find the "other" speaker
  var otherSpeaker = null;
  for (var j = 0; j < S.detectedSpeakers.length; j++) {
    if (S.detectedSpeakers[j].name !== issues[0].speaker) {
      otherSpeaker = S.detectedSpeakers[j].name;
      break;
    }
  }
  var msg = '检测到 ' + issues.length + ' 处连续同说话人（' + issues[0].speaker + '），可能存在交替遗漏。';
  if (otherSpeaker) {
    msg += '点击"自动交替"将这些段落改为 "' + otherSpeaker + '"。';
  }
  document.getElementById('alternationWarningText').textContent = msg;
  E.alternationWarning.style.display = 'block';
}

function autoFixAlternation() {
  if (S.speakerMode !== 'multi' || S.segments.length < 2) return;
  var speakers = S.detectedSpeakers.map(function(s) { return s.name; });
  if (speakers.length < 2) { showToast('至少需要 2 个说话人', 'error'); return; }
  // Find current speaker of each segment, swap if same as prev
  var curSpeaker = S.segments[0].speaker;
  for (var i = 1; i < S.segments.length; i++) {
    if (S.segments[i].speaker === curSpeaker) {
      // Swap to the other speaker
      var other = speakers.find(function(s) { return s !== curSpeaker; });
      S.segments[i].speaker = other;
      // Also update the speakerVoiceData
      if (S.speakerAssignments[other]) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[other]; });
        if (src) S.speakerVoiceData[other] = buildVoiceDataFromSource(src);
      }
    }
    curSpeaker = S.segments[i].speaker;
  }
  renderSegments();
  checkSpeakerAlternation();
  showToast('已自动交替', 'success');
}

// ---- BGM Upload / Preview ----
function handleBgmUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    S.config.bgmAudioBase64 = e.target.result;
    saveConfig();
    document.getElementById('bgmFileName').textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(1) + 'MB)';
    document.getElementById('cfgBgmEnabled').checked = true;
    S.config.bgmEnabled = true;
    saveConfig();
    renderBgmStatus();
    showToast('BGM 已加载', 'success');
  };
  reader.readAsDataURL(file);
}

function clearBgm() {
  S.config.bgmAudioBase64 = '';
  S.config.bgmEnabled = false;
  saveConfig();
  document.getElementById('bgmFileName').textContent = '';
  document.getElementById('cfgBgmEnabled').checked = false;
  renderBgmStatus();
  showToast('BGM 已清除', 'info');
}

function renderBgmStatus() {
  var el = document.getElementById('bgmFileName');
  if (!el) return;
  if (S.config.bgmAudioBase64) {
    el.textContent = '已加载 BGM（点击试听）';
  } else {
    el.textContent = '未选择 BGM';
  }
}

var _bgmPreviewAudio = null;
function previewBgm() {
  if (!S.config.bgmAudioBase64) { showToast('请先选择 BGM', 'error'); return; }
  var btn = document.querySelector('button[onclick="previewBgm()"]');
  if (_bgmPreviewAudio) {
    _bgmPreviewAudio.pause();
    _bgmPreviewAudio = null;
    if (btn) btn.innerHTML = svgIcon('play') + ' 试听';
    return;
  }
  _bgmPreviewAudio = new Audio(S.config.bgmAudioBase64);
  _bgmPreviewAudio.volume = Math.sqrt(S.config.bgmVolume || 0.126);
  _bgmPreviewAudio.play().then(function() {
    if (btn) btn.innerHTML = svgIcon('pause') + ' 停止';
  }).catch(function() { showToast('播放失败', 'error'); });
  _bgmPreviewAudio.onended = function() {
    _bgmPreviewAudio = null;
    if (btn) btn.innerHTML = svgIcon('play') + ' 试听';
  };
  _bgmPreviewAudio.onerror = function() {
    _bgmPreviewAudio = null;
    if (btn) btn.innerHTML = svgIcon('play') + ' 试听';
    showToast('播放失败', 'error');
  };
}

// ---- Intro/Outro Upload ----
function handleIntroUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    S.config.introAudioBase64 = e.target.result;
    saveConfig();
    document.getElementById('introFileName').textContent = file.name;
    if (!S.config.outroAudioBase64) {
      document.getElementById('cfgIntroOutroEnabled').checked = true;
      S.config.introOutroEnabled = true;
    }
    saveConfig();
    renderIntroOutroStatus();
    showToast('片头已加载', 'success');
  };
  reader.readAsDataURL(file);
}

function handleOutroUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    S.config.outroAudioBase64 = e.target.result;
    saveConfig();
    document.getElementById('outroFileName').textContent = file.name;
    if (!S.config.introAudioBase64) {
      document.getElementById('cfgIntroOutroEnabled').checked = true;
      S.config.introOutroEnabled = true;
    }
    saveConfig();
    renderIntroOutroStatus();
    showToast('片尾已加载', 'success');
  };
  reader.readAsDataURL(file);
}

function clearIntro() {
  S.config.introAudioBase64 = '';
  saveConfig();
  document.getElementById('introFileName').textContent = '';
  renderIntroOutroStatus();
  showToast('片头已清除', 'info');
}

function clearOutro() {
  S.config.outroAudioBase64 = '';
  saveConfig();
  document.getElementById('outroFileName').textContent = '';
  renderIntroOutroStatus();
  showToast('片尾已清除', 'info');
}

function renderIntroOutroStatus() {
  var introEl = document.getElementById('introFileName');
  var outroEl = document.getElementById('outroFileName');
  if (introEl) introEl.textContent = S.config.introAudioBase64 ? '已加载片头' : '未选择';
  if (outroEl) outroEl.textContent = S.config.outroAudioBase64 ? '已加载片尾' : '未选择';
}

// ---- Voice Volume Normalization ----
function computePeak(buffer) {
  var peak = 0;
  for (var ch = 0; ch < buffer.numberOfChannels; ch++) {
    var data = buffer.getChannelData(ch);
    for (var i = 0; i < data.length; i++) {
      var abs = Math.abs(data[i]);
      if (abs > peak) peak = abs;
    }
  }
  return peak;
}

function computeRms(buffer) {
  var sum = 0;
  var count = 0;
  for (var ch = 0; ch < buffer.numberOfChannels; ch++) {
    var data = buffer.getChannelData(ch);
    for (var i = 0; i < data.length; i++) {
      sum += data[i] * data[i];
      count++;
    }
  }
  return Math.sqrt(sum / Math.max(1, count));
}

function applyGainToBuffer(buffer, gain) {
  // Returns a NEW buffer with gain applied
  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  var out = audioCtx.createBuffer(buffer.numberOfChannels, buffer.length, buffer.sampleRate);
  for (var ch = 0; ch < buffer.numberOfChannels; ch++) {
    var src = buffer.getChannelData(ch);
    var dst = out.getChannelData(ch);
    for (var i = 0; i < src.length; i++) dst[i] = src[i] * gain;
  }
  audioCtx.close();
  return out;
}

function normalizeVoiceBuffers(buffers, speakers, segments) {
  // 1. Peak normalize each buffer to targetPeakDb
  var targetDb = S.config.voiceTargetPeakDb || -3;
  var targetPeak = Math.pow(10, targetDb / 20);
  var peakGains = [];
  for (var i = 0; i < buffers.length; i++) {
    var peak = computePeak(buffers[i]);
    var g = peak > 0 ? Math.min(2, targetPeak / peak) : 1;
    peakGains.push(g);
    buffers[i] = applyGainToBuffer(buffers[i], g);
  }
  // 2. Per-speaker RMS equalize
  if (S.config.speakerRmsEqualize && speakers && segments) {
    var spRms = {};
    var spCount = {};
    for (var j = 0; j < buffers.length; j++) {
      var sp = segments[j] ? (segments[j].speaker || '默认') : '默认';
      if (!spRms[sp]) { spRms[sp] = 0; spCount[sp] = 0; }
      spRms[sp] += computeRms(buffers[j]);
      spCount[sp]++;
    }
    var spAvgRms = {};
    var maxAvg = 0;
    Object.keys(spRms).forEach(function(k) {
      spAvgRms[k] = spRms[k] / Math.max(1, spCount[k]);
      if (spAvgRms[k] > maxAvg) maxAvg = spAvgRms[k];
    });
    Object.keys(spAvgRms).forEach(function(k) {
      var g = maxAvg > 0 ? Math.min(2, maxAvg / spAvgRms[k]) : 1;
      spAvgRms[k] = g;
    });
    for (var k = 0; k < buffers.length; k++) {
      var spk = segments[k] ? (segments[k].speaker || '默认') : '默认';
      if (spAvgRms[spk]) {
        buffers[k] = applyGainToBuffer(buffers[k], spAvgRms[spk]);
      }
    }
    appLog('[NORM] Per-speaker RMS gains: ' + JSON.stringify(spAvgRms), 'i');
  }
  appLog('[NORM] Peak normalize gains: ' + peakGains.map(function(g) { return g.toFixed(3); }).join(', '), 'i');
  return buffers;
}

// ---- BGM Mixing with Sidechain Ducking ----
async function mixBgmIntoVoice(voiceBuffer) {
  if (!S.config.bgmEnabled || !S.config.bgmAudioBase64) return voiceBuffer;
  showToast('正在混入 BGM...', 'info');
  // Decode BGM
  var bgmArrayBuffer = dataUrlToArrayBuffer(S.config.bgmAudioBase64);
  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  var bgmBuffer;
  try {
    bgmBuffer = await audioCtx.decodeAudioData(bgmArrayBuffer);
  } catch(e) {
    audioCtx.close();
    showToast('BGM 解码失败: ' + e.message, 'error');
    return voiceBuffer;
  }
  var sampleRate = voiceBuffer.sampleRate;
  var channels = Math.max(voiceBuffer.numberOfChannels, bgmBuffer.numberOfChannels);
  var totalDuration = voiceBuffer.duration;
  // Loop BGM if shorter than voice
  var offlineCtx = new OfflineAudioContext(channels, Math.ceil(totalDuration * sampleRate), sampleRate);
  // Voice source
  var voiceSrc = offlineCtx.createBufferSource();
  voiceSrc.buffer = voiceBuffer;
  var voiceGain = offlineCtx.createGain();
  voiceGain.gain.value = 1.0;
  voiceSrc.connect(voiceGain);
  voiceGain.connect(offlineCtx.destination);
  voiceSrc.start(0);
  // BGM source (loop)
  var bgmSrc = offlineCtx.createBufferSource();
  bgmSrc.buffer = bgmBuffer;
  bgmSrc.loop = true;
  var bgmGain = offlineCtx.createGain();
  var bgmVol = S.config.bgmVolume || 0.126;
  var duckDepth = S.config.bgmDuckDepth || 0.5;
  var fadeMs = S.config.bgmDuckFadeMs || 300;
  var fadeSec = fadeMs / 1000;
  // Build ducking automation: BGM at full volume from 0, duck down at voice start, recover at voice end
  bgmGain.gain.setValueAtTime(bgmVol, 0);
  bgmGain.gain.setValueAtTime(bgmVol, 0);
  bgmGain.gain.linearRampToValueAtTime(bgmVol * duckDepth, Math.min(fadeSec, totalDuration));
  // Stay ducked through the voice
  bgmGain.gain.setValueAtTime(bgmVol * duckDepth, Math.max(0, totalDuration - fadeSec));
  bgmGain.gain.linearRampToValueAtTime(bgmVol, totalDuration);
  bgmSrc.connect(bgmGain);
  bgmGain.connect(offlineCtx.destination);
  bgmSrc.start(0);
  var rendered = await offlineCtx.startRendering();
  audioCtx.close();
  return rendered;
}

function dataUrlToArrayBuffer(dataUrl) {
  var base64 = dataUrl.split(',')[1] || dataUrl;
  var binary = atob(base64);
  var bytes = new Uint8Array(binary.length);
  for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

// ---- Intro/Outro Splicing (port from podmerge.html) ----
async function spliceIntroOutro(mainBuffer) {
  if (!S.config.introOutroEnabled) return mainBuffer;
  if (!S.config.introAudioBase64 && !S.config.outroAudioBase64) return mainBuffer;
  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  var introBuffer = null, outroBuffer = null;
  try {
    if (S.config.introAudioBase64) {
      introBuffer = await audioCtx.decodeAudioData(dataUrlToArrayBuffer(S.config.introAudioBase64));
    }
    if (S.config.outroAudioBase64) {
      outroBuffer = await audioCtx.decodeAudioData(dataUrlToArrayBuffer(S.config.outroAudioBase64));
    }
  } catch(e) {
    audioCtx.close();
    showToast('片头/片尾解码失败: ' + e.message, 'error');
    return mainBuffer;
  }
  var sampleRate = mainBuffer.sampleRate;
  var channels = mainBuffer.numberOfChannels;
  var fadeSec = (S.config.introOutroFadeMs || 500) / 1000;
  var mode = S.config.introOutroMode || 'fade';

  var introDur = introBuffer ? introBuffer.duration : 0;
  var outroDur = outroBuffer ? outroBuffer.duration : 0;
  var totalDuration = introDur + mainBuffer.duration + outroDur;
  var offlineCtx = new OfflineAudioContext(channels, Math.ceil(totalDuration * sampleRate), sampleRate);

  var introSrc = introBuffer ? offlineCtx.createBufferSource() : null;
  var mainSrc = offlineCtx.createBufferSource();
  var outroSrc = outroBuffer ? offlineCtx.createBufferSource() : null;
  if (introSrc) introSrc.buffer = introBuffer;
  mainSrc.buffer = mainBuffer;
  if (outroSrc) outroSrc.buffer = outroBuffer;

  var introGain = offlineCtx.createGain();
  var mainGain = offlineCtx.createGain();
  var outroGain = offlineCtx.createGain();

  var outroStartTime = introDur + mainBuffer.duration;

  if (mode === 'fade' && fadeSec > 0) {
    if (introSrc) {
      introGain.gain.setValueAtTime(1, 0);
      introGain.gain.setValueAtTime(1, Math.max(0, introDur - fadeSec));
      introGain.gain.linearRampToValueAtTime(0, introDur);
    }
    mainGain.gain.setValueAtTime(0, introDur);
    mainGain.gain.linearRampToValueAtTime(1, introDur + fadeSec);
    mainGain.gain.setValueAtTime(1, Math.max(introDur + fadeSec, outroStartTime - fadeSec));
    mainGain.gain.linearRampToValueAtTime(0, outroStartTime);
    if (outroSrc) {
      outroGain.gain.setValueAtTime(0, outroStartTime);
      outroGain.gain.linearRampToValueAtTime(1, outroStartTime + fadeSec);
    }
  } else {
    if (introSrc) introGain.gain.setValueAtTime(1, 0);
    mainGain.gain.setValueAtTime(1, introDur);
    if (outroSrc) outroGain.gain.setValueAtTime(1, outroStartTime);
  }

  if (introSrc) { introSrc.connect(introGain); introGain.connect(offlineCtx.destination); introSrc.start(0); }
  mainSrc.connect(mainGain); mainGain.connect(offlineCtx.destination); mainSrc.start(introDur);
  if (outroSrc) { outroSrc.connect(outroGain); outroGain.connect(offlineCtx.destination); outroSrc.start(outroStartTime); }

  var rendered = await offlineCtx.startRendering();
  audioCtx.close();
  return rendered;
}

// ---- Podcast Metadata Generation ----
async function generateMetadata() {
  var apiKey = S.config.glmApiKey;
  if (!apiKey) { showToast('请先在设置中填入 GLM API Key', 'error'); return; }
  var text = E.textInput.value.trim();
  if (!text) { showToast('文本为空', 'error'); return; }
  E.genMetadataBtn.disabled = true;
  E.genMetadataBtn.innerHTML = svgIcon('refresh') + ' 正在生成...';
  showToast('正在调用 GLM 生成元数据...', 'info');
  var systemPrompt = '你是一个播客元数据生成助手，专为《娱乐资本论·娱资每日早报》设计。\\\\n'
    + '根据用户提供的播客台词文本（以及可选的原始新闻要点），生成以下三项内容：\\\\n'
    + '\\\\n'
    + '1. title: 标题必须严格遵循格式 "<月份>月<日期>日娱资每日早报：<核心内容概括>"，其中月份和日期从台词中提取（如台词中出现"6月18日"则标题为"6月18日娱资每日早报：<概括>"）。概括部分用 8-15 字简洁表达本期最核心的新闻主题，不要使用"等等""多个"等模糊词，可适当具象化（例如"6月18日娱资每日早报：TikTok短剧分账破亿，黑神话悟空销量破三千万"）。\\\\n'
    + '\\\\n'
    + '2. shownotes: 按以下结构输出（保留"关键词："、"本期主要内容："、"章节速览"、"关于《娱乐资本论》"、"欢迎全平台搜索关注【娱乐资本论】"等小标题，每节之间用空行分隔）：\\\\n'
    + '   关键词：\\\\n'
    + '   <15-20 个中文关键词，逗号分隔，覆盖本期所有新闻的核心名词与产业概念>\\\\n'
    + '   \\\\n'
    + '   本期主要内容：\\\\n'
    + '   <3-5 句中文摘要，概括本期 10 条新闻的核心信息流，体现产业逻辑而非简单罗列>\\\\n'
    + '   \\\\n'
    + '   章节速览\\\\n'
    + '   <按 00:00 / 00:30 / 01:00 等时间戳格式列出 5-8 个章节，每个章节标题对应一组相关新闻>\\\\n'
    + '   \\\\n'
    + '   关于《娱乐资本论》\\\\n'
    + '   <固定栏目介绍：娱乐资本论——中国娱乐产业第一垂直新媒体。我们关注文化的产业融合，影视的真挚表达，互联网娱乐的时代精神。如今，娱乐资本论的关注视角不仅仅局限在影视综、明星经济，现已快速覆盖至微短剧、互联网、电商、营销等多元领域，并致力于产出全网最优质的独家报道。娱乐资本论是北京市文化产业投融资协会会员单位，并与中国网络视听大会、北京国际电影节、上海国际电影节等行业大会展开了长期、深度的合作。>\\\\n'
    + '   \\\\n'
    + '   欢迎全平台搜索关注【娱乐资本论】\\\\n'
    + '\\\\n'
    + '3. tags: 8-12 个中文标签，逗号分隔，覆盖本期新闻涉及的产业领域、公司、产品名、技术概念等。\\\\n'
    + '\\\\n'
    + '严格按 JSON 格式输出：{"title":"...","shownotes":"...","tags":"标签1,标签2,..."}\\\\n'
    + '不要添加解释或 markdown 代码块标记。shownotes 字段内的换行用 \\\\n 表示。';
  try {
    var resp = await fetch('/api/glm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        apiKey: apiKey,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: (function() {
            var rawNews = document.getElementById('metadataRawNews') ? document.getElementById('metadataRawNews').value.trim() : '';
            var userContent = '【播客台词文本】\\n' + text.substring(0, 3500);
            if (rawNews) {
              userContent += '\\n\\n【原始新闻要点（用户补充）】\\n' + rawNews.substring(0, 1500);
            }
            return userContent;
          })() }
        ]
      })
    });
    var data = await resp.json();
    if (data.choices && data.choices[0]) {
      var content = data.choices[0].message.content.trim();
      // Strip code fences if present (escape backticks since we are inside template literal)
      var fence = String.fromCharCode(96);
      var fenceRe = new RegExp('^' + fence + fence + fence + 'json\\\\s*', 'i');
      var fenceRe2 = new RegExp('^' + fence + fence + fence + '\\\\s*');
      var fenceRe3 = new RegExp(fence + fence + fence + '\\\\s*$', '');
      content = content.replace(fenceRe, '').replace(fenceRe2, '').replace(fenceRe3, '');
      var parsed = JSON.parse(content);
      document.getElementById('metadataResult').style.display = 'block';
      document.getElementById('metadataTitle').value = parsed.title || '';
      document.getElementById('metadataShownotes').value = parsed.shownotes || '';
      document.getElementById('metadataTags').value = parsed.tags || '';
      showToast('元数据生成完成', 'success');
    } else {
      showToast('GLM 返回异常', 'error');
    }
  } catch(e) {
    showToast('生成失败: ' + e.message, 'error');
  } finally {
    E.genMetadataBtn.disabled = false;
    E.genMetadataBtn.innerHTML = svgIcon('spark') + ' 生成标题/摘要/标签';
  }
}

function copyMetadata() {
  var title = document.getElementById('metadataTitle').value;
  var shownotes = document.getElementById('metadataShownotes').value;
  var tags = document.getElementById('metadataTags').value;
  var text = '标题：' + title + '\\n\\nShownotes：\\n' + shownotes + '\\n\\nTags：' + tags;
  navigator.clipboard.writeText(text).then(function() {
    showToast('已复制到剪贴板', 'success');
  }).catch(function() {
    showToast('复制失败', 'error');
  });
}

// ---- v2.14 downloadWavVoiceOnly ----
function downloadWavVoiceOnly() {
  if (!S.resultWavBlobVoiceOnly) {
    showToast('纯人声版本不可用，请先合成', 'error');
    return;
  }
  var name = (S.projectName || S.downloadTimestamp || 'tts') + '-voiceonly.wav';
  downloadBlob(S.resultWavBlobVoiceOnly, name);
}
</script>
</body>
</html></html>`;
}
// v2.21.0 source — channel cleanup + NiceVoice input-layer fixes, deployed 2026-09-29

