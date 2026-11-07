# RESUME.md · 崩溃恢复协议（新会话 3 分钟接续）

> 上一会话若崩溃，按本文件顺序恢复，**不要重新调研**（前期调研已完成并固化在 01-findings/）。

## 1. 身份与环境（0.5 分钟）

- 任务：`1105-canvas-test-videos`（本文件夹 README.md 为项目章程）
- 凭证：百度网盘 token 与 GitHub token 由**用户在 prompt 中提供**，只 `export` 进环境变量使用，**绝不写入文件**：
  - `export BAIDU_NETDISK_ACCESS_TOKEN=<用户提供>`（获取链接见 skills/remotion-video-studio/SKILL.md §4.1）
  - `export GH_TOKEN=<用户提供>`（repo: `lishuhang/clock`，token 名 261023-glm）
- 沙盒 `~/.venv` 可能丢包：`yt-dlp` 缺则重装（版本 ≥2026.09）

## 2. 拉取最新工作区（1 分钟）

```bash
# 大仓库只许浅克隆+稀疏检出（6.8GB，禁止全量 clone）
git clone --filter=blob:none --depth 1 --no-checkout "https://x-access-token:${GH_TOKEN}@github.com/lishuhang/clock.git" github-work
cd github-work && git remote set-url origin https://github.com/lishuhang/clock.git
git sparse-checkout init --cone && git sparse-checkout set 1105-canvas-test-videos && git checkout main
```

## 3. 恢复上下文（1.5 分钟，按序读）

1. `1105-canvas-test-videos/README.md` —— 章程与进度勾选
2. `1105-canvas-test-videos/PIPELINE-DECOUPLE.md` —— 管线解耦架构（职责分层/最小重跑路径/换模型指南）
3. `1105-canvas-test-videos/01-findings/timeline.md` —— 项目来龙去脉
4. `1105-canvas-test-videos/02-storyboards/` —— 三集分镜表（若已批准则直接按表投产）
5. 根目录 `worklog.md` 尾部 —— 最近一次 Task 的 Work Log / Stage Summary

## 3.5 废墟重启标准动作（v2.3 解耦架构后，替代手工逐段恢复）

**工程仓=唯一事实源**（分镜/字幕卡/切片/canvas 页/脚本/字体/配音全部在库）；
frames 帧库与 build 中间件是派生物，崩溃即弃、脚本重生成：

```bash
cd /home/z/my-project/work-clock/1105-canvas-test-videos   # clone 出的工程目录
python3 scripts/pipeline.py --list            # 一屏看三集 check/render/assemble/deliver 实际状态
python3 scripts/pipeline.py --ep all          # 全量续跑（幂等=自动接续，零素材重下零动效重做）
# 或按需停留/跳步：
#   --ep 1 --from render          # ep1 从截帧开始
#   --ep 2 --skip render          # 帧已在只重组装
#   --ep 3 --segments subs,qc     # 只重跑字幕烧录+质检
#   --ep 1 --only-shots S08 --steps render   # 换某镜 H5 后单镜重截
```

注意事项：
- **长任务前台 timeout 分段跑**（沙盒后台进程必被会话回收，实测 nohup/setsid 均不可幸免）；
- 非幂等段（speed/speed_h/subs/subs_h）单独跑：`--segments speed` 一次一段，勿与长段混跑；
- 段级跳过判据=帧数 ffprobe 断言（v8b 轮已给 final/final_h 补上，防 >1MB 残骸骗过 getsize）；
- H5 页面替换（外部模型交付）：按 `H5-SPEC.md` 契约验收 → `--only-shots` 重截 → assemble，
  时间轴/字幕/切片一律不碰，G11/G13 锚点门禁自动把关防回归。

## 3.6 v6 防回归要点（历史存档，G8-G10 断言仍内建于 assemble setup/qc）

- **字幕唯一事实源**：`04-ep1-production/ep1_subtitles_whisper.json`（365 卡，带 _provenance；显示用卡=ep1_subtitles_v7.json 341 卡）
- **bg 视频一律原生比例**：fit=展示主体 / cover=氛围底，禁非等比拉伸（G9 断言）
- 三处历史回归的完整归因见 `05-retro/RETRO.md`；防回归机制通用版见 skill `references/anti-regression.md`

## 4. 接续规矩

- 每完成一个可交付小步立即 `git add 1105-canvas-test-videos/ && git commit && git push`（防回收）
- worklog.md 追加 verbatim 条目（Task ID / Agent / Task / Work Log / Stage Summary 格式，见既有条目）
- 报错**逐字**摘录进 worklog，禁止概括失真；原始输出进 logs/
- 失败先 `tail -30` 原始日志对照踩坑表，再决定换法；换法重试最多 1 次
