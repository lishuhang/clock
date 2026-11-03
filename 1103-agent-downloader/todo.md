# todo — 实抓轮 (2026-11-03) 完成状态

> 规则: 每平台失败最多换法重试 1 次; 未探索路径只记录。**实抓轮已完成, 5/7 平台成功。**

## Phase 0 — 准备 ✅
- [x] T0.1 Threads 插件安装验证 (`Extractor Plugins: ThreadsIE` ✓)
- [x] T0.2 密钥目录 (token 走 /home/z/my-project/scripts/.ghtoken, 未入库)
- [x] T0.3 测试目标选定 (B站热门API/微博搜索引擎转引/X Lemmy留档/抖音示例短链/Threads主页SSR抽code/小红书用户链接/YouTube ytsearch)
- [x] T0.4 通用脚本 lib_media.py + 每平台 dl_*.py

## Phase 1 — 实抓
- [x] T1.1 微博 ✅ 540x960 4.1MB (方案A/B发现失败 → 搜索引擎转引URL + yt-dlp游客)
- [x] T1.2 B站 ✅ 1280x536 29.2MB (html5 playurl 免登录720p档, 修正调研结论)
- [x] T1.3 YouTube ❌ 两 client 组合均 bot-check (未探索: bgutil POT / burner cookies)
- [x] T1.4 X ✅ 1920x1080 4.3MB (SpaceX 官方, 游客免cookie)
- [x] T1.5 Threads ✅ 720x1280 11.9MB (主页Googlebot SSR抽code → 插件下载, 原创发现)
- [x] T1.6 小红书 ✅ 720x1364 7.2MB (用户 xsec_token 链接 + yt-dlp 匿名档)
- [x] T1.7 Instagram — 用户豁免
- [x] T1.8 抖音 ❌ SSR 已收壳 + yt-dlp 要 cookies (未探索: ttwid注入/TikTokDownloader/playwright)

## Phase 2 — 汇总交付
- [x] T2.1 REPORT.md (自动生成 §1/§2 + 手写 §3-§6)
- [x] T2.2 ffprobe 体检 5/5 通过 (W021)
- [x] T2.3 失败平台如实记录 (报错逐字, REPORT §3)
- [x] T2.4 根 worklog 追加 + push
- [x] skill 固化 (skills/video-downloader)
