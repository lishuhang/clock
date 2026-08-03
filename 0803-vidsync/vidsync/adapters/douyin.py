"""
vidsync Douyin adapter
=======================
抖音创作者中心视频草稿保存。

页面结构（从 HTML 探查得到）：
- 视频上传：input[type=file][accept*='video']，class upload-btn-input-UY_qeY
- 标题：input.semi-input[placeholder*='填写作品标题']，限制 30 字
- 简介：div[data-slate-editor=true][contenteditable=true]（Slate 富文本）
- 话题：#添加话题 按钮
- 封面：class 含 cover-ybR0xM，按钮"选择封面"

格式约束：
- 视频：≤4GB，15min（长视频）
- 封面：3:4 = 1080×1440 推荐
- 标题：55 字含 #话题（实际 30 字）
- 标签：5 话题
- 标签格式：#话题（单 #）
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from .base import BaseAdapter, Material, AdapterResult

logger = logging.getLogger(__name__)


class DouyinAdapter(BaseAdapter):
    platform_id = "douyin"
    platform_name = "抖音"
    platform_url = "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish"
    cover_ratio_landscape = "16:9"
    cover_ratio_vertical = "9:16"
    title_max_chars = 30  # placeholder 显示 30 字
    tag_max_count = 5
    tag_format = "single_hash"
    needs_vertical_cover = True
    draft_expires_days = None  # 抖音草稿无明确过期

    def save_draft(self, material: Material) -> AdapterResult:
        """执行抖音草稿保存。"""
        try:
            # 1. 注入 cookies
            self.inject_cookies(domains=["douyin.com"])
            self.new_page()

            # 2. 访问发布页
            logger.info("[%s] navigating to %s", self.platform_id, self.platform_url)
            self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=30000)
            self.human_pause(3)
            self.screenshot("01_landed")

            # 3. 检查登录态
            if not self._check_logged_in():
                self.screenshot("01_not_logged_in")
                self.save_html_snapshot("not_logged_in")
                return AdapterResult(
                    platform_id=self.platform_id,
                    platform_name=self.platform_name,
                    status="failed",
                    error="未登录或 cookie 已失效",
                )

            # 4. 上传视频
            self._upload_video(material.video_path)
            self.screenshot("02_video_uploaded")

            # 5. 等待视频处理
            self._wait_video_processed()
            self.screenshot("03_video_processed")

            # 6. 上传封面（竖屏 3:4）
            self._upload_cover(material.vertical_cover_path)
            self.screenshot("04_cover_uploaded")

            # 7. 填写标题
            self._fill_title(material.long_title[:30])
            self.screenshot("05_title_filled")

            # 8. 填写简介
            self._fill_description(material.effective_description)
            self.screenshot("06_desc_filled")

            # 9. 添加话题
            self._add_topics(material.keywords[:5])
            self.screenshot("07_topics_added")

            # 10. 保存草稿
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
        """检查是否已登录。"""
        try:
            url = self.page.url
            if "login" in url or "passport" in url:
                logger.warning("[%s] redirected to login", self.platform_id)
                return False
            # 检查是否有上传按钮（登录后才有）
            upload = self.page.query_selector("input[type=file][accept*='video']")
            if upload:
                return True
            # 检查页面 title
            title = self.page.title()
            if "登录" in title or "login" in title.lower():
                return False
            return True
        except Exception as e:
            logger.warning("[%s] login check error: %s", self.platform_id, e)
            return False

    def _upload_video(self, video_path: str):
        """上传视频文件。"""
        selectors = [
            "input[type=file][accept*='video']",
            ".upload-btn-input-UY_qeY[accept*='video']",
            ".content-upload-new input[type=file]",
        ]
        for sel in selectors:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=10000)
                self.page.set_input_files(sel, video_path)
                logger.info("[%s] video uploaded via %s", self.platform_id, sel)
                return
            except Exception as e:
                logger.debug("[%s] try %s failed: %s", self.platform_id, sel, e)
                continue
        self.save_html_snapshot("video_upload_failed")
        raise RuntimeError("video upload failed")

    def _wait_video_processed(self, timeout_ms: int = 120000):
        """等待视频处理完成。"""
        logger.info("[%s] waiting for video processing...", self.platform_id)
        self.human_pause(3)
        try:
            self.wait_for(
                "video processing complete",
                lambda: self.page.query_selector("text=上传完成")
                       or self.page.query_selector("text=上传成功")
                       or self.page.query_selector("text=处理完成")
                       or self.page.query_selector("input[placeholder*='填写作品标题']"),
                timeout_ms=timeout_ms,
                interval_ms=2000,
            )
            logger.info("[%s] video processed", self.platform_id)
        except TimeoutError:
            logger.warning("[%s] video processing timeout", self.platform_id)
        self.human_pause(2)

    def _upload_cover(self, cover_path: str):
        """上传封面。抖音封面按钮文字是"选择封面"，上传后会弹出裁剪窗口。"""
        # 方案 1: 直接找 image input 上传
        selectors = [
            "input[type=file][accept*='image']",
            ".upload-btn-input-UY_qeY[accept*='image']",
        ]
        uploaded = False
        for sel in selectors:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=5000)
                self.page.set_input_files(sel, cover_path)
                logger.info("[%s] cover uploaded via %s", self.platform_id, sel)
                self.human_pause(2)
                uploaded = True
                break
            except Exception:
                continue

        if not uploaded:
            self.save_html_snapshot("cover_upload_failed")
            logger.warning("[%s] cover upload skipped", self.platform_id)
            return

        # 处理封面裁剪弹窗：抖音上传后会弹出"设置封面"窗口，需要点"完成"
        self._close_cover_editor()

    def _close_cover_editor(self):
        """关闭封面裁剪弹窗。抖音上传封面后会弹出编辑器，需点"完成"。"""
        self.human_pause(1)
        # 尝试多种"完成"按钮
        for sel in ["text=完成", "button:has-text('完成')", ".btn:has-text('完成')",
                    "[class*='confirm']:has-text('完成')", "text=确定",
                    ".modal button:has-text('完')"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(1)
                    logger.info("[%s] cover editor closed via %s", self.platform_id, sel)
                    return
            except Exception:
                continue
        logger.info("[%s] no cover editor dialog found, continuing", self.platform_id)

    def _fill_title(self, title: str):
        """填写标题。"""
        selectors = [
            "input[placeholder*='填写作品标题']",
            "input.semi-input[placeholder*='标题']",
            ".title-input input",
        ]
        for sel in selectors:
            try:
                self.page.wait_for_selector(sel, state="visible", timeout=5000)
                self.page.fill(sel, "")
                self.page.type(sel, title, delay=50)
                logger.info("[%s] title filled: %s", self.platform_id, title[:30])
                return
            except Exception:
                continue
        logger.warning("[%s] title fill skipped", self.platform_id)

    def _fill_description(self, desc: str):
        """填写简介。抖音用 Slate 富文本编辑器。
        直接用 JavaScript focus（最快），不试多个 selector。
        """
        try:
            found = self.page.evaluate("""() => {
                const el = document.querySelector('[contenteditable="true"]') ||
                           document.querySelector('.editor-comp-publish [contenteditable]');
                if (el) { el.focus(); return true; }
                return false;
            }""")
            if found:
                self.human_pause(0.3)
                self.page.keyboard.type(desc, delay=30)
                self.human_pause(0.3)
                logger.info("[%s] description filled via JS focus", self.platform_id)
                return
        except Exception as e:
            logger.warning("[%s] JS focus desc failed: %s", self.platform_id, e)

        self.save_html_snapshot("desc_fill_failed")
        logger.warning("[%s] description fill skipped", self.platform_id)

    def _add_topics(self, topics: list[str]):
        """添加话题。抖音话题格式 #话题。
        策略：在简介编辑器末尾输入 #话题 + Enter（触发推荐）。
        超时短，失败不阻塞。
        """
        try:
            # 找编辑器，按 End 到末尾
            editor = self.page.query_selector("[contenteditable='true']")
            if not editor:
                logger.warning("[%s] no editor for topics", self.platform_id)
                return
            editor.click()
            self.human_pause(0.2)
            self.page.keyboard.press("End")
            self.human_pause(0.2)

            added = 0
            for topic in topics[:5]:
                try:
                    topic_clean = topic.lstrip("#").strip()
                    if not topic_clean:
                        continue
                    self.page.keyboard.type(f" #{topic_clean}", delay=50)
                    self.human_pause(0.5)
                    # 选第一个推荐（如果有）
                    try:
                        self.page.keyboard.press("Enter", delay=200)
                    except Exception:
                        pass
                    self.human_pause(0.3)
                    added += 1
                except Exception as e:
                    logger.debug("[%s] topic %s failed: %s", self.platform_id, topic, e)
            logger.info("[%s] %d topics added", self.platform_id, added)
        except Exception as e:
            logger.warning("[%s] topic add failed: %s", self.platform_id, e)

    def _save_draft(self) -> str | None:
        """保存草稿。抖音的存草稿按钮文字是"暂存离开"（不是"存草稿"）。
        HTML 分析：<button class="cancel-btn-zy_rHA">暂存离开</button>
        """
        selectors = [
            "text=暂存离开",
            "button:has-text('暂存离开')",
            ".cancel-btn-zy_rHA",
            ".cancel-btn",
            "text=存草稿",
            "text=保存草稿",
        ]
        for sel in selectors:
            try:
                el = self.page.query_selector(sel)
                if el:
                    try:
                        el.click(timeout=3000)
                    except Exception:
                        el.evaluate("el => el.click()")
                    self.human_pause(3)
                    logger.info("[%s] draft saved (via %s)", self.platform_id, sel)
                    # 处理确认弹窗
                    self._handle_confirm_dialog()
                    return self.page.url
            except Exception:
                continue

        self.save_html_snapshot("save_draft_not_found")
        self.save_dom_state("save_draft_state")
        logger.warning("[%s] no save draft button found", self.platform_id)
        return self.page.url

    def _handle_confirm_dialog(self):
        """处理保存草稿后的确认弹窗。"""
        self.human_pause(0.5)
        for sel in ["text=确认", "text=确定", "text=继续保存", "text=仍然保存",
                    ".modal button:has-text('确')", ".semi-modal button:has-text('确')"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(1)
                    logger.info("[%s] confirmed dialog: %s", self.platform_id, sel)
                    return
            except Exception:
                continue
