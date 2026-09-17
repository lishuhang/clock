# iptv345 开发历史与经验教训

> **文档生成日期**: 2026-07-22 (HKT)
> **覆盖范围**: v1.0 → v2.12 完整开发周期
> **目的**: 避免后续会话因上下文过长而崩溃；保留踩坑经验供未来 debug 参考。
> **来源**: `chat-history.txt` (1771 行原始对话)

---

## 1. 项目目标

构建一个 Cloudflare Worker (`iptv345.lishuhang.workers.dev`，自定义域 `345.lishuhang.com`)，将 `m.345iptv.com` 的动态 m3u8 流转换为**固定 URL** 的中转源，让第三方播放器（VLC / PotPlayer / IINA / 浏览器 hls.js）可以直接使用。

**核心要求**:
- 用户使用的 URL 永远是 `https://iptv345.lishuhang.workers.dev/<tid><id>.m3u8`
- token 获取、user-agent 伪装、Referer 注入全部由 Worker 完成
- 后期扩展支持央视频 (ysp) 和学习强国 (xuexi) 源
- 提供 full 版（带前端 UI）和 blind 版（仅状态码 + m3u8 代理）以应对 DMCA 风险

---

## 2. 源站逆向机制 (345 源)

### 2.1 原始流程
```
浏览器加载播放页 → JS 解码生成动态 token
→ XHR 调用 https://p.iptv200.com/play.php?token=<动态>&tid=gt&id=5&p=0
→ 302 重定向到 https://t1.iptv200.com/live/tvbfc.m3u8?sign=<时间戳>-<md5>
→ 302 重定向到 https://t1.iptv200.com/live/tvbfc/index.m3u8?session=<随机>
→ 200 真实 m3u8 (引用 indexNNNN.js，其实是 .ts 片段)
```

### 2.2 关键破解点
- **pvjs.js 解密算法**: `base64-decode → XOR(key="iptv.com") → base64-decode → unescape`
- **变量名每次随机化**: 不能写死字段名，需用"最长 string var"启发式定位
- **inline script 有两种形态**: 有时反转、有时不反转 → 必须两种策略都尝试
- **URL 静态 token 不验证**: 任何 32-hex 都能通过 (dummy token 可用)
- **自定义 base64 解码器**: 源站 decode() 把 `=` 当作索引 64 而非 padding，标准 `atob` 会返回空

### 2.3 必须的请求头
- `User-Agent`: iPhone UA (`Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 ...)`)
- `Referer`: `https://m.345iptv.com/` — **段 URL 必须**，否则 404

---

## 3. 架构演进

### v1.0 → v1.4: 基础代理
- 单层 m3u8 解析 + 段代理
- **致命问题**: 段 URL 1-2 秒就过期，Worker 解析 m3u8 时 (3-4s) 把当次重定向到的 t-host 编码进段 URL → hls.js 几秒后请求段时该 host 段已 404

### v1.5: 三栏 SPA + 频道合并
- 1726 频道按地域/类型合并为 1065 个唯一频道，1692 条线路
- 三栏 UI: 左侧分类 / 中间频道 / 右侧播放器+线路切换
- 修复 `history.replaceState` 不能存 hls 实例对象（无法克隆）

### v1.6: 性能修复（关键）
**问题**:
1. 音调越来越低沉/音画不同步 ← hls.js back buffer 无限累积
2. 重复播放几分钟前的片段 ← m3u8 被 CDN 缓存

**修复**:
| 配置项 | 旧值 | 新值 | 作用 |
|---|---|---|---|
| lowLatencyMode | true | **false** | 源站不是 LL-HLS，开启会触发异常逻辑 |
| liveSyncDurationCount | 未设置 | **3** | 跟随 live edge 3 段 (~6s) |
| liveMaxLatencyDurationCount | 未设置 | **8** | 最大延迟 8 段，超过则追赶 |
| backBufferLength | 未设置 | **10** | 丢弃 >10s 的 back buffer (**关键**) |
| maxBufferLength | 未设置 | **20** | 限制前向缓冲 |
| fragLoadingMaxRetry | 未设置 | **6** | 段加载失败自动重试 |
| m3u8 CDN-Cache-Control | 未设置 | **no-store** | 明确禁止 CDN 缓存 m3u8 |
| PLAYPHP_URL_TTL | 3 min | **90 sec** | 更频繁刷新 token |
| SESSION_URL_TTL | 3 min | **60 sec** | 避免使用过期 session |

