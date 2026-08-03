# Existing Multi-Platform Publishing Tools Survey

> Research date: 2026-08-03
> Goal: find reusable wheels for batch / one-click publishing videos to 13 Chinese self-media platforms instead of building from scratch.
> Target platforms: 微信视频号, 哔哩哔哩 (Bilibili), 企鹅号/腾讯内容开放平台, 腾讯视频, 微博视频, 喜马拉雅, 百家号, 虎嗅, 36氪, 抖音创作者, 快手, 支付宝生活号, 小红书.

## Summary

- **Total tools surveyed:** 19 open-source projects + 5 SaaS / commercial products + 4 reverse-engineered API collections.
- **Best candidate:** `dreammis/social-auto-upload` (~14k stars, MIT, Python+Playwright, covers 6 of our 13 platforms with mature CLI + skill integration).
- **Strongest complementary tool:** `hanliang97/MatrixMedia` (Electron GUI + CLI + MCP server, GPL-2.0, 8 platforms fully automated including 头条 and 番茄视频).
- **Best browser extension:** `leaperone/MultiPost-Extension` (2.9k stars, Apache-2.0, 10+ Chinese platforms).
- **Recommendation:** Fork `social-auto-upload` as the primary engine, lift its platform adapters into a shared core, then incrementally add adapters for the 5 missing platforms (微博视频, 腾讯视频, 喜马拉雅, 虎嗅, 36氪, 支付宝生活号, 企鹅号). Do **not** rely on reverse-engineered unofficial APIs (legal risk + brittle), the bilibili-API-collect takedown is a strong warning.

## Detailed Tool Inventory

### Tool 1: dreammis/social-auto-upload

- URL: https://github.com/dreammis/social-auto-upload
- Stars: ~14,000 (Forks: 2.4k, 296 commits as of Jul 2026)
- Last updated: Jul 31, 2026 (active; maintainer announced a refactoring sprint in March 2026 and is delivering on it)
- Tech: Python 3 + Playwright (migrating to `patchright` for stealth); Flask backend + Web frontend retained for legacy; CLI entry `sau`; uv-based env; skills/ folder for Claude Code / OpenClaw / Codex integration; Docker support.
- Platforms covered (intersect with our 13):
  - ✅ 抖音 (login + video + image-text + scheduled + CLI + skill)
  - ✅ Bilibili (login + video + scheduled + CLI + skill; uses `biliup` auto-downloaded at runtime)
  - ✅ 小红书 (login + video + image-text + scheduled + CLI + skill)
  - ✅ 快手 (login + video + image-text + scheduled + CLI + skill)
  - ✅ 视频号 (login + video + scheduled; no image-text, no CLI yet — uses `tencent_uploader`)
  - ✅ 百家号 (login + video + scheduled; no image-text, no CLI)
  - ❌ 微博视频, 腾讯视频, 喜马拉雅, 虎嗅, 36氪, 支付宝生活号, 企鹅号 — NOT covered
  - Bonus: TikTok + YouTube (browser automation; YouTube supports playlist + visibility public/unlisted/private)
