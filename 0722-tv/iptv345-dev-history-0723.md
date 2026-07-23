# iptv345 开发历史与经验教训 (增量 0723)

> **文档生成日期**: 2026-07-23 (HKT) — 增量更新
> **覆盖范围**: v2.9 → v2.10 (卫视官网 wso- 源接入 + 固定直链源调研)
> **前序文档**: `iptv345-dev-history-0722.md` (v1.0→v2.12) + `iptv345-dev-history-0723.md` 第一版 (v1.0→v2.8)
> **本文档不重复 0722.md 已有内容，仅记录 0723 后续工作。**

---

## 9. v2.9: wso- (卫视官网) 源接入

### 9.1 背景

v2.8 之前只有 3 类源：345 (m.345iptv.com 中转)、ysp (央视频)、xuexi (学习强国)。用户要求接入省级卫视官网直播源，统一前缀 `wso-`（类似 ysp-/xuexi-）。

### 9.2 调研结论

对 40 个省级卫视官网直播流做系统调研，发现：

1. **绝大多数卫视官网直播流是动态的**（需 token/签名/加密）
2. **少数"半固定"源**：调用无签名 API 即可拿到 m3u8（但 m3u8 本身可能带时效参数）
3. **极少数"固定直链"**：URL 不变，可直接播放

### 9.3 v2.9 新增 wso- 源（3 个）

| wso Key | 卫视 | API | 解析方式 | 状态 |
|---|---|---|---|---|
| `wso-hainan` | 海南卫视 | `http://ps.hnntv.cn/ps/livePlayUrl?...&channelCode=STHaiNan_channel_lywsgq` | `d.resultSet[0].url` | ✅ 稳定 |
| `wso-dongnan` | 东南卫视 | `https://live.fjtv.net/m2o/channel/channel_info.php?channel_id=5` | `arr[0].m3u8` | ⚠️ CF 不可达（地域限制） |
| `wso-shaanxi` | 陕西卫视 | `http://qidian.sxtvs.com/sxtoutiao/getLiveTvV11?...` | `data[id=1131].onlineUrlForandroid` | ✅ 偶尔可用 |

### 9.4 实现细节

**WSO_CATALOG 结构**:
```js
const WSO_CATALOG = {
  'wso-hainan': {
    name: '海南卫视',
    api: 'http://ps.hnntv.cn/...',
    referer: 'https://www.hnntv.cn/',
    parseM3u8: (text) => { /* 从 API 响应提取 m3u8 URL */ }
  },
  // ...
};
```

**WSO_CACHE**: 5 分钟 TTL（m3u8 有 `_upt` 时效参数）

**路由**:
- `GET /wso-<name>.m3u8` → 调 API 获取 m3u8 → 代理 m3u8（改写段 URL 为 `/wseg/`）
- `GET /wseg/<wsoKey>/<encodedUrl>` → 段代理（带正确 Referer）

**段 URL 改写**: 段 URL 可能是相对路径或绝对 URL，统一 URL-encode 后通过 `/wseg/` 代理，确保带正确 Referer。

### 9.5 踩坑

1. **wso-dongnan 从 CF 不可达**：`live.fjtv.net` API 在本地可访问，但从 Cloudflare Worker 调用返回空响应。可能是地域限制或 CF IP 被屏蔽。
2. **parseM3u8 解析失败**：海南卫视 API 返回 `{"resultSet":[{"url":"..."}]}`，最初 parser 找 `d.url` 失败 → 修复为 `d.resultSet[0].url`。
3. **403 循环**：m3u8 过期后，`resolveWsoM3u8` 返回缓存的旧 URL → fetch 403 → 删除缓存 → 下次请求又返回同一 URL（API CDN 缓存）→ 死循环。v2.10 修复为同一次请求内强制重新 resolve。

---

## 10. v2.10: wso-guizhou + 固定源调研

### 10.1 新增 wso-guizhou

贵州卫视 API: `https://api.gzstv.com/v1/tv/ch01` → `d.stream_url`（含 `txSecret` 动态 token）

**问题**: API 返回的 m3u8 有 `txSecret`/`txTime` 参数，有效期短。403 后需重新调 API。v2.10 修复了 403 重试逻辑（同一次请求内重新 resolve）。

### 10.2 wso-jiangsu 失败

江苏卫视 `zjcn-live-play.jstv.com` 固定 URL，但需 Referer `https://api.chinaaudiovisual.cn/`。

**问题**: 即使带 Referer，从 Cloudflare Worker 调用仍返回 403。jstv.com 可能屏蔽 CF IP 段。

