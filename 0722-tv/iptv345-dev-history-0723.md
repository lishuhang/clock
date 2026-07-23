# iptv345 开发历史与经验教训

> **文档生成日期**: 2026-07-23 (HKT)
> **覆盖范围**: v1.0 → v2.8 完整开发周期 (含 ysp + xuexi 自动刷新)
> **目的**: 避免后续会话因上下文过长而崩溃；保留踩坑经验供未来 debug 参考。
> **来源**: `chat-history.txt` (1771 行) + 2026-07-22/23 任务对话

---

## 1. 项目目标

构建一个 Cloudflare Worker (`iptv345.lishuhang.workers.dev`，自定义域 `345.lishuhang.com`)，将 `m.345iptv.com` 的动态 m3u8 流转换为**固定 URL** 的中转源，让第三方播放器（VLC / PotPlayer / IINA / 浏览器 hls.js）可以直接使用。

**核心要求**:
- 用户使用的 URL 永远是 `https://345.lishuhang.com/<tid><id>.m3u8`
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

### v1.6: 性能修复（关键）
**问题**: 音调越来越低沉/音画不同步 ← hls.js back buffer 无限累积

**修复**:
| 配置项 | 旧值 | 新值 | 作用 |
|---|---|---|---|
| lowLatencyMode | true | **false** | 源站不是 LL-HLS |
| liveSyncDurationCount | 未设置 | **3** | 跟随 live edge 3 段 |
| backBufferLength | 未设置 | **10** | 丢弃 >10s back buffer |
| maxBufferLength | 未设置 | **20** | 限制前向缓冲 |
| fragLoadingMaxRetry | 未设置 | **6** | 段加载失败重试 |
| m3u8 CDN-Cache-Control | 未设置 | **no-store** | 禁止 CDN 缓存 m3u8 |

### v1.7: 源站可播性测试
对 1692 条线路全测。**结果**: 808 条线路不可播 (47.8%)
- fjitv 314 坏 (福建 IPTV，重定向到 HTTP IP)
- hlitv 142 坏 (黑龙江 IPTV，全部 HTTP IP)
- itv 241 坏 (综合源，大部分 HTTP IP)
- ipv6 93 坏
- gt 7 坏，movie/ys/ws 11 坏

UI 加 "隐藏源头不能播放的节目源" 设置。

### v2.0: 去敏感字眼
- CATALOG 数据中 name 字段清洗为 `tid+id` (如 `ws41`)
- 用户必须**导入名单**才能看到中文名
- URL 不写死，从 `window.location.origin` 读取
- 设置面板加 "导出 list" 按钮 → 输出 `名称,URL` 格式 txt

### v2.5 → v2.7: ysp 源接入 + 加密问题
- ysp API 流程: `POST /v1/player/auth` → `POST /v1/player/get_live_info` → 拿到 playurl
- Auth 签名: `MD5(排序参数 + 密钥 "n@7QKk%YeSjfw%22")`
- `get_live_info` 需要 WASM 生成的 cKey + SDK headers，**无法在 Worker 中复现** → 改用 Playwright 抓取 m3u8 URL
- **bufferAddCodecError 根因**: ysp TS 段使用 `encrypt:2` 加密 — H.264 NAL 单元被部分加扰，需 ysp 自己的 `hls.cmg.js + keygen_bg.wasm` 解密
- **结论**: 浏览器 hls.js **无法播放** ysp 源（绿屏），但 VLC/MPV/ffprobe 等原生 TS 播放器可正常播放

### v2.10: xuexi 源接入
- API: `POST https://gw-proxy-api.xuexi.cn/v1/api/exchangeAuthUrl` → 返回带 auth_key 的 m3u8 URL
- auth_key 有效期约 30 分钟
- 40 个频道 (CETV + 各省卫视)
- 段可直接 fetch，无需 Referer

### v2.8 (2026-07-22/23): 当前版本
**新增功能**:
1. **302/404 错误清晰化**: 区分 "channel not available at source" / "channel moved at source" / "stream broken at source"
2. **broken channel cache** (10 min TTL): 已知失效的频道不再反复请求源站
3. **/refresh/<tid><id>** 端点: 强制刷新某频道的所有缓存
4. **/health/<tid><id>** 端点: 单频道快速健康检查
5. **/refresh-gha** 端点: 手动触发 GitHub Actions 刷新 ysp/xuexi URL
6. **#EXT-X-PROGRAM-DATE-TIME 注入**: 在 m3u8 响应中注入当前时间戳，帮助 hls.js live edge 检测，缓解音画漂移
7. **版本号**: 状态页首行显示 `v2.8`

**部署**:
- `345.lishuhang.com` (custom domain) + `iptv345.lishuhang.workers.dev`
- 基础: v2.8-blind.js (175 KB)
- 完整版: v2.8-blind + 新鲜 YSP URLs (合并到现有 46 频道) + xuexi handlers (40 频道) = 192 KB
- GH_TOKEN secret 已设置到 worker，支持自动触发 GitHub Actions

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

