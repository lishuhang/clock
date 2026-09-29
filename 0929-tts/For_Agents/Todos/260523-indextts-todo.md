# IndexTTS-2 TTS Web Tool — 项目完整状态文档

> 最后更新: 2026-05-23 (UTC+8)
> 本文档供新 AI Agent 从零接手使用，由 v0.11 基准合并两版 README 生成
> 包含全部历史、技术细节、凭证、已知问题和下一步操作

---

## 一、项目概述

构建一个在线 TTS 语音合成工具，部署在 `https://indextts.lishuhang.workers.dev`，使用 IndexTTS-2 模型，支持双后端架构：

1. **Kaggle 后端**（优先）: FastAPI + IndexTTS-2 + cloudflared Quick Tunnel，运行在 Kaggle 免费 P100/T4 GPU 上
2. **HuggingFace 后端**（备用）: 客户端浏览器直接调用 HF ZeroGPU Space API

用户是非技术人员，要求完全无人值守操作。

---

## 二、架构图

```
浏览器 (Web UI)
    |
    +-- Kaggle 可用? --> Worker 代理 --> Kaggle FastAPI (/tts) --> IndexTTS-2 GPU 推理
    |                                     |
    |                    cloudflared tunnel (动态 URL)
    |                                     |
    |                    Workers KV 存储 tunnel URL
    |
    +-- Kaggle 不可用? --> 浏览器直接 --> HF Space API (gradio_api)
```

**关键流程:**
1. 用户访问 Worker --> 返回 HTML 页面
2. 页面检测后端状态 --> `/api/backend-status`
3. 如果 Kaggle 离线，显示"启动 Kaggle"按钮
4. 点击按钮 --> `/api/start-kaggle` --> 先尝试 Kaggle gRPC SaveKernel API 触发执行；若失败则 fallback 到 REST `kernels/push`（仅保存不执行）
5. Kaggle notebook 启动后: 安装依赖 --> 下载模型 --> 启动 FastAPI --> 启动 cloudflared tunnel --> 更新 KV
6. Worker 检测到 KV 中有 tunnel URL --> Kaggle 可用 --> 用户可以生成 TTS

---

## 三、当前部署状态

