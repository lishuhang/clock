---
AIGC: {"Label":"1","ContentProducer":"001191110108MA01KP2T5U00000","ProduceID":"ce55ae5455be59a2fd278203ef5af570","ReservedCode1":"","ContentPropagator":"001191110108MA01KP2T5U00000","PropagateID":"ce55ae5455be59a2fd278203ef5af570","ReservedCode2":""}
---

# iptv345 v2.5 更新文档（2026-06-21）

> 本文档仅包含 v2.1 → v2.5 的新增内容，不包含之前版本的文档。

---

## 新增功能：央视频（YSP）源代理

### 概述

v2.5 新增了对央视频（yangshipin.cn）直播源的中转支持。用户可通过固定地址 `https://iptv345.lishuhang.workers.dev/yspc01.m3u8` 播放 CCTV1，`/yspw03.m3u8` 播放东方卫视等。

### 命名规则

```
/ysp<type><idx>.m3u8
```

- `ysp` = 央视频源
- `<type>` = `c`（CCTV tab）或 `w`（卫视 tab）
- `<idx>` = 在对应 tab 中的排序序号（01 开始）

示例：
| URL | 频道 |
|-----|------|
| `/yspc01.m3u8` | CCTV1 |
| `/yspc02.m3u8` | CCTV2 |
| `/yspc07.m3u8` | CCTV6 |
| `/yspw01.m3u8` | 北京卫视 |
| `/yspw03.m3u8` | 东方卫视 |
| `/yspw31.m3u8` | 新疆卫视 |

### 频道覆盖

共 45/48 个频道成功捕获（3 个因页面加载超时未捕获）：

**CCTV（15/17）：** CCTV1-4, CCTV6-17（缺 CCTV5, CCTV5+）
**卫视（30/31）：** 北京/江苏/东方/浙江/湖南/湖北/广东/广西/黑龙江/海南/重庆/深圳/四川/河南/福建东南/贵州/江西/辽宁/安徽/河北/山东/天津/吉林/陕西/宁夏/内蒙古/云南/青海/西藏/新疆卫视（缺山西卫视）

### YSP 源站机制

央视频的播放流程比 345 源站简单：

```
1. POST player-api.yangshipin.cn/v1/player/auth
   → 返回 {token, ts}
   → 需要 signature（MD5 签名，已逆向出算法和密钥）

2. POST player-api.yangshipin.cn/v1/player/get_live_info
   → 返回 {playurl, extended_param}
   → 需要 cKey（WASM 生成的加密参数）+ SDK headers
   → 这一步无法在 Worker 中复现（需要浏览器 WASM）

3. GET playurl + extended_param
   → 返回 m3u8（HTTPS CDN，无需 Referer）
   → .ts 段也无需 Referer，直接可访问
```

**关键发现：**
- m3u8 和 .ts 段**无需 Referer**，可直接 fetch
- m3u8 URL 有效期较长（至少数小时）
- 段 URL 是相对路径，自动解析到同目录
- 不同频道可能用不同 CDN host（`outlivecloud-cdn.ysp.cctv.cn` / `mobilelive-play-1.ysp.cctv.cn`）

### 实现方式

由于 `get_live_info` API 需要 WASM 生成的 cKey（无法在 Worker 中复现），采用 **Playwright 代理方案**：

1. 用 Playwright 脚本（`scripts/gen_ysp_urls3.js`）在浏览器中打开 yangshipin.cn
2. 逐个频道导航（`?pid=XXXX`），从 `get_live_info` 响应中捕获 m3u8 URL
3. 将 45 个 m3u8 URL 嵌入 Worker 代码
4. Worker 直接 fetch 嵌入的 m3u8 URL，重写段 URL 为 `/yseg/<key>/<filename>`
5. 段代理直接从 YSP CDN 拉取（无需 Referer）

### 已逆向的签名算法

**Auth API 签名（已验证正确）：**
```
密钥: Ac = "n@7QKk%YeSjfw%22"
算法: 
  1. 取所有参数（除 signature）
  2. 按 key 排序
  3. 拼接为 key=value&key=value
  4. 追加密钥 Ac
  5. MD5
```

**get_live_info 签名（未完全验证）：**
```
密钥: du = "0f$IVHi9Qno?G"
算法: 同上，但需要 cKey（WASM 生成）
```

### 路由新增

| 路由 | 功能 |
|------|------|
| `GET /ysp<type><idx>.m3u8` | YSP m3u8 代理 |
| `GET /yseg/<yspKey>/<filename>` | YSP .ts 段代理 |

### 首页状态检测

blind 版首页现在显示双状态：
```
status: 345 ok; ysp ok
```

