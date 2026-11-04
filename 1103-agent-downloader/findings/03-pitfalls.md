# findings/03 — 已知坑总清单（跳坑前必查）

> 规则：**每条坑 = 现象 + 真因 + 对策 + 状态**。状态：✅本轮实测 / 📚来源核实 / `[上轮]`上会话血泪。
> 排序：先流程坑（对所有平台生效），后平台坑。

## A. 流程坑（与环境和工作方式相关）

| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| A1 | 上轮 8 个脚本（geetest_beat2.py/bili_fetch.py…）消失 | 只存沙盒本地未推 GitHub，沙盒回收即焚 | **每个任务完成立即 commit+push**（RESUME 铁律1） | `[上轮]`已发生，损失坐实 |
| A2 | nohup 长任务跑一半消失 | 沙盒后台进程会被环境回收 | 前台跑 + `timeout` 分段；跑完立刻查 log | `[上轮]` |
| A3 | 上下文过长 → 沙盒/会话崩溃，工作断档 | 对话 token 膨胀 | RESUME.md 协议：state.json + worklog 尾部 5 条即可恢复，不读全史 | 本轮已建机制 |
| A4 | 自然语言概括把关键细节（参数/报错/数字）抹掉 | 摘要失真 | worklog key_facts **逐字摘录**原始行；全文进 logs/ 留证 | 本轮已建机制 |
| A5 | token 狂烧原地打转（同一命令反复试） | 失败后不读原始报错就盲试；大输出直接进上下文 | 失败先 `tail -30` 原始 log → 对照本清单 → 换通路；bot-check 类错误**重试必然无效**（bigiron triage 明示）；脚本输出压缩 ≤20 行 | 📚 |
| A6 | api.github.com 403 | 无 token 的匿名请求被限流 | 全部 GitHub API 调用带 token | ✅本轮实测 |
| A7 | git clone 拖垮沙盒 | clock 仓库 5.8GB | 只用 sparse clone（命令在 RESUME.md） | ✅本轮实测 |
| A8 | 密钥/cookie 泄露进公开仓库 | 手滑提交 | 密钥只放 `/home/z/my-project/.secrets/`（仓库 .gitignore 已含 `.secrets`）；commit 前 `git status` 检查 | 预防性 |
| A9 | agent-browser eval 报 `already declared` | 变量跨调用残留 | 一律 IIFE `(() => {...})()` | `[上轮]` |
| A10 | pip 装的 yt-dlp 是 distro 旧版 | Debian 源滞后数周-数月 | 只用 `/home/z/.venv/bin/pip install -U yt-dlp`（当前 2026.10.26） | 📚 |

## B. 平台坑

### YouTube
| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| B1 | `Sign in to confirm you're not a bot` | 数据中心 IP（本沙盒 HK 阿里云正是）+ 缺 PO token | ①player_client 变体 ②bgutil POT provider(node 版) ③burner cookies；**重试无效** | 📚+`[上轮]`上轮死于验证码 |
| B2 | `nsig extraction failed` | yt-dlp 版本旧于 YouTube 播放器 JS | `pip install -U yt-dlp`（别折腾 cookie） | 📚 |
| B3 | 下载中途 403 | googlevideo 签名 URL 过期 | 删 `.part` **全新重下**（勿续传）；大文件配 `aria2c -x 8` | 📚 |
| B4 | 一律只给 360p | SABR 流机制 | `player_client=web,android_vr,tv_downgraded` | 📚 |
| B5 | `Only images are available` | 认证失败伪装成格式问题 | 按 B1 处理，别调 -f | 📚 |

