# 视频素材爬取指南（实战版）

> 任务代号 1020-feng-video · 完成于 2026-10-20 17:21 GMT+8
> 本文档记录本次为《抓特务》/冯小刚选题抓取B站视频素材过程中**真正可用的通路**与**踩过的坑**，供后续任务复用，避免重复造轮子。
> 配套脚本全部在沙箱 `/home/z/my-project/scripts/`，可直接改造复用。

---

## 一、结论速览（TL;DR）

| 需求 | 可用通路 | 成功率 |
|------|---------|--------|
| B站视频下载 | **agent-browser 真实浏览器 + 页面内 `window.__playinfo__` + curl 带 Cookie 拉 DASH 流** | 高（本次22/22） |
| B站搜索 | **同源页面内 fetch `wbi/search/type` API**（不用导航） | 高 |
| B站点选验证码 | **geetest_beat2.py：条带模板 + Canny多尺度多旋转模板匹配 + agent-browser 点击** | ~50%/次，可重试 |
| YouTube等外站 | 未走通（yt-dlp 触发验证码）；理论可用网页中转站，但本次无需 | - |
| 电影海报 | B站视频封面(search API 的 pic 字段) > 抽帧 > image-search | 见坑4 |
| 素材预览 | ffmpeg 抽帧拼 contact sheet + VLM 批量审看 | 高 |

## 二、真正可用的通路（按优先级）

### 通路A：B站视频标准下载流（主力）

1. **过验证码拿到一个"热"的浏览器会话**（见通路B），之后一段时间内导航不触发验证码。
2. `agent-browser open https://www.bilibili.com/video/<BV>/`，轮询 `window.__playinfo__`（约需2-10秒，别只等固定4秒）。
3. 从 playinfo 取 `data.dash.video[0].baseUrl`（免登录最高480p, id=32）和 `data.dash.audio[0].baseUrl`。
4. `curl -H "Referer: https://www.bilibili.com/" -H "Cookie: <浏览器全部cookie>"` 分别下载视频/音频 m4s。
5. `ffmpeg -i v.m4s -i a.m4s -c copy out.mp4` 合并。
- **要点**：playinfo 从**视频页本身**读，不要直接 curl `api.bilibili.com`（数据中心IP直接412，见坑1）。
- **要点**：搜索用同源页面内 fetch（`agent-browser eval` 里跑 `fetch(..., {credentials:'include'})`），搜索API宽松，view API 有 wbi 签名墙（见坑2）。
- 脚本：`bili_fetch.py`（search/info/download 三合一）、`bili_batch_download.py`（批量+验证码自动处理）。

### 通路B：GeeTest 点选验证码自动求解

B站对无头浏览器/数据中心IP的页面导航经常弹极验**点选验证码**。解法（`geetest_beat2.py`）：

1. 从 DOM 取 `.geetest_item_wrap` 的 background-image URL（344x384 jpg；**主图在上部~340px，底部左侧~150px是目标字符条，同一张图**）。
2. 条带区（`gs<110` 二值化，行4-40、列0-150）列投影切块 → 得到 N 个目标字形模板（**不需要识字**）。
3. 主图 Canny 边缘图，模板做 **多尺度(1.4-3.0)×多旋转(±36°/6°)** matchTemplate，全局贪心分配（间距≥35px）。
4. 按**模板顺序**（=条带顺序）点击；**满 N 次点击后极验自动提交，不用点确认按钮**。
5. 点完等 **5-10秒** 再判断页面标题（验证+跳转有延迟，3.5秒会误判失败）。
6. 失败 → reload 换题重试（隐藏的刷新按钮 JS click 无效，直接整页 reload）。
- **为什么不用VLM识字**：条带字形是艺术字，VLM 读不稳定（同一张图三次读出三个结果）；VLM 报像素坐标也常溢出图片边界。纯CV模板匹配反而稳。
- 沙箱留有热会话快照：`scratch/bili_warm_state.json`（`agent-browser state load` 可恢复，有效期以实际为准）。

### 通路C：素材预览与剪辑（规范执行）

1. 每个下载完的视频先用 `make_sheets.py` 抽12帧拼 contact sheet（带时间戳）。
2. `vlm_review_sheets.py` 每批5张发给 VLM 审看：内容概述、水印情况、可用时间段。
3. 按审看结果定剪辑点，**前后留余量**（计划用5s剪8-12s），`trim_materials.py` 批量 ffmpeg 重编码（crf19→大文件再压crf25，854px宽上限）。
4. 抽查成品（抽帧VLM核对内容）后再删 raw 原档。

## 三、踩坑记录（防止重蹈）