- Draft support: Yes — platforms support "定时发布" (scheduled publish) which effectively persists the upload as a draft at the platform; image-text + video drafts.
- Cookie / login mechanism: Each platform has its own login module. Most use QR-code scan in a real terminal (or `qrcode.png` if terminal doesn't render), then persist cookies under an `account_name` directory. Multi-account supported; cookies loaded into Playwright context per run.
- Cover image handling: Adapters set cover when the platform form has a cover field; bili has a dedicated cover-CLI workflow (PR #243). Documentation does not describe automatic cropping for 横屏/竖屏 mismatch — caller is expected to provide platform-appropriate cover.
- Tag count handling: Tags are passed as `--tags` (comma or space separated depending on platform). Per-platform limits enforced inside each uploader's `set_tags` routine; some platforms (e.g. 微信视频号) only accept a short title and description, no tags.
- License: MIT (stated in README; an Issue #236 notes the LICENSE file was missing but maintainer confirmed MIT intent).
- Known limitations / issues:
  - 抖音 occasionally requires SMS 二次验证; script reads `verify_code.txt` for headless runs.
  - 视频号 and 百家号 do not yet have CLI/Skill/image-text support.
  - Platform UIs change frequently; selectors need periodic fixing (see Issue list — 抖音 author declaration prompt not handled, B站 cover fix, etc.).
  - Maintainer notes 9k+ star project, "重构" ongoing, sometimes slow updates.
- Pros: Largest community, MIT, clean CLI, skill integration for AI agents, Docker, Windows batch script, well-documented.
- Cons: No coverage for 微博视频, 腾讯视频, 喜马拉雅, 虎嗅, 36氪, 支付宝生活号, 企鹅号. Video-number/Baijiahao adapters are second-class. No native multi-account concurrency (one account_name per process).
- Verdict for our use case: **Primary fork candidate.** It covers 6/13 platforms out-of-the-box and its adapter architecture (one folder per platform under `uploader/`) is the cleanest extension model we found.

### Tool 2: hanliang97/MatrixMedia (矩媒)

- URL: https://github.com/hanliang97/MatrixMedia
- Stars: ~270 commits, active development (last commit Jul 27, 2026)
- Last updated: Jul 27, 2026
- Tech: Electron + Vue.js GUI + Node.js CLI (`matrixmedia cli ...`) + MCP server (stdio). Uses puppeteer for headless 抖音 login; other platforms reuse GUI session partition (`persist:<phone><platform>`).
- Platforms covered (intersect with our 13):
  - ✅ 抖音, 快手, 百家号, B站, 头条号, 视频号, 小红书, 番茄视频 (8 platforms fully automated)
  - ❌ 微博视频, 腾讯视频, 喜马拉雅, 虎嗅, 36氪, 支付宝生活号, 企鹅号 — NOT covered
- Draft support: Yes — supports 定时发布 via MCP `publish_video` tool (max 35 minutes scheduling window).
- Cookie / login mechanism: GUI login one-time per platform; CLI and MCP reuse same session partition; CLI also supports QR-code login for 抖音 and 视频号.
- Cover image handling: Accepts cover image path; auto-upload per platform.
- Tag count handling: Tags passed via CLI args; per-platform limits enforced inside adapters.
- License: GPL-2.0 (note: copyleft, may restrict closed-source derivative distribution).
- Known limitations:
  - 小红书 increasingly detects Electron-built browsers ("AI 托管" warning); maintainer added "use real Chrome" mode to bypass.
  - GUI is required for initial login on all non-抖音/视频号 platforms.
  - HTTP API on `127.0.0.1:30088/publish` requires GUI running.
- Pros: 8 platforms automated, MCP server for Claude Desktop/Cursor/Cline, HTTP API for external orchestration, real-Chrome mode for 小红书 evasion.
- Cons: GPL-2.0 copyleft, requires Electron GUI for login flow, no coverage for our long-tail platforms.
- Verdict for our use case: **Strong secondary reference.** Borrow the MCP/HTTP-API design and the real-Chrome evasion pattern. Cannot directly embed due to GPL.

### Tool 3: leaperone/MultiPost-Extension

- URL: https://github.com/leaperone/MultiPost-Extension
- Stars: 2,900 (Forks: 329, 44 releases)
- Last updated: Aug 1, 2026 (v1.4.5)
- Tech: TypeScript browser extension (Manifest V3) + RESTful API + Extension API for web apps. pnpm + biome + tailwind.
- Platforms covered (intersect with our 13):
  - ✅ 小红书, 抖音 (video + image-text), 微博, 知乎, B站 (专栏 — article only, not video)
  - ❌ 视频号, 快手, 百家号, 腾讯视频, 喜马拉雅, 虎嗅, 36氪, 支付宝生活号, 企鹅号
  - Total supported platforms: 10+ (including international ones)
- Draft support: Yes — content lands as draft by default (manual publish click).
- Cookie / login mechanism: Uses the user's existing browser login session — no API keys, no separate login. Reads cookies directly in browser context.
- Cover image handling: Image upload handled by adapter; format conversions not explicitly described.
- Tag count handling: Per-platform adapter logic.
- License: Apache-2.0.
- Known limitations:
  - Article-focused; video support is limited to platforms that accept video through web editor (抖音 image-text, 小红书 image-text). True video uploads to 视频号/B站 are NOT supported.
  - Requires user to keep browser open during publish.
- Pros: 2.9k stars, very active, Apache-2.0, two API surfaces (Extension + RESTful), i18n, no API key needed.
- Cons: Not a video-first tool. Doesn't touch 视频号, 快手, B站 video uploads.
- Verdict for our use case: **Reference for browser extension architecture and image-text publishing.** Not the main engine for video.

### Tool 4: xiaoliangliang/auto-publish

- URL: https://github.com/xiaoliangliang/auto-publish
- Stars: 14 (very new — first release May 28, 2026)
- Last updated: Jun 7, 2026
- Tech: Chrome MV3 extension (vanilla JS), npm test validation.
- Platforms covered (intersect with our 13):
  - ✅ 抖音创作者中心, 小红书创作服务平台, 视频号助手, B站创作中心 (video upload + form fill)
  - + YouTube Studio
  - ❌ all others
- Draft support: No — explicitly "upload + fill form + human confirms publish", no draft persistence.
- Cookie / login: User logs in to each platform in their own browser; extension runs in same context.
- Cover image handling: Only 竖版封面 (vertical) supported; 横版 not supported.
- Tag count handling: Tags as space-separated string; per-platform adapter handles truncation.
- License: MIT.
- Known limitations:
  - No auto-publish (intentional — requires human to click publish).
  - No scheduled publish, no multi-account, no horizontal cover, no advanced platform fields.
  - B站 only fills title/cover/tags, not description.
  - DOM selectors break when platforms update UI; adapters use placeholder/text fuzzy matching.
- Pros: MIT, minimal, transparent, good starting point if you want a Chrome extension.
- Cons: New, low star count, no draft, no scheduled, only 4 of our platforms.
- Verdict for our use case: **Reference for Chrome MV3 short-video automation.** Consider as inspiration for a "human-in-the-loop" mode.

### Tool 5: wechatsync/Wechatsync (文章同步助手)

- URL: https://github.com/wechatsync/Wechatsync
- Stars: ~300+ commits, last commit May 27, 2026
- Last updated: May 27, 2026
- Tech: TypeScript, pnpm monorepo (`packages/extension`, `packages/cli`, `packages/mcp-server`, `packages/core`). Chrome MV3 extension + MCP server + CLI.
- Platforms covered (intersect with our 13):
  - ✅ 微信公众号, 微博 (article), 小红书 (article), B站专栏 (article), 百家号 (article), 抖音图文
  - 29+ platforms total (mostly article / image-text)
  - ❌ None of our pure-video platforms (视频号 video, 腾讯视频, 快手 video, etc.)
- Draft support: Yes — "草稿优先" is the default mode for every platform; user must manually click publish in each platform's draft box.
- Cookie / login: Uses user's existing browser cookies, no separate auth.
- Cover image handling: Auto-extracts cover from article; image auto-reupload to target platform.
- Tag count handling: Per-adapter.
- License: GPL-3.0.
- Known limitations:
  - Article-first; video coverage is minimal (only 抖音图文).
  - Adapters privatized via git submodule (Mar 2026) — limited visibility into per-platform API calls.
- Pros: 29+ platform adapters, MCP integration, mature CLI.
- Cons: GPL-3.0 (copyleft), not video-focused, adapter source partially privatized.
- Verdict for our use case: **Reference for MCP integration pattern and "draft-first" UX.** Not directly usable for video.

### Tool 6: dorisoy/ShortVideo.AutoPublisher

- URL: https://github.com/dorisoy/ShortVideo.AutoPublisher
- Stars: ~157
- Last updated: Apr 13, 2026
- Tech: .NET 8.0 WPF + Microsoft.Playwright 1.40 + SQLite/Dapper + Polly + SixLabors.ImageSharp + Serilog. WPF-UI 3.0.4 (Fluent Design, MVVM). OpenClaw AI agent integration.
- Platforms covered (intersect with our 13):
  - ✅ 抖音, 小红书, 百家号, 微信视频号, 今日头条 (5 platforms)
  - ❌ B站, 快手, 微博视频, 腾讯视频, 喜马拉雅, 虎嗅, 36氪, 支付宝生活号, 企鹅号
- Draft support: Mentions "CookieSession" and "PublishTask" entities; scheduling supported via `PublishTaskScheduler`.
- Cookie / login: `CookieSessionService` persists cookies per platform/account in SQLite.
- Cover image handling: `CoverImage` entity + `SixLabors.ImageSharp` for image processing (cropping). Most sophisticated cover handling of all surveyed tools.
- Tag count handling: Per-agent (DouyinAgent, XiaohongshuAgent, etc.).
- License: MIT.
- Known limitations: Windows-only (WPF), .NET 8.0 runtime required, no Linux/Mac GUI.
- Pros: Clean layered architecture (Domain / Infrastructure / Services / ViewModels), MIT, AI agent integration, image processing for cover cropping built-in.
- Cons: Windows-only, .NET ecosystem limits contributions, only 5 of our 13 platforms.
- Verdict for our use case: **Strong architectural reference.** Borrow the layered design and `CoverImage` cropping concept, but the .NET/WPF stack is a non-starter for cross-platform tooling.

### Tool 7: BetaStreetOmnis/xhs_ai_publisher

- URL: https://github.com/BetaStreetOmnis/xhs_ai_publisher
- Stars: ~141 commits, active
- Last updated: Jun 28, 2026
- Tech: Python 3.8+ + PyQt5 desktop UI + FastAPI service + Playwright; Nuitka release build; supports OpenAI/Claude/Ollama for content generation.
- Platforms covered: 小红书 ONLY (single-platform tool).
- Draft support: Yes — preview before publish, 定时发布 (无人值守) supported.
- Cookie / login: Phone login with country code, manual fallback for risk control, can import login state from system Chrome for SMS/scan bypass.
- Cover image handling: Built-in 营销海报 / 促销横幅 / 产品展示 templates, generates cover + multi-page content images locally.
- Tag count handling: AI-generated tag recommendations.
- License: Apache-2.0.
- Pros: Very mature 小红书 automation, multi-account, AI integration, hot-topic scraping from 微博/百度/头条/B站.
- Cons: Only 小红书.
- Verdict for our use case: **Use as the canonical 小红书 adapter reference** — particularly its login-state-import feature for handling 风控 (risk control) bypass.

### Tool 8: wordflowlab/pubcast

- URL: https://github.com/wordflowlab/pubcast
- Stars: small (25 commits)
- Last updated: Dec 2, 2025 (v0.2.3)
- Tech: Tauri 2.0 (Rust + React + TypeScript) + Playwright Node.js sidecar + Stealth反检测 + AES-256-GCM + Argon2id.
- Platforms covered: 微信公众号 + 小红书 (early stage; designed for extension).
- Draft support: Yes — content cached in `contents` table, `distribution_tasks` and `publish_jobs` tables orchestrate draft/publish.
- Cookie / login: Account management with system Keychain for password storage.
- Cover image handling: Not specifically documented.
- Tag count handling: Not specifically documented.
- License: Not specified in README (need to check repo).
- Pros: Beautiful architecture (Rust backend + SQLite + Playwright sidecar), built for extension.
- Cons: Only 2 platforms implemented, low activity.
- Verdict for our use case: **Architectural inspiration for a Rust+Tauri desktop app** if we go that route, but not directly usable.

### Tool 9: BadKid90s/Spreado

- URL: https://github.com/BadKid90s/Spreado
- Stars: ~252 commits, active (last commit Aug 2, 2026)
- Last updated: Aug 2, 2026
- Tech: Python 3.9+ + uv + Playwright; plugin architecture under `plugins/`; binary distribution (Windows/macOS/Linux x64 + ARM64); AI agent skill package.
- Platforms covered (intersect with our 13):
  - ✅ 抖音, 小红书, 快手, 腾讯视频号 (4 platforms)
  - ❌ B站, 微博视频, 腾讯视频, 喜马拉雅, 虎嗅, 36氪, 支付宝生活号, 企鹅号, 百家号
- Draft support: Yes — `--schedule 2` (hours from now) or `--schedule "2024-12-31 18:00"` for absolute time.
- Cookie / login: `spreado login <platform>` opens browser, QR/phone scan, auto-saves cookies under `cookies/<platform>/default/account.json`. Multi-account via `--cookies` path.
- Cover image handling: `--cover thumbnail.jpg` per platform.
- Tag count handling: `--tags "tag1,tag2,tag3"` (comma-separated); per-platform enforcement inside adapter.
- License: Apache-2.0.
- Pros: Apache-2.0, plugin architecture is genuinely extensible ("new platform → drop into plugins/ → auto-discovered"), binary distribution for non-Python users, parallel upload `--parallel 4`.
- Cons: Only 4 of our platforms, smaller community than social-auto-upload.
- Verdict for our use case: **Strong reference for plugin architecture and CLI ergonomics.** Could potentially be used as the framework and have additional platform adapters contributed.

### Tool 10: SamCheng0717/video-pusher

- URL: https://github.com/SamCheng0717/video-pusher
- Stars: 52 commits, active
- Last updated: Mar 16, 2026
- Tech: Python + uv + Playwright; designed as Claude Code / OpenClaw Skills (one folder per platform under `skills/`).
- Platforms covered (intersect with our 13):
  - ✅ 抖音, 小红书, 微信视频号
  - + Threads, Instagram
  - ❌ all others
- Draft support: No — semi-automatic ("script fills content, you click publish, close browser to advance to next platform").
- Cookie / login: Local `profile/` session storage; `vp-accounts.py login <group> <platform>` opens browser, login once, reuse forever.
- Cover image handling: Per-platform via `--file` arg.
- Tag count handling: `--tags "tag1 tag2"` (space-separated), auto-adds `#` prefix.
- License: Not specified (need to check).
- Pros: Skill-based design fits AI-agent workflow naturally, supports account groups.
- Cons: Only 3 of our platforms, semi-automatic only.
- Verdict for our use case: **Reference for skill-based orchestration and account-group concept.**

### Tool 11: kebenxiaoming/matrix

- URL: https://github.com/kebenxiaoming/matrix
- Stars: 937 (Forks: 198, 30 commits)
- Last updated: older (commits not dated in scrape)
- Tech: Python + Playwright + MySQL + Redis + supervisor. Queue-based: `user_queue_login.py` (type 1=抖音, 2=视频号, 3=小红书, 4=快手) + `publish_video_queue.py`.
- Platforms covered (intersect with our 13):
  - ✅ 抖音, 视频号, 小红书, 快手 (4 platforms)
  - ❌ all others
- Draft support: Multi-account queue management; per-account cookie persistence.
- Cookie / login: QR code stored in Redis as base64; SMS verification handled via cache; cookies stored per-platform in `account/` directories.
- Cover image handling: Not specifically documented.
- Tag count handling: Not specifically documented.
- License: Apache-2.0.
- Pros: Production-grade queue architecture (MySQL + Redis + supervisor), 937 stars suggest real usage.
- Cons: Heavy infra requirements (MySQL + Redis + supervisor), less actively maintained, smaller platform set than social-auto-upload.
- Verdict for our use case: **Reference for production queue architecture** if we need to scale to hundreds of accounts.

### Tool 12: Laihiujin/SynapseAutomation

- URL: https://github.com/Laihiujin/SYNAPSEAUTOMATION
- Stars: 66 commits
- Last updated: recent
- Tech: FastAPI + Next.js + Celery/Redis + Playwright + Electron. HermesAgent AI integration.
- Platforms covered (intersect with our 13):
  - ✅ 抖音, 快手, 小红书, 视频号, B站 (5 platforms)
  - ❌ all others; TikTok planned for international
- Draft support: Yes — `distribution_tasks` table with scheduling + retry.
- Cookie / login: Account binding via QR scan; status monitoring.
- Cover image handling: Not specifically documented.
- Tag count handling: AI auto-completes titles/tags.
- License: Apache-2.0.
- Pros: Full "编-投-管-回" loop (plan-publish-manage-recycle), data recovery for 抖音 + B站, Docker one-shot deploy.
- Cons: Heavy stack (5 services), only 5 platforms.
- Verdict for our use case: **Reference for the full SaaS-style backend architecture** if we want to build a managed product.

### Tool 13: iamtornado/playwright-automation

- URL: https://github.com/iamtornado/playwright-automation
- Stars: 18 commits
- Last updated: undated
- Tech: Python + Playwright + 豆包AI / Gemini. Article-focused (钉钉文档 → multi-platform).
- Platforms covered (intersect with our 13):
  - ✅ 微信公众号, 知乎, CSDN, 51CTO, 博客园, 抖音 (image-text), 快手 (image-text), 小红书 (image-text), B站 (专栏)
  - ❌ Pure video uploads NOT supported
- Draft support: Yes for 微信公众号 (saves as draft, manual publish); direct publish for others.
- License: Not specified.
- Pros: AI-powered cover generation, content summarization, tag generation, multi-platform format adaptation (120字摘要 for 微信公众号, 1000字限制 for 抖音/小红书).
- Cons: Article-focused, small project.
- Verdict for our use case: **Reference for AI-assisted content adaptation** between platforms with different length limits.

### Tool 14: profullstack/social-poster

- URL: https://github.com/profullstack/social-poster
- Stars: 11 commits
- Last updated: Aug 1, 2026
- Tech: Node.js + Puppeteer + pnpm; AI content generation via OpenAI.
- Platforms covered: International focus — X (Twitter), TikTok, Pinterest, LinkedIn, Reddit, Facebook, Hacker News.
- License: Not explicitly stated (check repo).
- Pros: Clean CLI, session management, dry-run mode, AI integration.
- Cons: Zero coverage of our Chinese platforms.
- Verdict for our use case: **Not applicable** to Chinese platforms; mentioned only for completeness.

### Tool 15: huyangnl/VidiBot (commercial / closed source)

- URL: https://github.com/huyangnl/VidiBot (landing) + https://www.vidibot.com
- License: **Closed source, commercial** (membership/subscription model).
- Tech: Real browser automation + fingerprint browser integration (BitBrowser, Hubstudio, VMlogin).
- Platforms covered: YouTube, TikTok, Facebook, VK, 视频号, B站, 抖音, 小红书 (broad coverage claimed).
- Pros: Mature commercial product, fingerprint browser integration for evasion, supports 300+ file batch upload.
- Cons: Paid, closed-source, no API for programmatic integration.
- Verdict for our use case: **Not usable** for an open-source / forkable project; benchmark only.

### Tool 16: SaaS products (蚁小二, 融媒宝, 易撰, 简媒, 新媒宝)

- **蚁小二** (https://www.yixiaoer.cn): 60+ 自媒体 platforms, multi-account management, AI 视频 creation, browser RPA publishing, network region setting. Has Chrome extension "蚁小二浏览器发布助手". **No public open API** for third-party integration — it's a managed SaaS.
- **融媒宝** (https://www.17van.com / https://www.rmeibao.com): 30-50+ platforms, 1000+ account management, AI视频混剪. **No public open API** documented.
- **易撰** / **简媒** / **新媒宝**: Similar SaaS, all closed-ecosystem, none expose open APIs for batch video publishing.
- **CreBee** (mentioned in comparisons): Adds API对接 and Skill/MCP接入 — possibly more open than the legacy SaaS, but still commercial.
- Verdict: **None of these SaaS products expose a usable open API** for our use case. Their value is benchmarking UX and platform-coverage claims (e.g., 蚁小二 claims 60+ platforms — but most are article platforms, the video platforms overlap heavily with what `social-auto-upload` already covers).

### Tool 17: SocialSisterYi/bilibili-API-collect (archived — legal warning)

- URL: https://github.com/SocialSisterYi/bilibili-API-collect (now archived)
- Status: **Archived January 2026** after maintainer received 律师函 (lawyer's letter) from B站 alleging "通过技术手段对哔哩哔哩平台非公开的API接口及其调用逻辑、参数结构、访问控制及安全认证机制进行系统性收集、整理".
- Tech: Pure documentation (markdown) of reverse-engineered B站 APIs.
- License: N/A (documentation).
- Verdict: **Critical legal precedent.** Reverse-engineered API collections for Chinese platforms face takedown risk. This is the strongest argument for using **cookie-based browser automation** (which performs the same actions a human user would) rather than calling reverse-engineered internal APIs.

### Tool 18: zsmhub/wx-channels-sdk + dsxksss/wx_video_sdk

- URLs: https://github.com/zsmhub/wx-channels-sdk (Go), https://github.com/dsxksss/wx_video_sdk (Python)
- Tech: Reverse-engineered 微信视频号 APIs.
- Platforms: 视频号 only.
- License: Not specified.
- Verdict: Useful as **reference for 视频号 internal API structure**, but risky to depend on (same legal precedent as bilibili-API-collect).

### Tool 19: NanmiCoder/MediaCrawler (reference for cookie/login techniques)

- URL: https://github.com/NanmiCoder/MediaCrawler
- Stars: very high (popular crawler)
- Tech: Playwright + JS expression signature capture (no JS reverse engineering needed) + login state persistence.
- Platforms: 小红书, 抖音, 快手, B站, 微博, 贴吧, 知乎 (data crawling, NOT publishing).
- Verdict: **Not a publishing tool** but its login-state-reuse + CDP-mode + JS expression technique is the gold standard for evading 风控. Borrow its patterns.

## Key Findings for Feasibility

### Platforms with NO open-source coverage at all (must build from scratch)

Of our 13 target platforms, the following have **zero usable open-source publishing code** as of August 2026:

1. **喜马拉雅 (Ximalaya)** — only downloaders exist (`xmlyfetcher`, `musicdl`); no upload/publish tool found. Will need a custom Playwright adapter against `studio.ximalaya.com/opus`.
2. **虎嗅 (Huxiu)** — no automation tools found. Will need a custom Playwright adapter against `www.huxiu.com/contribute.html`. Risk: 虎嗅 has captcha puzzle on entry (we hit it during research).
3. **36氪 (36kr)** — no automation tools found. Will need a custom Playwright adapter against `misopen.36kr.com`. Risk: 36kr has 滑块 captcha ("按住左边按钮拖动完成上方拼图").
4. **支付宝生活号 (Alipay)** — Alipay has official 生活号 OpenAPI (`opendocs.alipay.com`) but it's targeted at 商家 (merchants) with 企业认证. For individual creators, browser automation against `c.alipay.com/page/portal/home` is the only path; no open-source tool does this.
5. **腾讯视频 (Tencent Video)** — `mp.v.qq.com` creator platform has no open-source automation. The `cc.v.qq.com` 创作平台 is a separate long-video platform with manual onboarding only.
6. **企鹅号 / 腾讯内容开放平台 (QQ Shizi)** — `om.qq.com` has RSS sync and an open developer center (`open.om.qq.com`) for content sites, but no third-party Python/Node publishing library exists. Will need browser automation.
7. **微博视频 (Weibo)** — `weibo.com/upload/channel` has no dedicated video upload automation in any surveyed tool. Wechatsync covers Weibo articles only; `hjb2722404/weibo-video-upload` is a tiny Node/Puppeteer gist from years ago. Will need a fresh adapter.

**Bottom line: 7 of 13 platforms have no reusable open-source code.** These will require building new Playwright adapters from scratch.

### Platforms with automation but requiring reverse-engineered APIs that break often

- **Bilibili**: `biliup` (used by social-auto-upload) is the most stable approach — it's an unofficial upload library that mimics the web client. The SocialSisterYi/bilibili-API-collect documentation was forcibly archived in January 2026 after B站's lawyer letter. **Recommendation: use biliup or pure browser automation; do NOT call documented reverse-engineered APIs.**
- **微信视频号**: `zsmhub/wx-channels-sdk` and `dsxksss/wx_video_sdk` exist but are small projects with no legal review. Browser automation (`channels.weixin.qq.com/platform`) via Playwright is safer and more stable.
- **抖音 + 快手**: Both have **official OpenAPI** (`developer.open-douyin.com`, `open.kuaishou.com`) for content publishing, but access requires:
  - Registered developer account
  - 企业认证 (often)
  - Capacity application (申请权限) — frequently denied or slow
  - User OAuth flow per account
  - Quota limits
  For most creators, browser automation remains the practical choice. The official OpenAPI is viable only if the user has an approved developer account.

### Cookie-based browser automation is the only realistic approach for most platforms

The survey confirms this conclusively:

1. **Every actively maintained multi-platform tool uses Playwright/Puppeteer + cookie persistence**, not official APIs. (social-auto-upload, MatrixMedia, Spreado, MultiPost-Extension, ShortVideo.AutoPublisher, SynapseAutomation, video-pusher, xhs_ai_publisher, kebenxiaoming/matrix, iamtornado/playwright-automation).
2. **No Chinese platform except 抖音/快手 offers a usable public OpenAPI** for arbitrary creators. The 腾讯内容开放平台 developer center exists but is gated.
3. **Reverse-engineered API collections face legal takedown** (bilibili-API-collect precedent).
4. **Cookie-based automation is technically equivalent** to a human user clicking through the web UI, which is the legal ToS-compliant path. The risk is platform-side bot detection (风控), not legal action against the user.
5. **风控 evasion techniques** that work, borrowed from MediaCrawler and xhs_ai_publisher:
   - CDP mode: connect Playwright to a real Chrome instance instead of using Chromium.
   - Login-state import: log in manually in system Chrome, then import the user-data-dir into Playwright.
   - Stealth plugins: patchright / playwright-stealth.
   - Slow typing + random delays to mimic human rhythm.
   - Avoid headless mode for 小红书 (its 检测 is strictest).
   - Real-Chrome mode (MatrixMedia's approach) for 小红书.

### Best starting point strategy

**Recommended fork base:** `dreammis/social-auto-upload` (MIT, 14k stars, 6/13 platforms).

**Adapter architecture to adopt:** Lift social-auto-upload's `uploader/<platform>/` folder pattern into a shared core. Each platform gets:
- `<platform>_uploader.py` — Playwright automation
- `<platform>_login.py` — QR/phone/SMS login + cookie persistence
- `<platform>_schema.py` — per-platform field requirements (title length, tag count, cover aspect ratio)

**Borrow patterns from:**

| Pattern | Source |
|---|---|
| Plugin auto-discovery (`plugins/` directory) | BadKid90s/Spreado |
| MCP server for AI agents | hanliang97/MatrixMedia + wechatsync |
| HTTP API for external orchestration | hanliang97/MatrixMedia (`127.0.0.1:30088/publish`) |
| Account-group concept | SamCheng0717/video-pusher |
| Login-state import from system Chrome | BetaStreetOmnis/xhs_ai_publisher |
| CDP-mode + real-Chrome evasion | NanmiCoder/MediaCrawler + hanliang97/MatrixMedia |
| Queue + supervisor for scale | kebenxiaoming/matrix |
| Cover image cropping (SixLabors.ImageSharp) | dorisoy/ShortVideo.AutoPublisher |
| Draft-first UX (default to draft, manual publish) | wechatsync |
| Per-platform length-limit adaptation | iamtornado/playwright-automation |

**Phase plan:**

1. **Phase 1 (Week 1-2):** Fork social-auto-upload. Verify its 6 platforms still work (抖音, Bilibili, 小红书, 快手, 视频号, 百家号). Add CLI tests for each.
2. **Phase 2 (Week 3-4):** Build 4 new adapters for the missing Chinese platforms with simpler UIs: 虎嗅, 36氪, 微博视频, 企鹅号. Use Playwright + cookie persistence.
3. **Phase 3 (Week 5-6):** Build the harder adapters: 腾讯视频 (long-video review process may block automation), 喜马拉雅 (audio, not video — needs different upload flow), 支付宝生活号 (requires 商家认证 — may need to skip or use browser automation only).
4. **Phase 4 (Week 7-8):** Add MCP server + HTTP API + cover cropping + tag-count handling + draft-first mode. Borrow Spreado's plugin architecture for community contributions.

**Risks to plan for:**

- **Platform UI changes** will break selectors. Budget 1-2 days/month for adapter maintenance.
- **风控 escalation** on 小红书 and 抖音 — keep the real-Chrome mode ready.
- **Legal exposure** for any reverse-engineered API usage — stay strictly on browser automation.
- **ToS violations** — most platforms' ToS technically prohibit automated publishing; this is a known industry practice but should be disclosed to end users.
- **Captcha puzzles** on 36kr and 虎嗅 entry pages — may require 2captcha / manual solving integration.
- **支付宝生活号 + 腾讯视频** may require enterprise certification that individual creators don't have — these two may end up as "best effort, may not work for all accounts".

**Final recommendation:** Do not build from scratch. Fork `dreammis/social-auto-upload`, refactor its adapter layer into a plugin system inspired by Spreado, add the 7 missing platform adapters using Playwright + cookie persistence, and expose the result via CLI + HTTP API + MCP server. Expected effort: 6-8 weeks of focused development for a working v1 covering 11-12 of 13 platforms (生活号 and 腾讯视频 may require enterprise accounts that limit coverage).