### B站
| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| B6 | API 直连 412 `request was banned` | 数据中心 IP + 手拼 buvid cookie 过不了风控（要看 ExClimbWuzhi 上报、canvas/webgl 完整指纹） | **真实浏览器上下文**（agent-browser/playwright）；yt-dlp 直测若 412 同理回退 | `[上轮]` |
| B7 | view API 412 但 search API 通 | view 有 wbi 签名墙 | 元数据走视频页 `__playinfo__`/`__INITIAL_STATE__`，搜索走同源页面内 fetch（credentials:'include'） | `[上轮]` |
| B8 | 验证码明明点对了却判失败 | 极验点击后跳转延迟 5-10s | 判定前等满 8s；失败必须整页 reload（隐藏刷新按钮 JS click 无效；多余重试点击会把新题点废） | `[上轮]` |
| B9 | 下载文件 `Invalid NAL unit size` | upos CDN 偶发坏包（~1/3） | 下载后全量 `ffmpeg -v error -i f -f null` 体检，坏的重下即愈 | `[上轮]` |
| B10 | 放映厅视频 302 到 bangumi | 番剧流是 MSE blob 且可能付费，playinfo 拿不到 | 直接换同题材普通 UGC 视频 | `[上轮]` |
| B11 | 只给 480x640 | 免登录上限 | 接受 480p 或用 SESSDATA；报"become a premium member"是登录态问题不是会员问题 | 📚 |
| B12 | m4s 合并后画质差 | 忘了 `-c copy` 被重编码 | `ffmpeg -i v.m4s -i a.m4s -c copy out.mp4` | `[上轮]` |

### 抖音
| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| B13 | yt-dlp 报 `Fresh cookies (not necessarily logged in) are needed` | 内置 Douyin extractor 失效（2025 起，a_bogus 签名） | 走 iesdouyin 分享页 SSR 旁路（见 findings/02 §6 五步） | 📚 |
| B14 | 下载到的永远 720p 带水印 | 用了 `/playwm/` 端点（彻底忽略 ratio 参数）；分享 URL 默认写死 `ratio=720p` | `playwm→play` 改写 + `ratio=default`（原始 master 唯一 4K 路径） | 📚 |
| B15 | 合集批量下载部分条目 403 死循环 | 抖音风控按条目命中（TikTokDownloader issue #689） | 单视频任务不受影响；批量失败条目跳过勿重试 | 📚 |
| B16 | 签名接口突然全挂 | a_bogus 算法随版本变化 | 检查 TikTokDownloader 是否有当日更新（本项目依赖它做回退正因它日更） | 📚 |

### 小红书
| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| B17 | URL 无法识别/直接 403 | 链接缺 `xsec_token`（浏览器地址栏 URL 天生不带） | **只用 App 分享按钮复制的链接** | 📚 |
| B18 | 只有 720p | 匿名档上限 | 加匿名 `web_session` cookie（非登录态）→ 4K HEVC | 📚 |
| B19 | 拿不准当前是匿名还是登录 | — | 调 `edith.xiaohongshu.com/api/sns/web/v2/user/me` 看 `guest` 字段 | 📚 |

### 微博 / X / Instagram / Threads
| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| B20 | 微博视频 300MB+ | quality 模式撞上 4K 长视频 | 测试选短视频或 `--format` 限制 | 📚 |
| B21 | X 用 cookie 后账号被封 | auth_token 自动化有封号风险 | **只用 burner 号**；取 token 后勿登出（登出会刷新 token） | 📚 |
| B22 | Instagram 匿名 401/登录墙 | 匿名重度受限 | sessionid cookie 基本必须；控制频次防 checkpoint | 📚 |
| B23 | Threads 插件突然失效 | Googlebot UA 绕法脆弱（Meta 收紧爬虫待遇即死） | 回退手工 curl SSR 解析；关注插件仓库更新 | 📚 |
| B24 | gallery-dl `--list-extractors | grep threads` 有 18 个匹配 | 全是 FoolFuKa/jschan 论坛"threads"板块，**不是 threads.net** | 用 `grep "threads.net"` 精确判别 | ✅本轮实测 |

### 选型坑
| # | 现象 | 对策 | 状态 |
|---|---|---|---|
| B25 | 选了已归档项目 | BBDown/BiliTools/bilibili-API-collect/junhoyeo-threads-api 已 archived，勿作为依赖（文档仍可读） | ✅本轮核查 |
| B26 | 找 bgutil 插件 404 | 正确路径 `Brainicism/bgutil-ytdlp-pot-provider`（大写 B） | ✅本轮实测 |
| B27 | 网页中转站（snapany 等） | 第一次解析后弹登录墙，不可靠 | 不作为主通路 | `[上轮]` |

