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

## §7 v3 修复轮新坑（2026-11-06 价格篇重制实战，全部实测）

### 7.1 音画同步三连坑（用户 27s 处感知不同步的完整归因）
| # | 坑 | 真因 | 对策（已固化为铁律 13/14/15） |
|---|---|---|---|
| P1 | 字数权重估算漂移 ±27s | TTS 实际语速随数字/英文/停顿波动，5.02字/秒只是均值；句3 实测开口 29.38s vs 估算 27.33s（画面早切 2s），到句10 已偏 9s | whisper 词级时间戳 + silencedetect(-38dB/0.22s) 静音区间双校准；句首吸附区间起点 |
| P2 | concat 图像时长量化 | concat demuxer 对 PNG duration 量化到 1/25s 网格，每镜 +0.01~0.02s，43 镜累积 ~0.9s | 帧数精确架构（铁律14）；实测 `-r 30` 输入参数**不能**改变该网格 |
| P3 | 渲染器 1.5s 窗口截断 | v1 h5_render 只截前 1.5s，data-t>1.5s 元素全部不可见（42/43 页中招，最长 data-t=30s） | v3 时刻集 = 入场窗 ∪ 2fps 网格 ∪ SHOOT_DENSE ∪ 尾帧（铁律15） |

### 7.2 whisper 本地化
- `pip install faster-whisper`；PyAV 版本冲突时不要修 av，直接 `ffmpeg -ar 16000 -ac 1 -c:a pcm_f32le -f f32le` 转 raw + `np.fromfile` 喂数组（绕开 decode_audio）。
- HuggingFace 429（共享出口 IP）：`HF_ENDPOINT=https://hf-mirror.com` 或手动 curl `hf-mirror.com/Systran/faster-whisper-base/resolve/main/{model.bin,config.json,tokenizer.json,vocabulary.txt}`（vocabulary.json/preprocessor_config.json 是 15 字节的 404 页，别下）。
- base 模型 2C CPU 全片 740s 转写 42s（beam_size=1 + vad_filter + word_timestamps）；转写错字（郭帆→郭翻）不影响对齐——对齐用的是已知脚本文本 ↔ whisper 字符流 SequenceMatcher。
- z-ai asr API 限流窗口 ~13 次/周期，145 区间全量要数小时；本地 whisper 是正解。

### 7.3 B站素材通路（view API 412 时代）
- 412 墙：`x/web-interface/view`、视频页（curl/yt-dlp 均拦）、archive/stat API；**搜索/pagelist/reply/playurl API 游客可用**。
- 下载：`pagelist?bvid=` 拿 cid → `playurl?bvid=&cid=&qn=80&platform=html5&high_quality=1` 拿 durl mp4（720p）→ upos CDN 掐长连接，`curl -C - --retry 5 --retry-all-errors` 断点续传；下载后 ffprobe 时长体检（试看钳制坑 B31）。
- 截图：m.bilibili.com（iPhone UA）免验证码，`.main-cover .left` 元素截播放量条；player.bilibili.com 外链播放器（桌面 UA）截点赞计数（`contains('万')` DOM 定位）；评论区游客只见前 3 条热评，郭帆类名人评价 → 新闻报道段落截图（playwright 元素级 screenshot）。
- 真浏览器上下文也会遇 GeeTest 点击验证码（B8：点对也判负，等满 8s，失败整页 reload）——所以一律走 API+移动页，别碰桌面视频页。

### 7.4 图像处理小坑
- PIL 多通道求均值先 `.astype(int)`：uint8 相加溢出（206+209+209=624 → mod 256 = 112，均亮 37 假读数）。
- 白底 logo 键出阈值：距白 d<8 → alpha 0，d≥30 → 255，中间线性；纯黑字形（V=0）HSV 缩放无效，直接反转。
- 元素级网页截图常带"打开App"蓝横幅：按颜色行扫（B - max(R,G) > 15 首行）精确裁掉，比按高度比例裁可靠。

### 7.5 A/B 分段边界
- 终渲分段 `-t dur` 会在边界丢 2~3 帧（时间戳语义）；用 `-frames:v n` + B 段 `-ss n_A/30`，切点先 round 到帧边界；拼接后全片帧数必须 == round(总长×30)（本次 22211 精确命中）。
- 幂等检查不能只看文件存在：超时被杀会留 0 字节残骸（`getsize > 1MB` 才算完成）。

## §8 v4 验收修复轮新坑（2026-11-06 用户反馈，全部实测）

### 8.1 环境动效与 2fps 采样网格的适配（v4 最大隐患）
- 环境微动（float/pulse）由 sin 连续函数驱动，但截帧基础网格只有 2fps：float 若 data-sp>0.32（周期<3.1s），相邻采样帧位移可达 14px，物化到 30fps 后肉眼可见跳变。
- **红线参数**：float `data-sp≤0.32`、pulse `data-sp≤0.45`（amp×2π×sp 决定帧间位移，一律 ≤6px/0.5s）。
- 多元素环境动效必须用 `data-ph0` 错相（0/0.7/1.4…），否则同频同相=机械波，观感廉价。

### 8.2 入场动画的采样盲区
- v3 的时刻集（1.5s 入场窗 + 2fps 网格）对 data-t>1.5s 的入场只能采到 0~1 个中间帧——0.4s 的 pop 入场物化后变成瞬跳。
- v4 渲染器（h5_render_v4.py）直接解析 HTML 的 data-t/data-counter 自动生成入场窗（±0.45s@15fps；counter 按 ramp 全程@12fps），页面里的 SHOOT_KEYS 声明废弃（声明与实际 data-t 漂移后成为假数据）。