### v1.7: 源站可播性测试
对 1692 条线路全测：用 Node.js 调 `play.php` → 跟随 302 → 检查 m3u8 URL 协议。

**判定标准**:
- `https://*.iptv200.com` → 可播
- `http://<IP>` → 不可播 (Workers 禁止 fetch 裸 HTTP IP)
- `http://<domain>` → 不可播
- 404/超时 → 重试 2 次后判不可播

**结果**: 808 条线路不可播 (47.8%)
| 源 | 不可播数 | 说明 |
|---|---|---|
| fjitv | 314 | 福建 IPTV，几乎全部重定向到 HTTP IP |
| itv | 241 | 综合源，大部分 HTTP IP |
| hlitv | 142 | 黑龙江 IPTV，全部 HTTP IP |
| ipv6 | 93 | IPv6 源，大部分 HTTP IP |
| gt | 7 | 港澳台仅 7 个坏 |
| movie/ys/ws | 11 | 少量坏 |

UI 加 "隐藏源头不能播放的节目源" 设置；过滤模式下 334 个频道所有线路都坏 → 自动隐藏。

### v2.0: 去敏感字眼
**强制要求**: 禁止在源代码 / 生成的 HTML 中出现 `电视`、`TV`、`IPTV`、`频道` 等敏感词。

**实现**:
- CATALOG 数据中 name 字段清洗为 `tid+id` (如 `ws41`)，源标签清洗为 tid
- 用户必须**导入名单**才能看到中文名
- URL 不写死，从 `window.location.origin` 读取
- 删除独立播放页 (`/play/<tid>/<id>`)
- 设置面板加 "导出 list" 按钮 → 输出 `名称,URL` 格式 txt，第三方 IPTV 软件可读

### v2.1: 导出过滤
勾选 "隐藏不能播放的源" 时，导出的 txt 自动过滤坏线路。

### v2.5: 央视频 (ysp) 源接入
- API 流程: `POST /v1/player/auth` → `POST /v1/player/get_live_info` → 拿到 playurl
- Auth 签名: `MD5(排序参数 + 密钥 "n@7QKk%YeSjfw%22")`
- `get_live_info` 需要 WASM 生成的 cKey + SDK headers，**无法在 Worker 中复现** → 改用 Playwright 抓取 m3u8 URL
- m3u8/段**无需 Referer**，URL 有效期数小时
- 45/48 频道成功捕获 (缺 CCTV5/CCTV5+/山西卫视，页面加载超时)

### v2.6 → v2.7: ysp 加密问题
**bufferAddCodecError 根因**: ysp TS 段使用 `encrypt:2` 加密 — H.264 NAL 单元被部分加扰，需 ysp 自己的 `hls.cmg.js + keygen_bg.wasm` 解密。

**部分缓解**: 在 m3u8 响应中包装 master playlist + `CODECS="avc1.640029,mp4a.40.2"` 修正编解码器字符串 (hls.js 自动检测会得到错误的 `avc1.640129`)。

**最终结论**: 浏览器 hls.js **无法播放** ysp 源（绿屏 / bufferAddCodecError），但 VLC/MPV/ffprobe 等原生 TS 播放器可正常播放。

### v2.10: 学习强国 (xuexi) 源接入
- API: `POST https://gw-proxy-api.xuexi.cn/v1/api/exchangeAuthUrl` → 返回带 auth_key 的 m3u8 URL
- auth_key 有效期约 30 分钟
- 40 个频道 (CETV + 各省卫视)
- 段可直接 fetch，无需 Referer

### v2.12: 自动刷新架构
**问题**: ysp (ysign ~2h 过期) 和 xuexi (auth_key 30min 过期) 的 URL 会在 Worker 部署期间就过期。

**架构**:
| 层 | 机制 | 频率 | 作用 |
|---|---|---|---|
| 1 | GitHub Actions cron | 每 15-20 分钟 | 主动刷新所有 URL + 部署 |
| 2 | Worker Cron Trigger | 每 5 分钟 | 检测 403，触发 GitHub Actions |
| 3 | Worker on-demand | 用户访问时 | 检测 403，触发 GitHub Actions |
| 4 | 手动 | 按需 | `curl /refresh-gha` |