**结论**: 移除 wso-jiangsu，改用固定直链 `http://112.27.235.94:8000/hls/32/index.m3u8`（IPTV 组播转单播，无需 Referer）。

### 10.3 固定直链源调研（38 个）

系统测试了来自 `vbskycn/iptv`、`suxuang/myIPTV` 等 GitHub IPTV 聚合仓库的源，找到 **38 个可用固定直链**（200 + `#EXTM3U`，无需 token/referer）：

| 地区 | 卫视（固定直链可用） |
|---|---|
| 华北 | 北京、天津、河北、山西、内蒙古 |
| 东北 | 辽宁、吉林、黑龙江 |
| 华东 | 东方、江苏、浙江、安徽、山东、山东教育 |
| 华南 | 广东、广西、海南、深圳、厦门、三沙、大湾区、海峡 |
| 华中 | 河南、湖北、湖南 |
| 西南 | 重庆、四川、贵州、云南、西藏 |
| 西北 | 陕西、甘肃、青海、宁夏、新疆、兵团 |
| 其他 | 延边、安多、农林 |

**源类型**: 大部分是运营商 IPTV 组播转单播（`tsfile/live/` 或 `hls/N/` 格式），IP 地址如 `222.169.85.8:9901`、`112.27.235.94:8000` 等。

**注意**: 这些源**仅在中国大陆网络环境稳定**；海外/CF 访问可能不可达。但 tv-app 在用户浏览器播放，用户在中国大陆即可。

### 10.4 403 重试逻辑修复

**v2.9 问题**: m3u8 过期 (403) 后，`fetchAndRewriteWsoM3u8` 删除缓存并返回 502，但下次请求 `resolveWsoM3u8` 又从 API 拿到同一过期 URL（API CDN 缓存）→ 死循环。

**v2.10 修复**: 在 `fetchAndRewriteWsoM3u8` 的 403 分支中，**同一次请求内**重新调用 `resolveWsoM3u8`（强制刷新缓存）并重新 fetch。如果新 URL 与旧 URL 不同且 fetch 成功，继续处理；否则返回 502。

```js
if (resp.status === 403) {
  wsoCache.delete(wsoKey);
  const freshUrl = await resolveWsoM3u8(wsoKey);
  if (freshUrl && freshUrl !== m3u8Url) {
    const retryResp = await fetch(freshUrl, {...});
    if (retryResp.ok) { m3u8Url = freshUrl; resp = retryResp; }
  }
}
```

### 10.5 `direct:` 前缀支持

为支持"固定 URL"类型的 wso 源（如 wso-jiangsu），添加 `direct:` 前缀：
- `api: 'direct:https://example.com/live.m3u8'` → 不调用 API，直接返回 URL
- 适用于 URL 固定但需特定 Referer 的源

---

## 11. tv_list 版本演进

| 版本 | 内容 | 频道数 | URL 数 |
|---|---|---|---|
| tv_list.txt | 原始列表 | 73 | 108 |
| tv_list-v2.txt | 按 5 地区分类 | 73 | 108 |
| tv_list-v3.txt | v2 + ysp + xuexi | 123 | 194 |
| tv_list-v4.txt | v3 + 52 固定源 | 131 | 246 |
| tv_list-v5.txt | v4 + 3 wso- 源 | 131 | 249 |
| **tv_list-v6.txt** | v5 + 38 官网固定源 | 131 | 257 |

**v6 亮点**: 每个卫视有 3-5 个备选源（345 + ysp + xuexi + 固定直链 + wso），tv-app 自动 failover。

---

## 12. GitHub Actions 修复（2026-07-23）

### 12.1 问题

`lishuhang/345` repo 的 workflow 持续失败（12+ 次），GitHub 通知 "Refresh and Deploy workflow run failed"。

**根因**: `deploy_worker.py` 硬编码本地路径 `/home/z/my-project/.secrets`，在 GitHub Actions 环境不存在。

**345 token never used**: 因为 workflow 一直失败，CF API token 从未被调用。

### 12.2 修复

`deploy_worker.py` 改为优先从环境变量读取（`CF_API_TOKEN`、`ACCOUNT_ID`），本地 `.secrets` 作为 fallback：

```python
CF_API_TOKEN = os.environ.get('CF_API_TOKEN', '')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID', '')
if not CF_API_TOKEN or not ACCOUNT_ID:
    # Fall back to .secrets file for local development
    ...
```

### 12.3 xuexi URL 过期问题