### 8.3 视频背景镜的分拆模式（B-roll 前景展示）
- 影片叠底镜直接铺卡片，观众根本看不清影片本身（用户验收反馈）。标准解法见 layout-spec §六：a 镜纯净前景 2~3s → b 镜 scrim 淡入 + 卡片。
- bg 源切割必须按帧边界连续：a 镜 `-ss t0 -frames:v n_a`、b 镜 `-ss t0+n_a/30`，否则拼接处跳帧。
- 亮色屏幕录像（白底 UI 的 10 倍速操作延时）做背景：纯色 scrim 不够，要纵向渐变（上 0.72/中 0.16/下 0.80），中部露出操作、上下承托文字。
- 横屏源（2880×1800）切 9:16 会只留中间 35% 宽：选段时确认关键操作在画面水平中部。

### 8.4 字幕位与安全框
- 字幕从视频底部（MarginV 84）上移到 y=1740（Alignment 2 + MarginV 180 = 安全框下缘外 1 个出血位）：画面底缘字幕条与 stage 底部 .src 来源行刚好相切，无重叠（v4 实测）。
- 画中主体内容永远不许压 y=1680（4:3 下缘）；canvas 页 hud-sub 预览带同步改为 top:1650/height:90。

### 8.5 成片整体提速（用户指定 1.1x）
- 在最终压片一步完成（修改程度最小）：`[0:v]setpts=PTS/1.1,fps=30` + `[0:a]atempo=1.1`（不变调）；不要再在管线前段改时间轴（会污染全部已对齐数据）。
- 烧录字幕随视频同步提速（无需重烧）；外挂 srt 全部时间戳 ÷1.1 重定时。
- QC 按新时长验收：740.36s→673.05s，帧数 22211→~20192（fps=30 重采样丢帧属预期，10% 帧率抖动不可见）。

### 8.6 文本规范执行（用户验收反馈的机械排查）
- 间隔号 `·` 全片 137 处（含 43 个 title 标签）→ 确定性映射表脚本替换（短语→逗号、并列信息→换行、引用标题→改写）→ 全局 grep 复验为零。
- 括注思考（"（视频页截图）""（口径：全网…实证）"）→ 剥离或移入 production-report。
- 最小信息（"10家平台·三集连载·第一集 价格篇"→"① 价格篇"）逐处人工判别，不可机械替换（口径行是数据完整性必需，删到看不懂同样是错）。

## §9 v6 复盘轮：三处回归的完整归因与修复（2026-11-06，防回归架构的由来）

> 本章保留项目细节作为案例实录。通用机制已提炼进 `anti-regression.md`。

### 9.1 回归一：音画不同步复发（字幕烧错时间轴）
- 现象：v5 双版本字幕与配音错位。
- 根因五连：①v3 修复用的 whisper 字幕卡 JSON 只在沙盒未入库；②沙盒回收后 v5 误用仓库里 v2 时代的旧对齐文件（385 卡，实测漂移 -23.6~+27.8s，86% 采样点 >0.5s）；③无开工对账步骤（仓库里明明有已验收 srt 真值）；④G1-G7 无字幕同步门禁；⑤长上下文里铁律"禁字数权重投产"未被执行。
- 修复：`make_canonical_subs.py` 从已验收 srt 反向重建权威卡 JSON（带 `_provenance`）；`assemble_v6 setup` 段逐卡对账断言（卡数/文本/±10ms），不过不开工；G8 门禁复验烧录 ASS。

### 9.2 回归二：嵌入影片比例失调
- 现象：横屏版内嵌影片"被拉伸、比例尺不对"。
- 根因：母版规范"背景层拉伸铺满 9:16"是为氛围图设计；v4 把真实影片升级为展示主体（S02a/S03a 纯净前景）后缩放规则未改——`scale=1080:1920:force_original_aspect_ratio=increase,crop` 对 16:9 源=放大 2.67×横向只露 31.7%，对 2.34:1 源=放大 3.50×只露 24.1%；"只保留水平中部 35%"被记入已知妥协后再无人复审。
- 修复：bg 双模式（fit=展示主体原生比例入舞台框 / cover=氛围底等比裁切，禁非等比拉伸）；G9 几何断言（抽帧实测窗口矩形 vs ffprobe 推算期望 ±6px，6/6 过）。

### 9.3 回归三：进度条中段重置（v4 引入、v5 未察觉）
- 现象：进度条 0→54%，372s 切点跳回 0 再 0→54%，永远不满格。
- 根因：v2_seg 的 `gen_seg_cmds` 段偏移（段内时间=全局-t0）在 v4/v5 重写 final 段时丢失，换成 `gen_progress_cmds(TOTAL)`（0 起步全程指令，段 B 只执行到前半）。
- 修复：恢复段偏移 + G10 门禁（切点前后±2s 与片尾抽帧量条宽，断言单调连续+终值≈满格；实测 539→544→1078px）。
- 教训：**重写管线段前必须列旧实现"已验证行为清单"逐条核对**（anti-regression §5）。

### 9.4 目检的误报教训
- VLM 把源片贴地特写镜头（脚部在上、地面占满——影片自身构图）误判为"裁切拉伸"。
- 仲裁：手工按同参数链生成参考帧与产物做像素 diff（窗口区平均差 5.1=编码噪声级）→ 几何完全正确。
- 结论：感知级检查必须锚点化（先算期望再对照），几何争议一律像素 diff 裁决（anti-regression §6）。

### 9.5 备份纪律补丁
- 决定正确性的中间产物与作品同级入库：权威字幕卡 JSON、timeline/shots JSON、当轮全部脚本（含临时工具——para_dl.py 曾用完即丢被迫重写）。
- 仓库里不允许"名字合理但血统不明"的同类文件并存（本次清理了 03-skill/ 下过期的 v1.0 SKILL.md 副本）。
