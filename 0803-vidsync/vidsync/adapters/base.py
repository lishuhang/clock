"""
vidsync adapter base class
===========================
所有平台 adapter 的抽象基类。
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, BrowserContext

from ..processors.cookies import Cookie
from ..processors.logger import RunLogger

logger = logging.getLogger(__name__)


@dataclass
class Material:
    """编辑提供的物料。"""
    # 视频源文件（竖屏 9:16）
    video_path: str
    # 竖屏封面（视频号规格 1080×1260）
    vertical_cover_path: str
    # 横屏封面（16:9）
    horizontal_cover_path: str
    # 短标题（≤12 字）
    short_title: str
    # 长标题（≤22 字，超长截断）
    long_title: str
    # 关键字（5-10 个，逗号分隔的字符串或列表）
    keywords: list[str] | str
    # 视频简介（可选，留空时由 adapter 复制长标题）
    description: str = ""

    def __post_init__(self):
        if isinstance(self.keywords, str):
            # 逗号或空格分隔
            import re
            parts = re.split(r"[,，\s]+", self.keywords)
            self.keywords = [k.strip() for k in parts if k.strip()]

    @property
    def effective_description(self) -> str:
        """如未填简介，用长标题代替。"""
        return self.description or self.long_title


@dataclass
class AdapterResult:
    """adapter 执行结果。"""
    platform_id: str
    platform_name: str
    status: str  # "success" | "failed" | "skipped"
    draft_url: str | None = None
    error: str | None = None
    expires_at: str | None = None  # ISO 字符串，草稿过期时间
    extra: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """平台 adapter 抽象基类。"""

    platform_id: str = "base"
    platform_name: str = "Base Platform"
    platform_url: str = ""
    # 平台特定的格式约束
    cover_ratio_landscape: str = "16:9"  # 横屏比例
    cover_ratio_vertical: str = "9:16"   # 竖屏比例
    title_max_chars: int = 80
    tag_max_count: int = 10
    tag_format: str = "plain"  # "plain" / "single_hash" (#话题) / "double_hash" (#话题#)
    needs_landscape_cover: bool = False
    needs_vertical_cover: bool = False
    draft_expires_days: int | None = None  # 草稿过期天数

    def __init__(self, cookies: list[Cookie], run_logger: RunLogger,
                 browser_context: BrowserContext, config: dict | None = None):
        self.cookies = cookies
        self.run_logger = run_logger
        self.ctx = browser_context
        self.config = config or {}
        self.page: Page | None = None

    @abstractmethod
    def save_draft(self, material: Material) -> AdapterResult:
        """
        执行保存草稿流程。
        子类必须实现。
        """
        ...

    # ---- 公共辅助方法 ----

    def new_page(self) -> Page:
        """打开新页面。"""
        self.page = self.ctx.new_page()
        return self.page

    def inject_cookies(self, domains: list[str] | None = None):
        """
        把 cookies 注入浏览器 context。
        domains: 只注入匹配这些域名的 cookies；None = 全注入
        """
        from ..processors.cookies import filter_by_domain, filter_expired

        cookies = filter_expired(self.cookies)
        if domains:
            filtered = []
            for d in domains:
                filtered.extend(filter_by_domain(cookies, d))
            cookies = filtered

        playwright_cookies = [c.to_playwright() for c in cookies]
        try:
            self.ctx.add_cookies(playwright_cookies)
            logger.info("[%s] injected %d cookies", self.platform_id, len(playwright_cookies))
        except Exception as e:
            logger.error("[%s] cookie injection failed: %s", self.platform_id, e)
            raise

    def screenshot(self, step_name: str):
        """当前步骤截图。"""
        if self.page:
            self.run_logger.step_screenshot(self.platform_id, self.page, step_name)

    def save_html_snapshot(self, name: str = "page"):
        """失败时保存 HTML 快照。"""
        if self.page:
            self.run_logger.save_html_snapshot(self.platform_id, self.page, name)

    def save_dom_state(self, name: str = "dom_state"):
        """保存 DOM 状态（URL、title、可见按钮）。"""
        if self.page:
            self.run_logger.save_dom_state(self.platform_id, self.page, name)

    def wait_for(self, condition_desc: str, fn, timeout_ms: int = 30000, interval_ms: int = 500):
        """
        等待某条件成立。fn 返回真值则停止。
        超时抛 TimeoutError。
        """
        start = time.time()
        deadline = start + timeout_ms / 1000
        last_err = None
        while time.time() < deadline:
            try:
                result = fn()
                if result:
                    return result
            except Exception as e:
                last_err = e
            time.sleep(interval_ms / 1000)
        msg = f"timeout waiting for: {condition_desc} (last_error={last_err})"
        logger.warning("[%s] %s", self.platform_id, msg)
        raise TimeoutError(msg)

    def human_pause(self, seconds: float = 1.0):
        """模拟真人停顿。"""
        time.sleep(seconds)

    def safe_click(self, selector: str, timeout_ms: int = 10000):
        """安全点击：等待元素出现 → 点击 → 截图。"""
        if not self.page:
            raise RuntimeError("page not opened")
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            self.page.click(selector)
            self.human_pause(0.3)
        except Exception as e:
            logger.error("[%s] click failed: %s (selector=%s)", self.platform_id, e, selector)
            self.save_html_snapshot(f"click_failed_{selector}")
            self.save_dom_state()
            raise

    def safe_fill(self, selector: str, text: str, timeout_ms: int = 10000):
        """安全填充输入框。"""
        if not self.page:
            raise RuntimeError("page not opened")
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            self.page.fill(selector, "")
            self.page.type(selector, text, delay=50)  # 50ms/字符模拟真人
            self.human_pause(0.2)
        except Exception as e:
            logger.error("[%s] fill failed: %s (selector=%s)", self.platform_id, e, selector)
            self.save_html_snapshot(f"fill_failed_{selector}")
            self.save_dom_state()
            raise

    def safe_upload(self, selector: str, file_path: str, timeout_ms: int = 30000):
        """安全上传文件。"""
        if not self.page:
            raise RuntimeError("page not opened")
        try:
            abs_path = str(Path(file_path).resolve())
            # 优先用 set_input_files
            self.page.wait_for_selector(selector, state="attached", timeout=timeout_ms)
            self.page.set_input_files(selector, abs_path)
            logger.info("[%s] uploaded %s via %s", self.platform_id, file_path, selector)
        except Exception as e:
            logger.error("[%s] upload failed: %s (selector=%s, file=%s)",
                         self.platform_id, e, selector, file_path)
            self.save_html_snapshot(f"upload_failed_{selector}")
            self.save_dom_state()
            raise
