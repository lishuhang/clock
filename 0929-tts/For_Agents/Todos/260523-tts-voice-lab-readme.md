---
AIGC: {"Label":"1","ContentProducer":"001191110108MA01KP2T5U00000","ProduceID":"ed02e153b15b3c7a77d338b848a67f20","ReservedCode1":"","ContentPropagator":"001191110108MA01KP2T5U00000","PropagateID":"ed02e153b15b3c7a77d338b848a67f20","ReservedCode2":""}
---

# TTS Voice Lab - 完整使用与编程指南

> 版本: v1.3 | 源码: `tts-voice-lab-1.3.js` | 部署地址: `tts.lishuhang.workers.dev`

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 人类使用指南](#2-人类使用指南)
  - [2.1 三步上手](#21-三步上手)
  - [2.2 模型速查表](#22-模型速查表)
  - [2.3 语音克隆操作指南](#23-语音克隆操作指南)
  - [2.4 闭源模型 API Key 配置](#24-闭源模型-api-key-配置)
  - [2.5 高级功能](#25-高级功能)
  - [2.6 常见使用问题](#26-常见使用问题)
- [3. AI Agent 编程指南](#3-ai-agent-编程指南)
  - [3.1 架构概览](#31-架构概览)
  - [3.2 Worker 路由与 API 端点](#32-worker-路由与-api-端点)
  - [3.3 Gradio Queue API 调用流程](#33-gradio-queue-api-调用流程)
  - [3.4 各模型 API 调用详解](#34-各模型-api-调用详解)
  - [3.5 闭源模型代理调用](#35-闭源模型代理调用)
  - [3.6 前端状态管理](#36-前端状态管理)
  - [3.7 数据流全链路](#37-数据流全链路)
- [4. Debug 方向与排障指南](#4-debug-方向与排障指南)
  - [4.1 按症状索引](#41-按症状索引)
  - [4.2 HF Spaces 相关问题](#42-hf-spaces-相关问题)
  - [4.3 闭源模型常见错误](#43-闭源模型常见错误)
  - [4.4 前端渲染问题](#44-前端渲染问题)
- [5. 踩坑预警与注意事项](#5-踩坑预警与注意事项)
  - [5.1 安全相关](#51-安全相关)
  - [5.2 代码缺陷与已知 Bug](#52-代码缺陷与已知-bug)
  - [5.3 架构限制](#53-架构限制)
  - [5.4 运维与部署注意](#54-运维与部署注意)
  - [5.5 兼容性与边界情况](#55-兼容性与边界情况)
- [6. 自包含 README 与 CHANGELOG 原文](#6-自包含-readme-与-changelog-原文)
  - [6.1 代码内嵌 README](#61-代码内嵌-readme)
  - [6.2 代码内嵌 CHANGELOG](#62-代码内嵌-changelog)
- [7. Changelog](#7-changelog)

---

## 1. 项目概述

TTS Voice Lab 是一个部署在 Cloudflare Workers 上的单文件全栈 TTS (Text-to-Speech) 试用平台。它将前端 SPA、后端 API 代理和模型定义全部打包在一个 JS 文件中，无需构建步骤，直接部署到 Cloudflare Workers 即可运行。

**核心特性:**

- **9 个 TTS 模型集成**: 6 个开源模型（通过 HuggingFace Spaces 的 Gradio API）+ 3 个闭源模型（通过 Worker 代理的 REST API）
- **语音克隆**: F5-TTS、IndexTTS-2、SparkTTS 支持上传参考音频进行零样本声音克隆
- **8 维情感控制**: IndexTTS-2 提供开心/愤怒/悲伤/恐惧/厌恶/忧郁/惊讶/平静的精细情感调节
- **情感标记**: Orpheus TTS 支持 `<laugh>`、`<sigh>`、`<giggle>` 等 XML 式情感标记
- **多 Token 轮换**: 支持配置多个 HuggingFace Token，一个失败自动切换下一个
- **浏览器本地记忆**: 模型选择、声线、参数、参考音频均持久化到 localStorage
- **三面板响应式布局**: 宽屏并排、窄屏上下排列，900px 断点自适应

**技术栈:** Cloudflare Workers (ES Module export) + 原生 HTML/CSS/JS SPA，无框架依赖。

---

## 2. 人类使用指南

### 2.1 三步上手

1. **选择模型**: 左侧面板浏览模型列表，点击选择。绿色标签=免费开源模型，红色标签=需要 API Key 的闭源模型，克隆标签=支持语音克隆。可使用搜索框按名称/功能/语言过滤。
2. **声音设置**: 中间面板根据模型类型配置声线（预设声线选择 / 上传参考音频 / 情感滑块调节）和模型参数（语速、音调、温度等）。
3. **合成语音**: 右侧面板输入要合成的文本，点击"生成语音"按钮，等待生成完成后试听、下载或复制提示词。

### 2.2 模型速查表

| 模型 | 类型 | 声音模式 | 特色 | 费用 |
|------|------|----------|------|------|
| Edge TTS | 开源 | 预设声线 (323种) | 100+语言，SSML支持，语速/音调控制 | 免费 |
| F5-TTS | 开源 | 语音克隆 | 零样本克隆，情感保持 | 免费 |
| IndexTTS-2 | 开源 | 语音克隆 | 8维情感，中文优化，采样参数 | 免费 |
| Kokoro-82M | 开源 | 预设声线 (10种) | 仅82M参数，Apache协议可商用 | 免费 |
| Orpheus TTS | 开源 | 预设声线 (8种) | 情感标记，LLaMA架构 | 免费 |
| SparkTTS | 开源 | 克隆+属性控制 | 0.5B参数，性别/音高/语速属性 | 免费 |
| OpenAI TTS | 闭源 | 预设声线 (6种) | 高质量自然语音，tts-1/tts-1-hd | $0.015~0.030/1K字符 |
| ElevenLabs | 闭源 | 预设声线 (9种) | 专业级质量，稳定性/相似度/风格调节 | 免费10K字符/月 |
| MiniMax Speech | 闭源 | 预设声线 (10种) | TTS Arena第一，300+声线，音调/音量调节 | 免费额度有限 |

### 2.3 语音克隆操作指南

支持语音克隆的模型: F5-TTS、IndexTTS-2、SparkTTS (克隆模式)。

**操作步骤:**

1. 选择支持克隆的模型后，中间面板会显示"上传参考音频"区域。
2. 点击上传区域或拖拽音频文件（支持 WAV/MP3/FLAC 等格式）。
3. **重要**: 在"参考文本"输入框中填写参考音频中说的话。参考文本与音频内容的匹配度直接影响克隆质量，匹配度越高效果越好。
4. 在右侧面板输入要合成的新文本，点击生成。

**参考音频最佳实践:**

- 时长: 5-15 秒为最佳，过短克隆质量下降，过长增加推理延迟
- 质量: 清晰、无背景噪音、无混响的录音
- 语言: 参考音频和目标文本的语言一致时效果最好
- 内容: 自然语速，避免夸张的语调

**参考音频存储说明:** 上传的参考音频以 base64 DataURL 形式存储在浏览器 localStorage 中，不会上传到服务器持久保存。这意味着清除浏览器数据会丢失参考音频。

### 2.4 闭源模型 API Key 配置

1. 点击右上角"设置"按钮打开设置面板。
2. 在"API 密钥"部分找到对应模型的输入框，粘贴 API Key。
3. 所有 Key 仅存储在浏览器 localStorage 中，不会上传到服务器。
4. 点击"保存设置"完成配置。

**获取 API Key:**
- OpenAI: `sk-...` 格式，从 [platform.openai.com](https://platform.openai.com) 获取
- ElevenLabs: `xi-...` 格式，从 [elevenlabs.io](https://elevenlabs.io) 获取
- MiniMax: 从 [platform.minimaxi.com](https://platform.minimaxi.com) 获取

### 2.5 高级功能

**SSML 标记 (Edge TTS):** 在文本中使用以下标记精细控制语音:

```xml
<break time="500ms"/>               <!-- 插入停顿 -->
<prosody rate="fast">语速变化</prosody>  <!-- 局部语速调整 -->
<emphasis>重音</emphasis>            <!-- 强调 -->
```

**情感标记 (Orpheus TTS):** 在文本中嵌入 XML 式情感标记:

```xml
<laugh>哈哈哈</laugh>     <!-- 笑声 -->
<sigh>唉</sigh>           <!-- 叹气 -->
<giggle>嘻嘻</giggle>     <!-- 咯咯笑 -->
<cough>咳咳</cough>       <!-- 咳嗽 -->
<sniffle>...</sniffle>    <!-- 吸鼻子 -->
<groan>...</groan>        <!-- 呻吟 -->
<yawn>...</yawn>          <!-- 哈欠 -->
```

**8 维情感控制 (IndexTTS-2):** 使用滑块调节 8 个情感维度:

| 维度 | 含义 | 默认值 | 建议范围 |
|------|------|--------|----------|
| 开心 | 愉悦程度 | 0 | 0-0.8 |
| 愤怒 | 生气程度 | 0 | 0-0.6 |
| 悲伤 | 低落程度 | 0 | 0-0.6 |
| 恐惧 | 害怕程度 | 0 | 0-0.5 |
| 厌恶 | 反感程度 | 0 | 0-0.5 |
| 忧郁 | 忧伤程度 | 0 | 0-0.6 |
| 惊讶 | 诧异程度 | 0 | 0-0.5 |
| 平静 | 安宁程度 | 0.5 | 0.3-1.0 |

情感维度之间可以组合使用（如开心+惊讶），但建议总激活值不超过 1.5 以避免声音失真。平静维度默认 0.5 作为基准，降低平静值会让声音显得不自然。

**多 Token 轮换:** 在设置面板中配置"备用 HF Token"（逗号分隔），当一个 HuggingFace Token 额度用尽或报错时，系统会自动切换到下一个 Token 重试。

### 2.6 常见使用问题

**Q: 生成失败，提示"API调用失败"或"生成超时"?**
A: HuggingFace Spaces 的免费实例会在闲置时休眠，首次请求需要唤醒（可能需要 1-3 分钟）。等待一段时间后重试。如果持续失败，可能是 Space 维护或下线。

**Q: 闭源模型提示"请先在设置中配置 API Key"?**
A: 需要在设置面板中配置对应模型的 API Key 并点击保存。

**Q: 生成的音频播放不了或下载后损坏?**
A: 开源模型生成的音频 URL 来自 HuggingFace Spaces 的临时文件，Space 重启后文件会被清除。建议及时下载。闭源模型的音频使用 Blob URL，页面刷新后会丢失。

**Q: 语音克隆效果不好?**
A: (1) 确保参考音频清晰无噪音；(2) 务必填写参考文本且与音频内容完全匹配；(3) 参考音频时长控制在 5-15 秒；(4) 尝试不同的模型——F5-TTS 适合英文，IndexTTS-2 适合中文。

**Q: Edge TTS 的声线 ID 格式很奇怪?**
A: Edge TTS 的声线 ID 格式为 `语音名 - 语言代码 (性别)`，如 `zh-CN-XiaoxiaoNeural - zh-CN (Female)`。这是 HF Space 封装后的格式，包含了语言和性别信息。

---

## 3. AI Agent 编程指南

### 3.1 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                Cloudflare Worker (单文件)                  │
│                                                          │
│  ┌────────────────┐  ┌─────────────────────────────────┐ │
│  │  MODEL DEFS    │  │  Worker fetch handler            │ │
│  │  (9 models)    │  │  ├── / → 返回前端 SPA HTML       │ │
│  │                │  │  ├── /api/hf/call → Gradio POST  │ │
│  │  getFrontend   │  │  ├── /api/hf/poll → Gradio 轮询  │ │
│  │  HTML()        │  │  ├── /api/hf/upload → 文件上传   │ │
│  │                │  │  ├── /api/proxy/openai            │ │
│  │                │  │  ├── /api/proxy/elevenlabs        │ │
│  │                │  │  └── /api/proxy/minimax           │ │
│  └────────────────┘  └─────────────────────────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Frontend SPA (嵌入在 getFrontendHTML() 返回值中)      │ │
│  │  ├── state 对象 (选中模型/声线/配置/文本/结果)          │ │
│  │  ├── localStorage 持久化 (tts_memory, tts_history)    │ │
│  │  ├── 渲染函数 (ModelList/VoicePanel/TextPanel/Results) │ │
│  │  ├── API 调用函数 (gradioCall/gradioPoll/callXxx)     │ │
│  │  └── 结果管理 (下载/复制/复用/历史)                     │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**关键设计决策:**

- 前端通过 Worker 代理调用 HF Spaces API，而非直接调用，原因是 HuggingFace Spaces 对嵌入式 iframe 有跨域限制，Worker 代理绕过了 CORS 和嵌入限制。
- 闭源模型的 API Key 从前端 localStorage 读取，随请求发送到 Worker 代理，Worker 不存储任何 Key。
- `MODELS` 数组通过 `JSON.stringify(MODELS)` 注入前端 `<script>`，前后端共享同一份模型定义。

### 3.2 Worker 路由与 API 端点

| 路由 | 方法 | 用途 | 请求体 | 响应 |
|------|------|------|--------|------|
| `/` 或 `/index.html` | GET | 返回前端 SPA | - | HTML |
| `/api/hf/call` | POST | 发起 Gradio API 调用 | `{api_url, api_name, data, token}` | `{event_id}` |
| `/api/hf/poll` | POST | 轮询 Gradio 结果 | `{api_url, api_name, event_id, token}` | SSE stream |
| `/api/hf/upload` | POST | 上传音频到 Gradio Space | FormData: `files`, `api_url`, `token` | `[filepath]` |
| `/api/proxy/openai` | POST | 代理 OpenAI TTS | `{key, voice, model, speed, input}` | audio blob |
| `/api/proxy/elevenlabs` | POST | 代理 ElevenLabs | `{key, voiceId, modelId, text, stability, similarity_boost, style}` | audio blob |
| `/api/proxy/minimax` | POST | 代理 MiniMax | `{key, voiceId, model, text, speed, vol, pitch}` | `{data:{audio}}` 或 `{audio_file}` |

所有端点均返回 CORS 头 `Access-Control-Allow-Origin: *`，OPTIONS 请求返回 204。

### 3.3 Gradio Queue API 调用流程

开源模型统一使用 Gradio Queue API 模式，前端通过 Worker 代理分两步调用:

**步骤 1: 发起调用 (POST /api/hf/call)**

```javascript
// 前端代码
const res = await fetch('/api/hf/call', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    api_url: 'https://xxx.hf.space/gradio_api',
    api_name: 'tts_interface',
    data: [text, voice, rate, pitch],  // 各模型参数不同
    token: 'hf_xxx'
  })
});
const j = await res.json();
// 返回: {event_id: "abc123"}
```

Worker 代理将请求转发到 `{api_url}/call/{api_name}`，附带 Authorization Bearer token。

**步骤 2: 轮询结果 (POST /api/hf/poll)**

```javascript
// 前端每秒轮询，最多 120 次 (2 分钟超时)
const res = await fetch('/api/hf/poll', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    api_url: 'https://xxx.hf.space/gradio_api',
    api_name: 'tts_interface',
    event_id: 'abc123',
    token: 'hf_xxx'
  })
});
// Worker 代理 GET {api_url}/call/{api_name}/{event_id}
// 返回 SSE stream:
//   event: complete
//   data: [{"path": "tmpxxx.wav", ...}]
```

**结果解析 (extractAudioUrl):**

Gradio API 返回的音频数据有多种格式，`extractAudioUrl` 函数统一处理:

```javascript
// 格式1: 直接 URL 字符串
data[0] === "https://..." → 直接使用

// 格式2: base64 DataURL
data[0] === "data:audio/..." → 直接使用

// 格式3: 相对路径 (需拼接 Gradio file 端点)
data[0] === "tmpxxx.wav"
→ 拼接为: {space_origin}/gradio_api/file=tmpxxx.wav

// 格式4: 对象含 url 字段
data[0].url → 使用 url

// 格式5: 对象含 path 字段
data[0].path → 同格式3的逻辑处理
```

**音频上传流程 (clone 模型):**

```
用户选择本地文件
  → FileReader.readAsDataURL() 转为 base64 DataURL
    → 存入 state.refAudio.base64
      → 生成时: fetch(dataUrl) → Blob
        → FormData {files: blob, api_url, token}
          → POST /api/hf/upload
            → Worker 转发到 {api_url}/upload
              → 返回 [filepath]
                → 用 {path: filepath, meta: {_type: 'gradio.FileData'}} 构造调用参数
```

### 3.4 各模型 API 调用详解

#### Edge TTS

```javascript
gradioCall(apiUrl, 'tts_interface', [text, voice, rate, pitch], token)
```
- `text`: 要合成的文本 (支持 SSML)
- `voice`: 声线 ID，格式 `"语音名 - 语言 (性别)"`，如 `"zh-CN-XiaoxiaoNeural - zh-CN (Female)"`
- `rate`: 语速调整百分比，范围 -100~200，默认 0
- `pitch`: 音调调整 Hz，范围 -50~50，默认 0

**注意:** 声线 ID 格式不同于微软官方的短格式 (如 `zh-CN-XiaoxiaoNeural`)，这是 HF Space 封装后的格式，包含语言和性别信息后缀。

#### F5-TTS

```javascript
// 先上传参考音频
const uploaded = await uploadAudioToGradio(apiUrl, refAudioBase64, token, fileName);
// 然后调用
gradioCall(apiUrl, 'predict', [
  {path: uploadedPath, meta: {_type: 'gradio.FileData'}},
  refText,   // 参考文本 (参考音频的转录)
  text,      // 要合成的新文本
  removeSilence  // boolean, 默认 true
], token)
```

**关键点:** 必须先通过 `/api/hf/upload` 上传音频文件获取服务端路径，然后将路径包装为 `gradio.FileData` 对象传入。`refText` 为空字符串时克隆质量会明显下降。

#### IndexTTS-2

```javascript
gradioCall(apiUrl, 'gen_single', [
  emoControlMethod,  // 'reference'|'slider'|'text'
  {path: refPath, meta: {_type: 'gradio.FileData'}},  // 参考音频
  text,              // 要合成的文本
  null,              // emo_ref_path (情感参考音频，当前未使用)
  1.0,               // emo_weight
  vec1_happy,        // 开心 0-1
  vec2_angry,        // 愤怒 0-1
  vec3_sad,          // 悲伤 0-1
  vec4_afraid,       // 恐惧 0-1
  vec5_disgusted,    // 厌恶 0-1
  vec6_melancholic,  // 忧郁 0-1
  vec7_surprised,    // 惊讶 0-1
  vec8_calm,         // 平静 0-1, 默认 0.5
  '',                // emo_text (情感描述文本)
  false,             // emo_random
  800,               // max_text_tokens_per_segment
  true,              // do_sample
  0.9,               // top_p
  50,                // top_k
  1.0,               // temperature
  1.0,               // length_penalty
  1,                 // num_beams
  1.0,               // repetition_penalty
  1500               // max_mel_tokens
], token)
```

**关键点:** 这是参数最多的模型（22 个参数）。8 个情感向量的默认值中只有 `vec8_calm` 是 0.5，其余均为 0。采样参数 (do_sample/top_p/top_k/temperature 等) 当前使用硬编码默认值，前端未暴露控制。如果未来要增加采样参数的 UI 控制，需要修改 `callIndexTTS` 函数。

#### Kokoro-82M

```javascript
gradioCall(apiUrl, 'generate', [text, voice, speed], token)
```
- `voice`: 声线 ID 如 `"af_bella"` (前缀: `af_`=美式女, `am_`=美式男, `bf_`=英式女, `bm_`=英式男)
- `speed`: 语速 0.5-2.0，默认 1.0

**注意:** 此模型仅支持英文。apiName 为 `'generate'` 而非模型定义中的默认 apiName。

#### Orpheus TTS

```javascript
gradioCall(apiUrl, 'generate_speech', [text, voice, temperature, topP, repPenalty, 2048], token)
```
- `voice`: 声线 ID 如 `"tara"`
- `temperature`: 0.1-2.0，默认 0.6
- `topP`: 0.1-1.0，默认 0.9
- `repetition_penalty`: 1.0-2.0，默认 1.2
- 最后一个参数 `2048` 是 max_new_tokens，硬编码

**注意:** 文本中可嵌入情感标记如 `<laugh>...</laugh>`。temperature 越高情感表现越强，但也越不稳定。

#### SparkTTS

```javascript
// 克隆模式
gradioCall(apiUrl, 'voice_clone', [
  text,
  {path: refPath, meta: {_type: 'gradio.FileData'}},
  gender,   // 'female'|'male'
  speed     // 1-5, 默认 3
], token)

// 属性控制模式
gradioCall(apiUrl, 'voice_creation', [
  text,
  5,        // gender token (硬编码 5=female)
  pitch,    // 1-5
  speed     // 1-5
], token)
```

**关键点:** 这是唯一使用 `voiceMode: 'multi'` 的模型，有两种模式切换。克隆模式调用 `'voice_clone'` 端点，属性控制模式调用 `'voice_creation'` 端点。属性控制模式的 gender 参数被硬编码为 5（前端 config 中的 gender select 未被使用），这是一个 bug 或未完成的功能。

### 3.5 闭源模型代理调用

闭源模型的调用链:

```
前端 → POST /api/proxy/{provider} → Worker 代理 → 原厂 API → 音频数据
```

**OpenAI TTS:**
```javascript
// Worker 代理转发到 https://api.openai.com/v1/audio/speech
POST body: {key, voice, model, speed, input}
// 返回: audio blob (MP3)
```

**ElevenLabs:**
```javascript
// Worker 代理转发到 https://api.elevenlabs.io/v1/text-to-speech/{voiceId}
POST body: {key, voiceId, modelId, text, stability, similarity_boost, style}
// 返回: audio blob (MP3)
```

**MiniMax:**
```javascript
// Worker 代理转发到 MiniMax API
POST body: {key, voiceId, model, text, speed, vol, pitch}
// 返回: JSON {data: {audio: base64_string}} 或 {audio_file: url}
// 前端额外处理: base64 → atob → Uint8Array → Blob
```

**MiniMax 的特殊处理:** MiniMax 返回的是 JSON 中的 base64 编码音频，而非直接的音频流。前端需要手动解码:

```javascript
const binary = atob(data.data.audio);
const bytes = new Uint8Array(binary.length);
for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
return new Blob([bytes], {type: 'audio/mp3'});
```

### 3.6 前端状态管理

前端使用单一 `state` 对象管理所有状态，通过 localStorage 持久化:

```javascript
state = {
  selectedModel: null,    // 当前选中的模型 ID
  selectedVoice: null,    // 当前选中的声线 ID
  voiceMode: null,        // 'preset'|'clone'|'design'|'attribute'|'multi'
  refAudio: null,         // {base64: dataUrl, name: fileName}
  refText: '',            // 参考文本
  config: {},             // 模型参数 {paramId: value}
  text: '',               // 要合成的文本
  generating: false,      // 是否正在生成
  results: [],            // 当前会话的生成结果
  currentAudio: null,     // 当前播放的 audio 元素 (互斥播放)
  voiceDesign: ''         // 声音描述文本
}
```

**localStorage 键:**

| 键 | 内容 | 大小注意 |
|----|------|----------|
| `tts_memory` | state 持久化 (含 base64 音频) | 可能很大 |
| `tts_history` | 历史记录 (最多 100 条) | 中等 |
| `tts_key_{modelId}` | 各闭源模型 API Key | 小 |
| `tts_hf_token` | 用户自定义 HF Token | 小 |
| `tts_hf_tokens_backup` | 备用 HF Token 列表 (逗号分隔) | 小 |

**保存时机:** 几乎所有用户操作（选择模型、选择声线、修改参数、输入文本、上传音频）都会立即调用 `saveMemory()` 写入 localStorage。

**恢复时机:** 页面加载时 `DOMContentLoaded` 事件中调用 `loadMemory()`，恢复上次的状态。如果检测到 `state.selectedModel`，会自动选中该模型并渲染面板。

### 3.7 数据流全链路

以 F5-TTS 语音克隆为例的完整数据流:

```
1. 用户上传参考音频
   → FileReader.readAsDataURL(file)
   → state.refAudio = {base64: "data:audio/wav;base64,UklGRi...", name: "ref.wav"}
   → saveMemory() → localStorage.tts_memory

2. 用户点击"生成语音"
   → generate()
   → state.generating = true, abortCtrl = new AbortController()
   → callHFModel(model)
     → getHfTokens() → [主Token, 备用Token1, ...]
     → callHFModelWithToken(model, token)
       → callF5TTS(model, token)
         → uploadAudioToGradio()
           → fetch(state.refAudio.base64) → Blob
           → FormData {files: blob, api_url, token}
           → POST /api/hf/upload (Worker 代理)
             → Worker: POST {api_url}/upload
             → 返回 ["/tmp/gradio/xxx/audio.wav"]
         → gradioCall(apiUrl, 'predict', [{path, meta}, refText, text, removeSilence], token)
           → POST /api/hf/call (Worker 代理)
             → Worker: POST {api_url}/call/predict + Authorization: Bearer {token}
             → 返回 {event_id: "abc123"}
           → gradioPoll(apiUrl, 'predict', event_id, token)
             → 循环 120 次 (每秒一次):
               → POST /api/hf/poll (Worker 代理)
                 → Worker: GET {api_url}/call/predict/abc123
                 → 解析 SSE stream
                 → 检测 "event: complete" 行
                 → 解析后续 "data: " 行的 JSON
         → extractAudioUrl(data, apiUrl)
           → 返回音频 URL

3. 结果处理
   → result = {id, modelId, modelName, voice, text, config, audioUrl, time, date, isBlob: false}
   → state.results.unshift(result)
   → addHistory(result) → localStorage.tts_history
   → renderResults() → 渲染 <audio> 元素
```

---

## 4. Debug 方向与排障指南

### 4.1 按症状索引

| 症状 | 可能原因 | 排查方向 |
|------|----------|----------|
| 点击生成后无反应 | 前端 JS 报错 | 打开浏览器 DevTools Console 查看错误 |
| "请先选择模型" | state.selectedModel 为 null | 检查 localStorage.tts_memory 是否被清除 |
| "请输入文本" | 文本为空或仅空白 | 正常校验提示 |
| "API调用失败: 4xx" | Token 无效/过期 | 检查 HF Token 是否有效，尝试在设置中更新 |
| "API调用失败: 5xx" | HF Space 服务端错误 | Space 可能正在启动/维护，等待后重试 |
| "API未返回event_id" | Gradio API 端点变更 | 检查 Space 的 api_name 是否与代码一致 |
| "生成超时(120s)" | 模型推理慢或 Space 休眠 | 重试；如持续超时，Space 可能过载 |
| "所有Token均失败" | 所有 HF Token 都无效 | 更新 Token 配置 |
| "无音频数据返回" | Gradio 返回格式变更 | 检查 extractAudioUrl 是否覆盖了新格式 |
| "无法解析音频" | 未知的数据结构 | 查看 console 中的 JSON.stringify(audioData) |
| 音频 URL 404 | HF Space 重启，临时文件已清除 | 正常现象，需重新生成 |
| Blob URL 失效 | 页面刷新导致 Blob URL 释放 | 正常现象，闭源模型结果无法跨刷新保留 |
| MiniMax 返回错误 | API Key 无效或额度用尽 | 检查 Key 和余额 |
| 参考音频上传失败 | 文件过大/格式不支持/网络超时 | 尝试更小的文件，检查网络 |
| 设置保存后 Key 丢失 | localStorage 满或被浏览器清除 | 检查 localStorage 容量 |

### 4.2 HF Spaces 相关问题

**Space 休眠唤醒:**
HuggingFace 免费 Space 在无请求 48 小时后会自动休眠。首次请求需要等待 Space 启动（通常 30 秒到 3 分钟），期间 API 可能返回 503 或超时。这不是代码 Bug。

**Space API 变更:**
HF Space 的维护者可能随时更新 `api_name`、参数顺序或返回格式。如果某个模型突然无法使用，需要:
1. 访问 Space 页面，点击 "API" 查看最新 API 文档
2. 对比代码中的 `apiName` 和参数顺序
3. 更新 `MODELS` 数组中的 `apiName` 和对应 `callXxx` 函数

**Space 下线:**
如果 Space 被删除或设为私有，对应的模型将完全不可用。需要寻找替代 Space 或移除该模型。

**Gradio 版本差异:**
不同 Gradio 版本的 API 响应格式可能不同。代码中同时处理了 SSE stream 和直接 JSON 两种响应格式，但未来版本可能需要适配。

### 4.3 闭源模型常见错误

**OpenAI:**
- `401 Unauthorized`: API Key 无效
- `429 Too Many Requests`: 速率限制，需等待
- `400 Bad Request`: 文本超长 (上限 4096 字符) 或参数错误

**ElevenLabs:**
- `401 Unauthorized`: API Key 无效
- `429 Too Many Requests`: 免费额度用尽 (10K 字符/月)
- `422 Unprocessable Entity`: voiceId 无效

**MiniMax:**
- 返回 JSON 中无 `data.audio` 也无 `audio_file`: 请求参数错误或额度不足
- base64 解码失败: 返回格式变更

### 4.4 前端渲染问题

**模型列表为空:**
- 检查 `MODELS` 是否正确注入（前端 `const MODELS = ${JSON.stringify(MODELS)};`）
- 搜索过滤条件是否过于严格

**声音面板不更新:**
- `renderVoicePanel()` 依赖 `state.selectedModel` 查找模型对象
- 如果模型 ID 在 MODELS 中不存在，面板会显示空状态

**config 值不生效:**
- `updateConfig()` 仅更新 `state.config`，不会自动更新 UI 显示
- Range 类型的 config 有独立的 `oninput` 处理器更新显示值

---

## 5. 踩坑预警与注意事项

### 5.1 安全相关

**硬编码 HF Token (高危):**
源码第 5 行硬编码了一个 HuggingFace Token:
```javascript
const HF_TOKEN =
```
这个 Token 会被包含在前端 HTML 中（通过 `const DEFAULT_HF_TOKEN='${HF_TOKEN}'`），意味着所有用户都能看到它。这是一个安全风险:
- 任何人都可以滥用此 Token 调用 HF API
- Token 一旦泄露无法撤回（除非重新生成）
- 如果此 Token 有写权限，可能导致 Space 数据被篡改

**修复建议:** 将 HF Token 存储在 Cloudflare Workers 的环境变量 (secrets) 中，仅在后端 Worker 路由中使用，不注入前端。

**API Key 传输 (中危):**
闭源模型的 API Key 通过前端 → Worker 代理 → 原厂 API 的链路传输。Key 存储在 localStorage 中，通过 HTTPS 传输到 Worker，Worker 不持久化 Key。风险点:
- 如果用户在公共电脑上使用，localStorage 中的 Key 可能被后续用户看到
- 浏览器扩展可能读取 localStorage
- XSS 攻击可以窃取 localStorage 中的所有 Key

### 5.2 代码缺陷与已知 Bug

**1. select onchange 多余属性 (低危):**
```javascript
onchange="updateConfig(\'...\',this.value)=\""
```
渲染 select config 时，`onchange` 属性末尾多了一个 `=""`，虽然不影响功能（浏览器会忽略多余属性），但是不规范的 HTML。

**2. SparkTTS 属性控制模式 gender 硬编码 (中危):**
```javascript
// voice_creation 模式
gradioCall(apiUrl, 'voice_creation', [text, 5, pitch, speed], token)
```
gender 参数硬编码为 `5`，前端 config 中的 `gender` select (female/male) 未被传递。用户在 UI 上选择性别不会影响实际生成结果。

**3. 历史记录中 Blob URL 丢失:**
```javascript
addHistory({...result, audioUrl: audioBlob ? null : audioUrl});
```
闭源模型生成的 Blob URL 在 `addHistory` 时被设为 null（因为 Blob URL 跨页面不可用），但开源模型的 HF URL 可能过期。历史记录中的下载功能可能随时失效。

**4. 情感向量默认值不一致:**
IndexTTS-2 的 `vec8_calm` 默认值为 0.5，而其他 7 个情感向量默认值为 0。当用户切换到 IndexTTS-2 时，`calm` 值被初始化为 0.5，但如果用户之前没有手动修改，`state.config.vec8_calm` 可能为 undefined（因为初始化逻辑依赖 config 定义中的 default 值）。在 `callIndexTTS` 中使用 `state.config.vec8_calm || 0.5` 作为 fallback，但 `|| 0.5` 在值为 0 时也会触发 fallback（虽然 0 不是有效默认值），这不是 Bug 但容易造成混淆。

**5. 停止生成不取消 Worker 端请求:**
`stopGeneration()` 仅在前端调用 `abortCtrl.abort()` 终止 fetch 请求，但 Worker 端已经发出的 Gradio API 请求不会被取消，浪费了服务端资源。

**6. localStorage 容量风险:**
参考音频以 base64 DataURL 存储在 localStorage 中。一个 15 秒的 WAV 文件 base64 编码后约 2-4MB，接近 localStorage 5MB 限制。如果同时存储多条历史记录，很容易触发 `QuotaExceededError`。代码中的 `saveMemory()` 使用 try-catch 静默吞掉错误，不会提示用户。

### 5.3 架构限制

**单文件架构:**
所有代码（948 行）在一个文件中，前端 HTML/CSS/JS 通过模板字符串嵌入。优点是部署简单，缺点是:
- 无法使用代码压缩/Tree-shaking
- IDE 无法对模板字符串内的 HTML/CSS 提供语法高亮和检查
- 修改前端需要同时修改 JS 文件，容易引入转义错误

**Gradio 轮询效率:**
每秒轮询一次 Gradio API，最多 120 次。对于快速模型（如 Kokoro，推理通常 2-5 秒），多数轮询是无效的。对于慢速模型（如 IndexTTS-2，推理可能 30-60 秒），可能接近超时上限。更优方案是使用 WebSocket 或 SSE 直接接收结果，但需要 Worker 支持流式转发。

**无重试逻辑:**
HF Token 轮换仅在 Token 级别失败时切换，对于单个 Token 的瞬时网络错误没有重试机制。如果第一次请求因网络抖动失败，不会自动重试同一 Token。

### 5.4 运维与部署注意

**Cloudflare Workers 限制:**
- 单次请求 CPU 时间限制: 免费 10ms，付费 50ms (但 fetch 到外部 API 的等待时间不计入 CPU 时间)
- 请求体大小限制: 免费 100MB
- 子请求数限制: 每次 fetch 最多 50 个子请求
- Worker 脚本大小限制: 免费 1MB (当前 948 行 JS 远小于限制)

**部署步骤:**
1. 安装 Wrangler CLI: `npm install -g wrangler`
2. 登录: `wrangler login`
3. 部署: `wrangler deploy tts-voice-lab-1.3.js`
4. (可选) 配置自定义域名

**环境变量配置 (推荐但当前未使用):**
```toml
# wrangler.toml
[vars]
# 不要在这里放 secrets
# 使用 wrangler secret put HF_TOKEN 设置敏感信息
```

### 5.5 兼容性与边界情况

**浏览器兼容性:**
- 使用了 `AbortController` (IE 不支持)
- 使用了 `fetch` API (IE 不支持)
- 使用了 `FileReader.readAsDataURL` (IE10+ 支持)
- 使用了 CSS `backdrop-filter` (Firefox 默认禁用)
- 使用了 CSS 变量 (IE 不支持)
- 使用了模板字符串 (IE 不支持)
- 实质上仅支持现代浏览器 (Chrome/Firefox/Safari/Edge 最新版)

**Edge TTS 声线 ID 特殊性:**
Edge TTS 的 presetVoices ID 格式为 `"zh-CN-XiaoxiaoNeural - zh-CN (Female)"`，包含空格和特殊字符。如果后续要做声线搜索/过滤，需要注意 ID 与显示名的区别。

**移动端体验:**
- 900px 以下切换为竖向布局
- 音频播放器使用原生 `<audio controls>`，移动端体验因浏览器而异
- 拖拽上传在移动端不支持（移动端自动降级为点击上传）

**并发限制:**
前端没有限制同时生成的数量，但 `abortCtrl` 是全局单例，意味着点击"生成"时如果上一次生成仍在进行，`abortCtrl` 会被覆盖，上一次的请求无法正确取消。实际上 `generate()` 在 `state.generating === true` 时按钮是 disabled 的，所以正常 UI 流程不会出现并发。但如果用户通过 DevTools 强制调用 `generate()`，可能导致状态混乱。

---

## 6. 自包含 README 与 CHANGELOG 原文

### 6.1 代码内嵌 README

代码在 `README_HTML` 常量中包含了一份自包含的使用说明，通过设置面板中的"使用说明"区域渲染。原文如下:

> **概述**
> TTS Voice Lab 是一个集成多种开源和闭源文本转语音模型的在线试用平台。支持语音克隆、情感控制、多语言合成等高级功能。
>
> **三步使用**
> - **步骤1 - 选择模型**: 左侧面板浏览并选择TTS模型。绿色标签=免费模型，红色标签=需要API Key的闭源模型。
> - **步骤2 - 声音设置**: 中间面板配置声线选择或上传参考音频进行语音克隆，调整模型参数。
> - **步骤3 - 合成语音**: 右侧面板输入文本，点击生成，试听并下载结果。
>
> **语音克隆**
> 支持语音克隆的模型（F5-TTS、IndexTTS-2、SparkTTS）需要上传5-15秒的清晰参考音频。建议同时提供参考文本以提高克隆质量。参考音频保存在浏览器本地存储中。
>
> **闭源模型**
> OpenAI TTS、ElevenLabs、MiniMax需要在设置中配置API Key。Key仅存储在浏览器本地，不会上传到服务器。
>
> **多Token轮换**
> 在设置中可配置多个HuggingFace Token（逗号分隔），当一个Token额度用尽时自动切换到下一个。
>
> **历史记录**
> 每次生成都会记录。可下载音频（云端仍保存时）、复制提示词和配置、或复用之前的设置。
>
> **音频播放互斥**
> 播放一个语音时，其他正在播放的语音会自动暂停。
>
> **记忆功能**
> 平台会记住您上次选择的模型、声线、参数配置和参考音频，下次打开自动恢复。
>
> **AI Debug参考**
> 本平台部署于Cloudflare Workers。前端为单页SPA，通过Worker代理API请求。开源模型使用Gradio Queue API: POST `/gradio_api/call/{api_name}` 获取event_id，然后GET `/gradio_api/call/{api_name}/{event_id}` 轮询结果。音频上传使用`/gradio_api/upload`。闭源模型通过`/api/proxy/*`端点代理。HF Token支持多Token轮换。

### 6.2 代码内嵌 CHANGELOG

代码在 `renderChangelog()` 函数中包含了版本更新日志。原文如下:

> **v1.3** (2026-05-19)
> - 三面板布局: 模型选择/声音设置/文本合成，宽屏并排/窄屏上下
> - 6个开源模型: Edge-TTS(323语音)、F5-TTS(克隆)、IndexTTS-2(8维情感)、Kokoro-82M、Orpheus(情感标记)、SparkTTS(克隆+属性控制)
> - 3个闭源模型: OpenAI TTS、ElevenLabs、MiniMax，带API Key配置和用量说明
> - 语音克隆参考音频上传，本地存储
> - 多HF Token轮换
> - 音频播放互斥
> - 历史记录: 下载/复制提示词/复用配置
> - 记忆功能: 记住首选模型/声线
> - 设置页自包含README和Changelog
> - 模型专属参数配置

---

## 7. Changelog

### v1.3 (2026-05-19)

- 三面板布局: 模型选择/声音设置/文本合成，宽屏并排/窄屏上下
- 6个开源模型: Edge-TTS(323语音)、F5-TTS(克隆)、IndexTTS-2(8维情感)、Kokoro-82M、Orpheus(情感标记)、SparkTTS(克隆+属性控制)
- 3个闭源模型: OpenAI TTS、ElevenLabs、MiniMax，带API Key配置和用量说明
- 语音克隆参考音频上传，本地存储
- 多HF Token轮换
- 音频播放互斥
- 历史记录: 下载/复制提示词/复用配置
- 记忆功能: 记住首选模型/声线
- 设置页自包含README和Changelog
- 模型专属参数配置

---
*AI生成*
