// TV Monitor Wall · v1.4.1 — Worker wrapper
// Serves tv-app-v1.4.1.html as the response body for GET /
// HTML is embedded as a string literal.

const HTML_BODY = `<!DOCTYPE html>
<!--
================================================================================
TV Monitor Wall  ·  v1.4.1
================================================================================
AI AGENT NOTE
-------------
If you are an AI agent tasked with extending, refactoring or debugging this
single-file webapp, please OPEN THE IN-PAGE "关于" (About) tab inside the
Settings modal first. It contains the full self-introduction, purpose,
usage spec, source-list format and changelog — all maintained inline so the
deployed artifact is self-documenting.

In code, the same content is defined in the README_TEXT and CHANGELOG_TEXT
constants near the top of the <script> block. Update both places whenever
the behavior changes; bump APP_VERSION accordingly.

Deployment target: Cloudflare Worker "tv" → https://tv.lishuhang.workers.dev
(custom domain https://tv.lishuhang.com).

v1.4.1 changes (vs v1.4):
  1. 【无信号处理】设置项完善：在“通用 & 屏幕”标签页新增下拉选项，可选择「自动换台」或「反复重试」。
  2. 【源 pill 显示修复】修复 CSS 选择器错误，确保鼠标滑入视频区域时 pill 正常显示。
  3. 【播放不中断】窗口 resize 时不再重建 DOM，仅更新尺寸；增减屏幕时保留已有播放中的视频。
  4. 版本号统一更新至 v1.4.1，补充 v1.4 / v1.4.1 的 Changelog 和 README。

v1.4 changes (vs v1.3):
  1. 【无信号处理】新增“当前频道无信号时”设置项，支持「自动换台」和「反复重试」两种模式。
  2. 【源 pill 优化】source-pill 默认隐藏，仅在鼠标滑入视频区域 / 手触摸时才展开显示 pill-label，不显示 pill-dot 态。
  3. 【设置弹窗居中】设置浮窗打开时始终位于界面当前正中心。

v1.3 changes (vs v1.2):
  1. Navbar auto-hides after 3s of mouse inactivity (even when hovering video).
     Touch on top hot-zone doesn't pause playback; top hot-zone takes priority
     over navbar hot-zone when both overlap.
  2. Auto-rotate to next channel after 3 full source-rotation cycles fail.
     Rotation pauses while settings modal is open, resumes after close.
  3. Buffer/stall detection: if a screen stays buffering or stalled for >60s
     (and not user-paused), refresh the same source. If still failing, follow
     rule 2 (rotate to next channel).
  4. Export filename now includes date-time: tv_list-YYYYMMDD-HHMMSS.txt
================================================================================
-->
<html lang="zh-CN" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>TV Monitor Wall · v1.4.1</title>
    <!-- Tailwind CSS (v3.4) -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- HLS.js -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/hls.js/1.4.12/hls.min.js"></script>

    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        gray: {
                            850: '#1f2937',
                            900: '#111827',
                            950: '#030712',
                        }
                    },
                    transitionProperty: {
                        'transform': 'transform',
                    }
                }
            }
        }
    </script>
    <style>
        /* 基础重置 */
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }

        /* 播放器容器：完全填充格子（16:9 由外层 row 高度保证） */
        .video-wrapper {
            position: relative;
            width: 100%;
            height: 100%;
            background-color: black;
            overflow: hidden;
        }

        /* 视频元素 */
        video {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            object-fit: contain;
        }

        /* 状态/源头 pill（左上角，悬浮交互）
           v1.2: 默认只显示一个小圆点指示器，鼠标 hover / 触摸 / 键盘 focus 时才展开
                 显示完整频道名 + ▼ 提示，避免始终占据屏幕角落。 */
        .source-pill {
            position: absolute;
            top: 6px; left: 6px;
            background: rgba(0,0,0,0.65);
            color: rgba(255,255,255,0.92);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            pointer-events: auto;
            backdrop-filter: blur(2px);
            z-index: 15;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            max-width: calc(100% - 12px);
            cursor: pointer;
            user-select: none;
            /* v1.2: 默认收起 — 仅显示一个指示点 */
            min-width: 10px;
            padding: 3px 6px;
        }
        /* 默认收起：label / caret 隐藏，只留小圆点 */
        .source-pill .pill-dot { display: none; }
        .source-pill .pill-label,
        .source-pill .pill-caret,
        .source-pill .pill-dot { display: none; }
        /* v1.4: pill hidden by default */
        .source-pill { opacity: 0; transition: opacity 0.2s ease; pointer-events: none; }
        .video-wrapper:hover .source-pill,
        .video-wrapper:focus-within .source-pill,
        .source-pill.pill-expanded { opacity: 1; pointer-events: auto; }

        /* 任何触发条件：hover / focus-within / .pill-expanded → 展开 */
        .source-pill:hover,
        .source-pill:focus-within,
        .source-pill.pill-expanded {
            min-width: auto;
            padding: 3px 8px;
        }
        .source-pill:hover .pill-label,
        .source-pill:focus-within .pill-label,
        .source-pill.pill-expanded .pill-label { display: inline-block; }
        .source-pill:hover .pill-caret,
        .source-pill:focus-within .pill-caret,
        .source-pill.pill-expanded .pill-caret { display: inline-block; }
        .source-pill:hover .pill-dot,
        .source-pill:focus-within .pill-dot,
        .source-pill.pill-expanded .pill-dot { display: none; }

        .source-pill .pill-label {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 220px;
        }
        .source-pill .pill-caret {
            opacity: 0.7;
            font-size: 9px;
        }
        .source-dropdown {
            position: absolute;
            top: calc(100% + 4px);
            left: 0;
            min-width: 220px;
            max-width: 360px;
            max-height: 280px;
            overflow-y: auto;
            background: rgba(0,0,0,0.92);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 6px;
            padding: 4px 0;
            display: none;
            z-index: 30;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        .source-dropdown.open { display: block; }
        .source-option {
            padding: 6px 10px;
            font-size: 11px;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            color: rgba(255,255,255,0.85);
            cursor: pointer;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .source-option:hover { background: rgba(255,255,255,0.08); }
        .source-option.active {
            background: rgba(59,130,246,0.25);
            color: #93c5fd;
        }
        .source-option .opt-tag {
            display: inline-block;
            margin-right: 4px;
            padding: 0 4px;
            border-radius: 3px;
            background: rgba(255,255,255,0.1);
            font-size: 9px;
            color: #cbd5e1;
        }
        .source-option.active .opt-tag { background: rgba(147,197,253,0.25); color: #dbeafe; }

        /* 状态覆盖层（仅用于 loading / error，独立于 source pill） */
        .overlay-info {
            position: absolute;
            top: 6px; right: 6px;
            background: rgba(0,0,0,0.6);
            color: rgba(255,255,255,0.9);
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            pointer-events: none;
            backdrop-filter: blur(2px);
            z-index: 12;
            display: none;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }

        /* "tap to unmute" 浮层 */
        .unmute-hint {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0,0,0,0.35);
            color: white;
            font-size: 12px;
            z-index: 14;
            cursor: pointer;
            pointer-events: auto;
        }
        .unmute-hint .unmute-inner {
            background: rgba(0,0,0,0.7);
            padding: 6px 12px;
            border-radius: 16px;
            backdrop-filter: blur(4px);
            display: flex; align-items: center; gap: 6px;
        }

        /* 布局：行式 flex（每行高度由 JS 设定，使所有 cell 严格 16:9） */
        #monitor-grid {
            display: flex;
            flex-direction: column;
            gap: 2px;
            background-color: black;
            margin: 0 auto;
            transition: width 0.2s ease, height 0.2s ease;
        }
        .grid-row {
            display: flex;
            gap: 2px;
            width: 100%;
        }
        .grid-row > .monitor-unit {
            flex: 1 1 0;
            min-width: 0;
        }
        .monitor-unit {
            position: relative;
            background: black;
        }

        /* 隐藏滚动条 */
        body::-webkit-scrollbar { width: 0px; background: transparent; }

        /* 导航条动画 */
        .nav-hidden { transform: translateY(-100%); }

        /* v1.3: 顶部触发区 — 扩大为 48px 以便触控；
                 使用 pointer-events 仅在 nav-hidden 时启用，避免遮盖导航栏按钮 */
        #hover-trigger {
            position: fixed; top: 0; left: 0;
            width: 100%; height: 12px;
            z-index: 51;
            /* 当导航栏可见时禁用触发区，让导航栏按钮可点 */
            pointer-events: auto;
        }
        body:not(.nav-hidden-active) #hover-trigger { pointer-events: none; }

        /* v1.3: 当导航栏可见时，主内容下移以避免遮挡 source-pill */
        #main-container {
            transition: padding-top 0.3s ease;
            padding-top: 0;
        }
        body:not(.nav-hidden-active) #main-container {
            padding-top: 48px;
        }

        /* 模态框拖动时禁用选中文本 */
        .modal-dragging { user-select: none; }

        /* About / changelog 等长文本排版 */
        .prose-mini h1 { font-size: 1.05rem; font-weight: 700; margin: 0.6rem 0 0.3rem; }
        .prose-mini h2 { font-size: 0.95rem; font-weight: 700; margin: 0.6rem 0 0.3rem; color: #93c5fd; }
        .prose-mini h3 { font-size: 0.85rem; font-weight: 600; margin: 0.4rem 0 0.2rem; }
        .prose-mini p  { font-size: 0.78rem; line-height: 1.6; margin: 0.3rem 0; color: rgba(229,231,235,0.92); }
        .prose-mini ul { font-size: 0.78rem; line-height: 1.55; margin: 0.3rem 0 0.3rem 1.1rem; list-style: disc; color: rgba(229,231,235,0.92); }
        .prose-mini li { margin: 0.15rem 0; }
        .prose-mini code {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            background: rgba(148,163,184,0.18);
            padding: 1px 4px; border-radius: 3px;
            font-size: 0.74rem;
        }
        .prose-mini pre {
            background: rgba(0,0,0,0.45);
            border: 1px solid rgba(148,163,184,0.15);
            padding: 8px 10px; border-radius: 6px;
            overflow-x: auto; margin: 0.4rem 0;
        }
        .prose-mini pre code { background: transparent; padding: 0; font-size: 0.72rem; }
        .prose-mini hr { border-color: rgba(148,163,184,0.2); margin: 0.6rem 0; }
        .prose-mini a { color: #93c5fd; text-decoration: underline; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800 dark:bg-gray-950 dark:text-gray-200 transition-colors duration-300 h-[100dvh] flex flex-col overflow-hidden">

    <!-- 顶部触发区 -->
    <div id="hover-trigger"></div>

    <!-- 顶部导航 -->
    <nav id="navbar" class="fixed top-0 left-0 w-full shrink-0 z-50 bg-white/95 dark:bg-gray-900/95 backdrop-blur border-b border-gray-200 dark:border-gray-800 h-12 flex items-center justify-between px-4 transition-transform duration-300 nav-hidden shadow-md">
        <div class="flex items-center gap-2 font-bold text-base tracking-tight cursor-default">
            <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
            <span>Monitor<span class="text-blue-600 dark:text-blue-400">Hub</span></span>
            <span class="ml-1 text-[10px] font-mono text-gray-400">v1.4.1</span>
        </div>

        <div class="flex items-center gap-1">
            <button onclick="toggleFullscreen()" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors text-gray-600 dark:text-gray-400" title="全屏 (F11)">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"></path></svg>
            </button>

            <button onclick="togglePinNavbar()" id="btn-pin" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors text-gray-600 dark:text-gray-400" title="钉住导航条">
                <svg id="icon-pin-on" class="hidden w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 24 24"><path d="M16 12V6a4 4 0 00-8 0v6l-2 2v2h5v6l1 1 1-1v-6h5v-2l-2-2z"></path></svg>
                <svg id="icon-pin-off-simple" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
            </button>

            <button onclick="toggleSettings()" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors text-gray-600 dark:text-gray-400" title="设置">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
            </button>
        </div>
    </nav>

    <!-- 主内容区 -->
    <main id="main-container" class="bg-black flex flex-col items-center justify-start relative w-full h-full overflow-hidden">
        <div id="monitor-grid" data-count="0"></div>

        <div id="empty-state" class="hidden absolute inset-0 flex items-center justify-center text-gray-500 z-0">
            <div class="text-center">
                <p class="text-lg">No Active Screens</p>
                <button onclick="toggleSettings()" class="mt-2 text-blue-500 hover:underline">Open Settings</button>
            </div>
        </div>
    </main>

    <!-- 设置模态框 -->
    <div id="settings-modal" class="fixed inset-0 z-[100] hidden">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity" onclick="toggleSettings()"></div>

        <div id="settings-content" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-white dark:bg-gray-900 rounded-xl shadow-2xl flex flex-col h-[80vh] max-h-[90vh] overflow-hidden border border-gray-200 dark:border-gray-800 transition-transform">

            <div id="modal-header" class="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex justify-between items-center bg-gray-50 dark:bg-gray-850 cursor-move select-none">
                <h2 class="text-lg font-bold">控制台设置 <span class="text-xs font-mono text-gray-400 ml-1">v1.4.1</span></h2>
                <button onclick="toggleSettings()" class="text-gray-500 hover:text-red-500" onmousedown="event.stopPropagation()">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>

            <!-- Tabs (3 个) -->
            <div class="flex border-b border-gray-200 dark:border-gray-800">
                <button onclick="switchTab('tab-general')" id="btn-tab-general" class="tab-btn flex-1 py-3 text-sm font-medium border-b-2 border-blue-500 text-blue-600 dark:text-blue-400 bg-white dark:bg-gray-900">通用 & 屏幕</button>
                <button onclick="switchTab('tab-sources')" id="btn-tab-sources" class="tab-btn flex-1 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 bg-gray-50 dark:bg-gray-850">内容源编辑</button>
                <button onclick="switchTab('tab-about')" id="btn-tab-about" class="tab-btn flex-1 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 bg-gray-50 dark:bg-gray-850">关于</button>
            </div>

            <!-- Modal Body: 固定 flex-1 + min-h-0 + overflow-y-auto，使切 tab 时
                 modal 总高度不变（80vh），只是 body 内部滚动 -->
            <div class="flex-1 min-h-0 overflow-y-auto p-6 space-y-6 bg-white dark:bg-gray-900">

                <!-- Tab 1: 通用 & 屏幕 -->
                <div id="tab-general" class="space-y-6">
                    <div class="space-y-3">
                        <span class="block font-medium border-b dark:border-gray-800 pb-1">屏幕配置（类别 + 频道两级筛选）</span>
                        <div id="screen-controls" class="space-y-3"></div>
                    </div>

                    <div class="space-y-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                        <div class="flex items-center justify-between">
                            <span class="font-medium">界面主题</span>
                            <select id="theme-select" onchange="updateThemeAndSave()" class="bg-gray-100 dark:bg-gray-800 border-none rounded px-3 py-1 text-sm">
                                <option value="dark">深色模式 (默认)</option>
                                <option value="light">浅色模式</option>
                                <option value="system">跟随系统</option>
                            </select>
                        </div>

                        <div class="space-y-2">
                            <div class="flex justify-between items-baseline">
                                <span class="font-medium">带宽策略</span>
                                <span class="text-xs text-blue-500">Auto-Level</span>
                            </div>
                            <select id="bandwidth-mode" onchange="saveConfig()" class="w-full bg-gray-100 dark:bg-gray-800 border-none rounded p-2 text-sm">
                                <option value="unlimited">家庭宽带 (无限制)</option>
                                <option value="balanced">均衡模式 (限制720p)</option>
                                <option value="saver">手机网络 (限制480p)</option>
                                <option value="low">极速省流 (最低画质)</option>
                            </select>
                        </div>

                        <div class="space-y-2">
                            <div class="flex justify-between items-baseline">
                                <span class="font-medium">当前频道无信号时</span>
                            </div>
                            <select id="autorotate-mode" onchange="updateAutoRotateMode()" class="w-full bg-gray-100 dark:bg-gray-800 border-none rounded p-2 text-sm">
                                <option value="auto-switch">自动换台（轮换到下一频道）</option>
                                <option value="retry">反复重试（持续重试当前频道所有线路）</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Tab 2: 内容源 -->
                <div id="tab-sources" class="hidden space-y-4">
                    <div class="bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 p-3 rounded text-xs leading-relaxed space-y-1">
                        <p>每行格式：<code>名称,链接</code>。同名同名分组的多个 URL 视为该频道的多条线路。</p>
                        <p>可使用 Markdown 标题（<code>## 央视</code> / <code>### 海外</code> 等）进行分类；不论写法层级，统一作为平级类别显示。</p>
                        <p>未分类的频道归入默认空类别；屏幕配置中可按类别筛选。</p>
                    </div>
                    <textarea id="source-editor" class="w-full h-64 bg-gray-100 dark:bg-gray-800 p-3 rounded text-xs font-mono border border-gray-200 dark:border-gray-700 focus:outline-none focus:border-blue-500 whitespace-pre" spellcheck="false"></textarea>

                    <div class="flex gap-3">
                        <button onclick="exportSources()" class="flex-1 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">导出 .txt</button>
                        <button onclick="triggerImport()" class="flex-1 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 text-sm">导入 .txt</button>
                        <input type="file" id="file-import" class="hidden" accept=".txt" onchange="importSources(this)">
                    </div>
                    <button onclick="saveSourcesAndReload()" class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium shadow-lg shadow-blue-500/30">保存更改并刷新</button>
                </div>

                <!-- Tab 3: 关于 -->
                <div id="tab-about" class="hidden space-y-4">
                    <div class="flex border-b border-gray-200 dark:border-gray-800 gap-4 text-sm" id="about-subtabs">
                        <button onclick="switchAbout('readme')" id="btn-about-readme" class="py-2 border-b-2 border-blue-500 text-blue-600 dark:text-blue-400">README</button>
                        <button onclick="switchAbout('changelog')" id="btn-about-changelog" class="py-2 border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400">Changelog</button>
                    </div>
                    <div id="about-readme" class="prose-mini text-gray-200 dark:text-gray-200"></div>
                    <div id="about-changelog" class="prose-mini text-gray-200 dark:text-gray-200 hidden"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
    /* ============================================================================
       TV Monitor Wall · v1.4.1
       自包含单页 IPTV 监视墙：多画面 HLS 播放、智能布局、源选择、分类。
       详细说明见『关于』Tab / README_TEXT / CHANGELOG_TEXT。
       ============================================================================ */

    const APP_VERSION = '1.4.1';
    const MAX_SCREENS = 4;

    // --- README（关于 Tab 显示） ---
    const README_TEXT = \`
# TV Monitor Wall

> 单文件、零后端的多画面 HLS 监视墙，部署在 Cloudflare Worker 上。
> 当前版本：**v\${APP_VERSION}**

## 我是谁

本工具由 Super Z（基于 GLM 模型，由 Z.ai 构建）协助开发维护。
你正在使用的就是它交付的单文件网页 \\\`tv-app-v\${APP_VERSION}.html\\\`。

## 用途

把一个纯文本的 IPTV 源列表（M3U8/HLS）以多画面形式同时铺在你的浏览器窗口里，
适合做"监视墙"、"信号巡检"、"多路对比"等用途。所有播放、切换、状态记录都发生在
浏览器本地（localStorage），不依赖任何后端。

## 用法

1. 点击右上角 ⚙ 进入『控制台设置』。
2. 在『内容源编辑』Tab 粘贴源列表（格式见下），点 *保存更改并刷新*。
3. 在『通用 & 屏幕』Tab 勾选要启用的屏幕（1~4），分别为每块屏幕选 *类别* 与 *频道*。
   - 类别下拉最上方固定为【全部】；如列表未分类则只有【全部】可选。
4. 关闭设置，画面自动开始播放。鼠标移到屏幕左上角的源信息 pill 上（或手机轻触），
   会浮出 *源头选择* 下拉：
   - **自动**：默认项；当某条线路失败/超时 10s 时自动切下一条 URL，全部失败后循环重试。
   - 任意具体 URL：锁定该源；断讯时只重试该源，不再切换。
5. 同一屏幕换源（自动或手动）会**保留该屏幕的静音/非静音状态**；首次播放因浏览器策略
   可能仍需手动点击解除静音，之后会记住偏好。
6. 顶部导航栏会在鼠标滑入屏幕顶端时浮现；点击图钉可钉住。
7. 顶部右侧全屏按钮 / F11 进入全屏。

## 内容源格式

\\\`\\\`\\\`
## 央视

CCTV1,https://example.com/cctv1.m3u8
CCTV13,https://example.com/cctv13.m3u8
CCTV13,https://backup.example.com/cctv13.m3u8     # 同名 = 同一频道的备线

## 海外

CNN,https://example.com/cnn.m3u8
### 美洲                                          # h3/h4 也会被识别，但统一平级显示
FOX,https://example.com/fox.m3u8
\\\`\\\`\\\`

要点：
- 每行 \\\`名称,链接\\\`；同名行视为同频道的多线路，自动轮流 failover。
- \\\`# xxx\\\` 单行注释（行首 # 之后整行忽略）。
- Markdown 标题（\\\`#\\\` ~ \\\`######\\\`）定义类别；不论层级一律平级展示。
- 未在标题下的频道归入空类别（在筛选下拉里属于【全部】）。

## 智能屏幕布局

为最大化屏幕显示面积、最小化黑边，程序会按以下规则自动排布：

- 把 N 块屏幕切分为若干"行"，每行 cᵢ 块；列出 N 的所有有序分割。
- 每行内部所有 cell 等宽，整行填满 grid 宽度 → 严格的 16:9。
- 对每个候选分割计算可装入容器后的实际显示面积，挑选面积最大者。
- 平局时优先选择行数较少、更"方正"的方案。

举例：容器约 3:4 竖屏、4 块屏幕 → 2×2 会大量留白；程序会自动选 \\\`1+2+1\\\` 三行布局，
中间一行 2 块、上下各 1 块填满宽度，黑边显著减少。

## 无信号处理

在“通用 & 屏幕”标签页中，可选择频道无信号时的处理方式：
- **自动换台**：当前频道所有线路轮询 3 轮失败后，自动切换到源列表中下一个频道。
- **反复重试**：始终在当前频道的所有线路之间循环重试，不切换到其他频道。

## 部署

\\\`Cloudflare Worker\\\` 名为 \\\`tv\\\`；访问 \\\`https://tv.lishuhang.workers.dev/\\\`
会通过自定义域跳转到 \\\`https://tv.lishuhang.com\\\`。源代码即此 HTML 文件，
Worker 只把它作为字符串响应返回。

## 隐私

- 所有配置（源、屏幕分配、主题、带宽、静音偏好）都存在你浏览器的 localStorage。
- 播放流量直接走你的浏览器到源站，本 Worker 不转发、不记录。
- 顶部 beacon 是 Cloudflare Insights 自带统计，仅用于 Worker 自身观测。
\`;

    // --- CHANGELOG ---
    const CHANGELOG_TEXT = \`
# Changelog

## v1.4.1 — 2026-07-26

### 修复 / 优化
- **无信号设置项 UI 完善**：在“通用 & 屏幕”标签页新增「当前频道无信号时」下拉选项，可选择「自动换台」或「反复重试」。
- **源 pill 显示修复**：修复 CSS 选择器错误（.video-container → .video-wrapper），确保鼠标滑入视频区域时 source-pill 正常显示。
- **播放不中断**：窗口 resize 时不再触发全量重建，仅更新行高；增减屏幕时保留已有播放中的视频实例（HLS 不重建）。
- **版本号统一**：导航栏、设置弹窗、head-title、关于页全部统一为 v1.4.1。
- **死代码清理**：移除 handleFailover 中不可达的 rotateToNextChannel 调用。

## v1.4 — 2026-07-25

### 新增
- **无信号处理设置项**：新增「当前频道无信号时」配置项，支持「自动换台」和「反复重试」两种模式。
- **source-pill 默认隐藏**：source-pill 无动作时完全隐藏，仅在鼠标滑入视频区域 / 手触摸时才展开显示 pill-label。
- **设置弹窗始终居中**：打开设置浮窗时重置为界面正中心。

## v1.3 — 2026-07-22

### 新增 / 修复
- **导航栏空闲自动隐藏**：鼠标无论位于画面或导航栏上，只要 3 秒不动即自动隐藏，
  确保屏幕干净无干扰。鼠标再次移动立即浮现。
- **触控热区优化**：触摸顶部热区显示导航栏时不再触发播放暂停；顶部热区优先于
  导航栏 hover 热区，避免互相遮盖。
- **频道自动轮换**：某频道轮询其所有源 3 遍后仍无法播放时，自动切换到列表中下一
  个频道，直到找到可播放源为止，避免长时间黑屏。
- **设置打开时暂停轮换**：因设置面板内频道列表会跟随自动换台变化，打开设置时
  暂停频道轮换，关闭设置后继续。
- **缓冲超时刷新**：检测到屏幕处于长期缓冲或停止播放（非用户主动暂停）超过 60 秒
  时，先刷新同一个源；若仍无效则按"频道轮换"规则换源。
- **导出文件名带日期时间**：导出 .txt 时文件名格式改为 \\\`tv_list-YYYYMMDD-HHMMSS.txt\\\`，
  便于保留多个历史版本。
- **hls.js backBuffer 修复音画漂移**：默认 \\\`backBufferLength: 10\\\`、\\\`liveSyncDurationCount: 3\\\`、
  \\\`lowLatencyMode: false\\\`，缓解长时间播放后声音越来越低沉、音画不同步的问题。

## v1.2 — 2026-07-08

### 调整
- **屏幕数量上限改回 4**（v1.1 临时放开到 9 经实际使用反馈偏多，回归 4 屏以匹配常见监视墙需求）。
- **频道名不始终显示**：屏幕左上角的源 pill 默认收起为一个浅蓝小圆点指示器，
  仅在鼠标 hover / 触摸 / 键盘 focus / 点击展开下拉时才显示频道名 + ▼ 提示，避免遮挡画面。
- **示例源使用占位名**：内置默认源列表的频道名改为 \\\`apple\\\` / \\\`pear\\\` / \\\`orange\\\` / \\\`banana\\\` 等
  水果名占位，不再引用任何真实频道；URL 仍用公开 HLS 测试流以便开箱即用验证。
- **设置窗口切 tab 不再跳动**：模态框固定为 80vh 高度，切 tab 时只有 body 内部滚动，
  整体窗口高度与位置保持不变。

## v1.1 — 2026-07-08

### 新增
- **『关于』Tab**：内置 README + Changelog；代码顶部加入 AI agent 提示，便于后续开发与 debug。
- **智能屏幕布局**：以"行分割 + 面积最大化"算法替代原先写死的 2×2 / 1+2 / 1×1。
  任意容器比例、任意屏幕数（1~4）都能自动选最佳行排布，最小化黑边。
- **屏幕源头选择下拉**：每块屏幕左上角的源 pill 鼠标 hover / 手指轻触即可弹出。
  - 选项包含 \\\`自动\\\`（默认，原有轮流 failover）以及该频道每条 URL（只要 URL 不完全相同即视为不同源，即便域名前缀一致）。
  - 选固定源后断讯只重试该源，不再切下一源。
- **静音状态记忆**：换源（自动或手动）时同一屏幕维持原来的有声/无声设置；
  首次自动播放若被浏览器拦截，会显示"轻触解除静音"浮层。
- **Markdown 分类支持**：源列表可用 \\\`## 类别\\\` / \\\`### 子类\\\` 等定义类别；不论层级统一平级展示。
- **屏幕配置两级下拉**：原 \\[频道名\\] 改为 \\[类别\\]（首项固定为【全部】并默认选中）+ \\[频道名\\]。
- 屏幕数量上限从 4 提升到 9。

### 修复 / 优化
- 换源时不再清空播放器音量偏好；避免"原本有声换源后变静音"的问题。
- 跳帧源会被自动跳过（仅当处于 *自动* 模式且该线路真正失败时）。
- **重建屏幕布局时正确销毁旧 hls 实例与超时定时器**，避免旧 failover 闭包引用过期
  的频道源继续轮询，导致"切到无关 URL"的诡异现象。
- 类别筛选下拉只列出含有至少一个频道的类别，过滤空标题。
- 自动播放被浏览器拦截时显示"轻触解除静音"浮层，且不污染持久化的静音偏好。
- 模态框拖动 / 钉住导航 / 全屏 / 主题切换等行为与 v1.0 一致。

## v1.0 — 初始版本

- 4 块屏幕、固定 grid 模板；源列表 \\\`名称,链接\\\` 单行格式；同名多 URL 自动 failover；
  HTTPS 智能升级；带宽策略；导出/导入 .txt；拖动模态框；钉住导航。
\`;

    // --- 默认数据 ---
    // 示例源使用 fruit 名称占位（apple/pear/orange/banana/grape 等），不引用任何真实频道。
    // URL 仍使用公开 HLS 测试流以便开箱即用验证播放器。
    const DEFAULT_SOURCES_TEXT = \`## 演示

apple,https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
pear,https://test-streams.mux.dev/test_001/stream.m3u8
orange,https://test-streams.mux.dev/tos_ismc/main.m3u8
banana,https://test-streams.mux.dev/pts_shift/master.m3u8

## 备线示例

apple,https://sample.vodobox.net/skate_phantom_flex_4k/skate_phantom_flex_4k.m3u8
\`;

    const DEFAULT_ASSIGNMENTS = { 1: 0, 2: 1, 3: 2, 4: 3 };

    // --- 状态管理 ---
    let appState = {
        activeScreens: [1, 2, 3, 4],
        assignments: { ...DEFAULT_ASSIGNMENTS },
        // 每块屏幕的源选择：'auto' 或具体 URL 字符串
        screenSource: { 1: 'auto', 2: 'auto', 3: 'auto', 4: 'auto' },
        // 每块屏幕的静音偏好（仅当用户曾交互改变过才被持久化）
        screenMuted:  { 1: true, 2: true, 3: true, 4: true },
        // 每块屏幕的"用户已设置过音量"标记
        screenMutedTouched: { 1: false, 2: false, 3: false, 4: false },
        sources: [],          // [{ name, urls:[], category:'' }]
        categories: [],       // 顺序去重类别名
        theme: 'dark',
        bandwidth: 'unlimited',
        navbarPinned: false,
        autoRotateMode: 'auto-switch'
    };

    // 屏幕配置面板里"类别筛选"的当前值（UI 态，不持久化）
    const uiCategoryFilter = { 1: '', 2: '', 3: '', 4: '' };

    const hlsInstances = {};
    const retryTimers = {};
    const failoverState = {};   // 每屏当前的 failover 上下文 {lineIndex, trySecure, fixedUrl}
    const SCREEN_IDS = [1, 2, 3, 4];
    let storedPartition = null;  // v1.4.1: cache partition to avoid rebuild on resize

    // --- 初始化 ---
    window.addEventListener('DOMContentLoaded', () => {
        loadConfig();
        initTheme();
        initNavbarInteraction();
        initModalDrag();
        initGlobalDismiss();

        const sourceText = document.getElementById('source-editor').value || DEFAULT_SOURCES_TEXT;
        parseSources(sourceText);

        renderAbout();
        renderGrid();
        // v1.3: Init user-pause tracking after grid is rendered (videos exist now)
        setTimeout(() => initUserPauseTracking(), 100);
        // v1.4.1: Debounced resize — only update sizes, never rebuild DOM
        let resizeTimer = null;
        window.addEventListener('resize', () => {
            if (resizeTimer) clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => applyLayout(false), 80);
        });
        window.addEventListener('fullscreenchange', () => applyLayout(false));
    });

    // 全局点击关闭 source dropdown
    function initGlobalDismiss() {
        document.addEventListener('click', (e) => {
            document.querySelectorAll('.source-dropdown.open').forEach(dd => {
                if (!dd.parentElement.contains(e.target)) {
                    dd.classList.remove('open');
                    dd.parentElement.classList.remove('pill-expanded');
                }
            });
        }, true);
    }

    // --- 拖动模态框 ---
    function initModalDrag() {
        const header = document.getElementById('modal-header');
        const modalContent = document.getElementById('settings-content');
        let isDragging = false, startX, startY;

        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            const rect = modalContent.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;
            modalContent.style.transform = 'none';
            modalContent.style.left = \`\${rect.left}px\`;
            modalContent.style.top = \`\${rect.top}px\`;
            modalContent.style.margin = '0';
            document.body.classList.add('modal-dragging');
        });
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault();
            modalContent.style.left = \`\${e.clientX - startX}px\`;
            modalContent.style.top = \`\${e.clientY - startY}px\`;
        });
        document.addEventListener('mouseup', () => {
            isDragging = false;
            document.body.classList.remove('modal-dragging');
        });
    }

    // --- 导航条交互 ---
    // v1.3: 鼠标空闲超过 NAVBAR_IDLE_HIDE_MS 后自动隐藏，即使鼠标位于画面或导航栏上。
    //       鼠标移动立即重新显示（如果鼠标在画面内/导航栏热区）。
    //       触控顶部热区显示导航栏时不暂停播放，热区优先级高于导航栏 hover 热区。
    //       导航栏可见时主内容自动下移，避免遮挡 source-pill。
    const NAVBAR_IDLE_HIDE_MS = 3000;
    let navbarHideTimer = null;

    function setNavbarVisible(visible) {
        const navbar = document.getElementById('navbar');
        if (!navbar) return;
        if (visible) {
            navbar.classList.remove('nav-hidden');
            document.body.classList.remove('nav-hidden-active');
        } else {
            if (!appState.navbarPinned) {
                navbar.classList.add('nav-hidden');
                document.body.classList.add('nav-hidden-active');
            }
        }
    }

    function initNavbarInteraction() {
        const navbar = document.getElementById('navbar');
        const trigger = document.getElementById('hover-trigger');
        updateNavbarPinUI();
        // Initialize body class
        document.body.classList.add('nav-hidden-active');

        // 顶部热区 hover (鼠标移入)
        trigger.addEventListener('mouseenter', () => {
            setNavbarVisible(true);
            scheduleNavbarHide();
        });
        navbar.addEventListener('mouseenter', () => {
            setNavbarVisible(true);
            scheduleNavbarHide();
        });
        navbar.addEventListener('mouseleave', () => {
            if (!appState.navbarPinned) {
                scheduleNavbarHide(300);
            }
        });

        // v1.3: Touch on hover-trigger shows navbar without pausing playback.
        // preventDefault stops the touch from propagating to the video below.
        trigger.addEventListener('touchstart', (e) => {
            e.preventDefault();  // prevent tap from pausing video
            setNavbarVisible(true);
            scheduleNavbarHide();
        }, { passive: false });

        // v1.3: 全局鼠标移动重置空闲计时器
        document.addEventListener('mousemove', () => {
            scheduleNavbarHide();
        });

        // Initial schedule
        scheduleNavbarHide();
    }

    // v1.3: Schedule navbar hide after NAVBAR_IDLE_HIDE_MS (or custom delay)
    function scheduleNavbarHide(delay = NAVBAR_IDLE_HIDE_MS) {
        if (navbarHideTimer) clearTimeout(navbarHideTimer);
        navbarHideTimer = setTimeout(() => {
            const navbar = document.getElementById('navbar');
            if (!navbar) return;
            // Only hide if not pinned and not currently being hovered
            if (!appState.navbarPinned && !navbar.matches(':hover')) {
                setNavbarVisible(false);
            }
        }, delay);
    }
    function togglePinNavbar() {
        appState.navbarPinned = !appState.navbarPinned;
        updateNavbarPinUI();
        saveConfig();
    }
    function updateNavbarPinUI() {
        const navbar = document.getElementById('navbar');
        const on = document.getElementById('icon-pin-on');
        const off = document.getElementById('icon-pin-off-simple');
        const btn = document.getElementById('btn-pin');
        if (appState.navbarPinned) {
            navbar.classList.remove('nav-hidden');
            on.classList.remove('hidden'); off.classList.add('hidden');
            btn.classList.add('text-blue-600', 'bg-blue-50', 'dark:bg-blue-900/30');
        } else {
            if (!navbar.matches(':hover')) navbar.classList.add('nav-hidden');
            on.classList.add('hidden'); off.classList.remove('hidden');
            btn.classList.remove('text-blue-600', 'bg-blue-50', 'dark:bg-blue-900/30');
        }
    }

    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(()=>{});
        } else {
            document.exitFullscreen();
        }
    }

    /* ============================================================================
       智能布局：行分割 + 面积最大化
       ============================================================================ */

    // 枚举 n 的所有有序正整数分割（composition）
    function* compositions(n, maxLen = n) {
        if (n === 0) { yield []; return; }
        for (let first = 1; first <= n; first++) {
            for (const rest of compositions(n - first, maxLen)) {
                if (rest.length + 1 <= maxLen) yield [first, ...rest];
            }
        }
    }

    // 对一个分割，计算装入容器后的实际显示面积（以容器宽 W=1 为归一）
    function evaluatePartition(partition, containerAspect) {
        const sumInv = partition.reduce((s, c) => s + 1 / c, 0); // Σ 1/cᵢ
        const gridAspect = 16 / (9 * sumInv);
        let W_grid, H_grid;
        if (gridAspect >= containerAspect) {
            // 宽度受限：grid 撑满宽度
            W_grid = 1;
            H_grid = (9 / 16) * sumInv;
        } else {
            // 高度受限：grid 撑满高度（容器高 = 1/aspect，因 W=1）
            H_grid = 1 / containerAspect;
            W_grid = H_grid * gridAspect;
        }
        // 总可见面积 = W_grid² * (9/16) * Σ(1/cᵢ)
        const area = W_grid * W_grid * (9 / 16) * sumInv;
        return { partition, W_grid, H_grid, area, gridAspect, sumInv };
    }

    // 评估布局的"对称度"——回文分数（0=完全对称，越大越偏）
    function asymmetryScore(p) {
        let s = 0;
        for (let i = 0; i < Math.floor(p.length / 2); i++) {
            s += Math.abs(p[i] - p[p.length - 1 - i]);
        }
        return s;
    }

    function findBestLayout(N, containerAspect) {
        if (N === 0) return null;
        if (N === 1) return evaluatePartition([1], containerAspect);
        let best = null;
        for (const p of compositions(N)) {
            // 视觉约束：相邻行块数比 ≤ 3，避免出现 "1 大屏 + N 极小条" 这类极端布局
            let visualOk = true;
            for (let i = 1; i < p.length; i++) {
                const a = p[i-1], b = p[i];
                if (Math.max(a, b) / Math.min(a, b) > 3) { visualOk = false; break; }
            }
            // 单行布局跳过该约束（N 块全部塞一行）
            if (p.length > 1 && !visualOk) continue;

            const r = evaluatePartition(p, containerAspect);
            if (!best) { best = r; continue; }
            const dArea = r.area - best.area;
            if (dArea > 1e-9) {
                best = r;
            } else if (Math.abs(dArea) < 1e-9) {
                // 平局：① 行数更少 ② 对称度更高
                if (p.length < best.partition.length) best = r;
                else if (p.length === best.partition.length &&
                         asymmetryScore(p) < asymmetryScore(best.partition)) best = r;
            }
        }
        return best;
    }

    function applyLayout(forceRebuild) {
        const grid = document.getElementById('monitor-grid');
        const container = document.getElementById('main-container');
        const N = appState.activeScreens.length;
        if (N === 0) { grid.style.width = '0'; grid.style.height = '0'; storedPartition = null; return; }

        const W = container.clientWidth;
        const H = container.clientHeight;
        if (W === 0 || H === 0) return;
        const R = W / H;

        const best = findBestLayout(N, R);
        if (!best) return;

        const pxW = best.W_grid * W;
        const pxH = best.H_grid * W;
        grid.style.width = pxW + 'px';
        grid.style.height = pxH + 'px';

        // v1.4.1: Only recalculate partition on forceRebuild, not on resize
        if (forceRebuild || !storedPartition) {
            storedPartition = best.partition;
        }
        const usePartition = storedPartition;

        // 是否需要重建结构？
        const currentRows = Array.from(grid.children).filter(n => n.classList && n.classList.contains('grid-row'));
        const currentShape = currentRows.map(r => r.children.length).join(',');
        const targetShape  = usePartition.join(',');
        const needRebuild = forceRebuild || (currentShape !== targetShape) || (grid.dataset.count !== String(N));

        if (!needRebuild) {
            // 仅更新各 row 高度
            currentRows.forEach((row, i) => {
                const c = usePartition[i];
                row.style.height = (pxW / c * 9 / 16) + 'px';
            });
            return;
        }

        // v1.4.1: 保留仍激活屏幕的播放器，仅重建结构布局
        grid.dataset.count = String(N);
        const ids = [...appState.activeScreens].sort((a,b)=>a-b);

        // 保存仍激活屏幕的 monitor-unit（保留 HLS 实例和视频状态）
        const savedUnits = {};
        ids.forEach(id => {
            const existing = document.querySelector(\`.monitor-unit[data-id="\${id}"]\`);
            if (existing) {
                savedUnits[id] = existing; existing.remove();
            }
        });
        // 销毁不再激活的屏幕播放器
        SCREEN_IDS.forEach(id => {
            if (!appState.activeScreens.includes(id)) destroyPlayer(id);
        });

        grid.innerHTML = '';
        let idx = 0;
        usePartition.forEach(c => {
            const row = document.createElement('div');
            row.className = 'grid-row';
            row.style.height = (pxW / c * 9 / 16) + 'px';
            for (let i = 0; i < c; i++) {
                const id = ids[idx++];
                if (id === undefined) continue;
                if (savedUnits[id]) {
                    row.appendChild(savedUnits[id]);
                } else {
                    const unit = createMonitorUnit(id);
                    row.appendChild(unit);
                }
            }
            grid.appendChild(row);
        });

        // 仅为新创建的屏幕启动播放器
        ids.forEach(id => {
            if (!savedUnits[id]) initPlayer(id);
        });
        if (forceRebuild) initUserPauseTracking();
    }

    // --- 配置读写 ---
    function loadConfig() {
        const saved = localStorage.getItem('tv_monitor_config');
        if (saved) {
            const parsed = JSON.parse(saved);
            if (!parsed.theme) parsed.theme = 'dark';
            if (!parsed.screenSource) parsed.screenSource = {};
            if (!parsed.screenMuted)  parsed.screenMuted = {};
            if (!parsed.screenMutedTouched) parsed.screenMutedTouched = {};
        if (!parsed.autoRotateMode) parsed.autoRotateMode = 'auto-switch';
            appState = { ...appState, ...parsed };
        }
        document.getElementById('theme-select').value = appState.theme;
        document.getElementById('bandwidth-mode').value = appState.bandwidth;
        var armSel = document.getElementById('autorotate-mode'); if (armSel) armSel.value = appState.autoRotateMode || 'auto-switch';
        const savedSources = localStorage.getItem('tv_monitor_sources');
        document.getElementById('source-editor').value = savedSources || DEFAULT_SOURCES_TEXT;
    }

    function updateAutoRotateMode() { appState.autoRotateMode = document.getElementById("autorotate-mode").value; saveConfig(); }
    function saveConfig() {
        appState.bandwidth = document.getElementById('bandwidth-mode').value;
        localStorage.setItem('tv_monitor_config', JSON.stringify(appState));
        localStorage.setItem('tv_monitor_sources', document.getElementById('source-editor').value);
    }
    function updateThemeAndSave() {
        appState.theme = document.getElementById('theme-select').value;
        saveConfig();
        updateTheme();
    }

    // --- 源解析：支持 markdown 标题分类 + 同名合并 URL ---
    function parseSources(text) {
        const lines = text.split('\\n');
        const sources = [];
        const categorySet = new Set();  // 所有出现过的标题
        const usedCategorySet = new Set(); // 实际含有频道的标题
        let currentCategory = '';

        lines.forEach(raw => {
            const line = raw.trim();
            if (!line) return;
            // Markdown 标题：## / ### / #### …
            const h = line.match(/^(#{1,6})\\s+(.+)$/);
            if (h) {
                currentCategory = h[2].trim();
                categorySet.add(currentCategory);
                return;
            }
            // 行首注释（独立 # 行）
            if (line.startsWith('#')) return;

            const comma = line.indexOf(',');
            if (comma < 0) return;
            const name = line.slice(0, comma).trim();
            const url  = line.slice(comma + 1).trim();
            if (!name || !url) return;

            // 同名 + 同类别 → 合并为多 URL
            const key = currentCategory + '\\u0000' + name.toLowerCase();
            const existing = sources.find(s => s._key === key);
            if (existing) {
                if (!existing.urls.includes(url)) existing.urls.push(url);
            } else {
                sources.push({ name, urls: [url], category: currentCategory, _key: key });
                usedCategorySet.add(currentCategory);
            }
        });
        sources.forEach(s => delete s._key);

        appState.sources = sources;
        // 仅保留含有至少一个频道的类别（避免空类别出现在筛选下拉中）
        appState.categories = Array.from(usedCategorySet);

        // 修正可能越界的 assignment / 不存在的源
        SCREEN_IDS.forEach(id => {
            const idx = appState.assignments[id];
            if (idx === undefined || idx < 0 || idx >= sources.length) {
                appState.assignments[id] = sources.length > 0 ? 0 : -1;
            }
        });
    }

    // --- 渲染：屏幕格 ---
    function renderGrid() {
        const grid = document.getElementById('monitor-grid');
        const N = appState.activeScreens.length;
        if (N === 0) {
            document.getElementById('empty-state').classList.remove('hidden');
            grid.innerHTML = '';
            // 关闭所有播放器
            SCREEN_IDS.forEach(id => {
                if (document.getElementById(\`video-\${id}\`)) destroyPlayer(id);
            });
            return;
        }
        document.getElementById('empty-state').classList.add('hidden');

        // 销毁不再激活的播放器
        SCREEN_IDS.forEach(id => {
            if (!appState.activeScreens.includes(id)) {
                destroyPlayer(id);
            }
        });

        applyLayout(true);
        renderSourcePills(); // 同步 pill 内容
    }

    function createMonitorUnit(id) {
        const div = document.createElement('div');
        div.className = 'monitor-unit';
        div.dataset.id = id;
        div.innerHTML = \`
            <div class="video-wrapper">
                <video id="video-\${id}" class="w-full h-full" controls playsinline></video>
                <div class="source-pill" id="pill-\${id}" data-id="\${id}" tabindex="0" role="button" aria-label="源选择">
                    <span class="pill-dot" aria-hidden="true"></span>
                    <span class="pill-label" id="pill-label-\${id}">--</span>
                    <span class="pill-caret" aria-hidden="true">▼</span>
                    <div class="source-dropdown" id="dropdown-\${id}" role="menu"></div>
                </div>
                <div class="overlay-info" id="status-\${id}">Ready</div>
            </div>
        \`;
        // pill 点击切换下拉；点击后保持 .pill-expanded 直到下拉关闭
        const pill = div.querySelector(\`#pill-\${id}\`);
        pill.addEventListener('click', (e) => {
            e.stopPropagation();
            const dd = document.getElementById(\`dropdown-\${id}\`);
            const isOpen = dd.classList.contains('open');
            // 关闭其它屏的下拉与 expanded
            document.querySelectorAll('.source-dropdown.open').forEach(o => {
                o.classList.remove('open');
                o.parentElement.classList.remove('pill-expanded');
            });
            if (!isOpen) {
                populateSourceDropdown(id);
                dd.classList.add('open');
                pill.classList.add('pill-expanded');
            } else {
                pill.classList.remove('pill-expanded');
            }
        });
        return div;
    }

    function renderSourcePills() {
        appState.activeScreens.forEach(id => {
            updatePillLabel(id);
        });
    }

    function updatePillLabel(id) {
        const label = document.getElementById(\`pill-label-\${id}\`);
        if (!label) return;
        const idx = appState.assignments[id];
        const src = appState.sources[idx];
        if (!src) { label.textContent = '--'; return; }
        const sel = appState.screenSource[id] || 'auto';
        let txt = src.name;
        if (sel === 'auto') {
            if (src.urls.length > 1) txt += \` · 自动(\${src.urls.length})\`;
        } else {
            txt += \` · 固定\`;
        }
        label.textContent = txt;
    }

    function populateSourceDropdown(id) {
        const dd = document.getElementById(\`dropdown-\${id}\`);
        if (!dd) return;
        dd.innerHTML = '';
        const idx = appState.assignments[id];
        const src = appState.sources[idx];
        if (!src) return;
        const currentSel = appState.screenSource[id] || 'auto';

        // 自动
        const auto = document.createElement('div');
        auto.className = 'source-option' + (currentSel === 'auto' ? ' active' : '');
        auto.innerHTML = \`<span class="opt-tag">AUTO</span>自动（轮流 / 失败切换）\`;
        auto.onclick = (e) => {
            e.stopPropagation();
            appState.screenSource[id] = 'auto';
            saveConfig();
            dd.classList.remove('open');
            dd.parentElement.classList.remove('pill-expanded');
            updatePillLabel(id);
            initPlayer(id);
        };
        dd.appendChild(auto);

        // 分隔
        const sep = document.createElement('div');
        sep.style.cssText = 'height:1px;background:rgba(255,255,255,0.1);margin:4px 0;';
        dd.appendChild(sep);

        // 每个 URL
        src.urls.forEach((u, i) => {
            const opt = document.createElement('div');
            opt.className = 'source-option' + (currentSel === u ? ' active' : '');
            // 短显示：域名 + 路径尾段
            let pretty = u;
            try {
                const x = new URL(u);
                pretty = x.host + (x.pathname.length > 30 ? x.pathname.slice(0, 27) + '...' : x.pathname);
            } catch(_) {}
            opt.innerHTML = \`<span class="opt-tag">L\${i+1}</span>\${pretty}\`;
            opt.title = u;
            opt.onclick = (e) => {
                e.stopPropagation();
                appState.screenSource[id] = u;
                saveConfig();
                dd.classList.remove('open');
                dd.parentElement.classList.remove('pill-expanded');
                updatePillLabel(id);
                initPlayer(id);
            };
            dd.appendChild(opt);
        });
    }

    // --- 屏幕配置面板（两级下拉） ---
    function renderSettingsControls() {
        const container = document.getElementById('screen-controls');
        container.innerHTML = '';
        SCREEN_IDS.forEach(id => {
            const isActive = appState.activeScreens.includes(id);
            const savedIdx = appState.assignments[id] !== undefined ? appState.assignments[id] : -1;
            const currentSourceIdx = (savedIdx >= 0 && savedIdx < appState.sources.length) ? savedIdx : -1;
            const currentSource = currentSourceIdx >= 0 ? appState.sources[currentSourceIdx] : null;
            // 每次打开设置时，类别筛选默认 = 当前源所属类别（UI 临时态，不持久化）
            uiCategoryFilter[id] = currentSource ? (currentSource.category || '') : '';

            const row = document.createElement('div');
            row.className = 'flex items-center gap-2 bg-gray-50 dark:bg-gray-800/50 p-2 rounded';

            const toggleWrapper = document.createElement('label');
            toggleWrapper.className = 'flex items-center gap-2 cursor-pointer min-w-[88px]';
            toggleWrapper.innerHTML = \`
                <input type="checkbox" class="screen-toggle form-checkbox h-4 w-4 text-blue-600 rounded"
                    data-id="\${id}" \${isActive ? 'checked' : ''}>
                <span class="text-sm font-bold">Screen \${id}</span>
            \`;
            toggleWrapper.querySelector('input').onchange = (e) => handleScreenToggle(id, e.target.checked);

            // 类别下拉
            const catWrap = document.createElement('div');
            catWrap.className = 'flex flex-col gap-1 flex-1 min-w-0';
            const catLabel = document.createElement('span');
            catLabel.className = 'text-[10px] text-gray-400';
            catLabel.textContent = '类别';
            const catSelect = document.createElement('select');
            catSelect.className = 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-blue-500 w-full';
            catSelect.disabled = !isActive;
            const allOpt = document.createElement('option');
            allOpt.value = ''; allOpt.text = '全部';
            catSelect.appendChild(allOpt);
            appState.categories.forEach(c => {
                const o = document.createElement('option');
                o.value = c; o.text = c;
                catSelect.appendChild(o);
            });
            catSelect.value = uiCategoryFilter[id] || '';
            catSelect.onchange = () => {
                uiCategoryFilter[id] = catSelect.value;
                repopulateChannelSelect(id);
            };
            catWrap.appendChild(catLabel);
            catWrap.appendChild(catSelect);

            // 频道下拉
            const chanWrap = document.createElement('div');
            chanWrap.className = 'flex flex-col gap-1 flex-1 min-w-0';
            const chanLabel = document.createElement('span');
            chanLabel.className = 'text-[10px] text-gray-400';
            chanLabel.textContent = '频道';
            const chanSelect = document.createElement('select');
            chanSelect.id = \`chan-select-\${id}\`;
            chanSelect.className = 'bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded px-2 py-1 text-xs focus:ring-1 focus:ring-blue-500 w-full';
            chanSelect.disabled = !isActive;
            chanWrap.appendChild(chanLabel);
            chanWrap.appendChild(chanSelect);
            row.appendChild(toggleWrapper);
            row.appendChild(catWrap);
            row.appendChild(chanWrap);
            container.appendChild(row);
            // 必须在挂到 DOM 后再填充（repopulateChannelSelect 用 getElementById）
            repopulateChannelSelect(id);
            chanSelect.onchange = () => changeSource(id, chanSelect.value);
        });
    }

    function repopulateChannelSelect(id) {
        const sel = document.getElementById(\`chan-select-\${id}\`);
        if (!sel) return;
        const cat = uiCategoryFilter[id] || '';
        const filtered = appState.sources
            .map((s, i) => ({ s, i }))
            .filter(({ s }) => !cat || s.category === cat);

        sel.innerHTML = '';
        if (filtered.length === 0) {
            const o = document.createElement('option');
            o.text = '无内容源'; o.value = -1;
            sel.appendChild(o);
            return;
        }
        filtered.forEach(({ s, i }) => {
            const o = document.createElement('option');
            o.value = i;
            const cnt = s.urls.length > 1 ? \` (\${s.urls.length}源)\` : '';
            const cat = s.category ? \`[\${s.category}] \` : '';
            o.text = cat + s.name + cnt;
            sel.appendChild(o);
        });
        const saved = appState.assignments[id];
        if (saved !== undefined && saved >= 0 && filtered.some(({ i }) => i === saved)) {
            sel.value = saved;
        } else {
            sel.value = filtered[0].i;
        }
    }

    function handleScreenToggle(id, isChecked) {
        if (isChecked) {
            if (!appState.activeScreens.includes(id)) appState.activeScreens.push(id);
            // 给一个默认 assignment
            if (appState.assignments[id] === undefined || appState.assignments[id] < 0) {
                appState.assignments[id] = 0;
            }
        } else {
            appState.activeScreens = appState.activeScreens.filter(s => s !== id);
            destroyPlayer(id);
        }
        saveConfig();
        renderGrid();
        renderSettingsControls();
    }

    function changeSource(screenId, sourceIndex) {
        const idx = parseInt(sourceIndex);
        appState.assignments[screenId] = idx;
        // 切换频道时重置源选择为 auto
        appState.screenSource[screenId] = 'auto';
        saveConfig();
        if (appState.activeScreens.includes(screenId)) {
            initPlayer(screenId);
        }
        updatePillLabel(screenId);
    }

    /* ============================================================================
       播放器：failover / 固定源 / mute 保留
       ============================================================================ */
    function initPlayer(id) {
        const video = document.getElementById(\`video-\${id}\`);
        if (!video) return;
        const sourceIdx = appState.assignments[id];
        if (sourceIdx < 0 || !appState.sources[sourceIdx]) {
            showStatus(id, "No Source");
            return;
        }
        const src = appState.sources[sourceIdx];
        if (src.urls.length === 0) {
            showStatus(id, "Empty URLs");
            return;
        }

        // 清旧
        destroyPlayer(id);

        const sel = appState.screenSource[id] || 'auto';
        if (sel === 'auto') {
            // v1.3: cycleCount tracks how many full source-rotation cycles have failed.
            // After 3 cycles, rotate to next channel.
            failoverState[id] = { mode: 'auto', lineIndex: 0, trySecure: true, cycleCount: 0 };
            loadUrl(id, src.urls[0], true, src, 0);
        } else {
            // 固定源：直接尝试所选 URL；失败重试同一 URL
            failoverState[id] = { mode: 'fixed', url: sel, trySecure: true, retryCount: 0 };
            loadUrl(id, sel, true, src, -1);
        }
        // v1.3: Start buffer/stall detection
        startBufferDetection(id);
    }

    function loadUrl(id, url, trySecure, srcGroup, lineIndex) {
        const video = document.getElementById(\`video-\${id}\`);
        if (!video) return;
        const status = document.getElementById(\`status-\${id}\`);

        // 清旧 hls
        if (hlsInstances[id]) { hlsInstances[id].destroy(); delete hlsInstances[id]; }
        if (retryTimers[id])  { clearTimeout(retryTimers[id]); delete retryTimers[id]; }

        let actualUrl = url;
        let isUpgrading = false;
        if (trySecure && actualUrl.toLowerCase().startsWith('http://')) {
            actualUrl = actualUrl.replace(/^http:\\/\\//i, 'https://');
            isUpgrading = true;
        }

        // UI 反馈
        const sel = appState.screenSource[id] || 'auto';
        let prefix;
        if (sel === 'auto') {
            const li = lineIndex + 1;
            prefix = srcGroup.urls.length > 1 ? \`L\${li}/\${srcGroup.urls.length}\` : 'Loading';
        } else {
            prefix = 'FIXED';
        }
        const secureInfo = isUpgrading ? ' ↗https' : '';
        showStatus(id, \`\${prefix}\${secureInfo} …\`);

        // 设置 muted：尊重持久化偏好；未交互过则默认 muted
        const touched = appState.screenMutedTouched[id];
        const wantedMuted = touched ? !!appState.screenMuted[id] : true;
        // 用 programmaticMuted 标记区分"程序设置"与"用户操作"
        video._programmaticMuted = true;
        video.muted = wantedMuted;
        // 下一帧解除标记，确保上述赋值触发的 volumechange 被忽略
        requestAnimationFrame(() => { video._programmaticMuted = false; });

        // 监听 volumechange（仅绑定一次）
        if (!video.dataset.boundVol) {
            video.addEventListener('volumechange', () => {
                if (video._programmaticMuted) return; // 忽略程序化变更
                appState.screenMuted[id] = video.muted;
                appState.screenMutedTouched[id] = true;
                saveConfig();
                updateUnmuteHint(id);
            });
            video.dataset.boundVol = '1';
        }

        // 失败处理
        const handleFailover = (reason) => {
            console.warn(\`[Screen \${id}] failover: \${reason} | mode=\${failoverState[id].mode} line=\${lineIndex} upgrading=\${isUpgrading}\`);
            const st = failoverState[id];

            if (isUpgrading) {
                // 退回原始 HTTP
                showStatus(id, \`\${prefix} https失败,试http…\`);
                setTimeout(() => loadUrl(id, url, false, srcGroup, lineIndex), 400);
                return;
            }

            if (st.mode === 'fixed') {
                // 固定模式：重试同一 URL（带指数退避，上限 ~16s）
                st.retryCount = (st.retryCount || 0) + 1;
                const delay = Math.min(1500 * st.retryCount, 16000);
                showStatus(id, \`\${prefix} 断讯,\${Math.round(delay/1000)}s后重试 (#\${st.retryCount})\`);
                retryTimers[id] = setTimeout(() => loadUrl(id, st.url, true, srcGroup, -1), delay);
                return;
            }

            // 自动模式：切下一条线路
            const next = (lineIndex + 1) % srcGroup.urls.length;
            if (next === 0) {
                // v1.3: Completed a full cycle. Increment cycleCount.
                st.cycleCount = (st.cycleCount || 0) + 1;
                if (st.cycleCount >= 3) {
                    if (appState.autoRotateMode === 'auto-switch') {
                        showStatus(id, '3 rounds failed, switching...');
                        rotateToNextChannel(id);
                        return;
                    } else {
                        st.cycleCount = 0;
                        st.lineIndex = 0;
                        showStatus(id, 'All lines failed, retrying...');
                        retryTimers[id] = setTimeout(() => loadUrl(id, srcGroup.urls[0], true, srcGroup, 0), 2000);
                        return;
                    }
                }
                showStatus(id, \`全部线路失败,重试第\${st.cycleCount + 1}轮…\`);
            } else {
                showStatus(id, \`\${prefix} 失败,切 L\${next+1}…\`);
            }
            failoverState[id].lineIndex = next;
            retryTimers[id] = setTimeout(() => loadUrl(id, srcGroup.urls[next], true, srcGroup, next), 600);
        };

        // 10s 超时
        retryTimers[id] = setTimeout(() => {
            if (video.readyState < 3) handleFailover('Timeout 10s');
        }, 10000);

        const bandwidthConfig = getHlsConfig();

        if (Hls.isSupported()) {
            // v1.3: backBufferLength/liveSyncDurationCount/lowLatencyMode to fix audio pitch drift
            const hls = new Hls({ ...bandwidthConfig, debug: false, enableWorker: true, lowLatencyMode: false, backBufferLength: 10, liveSyncDurationCount: 3, liveMaxLatencyDurationCount: 8, maxBufferLength: 20, fragLoadingMaxRetry: 6 });
            hlsInstances[id] = hls;
            hls.loadSource(actualUrl);
            hls.attachMedia(video);
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                applyQualityCap(hls);
                video.play().catch(() => {
                    // 自动播放被拦截：若原本想要有声，退回 muted 重试一次
                    if (!video.muted) {
                        video._programmaticMuted = true;
                        video.muted = true;
                        requestAnimationFrame(() => { video._programmaticMuted = false; });
                        video.play().catch(()=>{});
                        showUnmuteHint(id);
                    }
                });
            });
            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            hls.destroy(); delete hlsInstances[id];
                            handleFailover('Network/CORS');
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            hls.recoverMediaError();
                            break;
                        default:
                            hls.destroy(); delete hlsInstances[id];
                            handleFailover('Fatal');
                            break;
                    }
                }
            });
            video.onplaying = () => {
                if (retryTimers[id]) { clearTimeout(retryTimers[id]); delete retryTimers[id]; }
                hideStatus(id);
                failoverState[id] && (failoverState[id].retryCount = 0);
                updateUnmuteHint(id);
            };
        } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = actualUrl;
            video.addEventListener('loadedmetadata', () => {
                video.play().catch(() => {
                    if (!video.muted) {
                        video._programmaticMuted = true;
                        video.muted = true;
                        requestAnimationFrame(() => { video._programmaticMuted = false; });
                        video.play().catch(()=>{});
                        showUnmuteHint(id);
                    }
                });
            }, { once: true });
            video.addEventListener('error', () => handleFailover('Native error'), { once: true });
            video.onplaying = () => {
                if (retryTimers[id]) { clearTimeout(retryTimers[id]); delete retryTimers[id]; }
                hideStatus(id);
                failoverState[id] && (failoverState[id].retryCount = 0);
                updateUnmuteHint(id);
            };
        }
    }

    function showStatus(id, msg) {
        const el = document.getElementById(\`status-\${id}\`);
        if (el) { el.innerText = msg; el.style.display = 'block'; }
    }
    function hideStatus(id) {
        const el = document.getElementById(\`status-\${id}\`);
        if (el) el.style.display = 'none';
    }

    function destroyPlayer(id) {
        if (retryTimers[id]) { clearTimeout(retryTimers[id]); delete retryTimers[id]; }
        if (hlsInstances[id]) { hlsInstances[id].destroy(); delete hlsInstances[id]; }
        // v1.3: Clear buffer detection timer
        if (bufferTimers[id]) { clearInterval(bufferTimers[id]); delete bufferTimers[id]; }
        if (bufferRefreshedFlag[id]) { delete bufferRefreshedFlag[id]; }
        const v = document.getElementById(\`video-\${id}\`);
        if (v) { v.pause(); v.removeAttribute('src'); v.load(); }
        delete failoverState[id];
    }

    // v1.3: Buffer/stall detection — checks every 5s.
    // If video is buffering or stalled (not playing, not user-paused) for >60s,
    // refresh the same source. If still failing after refresh, rotate to next channel.
    const bufferTimers = {};           // per-screen interval timer
    const bufferStallStart = {};       // per-screen timestamp when stall began
    const bufferRefreshedFlag = {};    // per-screen flag: already tried refresh, next time rotate
    const BUFFER_STALL_THRESHOLD_MS = 60 * 1000;  // 60 seconds

    function startBufferDetection(id) {
        // Clear any existing timer
        if (bufferTimers[id]) clearInterval(bufferTimers[id]);
        delete bufferStallStart[id];
        delete bufferRefreshedFlag[id];

        bufferTimers[id] = setInterval(() => {
            const video = document.getElementById(\`video-\${id}\`);
            if (!video) return;
            // If user paused, don't trigger
            if (video.paused && !video.ended && video._userPaused) return;
            // If user manually paused (we track via 'pause' event listener below)
            if (video.paused && video.dataset.userPaused === '1') return;

            // Detect stall: video is paused OR readyState < 3 (HAVE_FUTURE_DATA)
            const isStalled = video.paused || video.readyState < 3 || video.seeking;
            if (isStalled) {
                if (!bufferStallStart[id]) {
                    bufferStallStart[id] = Date.now();
                } else if (Date.now() - bufferStallStart[id] > BUFFER_STALL_THRESHOLD_MS) {
                    // Stall exceeded threshold
                    if (!bufferRefreshedFlag[id]) {
                        // First time: refresh the same source
                        console.warn(\`[Screen \${id}] Stall >\${BUFFER_STALL_THRESHOLD_MS/1000}s, refreshing same source\`);
                        bufferRefreshedFlag[id] = true;
                        bufferStallStart[id] = Date.now(); // reset timer for next check
                        showStatus(id, \`停滞>\${BUFFER_STALL_THRESHOLD_MS/1000}s,刷新源…\`);
                        initPlayer(id);  // restart same source
                    } else {
                        // Already refreshed, still stalled — rotate to next channel
                        console.warn(\`[Screen \${id}] Stall persists after refresh, rotating to next channel\`);
                        showStatus(id, \`刷新后仍停滞,换台…\`);
                        bufferRefreshedFlag[id] = false;
                        bufferStallStart[id] = null;
                        rotateToNextChannel(id);
                    }
                }
            } else {
                // Playing fine — reset stall tracking
                bufferStallStart[id] = null;
                bufferRefreshedFlag[id] = false;
            }
        }, 5000);
    }

    // v1.3: Rotate to next channel in source list.
    // Paused if settings modal is open (waits for user to close).
    let pendingRotation = {};  // screenId -> true (waiting for settings close)
    function rotateToNextChannel(screenId) {
        if (appState.autoRotateMode !== 'auto-switch') return;
        // If settings modal is open, defer rotation
        const modal = document.getElementById('settings-modal');
        if (modal && !modal.classList.contains('hidden')) {
            pendingRotation[screenId] = true;
            showStatus(screenId, \`等待设置关闭后换台…\`);
            return;
        }
        pendingRotation[screenId] = false;
        const currentIdx = appState.assignments[screenId];
        const sources = appState.sources;
        if (sources.length === 0) return;
        // Find next channel (skip current). Wrap around.
        let nextIdx = (currentIdx + 1) % sources.length;
        let attempts = 0;
        while (nextIdx === currentIdx && attempts < sources.length) {
            nextIdx = (nextIdx + 1) % sources.length;
            attempts++;
        }
        if (nextIdx === currentIdx) return; // only one channel, can't rotate
        console.log(\`[Screen \${screenId}] Rotating channel: \${currentIdx} → \${nextIdx}\`);
        // Use changeSource to switch channel (resets to auto source mode)
        changeSource(screenId, nextIdx);
    }

    // v1.3: Process pending rotations after settings modal closes
    function processPendingRotations() {
        Object.keys(pendingRotation).forEach(idStr => {
            const id = parseInt(idStr);
            if (pendingRotation[id]) {
                pendingRotation[id] = false;
                // Only rotate if screen is still active
                if (appState.activeScreens.includes(id)) {
                    rotateToNextChannel(id);
                }
            }
        });
    }

    // v1.3: Track user pause events to distinguish from auto-stall
    function initUserPauseTracking() {
        SCREEN_IDS.forEach(id => {
            const v = document.getElementById(\`video-\${id}\`);
            if (!v || v.dataset.boundPause) return;
            v.addEventListener('pause', () => {
                // Mark as user-paused (will be cleared on play)
                v.dataset.userPaused = '1';
            });
            v.addEventListener('play', () => {
                v.dataset.userPaused = '0';
            });
            v.dataset.boundPause = '1';
        });
    }

    function getHlsConfig() {
        const mode = appState.bandwidth;
        let config = {};
        if (mode === 'saver' || mode === 'low') {
            config.maxMaxBufferLength = 10; config.maxBufferLength = 10;
        } else {
            config.maxMaxBufferLength = 60;
        }
        return config;
    }
    function applyQualityCap(hls) {
        const mode = appState.bandwidth;
        if (mode === 'low') {
            hls.currentLevel = 0; hls.autoLevelEnabled = false;
        } else if (mode === 'saver') {
            hls.autoLevelEnabled = true; hls.autoLevelCapping = findLevelIndex(hls.levels, 480);
        } else if (mode === 'balanced') {
            hls.autoLevelEnabled = true; hls.autoLevelCapping = findLevelIndex(hls.levels, 720);
        } else {
            hls.autoLevelEnabled = true; hls.autoLevelCapping = -1;
        }
    }
    function findLevelIndex(levels, maxHeight) {
        let best = -1;
        levels.forEach((lv, i) => { if (lv.height <= maxHeight) best = i; });
        return best === -1 ? 0 : best;
    }

    /* "轻触解除静音"浮层 */
    function showUnmuteHint(id) {
        const wrap = document.querySelector(\`.monitor-unit[data-id="\${id}"] .video-wrapper\`);
        if (!wrap) return;
        if (wrap.querySelector('.unmute-hint')) return;
        const hint = document.createElement('div');
        hint.className = 'unmute-hint';
        hint.innerHTML = \`<div class="unmute-inner">🔊 轻触解除静音</div>\`;
        hint.onclick = (e) => {
            e.stopPropagation();
            const v = document.getElementById(\`video-\${id}\`);
            if (v) { v.muted = false; v.play().catch(()=>{}); }
            hint.remove();
        };
        wrap.appendChild(hint);
    }
    function updateUnmuteHint(id) {
        const v = document.getElementById(\`video-\${id}\`);
        const wrap = document.querySelector(\`.monitor-unit[data-id="\${id}"] .video-wrapper\`);
        if (!v || !wrap) return;
        const hint = wrap.querySelector('.unmute-hint');
        if (v.muted && appState.screenMutedTouched[id] && appState.screenMuted[id] === false) {
            // 想要声音但现在被静音 → 显示提示
            if (!hint) showUnmuteHint(id);
        } else {
            if (hint) hint.remove();
        }
    }

    /* ============================================================================
       UI 控制
       ============================================================================ */
    function toggleSettings() {
        const modal = document.getElementById('settings-modal');
        const isOpen = !modal.classList.contains('hidden');
        if (isOpen) {
            modal.classList.add('hidden');
            // v1.3: Settings closed — process any pending channel rotations
            setTimeout(() => processPendingRotations(), 200);
        } else {
            renderSettingsControls();
            // v1.4: Always reset to center when opening
            const mc = document.getElementById("settings-content");
            if (mc) { mc.style.left = ""; mc.style.top = ""; mc.style.transform = ""; mc.style.margin = ""; }
            modal.classList.remove('hidden');
            switchTab('tab-general');
        }
    }

    function switchTab(tabId) {
        ['tab-general','tab-sources','tab-about'].forEach(t => {
            document.getElementById(t).classList.add('hidden');
        });
        document.getElementById(tabId).classList.remove('hidden');

        const btns = document.querySelectorAll('.tab-btn');
        const activeClass = "tab-btn flex-1 py-3 text-sm font-medium border-b-2 border-blue-500 text-blue-600 dark:text-blue-400 bg-white dark:bg-gray-900";
        const inactiveClass = "tab-btn flex-1 py-3 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 bg-gray-50 dark:bg-gray-850";
        btns.forEach(b => b.className = inactiveClass);
        if (tabId === 'tab-general') document.getElementById('btn-tab-general').className = activeClass;
        else if (tabId === 'tab-sources') document.getElementById('btn-tab-sources').className = activeClass;
        else document.getElementById('btn-tab-about').className = activeClass;
    }

    function switchAbout(which) {
        const r = document.getElementById('about-readme');
        const c = document.getElementById('about-changelog');
        const br = document.getElementById('btn-about-readme');
        const bc = document.getElementById('btn-about-changelog');
        if (which === 'readme') {
            r.classList.remove('hidden'); c.classList.add('hidden');
            br.className = 'py-2 border-b-2 border-blue-500 text-blue-600 dark:text-blue-400';
            bc.className = 'py-2 border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400';
        } else {
            r.classList.add('hidden'); c.classList.remove('hidden');
            bc.className = 'py-2 border-b-2 border-blue-500 text-blue-600 dark:text-blue-400';
            br.className = 'py-2 border-b-2 border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400';
        }
    }

    function renderAbout() {
        document.getElementById('about-readme').innerHTML = renderMarkdownLite(README_TEXT);
        document.getElementById('about-changelog').innerHTML = renderMarkdownLite(CHANGELOG_TEXT);
    }

    // 极简 markdown 渲染：h1/h2/h3、代码块、行内 code、列表、hr、链接
    function renderMarkdownLite(md) {
        const escapeHtml = (s) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        const lines = md.split('\\n');
        let html = '';
        let inCode = false, codeBuf = [];
        let inList = false;
        const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
        for (let i = 0; i < lines.length; i++) {
            const l = lines[i];
            if (l.trim().startsWith('\`\`\`')) {
                if (inCode) {
                    html += \`<pre><code>\${escapeHtml(codeBuf.join('\\n'))}</code></pre>\`;
                    codeBuf = []; inCode = false;
                } else {
                    closeList();
                    inCode = true;
                }
                continue;
            }
            if (inCode) { codeBuf.push(l); continue; }
            const t = l.trim();
            if (!t) { closeList(); continue; }
            if (t === '---' || t === '***') { closeList(); html += '<hr/>'; continue; }
            const h = t.match(/^(#{1,6})\\s+(.*)$/);
            if (h) {
                closeList();
                const lvl = h[1].length;
                html += \`<h\${lvl}>\${escapeHtml(h[2])}</h\${lvl}>\`;
                continue;
            }
            if (/^[-*]\\s+/.test(t)) {
                if (!inList) { html += '<ul>'; inList = true; }
                html += \`<li>\${inlineMd(t.replace(/^[-*]\\s+/, ''))}</li>\`;
                continue;
            }
            // blockquote
            if (t.startsWith('> ')) {
                closeList();
                html += \`<p style="border-left:3px solid rgba(147,197,253,0.6);padding-left:8px;color:rgba(229,231,235,0.85);">\${inlineMd(t.slice(2))}</p>\`;
                continue;
            }
            closeList();
            html += \`<p>\${inlineMd(t)}</p>\`;
        }
        if (inCode) html += \`<pre><code>\${escapeHtml(codeBuf.join('\\n'))}</code></pre>\`;
        closeList();
        return html;

        function inlineMd(s) {
            s = escapeHtml(s);
            s = s.replace(/\`([^\`]+)\`/g, '<code>$1</code>');
            s = s.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
            s = s.replace(/\\[([^\\]]+)\\]\\((https?:[^)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
            return s;
        }
    }

    // --- 源导入 / 导出 ---
    function exportSources() {
        // 把解析结果回写为带分类标记的 txt
        let content = '';
        let lastCat = '__INIT__';
        appState.sources.forEach(s => {
            if (s.category !== lastCat) {
                if (s.category) content += \`\\n## \${s.category}\\n\\n\`;
                else content += '\\n';
                lastCat = s.category;
            }
            s.urls.forEach(u => { content += \`\${s.name},\${u}\\n\`; });
        });
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        // v1.3: Filename includes date-time: tv_list-YYYYMMDD-HHMMSS.txt
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const ts = \`\${now.getFullYear()}\${pad(now.getMonth()+1)}\${pad(now.getDate())}-\${pad(now.getHours())}\${pad(now.getMinutes())}\${pad(now.getSeconds())}\`;
        a.href = url; a.download = \`tv_list-\${ts}.txt\`; a.click();
        URL.revokeObjectURL(url);
    }
    function triggerImport() { document.getElementById('file-import').click(); }
    function importSources(input) {
        const f = input.files[0]; if (!f) return;
        const r = new FileReader();
        r.onload = (e) => { document.getElementById('source-editor').value = e.target.result; };
        r.readAsText(f);
        input.value = '';
    }
    function saveSourcesAndReload() {
        const text = document.getElementById('source-editor').value;
        parseSources(text);
        saveConfig();
        // 重置每屏源选择为 auto（防止固定源已不存在）
        appState.activeScreens.forEach(id => { appState.screenSource[id] = 'auto'; });
        appState.activeScreens.forEach(id => initPlayer(id));
        renderSettingsControls();
        renderSourcePills();
        const btn = document.querySelector('button[onclick="saveSourcesAndReload()"]');
        const orig = btn.innerText;
        btn.innerText = "已保存!";
        setTimeout(() => btn.innerText = orig, 1500);
    }

    // --- 主题 ---
    function initTheme() {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (appState.theme === 'system') updateTheme();
        });
        updateTheme();
    }
    function updateTheme() {
        const m = appState.theme;
        const html = document.documentElement;
        if (m === 'dark') html.classList.add('dark');
        else if (m === 'light') html.classList.remove('dark');
        else {
            if (window.matchMedia('(prefers-color-scheme: dark)').matches) html.classList.add('dark');
            else html.classList.remove('dark');
        }
    }
    </script>
<script src="https://static.cloudflareinsights.com/beacon.min.js/vcd15cbe7772f49c399c6a5babf22c1241717689176015" xintegrity="sha512-ZpsOmlRQV6y907TI0dKBHq9Md29nnaEIPlkf84rnaERnq6zvWvPUqr2ft8M1aS28oN72PdrCzSjY4U6VaAw1EQ==" data-cf-beacon='{"version":"2024.11.0","token":"c5a8ac315a3749018830bbca6eced246","r":1,"server_timing":{"name":{"cfCacheStatus":true,"cfEdge":true,"cfExtPri":true,"cfL4":true,"cfOrigin":true,"cfSpeedBrain":true},"location_startswith":null}}' crossorigin="anonymous"></script>
</body>
</html>
`;

addEventListener("fetch", (event) => {
  event.respondWith((async () => {
    const request = event.request;
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, OPTIONS',
          'Access-Control-Allow-Headers': '*',
        },
      });
    }

    if (path === '/' || path === '/index.html' || path === '') {
      return new Response(HTML_BODY, {
        status: 200,
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'CDN-Cache-Control': 'no-store',
        },
      });
    }

    if (path === '/favicon.ico') {
      return new Response(null, { status: 204 });
    }

      return new Response("Not Found", { status: 404 });
  })());
});
