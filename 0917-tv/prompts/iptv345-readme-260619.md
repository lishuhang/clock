---
AIGC: {"Label":"1","ContentProducer":"001191110108MA01KP2T5U00000","ProduceID":"2e1b4417d76ea2db77bef1f5234774a7","ReservedCode1":"","ContentPropagator":"001191110108MA01KP2T5U00000","PropagateID":"2e1b4417d76ea2db77bef1f5234774a7","ReservedCode2":""}
---

# iptv345 项目交接文档

> 最后更新：2026-06-19
> 当前线上版本：**blind v2.1**（无前端 UI，仅状态检测）
> 备份目录：`/home/z/my-project/download/`

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构与工作原理](#2-架构与工作原理)
3. [完整功能清单](#3-完整功能清单)
4. [Blind 脚本用途与用法](#4-blind-脚本用途与用法)
5. [版本迭代历程（Changelog）](#5-版本迭代历程changelog)
6. [Agent Debug 踩坑说明](#6-agent-debug-踩坑说明)
7. [文件清单与部署方法](#7-文件清单与部署方法)
8. [已知限制与未来方向](#8-已知限制与未来方向)

---

## 1. 项目概述

### 目标

构建 Cloudflare Worker 中转 `m.345iptv.com` 直播源，实现：
- 用户用**固定地址**（如 `https://iptv345.lishuhang.workers.dev/gt5.m3u8`）在第三方播放器播放
- Worker 自动完成 iPhone UA 伪装、动态 token 生成、重定向跟随、ts 段代理
- 用户无需关心源站的加密 token 机制

### 源站机制（逆向结果）

源站 `m.345iptv.com` 的播放流程：

```
用户浏览器 → 播放页 HTML（含加密 blob + pvjs.js 解密器）
           → JS 解密生成动态 token
           → XHR 调用 https://p.iptv200.com/play.php?token=<动态>&tid=<tid>&id=<id>&p=0
           → 302 重定向到 https://t1/t2/t3.iptv200.com/live/<channel>/<file>.m3u8?sign=<ts>-<md5>
           → 302 重定向到 /index.m3u8?session=<random>
           → 200 返回真实 m3u8
           → hls.js 持续拉取 .ts 段
```

**关键发现**：
- 播放页 URL 中的 `token` 参数可以是任意 32 位十六进制字符串（不被服务端校验）
- `pvjs.js` 是 jsjiami.com.v7 混淆，但核心算法是：`base64decode → XOR("iptv.com") → base64decode → unescape`
- 源站的 `decode()` 函数把 `=` 当作 keyStr 第 64 个字符（普通数据），不是 padding——标准 `atob` 遇到 `==` 开头的字符串会返回空
- 不同页面加载时 inline script 结构不一致：有时反转长变量、有时不反转
- 源站每次返回不同的 inline script（longVar 内容完全不同），token 每次都不同
- 段 URL 的有效期只有约 1-2 秒（连续抓 10 次，前 2 次成功，第 3 次开始 404）
- 源站每次 `play.php` 重定向到**不同的 t-host**（t1/t2/t3.iptv200.com）
- 段 URL 必须从对应的 t-host 拉取，从其他 t-host 拉同一段会 404
- 源站 iptv200.com 的 .ts 段**必须带 `Referer: https://m.345iptv.com/`** 才返回 200，否则 404

---

## 2. 架构与工作原理

### Worker 路由

| 路由 | 功能 | blind 版保留 |
|------|------|:---:|
| `GET /` | 首页（v2.1 是三栏 SPA；blind 是状态检测页） | ✅（改为状态页） |
| `GET /<tid><id>.m3u8` | m3u8 代理（如 `/gt5.m3u8` → tid=gt&id=5） | ✅ |
| `GET /seg/<tid>/<id>/<filename>` | .ts 段代理（实时解析 session URL，从同 host 拉段） | ✅ |
| `GET /cat/<tid>` | 文本列表（API） | ✅ |
| `GET /play/<tid>/<id>` | 独立播放页（v2.0 已删除） | ❌ |

### m3u8 解析流程（Worker 内部）

```
1. resolvePlayPhpUrl(tid, id):
   - 抓取播放页 HTML
   - 提取 inline script 中的长加密 blob
   - decryptXac: 尝试"反转"和"不反转"两种策略，选择产生有效 xac（以 <script> 开头）的
   - parseXac: 用正则提取 keyValue / staticToken / dynamicToken / xorSuffix
   - computePlayPhpUrl: reverse → b64decode → XOR(key+suffix) → b64decode → replace token → replace key
   - 缓存结果 90 秒

2. resolveSessionUrl(tid, id):
   - 调用 play.php → 跟随 302 重定向链 → 得到最终 session URL
   - 缓存 60 秒（复用同一 session，避免每次落到不同 t-host）

3. handleM3u8:
   - 用 session URL 拉 m3u8
   - 重写段 URL 为 /seg/<tid>/<id>/<filename> 格式
   - 返回带 CORS 头的 m3u8

4. handleSeg:
   - 实时调用 resolveSessionUrl 拿当前 session
   - 从同一个 host 拉段（段在 1 秒内有效，必须用同 host）
   - 404 时自动失效 session 缓存 + 重试一次
   - Cloudflare Cache API 缓存段 10 分钟
```

### 缓存策略

| 缓存 | 类型 | TTL | 说明 |
|------|------|-----|------|
| playPhpUrl | 内存 Map | 90 秒 | 动态 play.php URL |
| sessionUrl | 内存 Map | 60 秒 | play.php 重定向到的最终 m3u8 URL |
| .ts 段 | Cloudflare Cache API | 10 分钟 | 段是不可变的，可长期缓存 |
| m3u8 响应 | 不缓存 | - | 直播滑动窗口需要新鲜数据 |

### hls.js 配置（v1.6+ 优化）

```js
{
  liveDurationInfinity: true,
  lowLatencyMode: false,        // 源站是普通 HLS，非 LL-HLS
  enableWorker: true,
  liveSyncDurationCount: 3,     // 跟随 live edge 3 段（~6s）
  liveMaxLatencyDurationCount: 8,  // 最大延迟 8 段
  backBufferLength: 10,         // 丢弃 > 10s 的 back buffer（防 A/V 漂移）
  maxBufferLength: 20,          // 限制前向缓冲
  fragLoadingMaxRetry: 6,       // 段加载失败自动重试
  fragLoadingRetryDelay: 500,
}
```

### m3u8 响应头（防 CDN 缓存）

```
Cache-Control: no-cache, no-store, must-revalidate
CDN-Cache-Control: no-store
Surrogate-Control: no-store
Pragma: no-cache
Expires: 0
```

---

## 3. 完整功能清单

### v2.1 完整版功能

#### 三栏 SPA 界面
- **左栏**：5 个分类（央视/卫视/港澳台/地方/轮播），显示频道数
- **中栏**：当前分类的频道列表，多线路频道显示线路数徽章，搜索框实时过滤
- **右栏**：播放器（hls.js）+ 线路切换按钮 + 详情（名称/m3u8 直链）

#### 线路切换
- 同一频道多个源（如 CCTV-1 有 18 条线路：福建IPTV/黑龙江IPTV/IPv6/综合/咪咕/央视源）
- 点击线路按钮切换，m3u8 地址同步更新，播放器自动加载新源

#### 设置面板（右上角 ⚙️ 按钮）
1. **隐藏不能播放的源**：勾选后隐藏 808 条经测试不可播的线路；频道如所有线路都被隐藏则不显示
2. **导入名单**：导入 JSON 格式的 `tid+id → 中文名` 对应关系（如 `{"ws41":"三沙卫视"}`）
3. **导出名单**：导出当前名称映射为 `names.json`
4. **清除**：清除所有导入的名称
5. **导出 list**：下载 `list.txt`，格式 `名称,m3u8地址`，同一频道的不同源同名排列，可被第三方 IPTV 软件读取

#### URL 状态同步
- `?c=<分类>&ch=<频道索引>&line=<线路索引>`
- 浏览器后退/前进支持
- 设置存入 localStorage，刷新后保留

#### 频道合并与重分类
- 1726 个原始频道 → 1051 个唯一频道（1692 条线路）
- 合并规则：去除 FHD/HD/U/720p 后缀；CCTV-1综合/CCTV-1HD/CCTV1 → CCTV-1
- 手动合并：凤凰系列、CGTN 系列、CCTV 付费频道移到央视、北京纪实移到地方等
- 5 个分类：央视(52) / 卫视(51) / 港澳台(69) / 地方(283) / 轮播(596)

#### 不可播线路标记
- 808 条线路经测试在源站无法播放（重定向到 HTTP 裸 IP，Workers 不可达）
- 按源分布：fjitv 314全坏、hlitv 142全坏、itv 241坏/99好、ipv6 93坏/4好、gt 7坏/47好

### blind 版功能（当前线上）

- **首页**：`status ok`（正常）或 `status error` + debug log（出错时）
- **m3u8 代理**：全部保留（包括不可播的——不可播的会返回 502，但路由存在）
- **段代理**：全部保留
- **cat API**：保留
- **无任何前端 UI**：无 HTML/JS/CATALOG 数据暴露

---

## 4. Blind 脚本用途与用法

### 用途

blind 版本是"隐身模式"——隐藏所有前端界面和频道目录，只保留 m3u8 代理功能。适用于：
- 已导出 `list.txt` 和 `names.json`，不需要前端界面
- 防止搜索引擎或版权方爬取频道目录
- 只需要固定 m3u8 地址在第三方播放器中使用

### 用法

#### 日常使用

直接在 VLC / PotPlayer / IINA 等播放器中打开：
```
https://iptv345.lishuhang.workers.dev/gt5.m3u8
```

#### 健康检查

浏览器访问 `https://iptv345.lishuhang.workers.dev/`：
- 正常：显示 `status ok`（HTTP 200）
- 出错：显示 `status error` + 详细 debug log（HTTP 503），包含：
  - catalog 加载状态
  - bad_lines 加载状态
  - m3u8 解析测试结果（gt5）
  - 段抓取测试结果

#### 切换回完整版

手动上传 `iptv345-v2.1.js` 覆盖 Worker：
```bash
# 用 Cloudflare API 部署完整版
python3 /home/z/my-project/scripts/deploy_worker.py
# （deploy_worker.py 默认读取 work/worker.js，需先复制）
cp /home/z/my-project/download/iptv345-v2.1.js /home/z/my-project/work/worker.js
python3 /home/z/my-project/scripts/deploy_worker.py
```

#### 切换到 blind 版

```bash
cp /home/z/my-project/download/iptv345-2.1-blind.js /home/z/my-project/work/worker.js
python3 /home/z/my-project/scripts/deploy_worker.py
```

---

## 5. 版本迭代历程（Changelog）

### v1.0（初始版本）
- 逆向 `pvjs.js` 混淆解码器
- 实现播放页抓取 → token 解密 → play.php 调用 → m3u8 代理
- 首页列出 1726 个频道（10 个源分类）
- 部署到 `iptv345.lishuhang.workers.dev`

### v1.5（三栏 UI + 频道合并）
- 频道重分类：10 个源 → 5 个地域分类（央视/卫视/港澳台/地方/轮播）
- 同频道不同源合并为多线路（如 CCTV-1 有 18 条线路）
- 三栏 SPA 布局：左栏分类 / 中栏频道 / 右栏播放器+详情
- 线路切换：点击线路按钮切换，m3u8 地址同步更新
- URL 状态同步：`?c=<cat>&ch=<idx>&line=<idx>`

### v1.6（性能优化 + 手动合并）
- **hls.js 配置优化**：关闭 `lowLatencyMode`，添加 `backBufferLength: 10` / `liveSyncDurationCount: 3` / `maxBufferLength: 20`——修复音调越来越低沉/音画不同步问题
- **m3u8 缓存控制**：添加 `CDN-Cache-Control: no-store` / `Surrogate-Control: no-store`——修复重复播放几分钟前片段问题
- **缓存 TTL 缩短**：playPhpUrl 3min→90s，sessionUrl 3min→60s
- 手动合并：凤凰系列、CGTN 系列、CCTV 付费频道、北京纪实等
- 3 分钟连续播放测试：0 失败，完美实时跟播

### v1.7（不可播线路标记 + 设置按钮）
- 测试全部 1692 条线路的可播性（Node.js 脚本，检查 play.php 重定向目标）
- 标记 808 条不可播线路（重定向到 HTTP 裸 IP，Workers 不可达）
- 设置面板：右上角 ⚙️ 按钮
- "隐藏不能播放的节目源"开关：勾选后隐藏坏线路，频道全坏则不显示
- localStorage 持久化设置

### v2.0（去敏感化 + 导入导出）
- **去敏感字眼**：标题改"345"，去除 IPTV/电视/TV/频道/Cloudflare Worker 等字样
- CATALOG 数据清洗：频道名 → tid+id（如 `ws41`），源标签 → tid，分类名 → key
- 设置面板新增"导入名单"/"导出名单"：JSON 格式的 `tid+id → 中文名` 对应关系
- 设置面板新增"导出 list"：下载 `list.txt`，格式 `名称,m3u8地址`，同名排列
- URL 不写死：读地址栏 `window.location.origin` 组装
- 删除独立播放页（`/play/<tid>/<id>` 路由）
- 生成 `default_names.json`（1692 条默认名称映射）

### v2.1（导出过滤）
- 勾选"隐藏不能播放的源"时，导出的 `list.txt` 只包含可播源（1692→884 行）

### blind v2.1（当前线上）
- 隐藏所有前端 UI
- 首页改为状态检测页（`status ok` / `status error` + debug log）
- 保留全部 m3u8/seg/cat 代理功能（包括不可播的）

---

## 6. Agent Debug 踩坑说明

### 坑 1：`atob` vs 自定义 decoder

**现象**：某些频道的 xac 解密返回空字符串，导致 token 生成失败。

**根因**：源站的 `decode()` 函数把 `=` 当作 keyStr 第 64 个字符（普通数据），不是 padding。标准 `atob` 遇到 `==` 开头的字符串会返回空。

**修复**：实现自定义 `b64decode`，完全复刻源站的 `decode()` 行为：
```js
function b64decode(s) {
  const keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
  // ... 逐字符解码，= 当作 index 64
}
```

### 坑 2：inline script 反转不一致

**现象**：不同页面加载时，有时能解密有时不能。

**根因**：源站的 inline script 有时反转长变量、有时不反转。单一策略无法覆盖所有情况。

**修复**：`decryptXac` 同时尝试"反转"和"不反转"两种策略，选择产生有效 xac（以 `<script>` 开头）的那种。

### 坑 3：段 URL 几乎立刻过期

**现象**：m3u8 返回的段 URL 在几秒后就 404。

**根因**：
1. 源站段 URL 有效期只有约 1-2 秒
2. 源站每次 `play.php` 重定向到**不同的 t-host**（t1/t2/t3）
3. 段 URL 必须从对应的 t-host 拉取，从其他 t-host 拉同一段会 404
4. 旧架构在 m3u8 里硬编码当次重定向的 t-host，等 hls.js 几秒后请求段时已过期

**修复**：引入 **session URL 缓存**：
- 缓存 play.php 重定向到的最终 `index.m3u8?session=xxx` URL（60 秒 TTL）
- m3u8 请求复用缓存 session（每次只 0.5s）
- 段 URL 改为 `/seg/<tid>/<id>/<filename>` 格式，不预编码 host
- `handleSeg` 实时调用 `resolveSessionUrl` 拿当前 session，**从同一个 host 拉段**
- 404 时自动失效 session 缓存 + 重试一次

### 坑 4：Chrome 直接访问 m3u8 黑屏

**现象**：Chrome 直接访问 m3u8 URL 显示有宽高比但黑屏，F12 网络面板无新增下载。

**根因**：Chrome 桌面版不原生支持 HLS 播放（Safari 才支持），直接访问 m3u8 只会显示空白的 video 容器。

**修复**：新增 `/play/<tid>/<id>` HTML 播放页面，用 hls.js 在浏览器内播放（v2.0 删除该功能，改为三栏 SPA 内嵌播放器）。

### 坑 5：音调越来越低沉/音画不同步

**现象**：某些源播放几分钟后音调变低、语速变慢、音画不同步。

**根因**：hls.js 的 back buffer 无限累积，demuxer 处理越来越慢，A/V PTS 渐行渐远。`lowLatencyMode: true` 不适合普通 HLS 流（源站不是 LL-HLS）。

**修复**：
- `lowLatencyMode: false`
- `backBufferLength: 10`（丢弃 > 10s 的 back buffer）
- `liveSyncDurationCount: 3` / `liveMaxLatencyDurationCount: 8`
- `maxBufferLength: 20`（限制前向缓冲）

### 坑 6：重复播放几分钟前的片段

**现象**：播放器重复播放旧片段，直到中断。

**根因**：m3u8 响应只有 `Cache-Control: no-cache`，Cloudflare 边缘节点可能忽略它，自己缓存 m3u8 → hls.js 持续拿到旧 MEDIA-SEQUENCE → 持续请求旧段名 → 段缓存命中返回旧内容。

**修复**：m3u8 响应添加 `CDN-Cache-Control: no-store` + `Surrogate-Control: no-store` + `Pragma: no-cache` + `Expires: 0`。

### 坑 7：fjitv/hlitv 等 IPTV 源不能播放

**现象**：fjitv:1 (CCTV-1) 在 Worker 中转后无法播放。

**根因**：源站的 play.php 把 fjitv/hlitv 频道重定向到 `http://112.50.243.8/...`（HTTP 裸 IP），而 Cloudflare Workers 环境禁止 fetch 裸 HTTP IP。

**修复**：标记 808 条不可播线路，前端可隐藏。这些线路在源站本身就不能播放，中转无意义。

### 坑 8：Python subprocess 调用 Node helper 的 token 失效

**现象**：Python 调用 Node 生成 play.php URL 后，再用 Python fetch 时 play.php 返回 404。

**根因**：Python `subprocess.run(['node', ...])` 启动 Node 要 ~2s，token 在那 2s 内可能就过期了。源站对每个 token 只在**短时间内**有效。

**修复**：改用纯 Node.js 脚本完成整个测试流程（getPlayphp + fetch 在同一进程内连续完成，几毫秒内完成）。

### 坑 9：Node.js 并发测试进程崩溃

**现象**：1692 条线路的并发测试脚本经常崩溃，只跑出几十条结果。

**根因**：
- `open files` 限制只有 1024，6 并发 + keep-alive 耗尽文件描述符
- 单进程内存泄漏（多个 worker thread 上下文）

**修复**：
- 降到 3 并发
- 加 checkpoint 文件（每 30 条保存一次，断点续跑）
- 自动重启脚本（进程死后从 checkpoint 恢复）
- `--max-old-space-size=128` 限制内存

### 坑 10：源站 play.php 间歇性 404

**现象**：同一个频道，有时 play.php 返回 302（成功），有时返回 404。

**根因**：源站负载均衡某些后端节点没有该频道，或者 token 验证不稳定。

**修复**：测试脚本重试 5 次，只有全部失败才判为不可播。实际成功率约 50-80%。

### 坑 11：`window.history.replaceState` 无法克隆 HLS 实例

**现象**：切换线路时 JS 报错 `Failed to execute 'replaceState' on 'History': function t(t){...} could not be cloned`。

**根因**：`replaceState(state, ...)` 的 state 对象包含了 hls.js 实例（不可序列化）。

**修复**：传一个纯对象 `{ cat, chIdx, lineIdx }` 而不是整个 state 对象。

### 坑 12：hls.js `canPlayType` 误判

**现象**：Playwright 的 Chromium 走了"原生 HLS"分支但实际播放不了（readyState=1, paused=true）。

**根因**：桌面 Chrome 的 `canPlayType('application/vnd.apple.mpegurl')` 返回 'maybe'，但实际不能播放 HLS。

**修复**：优先用 hls.js（`if (window.Hls && Hls.isSupported())`），不信任 `canPlayType`。

---

## 7. 文件清单与部署方法

### 文件清单

```
/home/z/my-project/
├── download/                          # 用户可下载的交付物
│   ├── iptv345-v1.0.js               # v1.0 初始版本
│   ├── iptv345-v1.5.js               # v1.5 三栏 UI + 频道合并
│   ├── iptv345-v1.6.js               # v1.6 性能优化
│   ├── iptv345-v1.7.js               # v1.7 不可播标记
│   ├── iptv345-v2.0.js               # v2.0 去敏感化
│   ├── iptv345-v2.1.js               # v2.1 导出过滤（完整版）
│   └── iptv345-2.1-blind.js          # blind 版（当前线上）
├── scripts/                           # 构建与测试脚本
│   ├── worker_template.js            # Worker 模板（含占位符）
│   ├── build_worker.py               # 构建脚本（嵌入 catalog + bad_lines）
│   ├── deploy_worker.py              # 部署脚本（Cloudflare API）
│   ├── reclassify_catalog.py         # 频道重分类 + 合并 + 清洗
│   ├── classify_lines.js             # 源站可播性测试
│   ├── scrape_catalog.py             # 抓取源站频道列表
│   └── ...                           # 各种测试脚本
├── work/                              # 工作文件
│   ├── catalog.json                  # 原始频道列表（10 个源）
│   ├── catalog_v2.json               # 重分类+清洗后的 catalog（5 个分类）
│   ├── bad_lines.json                # 808 条不可播线路
│   ├── default_names.json            # 1692 条默认名称映射
│   └── worker.js                     # 当前构建的 Worker（= blind 版）
└── worklog.md                         # 工作日志
```

### 部署方法

#### 前提
- Cloudflare API Token: `cfat_neyR5qerEFYKtkpKZ0zuL6r0TVyDXH5YrOfLAOMI26d2f730`
- 账户 ID: `ec44dddde866c789a9dd26f5d0cdb248`
- Worker 名: `iptv345`
- 子域名: `lishuhang.workers.dev`

#### 部署完整版

```bash
cp /home/z/my-project/download/iptv345-v2.1.js /home/z/my-project/work/worker.js
cd /home/z/my-project && python3 scripts/deploy_worker.py
```

#### 部署 blind 版

```bash
cp /home/z/my-project/download/iptv345-2.1-blind.js /home/z/my-project/work/worker.js
cd /home/z/my-project && python3 scripts/deploy_worker.py
```

#### 重新生成 catalog（如源站频道有变化）

```bash
cd /home/z/my-project
python3 scripts/scrape_catalog.py          # 1. 抓取源站频道列表
python3 scripts/reclassify_catalog.py      # 2. 重分类 + 合并 + 清洗
node scripts/classify_lines.js             # 3. 测试可播性（~15 分钟）
python3 scripts/build_worker.py            # 4. 构建 Worker
python3 scripts/deploy_worker.py           # 5. 部署
```

---

## 8. 已知限制与未来方向

### 已知限制

1. **fjitv/hlitv 全部不可播**：这些源重定向到 HTTP 裸 IP，Workers 不可达。共 808 条线路不可播。
2. **段 URL 1 秒过期**：源站段 URL 有效期极短，必须实时解析 session URL 从同 host 拉段。
3. **源站间歇性 404**：play.php 对同一频道有时返回 302 有时 404（负载均衡问题），Worker 有重试机制但偶尔仍会失败。
4. **Cloudflare Workers 内存缓存隔离**：不同 Worker 实例不共享内存缓存（playPhpUrlCache / sessionUrlCache），可能导致每次请求都重新解析。Cloudflare Cache API（段缓存）是全局共享的。
5. **blind 版无前端**：如需使用频道目录/搜索/线路切换功能，需切换到完整版。

### 未来方向

1. **D1 数据库**：将 catalog 和 bad_lines 存入 Cloudflare D1，避免嵌入 Worker 代码（当前 150KB）
2. **定时健康检查**：用 Cron Triggers 定期测试源站可播性，自动更新 bad_lines
3. **自定义域名**：绑定自定义域名（如 `iptv.example.com`），URL 不写死所以无需改代码
4. **多源站支持**：如果源站更换域名或算法，只需修改 `ORIGIN` 常量和解密逻辑
5. **WebSocket 实时状态**：用 Durable Objects 维护实时播放状态，多用户共享 session URL 缓存

---

## 附录：关键数据

| 指标 | 数值 |
|------|------|
| 原始频道数 | 1726 |
| 合并后唯一频道数 | 1051 |
| 总线路数 | 1692 |
| 不可播线路数 | 808 |
| 可播线路数 | 884 |
| 分类数 | 5（央视/卫视/港澳台/地方/轮播） |
| Worker 代码大小（完整版） | 150 KB |
| Worker 代码大小（blind 版） | 127 KB |
| 长播放测试 | 3 分钟 0 失败（v1.6） |
| 段缓存 TTL | 10 分钟 |
| session URL TTL | 60 秒 |
| play.php URL TTL | 90 秒 |

---

*文档结束*

---
*AI生成*