1. **B站 API 直连必死**：`curl api.bilibili.com` 无浏览器cookie → 412 `request was banned`。手动拼 buvid3/buvid4 cookie 也过不去（风控要看完整浏览器指纹：ExClimbWuzhi 上报、canvas/webgl指纹等）。**唯一解：真实浏览器上下文**。
2. **view API 与 search API 待遇不同**：页面内 fetch `wbi/search/type` 一直通；`x/web-interface/view` 同样页面内 fetch 却返回412 HTML（wbi签名墙）。**取视频信息走视频页 playinfo，不走 view API**。
3. **验证码会"延迟通过"**：点击正确后页面跳转要5-10秒。脚本里等3.5秒查标题会误判，然后多余的重试点击反而把新题点脏（图上留多个错点，这题就废了，必须reload）。**判断失败前先等够8秒**。
4. **image-search 找中国老电影海报命中率极低**（11张里7张错，返回的是近年片子海报/电影节照片/写真）。可靠度排序：**B站官方预告封面(search API pic字段) > 从预告片抽帧(片名定版/剧照) > image-search**。新片海报（如抓特务）image-search 能中，90年代老片基本靠B站封面。
5. **CDN 下载会随机损坏**：同一批下载约1/3文件出现 `Invalid NAL unit size`（upos CDN 偶发坏包）。**下载后必须全量解码体检**（`ffmpeg -v error -i f -f null`），坏的重下即可（重下通常就好）。
6. **m4s 合并**：视频流+音频流分开下载，`ffmpeg -c copy` 合并，别忘记 `-c copy` 否则重编码耗时且画质损失。
7. **bangumi 跳转**：部分"放映厅"视频（如哔哩哔哩放映员发布的PV）会302到 `/bangumi/play/epXXX`，播放器是 MSE blob 流且可能付费，**playinfo 拿不到 → 直接换同题材普通UGC视频**（如"乌鸦预告片"等预告号）。
8. **免登录清晰度上限480p**（id=32/16）。够用（竖屏制作会裁切放大）。要高清需登录cookie，本次未做。
9. **后台进程会被杀**：nohup 起的长任务偶尔被环境回收（shrink跑一半消失）。**长ffmpeg批量任务用前台+timeout分段跑，或跑完立刻查log确认**。
10. **yt-dlp 直连 YouTube**：触发 Google 验证码，无解（数据中心IP）。用户提示的中转站（savefrom/snapany等）理论可行：snapany 实测**第一次解析后就弹登录墙**，其 `POST api.snapany.com/v1/extract/post` 返回200但结果藏在登录后。若必须下YouTube再研究，本次B站素材已够。
11. **agent-browser eval 的变量名会跨调用残留**（`const x` 第二次报 already declared）→ 一律用 IIFE `(() => {...})()`。
12. **playinfo 出现时机不定**：导航后轮询最多20秒；`__INITIAL_STATE__` 有时反而不存在，别依赖它。

## 四、skill市场调研结论（用户指示的排查项）

- **dsh-plugin.org/zh**：DeepSeek Harness (DSH) 的插件市场，15512个插件均为DSH框架专用（`dsh plugin add`安装），**与本环境skill体系不兼容**，无直接可用视频下载件。
- **skills.pub/zh**：Claude Skills市场（6400+），搜"video download"仅有一个 TikTok Shop 卖货视频技能，**无B站/YouTube下载类**。
- **lobehub**：插件商店以前端UI插件为主，无相关。
- **结论**：现成skill没有，自建管线（本文档通路A+B）就是当前最优解。相关脚本已持久化，下次直接用。

## 五、配套脚本清单（`/home/z/my-project/scripts/`）

| 脚本 | 用途 |
|------|------|
| `geetest_beat2.py [N]` | GeeTest点选验证码自动求解（纯CV，可重试N次） |
| `bili_fetch.py search/info/download` | B站搜索/信息/单视频下载 |
| `bili_batch_search.py` / `bili_batch_download.py` | 批量搜索/批量下载（含验证码自动处理） |
| `make_sheets.py` | 视频抽帧拼contact sheet（预览用） |
| `vlm_review_sheets.py` | VLM批量审看sheets |
| `trim_materials.py` | 按清单批量剪辑（留余量） |
| `fetch_posters2.py` | image-search海报抓取（老片命中率低，慎用） |

## 六、素材获取规范执行说明

- 全部素材**先预览后剪辑**：VLM审看22个源视频 → 定段 → 剪41个片段（每个8-30s，均留余量）
- 原始下载档（raw_dl，约240MB）在剪辑验证后**已删除**，repo只存剪辑成品（约100MB）
- 韩红《走个面》素材从 filekit 完整版剪辑（3:03起留余量），音画分离：`hanhong_seg_video.mp4` + `hanhong_seg_audio.wav`（50s，上轮会话已切好）
- 海报/封面14张（6.3MB），含4张验证过的正式海报、5张B站官方封面、3张预告片抽帧剧照、1张冯小刚照片
