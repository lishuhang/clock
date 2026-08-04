"""
vidsync Bilibili adapter
=========================
B站视频草稿保存。

关键流程：
1. 注入 cookies
2. 访问 https://member.bilibili.com/platform/upload-manager/article
3. 点击"投稿" → 进入视频上传页
4. 上传视频文件
5. 等待视频处理完成
6. 填写封面（横屏 16:9，1146×717 推荐）
7. 填写标题（≤80字）
8. 填写简介
9. 填写标签（≤10个）
10. 选择分区
11. 点击"保存草稿"

格式约束：
- 横屏封面 16:9（1146×717 推荐，最小 960×600，≤5MB）
- 标题 ≤80 字
- 标签 ≤10 个，自由格式无 #
- 视频草稿 10 天过期
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from playwright.sync_api import TimeoutError as PWTimeoutError

from .base import BaseAdapter, Material, AdapterResult

logger = logging.getLogger(__name__)


class BilibiliAdapter(BaseAdapter):
    platform_id = "bilibili"
    platform_name = "哔哩哔哩"
    platform_url = "https://member.bilibili.com/platform/upload-manager/article"
    cover_ratio_landscape = "16:9"
    cover_ratio_vertical = "9:16"
    title_max_chars = 80
    tag_max_count = 10
    tag_format = "plain"
    needs_landscape_cover = True
    draft_expires_days = 10

    def save_draft(self, material: Material) -> AdapterResult:
        """执行 B 站草稿保存。"""
        try:
            # 1. 注入 cookies
            self.inject_cookies(domains=["bilibili.com"])

            # 2. 打开新页面
            self.new_page()

            # 3. 访问投稿页
            logger.info("[%s] navigating to %s", self.platform_id, self.platform_url)
            self.page.goto(self.platform_url, wait_until="domcontentloaded", timeout=30000)
            self.human_pause(2)
            self.screenshot("01_landed")

            # 4. 检查是否已登录
            if not self._check_logged_in():
                self.screenshot("01_not_logged_in")
                self.save_html_snapshot("not_logged_in")
                return AdapterResult(
                    platform_id=self.platform_id,
                    platform_name=self.platform_name,
                    status="failed",
                    error="未登录或 cookie 已失效，请重新导出 cookies.txt",
                )

            # 5. 点击"投稿"按钮
            self._click_publish_entry()
            self.screenshot("02_publish_page")

            # 6. 切换到"视频投稿"tab（如果在投稿管理页）
            self._switch_to_video_tab()
            self.screenshot("03_video_tab")

            # 7. 上传视频文件
            self._upload_video(material.video_path)
            self.screenshot("04_video_uploaded")

            # 8. 等待视频处理
            self._wait_video_processed()
            self.screenshot("05_video_processed")

            # 9. 上传横屏封面
            self._upload_cover(material.horizontal_cover_path)
            self.screenshot("06_cover_uploaded")

            # 10. 填写标题
            self._fill_title(material.long_title[:80])
            self.screenshot("07_title_filled")

            # 11. 填写简介
            self._fill_description(material.effective_description)
            self.screenshot("08_desc_filled")

            # 12. 填写标签
            self._fill_tags(material.keywords[:10])
            self.screenshot("09_tags_filled")

            # 13. 选择分区（默认"生活 - 日常"，编辑可后续修改）
            self._select_category()
            self.screenshot("10_category_selected")

            # 14. 保存草稿
            draft_url = self._save_draft()
            self.screenshot("11_draft_saved")

            expires_at = (datetime.now() + timedelta(days=self.draft_expires_days)).isoformat()

            self.run_logger.record_platform_result(
                platform_id=self.platform_id,
                status="success",
                draft_url=draft_url or self.platform_url,
                expires_at=expires_at,
            )

            return AdapterResult(
                platform_id=self.platform_id,
                platform_name=self.platform_name,
                status="success",
                draft_url=draft_url or self.platform_url,
                expires_at=expires_at,
                extra={"note": "B站草稿10天后自动删除，请及时复核发布"},
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

    # ---- 内部步骤 ----

    def _check_logged_in(self) -> bool:
        """检查是否已登录。"""
        try:
            # B站登录后右上角会显示头像或"投稿"按钮
            # 未登录会跳转到 passport.bilibili.com/login
            url = self.page.url
            if "passport.bilibili.com" in url or "/login" in url:
                logger.warning("[%s] redirected to login page", self.platform_id)
                return False
            # 检查页面是否有登录态特征
            # 比如 .header-login-entry（未登录） vs .header-upload-entry（已登录）
            not_logged = self.page.query_selector(".header-login-entry, .login-btn, [data-test='login']")
            if not_logged:
                logger.warning("[%s] login button visible, not logged in", self.platform_id)
                return False
            return True
        except Exception as e:
            logger.warning("[%s] login check error: %s", self.platform_id, e)
            return False

    def _click_publish_entry(self):
        """点击"投稿"入口。"""
        # 多 selector 兜底
        selectors = [
            "a[href*='upload']:not([href*='article'])",
            ".header-upload-entry",
            "a:has-text('投稿')",
            "button:has-text('投稿')",
            ".side-bar-upload",
        ]
        for sel in selectors:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(1.5)
                    return
            except Exception:
                continue
        # 如果都不在，可能已经在投稿页
        logger.info("[%s] no publish entry clicked, assuming already on upload page", self.platform_id)

    def _switch_to_video_tab(self):
        """切换到视频投稿 tab。"""
        try:
            self.page.click("a:has-text('视频投稿')", timeout=5000)
            self.human_pause(1)
        except Exception:
            logger.info("[%s] video tab switch skipped", self.platform_id)

    def _upload_video(self, video_path: str):
        """上传视频文件。B站用 input[type=file] 接受拖拽上传。"""
        # B站的上传 input 通常是隐藏的，需要找到它的 selector
        # 常见的：.bcc-upload-wrapper input[type=file], .upload-btn input[type=file]
        selectors = [
            "input[type=file][accept*='video']",
            ".bcc-upload-wrapper input[type=file]",
            ".upload-input-wrapper input[type=file]",
            ".upload-btn input[type=file]",
            "input[type=file]",
        ]
        last_err = None
        for sel in selectors:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=10000)
                self.page.set_input_files(sel, video_path)
                logger.info("[%s] video uploaded via %s", self.platform_id, sel)
                return
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"video upload failed (last_error={last_err})")

    def _wait_video_processed(self, timeout_ms: int = 180000):
        """等待视频处理完成。B站会显示进度条然后变成"上传完成"。"""
        logger.info("[%s] waiting for video processing...", self.platform_id)
        # 先等至少看到上传进度或处理中提示
        self.human_pause(3)
        try:
            # 等待进度条消失或"上传完成"出现
            self.wait_for(
                "video processing complete",
                lambda: self.page.query_selector("text=上传完成")
                       or self.page.query_selector("text=转码完成")
                       or self.page.query_selector("text=处理完成")
                       or self.page.query_selector(".success-icon")
                       or self.page.query_selector(".video-title input"),  # 标题输入框出现也算
                timeout_ms=timeout_ms,
                interval_ms=2000,
            )
            logger.info("[%s] video processed", self.platform_id)
        except TimeoutError:
            logger.warning("[%s] video processing timeout, continuing anyway", self.platform_id)
        # 额外等待确保 UI 稳定
        self.human_pause(2)

    def _upload_cover(self, cover_path: str):
        """上传横屏封面。B站按钮文字是"添加主封面"，点击后弹出 file chooser。"""
        # 方案 1: 用 expect_file_chooser 处理文件选择对话框
        try:
            # 先尝试找到"添加主封面"按钮
            cover_btn = None
            for sel in ["text=添加主封面", "text=上传封面", ".cover-upload", ".video-cover-upload"]:
                try:
                    el = self.page.query_selector(sel)
                    if el and el.is_visible():
                        cover_btn = el
                        logger.info("[%s] found cover button: %s", self.platform_id, sel)
                        break
                except Exception:
                    continue

            if cover_btn:
                # 用 filechooser 事件处理
                with self.page.expect_file_chooser(timeout=10000) as fc_info:
                    cover_btn.click()
                fc = fc_info.value
                fc.set_files(cover_path)
                logger.info("[%s] cover uploaded via file chooser", self.platform_id)
                self.human_pause(2)
                return
        except Exception as e:
            logger.warning("[%s] cover upload via file chooser failed: %s", self.platform_id, e)

        # 方案 2: 直接找 input[type=file][accept*='image']
        selectors = [
            ".cover-upload input[type=file]",
            ".video-cover-upload input[type=file]",
            ".upload-cover input[type=file]",
            "input[type=file][accept*='image']",
        ]
        for sel in selectors:
            try:
                self.page.wait_for_selector(sel, state="attached", timeout=5000)
                self.page.set_input_files(sel, cover_path)
                logger.info("[%s] cover uploaded via %s", self.platform_id, sel)
                self.human_pause(1.5)
                return
            except Exception:
                continue

        # 方案 3: 保存 HTML 快照供 debug
        self.save_html_snapshot("cover_upload_failed")
        self.save_dom_state("cover_upload_state")
        logger.warning("[%s] cover upload skipped (no input found, HTML snapshot saved)",
                       self.platform_id)

    def _fill_title(self, title: str):
        """填写标题。"""
        selectors = [
            ".input-title input",
            ".video-title input",
            "input[placeholder*='标题']",
            "#inputTitle",
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
        """填写简介。B站简介区域标签是"简介"，用 textarea。"""
        # 方案 1: 用多种 selector 找 textarea
        selectors = [
            ".input-desc textarea",
            ".video-desc textarea",
            "textarea[placeholder*='简介']",
            "#inputDesc",
            ".desc-textarea textarea",
            ".video-desc-box textarea",
            "textarea[placeholder*='描述']",
            ".ql-editor[contenteditable=true]",  # 富文本编辑器
        ]
        for sel in selectors:
            try:
                self.page.wait_for_selector(sel, state="visible", timeout=3000)
                self.page.fill(sel, "")
                self.page.type(sel, desc, delay=30)
                logger.info("[%s] description filled via %s", self.platform_id, sel)
                return
            except Exception:
                continue

        # 方案 2: 找"简介"标签附近的 textarea
        try:
            # 找包含"简介"文字的元素，然后找其父容器内的 textarea
            label = self.page.query_selector("text=简介")
            if label:
                # 向上找容器，再向下找 textarea
                parent = label.evaluate("el => el.closest('.video-desc, .desc-box, .form-item, [class*=desc]')")
                if parent:
                    textarea = self.page.query_selector(f"{parent} textarea, {parent} [contenteditable=true]")
                    if textarea:
                        textarea.click()
                        self.page.keyboard.type(desc, delay=30)
                        logger.info("[%s] description filled via label-lookup", self.platform_id)
                        return
        except Exception as e:
            logger.debug("[%s] label-lookup description failed: %s", self.platform_id, e)

        # 方案 3: 保存 HTML 快照
        self.save_html_snapshot("desc_fill_failed")
        self.save_dom_state("desc_fill_state")
        logger.warning("[%s] description fill skipped (HTML snapshot saved)", self.platform_id)

    def _fill_tags(self, tags: list[str]):
        """填写标签。B站标签不需要 #，每个输入后回车。"""
        selectors = [
            ".tag-container input",
            ".input-tag input",
            "input[placeholder*='标签']",
            ".tag-input input",
            ".video-tag input",
            "input[placeholder*='按回车']",
        ]
        for sel in selectors:
            try:
                self.page.wait_for_selector(sel, state="visible", timeout=5000)
                for tag in tags[:10]:
                    self.page.fill(sel, "")
                    self.page.type(sel, tag, delay=50)
                    self.human_pause(0.2)
                    self.page.press(sel, "Enter")
                    self.human_pause(0.2)
                logger.info("[%s] %d tags filled", self.platform_id, min(len(tags), 10))
                return
            except Exception:
                continue
        logger.warning("[%s] tag fill skipped", self.platform_id)

    def _select_category(self):
        """选择分区。
        从 HTML 分析：B站默认会根据视频内容预选分区（.select-item-cont-inserted）。
        策略：如果已有预选分区，直接用；否则点击 .select-controller 选第一个。
        """
        try:
            # 方案 1: 检查是否已有选中分区
            selected = self.page.query_selector(".select-item-cont-inserted")
            if selected:
                txt = selected.inner_text().strip()
                logger.info("[%s] category already selected: %s (using default)", self.platform_id, txt)
                return

            # 方案 2: 点击 .select-controller 打开下拉，选第一个
            controller = self.page.query_selector(".select-controller, .select-item-cont")
            if controller:
                controller.click()
                self.human_pause(0.5)
                # 选第一个选项
                first = self.page.query_selector(".select-item-cont:not(.select-item-cont-inserted)")
                if first:
                    first.click()
                    txt = first.inner_text().strip()
                    logger.info("[%s] category selected: %s (first option)", self.platform_id, txt)
                    return
        except Exception as e:
            logger.debug("[%s] category selection error: %s", self.platform_id, e)

        # 方案 3: 保存快照供 debug
        self.save_html_snapshot("category_select_failed")
        logger.warning("[%s] category selection skipped (HTML snapshot saved)", self.platform_id)

    def _save_draft(self) -> str | None:
        """点击"保存草稿"按钮，返回草稿 URL。
        HTML 分析：B站存草稿按钮是 <span class="submit-draft">存草稿</span>
        """
        try:
            # 多种 selector 尝试
            selectors = [
                ".submit-draft",
                "span.submit-draft",
                "[data-reporter-id='105']",
                "text=存草稿",
                "text=保存草稿",
                ".submit-container .submit-draft",
            ]
            for sel in selectors:
                try:
                    el = self.page.query_selector(sel)
                    if el:
                        # 不检查 is_visible，直接尝试点击
                        try:
                            el.click(timeout=3000)
                        except Exception:
                            # fallback: 用 JavaScript 点击
                            el.evaluate("el => el.click()")
                        self.human_pause(3)
                        logger.info("[%s] draft saved (via %s)", self.platform_id, sel)
                        self._handle_confirm_dialog()
                        return self.page.url
                except Exception as e:
                    logger.debug("[%s] click %s failed: %s", self.platform_id, sel, e)
                    continue

            # 最后兜底：用 page.click 直接点 text
            try:
                self.page.click("text=存草稿", timeout=5000)
                self.human_pause(3)
                logger.info("[%s] draft saved (via text=存草稿 fallback)", self.platform_id)
                self._handle_confirm_dialog()
                return self.page.url
            except Exception:
                pass

            # 保存 HTML 快照供 debug
            self.save_html_snapshot("save_draft_button_not_found")
            self.save_dom_state("save_draft_state")
            logger.warning("[%s] no save draft button found (HTML snapshot saved)", self.platform_id)
            return self.page.url
        except Exception as e:
            logger.error("[%s] save draft failed: %s", self.platform_id, e)
            return None

    def _handle_confirm_dialog(self):
        """处理保存草稿后可能出现的确认弹窗。"""
        self.human_pause(0.5)
        for sel in ["text=确认", "text=确定", "text=继续保存", "text=仍然保存",
                    ".bcc-modal button:has-text('确')", ".modal button:has-text('确')"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(1)
                    logger.info("[%s] confirmed dialog: %s", self.platform_id, sel)
                    return
            except Exception:
                continue
