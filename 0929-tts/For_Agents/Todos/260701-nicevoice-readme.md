# NiceVoice Multi-Channel TTS Worker

> 一个部署在 Cloudflare Workers 上的多通道语音克隆工具，支持 NiceVoice、KikiVoice 和本地 F5-TTS ONNX 推理三种通道，可生成长文本语音并自动拼合。

**在线地址**：<https://nicevoice.lishuhang.workers.dev/>
**当前版本**：v1.16.6（2026-07-01）
**代码仓库**：单文件 `worker.js`（含 HTML + JS 模板字面量），无构建步骤

---

## 目录

- [项目概述](#项目概述)
- [三大通道架构](#三大通道架构)
- [核心功能详解](#核心功能详解)
- [F5-TTS 浏览器推理 Debug 全过程](#f5-tts-浏览器推理-debug-全过程)
- [部署方法](#部署方法)
- [使用指南](#使用指南)
- [API 端点](#api-端点)
- [版本历史](#版本历史)
- [已知限制与后续规划](#已知限制与后续规划)

---

## 项目概述

NiceVoice Worker 是一个一站式语音克隆解决方案，单文件部署到 Cloudflare Workers 后即可在浏览器中使用。它解决了三个核心痛点：

1. **长文本生成**：NiceVoice 单次请求限 150 字，本工具自动按中文标点切句、贪心打包、串行生成、Web Audio API 拼接为单个 WAV
2. **多服务商聚合**：免费无限 NiceVoice、付费 KikiVoice、本地推理 F5-TTS 三通道并列，用户可按需切换
3. **本地推理实验**：把 633MB 的 F5-TTS ONNX 模型搬进浏览器跑，纯客户端推理无需服务器

项目自 2026-05-23 起迭代至今，从单一 NiceVoice 通道逐步扩展到三通道架构，并完成了 F5-TTS 浏览器推理的完整 Debug 闭环（目前 Preprocess 阶段仍有一处 tensor shape 问题待解，详见下文）。

---

## 三大通道架构

```
┌─────────────────────┐
│   浏览器 (单页应用)  │
│                     │
│  ┌────┐ ┌────┐ ┌──────────┐
│  │ NV │ │ KK │ │ LocalEng │
│  └─┬──┘ └─┬──┘ └────┬─────┘
│    │      │          │ F5-TTS ONNX
│    │      │          │ (浏览器内推理)
└────┼──────┼──────────┼──────────┐
     │      │          │
┌────▼──────▼──────────┴──────────┴─┐
│   Cloudflare Worker (worker.js)   │
│   - HMAC 签名代理                  │
│   - Geetest 验证代理               │
│   - 音频上传/下载代理               │
└────┬──────────────┬────────────────┘
     │              │
     ▼              ▼
api.turbovoice   kikivoice.ai
  .online         (Geetest v4)
```

### NiceVoice（免费 / 无限）

- 浏览器 → Worker 签名代理 → `api.turbovoice.online`
- 单次请求限 150 字，长文本自动分段串行生成
- 16 秒/段请求间隔（API 限流），失败自动重试 3 次
- 音频在浏览器端用 Web Audio API 拼接，段间插 50ms 静音

### KikiVoice（60k 积分 / 7 天）

- 浏览器 → Worker 代理 → `kikivoice.ai`
- 三种模型可选：Core（2x 积分）、Pro（3x 积分，含情感控制）、Multilingual（2x 积分）
- 实时积分监控、剩余天数显示
- 文本按模型限制自动分段（Core 1000 字 / Pro 500 字 / Multilingual 2000 字）
- 模型参数可调：语速、音量、情感、强度、性别、HQ

#### CF 验证传导机制（核心创新）

KikiVoice 使用极验 Geetest v4 人机验证，且验证是 IP 绑定的。Worker 的解决方案：

1. 首次调用 `create-clone-task` 返回 777 错误码，附 `validation_url_path`、`public_ip`、`auth_solution`
2. Worker 代理加载 Geetest 验证页面，重写其中的 `fetch('/jsapi/auth/geetest-validation')` 为 Worker 代理端点
3. 用户在 iframe 中完成滑块验证，提交请求经 Worker 转发，确保提交 IP 与 Worker IP 一致
4. 验证完成后 Worker IP 被标记为已验证，后续请求不再触发 777
5. Worker 自动重试原任务

这个方案把"人机验证"从浏览器 IP 转移到 Worker IP，是整个 KikiVoice 集成的关键。

### LocalEngine（F5-TTS 浏览器推理）

- 完全在浏览器内运行，无服务器参与
- 加载 F5-TTS ONNX 三件套：`F5_Preprocess.onnx`（16.2MB）+ `F5_Transformer.onnx`（633.6MB）+ `F5_Decode.onnx`（28.8MB）
- ONNX Runtime Web 1.25.1，WASM 后端（float16 原生支持）
- 三阶段推理：Preprocess → Transformer Euler ODE 循环 → Decode
- 内嵌 F5-TTS 词汇表（2544 条，含拼音 + 国际音标）
- 拼音转换：动态加载 pinyin-pro（esm.sh CDN）

---

## 核心功能详解

### 长文本智能分段

NiceVoice 通道的核心算法。策略：

1. 优先在 `。！？` 处切句
2. 超长句再用 `，、` 二次切分
3. 贪心打包：尽量把多句塞进 150 字上限内
4. 711 字测试文本可压缩到 5 段（朴素逐句切会得到 22 段）

### 设置持久化

- 所有配置（API key、模型选择、参数等）存 localStorage
- 支持导出/导入 JSON 配置
- LocalEngine 支持项目级导出（参考文本、生成文本、参数、文件名，不含 base64）

### 模型参数面板（KikiVoice）

| 参数 | 范围 | 默认 | 说明 |
|------|------|------|------|
| 语速 Speed | 0.5 ~ 2.0 | 1.0 | 0.5 慢 / 2.0 快 |
| 音量 Volume | 50 ~ 200 | 100 | 50 低 / 200 高 |
| 情感 Emotion | normal/happy/sad/angry/fearful | normal | 仅 Pro 模型 |
| 强度 Intensity | normal/strong/weak | normal | 仅 Pro 模型 |
| 性别 Gender | 0(女)/1(男) | 0 | 影响生成音色 |
| 高品质 HQ | 0/1 | 0 | 高品质模式 |

切换模型时 Pro 专属控件自动启用/禁用，选中模型高亮显示。

### 控制台日志

LocalEngine 通道内置控制台，实时显示：

- 模型加载进度、输入输出 tensor 元信息
- 拼音转换结果、token 化结果
- 每步 Transformer 迭代的 noise shape、time_step、dt
- 错误堆栈首行（便于定位）
- 支持一键复制全部日志到剪贴板（v1.16.4 新增）

---

## F5-TTS 浏览器推理 Debug 全过程

LocalEngine 通道的核心难点是把 F5-TTS 训练时的 PyTorch 推理流程完整搬到浏览器 ONNX Runtime Web 上。这个过程经历了 v1.11 到 v1.16.6 共 6 个大版本的反复 Debug，下面按时间顺序记录每次错误和修复，供后续维护参考。

### v1.11：初始实现

完成了基本的 3 阶段管线：

- 目录选择器（`webkitdirectory`）自动检测 F5 三件套 + vocab.txt
- 参考音频上传 → Int16 PCM → Float32 归一化
- 拼音转换（pinyin-pro CDN 动态加载）
- 内嵌 2544 条词汇表
- Euler ODE 求解器骨架

### v1.12 ~ v1.12.1：模板字面量转义陷阱

**问题**：v1.12 上线后 LocalEngine 标签页完全打不开，报 `SyntaxError: Unexpected string` 和 `pickCh is not defined`。

**根因**：整个 HTML + JS 是写在 Worker 的 JS 模板字面量（反引号字符串）里的。模板字面量会先解释 `\n`、`\s` 等转义序列，再生成最终 HTML。也就是说：

```javascript
// 源码里写
vocabText.split('\n')
// 模板字面量会先把 \n 变成真实换行符，生成的 HTML 里变成
vocabText.split('
')  // SyntaxError!
```

**修复**：所有 `\n`、`\s`、`\r`、`\-`、`\/` 都要写成 `\\n`、`\\s` 等双反斜杠，这样模板字面量输出 `'\n'` 才是正确的转义序列。base64 字符串也要用引号包起来：`atob("${B64}")` 而不是 `atob(${B64})`。

**教训**：在 JS 模板字面量里嵌套 JS 代码时，所有反斜杠转义都要双重化。这个坑在 v1.16.1 又踩了一次（`e.stack.split('\n')` 报错），改为 `split('\\n')` 后修复。

### v1.15：Transformer 推理修复

**问题**：Transformer 阶段 `OrtRun` 失败，错误指向 time_step tensor 类型不对。

**根因**：time_step 是离散的步索引（0, 1, ..., NFE-1），应该是 int32，但代码里直接把 Preprocess 输出的 float16 张量透传过去，导致类型不匹配。

**修复**：

1. time_step 改为 `new ort.Tensor('int32', new Int32Array([step]), [1])`
2. Euler ODE 求解器实现正确的 `noise = noise + dt * velocity` 步进，含 float16↔float32 批量转换（自定义 `halfToFloat32` / `float32ToHalf`）
3. 循环次数修正为 NFE 次（之前是 NFE-1）
4. time_step 每步递增 step index（之前是静态值）
5. Preprocess 输出到 Transformer 输入改用精确名称匹配，减少 substring 误匹配

### v1.16：Preprocess 输入类型连环 Debug

这是最曲折的一段，从 v1.16 到 v1.16.6 反复迭代。

#### v1.16.0：初始尝试

把 Preprocess 的 audio 输入从 int16 PCM 改成 float16（int16 → float32 归一化 → float16），time_step 改成 int32。结果 WebGPU 后端报错：

```
Actual: tensor(float), Expected: tensor(float16)
```

WebGPU 后端无法正确处理 JS 侧上传的 float16 输入张量。

#### v1.16.1：模板字面量 `\n` 又踩坑

Debug 时加的 `e.stack.split('\n')` 在模板字面量里又触发了 SyntaxError，改回 `split('\\n')`。

#### v1.16.2：Preprocess 改用 WASM 后端

把 Preprocess 单独用 WASM 后端跑（`executionProviders:['wasm']`），Transformer/Decode 仍用 WebGPU+WASM。float16 音频输入不再报错。

但 max_duration 又出问题：

- int32 → `Actual: tensor(int32), expected: tensor(int64)`（模型要 int64）
- int64 → 内部错误码 `31286248`（ORT Web 1.21.0 的 WASM 后端对 int64 BigInt64Array 支持有 bug）

#### v1.16.3：尝试 fp16→fp32 protobuf 补丁

写了一个 `patchOnnxFp16ToFp32` 函数，想法是直接在浏览器里把 ONNX protobuf 二进制中所有 FLOAT16 类型声明改成 FLOAT，这样 WebGPU 也能跑。

实现是粗暴的字节级替换：扫描 `0x08 0x0A`（field tag 1 + value 10）改成 `0x08 0x01`（value 1）。

**结果**：替换了 190 个位置，但绝大多数并不是 `elem_type` 字段，protobuf 结构被破坏，报：

```
Failed to load model because protobuf parsing failed.
```

#### v1.16.4：彻底换 WASM + 升级 ORT

**决策**：放弃 WebGPU 路线，三个模型全部用 WASM 后端（float16 在 WASM 上原生支持），不再做任何 protobuf 修改。

**配套改动**：

1. 移除 `patchOnnxFp16ToFp32` 函数
2. Preprocess 推理时发送 float16 音频（未修改的模型期望 float16）
3. `max_duration` 用 `BigInt64Array` 构造 int64 张量
4. Decode 输出增加 float16 → float32 → Int16 的 WAV 编码路径
5. 升级 onnxruntime-web 1.21.0 → 1.25.1（更好的 int64/float16 支持）
6. 顺手加了"复制"按钮（控制台日志区，清空按钮左边）

#### v1.16.5：audio tensor shape

**问题**：Preprocess 报：

```
expected rank: 1 got: 2. Ranks of input data are different, cannot concatenate them.
```

**误判**：以为是 audio shape `[1,1,N]`（3D）多了一维 channel，改成 `[1,N]`（2D）。

**结果**：新错误 `Got: 2 Expected: 3`——模型确实要 3D。Concat rank mismatch 不是 audio 的问题，是 max_duration shape `[1]`（1D）的问题。

#### v1.16.6：max_duration shape 自动探测

**决策**：audio 改回 `[1,1,N]`，max_duration 改成自动尝试多种 shape：

```javascript
const maxDurShapes=[
  {dims:[], label:'scalar []'},      // 0D
  {dims:[1,1], label:'[1,1] 2D'},    // 2D
  {dims:[1], label:'[1] 1D'},        // 1D (已知会触发 Concat 错误)
];
```

先用 int64 尝试三种 shape，全部失败再用 int32 尝试。同时加了 session metadata 诊断日志。

**当前状态**：v1.16.6 已部署，等待用户测试反馈。从错误信息推断，max_duration 可能需要是 scalar（0D）或 `[1,1]`（2D），如果都不行，可能需要检查模型导出时的 max_duration 节点定义。

### Debug 经验总结

1. **模板字面量转义**：在 JS 模板字面量里嵌 JS，所有 `\` 都要写成 `\\`。这是这个项目最高频的 bug 来源。
2. **ORT Web 后端选择**：WebGPU 无法上传 float16 输入张量（JS 没有 float16 类型），WASM 可以。如果模型输入是 float16，只能用 WASM。
3. **protobuf 二进制修改要谨慎**：粗暴的字节级替换会破坏结构，必须做完整的 protobuf 解析。
4. **tensor shape 要精确匹配**：ORT 对 shape 检查很严格，多一维少一维都会报错，错误信息里的 `Expected` 就是模型期望的 shape。
5. **错误信息要读全**：`Actual: tensor(float), Expected: tensor(float16)` 这种类型错误，和 `expected rank: 1 got: 2` 这种 shape 错误，根因完全不同，不能混为一谈。

---

## 部署方法

### 前置条件

- Cloudflare 账号
- Wrangler CLI（`npm install -g wrangler`）

### 配置文件

`wrangler.toml`：

```toml
name = "nicevoice"
main = "worker.js"
compatibility_date = "2024-12-01"
```

### 部署命令

```bash
cd /home/z/my-project/nicevoice-worker
CLOUDFLARE_API_TOKEN=<your_token> \
CLOUDFLARE_ACCOUNT_ID=<your_account_id> \
npx wrangler deploy --config wrangler.toml
```

部署后访问 `https://nicevoice.<your-subdomain>.workers.dev/`。

### 自定义域名

在 Cloudflare Dashboard 的 Workers 路由中添加自定义域名，或在 `wrangler.toml` 里配置 `routes`。

---

## 使用指南

### NiceVoice（推荐，免费无限）

1. 上传 5-30 秒参考音频
2. 输入参考文本（音频对应的文字）
3. 输入要生成的长文本（自动分段，每段最多 150 字）
4. 点击"开始生成"
5. 等待训练 + 串行生成完成
6. 下载单个 WAV 或单独 MP3 段

### KikiVoice（60k 积分 / 7 天）

1. 切换到 KikiVoice 标签页
2. 点击"检测连接"确认 API 可达
3. 选择模型（Core / Pro / Multilingual）
4. 调节模型参数（语速、音量、情感等，Pro 专属参数仅 Pro 模型激活）
5. 上传参考音频
6. 输入文本（按模型限制自动分段）
7. 点击"开始生成"
8. 如果出现 CF 验证面板：
   - 在嵌入的 iframe 中完成 Geetest 滑块验证
   - 或点击"在新标签页打开"完成验证
   - 验证成功后点击"验证完成，继续生成"
9. 等待生成完成，下载音频

### LocalEngine（F5-TTS 浏览器推理）

1. 切换到 LocalEngine 标签页
2. 准备 F5-TTS ONNX 三件套（`F5_Preprocess.onnx`、`F5_Transformer.onnx`、`F5_Decode.onnx`、可选 `vocab.txt`）
3. 点击"选择目录"选中包含模型文件的目录（自动检测同目录下的其他文件）
4. 点击"加载模型"（约 20-30 秒，633MB Transformer 加载较慢）
5. 上传参考音频（24kHz 采样率最佳）
6. 输入参考文本（中文，会自动转拼音）
7. 输入生成文本
8. 调节 speed / NFE / CFG 参数
9. 点击"开始生成"
10. 观察控制台日志，关注 Preprocess / Transformer / Decode 三阶段进度
11. 生成完成后自动播放，可下载 WAV

> 注意：LocalEngine 通道目前 Preprocess 阶段仍有 tensor shape 问题待修复，可能无法成功生成音频。其他两个通道可正常使用。

---

## API 端点

Worker 代理的所有端点：

### NiceVoice 代理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回单页 HTML 应用 |
| `/api/clone/getUploadUrl` | POST | 获取预签名上传 URL |
| `/api/clone/saveRefAudio2` | POST | 创建声音克隆 |
| `/api/clone/getSyncRefStatus` | POST | 轮询克隆训练状态 |
| `/api/clone/tts` | POST | 请求 TTS 生成 |
| `/api/clone/getItemByTaskSn` | POST | 轮询 TTS 任务状态 |
| `/api/clone/getAudioUrl` | POST | 获取音频下载 URL |
| `/api/upload` | POST | 代理音频文件上传 |
| `/api/audio` | GET | 代理音频文件下载 |

### KikiVoice 代理

| 端点 | 方法 | 说明 |
|------|------|------|
| GET `/jsapi/model-capabilities` | ✅ | 获取模型能力和积分费率 |
| GET `/jsapi/get-cloning-file-sig` | ✅ | 获取上传签名 |
| POST `/jsapi/detect-language` | ✅ | 语言检测 |
| POST `/jsapi/create-new-clone-task` | ✅ (需首次验证) | 需极验人机验证 |
| GET `/jsapi/get-job-task-status` | ✅ | 轮询任务状态 |
| POST `custom-voice-upload.kikivoice.ai/create-voice` | ✅ | 上传声音文件 |
| GET `/jsapi/auth/geetest-validation-page/<IP>` | ✅ | 极验验证页面（Worker 代理） |
| POST `/jsapi/auth/geetest-validation` | ✅ (Worker 代理) | 验证提交（确保 IP 一致） |

---

## 版本历史

### v1.16.6 (2026-07-01)

- **修复**：audio tensor shape 恢复为 `[1,1,N]`（3D，模型要求）
- **修复**：max_duration shape 自动探测，依次尝试 scalar `[]`、`[1,1]`、`[1]`，先用 int64 再用 int32
- **新增**：Session metadata 诊断日志

### v1.16.5 (2026-07-01)

- **误判修复**：尝试把 audio shape 从 `[1,1,N]` 改成 `[1,N]`，结果模型报 `Got: 2 Expected: 3`，下一版改回

### v1.16.4 (2026-07-01)

- **新增**：控制台日志区"复制"按钮（清空按钮左边）
- **修复**：移除破坏性的 `patchOnnxFp16ToFp32`（朴素字节替换导致 protobuf 损坏）
- **修复**：三个模型全部用 WASM 后端（float16 原生支持）
- **修复**：Preprocess 发送 float16 音频输入（未修改模型期望 float16）
- **修复**：max_duration 用 `BigInt64Array` 构造 int64 张量
- **修复**：Decode 输出 float16 → float32 → Int16 WAV 编码路径
- **升级**：onnxruntime-web 1.21.0 → 1.25.1

### v1.16.1 ~ v1.16.3 (2026-06-24)

- v1.16.1：修复模板字面量 `\n` 转义（`e.stack.split('\n')` → `split('\\n')`）
- v1.16.2：Preprocess 改用 WASM 后端，规避 WebGPU float16 输入 bug
- v1.16.3：尝试 fp16→fp32 protobuf 补丁（失败，protobuf 损坏）

### v1.16 (2026-06-24)

- Preprocess audio 输入改 float16（int16 PCM → float32 → float16）
- time_step tensor 改 int32
- Euler ODE 求解器：`noise = noise + dt * velocity`
- 修复循环 NFE 次迭代（之前是 NFE-1）
- pinyin-pro esm.sh 导入，自动检测导出形状
- 简化文件选择器：只保留目录选择器，精确文件名匹配
- 新增项目导入/导出（JSON，相对文件名，不含 base64）

### v1.15 (2026-06-22)

- 修复 time_step 类型错误（int32 而非 float16）
- 修复 Euler ODE 求解器实现
- 修复循环次数（NFE 次而非 NFE-1）
- 修复 time_step 步进（每步递增而非静态）
- 精确名称匹配 Preprocess 输出到 Transformer 输入
- 详细的 feed 类型/形状日志

### v1.12.1 (2026-06-02)

- 修复 v1.12 模板字面量转义 bug（`\n`、`\s`、`\r`、`\-`、`\/` 双反斜杠化）
- 修复 base64 字符串未加引号导致的 SyntaxError

### v1.12 (2026-06-02)

- 智能多文件选择器：选中任一 `F5_*.onnx` 自动检测同目录其余文件
- 文件筛选模式：指定文件名 / 指定后缀名 / 所有文件
- `F5_DeCode.onnx` 大小写兼容

### v1.11 (2026-05-30)

- **F5-TTS ONNX 浏览器推理**：LocalEngine 标签页完整 3 阶段管线
- 智能模型文件选择（目录选择器 + 独立文件选择器）
- 参考音频上传 + 参考文本输入
- 拼音转换：动态加载 pinyin-pro CDN
- 内嵌 F5-TTS 词汇表（2544 条目）
- ONNX Runtime Web 懒加载，WebGPU + WASM 后端自动回退
- 生成参数：speed / NFE / CFG 可调

### v1.10 (2026-05-29)

- **移除 Fish Audio 通道**：API key 余额问题频发（402 Insufficient Balance），免费额度仅 7 分钟/月
- 清理全部 Fish Audio 后端代理、前端代码
- 3-tab UI：NiceVoice + KikiVoice + LocalEngine

### v1.9 (2026-05-28)

- 修复 fishProxy body 双重消费导致 CF error 1101 崩溃
- 修复创建模型缺少 type/train_mode/voices/visibility 必填字段
- 修复 TTS 错误响应（如 402）未转发给用户
- 修复模型列表解析期望数组，API 返回 `{total, items}`

### v1.8 (2026-05-27)

- 新增 Fish Audio 通道（server-side API，用户 API key，zero-shot 克隆）— v1.10 已移除
- 新增 LocalEngine 通道（浏览器端模型管理、下载链接、文件配置）
- 设置系统：localStorage 持久化、JSON 导入/导出
- 4-tab UI（v1.10 后改 3-tab）
- Changelog 区块

### v1.7 (2026-05-26)

- 重命名 SoundTools 通道为独立 Fish Audio 入口
- 整理 KikiVoice 配置面板

### v1.6 (2026-05-26)

- 新增 SoundTools 通道（Fish Audio 集成）
- 3-tab UI：NiceVoice + KikiVoice + SoundTools

### v1.5 (2026-05-25)

- **修复模型选择 Bug**：`pickModel` 把 `kiki_core` 错转成 `mKikiCore`，实际 HTML ID 是 `mCore`，改用显式映射表 `MODEL_IDS = {'kiki_core':'mCore','kiki_pro':'mPro','kiki_multilingual':'mMulti'}`
- **新增模型参数面板**：语速、音量、情感、强度、性别、HQ 控件
- Pro 模型专属参数：emotion/intensity 仅 Pro 模型激活
- 模型切换视觉反馈：选中模型高亮，emotion/intensity 自动启用/禁用

### v1.4 (2026-05-25)

- **KikiVoice 通道集成**：模型选择（Core/Pro/Multilingual）、积分监控、语言检测
- **CF 验证传导机制**：Worker 代理 Geetest 验证页面和提交，确保 IP 一致
- 通道切换 UI：NiceVoice / KikiVoice 双通道 Tab
- KikiVoice API 集成：Worker 代理可达所有端点
- 100% 原始响应透明展示

### v1.1 (2026-05-24)

- 改进文本分段算法：贪心句子打包，711 字 → 5 段（原来 22 段）

### v1.0 (2026-05-23)

- 初始版本：NiceVoice 语音克隆、自动分段、音频拼合
- HMAC-SHA256 签名代理
- 16 秒/段请求间隔（API 限流）
- 重试逻辑（3 次指数退避）
- 实时进度条和段状态
- WAV 音频拼接（Web Audio API）
- ASR 验证确认文本转语音正确

---

## 已知限制与后续规划

### 当前限制

1. **LocalEngine Preprocess 仍未跑通**：v1.16.6 在尝试多种 max_duration shape，需要用户测试反馈确定正确组合
2. **拼音转换对数字/英文处理不佳**：如 "6月22日" 会被转成 "6 yue4 2 2 ri4"，"HappyHorse" 会被逐字母转成 "H a p p y H o r s e"。需要预处理把数字转中文、英文词整体保留或转音标
3. **NiceVoice 单次请求 150 字上限**：已通过自动分段解决，但段间 16 秒间隔导致长文本生成慢
4. **KikiVoice 积分有限**：60k/7 天，Pro 模型 3x 积分消耗较快
5. **WASM 后端性能**：633MB Transformer 在 WASM 上推理较慢，WebGPU 路线因 float16 输入问题暂搁置

### 后续规划

1. **修复 Preprocess max_duration shape**：根据 v1.16.6 测试日志确定正确 shape，或检查模型导出时的节点定义
2. **拼音预处理增强**：数字转中文、英文词整体处理、标点过滤
3. **WebGPU 路线重启**：实现正确的 protobuf fp16→fp32 转换（需要完整 protobuf 解析，不能字节级替换），让 Transformer/Decode 回到 WebGPU 加速
4. **LocalEngine 模型缓存**：用 IndexedDB 缓存已加载的模型，避免每次刷新重新加载 633MB
5. **批量生成队列**：LocalEngine 支持多文本排队生成

---

## 技术栈

- **运行时**：Cloudflare Workers（V8 isolate）
- **前端**：单文件 HTML + JS（模板字面量嵌入 Worker），无构建步骤
- **签名**：HMAC-SHA256（Web Crypto API）
- **音频处理**：Web Audio API（解码、拼接、WAV 编码）
- **ONNX 推理**：onnxruntime-web 1.25.1（WASM 后端）
- **拼音转换**：pinyin-pro（esm.sh CDN 动态加载）
- **部署**：Wrangler CLI

## 配置常量

`worker.js` 顶部的关键配置：

```javascript
const API_BASE = 'https://api.turbovoice.online';   // NiceVoice API
const HMAC_KEY_HEX = '';  // 签名密钥
const APP_ID = '10';
const APP_CODE = '110';
const KIKA = 'https://kikivoice.ai';                 // KikiVoice API
const KIKA_UP = 'https://custom-voice-upload.kikivoice.ai';
```

---

## 许可声明

本工具仅供个人学习使用。使用 NiceVoice、KikiVoice 服务时请遵守各自的服务条款。F5-TTS 模型遵循其原始许可证（CC-BY-NC-4.0）。

---
*AI生成*
