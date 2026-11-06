---
name: explainer-video-studio
description: 解说视频一站式生产管线（B站知识区/竖屏9:16风格）。用户一句话给出风格、主题、时长、素材来源（可含百度网盘 token），即可走完 事实核查→分镜表→TTS配音对齐→HTML canvas动效→受控时钟截帧→ffmpeg混音组装→成片质检 全流程。当用户要求"做解说视频/知识区视频/把文章或报告改成视频/竖屏短视频/科普视频/横评视频"时使用。
---

# 解说视频工作室 · 一站式生产管线（v2.0，2026-11-06 实战固化）

> **v2.0 修订（价格篇 v3 修复轮实战）**：①配音实测对齐（whisper 词级时间戳，废弃字数权重估算投产）②帧数精确组装（修复 concat 图像时长量化漂移）③B站真实素材铁律（原片叠底+网页截图取证）④黑底暗色系规范（本类片专用）。修 bugs 详情见 `references/pipeline.md` §7。

本 skill 由四源整合：Remotion 渲染合规调研（水印/许可）、Gemini 视频任务防踩坑指南（Token 黑洞与 H5 受控截帧架构）、娱资信息图 skill v3.2（品牌视觉系统）、1105 画布横评三集视频实操（网盘素材管线 + 分镜表方法论 + timeline JSON）。

## §0 一句话用法（对用户的承诺）

用户只需提供：**风格 + 主题 + 时长 + 素材来源**（例："按小Lin说风格做一支10分钟竖屏解说视频，讲XX，文章和素材在我网盘，token是XXX"）。
本 skill 即输出：分镜表（求批准）→ 成片 mp4 + 字幕 srt + 分镜 timeline JSON + 全套中间件。

## §1 起点决策表（按用户给的东西定入口）

| 用户给了什么 | 从哪步开始 | 关键动作 |
|---|---|---|
| 只有主题（连文案都没有） | Step 0 选题+文案 | 按 `references/style-guide.md` 的改编 SOP/文风配方写口播稿（用户确认后才进分镜） |
| 有文章/报告（要改编） | Step 0.5 文案改编 | 同上，保骨肉去水分，口径以用户终稿为准 |
| 有口播终稿 | Step 1 事实核查 | `facts-gate.md` 门禁 |
| 有终稿+配音 | Step 3 对齐 | **whisper 实测对齐**：本地 faster-whisper（hf-mirror 拉模型）词级时间戳 + silencedetect 双校准（`scripts/align_final.py`），句首误差≤0.3s；字数权重只作兜底 |
| 什么都有只要成片 | Step 4 起投产 | 按 timeline JSON 逐镜生产 |

素材来源决策：百度网盘（token→`scripts/netdisk.py`/`batch_download.py`，只读不上传）｜本地文件｜外部平台（见 `references/video-downloader-skill.md`：B站免登录720p、微博游客、小红书需cookie、YouTube数据中心IP死路）｜自制 canvas 动效（本 skill 主力）。

## §2 十步状态机（每步完成即落盘 `.step_N_done` 标记，幂等可续跑）

```
Step 0  选题与文案（若需）      → script.md（口播终稿，须用户批准）
Step 1  事实核查门禁            → facts_ledger.json（校验不过禁止进 Step 2）
Step 2  分镜表                  → storyboard.md + timeline.json（须用户批准）
Step 3  配音与对齐              → audio/S##.mp3 + aligned-timeline.json（既有配音走 whisper 实测对齐，见铁律13）
Step 4  素材拉取                → assets/（网盘/外部/截图，含 meta 留痕）
Step 5  canvas 动效制作         → canvas/S##.html（受控时钟 renderFrame API）
Step 6  受控截帧                → frames/S##/ + render-manifest.json（v3：入场窗30fps∪2fps网格∪页面SHOOT_DENSE窗，见铁律15）
Step 7  组装混音                → build/（帧数精确架构：逐镜 n=round(dur×30) 段编码 + concat -c copy，见铁律14）
Step 8  质检门禁                → BUILD_SUCCESS 或打回（坏帧/黑屏/响度/水印/乱码）
Step 9  交付                    → output/ 成片+srt+timeline+报告
```

工作目录结构（固定，长任务防崩）：`project/{script.md, facts_ledger.json, storyboard.md, timeline.json, audio/, assets/, canvas/, frames/, build/, output/, worklog.md}`。**每完成一步 commit+push 到用户指定的 Git 工作仓（若有）**；网盘源文件永不入 Git，只入切片/半成品/canvas HTML。

## §3 硬性铁律（全部来自实测血泪，违反=返工）