<<<<<<< HEAD
### 素材轮新坑（B站管线, 2026-11-03 W021-W023）
| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| B28 | 游客搜索 code=0 但 result 空 | 长尾组合词风控软拦截（热点实体词命中率高） | 换社区常用词面，**仅一次**，不可穷尽 | ✅两轮22词实测 |
| B29 | view API 412 `request was banned` | 数据中心IP+游客直连（B6 变体）；dl_bilibili 上轮靠 popular 提供cid 特意绕开 view | **pagelist 替代 view 取 cid**（游客稳）；playurl 不受影响 | ✅实测 |
| B30 | 搜索API duration 与实际差4倍（S004 记485s 实1906s；S007 记1217s 实151s） | 搜索结果字段与分P真实时长不同源 | 期望时长一律用 pagelist 分P duration | ✅实测 |
| B31 | playurl durl 声称1087s/9MB，实际仅前180s（S008） | 平台对游客的**试看钳制** | 体检必须含"可解码时长比对"；yt-dlp 对B站同样 412（B6 原文命中） | ✅实测 |
| B32 | `/home/z/.venv/bin/yt-dlp` 消失 | 沙盒重启丢 venv 包（`/home/z/my-project/` 挂载卷不受影响） | 用前先 `--version` 探测，丢了 `venv pip install -U yt-dlp` | ✅实测 |
| B33 | push 被 GitHub 拒 | 单文件 100MB 硬限 | >100MB 素材 `split -b 90m` 分卷+md5 入库；commit 前 `git status` 复核 | ✅实测 |
| B34 | 长任务被 Bash 600s 上限杀掉留半截文件 | 单段超时（A2 变体）；半截文件 size≠durl.size 但容器 duration 元数据仍在 | 下载脚本做成**幂等续跑**（体检含字节数±2%比对）；分段重入 | ✅实测 |
| B35 | 体检把 dts 警告当坏包（"non monotonically increasing dts to muxer"） | `ffmpeg -f null` 对部分 mp4 时间基过敏，播放实际正常 | 只拦致命错误（Invalid data/NAL/moov/corrupt/EOF），dts 警告放行 | ✅实测 |
=======
## Round 2 新坑 (C系列)
| # | 现象 | 真因 | 对策 | 状态 |
|---|---|---|---|---|
| C1 | m.weibo.cn容器API纯HTTP永远ok=-100 | 访客SUB需JS护照(visitor.passport.weibo.cn链), requests/首页GET拿不到 | agent-browser真浏览器自动完成; 别再试纯HTTP | ✅已解 |
| C2 | genvisitor2教程写死tid担心过期 | tid竟是可复用的 | 直接用教程参数(2025-08教程, 2026-11实测仍有效) | 📚 |
| C3 | RedCrack import报 eval() arg TypeError | config.py相对路径读ini | 必须 os.chdir(RedCrack仓库根) 再import | 📚 |
| C4 | 小红书游客471/300012/-101三层墙 | 数据中心IP+无登录态叠加风控 | web_session cookie唯一解; 三层分别是shield风控/页面IP风控/API登录校验, 全测过才知最深一层是登录 | ✅终判 |
| C5 | 沙盒访问xiaohongshu.com首页变rednote.com | 海外IP判定自动切国际站 | 国际版API/签名函数(_webmsxyw)与国内版同源, 可直接用 | 📚 |
| C6 | agent-browser eval返回JSON被双层引号包裹 | CLI输出格式 | 解析循环: 先去引号层再解JSON文本层(见weibo_search_download.py ab_eval) | 📚 |
| C7 | 微博旧视频playback_list只有stream一档 | 2020年前后老微博无多码率 | 新视频有多档; 选档逻辑vids[-1]取最高 | 📚 |
>>>>>>> 4d8c76e (R2: 微博搜索→下载全链路固化(游客/零token) + 小红书搜索终判(web_session唯一钥匙) + 探针×10 + findings/坑清单C系列)
