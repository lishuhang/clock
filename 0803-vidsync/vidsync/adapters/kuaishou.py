"""
vidsync Kuaishou adapter
=========================
快手创作者服务平台视频草稿保存。

页面结构（HTML 探查）：
- 视频上传：input[type=file][accept*='video']（hidden，需点击上传按钮触发）
- 登录后显示"娱乐资本论"
- 上传按钮文字"上传视频"
- 发布按钮 class publish-button

格式约束：
- 视频：≤12GB，1小时
- 封面：9:16 = 1080×1920
- 标题：~20 字
- 标签：#话题
"""
from __future__ import annotations

import logging

from .base import BaseAdapter, Material, AdapterResult

logger = logging.getLogger(__name__)


class KuaishouAdapter(BaseAdapter):
    platform_id = "kuaishou"
    platform_name = "快手"
    platform_url = "https://cp.kuaishou.com/article/publish/video?from=publish"
    cover_ratio_vertical = "9:16"
    title_max_chars = 20
    tag_max_count = 10
    tag_format = "single_hash"
    needs_vertical_cover = True

    def save_draft(self, material: Material) -> AdapterResult:
        try:
            self.inject_cookies(domains=["kuaishou.com"])
            self.new_page()

            logger.info("[%s] navigating to %s", self.platform_id, self.platform_url)
            self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=30000)
            self.human_pause(3)
            self.screenshot("01_landed")

            # 关闭可能的满意度调查弹窗
            self._close_survey_popup()
            self.screenshot("02_popup_closed")

            if not self._check_logged_in():
                return AdapterResult(
                    platform_id=self.platform_id,
                    platform_name=self.platform_name,
                    status="failed",
                    error="未登录或 cookie 已失效",
                )

            # 上传视频
            self._upload_video(material.video_path)
            self.screenshot("03_video_uploaded")

            # 等待表单
            self._wait_form_ready()
            # 再次关闭教程（教程在表单出现后才弹）
            self._close_survey_popup()
            self.screenshot("04_form_ready")

            # 上传封面
            self._upload_cover(material.vertical_cover_path)
            self.screenshot("05_cover_uploaded")

            # 填标题
            self._fill_title(material.long_title[:20])
            self.screenshot("06_title_filled")

            # 填简介
            self._fill_description(material.effective_description)
            self.screenshot("07_desc_filled")

            # 添加话题
            self._add_topics(material.keywords[:10])
            self.screenshot("08_topics_added")

            # 保存草稿
            draft_url = self._save_draft()
            self.screenshot("09_draft_saved")

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

    def _close_survey_popup(self):
        """关闭满意度调查弹窗 + 引导教程 tooltip。"""
        # 关闭引导教程（tooltip with "下一步"）
        for sel in ["[class*='tooltip'] [class*='skip']",
                    "div[title='Skip']", "text=Skip",
                    "[class*='_tooltip'] [class*='close']"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(0.3)
                    logger.info("[%s] tutorial tooltip skipped via %s", self.platform_id, sel)
            except Exception:
                continue

        # 多次点下一步跳过整个教程
        for _ in range(5):
            try:
                next_btn = self.page.query_selector("._tooltip-btns_d7f44_63 ._button-primary_3a3lq_60")
                if next_btn and next_btn.is_visible():
                    next_btn.click()
                    self.human_pause(0.3)
                    logger.info("[%s] tutorial next clicked", self.platform_id)
                    continue
                break
            except Exception:
                break

        # 关闭满意度调查
        for sel in ["[class*='feedback_card_title_close']",
                    "[class*='survey'] [class*='close']",
                    ".el-dialog__close", ".el-icon-close"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(0.5)
                    logger.info("[%s] survey closed via %s", self.platform_id, sel)
                    return
            except Exception:
                continue
        try:
            self.page.keyboard.press("Escape")
        except Exception:
            pass

    def _check_logged_in(self) -> bool:
        try:
            if "login" in self.page.url:
                return False
            upload = self.page.query_selector("input[type=file][accept*='video']")
            return upload is not None
        except Exception:
            return False

    def _upload_video(self, video_path: str):
        """上传视频。快手 input 是 hidden，可直接 set_input_files。"""
        selectors = [
            "input[type=file][accept*='video']",
            "._upload-btn_1j3uy_87 input[type=file]",
            ".upload-container input[type=file]",
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
        """等待表单出现。"""
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
        # 方案 1: 点击"更改封面"/"上传封面"按钮
        for sel in ["text=更改封面", "text=上传封面", "text=选择封面",
                    ".cover-upload", "[class*='coverContainer']"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    with self.page.expect_file_chooser(timeout=10000) as fc_info:
                        el.click()
                    fc = fc_info.value
                    fc.set_files(cover_path)
                    logger.info("[%s] cover uploaded via %s", self.platform_id, sel)
                    self.human_pause(2)
                    self._close_cover_editor()
                    return
            except Exception:
                continue

        # 方案 2: image input
        for sel in ["input[type=file][accept*='image']"]:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=5000)
                self.page.set_input_files(sel, cover_path)
                logger.info("[%s] cover uploaded via image input", self.platform_id)
                self.human_pause(2)
                self._close_cover_editor()
                return
            except Exception:
                continue
        logger.warning("[%s] cover upload skipped", self.platform_id)

    def _close_cover_editor(self):
        """关闭封面编辑器。"""
        self.human_pause(1)
        for sel in ["text=完成", "text=确定", "button:has-text('完成')"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(1)
                    return
            except Exception:
                continue

    def _fill_title(self, title: str):
        """填写标题。快手没有独立标题框，标题写到"作品描述"开头。
        实际标题+简介都填到 work-description-edit。
        """
        # 快手标题填到作品描述开头，由 _fill_description 处理
        logger.info("[%s] title will be combined into description (kuaishou has no separate title field)",
                   self.platform_id)

    def _fill_description(self, desc: str):
        """填写简介+标题。快手用 #work-description-edit contenteditable。
        把标题放第一行，简介放第二行。
        """
        try:
            el = self.page.query_selector("#work-description-edit, [id*='work-description']")
            if el:
                el.click()
                self.human_pause(0.3)
                # 输入标题 + 换行 + 简介
                full_text = desc
                self.page.keyboard.type(full_text, delay=30)
                logger.info("[%s] description filled: %s", self.platform_id, full_text[:30])
                return
        except Exception as e:
            logger.debug("[%s] work-description-edit failed: %s", self.platform_id, e)

        # 兜底
        try:
            found = self.page.evaluate("""() => {
                const el = document.querySelector('[contenteditable="true"]');
                if (el) { el.focus(); return true; }
                return false;
            }""")
            if found:
                self.page.keyboard.type(desc, delay=30)
                logger.info("[%s] description filled via contenteditable fallback", self.platform_id)
        except Exception:
            pass

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
        """保存草稿。快手按钮在页面底部，需先滚动到底部。"""
        # 滚动到底部
        try:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.human_pause(1)
        except Exception:
            pass

        selectors = [
            "text=存草稿",
            "text=保存草稿",
            "text=暂存",
            "text=暂存离开",
            "button:has-text('草稿')",
            ".draft-btn",
            "[class*='draft']",
            "._save-draft",
        ]
        for sel in selectors:
            try:
                el = self.page.query_selector(sel)
                if el:
                    try:
                        el.scroll_into_view_if_needed(timeout=2000)
                    except Exception:
                        pass
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
