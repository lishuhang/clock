"""
vidsync browser launcher
=========================
启动系统已安装的 Chrome/Edge，不下载 Chromium。

策略：
1. 优先使用 channel='chrome'（系统 Google Chrome）
2. 备选 channel='msedge'（系统 Microsoft Edge）
3. 如配置了 executable_path，直接用该路径
4. 不调用 playwright.install()，避免下载 Chromium

使用 persistent_context 模式，保留 storageState 以减少重复登录。
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, BrowserContext, Page, Browser

logger = logging.getLogger(__name__)


# 平台域名 → 起始 URL 映射
PLATFORM_URLS = {
    "bilibili": "https://member.bilibili.com/platform/upload-manager/article",
    "douyin": "https://creator.douyin.com/creator-micro/content/manage?enter_from=publish",
    "xiaohongshu": "https://creator.xiaohongshu.com/publish/publish",
    "kuaishou": "https://cp.kuaishou.com/article/manage/video?status=2&from=publish",
    "wechat_channels": "https://channels.weixin.qq.com/platform/",
    "baijiahao": "https://baijiahao.baidu.com/builder/rc/content",
    "qq_shizi": "https://shizi.qq.com/content/article-manage",
    "tencent_video": "https://mp.v.qq.com/manage/0",
    "weibo": "https://weibo.com/upload/channel",
    "huxiu": "https://www.huxiu.com/contribute.html",
    "kr36": "https://misopen.36kr.com",
    "alipay": "https://c.alipay.com/page/portal/home",
}


class BrowserLauncher:
    """浏览器启动器，单例。"""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def _resolve_channel(self) -> tuple[str, str | None]:
        """
        决定用哪个浏览器 channel。
        返回 (channel, executable_path)
        """
        # 1. 如果配置了 executable_path，直接用
        exe = self.config.get("executable_path")
        if exe and Path(exe).exists():
            logger.info("using executable_path: %s", exe)
            return ("chromium", exe)  # channel=chromium + executable_path = 用指定 Chrome

        # 2. 否则按 channel 配置
        channel = self.config.get("channel", "chrome")
        if channel not in ("chrome", "msedge", "chromium"):
            logger.warning("unknown channel %s, fallback to chrome", channel)
            channel = "chrome"

        # 3. 在 Linux 沙盒环境，chrome/msedge 可能不存在；fallback 到 chromium
        # 但只在 Linux 检测；Windows/Mac 默认 chrome 一定有
        if sys.platform.startswith("linux"):
            # 检测 chrome / msedge / chromium 是否在 PATH
            for candidate in (channel, "chromium", "google-chrome", "microsoft-edge"):
                if self._which(candidate):
                    logger.info("detected browser in PATH: %s", candidate)
                    # playwright channel 名映射
                    if candidate in ("google-chrome",):
                        return ("chrome", None)
                    if candidate in ("microsoft-edge",):
                        return ("msedge", None)
                    return (candidate, None)
            logger.warning("no system browser detected on Linux, will try chromium channel")

        return (channel, None)

    def _which(self, name: str) -> str | None:
        """cross-platform which。"""
        from shutil import which
        return which(name)

    def launch(self) -> BrowserContext:
        """启动浏览器，返回 BrowserContext。"""
        if self._context is not None:
            return self._context

        self._playwright = sync_playwright().start()
        channel, exe = self._resolve_channel()

        launch_kwargs: dict[str, Any] = {
            "headless": self.config.get("headless", False),
            "slow_mo": self.config.get("slow_mo", 100),
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--lang=zh-CN",
            ],
        }
        if exe:
            launch_kwargs["executable_path"] = exe
        else:
            launch_kwargs["channel"] = channel

        viewport = self.config.get("viewport", {"width": 1280, "height": 800})

        try:
            # 用 persistent_context 才能注入 cookies 并跨页保留
            # 但 persistent_context 需要 user_data_dir；这里用一个临时目录
            import tempfile
            user_data_dir = self.config.get("user_data_dir") or tempfile.mkdtemp(prefix="vidsync_")

            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                viewport=viewport,
                **launch_kwargs,
            )
            logger.info("browser launched: channel=%s, exe=%s, headless=%s",
                        channel, exe, launch_kwargs["headless"])
        except Exception as e:
            logger.error("browser launch failed: %s", e)
            # fallback: 尝试默认 chromium（如果 playwright 已下载）
            logger.info("fallback: trying default chromium (no channel)")
            import tempfile
            user_data_dir = tempfile.mkdtemp(prefix="vidsync_fallback_")
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                viewport=viewport,
                headless=launch_kwargs["headless"],
                slow_mo=launch_kwargs["slow_mo"],
                args=launch_kwargs["args"],
            )
            logger.info("fallback chromium launched")

        # 注入反检测脚本
        try:
            self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en']});
                window.chrome = window.chrome || {runtime: {}};
            """)
        except Exception as e:
            logger.warning("inject anti-detect script failed: %s", e)

        return self._context

    def new_page(self) -> Page:
        """打开新页面。"""
        ctx = self.launch()
        return ctx.new_page()

    def close(self):
        """关闭浏览器。"""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("browser closed")


# 模块级单例
_launcher: BrowserLauncher | None = None


def get_launcher(config: dict | None = None) -> BrowserLauncher:
    global _launcher
    if _launcher is None:
        _launcher = BrowserLauncher(config)
    return _launcher


def reset_launcher():
    """重置单例（用于测试）。"""
    global _launcher
    if _launcher:
        _launcher.close()
    _launcher = None


if __name__ == "__main__":
    # 自测：尝试启动浏览器并访问 about:blank
    logging.basicConfig(level=logging.INFO)
    launcher = BrowserLauncher({"headless": True, "channel": "chrome"})
    try:
        page = launcher.new_page()
        page.goto("about:blank")
        print("title:", page.title())
        print("user agent:", page.evaluate("() => navigator.userAgent"))
    finally:
        launcher.close()
