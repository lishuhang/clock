# WorkBuddy 产出问题分析报告 &amp; v2.23 Skill 改进说明

## 一、问题清单

### P1: Logo 显示为文字「娱乐资本论」而非图形 Logo
**现象**: workbuddy 所有新建的 1:1 HTML 中，右上角 logo 区域显示的是纯文字 "娱乐资本论"。
**根因**: v2.22a skill 文件中内嵌了一个超过 15000 行的 SVG logo path（`#yz-logo-icon` sprite），总文件 527KB。workbuddy（hy3 模型）正确判断了内联该 SVG 不可行，选择用文字 wordmark 替代。但 skill 文档中写的是 "引用隐藏 sprite 中的 #yz-logo-horizontal"，并未告知 agent "如果 sprite 不可用则用文字替代" 的降级方案。
**v2.23 修正**: 在 skill 文档中明确写明两条路径：(a) 如果有 logo.svg 文件则用 `<img src>`；(b) 否则用文字 wordmark "娱乐资本论"。删除对不存在的 `#yz-logo-icon` sprite 的引用。

### P2: 大量图片显示空白
**现象**: workbuddy 渲染的 PNG 中，部分图片内容为空白。
**根因**: (1) workbuddy 的 render.js 中 require 路径写死为 `C:/Users/james/.workbuddy/binaries/...`，这是 Windows 本地绝对路径，在其他环境中完全不可用；(2) 字体 CDN (`@fontpkg/alibaba-puhuiti-3-0`) 在离线或网络受限环境下无法加载，导致文字渲染为系统默认字体，如果系统无中文字体则显示空白。这并非 skill 本身的问题，而是环境问题，但 skill 应提供离线字体降级说明。
**v2.23 修正**: skill 中增加 FONT FALLBACK 段落，说明如果 CDN 不可用，应在 CSS 末尾追加系统字体降级：`'PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif`。

### P3: MP4 未产出
**现象**: workbuddy 报告 20 个 MP4 "后台渲染中"但最终未交付。
**根因**: (1) render.js 在 Windows 环境下用 `require('C:/Users/...')` 硬编码路径，在其他环境失效；(2) Playwright chromium 安装可能不完整（workbuddy 日志提到 `dirlock cleanup failure`）；(3) ffmpeg-static 包提供的 ffmpeg 可能与系统不兼容。这些问题叠加导致 MP4 渲染全部失败。
**v2.23 修正**: v2.23c 的录屏脚本改用 Python + `playwright.async_api`（跨平台），ffmpeg 用系统 `ffmpeg` 命令（非 ffmpeg-static npm 包），并增加环境检查步骤。

### P4: a-step 大图过于简陋
**现象**: workbuddy 产出的 a-step 大图（如 shenteng-a-styled.html）仅用简单的文字卡片堆叠，没有利用 skill 中定义的 SHARED CSS 组件（如 .yz-bar-row, .hm-table 等），视觉效果与之前的 round1/round2 demo 差距巨大。
**根因**: v2.22a skill 文件高达 15411 行（其中 14000+ 行是 SVG logo path），agent 读取时注意力被大量 SVG 路径数据稀释，难以聚焦到真正重要的模板结构（在文件末尾 300 行）。workbuddy（hy3）选择了自建 CSS 而非从 skill 中提取 SHARED CSS 类，导致产出与 skill 规范不一致。
**v2.23 修正**: (1) v2.23a 删除内联 SVG logo，文件从 15K 行压缩到 ~400 行；(2) 使用 `<!-- BEGIN_TEMPLATE -->` / `<!-- END_TEMPLATE -->` 标记清晰界定可复制区域；(3) SHARED CSS 组件直接内联在模板中，agent 无需在 15000 行中搜索。

### P5: b-step 未复用 skill 的 SHARED CSS 类
**现象**: workbuddy 的 b-step 文件使用了自定义类名（.qc-meta, .qc-badge, .qc-film 等），而 v2.22b 中定义了标准类名（.phase-label, .phase-badge, .chart-legend 等）。
**根因**: v2.22b 文件高达 44017 行，同样因为文件过大导致 agent 无法有效提取和复用标准类名。agent 选择自建一套 CSS 更简单直接。
**v2.23 修正**: (1) v2.23b 压缩到 ~200 行核心模板，标准类名直接可见；(2) 在 QUICK START 中明确列出必须使用的类名；(3) 增加 yzCheck1x1() 自检函数验证关键类存在。

