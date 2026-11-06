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
2. `1105-canvas-test-videos/01-findings/timeline.md` —— 项目来龙去脉
3. `1105-canvas-test-videos/01-findings/assets-map.md` —— 素材地图（哪些在网盘/哪些要做/哪些要外采）
4. `1105-canvas-test-videos/02-storyboards/` —— 三集分镜表（若已批准则直接按表投产）
5. 根目录 `worklog.md` 尾部 —— 最近一次 Task 的 Work Log / Stage Summary
6. 网盘文案原文在沙盒 `/home/z/my-project/netdisk_pull/key_files/`（若沙盒被回收，用 `scripts/batch_download.py` 重新拉）

## 3.5 v6 防回归要点（新会话必读）

- **字幕唯一事实源**：`04-ep1-production/ep1_subtitles_whisper.json`（365 卡，带 _provenance；旧的 ep1_subtitles.json 已作废仅存档）
- **开工先跑对账**：`python3 scripts/assemble_v6.py setup`（G8 前置：与 output/字幕v3.srt 逐卡对账，不过不开工）
- **bg 视频一律原生比例**：BG_V6 模式表（fit=展示主体/cover=氛围底），禁非等比拉伸；G9 几何断言把关
- **进度条分段必须带偏移**：gen_seg_cmds(total,t0,t1)；G10 连续性断言把关
- 三处回归的完整归因见 `05-retro/RETRO.md`；防回归机制通用版见 skill v2.0 `references/anti-regression.md`

## 4. 接续规矩

- 每完成一个可交付小步立即 `git add 1105-canvas-test-videos/ && git commit && git push`（防回收）
- worklog.md 追加 verbatim 条目（Task ID / Agent / Task / Work Log / Stage Summary 格式，见既有条目）
- 报错**逐字**摘录进 worklog，禁止概括失真；原始输出进 logs/
- 失败先 `tail -30` 原始日志对照踩坑表，再决定换法；换法重试最多 1 次
