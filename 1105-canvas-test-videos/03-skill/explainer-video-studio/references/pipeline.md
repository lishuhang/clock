# 管线详解与踩坑总表（references/pipeline.md）

> 来源：Gemini《1104-1800 防踩坑指南》血泪复盘 + Remotion 调研实测 + 1105 横评实操。原则：**只有必须用 token 的才交给 AI，可复用的一切脚本化。**

## 一、四大 Token 黑洞（架构级根因，本项目已全部规避）

| 黑洞 | 原现场 | 架构解 |
|---|---|---|
| 反爬死磕 | YouTube→yt-dlp→B站412→云电脑→Homebrew→访客cookie→WBI→…几十轮 | 素材通路提前固化为静态 skill（video-downloader）；运行期只走已验证通路，失败预算 1 次 |
| 环境/CLI 探针试错 | drawtext 缺滤镜、转写 5min 超时→30s→2min、ffmpeg 无 -nostdin 挂起 | `env_check.py` 一次性能力清单；ffmpeg 强制 `-nostdin -y`；文字一律 HTML/CSS 渲染 |
| 人肉 For 循环 | 52 段视频手写 6 批 Tool Call，断连补跑 | 批量调度收进单脚本；幂等标记（`.done`）断点续跑 |
| 风格研究 Context 爆炸 | 每次重看 10 期原片 | 风格资产静态化（style-guide.md），一次提炼永久复用 |

## 二、管线十步详解（对应 SKILL.md §2）

**Step 3 配音对齐**（`tts_align.py`）
- 新配音：逐句调用 tts.lishuhang.com（Playwright 拦截 audio 响应）；`silenceremove` 裁首尾静音（-40dB/0.05s，尾留 0.12s 呼吸）；句内字幕按"汉字 1.0+句末标点 1.2"权重线性映射实测时长，**抛弃外部 SRT**（跨句漂移 1.5~3s 不可救）
- 既有整条配音：`silencedetect`（-38dB/0.28s）切出说话区间 → 全片字数权重在区间流内推进 → 每镜 start/dur（1105 横评 V1 用此法对齐 740.36s 实测配音）
- 验收：对齐后各镜 dur 与字数比值的标准差 ≤15%（防某镜对歪）

**Step 5 canvas 动效**：复制 `vertical_master.html` 只改 YZ_EDIT 区；元素 `data-anim/data-t/data-d`；禁止自写整页 CSS（排版崩坏+文字溢出是弱模型最大翻车点）；`yzCheck()` 必须 compliant
**Step 6 受控截帧**（`h5_render.py`）：动效窗口 1.5s 按 30fps，静态区单帧复用；10 分钟全片实截帧数从 14400 降到数百，渲染分钟级
**Step 7 总装**（`ffmpeg_master.py`）：帧轨 concat → 人声轨（逐镜 mp3 adelay 叠加或整条）→ BGM `sidechaincompress` 闪避 -13.5dB → `loudnorm` 两遍（I=-15）→ faststart
**Step 8 质检门禁**：G1 零坏帧 / G2 时长±2s / G3 1080×1920 / G4 -15±2 LUFS / G5 无>3s 黑屏 / G6 无 Remotion 元数据；全 PASS 才 `BUILD_SUCCESS`

## 三、素材通路速查（详见 video-downloader-skill.md）

| 来源 | 通路 | 坑 |
|---|---|---|
| 百度网盘 | `netdisk.py`/`batch_download.py`（xpan 三步，UA 必须 pan.baidu.com） | 只读不上传；dlink 8h 有效；QPS≈10/s |
| B站 | 免登录 `playurl?platform=html5&high_quality=1` 720p | 412 风控时走 agent-browser 真实上下文；1080p 需 SESSDATA |
| 微博 | yt-dlp 单视频游客 4K | "列时间线"已上访客墙，用搜索引擎转引拿具体 URL |
| 小红书 | 必须带 xsec_token 的 App 分享链 | 地址栏 URL 必死；游客搜索死路 |
| YouTube | 数据中心 IP = bot-check | 对症解是 PO token/cookies，别换 client 空试 |
| 抖音 | 免登录通路 2026-11 已全部收壳 | 需 ttwid 注入或用户给 cookie |
| 官网/页面 | agent-browser 直接截屏 | 比"找视频"稳，截图+Ken Burns 常常够用 |
| 娱资历史文章 | 网盘 娱乐资本论历史文章备份/ + 微信检索 | 引自家报道先查网盘备份 |

## 四、Remotion 合规（若用其渲染片段）

- 画面无水印、无像素隐写；但 MP4/MOV 容器写死 `comment="Made with Remotion x.y.z"`，**无任何开关可关**
- 清除（无损）：`ffmpeg -y -i in.mp4 -c copy -map 0 -metadata comment=" " out.mp4`（视频流哈希不变，本 skill 的 ffmpeg_master 已内置）
- 许可：≥4 人盈利组织需 Company License（$25/月）；生成媒体版权归用户
- 渲染入口必须指向调用 `registerRoot()` 的 Root 文件（不是组件文件）

## 五、Git 协作规矩（用户给了工作仓时）

- 大仓（GB 级）只许 `clone --filter=blob:none --depth 1 --no-checkout` + `sparse-checkout set <目录>` + `read-tree` 思路提交（见 RESUME 范本）
- 每完成一步 commit+push；worklog.md 追加 verbatim 条目（Task ID/Agent/Task/Work Log/Stage Summary）
- 网盘源文件不入库；切片/半成品/canvas HTML 可入库；单文件 ≤99MB（GitHub 硬限）
- token/cookie 永不入库，push 用 `https://x-access-token:${GH_TOKEN}@...` 内联，不写进 remote

## 六、失败处置协议

报错先 `tail -30` 原始日志对照本表 → 换法重试 ≤1 次 → 仍失败记入 production-report.md「未探索/待用户」节并继续其余镜头（禁死磕）。沙盒重置后：`.venv` 重装 yt-dlp（≥2026.09）、按 RESUME.md 三分钟接续。
