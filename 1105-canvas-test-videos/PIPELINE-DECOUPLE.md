# 1105 三部曲 · 制作过程复盘与管线解耦方案

> 2026-11-07 · 应用户指令复盘：截至目前的制作分哪几个部分、各用什么能力完成、如何解耦
> （一部分交脚本常态执行、一部分可换其他模型如 Kimi K3.1 优化 H5、任何步骤可指定停留、
> 任何时候可从 workspace 废墟重启回到原进度）。
> 本文档随工程交付，与 `H5-SPEC.md`（画面层接口契约）、`scripts/pipeline.py`（统一运行器）
> 配套使用。

---

## 一、制作过程复盘：分部 × 能力归属

三部曲成片：第一篇·价格篇 v8（740.36s 画布 → 1.1x = 673.2s，46 镜）｜
第二篇·功能篇 v1（566.99s，1.0x，39 镜）｜第三篇·实测篇 v1（689.53s，1.0x，51 镜）。
每集双版本（竖屏 1080×1920 + 横屏 1080×810），QC 门禁 G1-G14 全 PASS。

| # | 部分 | 具体工作 | 完成能力 | 产出物 | 解耦归属 |
|---|---|---|---|---|---|
| P0 | 调研盘点 | 网盘全量遍历（260 目录/3368 文件/7.3GB）、关键素材识别、项目时间线复原 | 脚本采集（traverse_netdisk/netdisk.py）+ AI 判断 | 01-findings/（素材地图/时间线） | 脚本为主，AI 只做一次 |
| P1 | 文案 | 三篇文章终稿（价格/功能/实测篇） | 用户提供（网盘成品稿件） | 口播稿 | 不在本管线 |
| P2 | 分镜表 | 46+39+51 镜切分、节奏三型编排（hook_punch/fast_list/deep_explain）、4:3 安全框布局、镜头边界语义归属 | **AI 创意**（分镜方法论已固化 skill） | storyboard.md + shots JSON | AI（换模型亦可） |
| P3 | 配音对齐 | whisper 词级实测对齐、句级全局单调对齐（二三篇）、jieba 分卡、退化卡合并、同句同档字号 | 脚本（align_final.py / resplit_subs.py / 分卡脚本） | sentences_real / subtitles JSON（341/317/400 卡） | 脚本（零 token） |
| P4 | 素材拉取与切片 | B 站原片/网盘大素材一次性下载 → 切片（单片 1.5~6MB<20MB）→ MANIFEST 标名用途 | 脚本（dl_bili_v2/slice_materials.py） | clips/ 16 切片 + MANIFEST.json | 脚本（崩溃后不再重下大件） |
| P5 | **H5 动效制作** | 136 镜 canvas 页面：推箱子、盖章、闸门、矩阵、图表、logo 墙、场景实拍叠层 | **AI 创意**（HTML/CSS/vanilla JS 逐镜手写 + 组件库） | canvas/ + canvas-ep2/ + canvas-ep3/ | **可换模型（Kimi K3.1 等）**，按 H5-SPEC.md 契约 |
| P6 | 受控截帧 | renderFrame 受控时钟驱动，动效窗 12-30fps、静态区 2fps 网格、帧复用 | 脚本（h5_render_v4.py） | frames/（ep1 6038→22211 帧序列） | 脚本（零 token） |
| P7 | 总装 | bg 视频叠底（fit/cover 原生比例）、逐镜编码、concat 帧数精确、等比水印、横屏裁切、BGM 闪避混音 loudnorm、变速 | 脚本（assemble_v8.py / assemble_ep.py） | 1x 母带 + 提速干净片 | 脚本（15 段可单独重跑） |
| P8 | 字幕烧录 | ASS 生成（tier 句内同档/÷speed 重定时）+ 最后一步烧录 | 脚本（assemble 的 subs/subs_h 段） | 成片 + srt | 脚本（改字幕只重跑此段） |
| P9 | 质检门禁 | G1 零坏帧 / G2 帧数 / G3 时长 / G4 分辨率 / G6 无黑屏 / G7 元数据 / G8 字幕对账 / G9 素材几何 / G10 无进度条 / G11 语义锚点 / G12 字幕质量 / G13 像素锚点 / G14 水印等比 | 脚本（qc 段） | qc_report_*.json + BUILD_SUCCESS | 脚本 |
| P10 | 交付归档 | 成片/srt/QC 报告入仓库 output/、push GitHub、download/ 交付 | 脚本（pipeline deliver 段）+ AI 汇报 | 交付物清单 | 脚本为主 |

**复盘结论**：全过程只有 P2（分镜）与 P5（H5 动效）是"必须用模型"的创意工作，
其余八个部分已全部脚本化。P5 是单镜独立、契约明确的 HTML 产物——正是最适合
外包给其他模型（H5 生成能力更强的 Kimi K3.1 等）逐镜优化替换的部分。

---

## 二、解耦架构（本次落地）

### 2.1 分层模型

```
┌─ 创意层（AI / 可换模型，烧 token）──────────────────────┐
│  P2 分镜 → shots JSON     P5 H5 页面 → canvas/S##.html  │
│  接口契约：H5-SPEC.md（画面）+ shots JSON（时间轴）       │
├─ 数据层（仓库即事实源，崩溃恢复的锚点）──────────────────┤
│  clips/ 切片+MANIFEST · 字幕 JSON · 配音/BGM · assets/    │
├─ 机械层（脚本，零 token，`scripts/pipeline.py` 统一编排）─┤
│  check 齐全性 → render 受控截帧 → assemble 总装15段       │
│  → deliver b命名归档（水印/裁切/变速/字幕全部在 assemble）│
└──────────────────────────────────────────────────────┘
```

