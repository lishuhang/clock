# RESUME — 新会话恢复协议

> 你是接手 1103-agent-downloader 任务的新 agent 会话。**先完整读完本文件，再动手。** 目标：用最少的 token 恢复全部上下文，绝不重蹈覆辙。

## 恢复步骤（按序执行，约 3 分钟）

1. **读本目录 `state.json`** —— 单一事实来源：当前 phase、next_task、blocked_on、平台状态。不读全史。
2. **读 `worklog.md` 的最后 5 条**（`tail -60 worklog.md`）—— 只看最近的实验结果，不从头读。
3. **读 `findings/01-feasibility-matrix.md`** —— 各平台主通路/回退通路速查。
4. 遇到报错或疑问时，**才**去查 `findings/02-platform-notes.md`（分平台细节）和 `findings/03-pitfalls.md`（已知坑清单——**跳坑前必查**）。
5. 按 `todo.md` 对应 Phase 执行。

## 环境速查（沙盒若被回收重建，照此恢复）

- 沙盒：Debian 13 / 2C4G / Python 3.12.16（venv 在 `/home/z/.venv`，pip 直装）/ node v24 / **ffmpeg 7.1.5 与 playwright+chromium 预装**
- 出口 IP：香港阿里云（无 GFW，国内外平台均网络可达）
- GitHub token：`/home/z/my-project/.secrets/github_token`（**绝不入库**；仓库根 .gitignore 已含 `.secrets`）
- 仓库克隆（5.8GB 仓库，**禁止全量 clone**）：
  ```bash
  TOK=$(cat /home/z/my-project/.secrets/github_token)
  git clone --depth 1 --filter=blob:none --no-checkout \
    "https://x-access-token:${TOK}@github.com/lishuhang/clock.git" clock
  cd clock && git sparse-checkout init --cone && git checkout main
  git sparse-checkout set 1103-agent-downloader   # 之后工作只在此目录
  ```
- 工具安装：`/home/z/.venv/bin/pip install -U yt-dlp gallery-dl`（本轮已装 yt-dlp 2026.10.26 / gallery-dl 1.32.19）

## 硬性规则（违反任何一条 = 任务失败风险）

1. **每个任务完成立即 `git add -A && git commit -m "[Wxxx] 一句话结果" && git push`**。上一轮会话（1020-feng-video）的 geetest_beat2.py 等 8 个脚本因只存沙盒本地、未推 GitHub，**沙盒回收后已全部丢失**——这是本协议存在的第一原因。
2. worklog **只追加，永不改写历史**；纠错 = 新条目并注明 `corrects [Wxxx]`。
3. worklog 条目的 key_facts 必须**逐字摘录**原始输出行（数字、报错信息一字不改）。禁止"大概是/应该是"式概括。
4. 原始输出全文放 `logs/<id>.txt`，worklog 只放指针 + ≤5 行摘录。**禁止把长输出粘进 worklog 或对话**。
5. **能用脚本做的绝不用模型做**（探测/解析/批量/校验全部脚本化）；脚本输出压缩到 ≤20 行再给人看。
6. 失败处理：先 `tail -30 logs/<id>.txt` 看真实报错 → 对照 03-pitfalls.md → 换通路。**禁止连续盲试同一命令**（token 狂烧原地打转的根源）。
7. 任何 cookie/token/密钥只放 `/home/z/my-project/.secrets/`（不入库）。
8. 沙盒**后台进程会被杀**：长任务前台跑 + `timeout` 分段，跑完立刻查 log。
9. 上下文快满/即将崩溃时：把当前进度写进 state.json（哪怕半句话）→ commit+push → 再崩。恢复时从 state.json 续。