**发现**: xuexi `auth_key` 格式为 `auth_key=<start_time>-0-<random>-<hash>`，`start_time` 是**20 分钟前**的时间戳。URL 有效期从 `start_time` 算约 30 分钟，即**生成后仅剩 10 分钟有效**。

**问题**: workflow 每 15 分钟跑一次，xuexi URL 在 build 时已 4 分钟旧，部署后 6 分钟过期 → 下次 workflow 还有 5 分钟空窗。

**修复**: 
1. workflow 间隔从 15 分钟改为 **10 分钟**
2. 添加 **dual xuexi refresh**：build 前再刷一次 xuexi URL，确保最新

```yaml
- name: Refresh xuexi URLs (first pass)
  run: rm -f work/xuexi_checkpoint.json && timeout 300 node scripts/gen_xuexi_fast.js || true
- name: Refresh YSP URLs
  run: rm -f work/ysp_checkpoint.json && timeout 480 node scripts/gen_ysp_fast.js || true
- name: Refresh xuexi URLs (second pass, right before build)
  run: rm -f work/xuexi_checkpoint.json && timeout 180 node scripts/gen_xuexi_fast.js || true
```

---

## 13. 当前部署状态 (v2.10, 2026-07-23)

### 13.1 iptv345 worker

- **域名**: `345.lishuhang.com` (custom) + `iptv345.lishuhang.workers.dev`
- **版本**: v2.10-blind (含 345 + ysp + xuexi + wso)
- **状态页**: `v2.10 / status: 345 ok; ysp ok/error; xuexi ok; wso ok`
- **大小**: ~203 KB

### 13.2 路由总表

| 路由 | 说明 |
|---|---|
| `GET /` | 状态页 (v2.10 / status: 345 ok; ysp ok; xuexi ok; wso ok) |
| `GET /<tid><id>.m3u8` | 345 源 m3u8 代理 (如 `/gt5.m3u8`) |
| `GET /seg/<tid>/<id>/<file>` | 345 .ts 段代理 |
| `GET /ysp<...>.m3u8` | ysp m3u8 代理 (如 `/yspc01.m3u8`) |
| `GET /yseg/<yspKey>/<file>` | ysp .ts 段代理 |
| `GET /xuexi_<hash>.m3u8` | xuexi m3u8 代理 |
| `GET /xseg2/<host>/<path>` | xuexi .ts 段代理 |
| `GET /wso-<name>.m3u8` | **v2.9+** 卫视官网 m3u8 代理 |
| `GET /wseg/<wsoKey>/<encodedUrl>` | **v2.9+** 卫视官网 .ts 段代理 |
| `GET /cat/<tid>` | 345 文本列表 |
| `GET /refresh/<tid><id>` | 强制刷新 345 频道缓存 |
| `GET /health/<tid><id>` | 345 频道健康检查 |
| `GET /refresh-gha` | 触发 GitHub Actions 刷新 ysp/xuexi |

### 13.3 WSO 源状态

| wso Key | 卫视 | 状态 | 备注 |
|---|---|---|---|
| `wso-hainan` | 海南卫视 | ✅ 稳定 | API 返回 `_upt` 时效 URL |
| `wso-shaanxi` | 陕西卫视 | ✅ 偶尔可用 | 源站偶尔超时 |
| `wso-dongnan` | 东南卫视 | ⚠️ CF 不可达 | API 地域限制 |
| `wso-guizhou` | 贵州卫视 | ⚠️ 不稳定 | API 偶尔返回空 |

### 13.4 GitHub Actions

- **Repo**: `lishuhang/345` (main 分支)
- **频率**: 每 10 分钟
- **流程**: Playwright 刷 xuexi → Playwright 刷 ysp → 再刷 xuexi → build (v2.10 base + 新鲜 URL) → deploy → verify
- **Secrets**: `CF_API_TOKEN` (cfut_ 前缀) + `ACCOUNT_ID`
- **Worker secret**: `GH_TOKEN` (用于 `/refresh-gha` 触发 workflow)

### 13.5 tv-app 前端

- **域名**: `tv.lishuhang.com` (worker "tv")
- **版本**: v1.3 (4 项修复：导航栏自动隐藏、3轮换台、60s缓冲刷新、导出文件名带时间戳)
- **最新频道列表**: `tv_list-v6.txt` (131 频道, 257 URL)

---

## 14. 文件清单更新

### 14.1 lishuhang/clock main 分支 (0722-tv/)

