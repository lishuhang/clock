# EarthTV 与 Live News Chat 外部机制发现

**采集时间：** 2026-08-15（GMT+8）

## EarthTV

EarthTV 官网入口为 `https://earthtv.com/`，其英文摄像头页会在公开 HTML 的 `<etv-player>` 元素中嵌入一个 `token` 属性。官方播放器脚本的公开配置接口为：

```text
https://livecloud.earthtv.com/api/v1/media.getPlayerConfig?playerToken=<player-token>
```

播放器以同一 `playerToken` 定期重取配置；脚本中未发现根据固定媒体标识自行签发新 token 的公开客户端接口。用户提供的 HLS 主清单会把 token 继续传递到子清单；去除 token 时未能取得可用清单。

已从 `https://www.earthtv.com/en/sitemap.xml` 枚举 279 个官方 `/webcam/` 页面，仅检测目标媒体标识 `HicYJzEAB5E` 是否出现，结果为 **0 个匹配**。因此当前没有找到可由 Worker 在每次请求时抓取最新 token 的目标固定官方页面，未为 EarthTV 部署路由。

## Live News Chat

官网：`https://livenewschat.eu/`。其 hls.js 驱动的直播页加载公开目录脚本：

```text
https://data.lncoperations.ee/server.json
```

该脚本返回 `serverReady({"totalConns":…,"best":"<host>.lncoperations.ee"});`，其中 `best` 是当前可用 CDN 节点。播放器页面以以下固定结构请求直播：

```text
https://<best-host>/hls/<stream-code>/index.m3u8
```

访问媒体资源时需要以下公开浏览器上下文请求头：

```text
Origin: https://livenewschat.eu
Referer: https://livenewschat.eu/
```

根 Referer 已验证可覆盖以下 10 个流代号的清单与首个媒体分片，均返回 HTTP 200；因此 Worker 不必存储任何频道页面 slug 或 token：

| 数字路由 | 非展示流代号 |
|---:|---|
| `lnc1.m3u8` | `bloomberg_live` |
| `lnc2.m3u8` | `cnbc_live` |
| `lnc3.m3u8` | `cnni_live` |
| `lnc4.m3u8` | `cnnus_live` |
| `lnc5.m3u8` | `dw_live` |
| `lnc6.m3u8` | `fstv_live` |
| `lnc7.m3u8` | `global_hd` |
| `lnc8.m3u8` | `msnbcintl_live` |
| `lnc9.m3u8` | `nbcnewsnow_live` |
| `lnc10.m3u8` | `skynews_live` |

已遍历 59 个规范直播页面；其中可发现并在清单、首个媒体分片、AES 密钥都验证成功的唯一有效流代号为上表 10 个。若页面使用 YouTube 嵌入或返回不存在的 LNC 流代号，则未纳入。

所有探测均为 HLS 传输层验证，不能保证地域、授权或播放器解码体验。本文不记录任何动态媒体 URL 查询参数、token 或用户本地路径。