GitHub repo: `lishuhang/345` (含 Playwright 脚本 + 部署脚本 + workflow)

---

## 4. 关键踩坑记录 (Agent Debug 必读)

### 4.1 atob 陷阱
源站 `decode()` 把 `=` 当作索引 64 (普通字符)，**不是 padding**。标准 `atob` 遇到开头的 `=` 直接返回空字符串。**必须实现自定义解码器**。

### 4.2 inline script 反转
不同页面加载时 inline script 结构不一样，**有时反转有时不反转**。最稳健方案是两种策略都尝试，选择产生有效 xac 的那种。

### 4.3 段 URL 几乎立刻过期
- 同一个段 URL 连续抓 10 次，前 2 次成功，第 3 次开始 404 (窗口只有约 1 秒)
- 源站每次重定向到不同 t-host (t1/t2/t3.iptv200.com)
- 段必须从对应 t-host 拉取，从其他 t-host 拉同一段会 404
- **解决方案**: 缓存 session URL (60s TTL)，m3u8 和 seg 都用同一 session URL 实时拉取

### 4.4 Chrome 桌面版不原生支持 HLS
- `canPlayType('application/vnd.apple.mpegurl')` 可能返回 `'maybe'` 导致误判
- 必须优先用 hls.js，不信任 canPlayType
- 静音自动播放绕过浏览器策略，点击视频可取消静音

### 4.5 CDN 缓存 m3u8 导致重复播放
- 仅 `Cache-Control: no-cache` 不够，Cloudflare 边缘节点可能忽略它
- 必须显式 `CDN-Cache-Control: no-store` + `Surrogate-Control: no-store`

### 4.6 backBuffer 累积导致音画漂移
- hls.js 默认不限制 back buffer → 旧数据不被丢弃 → demuxer 处理越来越慢 → A/V PTS 渐行渐远
- 必须设置 `backBufferLength: 10` (秒)
- `lowLatencyMode: true` 不适合普通 HLS 流，会触发 LL-HLS 特定逻辑导致异常

### 4.7 Workers 禁止 fetch 裸 HTTP IP
- fjitv/hlitv 等源的 play.php 重定向到 `http://112.50.243.8/...` (HTTP + 裸 IP)
- Cloudflare Workers 环境禁止 fetch 裸 HTTP IP → 这些线路在中转后无法播放
- 必须预先测试，生成 `bad_lines` 列表，前端可隐藏

### 4.8 Python subprocess 调用 Node 的 token 失效问题
- Python `subprocess.run(['node', '-e', helper, ...])` 启动 Node 要 ~2s
- 这 2s 内 token 可能就过期了
- **解决方案**: 用纯 Node 脚本一次性完成 "生成 token + fetch m3u8"

### 4.9 进程崩溃 (OOM / 文件描述符泄漏)
- `ulimit -n` 默认 1024，Node 高并发 + keep-alive 可能耗尽
- 解决: 降低并发到 3-4，关 keep-alive，加 `--max-old-space-size=256`
- 加 checkpoint 文件支持断点续跑

### 4.10 间歇性 404
- 源站对某些 token 返回 404，重新生成 token 又可能 302
- fjitv:1 测试 10 次有 5 次成功 — 不可靠
- **解决方案**: 增加 5 次重试，每次重新生成 token

### 4.11 history.replaceState 不能存 hls 实例
- `replaceState(state, ...)` 的 state 必须可克隆
- hls 实例包含不可克隆的引用 → 报错
- **解决方案**: state 只存简单字段 (lineIndex 等)

### 4.12 ysp encrypt:2 加密无法在浏览器解密
- TS 段 H.264 NAL 单元被部分加扰
- 标准 hls.js 无法解密
- ysp 自己用 `hls.cmg.js + keygen_bg.wasm` 解密
- **结论**: 浏览器无法播放 ysp 源，但 VLC/MPV/ffprobe 等原生 TS 播放器可正常播放
- **未解决问题**: 需要将 ysp 的 hls.cmg.js + WASM 集成到播放页面 (大工程)

---

## 5. 当前状态 (v2.7-blind)

### 5.1 部署
- Worker: `iptv345.lishuhang.workers.dev`
- 自定义域: `345.lishuhang.com`
- 当前部署: v2.7-blind (含 345 + ysp + xuexi 三源)