```
0722-tv/
├── chat-history.txt                # 原始开发对话 (1771 行)
├── iptv345-dev-history-0722.md     # v1.0→v2.12 开发历史
├── iptv345-dev-history-0723.md     # v2.9→v2.10 增量 (本文档)
├── iptv345-v2.1.js                 # 历史完整版
├── iptv345-v2.7-blind.js           # 历史 blind 版
├── iptv345-v2.8.js / -blind.js     # v2.8 (broken cache + /health + /refresh)
├── iptv345-v2.9.js / -blind.js     # v2.9 (wso- 源接入)
├── iptv345-v2.10.js / -blind.js    # v2.10 (wso-guizhou + 403重试) ← 当前
├── iptv345-channel-list.txt        # 完整频道清单 (1778 URL)
├── v2.8-plan-0722-1946.md          # 外部配合方案
├── tv-app-v1.2.html / v1.3.html    # 前端
├── tv_list.txt → tv_list-v6.txt    # 频道列表演进 (6 个版本)
└── scripts/
    ├── deploy_worker.py            # CF Worker 部署脚本
    ├── build_tv_worker.py          # tv worker 构建脚本
    ├── tv_worker_template.js       # tv worker 模板
    └── build_v28_full.py           # v2.8 + ysp + xuexi 构建脚本
```

### 14.2 lishuhang/345 main 分支

```
├── .github/workflows/refresh.yml   # 自动刷新 workflow (每 10 分钟, dual xuexi refresh)
├── scripts/
│   ├── gen_ysp_fast.js             # Playwright 刷新 ysp URL
│   ├── gen_xuexi_fast.js           # Playwright 刷新 xuexi URL
│   ├── fetch_xuexi_urls.py         # xuexi 频道 ID 抓取
│   ├── build_v210_blind.py         # 构建 worker (v2.10 base + ysp + xuexi)
│   └── deploy_worker.py            # 部署脚本 (env vars 优先)
└── work/
    ├── worker_v26_blind.js         # 基础 worker (= v2.10-blind) ← 已更新
    ├── catalog_v2.json             # 345 频道目录
    ├── bad_lines.json              # 345 失效线路列表
    └── xuexi_m3u8_urls.json        # xuexi 频道 ID 映射
```

---

## 15. 新增踩坑记录 (4.17-4.19)

### 4.17 Cloudflare Worker 调用外部 API 受地域限制

**现象**: `live.fjtv.net` (东南卫视) API 在本地 curl 可访问，但从 Cloudflare Worker 调用返回空响应。

**原因**: 部分中国省级电视台 API 有地域限制，CF 边缘节点 IP（海外）被屏蔽。

**解决方案**: 无法绕过。改用其他源（固定直链或 345 中转）。

### 4.18 xuexi auth_key 时效机制

**现象**: gen_xuexi_fast.js 抓取的 URL 在抓取时就已经"20 分钟旧"。

**根因**: xuexi `auth_key` 的 `start_time` 是**20 分钟前**的时间戳，URL 有效期从 `start_time` 算约 30 分钟 → 生成后仅剩 10 分钟有效。

**解决**: 
1. workflow 间隔缩短到 10 分钟
2. build 前再刷一次 xuexi（dual refresh）
3. 确保部署后 URL 还有 ~8 分钟有效期，覆盖到下次 workflow

### 4.19 wso 403 死循环

**现象**: wso 源 m3u8 过期 (403) 后，删除缓存 → 下次请求 `resolveWsoM3u8` 又从 API 拿到同一过期 URL（API CDN 缓存）→ 403 → 死循环。

**解决**: 在 `fetchAndRewriteWsoM3u8` 的 403 分支中，**同一次请求内**重新 resolve + fetch。如果 API 返回新 URL 则重试，否则返回 502。

---

## 16. 后续方向 (更新)

1. **ysp 浏览器播放**: 集成 `hls.cmg.js + keygen_bg.wasm` 解密 (大工程)
2. **更多 wso- 源**: 调研报告中有更多卫视 API（江苏/贵州/山西/青海/西藏等），但多数需要复杂签名或从 CF 不可达
3. **固定直链源稳定性**: 38 个固定源来自运营商 IPTV，IP 可能变化，需定期重新测试
4. **wso-guizhou 稳定性**: API 偶尔返回空，需增加重试或 fallback 到固定直链
5. **前端 v1.4+**: 频道收藏、快捷键换台、EPG 节目单
6. **tv_list-v7+**: 用户自定义频道补充

---

*本文档由 Super Z (基于 GLM 模型，由 Z.ai 构建) 于 2026-07-23 增量整理。前序内容见 `iptv345-dev-history-0722.md` 和 `iptv345-dev-history-0723.md` 第一版。*