1. **只有必须用 token 的才交给 AI**：可复用的一切（下载/截帧/对齐/组装/质检）必须脚本化；AI 只产出 JSON 配置与文案，不手写执行命令。
2. **禁实时录屏**：Playwright `record_video_dir` 在沙盒高负载下掉帧导致音画错位；一律走受控时钟 `renderFrame(payload)` 截帧，静态区间单帧复用（`-loop 1 -t` 延展），只有动效窗口按 fps 截。
3. **ffmpeg 永远 `-nostdin -y`**；文字渲染 100% 走 HTML/CSS（或 PIL 降级），禁用 `drawtext`（沙盒常缺 freetype/中文字体）。
4. **字体本地加载**：`assets/h5_templates` 与信息图包自带阿里普惠体/思源系，`@font-face` 用本地绝对路径，禁 Google Fonts/CDN；截帧前 `await document.fonts.ready`。
5. **外部素材失败预算**：每素材重试≤1 次、超时 5s 即回退 canvas 自制动效或网盘替代素材；静态图优先于视频（Ken Burns 补动效）。
6. **TTS 分句合成，严禁整篇**：跨句累积误差不可救；句内字幕按"汉字权重1.0+句末标点1.2"线性映射实测时长，误差<0.1s。既有一整条配音时用 `--existing` 静音切分重对齐。
7. **事实门禁前置**：`facts_ledger.json` 每条数字带 claim/raw_inputs/formula/source_url/is_estimated，`verify_facts.py` 重算不过 = 禁止开写分镜；推算值画面自动打"\*推算"角标。
8. **节奏方差**：hook_punch(2~4s 大字+boom) / fast_list(3~5s 卡片+pop) / deep_explain(8~15s 流程图) 三型交替，相邻两个 deep 之间必须插暴击或快闪（防匀速念经）。
9. **成片强制机器质检**：`ffmpeg -v error -f null` 零坏帧 + LUFS -14~-16 + 无黑屏段 + 抽帧 contact sheet 无乱码豆腐块 + 分辨率/时长复核；输出 `BUILD_SUCCESS` 才可交付。
10. **渲染水印合规**：若用 Remotion 渲染任何片段，交付前必须 `ffmpeg -c copy -metadata comment=" "` 清除 `Made with Remotion` 容器元数据（画面本身无水印，详见 `references/pipeline.md` §6）。
11. **token/cookie 永不落盘**：只走环境变量，不进任何产物/日志/Git。
12. **网盘只读**：素材只拉不上传；用户 GitHub 仓只放中间件与半成品（≤99MB/文件）。
13. **配音实测对齐，禁字数权重直接投产**：字数权重×平均语速的估算全片可漂移 ±27s（1105 实测，用户在 27s 处即感知音画不同步）。既有整条配音必须 whisper（本地 faster-whisper，HF 429 时走 hf-mirror.com 手动下 model.bin/config/tokenizer/vocabulary）+ silencedetect 静音区间双校准；字幕分卡时间用词锚定；估算值仅用于分镜表预览列。
14. **帧数精确组装，禁 concat demuxer 图像时长**：concat 清单里 PNG 的 `duration` 会被量化到 1/25s 网格（实测每镜 +0.01~0.02s，43 镜累积近 0.9s 漂移）。正确架构：每镜 `n_i = round(dur_i×30)`，序列物化（符号链接指向渲染帧，按"最大 t′≤k/30"映射）→ 逐镜 `-framerate 30 -i seq -frames:v n_i` 编码 → `concat -c copy -video_track_timescale 30000`；终渲 A/B 分段用 `-frames:v` 而非 `-t`（`-t` 会在段边界丢 2~3 帧）。全片帧数必须 == round(总长×30)。
15. **截帧必须覆盖全部动效时刻**：v1 渲染器只截前 1.5s 入场窗，data-t>1.5s 的元素全部丢失（42/43 页中招）。v3 时刻集 = 入场窗(1.5s@30fps) ∪ 基础网格(2fps 全程) ∪ 页面 `SHOOT_DENSE=[[t0,t1,fps],...]` 声明 ∪ 尾帧；页面动画超过 2fps 采样密度时必须声明 DENSE。
16. **B站真实素材铁律**：①作品/影片类素材找原片片段做背景叠底（压暗 82% scrim），不用 canvas 模拟；②播放量/点赞等外部数字证据一律网页截图+裁切（m.bilibili.com 移动页免验证码截播放量；player.bilibili.com 外链播放器 DOM 截点赞数——游客只见前 3 条热评，名人评价用新闻报道段落截图留证）；③下载通路：`pagelist` API 拿 cid → `playurl?platform=html5&high_quality=1` 游客 720p（view API/视频页有 412/验证码墙勿碰；CDN 掐长连接用 `curl -C -` 断点续传）；④ B31 试看钳制：durl 声称时长≠实际可解码时长，下载后必须 ffprobe 体检。
17. **黑底暗色系（本类解说片专用）**：小Lin说式黑底片一律暗色系——底 `#131110`/面板 `#1e1b19`/正文 `#f2efec`/次级 `#b5aea9`/线 `#3a3634`；**品牌橙 #fc8166/#e55b46 原样保留**（黑底白字、橙高亮不违反品牌规范，属本类片的合法换肤）；yz-infographic 白底信息图进入本类视频前必须按映射表换肤（见 layout-spec §2b）；白底网页截图用深色卡片承托；深色 logo 白底键出透明（距白 <8 → alpha 0），纯黑字形反转白色。