### Cloudflare Worker
- **域名**: `https://indextts.lishuhang.workers.dev`
- **版本**: v0.11
- **代码位置**: `/home/z/my-project/indextts-worker/src/index.ts` (~1960行)
- **KV 命名空间**: `indextts-kaggle` (=
- **KV 绑定名**: `KAGGLE_KV`
- **Wrangler 配置**: `/home/z/my-project/indextts-worker/wrangler.toml`

### Workers KV 键值
- `kaggle_tunnel_url` — Kaggle cloudflared tunnel 的当前 URL
- `kaggle_daily_usage` — JSON: `{"date":"YYYY-MM-DD","gpu_seconds":0,"requests":0}`
- 当前 KV 中 tunnel URL 可能仍为旧值或已清除

### Kaggle Notebook
- **Slug**: `lishuhang1/indextts2server`
- **Kernel ID**: `119905232`
- **最新推送版本**: ~v79 (历经大量依赖修复调试)
- **状态**: 未运行（Kaggle session 最长 12 小时，已超时）
- **代码**: 嵌入在 Worker 的 `KAGGLE_NOTEBOOK_SOURCE` 常量中（约 180 行 Python）
- **独立副本**: `/home/z/my-project/kaggle-notebook/server.py`
- **关键发现**: Kaggle 环境为 P100 GPU，预装 transformers > 4.52.1，降级会破坏 CUDA 兼容性
- **最新方案 (v79)**: 安装 transformers==4.52.1 --no-deps + 缓存类补丁 + .pyc 缓存清理

### HuggingFace 后端
- **Space API**: `https://indexteam-indextts-2-demo.hf.space/gradio_api`
- **问题**: CF Workers 共享 IP 被 HF ZeroGPU 标记为滥用 --> 返回 403/quota 错误
- **解决方案**: 客户端浏览器直接调用（不走 Worker 代理）
- **7 个 HF Token**: 全部之前测试时配额已用尽（可能已恢复，需要重新测试）

---

## 四、凭证清单

---

## 五、v0.11 已实现的功能清单

### Feature A: Kaggle/HF Token 导入导出 + 多实例轮询
- HF Token 管理：localStorage 存储，支持添加/删除/验证/配额查询
- Kaggle Token 管理：支持多个 Kaggle 实例（名称 + KGAT Token + notebook slug）
- Round-robin 轮询：按 lastUsed 排序选择最久未用的 token
- 导入/导出：JSON 格式，包含 HF tokens + Kaggle tokens + 音频源 + 配置
- 启动 Kaggle 时支持 `X-Kaggle-Token` 请求头和 `body.slug` / `body.kernelId` 参数

### Feature B: 高级设置折叠区
- TTS 参数放入可折叠 accordion（默认折叠）
- 包含：最大字数/段、最大生成 tokens、并发数、重试次数、do_sample、温度、Top-P、Top-K、情感权重、length_penalty、num_beams、repetition_penalty

### Feature C: 本地存储音源管理
- 保存当前上传音频为命名音源（localStorage，存为 DataURL）
- 下拉选择已保存音源，快速切换
- 支持删除音源、设置默认音源
- localStorage 键: `indextts_audio_sources`, `indextts_default_source`

### Feature D: README/Changelog 模态框
- 设置页底部"查看 README 与更新日志"按钮
- README 模态框包含：功能指南、Debug 指南（AI Agent 用）、API 路由、已知问题、localStorage 键
- 版本号显示在 header 和 README 按钮上
- 源码顶部 AI Agent 头部注释（提示 Agent 查看 showReadme() 函数）

### Feature E: 音频下载文件名格式
- 格式：`yyyymmdd-hhmmss-<首句前10字符去标点>.<ext>`
- 例：`20260523-143025-你以为万通筋骨贴.wav`

### Feature F: Word 文档上传 (v0.10)
- JSZip CDN 引入，DOCX 拖放和按钮上传
- 自动读取两列表格左列文本，右列忽略
- 若无表格，则提取全文段落文本
- 拖放时有视觉覆盖层提示

### Feature G: 启动 Kaggle 双 API 策略 (v0.11)
- 优先使用 gRPC SaveKernel API：`POST https://www.kaggle.com/api/v1/kernels.KernelsApiService/SaveKernel`，可真正触发执行
- 若 SaveKernel 失败（如 401），fallback 到 REST `kernels/push`（仅保存代码版本）
- 支持从请求体传入 `slug` 和 `kernelId` 参数
- 支持 `X-Kaggle-Token` 请求头覆盖默认 Token

---

## 六、Worker API 路由

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回 Web UI HTML 页面 |
| `/api/backend-status` | GET | 检查 Kaggle/HF 后端可用性 + 每日用量 |
| `/api/kaggle/tts` | POST | 代理 TTS 请求到 Kaggle (FormData: text, audio, max_tokens, do_sample 等) |
| `/api/start-kaggle` | POST | 触发 Kaggle notebook 启动，支持 X-Kaggle-Token + body.slug/kernelId |
| `/api/kaggle-status` | GET | 查询 Kaggle kernel 运行状态 |
| `/api/update-kaggle-url` | POST | 更新 KV 中的 tunnel URL (需 X-Update-Key) |
| `/api/verify-token` | GET | 验证 HF Token (需 X-HF-Token) |
| `/api/check-quota` | POST | 检查 HF Token 配额 (需 X-HF-Token) |
| `/api/usage` | GET | 获取每日用量统计 |

**请求头支持**:
- `Content-Type` — 标准请求
- `X-HF-Token` — HF Token 认证
- `X-API-Base` — 自定义 API 基地址
- `X-Update-Key` — 更新 KV 的密钥
- `X-Kaggle-Token` — Kaggle API Token 覆盖

---

## 七、已知 Bug 和问题

### Bug 1: Kaggle Notebook 依赖冲突（关键 - 未解决）
**现象**: Kaggle 预装 transformers > 4.52.1 + tokenizers==0.22.2，IndexTTS2 要求 transformers==4.52.1
**修复尝试**: v65-v79 多轮调试
- v77: glob.glob 覆盖 dependency_versions_check.py（部分成功）
- v78: dep_version_check no-op patch（.pyc 缓存干扰）
- v79: 添加 .pyc 缓存清理 + cache_utils 补丁
**状态**: v79 推送后未确认是否成功运行，需要继续调试

### Bug 2: HF ZeroGPU 配额耗尽
**现象**: 所有 7 个 HF Token 的 ZeroGPU 配额之前已耗尽
**状态**: 可能已恢复（按小时/日重置），需要重新测试

### Bug 3: Kaggle REST API Push 不触发执行
**现象**: `POST /api/v1/kernels/push` 只创建代码版本但不触发 notebook 执行
**解决方案**: v0.11 已改用 gRPC SaveKernel API 作为主要方式，push 作为 fallback
**已验证**: SaveKernel API (`kernels.KernelsApiService/SaveKernel`) 可用 KGAT Bearer token 触发执行

### Bug 4: `/api/start-kaggle` 无认证
**现象**: 任何人都可以调用 `POST /api/start-kaggle` 触发 GPU 运行
**风险**: 恶意用户可反复触发，烧光每日预算
**缓解**: v0.11 支持 X-Kaggle-Token 头，但未强制验证

### Bug 5: 双重用量计数（已修复 ✅）
**状态**: Worker 端已删除用量计数逻辑，只依赖 Kaggle server 自己跟踪

### Bug 6: m4a 音频格式（已修复 ✅）
**状态**: server.py 已添加 torchaudio 格式自动转换

### Bug 7: 时区不一致（已修复 ✅）
**状态**: getTodayDate() 已改为 UTC+8

---

## 八、Kaggle API 关键信息

### Kaggle REST API
- `POST /api/v1/kernels/push` — 推送代码，但只创建版本不触发执行
- `GET /api/v1/kernels/pull/{slug}` — 获取 notebook 元数据
- Bearer Token 认证: `Authorization: Bearer 
### Kaggle gRPC/SaveKernel API (真正触发执行)
- 端点: `https://www.kaggle.com/api/v1/kernels.KernelsApiService/SaveKernel`
- 请求体: `{ id, slug, text, language, kernel_type, is_private, enable_gpu, enable_internet, kernel_execution_type }`
- `kernel_execution_type: 1` 表示 "Save & Run All (Commit)"
- 需要: Bearer Token 认证
- 已验证可用

### Kaggle 限制
- 免费限制: 30小时 GPU/周，每次 session 最长 12 小时
- 每日预算: $3/day (约 3.3 小时 T4 GPU 时间)
- Session 过期后需要重新启动

### Kaggle Notebook 启动时间估算

| 步骤 | 预估时间 |
|------|----------|
| 安装 pip 依赖 | 2-3 分钟 |
| 下载 cloudflared | 10 秒 |
| git clone IndexTTS-2 | 30 秒 |
| 安装 IndexTTS 依赖 | 3-5 分钟 |
| 下载 IndexTTS-2 模型 | 3-5 分钟 |
| 下载附加模型 | 2-3 分钟 |
| 加载模型到 GPU | 1-2 分钟 |
| 启动 FastAPI + Tunnel | 10 秒 |
| **总计** | **约 10-18 分钟** |

---

## 九、技术细节

### cloudflared Quick Tunnel
- 命令: `cloudflared tunnel --url http://localhost:8000`
- 每次启动生成随机 URL: `https://xxx-xxx.trycloudflare.com`
- 免费，无需配置，但 URL 不固定
- Server 启动后自动将 URL 写入 Workers KV

### Workers KV 注意
- 最终一致性，写入后可能需要 60 秒才能全球读取
- 单次操作最大 25MB
- 免费版: 100K reads/day, 1K writes/day

### IndexTTS-2 模型
- HuggingFace: `IndexTeam/IndexTTS-2`
- 需要额外模型: `amphion/MaskGCT`, `facebook/w2v-bert-2.0`, `nvidia/bigvgan_v2_22khz_80band_256x`
- 输出: 24kHz WAV
- 单次推理约 5-10 秒 (T4 GPU)
- 支持长文本分段处理

### HF Space API (Gradio)
- 提交: `POST /gradio_api/call/gen_single` --> 返回 event_id
- 结果: `GET /gradio_api/call/gen_single/{event_id}` --> SSE 流
- 浏览器直接调用时需处理 CORS 和 SSE 解析
- ZeroGPU Space 有请求配额限制，共享 IP 容易被标记

### 前端 localStorage 键
| 键名 | 内容 |
|------|------|
| `indextts_config` | TTS 参数配置 (backend, maxChars, maxTokens 等) |
| `indextts_tokens` | HF Token 数组 (id, name, token, status 等) |
| `indextts_kaggle_tokens` | Kaggle Token 数组 (name, token, slug) |
| `indextts_audio_sources` | 保存的音源数组 (id, name, dataUrl, addedAt) |
| `indextts_default_source` | 默认音源 ID |

---

## 十、项目核心代码文件

| 文件路径 | 说明 |
|----------|------|
| `/home/z/my-project/indextts-worker/src/index.ts` | Worker 主源码（v0.11, ~1960行，含完整 Web UI + API） |
| `/home/z/my-project/indextts-worker/wrangler.toml` | Cloudflare Worker 部署配置 |
| `/home/z/my-project/kaggle-notebook/server.py` | Kaggle notebook 独立副本（FastAPI server + IndexTTS2 推理） |
| `/home/z/my-project/worklog.md` | 所有 Agent 的工作日志 |

---

## 十一、工作历史摘要

### 阶段 1: Bug 修复与首次部署 (v0.8)
- 修复 m4a 音频转换、双重用量计数、时区不一致
- 部署 Worker v0.8，启动 Kaggle（版本 19-21）
- HF 后端验证成功：5段合成、157秒输出、97% ASR 覆盖率

### 阶段 2: Word 文档功能 (v0.9-v0.10)
- 添加 JSZip CDN、DOCX 拖放上传、表格左列提取
- 修复 SSE 解析语法错误
- 部署 v0.10，世界杯 TTS 测试成功

### 阶段 3: v0.11 功能 + Kaggle 调试
- 完成全部 5 项 v0.11 功能开发（Token 多实例轮询、高级设置折叠、音源管理、README 模态框、下载文件名格式）
- 部署 v0.11 到 Cloudflare
- Kaggle 依赖调试（v65-v79）：transformers/protobuf/tokenizers/CUDA 兼容性
- 发现 Kaggle P100 环境，预装包与 IndexTTS2 要求冲突
- v79 方案：--no-deps 安装 + 缓存类补丁 + .pyc 清理
- 启动 Kaggle 改用 gRPC SaveKernel API（真正触发执行）

### 阶段 4: 待完成
- 确认 v79 Kaggle notebook 是否成功运行
- 如果失败，继续调试依赖问题
- 等待 HF 配额恢复，重新测试 HF 后端
- 测试泰国娱乐稿（用户要求的下一个测试）

---

## 十二、下载/上传文件夹文件说明

### 下载文件夹历史音频产出
| 文件名 | 大小 | 用途/来源 |
|--------|------|-----------|
| `tts_full_output.wav` | 6.9MB | HF 后端完整 TTS 输出（浪姐文本，5段拼接，2.6分钟） |
| `tts_output_hf.wav` | 181KB | HF 后端单段测试输出 |
| `世界杯_full.wav` | 6.0MB | HF 后端完整 TTS 输出（世界杯文本，5段拼接，2.3分钟） |
| `seg_1.wav` ~ `seg_5.wav` | 各约 1.4MB | 浪姐文本 5 个分段的独立 TTS 输出 |
| `swcup_seg_1.wav` ~ `swcup_seg_5.wav` | 各约 1.4MB | 世界杯文本 5 个分段的独立 TTS 输出 |

### 上传文件夹常用文件
| 文件名 | 用途 |
|--------|------|
| `测试音源.m4a` | 参考音频（中文播客/解说风格） |
| `test_ref.wav` | 测试参考音频（WAV 格式） |
| `0516 世界杯.docx` | 世界杯主题中文稿（979字，6行表格） |
| `0519 陪爬.docx` | 陪爬主题中文稿（1318字，8行表格） |
| `www.kaggle.com_cookies.txt` | Kaggle 浏览器 cookies（可能已过期） |

---

## 十三、下一步操作清单（按优先级排序）

1. **确认 Kaggle v79 状态**: 检查 notebook 是否成功启动
2. **继续调试 Kaggle 依赖**: 如果 v79 失败，分析错误日志并修复
3. **测试 HF 配额恢复**: 逐个验证 7 个 HF Token 是否恢复
4. **端到端测试**: 使用完整文本（浪姐/世界杯/泰国娱乐稿）测试 TTS 生成
5. **添加认证保护**: 给 `/api/start-kaggle` 添加密码或 rate limit
6. **测试 v0.11 新功能**: 音源管理、高级设置、导入导出、下载文件名格式、Kaggle 多实例轮询

---

## 十四、用户要求的工作方式

1. **无人值守**: 编写 --> 部署 --> 访问 --> 统计 bug --> 修复 --> 重复
2. **非技术人员**: 不能要求用户手动操作 Kaggle 界面
3. **一键启动**: 点击"启动 Kaggle"按钮后自动完成所有步骤
4. **自动化 debug**: 发现问题自行修复直到成功

---

## 十五、环境信息

- **开发环境**: AI Agent 环境（无持久化，会话结束后文件不保留）
- **项目目录**: `/home/z/my-project/`
- **下载目录**: `/home/z/my-project/download/`
- **上传目录**: `/home/z/my-project/upload/`
- **Worker 部署方式**: `cd /home/z/my-project/indextts-worker && npx wrangler deploy`
- **KV 操作**: 通过 Cloudflare API 或 Worker 代码
- **Kaggle 操作**: 通过 Kaggle REST/gRPC API