### 4.13 Cloudflare API Token 格式 (2026-07-22 踩坑)
- `cfat_` 前缀的 token 不是标准 API Token，无法直接调用 REST API
- 需要使用 `cfut_` 前缀的 User API Token (40 字符)
- 验证: `GET /user/tokens/verify` 返回 `{"status":"active"}` 才可用
- 部署 worker: `PUT /accounts/{id}/workers/scripts/{name}` + multipart body

### 4.14 GitHub Actions workflow 覆盖部署 (2026-07-23 踩坑)
- lishuhang/345 repo 的 workflow 每 15 分钟自动跑，会用 repo 中的 `worker_v26_blind.js` 作为基础重建并部署
- 如果手动部署了新版本但没更新 repo，下次 workflow 运行会覆盖
- **解决方案**: 更新 repo 中的 `work/worker_v26_blind.js` 为新版本，并修改 `build_v210_blind.py` 注入新鲜 YSP URLs

### 4.15 YSP URL 刷新成功率不稳定
- gen_ysp_fast.js 用 Playwright 加载 yangshipin.cn 页面，捕获 m3u8 URL
- 部分频道 (CCTV1-3, CCTV5, CCTV5+) 经常加载失败 (页面超时或播放器不触发)
- 46 频道中通常只有 36-42 个能成功刷新
- **缓解**: build 脚本合并新鲜 URL 到现有 catalog (保留全部 46 频道)，未刷新的频道保持旧 URL (会 403)

### 4.16 build script 输出文件名必须匹配 workflow 期望
- workflow 期望 `work/worker_v210_blind.js`
- build 脚本最初输出 `work/worker_v28_full_blind.js` → workflow 的 `node --check` 失败
- **解决方案**: build 脚本输出文件名改为 `worker_v210_blind.js`

---

## 5. 当前状态 (v2.8 + ysp + xuexi, 2026-07-23)

### 5.1 部署
- Worker: `iptv345.lishuhang.workers.dev` (自定义域 `345.lishuhang.com`)
- 当前部署: v2.8-blind + ysp (46 频道) + xuexi (40 频道)
- 状态页: `v2.8 / status: 345 ok; ysp ok/error; xuexi ok`

### 5.2 路由
- `GET /` → 状态检测页 (`v2.8 / status: 345 ok; ysp ok; xuexi ok` 或错误详情)
- `GET /<tid><id>.m3u8` → 345 源 m3u8 代理 (如 `/gt5.m3u8`)
- `GET /ysp<...>.m3u8` → ysp m3u8 代理 (如 `/yspc01.m3u8` 为 CCTV1)
- `GET /xuexi_<hash>.m3u8` → xuexi m3u8 代理
- `GET /seg/<tid>/<id>/<file>` → 345 .ts 段代理
- `GET /yseg/<yspKey>/<file>` → ysp .ts 段代理
- `GET /xseg2/<host>/<path>` → xuexi .ts 段代理
- `GET /cat/<tid>` → 345 文本列表 (API)
- `GET /refresh/<tid><id>` → 强制刷新 345 频道缓存
- `GET /health/<tid><id>` → 345 频道健康检查
- `GET /refresh-gha` → 手动触发 GitHub Actions 刷新 ysp/xuexi

### 5.3 GitHub Actions 自动刷新
- Repo: `lishuhang/345`
- Workflow: 每 15 分钟运行
- 流程:
  1. Playwright 刷新 ysp + xuexi URL
  2. `build_v210_blind.py` 合并新鲜 YSP URLs 到 v2.8-blind 基础 + 注入 xuexi handlers
  3. `node --check` 语法验证
  4. `deploy_worker.py` 部署到 Cloudflare Workers
  5. 验证状态页
- Worker secret `GH_TOKEN`: 允许 `/refresh-gha` 端点触发 workflow

### 5.4 tv-app v1.3 (前端)
- 部署: `tv.lishuhang.com` (worker "tv")
- 4 项修复:
  1. 导航栏 3 秒静止自动隐藏
  2. 频道 3 轮失败后自动换台 (设置打开时暂停)
  3. 缓冲 60 秒超时刷新同源，仍失败则换台
  4. 导出文件名带日期时间 `tv_list-YYYYMMDD-HHMMSS.txt`
- hls.js 配置: backBufferLength=10, liveSyncDurationCount=3, lowLatencyMode=false