## §4 画面与动效规范

见 `references/layout-spec.md`（9:16/4:3 安全框/上下字幕带/品牌色字体/13 个 canvas 模板枚举/信息图 HTML 复用法）。若用户未指定品牌系，默认用该 spec 的中性科技配色；娱资项目强制品牌系（#fc8166/#e55b46 + 阿里普惠体 + 河豚 logo）。

## §5 管线脚本（`scripts/`，均可独立运行）

| 脚本 | 作用 | 关键参数 |
|---|---|---|
| `env_check.py` | 环境自检（node/playwright/ffmpeg/字体/网盘token）输出能力清单 | `--netdisk` 顺带验 token |
| `make_storyboard.py` | 口播稿→分镜表 md + timeline.json（段/句切片数据 + 字数权重时间码；有整条配音时按实测时长反推语速） | `--audio-sec 740.36` 校准 |
| `tts_align.py` | 逐句 TTS（tts.lishuhang.com，Playwright 自动化）+ 静音裁切 + 时间轴重算；`--existing` 模式对齐整条既有配音 | `--voice`（站点内音色） |
| `h5_render.py` | timeline + canvas HTML → 受控截帧（renderFrame 注入，动效窗口 30fps，静态复用）→ concat 清单 | `--fps 30` |
| `ffmpeg_master.py` | 总装混音（v1 基础版） | 视频轨+人声+BGM(ducking -13.5dB)+音效 → loudnorm → 质检 → BUILD_SUCCESS；含 Remotion 元数据清除 | `--bgm-loop` 无缝循环 |
| `ffmpeg_master_v2.py` / `ffmpeg_master_v2_seg.py` | 总装混音 v2（1105 价格篇实战版）：ASS白字黑边字幕烧录 + sendcmd/drawbox 动画进度条 + 全屏水印顶层叠加 + BGM闪避修正(sidechaincompress双输入+aformat统一采样率)；`_seg` 分段模式绕沙箱600s命令超时，段B字幕/cmds自动偏移，幂等续跑 | `--preview-ts 10,300,700` 出静帧目检 |
| `align_final.py` / `subs_real.py` | **v2 新增**：whisper 词级时间戳 + 脚本字符流模糊对齐 + 静音边界吸附 → 每句实测时间码 + jieba 词边界字幕分卡 | 先跑 faster-whisper 全片转写出 whisper_segs.json |
| `h5_render_v3.py` | **v2 新增**：受控截帧 v3（入场窗∪2fps网格∪DENSE 窗 + render-manifest + 透明叠层模式 `TRANSPARENT_SHOTS`） | `--only S01,S02` 幂等续跑 |
| `assemble_v3.py` | **v2 新增**：帧数精确总装（bg 视频段/seq 序列物化/逐镜 enc/concat/final A-B/audio/mux/qc 七段幂等） | `python3 assemble_v3.py bg\|seq\|enc\|cat\|final\|audio\|mux\|qc` |
| `netdisk.py` / `batch_download.py` | 网盘 quota/list/search/meta/download / 按正则批量（tree.json fs_id 直连） | token 走环境变量 |

## §6 与其他 skill 的协作

- 素材外部下载：`references/video-downloader-skill.md`（8 平台通路+16 条踩坑，2026-11 实测）
- 图表/信息图：`references/yz-infographic-skill.md`（娱资品牌图表规范与 11s 动效引擎；横评项目信息图 HTML 可直接改造为 canvas 动效底版）
- 图像生成/搜索：宿主 `image-generation`/`image-search` skill 可补外部静图（失败回退 canvas）

## §7 交付规范

`output/` 内：`成片.mp4`（1080×1920×30fps H.264）+ `字幕.srt`（Aegisub/B站投稿均兼容）+ `timeline.json`（复用改版）+ `production-report.md`（事实账本核对结果、素材来源清单、音画对齐误差、质检输出、已知妥协）。口径矛盾（不同来源数字打架）在报告中列明并说明采用理由，**不静默修改用户文案数字**。

## §8 实战样例

`examples/timeline-ep1.json`：1105 画布横评·价格篇（43 镜/12:20/真实配音校准）。完整工作现场：GitHub `lishuhang/clock` → `1105-canvas-test-videos/`（含三集分镜表、素材地图、时间线复原）。