### 2.2 统一运行器 `scripts/pipeline.py`

```bash
python3 scripts/pipeline.py --list                      # 三集步骤×状态总览（废墟重启先跑这个）
python3 scripts/pipeline.py --ep 1                      # 单集全流程 check→render→assemble→deliver
python3 scripts/pipeline.py --ep all                    # 三集全流程
python3 scripts/pipeline.py --ep 2 --from render        # 从某步开始
python3 scripts/pipeline.py --ep 3 --to assemble        # 跑到某步为止（指定停留）
python3 scripts/pipeline.py --ep all --steps check,render   # 只跑指定步
python3 scripts/pipeline.py --ep 1 --skip render        # 跳过截帧（帧已在）
python3 scripts/pipeline.py --ep 1 --segments subs,subs_h,qc  # 只重跑总装某几段
python3 scripts/pipeline.py --ep 2 --only-shots S07,S25 # 只重截指定镜（换 H5 后）
```

assemble 的 15 段（每段可独立重跑，均幂等）：
`setup → bg → seq → enc → cat → final → final_h → audio → mux → mux_h → speed → speed_h → subs → subs_h → qc`

### 2.3 常见迭代场景的最小重跑路径（省 token 的关键）

| 改了什么 | 只需重跑 |
|---|---|
| 字幕文本/字号/时间 | `--segments subs,subs_h,qc`（2 次单编码，不碰画面管线） |
| 某镜 H5 动效（换 Kimi 产出） | `--only-shots S08 --steps render` + `--steps assemble --segments seq,enc,cat,final,final_h,mux,mux_h,speed,speed_h,subs,subs_h,qc` |
| 水印/BGM/响度 | `--segments audio,mux,mux_h,speed,speed_h,subs,subs_h,qc` |
| 变速参数 | 改 SPEED 后 `--segments speed,speed_h,subs,subs_h,qc` |
| 时间轴/镜表 | 重走 P2-P3 后全量（发生频率最低，成本最高，符合直觉） |

### 2.4 幂等与续跑设计（废墟重启的技术基础）

- 截帧：每镜 `.done` 标记，重跑自动跳过已完成镜
- bg/enc/cat：产物存在 + `ffprobe` 帧数 == 镜表帧数才跳过（防残骸文件骗过 getsize）
- final/final_h/audio：产物存在性 + 大小阈值
- speed/subs：无条件重跑（覆盖式，QC 兜底）
- 状态日志：`.pipeline/state-ep{N}.json`（仅信息性；**真实状态=文件系统**，永不失真）
- 后台进程会被会话回收：长任务用「前台 timeout 分段跑」轮次推进，每轮结束状态落盘

---

## 三、H5 外包给其他模型的协作方式

1. **给对方**：`H5-SPEC.md`（本工程画面层契约）+ 一两个现有镜作参考（如 canvas/S08.html 推箱子）
   + 该镜要用到的素材相对路径（assets/logos/…）
2. **对方交付**：符合契约的单镜 HTML（yzCheck compliant + renderFrame 受控时钟）
3. **回接验收**：
   ```bash
   python3 -m http.server -d 1105-canvas-test-videos 8000   # 浏览器开 play.html 顺序预览
   python3 scripts/pipeline.py --ep 1 --only-shots S08 --steps render   # 单镜重截帧
   python3 scripts/pipeline.py --ep 1 --steps assemble --segments seq,enc,cat,final,final_h,mux,mux_h,speed,speed_h,subs,subs_h,qc
   ```
4. **红线**：H5 替换只动画面层，不碰 shots JSON（时间轴）/subs JSON（字幕）/clips（素材），
   音画同步由 G11 语义锚点 + G13 像素锚点自动把关，旧镜零回归。

---

## 四、废墟重启协议（任何时候回到原有进度）

1. 新会话读 `RESUME.md`（3 分钟接续）：clone 工作仓（浅克隆）→ 凭证走环境变量
2. `python3 scripts/pipeline.py --list` —— 一屏看清三集的 check/render/assemble/deliver 实际状态
3. 断点续跑：`--from <步骤>` 或全量重跑（幂等设计使"重跑"= 自动续跑）
4. 本次实测（2026-11-07）：沙盒崩溃全损后，clone → check 三集全 PASS（136 镜 canvas 页、
   16 路切片、配音/字幕/字体全在库，**零大文件重下**）→ render 136 镜重截帧（帧是唯一
   未入仓的派生物，~10 分钟）→ assemble 重组装——完整回到崩溃前进度。

---

## 五、b 版本：解耦有效性验证（本次交付）

- **目的**：验证"用解耦后的 pipeline.py 从废墟重组装"产出与原版一致，不重找素材、不重做动效
- **命名**：v8 → v8b（第一篇）、v1 → v1b（第二/三篇）——小版本加 b 后缀表示内容未变，
  仅流程解耦验证
- **路径**：check PASS → render（136 镜全部重截，H5 页面零改动）→ assemble 15 段全量 →
  deliver（b 命名归档 + QC 报告）
- **验收**：G1-G14 全 PASS + 帧数与原版一致（ep1 20192/20192、ep2 17010、ep3 20686）
  + 语义/像素锚点命中
