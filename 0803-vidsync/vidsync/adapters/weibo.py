"""
vidsync Weibo adapter
======================
微博视频草稿保存。

页面结构（HTML 探查）：
- 视频上传：input._file_hqmwy_20[type=file][accept*='video']
- 标题 placeholder：填写标题（0～30个字）
- 登录后 title="视频发布 - 微博"

格式约束：
- 视频：PC 15GB，≥3s
- 封面：16:9 或 9:16
- 标题：6-30 字（≥6 字最低限制）
- 标签：#话题#（双 #）
"""
from __future__ import annotations

import logging

from .base import BaseAdapter, Material, AdapterResult
from ..processors.title import weibo_validate_title

logger = logging.getLogger(__name__)


class WeiboAdapter(BaseAdapter):
    platform_id = "weibo"
    platform_name = "微博"
    platform_url = "https://weibo.com/upload/channel"
    cover_ratio_landscape = "16:9"
    title_max_chars = 30
    tag_max_count = 10
    tag_format = "double_hash"
    needs_vertical_cover = True

    def save_draft(self, material: Material) -> AdapterResult:
        try:
            self.inject_cookies(domains=["weibo.com"])
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
            self._upload_cover(material.vertical_cover_path)
            self.screenshot("04_cover_uploaded")

            # 填标题（微博 ≥6 字）
            title = weibo_validate_title(material.long_title[:30])
            self._fill_title(title)
            self.screenshot("05_title_filled")

            # 填简介
            self._fill_description(material.effective_description)
            self.screenshot("06_desc_filled")

            # 添加话题（双 #）
            self._add_topics(material.keywords[:10])
            self.screenshot("07_topics_added")

            # 保存草稿
            draft_url = self._save_draft()
            self.screenshot("08_draft_saved")

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
            title = self.page.title()
            return "视频发布" in title or "微博" in title
        except Exception:
            return False

    def _upload_video(self, video_path: str):
        selectors = [
            "input._file_hqmwy_20[accept*='video']",
            "input[type=file][accept*='video']",
            "input[type=file]",
        ]
        for sel in selectors:
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
        self.human_pause(3)
        try:
            self.wait_for(
                "form ready",
                lambda: self.page.query_selector("input[placeholder*='标题']")
                       or self.page.query_selector("[contenteditable='true']")
                       or self.page.query_selector("textarea"),
                timeout_ms=timeout_ms,
                interval_ms=2000,
            )
            logger.info("[%s] form ready", self.platform_id)
        except TimeoutError:
            logger.warning("[%s] form not ready", self.platform_id)
        self.human_pause(2)

    def _upload_cover(self, cover_path: str):
        """上传封面。"""
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
        """填写标题。微博 placeholder 是'填写标题（0～30个字）'。"""
        for sel in ["input[placeholder*='填写标题']",
                    "input[placeholder*='标题']",
                    "input[type='text'][placeholder*='标题']"]:
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
        """填写简介。"""
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

        for sel in ["textarea[placeholder*='简介']", "textarea[placeholder*='描述']",
                    "textarea"]:
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

    def _add_topics(self, topics: list[str]):
        """添加话题。微博双 # 格式。"""
        try:
            editor = self.page.query_selector("[contenteditable='true'], textarea")
            if not editor:
                return
            editor.click()
            self.page.keyboard.press("End")
            for topic in topics[:10]:
                topic_clean = topic.lstrip("#").strip()
                if topic_clean:
                    # 微博双 # 格式
                    self.page.keyboard.type(f" #{topic_clean}#", delay=50)
                    self.human_pause(0.3)
                    self.page.keyboard.press("Space")
                    self.human_pause(0.2)
            logger.info("[%s] topics added", self.platform_id)
        except Exception as e:
            logger.warning("[%s] topic add failed: %s", self.platform_id, e)

    def _save_draft(self) -> str | None:
        """保存草稿。
        重要发现：微博没有"存草稿"功能！
        微博视频上传完毕后会"自动发布微博"（HTML 中确认）。
        因此微博无法保存草稿，编辑需在视频上传前就填好所有信息。
        v0.3 策略：跳过存草稿，返回当前 URL，标记为 "no_draft_feature"。
        """
        logger.warning("[%s] 微博无草稿功能（视频上传后自动发布），跳过存草稿",
                       self.platform_id)
        # 尝试找"存草稿"按钮（虽然大概率没有）
        for sel in ["text=存草稿", "text=保存草稿", "text=暂存离开"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click(timeout=3000)
                    self.human_pause(3)
                    logger.info("[%s] draft saved (via %s)", self.platform_id, sel)
                    return self.page.url
            except Exception:
                continue

        # 微博无草稿功能，返回 extra 标记
        return self.page.url
