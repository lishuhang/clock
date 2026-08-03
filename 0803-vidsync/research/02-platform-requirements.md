# Platform Requirements Matrix

> Research date: 2025 (latest verified)
> Scope: 13 Chinese self-media platforms investigated for video publishing
> Method: Web search + page reader for official help docs, GitHub repositories, and operational guides
> Verified user-mentioned quirks (B站 横屏封面, 36kr 裁剪, 微博 #话题#, etc.) and added newly discovered quirks

---

## Comparison Table (quick view)

| # | Platform | Login | Draft? | Cover dims | Title limit | Tag limit | Tag format | Video max | API? |
|---|----------|-------|--------|------------|-------------|-----------|------------|-----------|------|
| 1 | 微信视频号 | WeChat scan QR | ✅ Yes (mobile + PC) | 6:7=1080×1260, 16:9=1080×608 | ~30字 | 10 | #话题 (single #) | 2GB / 60min (mobile), 8h (PC) | No public |
| 2 | 哔哩哔哩 (Bilibili) | Phone SMS / password / 3rd-party | ✅ Yes (10-day expiry for video drafts) | 横版 1146×717 (≥960×600) min, 16:9, ≤5MB | 80字 | 10 | 自由标签 (no #) | 8GB (16GB for premium), 10h | Reverse-eng only (SocialSisterYi/bilibili-API-collect) |
| 3 | 企鹅号 (QQ Shizi) | Phone/email/QQ register | ✅ Yes | 16:9, 1280×720 min (640×360 abs min), ≤5MB JPG/PNG | 6~30字 (video) | 5 | Custom | 4GB (Chrome), 500MB (other browsers), 1sec-10h | RSS sync, Open API for partners |
| 4 | 腾讯视频 | QQ/WeChat scan | ✅ Yes (album + draft) | Recommended 1280×720 | Required | Open-ended | Custom | 2GB (free), 4GB (VIP), 10h max | No public, only partner API |
| 5 | 微博视频 | Weibo scan / SMS | ✅ Yes (PC) | 16:9 or 9:16, no strict dims | ≥6字 | Open | #话题# (double #) | PC 15GB, mobile 4GB, ≥3s | No public |
| 6 | 喜马拉雅 | Ximalaya APP scan | ✅ Yes (album-based) | Audio cover 1400×1400 for podcast; video supports 16:9 | Required | Open | Custom | Audio ≤200MB; Video similar to standard | Has open platform API (open.ximalaya.com) |
| 7 | 百家号 | Baidu scan / SMS | ✅ Yes (auto-save + manual) | 16:9, ≥660×370 (1280×720 recommended), ≤5MB | 6~30字 (video) | Open | Custom | 2GB max, MP4/MOV | Open platform API (集简云 integration) |
| 8 | 虎嗅 (Huxiu) | Phone SMS / 3rd-party | ✅ Yes (continue editing last) | 800×450 (16:9 landscape recommended) | 60字 | None (no tags) | N/A | 720P+, no size cap stated | No public |
| 9 | 36氪 (36kr) | Phone SMS + verification | ✅ Yes (misopen JS app) | Unknown — requires author cert | Required | ~5 (claimed) | Custom | Unknown — separate application | No public |
| 10 | 抖音创作者 | Douyin APP scan | ✅ Yes | 3:4 = 1080×1440 (recommended) | 55字 (含#话题) | 5 hot topics | #话题 (single #) | 4GB, 15min (long video) | Reverse-eng (SocialSisterYi, dreammis/social-auto-upload) |
| 11 | 快手 (Kuaishou) | Kuaishou APP scan | ✅ Yes | 9:16 = 1080×1920 | ~20字 | Open | #话题 | 4GB, 15min | Open API (open.kuaishou.com) + reverse-eng |
| 12 | 支付宝生活号 | Alipay APP scan | ✅ Yes | Cover ≤10MB; ratio 3:4 to 16:9 | Required | Open | #话题 | 1GB (regular) / 2GB (higher tier), 15s–30min | Open API (opendocs.alipay.com) |
| 13 | 小红书 (Xiaohongshu) | XHS APP scan | ✅ Yes | 3:4 = 1080×1440 recommended (also 1:1, 9:16) | 20字 | 10 | #话题 (single #) | 500MB (PC), 15min (5min for non-cert) | No official; reverse-eng (dreammis/social-auto-upload) |

---

## Per-Platform Detailed Analysis

### 1. 微信视频号 (WeChat Channels)

#### Login
- **Method**: Scan QR code with WeChat mobile app (强制). No username/password option.
- **URL**: https://channels.weixin.qq.com/platform/ (creator backend) or https://channels.weixin.qq.com/login.html (direct login)
- **2FA**: Implicit — relies on WeChat mobile confirmation, no separate 2FA prompt
- **Session expiry**: Cookie persists long (weeks) but on suspicious device change it will invalidate. Can invite up to 20 operators per channel
- **Non-technical operator**: Once scanned on phone, the desktop cookie persists. Operator can log in once and the cookie will be valid for ~30+ days unless WeChat detects risk

#### Posting Flow
- **URL**: https://channels.weixin.qq.com/platform/post/create
- **Draft support**: ✅ Yes — both mobile (手机端) and PC have 草稿箱. On PC you can save a draft and return later. On mobile, drafts persist on phone storage
- **Review**: ✅ Video must pass machine审核 before publishing. Common审核 time ~1hr
- **Drafts editable later**: ✅ Yes

#### Required Materials
- **Video**: 格式不限 (any format); ratio 0.33~3.0 (宽/高); 时长 3s~60min (mobile) or 3s~8h (PC); size ≤2GB; resolution 建议 1080p+; encoding 不限; **不支持 GIF/HDR video**; H.265 only works via iPhone or Mac Safari (Chrome won't accept H.265)
- **Cover**: Vertical 6:7 = 1080×1260; Landscape 16:9 = 1080×608; ratio must fit 0.33–3.0 range. Auto-generated from video frame or custom upload
- **Title**: Short title limit ~30字
- **Description**: Plain text; limit ~1000字
- **Tags/话题**: Up to 10 hashtags; format `#话题#` (single #, auto-closed)
- **Category**: Optional (内嵌于话题推荐)
- **Topic/合集**: Optional but supported (合集/系列功能)

#### Format Quirks
- **H.265 caveat**: PC web upload via Chrome does NOT support H.265. Must use iPhone to publish H.265 videos, or use Mac Safari
- **Cover ratio flexibility**: Very permissive (0.33–3.0). But朋友圈 share will crop to 1:1, so design cover content centered
- **Picture text posts**: Up to 18 images on PC (20 on mobile). Over 18 images becomes auto-generated video

#### API
- **Official**: No public Open API for video publishing. WeChat公众号 has draft API (`/cgi-bin/draft/add`) but this is for公众号 articles, NOT 视频号
- **OAuth**: Not available
- **Cookie-based**: Yes — community projects (e.g. `dreammis/social-auto-upload` tencent_uploader module) drive the browser via Playwright with cookie persistence

#### Anti-bot
- **CAPTCHA on login**: Usually just QR scan, no slider if cookie persists
- **CAPTCHA on publish**: Slider/拼图 can appear on rapid-fire publishing or new devices
- **Device fingerprinting**: Heavy (WeChat fingerprints the device)
- **Headless browser**: Likely blocked — `dreammis/social-auto-upload` recommends non-headless patchright (a stealthy playwright fork)

#### Notes for Automation
- Best practice: Use Playwright (patchright) with persistent context (storageState). Have operator scan QR once, save state to JSON, reuse across runs
- Watch for H.265 issue if videos come from iPhone — transcode to H.264 before upload
- Cover should be designed to look good in both 6:7 and 1:1 (cropped for朋友圈)

---

### 2. 哔哩哔哩 (Bilibili)

#### Login
- **Method**: QR scan (B站客户端), SMS, password, 3rd-party (微信/微博/QQ)
- **URL**: https://passport.bilibili.com/login (then redirects to member.bilibili.com)
- **2FA**: Phone number binding required; SMS verification on suspicious login
- **Session expiry**: SESSDATA cookie persists ~30 days; buvid3 (device fingerprint) is permanent per browser profile
- **Non-technical operator**: Can scan QR once and cookie persists for weeks

#### Posting Flow
- **URL**: https://member.bilibili.com/platform/upload-manager/article (article) or https://member.bilibili.com/platform/upload/video/frame (video)
- **Draft support**: ✅ Yes — but **drafts only persist 10 days** for video. After that they are auto-deleted (a frequent complaint)
- **Review**: ✅审核 takes 1–2 hours; rush hours 16:00–22:00 slower
- **Drafts editable**: ✅ Yes (within 10-day window)

#### Required Materials
- **Video**: Recommended MP4/FLV; supported formats: mp4, flv, avi, wmv, mov, webm, mpeg4, ts, mpg, rm, rmvb, mkv; size ≤8GB web (16GB for premium电磁力 users); duration ≤10 hours; bitrate avg ≤6000kbps, peak ≤24000kbps (else二次压制); audio ≤320kbps; max resolution 8K
- **Cover**: **横版 16:9 = 1146×717 recommended (min 960×600); file ≤5MB;** 竖版封面 also supported. **MUST be landscape 16:9 — confirmed user quirk**
- **Title**: ≤80字 (recommended ≤25字 for click optimization)
- **Description/简介**: ≤250字 default; some categories (动画/游戏/舞蹈) allow ≤2000字
- **Tags/标签**: ≤10 tags, free text (no # prefix needed). **Confirmed user quirk: 10 tags max**
- **Category/分区**: Required — predefined list (动画、番剧、国创、音乐、舞蹈、游戏、科技、生活、鬼畜、时尚、广告、娱乐、影视、纪录片、电影、电视剧)
- **Topic/合集**: Optional; can attach to a series (合集)
- **Other**: Visible scope (公开/仅自己可见), comments permission, danmaku mode

#### Format Quirks
- **二次压制 (re-encoding)**: All uploads are now re-encoded. Original bitrate above 6000kbps triggers aggressive compression. **Solution**: Pre-encode to H.264 with avg bitrate ≤6000kbps, audio AAC ≤320kbps
- **Cover landscape 16:9**: Confirmed — vertical covers work but standard format is 16:9. **Must avoid black bars / 边框 / official角标** in cover
- **分区-conditional limits**: Game/Animation categories allow 2000字 descriptions; others are 250字
- **Tag limit**: Confirmed 10 tags, free-form text (no # needed)
- **Title character limit**: 80字 hard limit (much longer than most platforms)

#### API
- **Official**: No official publishing API. However, B站 has an "Open Platform" (open.bilibili.com) for content partners — provides 专栏稿件图片上传 interface (`/arcopen/fn/...`). Not for general video publishing
- **Reverse-engineered**: `SocialSisterYi/bilibili-API-collect` is the de-facto reference. Implements WBI签名 + Cookie auth
- **`nemo2011/bilibili-api`** Python wrapper covers video upload flow
- **Rate limits**: Generally lenient for logged-in users; aggressive for anonymous

#### Anti-bot
- **WBI签名**: Most API calls require WBI (Winston-Bilibili-Index) signature — anti-tamper
- **b_ut=5 cookie + buvid3**: Device fingerprint cookies; missing → suspicious
- **CAPTCHA**: Slider (极验) on login when IP/device looks unusual
- **Headless browser**: Detectable via missing `navigator.webdriver` flag; `playwright-stealth` or `patchright` recommended
- **`biliup`** open-source tool uses official upload endpoints with WBI signing

#### Notes for Automation
- Use `biliup-rs` (Rust) or `biliup` (Python) which already handle WBI signing and chunked upload
- Pre-encode videos to fit under bitrate thresholds to avoid二压
- Cover MUST be 16:9 landscape (1146×717 ideal). User-confirmed quirk
- Drafts auto-delete after 10 days — **cannot rely on draft as long-term storage**

---

### 3. 企鹅号 / 腾讯内容开放平台 (QQ Shizi)

#### Login
- **Method**: Phone register, email register, or QQ号 (mobile only)
- **URL**: https://om.qq.com (PC) or https://m.om.qq.com (mobile)
- **2FA**: Phone verification required at registration; identity verification (身份证) required
- **Session expiry**: Persistent; cookies last weeks
- **Non-technical operator**: One scan, then cookie persists
- **One identity = max 3 accounts** per身份证

#### Posting Flow
- **URL**: https://shizi.qq.com/content/article-manage
- **Draft support**: ✅ Yes — drafts can be saved indefinitely; supports定时发布 (up to 72h later)
- **Review**: ✅ 审核 ~2 hours avg; high-traffic periods slower
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: Max 4GB on Chrome browser, 500MB on other browsers; duration 1sec–10h; supports竖屏 direct upload; formats include mp4, flv, f4v, webm, m4v, mov, 3gp, 3g2, rm, rmvb, wmv, avi, asf, mpg, mpeg, mpe, ts, div, dv, divx, vob, dat, mkv, swf, lavf, cpk, dirac, ram, qt, fli, flc, mod; also主流音频 mp3, aac, ac3, wav, m4a, ogg
- **Cover**: Min 640×360, max 5MB; formats JPG/JPEG/PNG; ratio 16:9 (横版 1280×720 min, 竖版 1080×1920 min); supports自定义封面, 系统封面, 截图封面
- **Title**: Video title 6~30字; article title 6~40字; **no special chars** (★, ┥, etc.); no consecutive punctuation (!!, ~~~); must start with 汉字/字母/数字/《》/""
- **Description**: Plain text
- **Tags/标签**: Up to 5 tags typically
- **Category/分类**: Optional but recommended (improves recommendation quality)
- **Topic/合集**: Optional
- **Other**: 原创声明 (manual only, not for RSS-synced); visible scope

#### Format Quirks
- **Browser-specific file size**: Chrome = 4GB, others = 500MB. **Critical to use Chrome-based automation**
- **Cross-platform sync**: 企鹅号 distributes to 腾讯新闻, 腾讯视频, QQ看点, 微视 — each may do secondary审核. So one upload multiplies审核 risk
- **Title char rules**: Strict — no表情符号, no consecutive punctuation
- **RSS sync option**: Can auto-sync from微信公众号 or custom RSS feed (doesn't count toward 5/day limit)
- **Daily post limit**: 一级/二级 = 3 posts/day; 三级/四级/五级 = 5 posts/day (video max 3/day)

#### API
- **Official**: ✅ Has developer center (om.qq.com/assets) — Open API for content partners (媒体合作). RSS support is publicly available
- **OAuth**: Not for individual creators; partner-level only
- **Cookie-based**: Yes; community projects (e.g. 集简云) integrate via RPA / cookie

#### Anti-bot
- **CAPTCHA on login**: Slider/拼图 on suspicious IP
- **CAPTCHA on publish**: Generally no
- **Device fingerprinting**: Moderate
- **Headless browser**: Should work with stealth plugins

#### Notes for Automation
- Use Chrome-family browser for 4GB upload limit
- Pre-upload videos must meet basic specs (1s–10h, any of listed formats)
- Cover image is critical — **landscape 16:9 1280×720 is the safe default**
- Content gets redistributed to multiple Tencent properties — make sure original content is suitable for 腾讯新闻 (mainstream) and 腾讯视频 (longer form)

---

### 4. 腾讯视频 (Tencent Video)

#### Login
- **Method**: QQ scan / WeChat scan / 手机号 + SMS
- **URL**: https://mp.v.qq.com (创作者 platform)
- **2FA**: Phone verification
- **Session expiry**: Persistent
- **Non-technical operator**: Easy

#### Posting Flow
- **URL**: https://mp.v.qq.com/manage/0 (manage); publish via https://mp.v.qq.com/neo/video-album (album-based) or short-video直接发布
- **Draft support**: ✅ Yes (album drafts + individual video drafts)
- **Review**: ✅ Required; time depends on content type (短剧 vs 短视频 vs 长视频)
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: Common formats MP4/AVI/FLV/MOV/WMV/MKV; size ≤2GB regular users, ≤4GB VIP; duration 1s–10h
- **Cover**: Recommended 1280×720 (16:9); JPG/PNG
- **Title**: Required, plain text
- **Description**: Plain text
- **Tags/话题**: Custom + 关联话题 (predefined list)
- **Category**: Required (short video, short drama 短剧, 知识, 影视, 纪录片, 少儿, etc.)
- **Topic/合集/专辑**: Required for some content types (esp. 短剧, 短番, 短节目) — album must be created first
- **Other**: 定时发布 available

#### Format Quirks
- **Album structure**: Unlike short-video platforms, 腾讯视频 organizes content into专辑 (albums) — particularly for短剧, 短番, 短节目. Must apply for album creation权限
- **Cover cropping**: Platform does some cropping to fit different display contexts (recommend landscape 16:9)
- **Short drama 激励计划**: Special category with revenue sharing (1.5–3元/小时 watched)
- **No GIF/HEIC**: Not supported
- **Cooperation with 抖音**: Since April 2023, Tencent Video and Douyin have cross-licensing — content can flow both ways

#### API
- **Official**: No public API. Partner-level access only
- **Cookie-based**: Yes

#### Anti-bot
- **CAPTCHA on login**: Slider on suspicious activity
- **CAPTCHA on publish**: Generally no
- **Device fingerprinting**: Moderate (Tencent统一账号 system)
- **Headless browser**: Should work

#### Notes for Automation
- Mainly suited for long-form content; less relevant for short-video distribution
- 短剧 content has special审核 + revenue model — different workflow
- Cover: stick to 1280×720 16:9

---

### 5. 微博视频 (Weibo)

#### Login
- **Method**: Scan with Weibo mobile, SMS, password
- **URL**: https://weibo.com (main) → 创作中心
- **2FA**: Phone绑定 required
- **Session expiry**: SUB cookie persists ~30 days; can extend
- **Non-technical operator**: Easy

#### Posting Flow
- **URL**: https://weibo.com/upload/channel (video channel); also via https://weibo.com (main composer with视频 tab)
- **Draft support**: ✅ Yes on PC (草稿箱 in创作中心)
- **Review**: ✅审核中 status; video社区投稿需审核
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: Format MP4 recommended; PC upload max 15GB; mobile max 4GB; minimum duration 3s (mobile); no转码率 limit stated
- **Cover**: 16:9 or 9:16 supported; no strict pixel dimension
- **Title**: ≥6字 (minimum, not maximum!); used for视频号 community投稿
- **Description/正文**: ≤2000字 (since Nov 2016 cancellation of 140字 limit); can include图片 (max 9) + 视频 mixed
- **Tags/话题**: **Format `#话题#` — DOUBLE #** (one at start, one at end). Confirmed user quirk. Also 超话 (super topic) with diamond icon
- **Category/频道**: Required for视频社区投稿 — predefined list
- **Topic/合集/专辑**: Optional (album功能)
- **Other**: 类型 (原创/转载), 水印选项

#### Format Quirks
- **Double # hashtag**: Confirmed — Weibo uses `#话题#` (start AND end #), unlike Twitter's single #. This is unique to Weibo (and historically to older Chinese platforms)
- **超话 (super topic)**: Different from regular话题 — needs to be created/approved; shows diamond icon
- **Minimum title length**: 6字 minimum (rare — most platforms have max, not min)
- **PC vs mobile file size**: PC = 15GB, mobile = 4GB (big difference)
- **Mixed image+video post**: One微博 can contain up to 9 images+video mix (微博客户端 12.11.4+)
- **720P requirement**: 视频社区 requires ≥720P

#### API
- **Official**: Limited Open API (open.weibo.com) for read/search; not for video publishing
- **OAuth**: Available for read APIs (OAuth2.0)
- **Cookie-based**: Required for publishing

#### Anti-bot
- **CAPTCHA on login**: Slider on suspicious IP/device
- **CAPTCHA on publish**: Sometimes for high-frequency posting
- **Device fingerprinting**: Yes (Weibo fingerprints browser)
- **Headless browser**: Triggers risk control more aggressively than Douyin/Bilibili

#### Notes for Automation
- Watch double-# hashtag format — common conversion bug
- Use PC for large files (>4GB)
- Title minimum 6字 — important for short video clips (don't use too-short titles)
- 超话 requires pre-existing super-topic — can't create on the fly
- Best fit for: time-sensitive / trending topics / news videos

---

### 6. 喜马拉雅 (Ximalaya)

#### Login
- **Method**: Ximalaya APP scan; phone SMS; 3rd-party (微信/QQ/微博)
- **URL**: https://studio.ximalaya.com (creator studio) or https://studio.ximalaya.com/upload
- **2FA**: Phone verification
- **Session expiry**: Persistent (~30 days)
- **Non-technical operator**: Easy

#### Posting Flow
- **URL**: https://studio.ximalaya.com/opus (publish) or /upload
- **Draft support**: ✅ Yes — audio can be saved in云剪辑 (cloud editor) indefinitely; album-based structure allows draft saves
- **Review**: ✅ Required
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Audio (primary)**: MP3, WMA, AIFF, AIF, WAV, FLAC, OGG, MP2, AAC, AMR; size ≤200MB per file
- **Video**: Supported via APP upload (新功能); specs similar to standard video (MP4, etc.)
- **Cover**: Album cover; for Apple Podcast RSS — 1400×1400 required
- **Title**: Required; album title ≤30字 typically
- **Description/简介**: Plain text; album简介 + per-episode简介
- **Tags/标签**: Custom; album-level
- **Category/分类**: Required (predefined — 相声, 评书, 音乐, 教育, 有声书, etc.)
- **Topic/专辑**: **Required** — content must be organized into专辑 (albums); each episode belongs to an album
- **Other**: 定时发布 available; 版权声明

#### Format Quirks
- **Audio-first platform**: Although video upload is supported, Ximalaya is fundamentally an audio platform. Video is secondary
- **Album structure mandatory**: Cannot publish a standalone音频/video — must belong to an album. Albums are akin to播客 channels
- **Podcast RSS**: For Apple Podcasts distribution, album cover MUST be 1400×1400
- **云剪辑 (cloud editing)**: Built-in audio editor at audioeditor.ximalaya.com — supports ASR语音转文字
- **音剪AI**: AI-powered audio creation tool

#### API
- **Official**: ✅ Has open platform (open.ximalaya.com) with API documentation (doc/detailApi). Supports content retrieval and metadata
- **OAuth**: Available for partner-level
- **Cookie-based**: Required for publishing
- **Rate limits**: Not publicly disclosed

#### Anti-bot
- **CAPTCHA on login**: SMS-based primarily
- **CAPTCHA on publish**: No
- **Device fingerprinting**: Light
- **Headless browser**: Should work

#### Notes for Automation
- **Different use case** — primarily for audio content (podcast, audiobook, talk show)
- Video uploads work but audience is smaller
- Album creation is a prerequisite — pre-create albums before bulk-publishing episodes
- For podcast distribution, ensure 1400×1400 album cover

---

### 7. 百家号 (Baijiahao)

#### Login
- **Method**: Baidu scan / SMS / Baidu账号
- **URL**: https://baijiahao.baidu.com (main); https://baijiahao.baidu.com/builder/rc/content (publish)
- **2FA**: Phone绑定
- **Session expiry**: Persistent (Baidu统一账号)
- **Non-technical operator**: Easy

#### Posting Flow
- **URL**: https://baijiahao.baidu.com/builder/rc/content
- **Draft support**: ✅ Yes — auto-save + manual save; supports定时发布
- **Review**: ✅ Required; ~1–2 hours
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: Max 2GB; formats MP4/MOV (other formats need conversion); recommended 720P+
- **Cover**: Min 660×370; recommended 16:9 1280×720; JPG/PNG ≤5MB; cover最好 from video screenshot
- **Title**: 6~30字 (video); article title 8~30字; no标题党 vocabulary
- **Description**: Plain text; short description
- **Tags/标签**: Open count
- **Category/分类**: Required (vertical领域 — e.g. 科技, 财经, 娱乐, 体育, 历史, etc.)
- **Topic/合集**: Optional
- **Other**: 原创 (原创声明 toggle, requires certification), visible scope, 定时发布

#### Format Quirks
- **Strict title rules**: 6–30字 (video) and 8–30字 (article); no标题党 vocabulary (日了狗, 不看后悔)
- **Cover dimensions**: Min 660×370 (older docs) or 1280×720 (newer docs); 16:9 mandatory
- **垂直度 (verticality)**: Account health score includes垂直度 — must stay in same category for better recommendation
- **Daily limits**: 新手 = 1 post/day; 转正 = 5/day; 原创 = 10/day
- **Original label**: Must apply separately for原创标签; brings 3x流量主收益
- **Image with文字**: Will be filtered (marketing text in images is blocked)

#### API
- **Official**: Has 百家号挂载API (流量分发资源) — `lyungy/auto_baijiahao` open-source Python tool exists
- **OAuth**: Partner-level only
- **Cookie-based**: Yes; 集简云 integration supports cookie-based automation
- **AIWriteX project**: Supports百家号 with auto-publish and draft箱

#### Anti-bot
- **CAPTCHA on login**: Slider on Baidu账号 login
- **CAPTCHA on publish**: No
- **Device fingerprinting**: Moderate
- **Headless browser**: Should work with stealth

#### Notes for Automation
- Use auto-save + draft workflow for safety
- Pre-create cover images at 1280×720 (16:9)
- Title 6–30字 is narrow — keep titles in this range
- 申请原创标签 for higher revenue (3x multiplier)
- Daily limits per account — distribute across multiple accounts if scaling

---

### 8. 虎嗅 (Huxiu)

#### Login
- **Method**: Phone SMS / 3rd-party; first-time contributors must complete备案 (filing)
- **URL**: https://www.huxiu.com/contribute.html (article); https://m.huxiu.com/contribute/video_article (video)
- **2FA**: Phone verification at备案
- **Session expiry**: Persistent
- **Non-technical operator**: Moderate — requires initial备案 setup

#### Posting Flow
- **URL (video)**: https://m.huxiu.com/contribute/video_article
- **URL (article)**: https://m.huxiu.com/contribute/article (only accepts微信公众号 links! Cannot直接 upload articles)
- **Draft support**: ✅ Yes — explicit "继续编辑上次的内容? 创建新内容" prompt
- **Review**: ✅ **Heavy编辑审核** — Huxiu is an editorial-curated platform, not pure UGC. Editor may modify or reject submissions
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: 尺寸建议 16:9 or 9:16; resolution ≥720P; size limit not stated (likely <2GB)
- **Cover**: Recommended 800×450 (16:9 landscape); confirms user quirk about横屏 cover requirement
- **Title**: ≤60字
- **Description/正文**: Plain text (used for video description)
- **Tags**: No标签 system — Huxiu uses编辑分类 instead
- **Category/创作领域**: Required at备案 — 时政新闻, 财经金融, 娱乐生活, 医疗健康, 文化教育, 金融地产, 企业服务, 创业报道, 社交通讯, 全球观察, 车与出行, 商业观察, 前沿科技, 年轻一代
- **Topic/合集**: N/A
- **Other**: 给编辑留言 (0/100 chars), 联系方式 (phone/email), 开启赞赏 (0/15 chars), 微信授权 (原创标独家 / 白名单), 匿名投稿 option
- **For article submission**: Only accepts微信公众号 link — auto-imports article content

#### Format Quirks
- **Article submission via WeChat公众号 link only**: Cannot直接 paste article content for article submission. Must first publish on微信公众号, then submit the link. **Confirmed**: "暂不能转采文内视频"
- **Video submission: direct upload only** — separate flow from article submission
- **Cover must be 16:9 landscape** (800×450) — confirmed user quirk
- **Editorial review**: Submissions are reviewed by Huxiu editors — not guaranteed publication. Editor can修改/删减/编辑/翻译/改编/加注或配图
- **Filing required**: First-time contributors must submit备案 (account type, real name, ID, creation领域). 时政领域 requires《互联网新闻信息服务许可证》
- **5 submissions/day limit** for article (WeChat link)

#### API
- **Official**: ❌ No public API; Huxiu is editorial-curated
- **OAuth**: N/A
- **Cookie-based**: The only path; but editorial review means automation is pointless

#### Anti-bot
- **CAPTCHA on login**: Light
- **CAPTCHA on publish**: N/A (manual review by editors)
- **Device fingerprinting**: Light
- **Headless browser**: Not particularly useful due to editorial review

#### Notes for Automation
- **Huxiu is not a UGC platform** — it's an editorial-curated tech/business publication
- Cannot truly automate — editor review is mandatory and slow
- For article submission: must first publish on微信公众号, then submit the link
- For video submission: direct upload with 800×450 cover
- Best fit for: long-form business/tech analysis (5000–8000字 深度稿; 1500–3000字 快评/专栏)
- Filed accounts can submit 5 articles/day

---

### 9. 36氪 (36kr)

#### Login
- **Method**: Phone SMS (+86 only, no international); verification required
- **URL**: https://misopen.36kr.com (creator backend, JS SPA); https://www.36kr.com/external-author-apply (author application)
- **2FA**: Phone verification
- **Session expiry**: Persistent (~30 days)
- **Non-technical operator**: Moderate — first requires author application

#### Posting Flow
- **URL**: https://misopen.36kr.com (创作者 backend, fully JS-rendered SPA — "页面加载中..." on no-JS access)
- **Author application URL**: https://www.36kr.com/external-author-apply
- **Draft support**: ✅ Yes (misopen supports草稿 save)
- **Review**: ✅ Required; editorial-curated like Huxiu
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: Application-based; specific specs depend on认证 type (个人/企业)
- **Cover**: Dimensions not publicly documented; landscape 16:9 typical; **does secondary cropping** (per user info) — exact crop dimensions need testing
- **Title**: Required
- **Description**: Plain text
- **Tags**: **Max 5 tags** (per user-supplied info; not directly verified but commonly cited)
- **Category**: Required (文章/音频/视频/直播 at application time)
- **Other**: 认证辅助信息 (screenshots of other platform presence, 20+ original articles recommended)

#### Format Quirks
- **Author certification prerequisite**: Must apply for认证 (个人 or 企业); requires身份证 photos, 微信号码, 投稿意向, 认证辅助信息 (other-platform screenshots)
- **Misopen is fully JS SPA**: Cannot scrape with simple HTTP — needs headless browser
- **5 tags limit**: Per user info (not directly verified in搜索 results)
- **Cover secondary cropping**: Per user info — cover gets cropped to multiple dimensions for different display contexts (homepage, search, mobile app)
- **36kr logo placement**: Often re-brands content with 36kr logo on cover

#### API
- **Official**: ❌ No public API
- **OAuth**: N/A
- **Cookie-based**: Yes; but editorial-curated

#### Anti-bot
- **CAPTCHA on login**: Slider/拼图 (the misopen front-page showed "请完成下列验证后继续" with拼图 slider)
- **CAPTCHA on publish**: Likely similar
- **Device fingerprinting**: Moderate
- **Headless browser**: Probably detectable due to heavy JS + slider

#### Notes for Automation
- **Editorial-curated platform** — cannot truly automate publishing
- Author认证 required first (with身份证, etc.)
- Tag limit (5 max) needs to be enforced in any tool
- Cover should account for secondary cropping — keep important content centered
- Best fit for: 创投/科技/startup content (36kr's core audience)

---

### 10. 抖音创作者 (Douyin Creator)

#### Login
- **Method**: Scan with Douyin APP (recommended); SMS login (86 only)
- **URL**: https://creator.douyin.com/creator-micro/home
- **2FA**: Phone绑定
- **Session expiry**: ~3 months for stable cookies; but can invalidate on device change
- **Non-technical operator**: Easy scan-once flow

#### Posting Flow
- **URL**: https://creator.douyin.com/creator-micro/content/upload (publish); https://creator.douyin.com/creator-micro/content/manage (manage)
- **Draft support**: ✅ Yes (草稿箱 on both mobile and PC)
- **Review**: ✅ Required; ~1 hour typical
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: MP4 recommended; vertical 9:16 = 1080×1920 (preferred); horizontal 16:9 = ≥1280×720; bitrate ≥516kbps; size ≤4GB; duration ≥4s; max 15min for长视频; 1080P max recommended
- **Cover**: 3:4 = 1080×1440 (recommended for信息流 display); 9:16 also supported; JPG/PNG ≤5MB
- **Title/文案**: ≤55字 (includes #话题); 1000字 for长图文 (newer feature)
- **Description**: Combined with title (single文案 field)
- **Tags/话题**: Up to 5 hot topics (#话题); **format #话题** (single #, no closing #)
- **Category**: Optional but improves recommendation
- **Topic/合集**: Optional
- **Other**: 位置 (location), 可见范围 (公开/好友/私密), 定时发布, 共创 (co-creation, requires 7000+ followers), 商品 (ecommerce link)

#### Format Quirks
- **Title limit is 55字 INCLUDING #话题** — major constraint; if 5 hashtags avg 4 chars each, only 35字 left for actual title
- **Cover ratio 3:4 ≠ video ratio 9:16**: Cover in信息流 displays as 3:4 (cropped from 9:16 video), but full video plays as 9:16
- **Vertical preferred**: 9:16 1080×1920 is the standard; horizontal videos get less traffic
- **500MB App upload limit**: Mobile app single file ≤500MB (per创作者服务协议); PC web allows 4GB
- **共创投稿**: Requires粉丝 >7000; max 4/month
- **6类必选标签**: Per中央网信办 2025 mandate — 必须标注 AI生成/虚构演绎/时事信息/营销内容等 6类标签之一

#### API
- **Official**: 抖音开放平台 (developer.open-douyin.com) — focused on小程序 and read-only video APIs; NOT for personal publishing
- **OAuth**: Available for read APIs
- **Reverse-engineered**: Multiple Python projects (A2Data/auto_douyin, dreammis/social-auto-upload); use cookie-based with WBI签名 + slider CAPTCHA solving

#### Anti-bot
- **CAPTCHA on login**: Slider (`x-vc-bdturing-sdk`); often blocks non-Chinese IPs
- **CAPTCHA on publish**: Can appear on rapid posting
- **Device fingerprinting**: Heavy — `s_v_web_id` cookie tracks device
- **Headless browser**: Highly detected; `playwright-stealth` or `patchright` essential
- **Cookie expiry**: Variable; can invalidate on device/IP change

#### Notes for Automation
- Most-covered platform in open-source auto-upload tools (dreammis/social-auto-upload, A2Data/auto_douyin)
- Use patchright (stealth playwright) for stability
- Pre-create cover at 3:4 = 1080×1440 to avoid cropping
- Title budget: 55字 total including #话题 — pre-calculate
- For long视频 (>1min), requires开通长视频权限 (account-level)
- Avoid running multiple accounts on same device/IP — high封禁 risk

---

### 11. 快手 (Kuaishou)

#### Login
- **Method**: Kuaishou APP scan / 手机号 + SMS
- **URL**: https://cp.kuaishou.com (创作者平台)
- **2FA**: Phone绑定
- **Session expiry**: Persistent
- **Non-technical operator**: Easy

#### Posting Flow
- **URL**: https://cp.kuaishou.com/article/manage/video?status=2&from=publish (publish); https://cp.kuaishou.com/article/manage (manage)
- **Draft support**: ✅ Yes (草稿箱)
- **Review**: ✅ Required
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: Max 4GB; max duration 15min (long video requires权限); recommended 720P+
- **Cover**: 9:16 = 1080×1920 (recommended); JPG/PNG ≤5MB; can select frame or custom upload
- **Title/描述**: ≤500字 (描述字段); title (separate) ~20字
- **Tags/话题**: Format `#话题` (single #)
- **Category**: Optional
- **Topic/合集**: Optional
- **Other**: 位置, 可见范围, 定时发布, 原创标签 toggle (must be set before publish)

#### Format Quirks
- **Cover is 9:16 (full vertical)**: Unlike抖音's 3:4 cover, 快手 uses full 9:16 1080×1920 — **less cropping** but bottom 20% gets obscured by UI elements
- **Original标签 toggle**: Must explicitly mark as原创 in edit界面 (not auto-detected)
- **Long video权限**: 5min–15min requires account in good standing
- **手机上传 long视频**: <500MB, <10min for older mobile upload path
- **Multiple crop ratios on different pages**: 发现页, 关注页, 搜索页 each auto-crop cover differently — design cover with center safe zone

#### API
- **Official**: ✅ Has open platform (open.kuaishou.com) — supports视频 create/upload APIs with分片 (chunked) upload support (≤10MB chunks recommended)
- **OAuth**: Available
- **Reverse-eng**: `dreammis/social-auto-upload` covers Kuaishou via browser automation
- **Cookie-based**: Yes; popular approach

#### Anti-bot
- **CAPTCHA on login**: Slider on suspicious activity
- **CAPTCHA on publish**: Generally no
- **Device fingerprinting**: Moderate
- **Headless browser**: Works with stealth plugins

#### Notes for Automation
- Use 1080×1920 cover (full vertical) with safe zone (avoid bottom 20%)
- 原创标签 must be toggled explicitly
- Open API available (open.kuaishou.com) — preferred over browser automation if approved partner
- Pre-create covers with主体居中 to handle multi-ratio cropping

---

### 12. 支付宝生活号 (Alipay)

#### Login
- **Method**: Alipay APP scan; 手机号 + SMS
- **URL**: https://c.alipay.com/page/portal/home (creator portal); PC publish at https://s.alipay.com or https://sweb.alipay.com
- **2FA**: Alipay account has built-in 2FA (支付密码 + 实名认证)
- **Session expiry**: Persistent
- **Non-technical operator**: Easy

#### Posting Flow
- **URL**: PC: login S.alipay.com → 创作内容 → 发内容 → 短视频创作; mobile: 支付宝 APP → 生活号+ 创作中心
- **Draft support**: ✅ Yes (草稿箱)
- **Review**: ✅ Required
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: 
  - 手机端 拍摄: 3s–60s
  - 手机端 导入: 3s–300s (5min)
  - PC端: 15s–30min (recommended); max file size 1GB (飞达激励计划) or 2GB (content creation guide)
  - Format: MP4 (H264) primary; also MOV, AVI, M4V, MKV, WEBM; H265 supported
  - Resolution: 540P min, 1080P+ recommended
  - Ratio: 3:4 to 16:9 (vertical 9:16, landscape 4:3 or 16:9, all supported)
- **Cover**: ≤10MB; local upload supported; ratio matches video
- **Title**: Required; ~20字 typical
- **Description**: Plain text
- **Tags/话题**: Format `#话题`
- **Category**: Optional
- **Topic/合集**: Optional
- **Other**: 关联小程序 (link to mini-program), 商品 (ecommerce), 定时发布, 内容二次编辑 (post-publish editing)

#### Format Quirks
- **Multiple duration limits by entry point**: 拍摄 60s, 导入 5min, PC 30min — **be aware of which entry point you're using**
- **File format flexibility**: H265 supported (unlike many platforms)
- **540P min resolution**: Lower than other platforms' 720P
- **Cover ≤10MB**: Generous (vs. 5MB on most platforms)
- **Mini-program linking**: Strong feature — can attach小程序 to video for transactional content
- **飞达激励计划**: Special revenue program with stricter requirements (1080P+, 15s–5min, MP4 H264, no third-party watermarks)

#### API
- **Official**: ✅ Comprehensive — opendocs.alipay.com has full API documentation for生活号 (Life Account)
  - File upload API (multipart/form-data)
  - 生活号 creation/management APIs
  - Video ID retrieval API (opendocs.alipay.com/mini/081db1)
- **OAuth**: Available via蚂蚁金服开放平台
- **Rate limits**: Standard Alipay open platform limits
- **Cookie-based**: Also works for browser automation

#### Anti-bot
- **CAPTCHA on login**: Alipay login is heavily protected — slider + sometimes人脸识别 for sensitive actions
- **CAPTCHA on publish**: No
- **Device fingerprinting**: Heavy (Alipay fingerprints heavily for fraud prevention)
- **Headless browser**: Detectable; Alipay may flag account

#### Notes for Automation
- **Best official API support** of all 13 platforms — first choice for legitimate automation
- Use Open API (opendocs.alipay.com) over browser automation when possible
- Mind the duration limits by entry point (拍摄 60s vs 导入 5min vs PC 30min)
- For飞达激励计划: stick to 1080P+ MP4 H264, 15s–5min, no watermarks
- Cover can be up to 10MB — allows higher quality
- Excellent for transactional content (mini-program linking)

---

### 13. 小红书 (Xiaohongshu)

#### Login
- **Method**: XHS APP scan; 手机号 + SMS; 微信/QQ 3rd-party
- **URL**: https://creator.xiaohongshu.com/publish/publish (publish); https://creator.xiaohongshu.com (creator home)
- **Note**: Some users report `creator.xiaohongshu.com` is GeoIP-blocked overseas — fallback domain `creator.rednote.com` exists
- **2FA**: Phone绑定
- **Session expiry**: Persistent (~30 days)
- **Non-technical operator**: Easy

#### Posting Flow
- **URL**: https://creator.xiaohongshu.com/publish/publish
- **Draft support**: ✅ Yes — both mobile (本地草稿, deleted on app uninstall) and PC (cloud草稿箱)
- **Review**: ✅ Required; ~1 hour typical; stricter for product/affiliate content
- **Drafts editable**: ✅ Yes

#### Required Materials
- **Video**: 
  - Format: MP4/MOV (H.264, AAC audio)
  - Size: ≤500MB (PC upload)
  - Duration: 5s–5min (regular accounts); up to 15min (小红书视频号认证 accounts); web supports 15min/10GB
  - Resolution: 720P+ recommended (1080P ideal)
  - Ratios: 9:16, 3:4, 1:1, 4:3 (3:4 is preferred for vertical; 16:9 gets black bars / 限流)
- **Cover**: 3:4 = 1080×1440 (推荐); also 1:1 = 1080×1080; can upload 1 default + 3 PK covers for A/B testing (system auto-selects best CTR after 10h)
- **Title**: ≤20字 (汉字计)
- **Description/正文**: ≤1000字 (regular); ≤6000字 (长文功能 — new 2025 feature, internal testing)
- **Tags/话题**: ≤10 tags; format `#话题` (single #)
- **Category**: Optional (improves recommendation)
- **Topic/合集**: Optional (合集功能)
- **Other**: 位置, @提及, 商品 (商品链接), 图片标签 (clickable tags on image)

#### Format Quirks
- **9-grid limit is for IMAGES, not video**: Confirmed user quirk. Video posts are single video; image posts are 1–9 images. **Mixed image+video post**: not supported (unlike微博)
- **Cover ratio 3:4 strongly preferred**: 16:9 covers get 限流 (less traffic)
- **A/B cover testing**: Unique feature — upload 1 default + 3 PK covers; system picks best CTR after 10 hours
- **Title 20字 hard limit**: One of the shortest among all platforms
- **Long文 feature (2025 internal test)**: 6000字 max正文, with auto-pagination to image format
- **Cannot directly upload video to小红书 without account**: Account required (registration via APP only)
- **GeoIP issues**: creator.xiaohongshu.com blocked overseas; use creator.rednote.com (verified in dreammis/social-auto-upload issue #226)
- **Tag limit 10**: Confirmed
- **Topic is tag, not category**: 小红书 conflates "topic" and "tag" — both use #话题

#### API
- **Official**: ❌ No public API for personal publishing
- **OAuth**: Not available
- **Cookie-based**: Required; `dreammis/social-auto-upload` xiaohongshu module (browser automation)
- **Note**: Some content爬虫 APIs exist for READ (e.g. ReaChief/xhs) but NOT for publish

#### Anti-bot
- **CAPTCHA on login**: Slider (点选/拼图) on suspicious activity
- **CAPTCHA on publish**: Can appear; especially for new accounts
- **Device fingerprinting**: Heavy — 小红书 fingerprints device aggressively
- **Headless browser**: Highly detected; `patchright` (stealth playwright fork) essential
- **GeoIP blocking**: creator.xiaohongshu.com blocked overseas — use creator.rednote.com

#### Notes for Automation
- Use `creator.rednote.com` for overseas deployment
- Pre-create cover at 3:4 = 1080×1440 (vertical preferred)
- Title ≤20字 — extremely tight; design content templates around this
- 9-grid limit only applies to image posts (single video per video post)
- For long视频 (>5min): requires视频号认证 first
- Heavy A/B cover testing — leverage it for CTR optimization
- Best fit for: 种草 (product recommendation), 美妆, 时尚, 旅行, food content

---

## Cross-Platform Differences Summary

### Cover Image Dimensions Needed Per Platform

| Platform | Recommended cover dims | Ratio | Format | Max size |
|----------|------------------------|-------|--------|----------|
| 微信视频号 | 1080×1260 (vertical) / 1080×608 (landscape) | 6:7 / 16:9 | JPG/PNG | ~5MB |
| 哔哩哔哩 | **1146×717** (横版) | 16:9 (landscape ONLY) | JPG/PNG | 5MB |
| 企鹅号 (QQ Shizi) | 1280×720 (横版) / 1080×1920 (竖版) | 16:9 / 9:16 | JPG/JPEG/PNG | 5MB |
| 腾讯视频 | 1280×720 | 16:9 | JPG/PNG | ~5MB |
| 微博视频 | No strict dims | 16:9 or 9:16 | JPG/PNG | ~5MB |
| 喜马拉雅 | 1400×1400 (podcast) | 1:1 | JPG/PNG | 5MB |
| 百家号 | 1280×720 (≥660×370 min) | 16:9 | JPG/PNG | 5MB |
| 虎嗅 | **800×450** | 16:9 (landscape) | JPG/PNG | 5MB |
| 36氪 | Unknown — subject to secondary cropping | 16:9 (assumed) | JPG/PNG | Unknown |
| 抖音 | **1080×1440** | 3:4 (NOT 9:16) | JPG/PNG | 5MB |
| 快手 | **1080×1920** | 9:16 | JPG/PNG | 5MB |
| 支付宝生活号 | Matches video ratio | 3:4–16:9 | JPG/PNG | **10MB** (most generous) |
| 小红书 | **1080×1440** | 3:4 (preferred) / 1:1 | JPG/PNG | 5MB |

**Universal safe dimensions**: Design at 1920×1080 (16:9) master + 1080×1440 (3:4) master + 1080×1920 (9:16) master. Crop down per platform.

### Tag Count Limits

| Platform | Max tags | Notes |
|----------|----------|-------|
| 微信视频号 | 10 | #话题 |
| 哔哩哔哩 | **10** | Free text, no # prefix |
| 企鹅号 | ~5 | Custom |
| 腾讯视频 | Open | Custom + 关联话题 |
| 微博视频 | Open | #话题# (double #) |
| 喜马拉雅 | Open | Album-level |
| 百家号 | Open | Custom |
| 虎嗅 | 0 | No tag system |
| 36氪 | **~5** (per user info) | Custom |
| 抖音 | **5** | #话题 |
| 快手 | Open | #话题 |
| 支付宝生活号 | Open | #话题 |
| 小红书 | **10** | #话题 |

### Tag Format Quirks

| Platform | Tag format | Example | Notes |
|----------|------------|---------|-------|
| 微信视频号 | `#话题` (single #, no closing) | `#美食探店` | Auto-completes via话题 library |
| 哔哩哔哩 | Free text (no # prefix) | `美食探店` | Plain text input field |
| 企鹅号 | Custom text | `美食探店` | Plain text |
| 腾讯视频 | Custom + 关联话题 | `美食探店` | Mix of free + predefined |
| **微博视频** | **`#话题#` (DOUBLE #)** | **`#美食探店#`** | **UNIQUE TO WEIBO** — both start AND end # |
| 喜马拉雅 | Custom text | `美食探店` | Album-level only |
| 百家号 | Custom text | `美食探店` | Plain text |
| 虎嗅 | N/A | — | No tag system |
| 36氪 | Custom text | `美食探店` | Plain text |
| 抖音 | `#话题` (single #) | `#美食探店` | Counts toward 55字 title limit |
| 快手 | `#话题` (single #) | `#美食探店` | In描述 field |
| 支付宝生活号 | `#话题` (single #) | `#美食探店` | In描述 field |
| 小红书 | `#话题` (single #) | `#美食探店` | Up to 10 |

**Critical conversion rule**: When syndicating from微博 → other platforms, MUST strip the trailing `#`. When syndicating TO微博, MUST add trailing `#`.

### Title Character Limits

| Platform | Title limit | Notes |
|----------|-------------|-------|
| 微信视频号 | ~30字 | Short title field |
| 哔哩哔哩 | **80字** (recommended ≤25) | One of the longest |
| 企鹅号 | **6–30字** (video) / 6–40字 (article) | Has MINIMUM 6字 |
| 腾讯视频 | Required, no strict limit | Plain text |
| 微博视频 | **≥6字 minimum** (no max) | Unique — has MINIMUM not max |
| 喜马拉雅 | ~30字 | Album title |
| 百家号 | **6–30字** (video) / 8–30字 (article) | Has MINIMUM 6字 |
| 虎嗅 | ≤60字 | Plain text |
| 36氪 | Required | Plain text |
| 抖音 | **55字 (含#话题)** | Most restrictive; includes hashtags |
| 快手 | ~20字 | Plain text |
| 支付宝生活号 | ~20字 | Plain text |
| 小红书 | **20字** | One of the shortest |

### Video File Size & Duration Limits

| Platform | Max file size | Max duration | Min duration | Recommended encoding |
|----------|---------------|--------------|--------------|----------------------|
| 微信视频号 | 2GB | 60min (mobile), 8h (PC) | 3s | Any (H.264 safest) |
| 哔哩哔哩 | 8GB (16GB premium) | 10h | None | H.264, ≤6000kbps avg |
| 企鹅号 | 4GB (Chrome), 500MB (others) | 10h | 1s | MP4 |
| 腾讯视频 | 2GB (4GB VIP) | 10h | 1s | MP4 |
| 微博视频 | 15GB (PC), 4GB (mobile) | Unlimited | 3s (mobile) | MP4 |
| 喜马拉雅 | 200MB (audio) | ~20min recommended | None | MP3/AAC |
| 百家号 | 2GB | None stated | None | MP4/MOV |
| 虎嗅 | Not stated (likely 2GB) | None | None | MP4, 720P+ |
| 36氪 | Unknown | Unknown | Unknown | MP4 |
| 抖音 | 4GB (PC), 500MB (mobile APP) | 15min (long video权限) | 4s | MP4 H.264 |
| 快手 | 4GB | 15min | None | MP4 |
| 支付宝生活号 | 1–2GB | 30min (PC), 5min (mobile导入), 60s (mobile拍摄) | 3s | MP4 H.264/H.265 |
| 小红书 | 500MB (PC), 10GB (some accounts) | 5min (regular), 15min (视频号认证) | 5s | MP4/MOV H.264 |

### Platforms with NO Draft Support (highest risk)

**ALL 13 platforms support draft functionality in some form.** However, there are important caveats:

| Platform | Draft support details |
|----------|----------------------|
| 哔哩哔哩 | ⚠️ **Drafts auto-delete after 10 days** — cannot rely on long-term |
| 微信视频号 | ✅ Persistent (mobile local + PC cloud) |
| 企鹅号 | ✅ Persistent; supports定时发布 (72h later) |
| 腾讯视频 | ✅ Persistent (album drafts) |
| 微博视频 | ✅ PC draft箱; mobile drafts local only |
| 喜马拉雅 | ✅ Cloud (云剪辑) — indefinite |
| 百家号 | ✅ Persistent; auto-save |
| 虎嗅 | ✅ "继续编辑上次的内容" prompt — session-based |
| 36氪 | ✅ Persistent (misopen SPA) |
| 抖音 | ✅ Persistent; both mobile + PC |
| 快手 | ✅ Persistent |
| 支付宝生活号 | ✅ Persistent; supports二次编辑 after publish |
| 小红书 | ⚠️ Mobile drafts lost on app uninstall; PC drafts cloud-persist |

### Platforms Where Automation is Hardest (CAPTCHA, Anti-bot, Editorial Review)

Ranked from hardest to easiest:

1. **虎嗅 (Huxiu)** — Editorial review is mandatory. Editors modify/reject submissions. No API. Even if you automate the upload, you cannot bypass editorial gatekeeping
2. **36氪 (36kr)** — Author认证 required (身份证, etc.); slider CAPTCHA on misopen; editorial review; fully JS SPA requires headless browser
3. **抖音创作者** — Heavy slider CAPTCHA (x-vc-bdturing-sdk); device fingerprinting (s_v_web_id); headless detection; GeoIP issues; but well-documented reverse-eng APIs exist (dreammis/social-auto-upload)
4. **小红书** — Heavy device fingerprinting; GeoIP blocking of creator.xiaohongshu.com (use creator.rednote.com); headless detection; needs patchright
5. **微信视频号** — WeChat device fingerprint; H.265 only works via iPhone/Safari; QR scan required (no SMS alt)
6. **支付宝生活号** — Heavy Alipay device fingerprint; BUT has official Open API — use API for legitimate automation
7. **微博视频** — Multiple CAPTCHA layers; risk control aggressive on new accounts; double-# tag format is unique
8. **哔哩哔哩 (Bilibili)** — WBI签名 required; buvid3 fingerprint; but well-documented (SocialSisterYi/bilibili-API-collect) and `biliup` tool exists
9. **企鹅号** — Standard CAPTCHA; daily post limits; multi-platform distribution may trigger secondary审核
10. **百家号** — Baidu account CAPTCHA; daily limits; but `auto_baijiahao` open-source tool exists
11. **腾讯视频** — Standard CAPTCHA; mainly for长视频/短剧 — different workflow
12. **快手** — Open API available (open.kuaishou.com); covered by dreammis/social-auto-upload
13. **喜马拉雅** — Open platform API; light anti-bot; but album-based structure requires pre-setup

### Critical Format Quirks Confirmed (from user requirements)

| User-claimed quirk | Verification status | Notes |
|---|---|---|
| B站, 虎嗅 require 横屏 cover (landscape 16:9) | ✅ **CONFIRMED** | B站: 1146×717 (16:9); 虎嗅: 800×450 (16:9) |
| 36kr, 腾讯新闻 do secondary cropping of cover | ⚠️ **PARTIALLY CONFIRMED** | 36kr: cropping behavior reported but exact dimensions unknown (needs live testing). 腾讯新闻 is part of企鹅号 distribution — cover gets cropped per Tencent platform (腾讯新闻 vs 腾讯视频 vs QQ看点) |
| 36kr allows max 5 tags | ⚠️ **NOT DIRECTLY VERIFIED** | Commonly cited in 3rd-party docs; official misopen is JS-only so could not directly confirm. Treat as 5 max for safety |
| B站 allows 10 tags | ✅ **CONFIRMED** | Multiple sources confirm 10-tag max |
| 微博 tags use `#话题#` (double #) | ✅ **CONFIRMED** | Verified in academic research (PMC7856455) — "topics on Weibo are confined in double hashtags one at the beginning and one at the end" |
| 小红书 9-grid image limitation for image posts, but for video? | ✅ **CONFIRMED**: 9-grid applies to IMAGE posts only; video is single video per post (no multi-video grid). Mixed image+video not supported. |
| 抖音 vertical video preferred, max 1080P recommended | ⚠️ **PARTIALLY CONFIRMED** | Vertical 9:16 IS preferred. Max resolution: actually up to 4K is supported, but 1080P is the sweet spot for file size / quality balance. Multiple sources recommend 1080×1920 |

### Newly Discovered Quirks (not in user list)

| Platform | Quirk |
|---|---|
| B站 | Drafts auto-delete after 10 days — cannot be long-term storage |
| B站 | Game/Animation categories allow 2000字 descriptions (vs 250字 default) |
| B站 | 二次压制 (re-encoding) is mandatory for all uploads; pre-encode to ≤6000kbps avg bitrate |
| 视频号 | H.265 video upload via Chrome fails — must use iPhone or Mac Safari |
| 视频号 | Cover 6:7 ratio shares to朋友圈 cropped to 1:1 — design for both |
| 抖音 | Title 55字 limit INCLUDES #话题 hashtags — major budget constraint |
| 抖音 | 6类必选标签 mandated by中央网信办 (2025) — AI生成/虚构演绎/时事信息 etc. |
| 抖音 | 共创投稿 requires 7000+ followers, max 4/month |
| 快手 | 原创标签 must be explicitly toggled before publish (not auto-detected) |
| 快手 | Different crop ratios on different pages (发现页/关注页/搜索页) — design cover with center safe zone |
| 支付宝 | Multiple duration limits by entry: 拍摄60s, 导入5min, PC30min |
| 支付宝 | Has the BEST official Open API of all 13 platforms — preferred for legitimate automation |
| 小红书 | creator.xiaohongshu.com GeoIP-blocked overseas — use creator.rednote.com |
| 小红书 | A/B cover testing: upload 1 default + 3 PK covers; system auto-picks best CTR after 10h |
| 小红书 | Long文 feature (2025 internal test): 6000字 max正文 with auto-pagination |
| 微博 | 6字 MINIMUM title length (rare — most platforms have max, not min) |
| 微博 | Mixed image+video post: up to 9 images+video mix in one微博 (since client 12.11.4) |
| 微博 | PC vs mobile file size gap: 15GB PC vs 4GB mobile (huge difference) |
| 企鹅号 | Browser-specific file size: Chrome = 4GB, other browsers = 500MB |
| 企鹅号 | Daily limits by等级: 一级/二级 = 3 posts, 三级+ = 5 posts (video max 3/day) |
| 企鹅号 | RSS sync (from微信公众号 or custom RSS) doesn't count toward daily limit |
| 虎嗅 | Article submission only accepts微信公众号 link — cannot paste article content directly |
| 虎嗅 | Editorial review mandatory — editors can modify content |
| 36氪 | Author认证 required first (身份证, 微信号, 认证辅助信息); 20+ original articles recommended |
| 36氪 | misopen is fully JS SPA — needs headless browser, no static HTML available |
| 喜马拉雅 | Album structure mandatory — cannot publish standalone content |
| 喜马拉雅 | 1400×1400 album cover required for Apple Podcast RSS distribution |
| 百家号 | 垂直度 score — must stay in same category for better recommendation |
| 百家号 | 申请原创标签 for 3x revenue multiplier (separate application) |

### API Availability Summary

| Platform | Official Open API | OAuth | Reverse-eng API | Cookie-based |
|----------|-------------------|-------|-----------------|--------------|
| 微信视频号 | ❌ No (公众号 has draft API but not视频号) | ❌ No | ❌ Limited | ✅ |
| 哔哩哔哩 | Limited (open.bilibili.com — partner only) | ❌ No | ✅ SocialSisterYi/bilibili-API-collect | ✅ |
| 企鹅号 | ✅ RSS sync + Open API for partners | Limited | ✅ | ✅ |
| 腾讯视频 | ❌ Partner only | ❌ No | ❌ Limited | ✅ |
| 微博视频 | ✅ Read-only (open.weibo.com) | ✅ OAuth2.0 (read) | ✅ | ✅ |
| 喜马拉雅 | ✅ open.ximalaya.com | ✅ | ✅ | ✅ |
| 百家号 | ✅ Has挂载API + 集简云 integration | Partner only | ✅ lyungy/auto_baijiahao | ✅ |
| 虎嗅 | ❌ No | ❌ No | ❌ No | ✅ (but editorial review) |
| 36氪 | ❌ No | ❌ No | ❌ No | ✅ (but editorial review) |
| 抖音 | Limited (developer.open-douyin.com — read + 小程序) | ✅ (read) | ✅ Multiple (A2Data/auto_douyin, dreammis) | ✅ |
| 快手 | ✅ open.kuaishou.com (chunked upload) | ✅ | ✅ | ✅ |
| 支付宝生活号 | ✅ **Best documented** (opendocs.alipay.com) | ✅ | ✅ | ✅ |
| 小红书 | ❌ No | ❌ No | ✅ dreammis/social-auto-upload | ✅ |

### Open-Source Automation Coverage

The `dreammis/social-auto-upload` project (14k stars) covers 6 of the 13 platforms:
- ✅ 抖音 (full support, primary focus)
- ✅ Bilibili (uses `biliup` integration)
- ✅ 小红书 (browser automation; uses creator.rednote.com fallback)
- ✅ 快手 (browser automation)
- ✅ 视频号 (via tencent_uploader)
- ✅ 百家号 (browser automation)

NOT covered by social-auto-upload (7 platforms):
- ❌ 企鹅号 (QQ Shizi)
- ❌ 腾讯视频
- ❌ 微博视频
- ❌ 喜马拉雅
- ❌ 虎嗅 (editorial-curated; not automatable)
- ❌ 36氪 (editorial-curated; not automatable)
- ❌ 支付宝生活号 (use official API instead)

For the 7 not-covered platforms, custom implementations would need to be built. Of these, **支付宝** has the best official API, **喜马拉雅** has open API, **企鹅号** has RSS sync, **微博** has read-only OAuth — the rest require browser automation with anti-bot mitigations.

---

## Strategic Recommendations for Multi-Platform Distribution

Based on this research, prioritize platforms as follows:

### Tier 1 (Best automation support — do these first)
1. **支付宝生活号** — Official Open API, no CAPTCHA on publish, well-documented
2. **哔哩哔哩** — `biliup` tool handles WBI signing; well-documented reverse-eng
3. **抖音** — dreammis/social-auto-upload mature; primary focus of community
4. **快手** — Official Open API + social-auto-upload coverage

### Tier 2 (Covered by social-auto-upload, but with caveats)
5. **小红书** — Patchright required; GeoIP issues; use creator.rednote.com
6. **百家号** — Browser automation works; daily limits apply
7. **微信视频号** — H.265 caveats; WeChat device fingerprint

### Tier 3 (Need custom implementation)
8. **企鹅号** — RSS sync is easiest path; or cookie-based browser automation
9. **微博视频** — Double-# tag conversion; 6字 title minimum
10. **腾讯视频** — Long-form content focus; album structure
11. **喜马拉雅** — Album-based; use open API

### Tier 4 (Editorial-curated; cannot truly automate)
12. **虎嗅** — Must submit via微信公众号 link; editor review
13. **36氪** — Author认证 + editor review; misopen is JS SPA

---

## Sources

- 微信视频号: https://findeross.weixin.qq.com/cgi-bin/mmfindernodelivecrmwebbroker-bin/helper-center/pages/Yhdpjlq2RIkcmnQu
- 哔哩哔哩: https://member.bilibili.com (creator backend); https://github.com/SocialSisterYi/bilibili-API-collect
- 企鹅号: https://om.qq.com/assets/Guide.html (official入驻指引)
- 腾讯视频: https://mp.v.qq.com (creator platform)
- 微博视频: https://kefu.weibo.com/faqdetail?id=21503 + https://kefu.weibo.com/faqdetail?id=20938 + https://kefu.weibo.com/faqdetail?id=20995
- 喜马拉雅: https://www.ximalaya.com/helper/questionPage?questionId=76 + https://open.ximalaya.com/doc/detailApi
- 百家号: https://baijiahao.baidu.com + https://www.jijyun.cn/help/detail/124
- 虎嗅: https://m.huxiu.com/contribute/video_article + https://m.huxiu.com/contribute/article
- 36氪: https://misopen.36kr.com + https://www.36kr.com/external-author-apply
- 抖音: https://creator.douyin.com + https://blog.csdn.net/Tzlove20200829/article/details/136816809
- 快手: https://cp.kuaishou.com + https://www.kuaishou.com/help/feedback/4000 + https://open.kuaishou.com/platformDocs
- 支付宝生活号: https://opendocs.alipay.com/b/03at8r + https://opendocs.alipay.com/b/03awbp + https://opendocs.alipay.com/b/03al0z + https://opendocs.alipay.com/p/01v5or
- 小红书: https://creator.xiaohongshu.com/publish/publish + https://github.com/dreammis/social-auto-upload/issues/226
- Multi-platform guide: https://www.secaiyun.com/docs/short-video-cover-size-guide-2026-05-23.html
- Automation framework: https://github.com/dreammis/social-auto-upload (14k stars)
- Bilibili API reference: https://github.com/SocialSisterYi/bilibili-API-collect
- Anti-bot analysis: https://nanmicoder.github.io/MediaCrawler