如果其中之一出错：
```
status: 345 ok; ysp error

[timestamp] === Health check start ===
[timestamp] --- 345 check ---
[timestamp] OK 345 catalog: 5 categories, 1051 items
[timestamp] Testing 345 m3u8 for gt5...
[timestamp] OK 345 m3u8 fetched
[timestamp] --- ysp check ---
[timestamp] FAIL ysp m3u8: status=403 (URL may have expired)
[timestamp] === Health check done (5380ms) ===
```

### YSP URL 过期问题

嵌入的 m3u8 URL 包含 `ysign` 和 `ytime` 参数，会过期。过期后 m3u8 返回 403。

**刷新方法：**
```bash
cd /home/z/my-project
node scripts/gen_ysp_urls3.js    # 重新生成（约 10-15 分钟）
python3 scripts/build_v25_blind.py  # 重新构建
python3 scripts/deploy_worker.py    # 重新部署
```

或手动：
```bash
cp download/iptv345-v2.5-blind.js work/worker.js
python3 scripts/deploy_worker.py
```

### 性能优化

YSP 源的 .ts 段较大（1.4-2.2MB，比 345 源的 0.8MB 大），且 YSP m3u8 的 `TARGETDURATION` 为 5-8 秒（比 345 的 2 秒长），所以：
- 段缓存 TTL 设为 10 分钟（段不可变）
- m3u8 不缓存（直播滑动窗口）
- hls.js 配置与 345 相同（`backBufferLength: 10`, `maxBufferLength: 20`）

### 测试结果

- m3u8 轮询：3 次连续获取，MEDIA-SEQUENCE 递增（1756947832→833→834）✓
- 段下载：1.8-1.9MB，首字节 0x47（MPEG-TS sync）✓
- 不同 CDN host 均可访问（outlivecloud-cdn / mobilelive-play）✓
- 345 源不受影响（gt5.m3u8 正常）✓
- 首页双状态正常显示 ✓

### 缺失频道

| 频道 | 原因 |
|------|------|
| CCTV5 (yspc05) | 页面加载超时 |
| CCTV5+ (yspc06) | 页面加载超时 |
| 山西卫视 (yspw28) | 页面加载超时 |

可重跑 `gen_ysp_urls3.js` 尝试捕获（有 checkpoint 机制，会跳过已捕获的频道）。

---

## 文件清单

| 文件 | 说明 |
|------|------|
| `download/iptv345-v2.5-blind.js` | v2.5 blind 版 Worker（当前线上） |
| `download/list-ysp.txt` | 仅 YSP 源的播放列表（45 条） |
| `download/iptv345-readme-260621.md` | 本文档 |
| `scripts/gen_ysp_urls3.js` | YSP m3u8 URL 生成脚本（Playwright） |
| `scripts/probe_ysp*.js` | YSP 探测脚本 |
| `work/ysp_m3u8_urls.json` | 生成的 YSP m3u8 URL 数据 |
| `work/default_names.json` | 默认名称映射 |

---

## Agent Debug 踩坑说明（v2.5 新增）

### 坑 13：YSP API 需要 WASM 生成的 cKey

**现象**：Auth API 签名已正确逆向，但 get_live_info API 始终返回 401。

**根因**：get_live_info 需要 `cKey` 参数（由 `RJq7sO71JF.wasm` 生成），以及 SDK headers（`yspsdkinput`, `yspsdksign`）。这些无法在 Worker 中复现。

**修复**：改用 Playwright 代理方案——在浏览器中调用 API，捕获 m3u8 URL，嵌入 Worker。

### 坑 14：YSP m3u8 URL 的 HASH 路径每次不同

**现象**：同一频道两次获取的 m3u8 URL 的路径 HASH 不同。

**根因**：`get_live_info` 每次返回不同的 CDN 路径（可能是负载均衡或防链机制）。

**影响**：无法构造固定的 m3u8 URL，必须通过 API 获取。但 URL 获取后有效期较长（数小时）。

### 坑 15：Playwright 逐频道导航超时

**现象**：部分频道（CCTV5, CCTV5+, 山西卫视）在 `page.goto('?pid=XXXX')` 后未触发 `get_live_info` 请求。

**根因**：页面加载超时或频道切换失败。

**修复**：添加 checkpoint 机制，跳过已捕获的频道，支持断点续跑。3 个频道缺失不影响主要功能。

### 坑 16：Worker 路由优先级

**现象**：`/yspc01.m3u8` 被 345 的 `/<tid><id>.m3u8` 路由匹配，导致 `yspc` 被当作 tid。

**根因**：YSP 路由没有在 345 m3u8 路由之前检查。

**修复**：在路由表中将 YSP m3u8 和 YSP 段路由放在 345 m3u8 路由之前。

---

*文档结束*

---
*AI生成*
