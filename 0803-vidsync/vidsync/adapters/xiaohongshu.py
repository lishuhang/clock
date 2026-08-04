"""
vidsync Xiaohongshu (小红书) adapter
=====================================
小红书创作者平台视频草稿保存。

页面结构（HTML 探查）：
- 视频上传：input.upload-input[type=file][accept*='mp4']
- 登录后显示用户名"娱乐资本论"
- 草稿按钮：.header-draft / .draft-title-box

格式约束：
- 视频：≤500MB，15min（非认证 5min）
- 封面：3:4 = 1080×1440 推荐
- 标题：20 字
- 标签：10 个 #话题
"""
from __future__ import annotations

import logging

from .base import BaseAdapter, Material, AdapterResult

logger = logging.getLogger(__name__)


class XiaohongshuAdapter(BaseAdapter):
    platform_id = "xiaohongshu"
    platform_name = "小红书"
    platform_url = "https://creator.xiaohongshu.com/publish/publish"
    cover_ratio_vertical = "3:4"
    title_max_chars = 20
    tag_max_count = 10
    tag_format = "single_hash"
    needs_vertical_cover = True

    def save_draft(self, material: Material) -> AdapterResult:
        try:
            self.inject_cookies(domains=["xiaohongshu.com"])
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

            # 等待表单出现
            self._wait_form_ready()
            self.screenshot("03_form_ready")

            # 上传封面
            self._upload_cover(material.vertical_cover_path)
            self.screenshot("04_cover_uploaded")

            # 填标题
            self._fill_title(material.long_title[:20])
            self.screenshot("05_title_filled")

            # 填简介
            self._fill_description(material.effective_description)
            self.screenshot("06_desc_filled")

            # 添加话题
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
            if "login" in self.page.url:
                return False
            # 小红书登录后会有上传按钮
            upload = self.page.query_selector("input.upload-input, input[type=file]")
            return upload is not None
        except Exception:
            return False

    def _upload_video(self, video_path: str):
        selectors = [
            "input.upload-input[accept*='mp4']",
            "input[type=file][accept*='mp4']",
            ".upload-wrapper input[type=file]",
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
        """等待视频上传后表单出现。"""
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
            logger.warning("[%s] form not ready, continuing", self.platform_id)
        self.human_pause(2)

    def _upload_cover(self, cover_path: str):
        """上传封面。小红书上传视频后会显示封面选择。"""
        # 方案 1: 找"上传封面"/"更改封面"按钮
        for sel in ["text=上传封面", "text=更改封面", "text=选择封面",
                    ".cover-upload", "[class*='coverContainer']"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    with self.page.expect_file_chooser(timeout=10000) as fc_info:
                        el.click()
                    fc = fc_info.value
                    fc.set_files(cover_path)
                    logger.info("[%s] cover uploaded via file chooser (%s)", self.platform_id, sel)
                    self.human_pause(2)
                    self._close_cover_editor()
                    return
            except Exception:
                continue

        # 方案 2: 找 image input
        for sel in ["input[type=file][accept*='image']",
                    ".upload-input[accept*='image']"]:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=5000)
                self.page.set_input_files(sel, cover_path)
                logger.info("[%s] cover uploaded via %s", self.platform_id, sel)
                self.human_pause(2)
                self._close_cover_editor()
                return
            except Exception:
                continue

        logger.warning("[%s] cover upload skipped", self.platform_id)

    def _close_cover_editor(self):
        """关闭封面编辑器弹窗。"""
        self.human_pause(1)
        for sel in ["text=完成", "text=确定", "button:has-text('完成')",
                    ".d-button:has-text('完成')"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(1)
                    logger.info("[%s] cover editor closed via %s", self.platform_id, sel)
                    return
            except Exception:
                continue

    def _fill_title(self, title: str):
        """填写标题。"""
        selectors = [
            "input[placeholder*='标题']",
            ".title-input input",
            ".c-input input",
            "input.title",
        ]
        for sel in selectors:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click()
                    self.page.keyboard.type(title, delay=50)
                    logger.info("[%s] title filled: %s", self.platform_id, title[:20])
                    return
            except Exception:
                continue
        logger.warning("[%s] title fill skipped", self.platform_id)

    def _fill_description(self, desc: str):
        """填写简介。小红书可能用 contenteditable 或 textarea。"""
        # 方案 1: contenteditable
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

        # 方案 2: textarea
        for sel in ["textarea[placeholder*='简介']", "textarea[placeholder*='描述']",
                    ".desc-textarea textarea", "textarea"]:
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
        """添加话题。"""
        try:
            editor = self.page.query_selector("[contenteditable='true'], textarea")
            if not editor:
                return
            editor.click()
            self.page.keyboard.press("End")
            for topic in topics[:10]:
                topic_clean = topic.lstrip("#").strip()
                if topic_clean:
                    self.page.keyboard.type(f" #{topic_clean}", delay=50)
                    self.human_pause(0.3)
                    try:
                        self.page.keyboard.press("Enter", delay=200)
                    except Exception:
                        pass
                    self.human_pause(0.2)
            logger.info("[%s] topics added", self.platform_id)
        except Exception as e:
            logger.warning("[%s] topic add failed: %s", self.platform_id, e)

    def _save_draft(self) -> str | None:
        """保存草稿。小红书用 <xhs-publish-btn> Web Component（closed shadow DOM）。
        方案：用 Playwright piercing selector `>>>` 或基于坐标点击。
        """
        # 方案 1: Playwright piercing selector
        for sel in ["xhs-publish-btn >>> button:has-text('暂存')",
                    "xhs-publish-btn >>> button",
                    "xhs-publish-btn >>> [class*='save']",
                    "xhs-publish-btn >>> [class*='draft']"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click(timeout=3000)
                    self.human_pause(3)
                    logger.info("[%s] draft saved via piercing selector %s", self.platform_id, sel)
                    return self.page.url
            except Exception as e:
                logger.debug("[%s] piercing %s failed: %s", self.platform_id, sel, e)

        # 方案 2: 用 evaluate 找 xhs-publish-btn 元素的 bounding box，点左侧（暂存按钮通常在左）
        try:
            box = self.page.evaluate("""() => {
                const btn = document.querySelector('xhs-publish-btn');
                if (!btn) return null;
                const rect = btn.getBoundingClientRect();
                return {x: rect.x + rect.width * 0.25, y: rect.y + rect.height / 2};
            }""")
            if box:
                self.page.mouse.click(box["x"], box["y"])
                self.human_pause(3)
                logger.info("[%s] draft saved via coordinate click (%.0f, %.0f)",
                           self.platform_id, box["x"], box["y"])
                return self.page.url
        except Exception as e:
            logger.warning("[%s] coordinate click failed: %s", self.platform_id, e)

        # 方案 3: 普通 selector 兜底
        for sel in ["text=暂存离开", "text=存草稿"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click(timeout=3000)
                    self.human_pause(3)
                    return self.page.url
            except Exception:
                continue

        self.save_html_snapshot("save_draft_not_found")
        logger.warning("[%s] no save draft button found", self.platform_id)
        return self.page.url