### P6: c-step 动画注入不完整
**现象**: workbuddy 的 c-step 动画仅用简单的 `fadeIn` 应用于整个 `.chart-body-1x1`，缺少针对不同图表类型的特定动画（饼图扫描、柱状生长、表格逐行 fade 等）。
**根因**: v2.22c 文件仅 153 行，内容精简但缺少具体的注入指导。agent 只实现了最简单的 fallback 动画。
**v2.23 修正**: v2.23c 提供完整的、可直接复制粘贴的 ANIMATION_CSS 块，包含表格逐行 stagger、文字卡 slideUp、SVG fadeIn 等多种图表类型的动画。agent 只需复制粘贴，无需理解 CSS 动画原理。

## 二、模型差异根因分析

### 2.1 文件大小问题（最关键）
| Skill | 行数 | 大小 | 核心问题 |
|-------|------|------|----------|
| v2.22a | 15411 | 527KB | 14000+ 行 SVG path 淹没模板 |
| v2.22b | 44017 | 1.4MB | 示例代码+CSS过多，agent迷失 |
| v2.22c | 153 | 7.5KB | 过于简略，缺少具体CSS |

**结论**: v2.22a/b 的核心问题是**信号噪声比极低**。有效指令被大量 SVG path 和重复的示例代码淹没。不同模型（GLM-5.2, Claude, GPT, DeepSeek, hy3）对长文件的注意力分配策略不同：
- GLM-5.2：能在 15K 行文件中定位到末尾的模板（因为训练时见过类似结构）
- hy3/workbuddy：倾向于自建方案而非在长文件中搜索模板
- Claude Code：可能因上下文窗口限制而截断文件
- Codex：对 HTML 模板类任务的指令遵从度较低

### 2.2 Logo 引用方式不兼容
v2.22a/b 使用 `<svg><use href="#yz-logo-icon"/></svg>` 引用一个在 HTML comment 中定义的 sprite。这个设计假设 agent 会在同一个文件中保留完整的 SVG 定义。但当 agent 从零开始写 HTML 时（不复制整个 skill 文件），sprite 引用必然断裂。

### 2.3 Skill 结构不适合跨 Agent 使用
v2.22 系列的 skill 文件混合了三种内容：(1) 人类阅读的文档注释，(2) 可复制的模板代码，(3) 大量示例代码。不同 agent 对这三种内容的处理方式不同，导致产出不一致。

## 三、v2.23 改进策略

### 3.1 极简文件 (核心改进)
- v2.23a: ~400 行（vs 15411 行）— 删除 SVG，保留模板
- v2.23b: ~200 行（vs 44017 行）— 纯模板+最小CSS
- v2.23c: ~150 行（不变）— 补充完整可用的动画CSS块

### 3.2 模板标记
使用 `<!-- BEGIN_TEMPLATE -->` / `<!-- END_TEMPLATE -->` 明确标记可复制区域。agent 只需复制这个区域。

### 3.3 Logo 降级文档
在文档中明确说明 logo 的两种实现方式，避免 agent 猜测。

### 3.4 自检函数
每个 skill 内置自检函数（yzCheck / yzCheck1x1），agent 运行即可验证产出质量。

### 3.5 语言与格式
- 所有文档注释使用英文（提高跨模型兼容性，避免中文分词差异）
- CSS 类名保持英文
- 占位符使用 【UPPER_CASE】 格式（中英文字符均能识别）

### 3.6 兼容性测试矩阵
| Agent | v2.22 预期问题 | v2.23 预期改善 |
|-------|---------------|---------------|
| GLM-5.2 | 能用但浪费 token | 文件小 10x，token 省 10x |
| hy3/WorkBuddy | logo 空白、自建 CSS | 有明确降级方案和模板 |
| Claude Code | 可能截断 44K 行文件 | 200 行无截断风险 |
| Codex | HTML 模板遵从度低 | 模板标记清晰，直接复制 |
| DeepSeek | 长文件注意力分散 | 核心指令集中在文件前 50 行 |
| Manus/Trae | 环境差异大 | Python 录屏脚本跨平台 |
| OpenClaw | 未知 | 模板结构通用 |

## 四、遗留风险
1. **字体 CDN 依赖**: AliPuHui 字体仍依赖 jsDelivr CDN，离线环境需预先下载
2. **MP4 渲染**: 依赖 Playwright + ffmpeg + Chromium，部分 agent 环境可能不具备
3. **数据准确性**: agent 可能编造数据而非从原文提取，需人工校验
4. **图片提取**: 微信公众号文章的图片有防盗链，直接下载可能失败