### 5.5 频道清单文件
- `tv_list-v2.txt`: 108 条，按 5 地区分类 (国际/香港/台湾/大陆/其他)
- `tv_list-v3.txt`: 194 条，v2 + ysp 46 频道 + xuexi 40 频道 (同名合并为多线路)
- `iptv345-channel-list.txt`: 1778 条 URL (345 源 1692 + ysp 46 + xuexi 40)，含所有频道与 m3u8 对应关系

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
- 每次成功部署后立即备份到 `download/`
- 同时 commit 到 GitHub repo (`lishuhang/clock` 0722-gpt2 分支 + `lishuhang/345` main 分支)
- **关键**: 更新 `lishuhang/345` 的 `work/worker_v26_blind.js` 为最新版本，否则 workflow 会用旧版覆盖

### 6.5 安全
- **永远不要把 Cloudflare token / GitHub token 写入 repo**
- 用本地 `.secrets` 文件存储 (已加 .gitignore)
- blind 版不暴露任何频道名、目录、UI，只返回状态码

### 6.6 GitHub Actions workflow 维护
- workflow 用 repo 中的脚本和基础 worker，必须同步更新
- build 脚本输出文件名必须匹配 workflow 期望 (`worker_v210_blind.js`)
- YSP URL 刷新成功率不稳定，build 脚本应**合并**新鲜 URL 到现有 catalog (保留全部频道)，而非替换

### 6.7 Cloudflare Token
- 使用 `cfut_` 前缀的 User API Token (不是 `cfat_` 前缀)
- 权限: `Account > Workers Scripts > Edit`
- 验证: `GET /user/tokens/verify` 返回 `{"status":"active"}`
- 设置 worker secret: `PUT /accounts/{id}/workers/scripts/{name}/secrets`

---

## 7. 文件清单

### 7.1 lishuhang/clock 0722-gpt2 分支
```
0722-tv/
├── chat-history.txt              # 原始开发对话 (1771 行)
├── iptv345-dev-history-0722.md   # 旧版开发历史
├── iptv345-dev-history-0723.md   # 本文档
├── iptv345-v2.1.js               # 历史完整版 (含三栏 UI)
├── iptv345-v2.7-blind.js         # 历史 blind 版
├── iptv345-v2.8.js               # 当前完整版 (155 KB)
├── iptv345-v2.8-blind.js         # 当前 blind 版基础 (176 KB)
├── v2.8-plan-0722-1946.md        # 外部配合方案
├── tv-app-v1.2.html              # 历史前端
├── tv-app-v1.3.html              # 当前前端 (85 KB)
├── tv_list.txt                   # 原始频道列表
├── tv_list-v2.txt                # 按 5 地区分类 (108 条)
├── tv_list-v3.txt                # v2 + ysp + xuexi (194 条)
├── iptv345-channel-list.txt      # 完整频道清单 (1778 条 URL)
└── scripts/
    ├── deploy_worker.py          # CF Worker 部署脚本
    ├── build_tv_worker.py        # tv worker 构建脚本 (HTML 包装)
    ├── tv_worker_template.js     # tv worker 模板
    └── build_v28_full.py         # v2.8 + ysp + xuexi 构建脚本
```

### 7.2 lishuhang/345 main 分支
```
├── .github/workflows/refresh.yml # 自动刷新 workflow (每 15 分钟)
├── scripts/
│   ├── gen_ysp_fast.js           # Playwright 刷新 ysp URL
│   ├── gen_xuexi_fast.js         # Playwright 刷新 xuexi URL
│   ├── fetch_xuexi_urls.py       # xuexi 频道 ID 抓取
│   ├── build_v210_blind.py       # 构建 worker (v2.8 base + ysp + xuexi)
│   └── deploy_worker.py          # 部署脚本
└── work/
    ├── worker_v26_blind.js       # 基础 worker (= v2.8-blind)
    ├── catalog_v2.json           # 345 频道目录
    ├── bad_lines.json            # 345 失效线路列表
    ├── xuexi_m3u8_urls.json      # xuexi 频道 ID 映射
    └── ysp_handlers.js           # ysp handlers (参考)
```

---

## 8. 后续方向

1. **ysp 浏览器播放**: 集成 `hls.cmg.js + keygen_bg.wasm` (大工程，用户已确认允许后续修复)
2. **GitHub Actions 稳定性**: ysp URL 刷新成功率不稳定 (36-42/46)，可考虑增加重试或并行刷新
3. **bad_lines 自动更新**: 源站线路状态会变化，bad_lines 应定期重新测试
4. **更多源**: 可考虑接入其他 IPTV 聚合站
5. **前端 v1.4+**: 多屏监视墙可加入"频道收藏"、"快捷键换台"、"EPG 节目单"等
6. **tv_list 用户自定义**: 用户可在 tv_list-v3.txt 基础上补充自定义频道，导入 tv-app 即可使用

---

*本文档由 Super Z (基于 GLM 模型，由 Z.ai 构建) 于 2026-07-23 整理。如需查阅原始对话，见 `chat-history.txt` (v1.0→v2.12) 和本次任务对话 (v2.8)。*