### 5.2 路由
- `GET /` → 状态检测页 (`status: 345 ok; ysp ok; xuexi ok` 或错误详情)
- `GET /<tid><id>.m3u8` → m3u8 代理 (345 源，如 `/gt5.m3u8`)
- `GET /ysp<...>.m3u8` → ysp m3u8 代理 (如 `/yspc01.m3u8` 为 CCTV1)
- `GET /xuexi_<hash>.m3u8` → xuexi m3u8 代理
- `GET /seg/<tid>/<id>/<file>` → .ts 段代理
- `GET /cat/<tid>` → 文本列表 (API)
- `GET /refresh-gha` → 手动触发 GitHub Actions 刷新

### 5.3 已知问题 (待 v2.8 修复)
1. 港澳台翡翠台、无线新闻台等: 播放一段时间后声音越来越低沉 → 可能 backBuffer 配置未在 blind 版生效
2. now新闻台、hoy78 等部分源: 有时无法播放或卡住 → 需检查具体线路
3. xuexi 和 ysp: token 无法实时更新，GitHub Actions 自动化有失败情况
4. 部分 345 源可能因源站限流而间歇性 404

### 5.4 GitHub Actions 自动刷新
- Repo: `lishuhang/345`
- Workflow: 每 15-20 分钟运行
- 流程: Playwright 刷新 ysp + xuexi URL → 构建 Worker → 部署
- Worker Cron: 每 5 分钟检测 403 → 触发 workflow

---

## 6. 经验法则

### 6.1 调试 345 源
- 用 iPhone UA + Referer `https://m.345iptv.com/`
- 测试段时必须立即抓取 (1 秒内)，否则过期
- 失败时重新生成 token (不要复用)

### 6.2 测试 Workers 部署
- 用 Playwright 模拟 Chrome 131，拦截网络请求
- 长时间播放测试至少 2-3 分钟，确认 currentTime 持续前进 + 0 失败请求
- `paused: false` + `readyState: 4` 才是真在播放

### 6.3 防止进程崩溃
- Node 测试脚本: 并发 ≤ 4，加 `--max-old-space-size=256`
- 加 checkpoint 文件，支持断点续跑
- 用 `process.stdout.write` + flush 而不是 `console.log`

### 6.4 文件备份
- 每次成功部署后立即备份到 `download/iptv345-vX.Y(-blind).js`
- 同时 commit 到 GitHub repo (lishuhang/clock / 0722-tv 目录)

### 6.5 安全
- **永远不要把 Cloudflare token / GitHub token 写入 repo**
- 用本地 `.secrets` 文件存储 (已加 .gitignore)
- blind 版不暴露任何频道名、目录、UI，只返回状态码

---

## 7. 文件清单

### 7.1 输入文件 (本次任务)
```
/home/z/my-project/clock-repo/0722-tv/
├── iptv345-v2.1.js           # 历史完整版 (含三栏 UI)
├── iptv345-v2.7-blind.js     # 当前线上 blind 版
├── tv-app-v1.2.html          # 当前线上前端
├── tv_list.txt               # 频道列表
└── chat-history.txt          # 完整开发对话
```

### 7.2 期望输出 (本次任务)
```
iptv345-dev-history-0722.md   # 本文档
iptv345-v2.8.js               # 完整版 (含三栏 UI + 修复)
iptv345-v2.8-blind.js         # blind 版 (仅状态 + m3u8 代理)
v2.8-plan-0722-1822.md        # (可选) 需外部配合的方案
tv-app-v1.3.html              # 前端 v1.3 (4 项修复)
tv_list-v2.txt                # 按国家/地区分类
```

---

## 8. 后续方向

1. **ysp 浏览器播放**: 集成 `hls.cmg.js + keygen_bg.wasm` (大工程)
2. **GitHub Actions 稳定性**: ysp URL 在 workflow 运行期间过期 — 需要更频繁的刷新或分批部署
3. **bad_lines 自动更新**: 源站线路状态会变化，bad_lines 应定期重新测试
4. **更多源**: 可考虑接入其他 IPTV 聚合站
5. **前端 v1.3+**: 多屏监视墙可加入"频道收藏"、"快捷键换台"、"EPG 节目单"等

---

*本文档由 Super Z (基于 GLM 模型，由 Z.ai 构建) 于 2026-07-22 整理。如需查阅原始对话，见 `chat-history.txt`。*
