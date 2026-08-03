"""
vidsync QQ Shizi (企鹅号) adapter
===================================
腾讯内容开放平台视频草稿保存。

页面结构（HTML 探查）：
- 视频上传：input[type=file][accept*='video']（hidden）
- 发布页 URL：https://shizi.qq.com/creation/video
- 表单动态加载（视频上传后才出现）

格式约束：
- 视频：4GB（Chrome），10h
- 封面：16:9，1280×720 推荐
- 标题：6-30 字
- 标签：自定义
"""
from __future__ import annotations

import logging

from .base import BaseAdapter, Material, AdapterResult

logger = logging.getLogger(__name__)


class QQShiziAdapter(BaseAdapter):
    platform_id = "qq_shizi"
    platform_name = "企鹅号"
    platform_url = "https://shizi.qq.com/creation/video"
    cover_ratio_landscape = "16:9"
    title_max_chars = 30
    tag_max_count = 10
    tag_format = "plain"
    needs_landscape_cover = True

    def save_draft(self, material: Material) -> AdapterResult:
        try:
            self.inject_cookies(domains=["qq.com"])
            self.new_page()

            logger.info("[%s] navigating to %s", self.platform_id, self.platform_url)
            self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=30000)
            self.human_pause(3)
            self.screenshot("01_landed")

            if not self._check_logged_in():
                return AdapterResult(
                    platform_id=self.platform_id,
                    platform_name=self.platform_name,
                    status="failed",
                    error="未登录或 cookie 已失效",
                )

            # 上传视频
            self._upload_video(material.video_path)
            self.screenshot("02_video_uploaded")

            # 等待表单
            self._wait_form_ready()
            self.screenshot("03_form_ready")

            # 上传封面
            self._upload_cover(material.horizontal_cover_path)
            self.screenshot("04_cover_uploaded")

            # 填标题
            self._fill_title(material.long_title[:30])
            self.screenshot("05_title_filled")

            # 填简介
            self._fill_description(material.effective_description)
            self.screenshot("06_desc_filled")

            # 保存草稿
            draft_url = self._save_draft()
            self.screenshot("07_draft_saved")

            self.run_logger.record_platform_result(
                platform_id=self.platform_id,
                status="success",
                draft_url=draft_url or self.platform_url,
            )
            return AdapterResult(
                platform_id=self.platform_id,
                platform_name=self.platform_name,
                status="success",
                draft_url=draft_url or self.platform_url,
            )

        except Exception as e:
            logger.exception("[%s] save_draft failed", self.platform_id)
            self.save_html_snapshot("error")
            self.save_dom_state()
            self.run_logger.record_platform_result(
                platform_id=self.platform_id,
                status="failed",
                error=str(e),
            )
            return AdapterResult(
                platform_id=self.platform_id,
                platform_name=self.platform_name,
                status="failed",
                error=str(e),
            )

    def _check_logged_in(self) -> bool:
        try:
            if "login" in self.page.url or "passport" in self.page.url:
                return False
            return True
        except Exception:
            return False

    def _upload_video(self, video_path: str):
        for sel in ["input[type=file][accept*='video']", "input[type=file]"]:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=10000)
                self.page.set_input_files(sel, video_path)
                logger.info("[%s] video uploaded via %s", self.platform_id, sel)
                return
            except Exception:
                continue
        self.save_html_snapshot("video_upload_failed")
        raise RuntimeError("video upload failed")

    def _wait_form_ready(self, timeout_ms: int = 60000):
        logger.info("[%s] waiting for form...", self.platform_id)
        self.human_pause(5)
        try:
            self.wait_for(
                "form ready",
                lambda: self.page.query_selector("input[placeholder*='标题']")
                       or self.page.query_selector("[contenteditable='true']")
                       or self.page.query_selector("textarea")
                       or self.page.query_selector("button:has-text('草稿')"),
                timeout_ms=timeout_ms,
                interval_ms=2000,
            )
            logger.info("[%s] form ready", self.platform_id)
        except TimeoutError:
            logger.warning("[%s] form not ready", self.platform_id)
        self.human_pause(2)

    def _upload_cover(self, cover_path: str):
        for sel in ["text=上传封面", "text=更改封面", "text=选择封面",
                    ".cover-upload", "[class*='cover']"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    with self.page.expect_file_chooser(timeout=10000) as fc_info:
                        el.click()
                    fc = fc_info.value
                    fc.set_files(cover_path)
                    logger.info("[%s] cover uploaded via %s", self.platform_id, sel)
                    self.human_pause(2)
                    return
            except Exception:
                continue
        for sel in ["input[type=file][accept*='image']"]:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=5000)
                self.page.set_input_files(sel, cover_path)
                logger.info("[%s] cover uploaded via image input", self.platform_id)
                self.human_pause(2)
                return
            except Exception:
                continue
        logger.warning("[%s] cover upload skipped", self.platform_id)

    def _fill_title(self, title: str):
        for sel in ["input[placeholder*='标题']",
                    "input[placeholder*='填写标题']",
                    ".title-input input",
                    "input[type='text']:visible"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click()
                    self.page.keyboard.type(title, delay=50)
                    logger.info("[%s] title filled: %s", self.platform_id, title[:30])
                    return
            except Exception:
                continue
        logger.warning("[%s] title fill skipped", self.platform_id)

    def _fill_description(self, desc: str):
        try:
            found = self.page.evaluate("""() => {
                const el = document.querySelector('[contenteditable="true"]');
                if (el) { el.focus(); return true; }
                return false;
            }""")
            if found:
                self.page.keyboard.type(desc, delay=30)
                logger.info("[%s] description filled via contenteditable", self.platform_id)
                return
        except Exception:
            pass
        for sel in ["textarea[placeholder*='简介']", "textarea[placeholder*='描述']", "textarea"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click()
                    self.page.keyboard.type(desc, delay=30)
                    logger.info("[%s] description filled via %s", self.platform_id, sel)
                    return
            except Exception:
                continue
        logger.warning("[%s] description fill skipped", self.platform_id)

    def _save_draft(self) -> str | None:
        for sel in ["text=存草稿", "text=保存草稿", "text=暂存离开",
                    "button:has-text('草稿')", "[class*='draft']"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    try:
                        el.click(timeout=3000)
                    except Exception:
                        el.evaluate("el => el.click()")
                    self.human_pause(3)
                    logger.info("[%s] draft saved (via %s)", self.platform_id, sel)
                    return self.page.url
            except Exception:
                continue
        self.save_html_snapshot("save_draft_not_found")
        logger.warning("[%s] no save draft button found", self.platform_id)
        return self.page.url
