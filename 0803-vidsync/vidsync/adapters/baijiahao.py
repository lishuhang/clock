"""
vidsync Baijiahao adapter
==========================
百家号视频草稿保存。

页面结构（HTML 探查）：
- 视频上传：input[type=file][accept*='mp4']（multiple）
- 发布页 URL：https://baijiahao.baidu.com/builder/rc/edit?type=video
- 存草稿按钮：<button class="cheetah-btn-third"><span>存草稿</span></button>
  selector: button:has(span:has-text('存草稿')) 或 [data-testid='draft-btn']

格式约束：
- 视频：≤2GB，MP4/MOV
- 封面：16:9，≥660×370（1280×720 推荐），≤5MB
- 标题：6-30 字
- 标签：自定义
"""
from __future__ import annotations

import logging

from .base import BaseAdapter, Material, AdapterResult

logger = logging.getLogger(__name__)


class BaijiahaoAdapter(BaseAdapter):
    platform_id = "baijiahao"
    platform_name = "百家号"
    platform_url = "https://baijiahao.baidu.com/builder/rc/edit?type=video"
    cover_ratio_landscape = "16:9"
    title_max_chars = 30
    tag_max_count = 10
    tag_format = "plain"
    needs_landscape_cover = True

    def save_draft(self, material: Material) -> AdapterResult:
        try:
            self.inject_cookies(domains=["baidu.com"])
            self.new_page()

            # 百家号 edit?type=video 会重定向到 content，所以直接在 content 页找入口
            logger.info("[%s] navigating to content page", self.platform_id)
            self.page.goto("https://baijiahao.baidu.com/builder/rc/content",
                          wait_until="domcontentloaded", timeout=30000)
            self.human_pause(3)
            self.screenshot("01_landed")

            if not self._check_logged_in():
                return AdapterResult(
                    platform_id=self.platform_id,
                    platform_name=self.platform_name,
                    status="failed",
                    error="未登录或 cookie 已失效",
                )

            # 点击"+"发布按钮，选"视频"
            self._click_publish_video_entry()
            self.human_pause(3)
            self.screenshot("02_publish_page")

            # 上传视频
            self._upload_video(material.video_path)
            self.screenshot("03_video_uploaded")

            # 等待表单
            self._wait_form_ready()
            self.screenshot("04_form_ready")

            # 上传封面
            self._upload_cover(material.horizontal_cover_path)
            self.screenshot("05_cover_uploaded")

            # 填标题
            self._fill_title(material.long_title[:30])
            self.screenshot("06_title_filled")

            # 填简介
            self._fill_description(material.effective_description)
            self.screenshot("07_desc_filled")

            # 填标签
            self._fill_tags(material.keywords[:10])
            self.screenshot("08_tags_filled")

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

    def _check_logged_in(self) -> bool:
        """检查是否已登录。百家号登录后右上角有头像。"""
        try:
            if "login" in self.page.url or "passport" in self.page.url:
                return False
            # 简单判断：不在登录页就算登录
            return True
        except Exception:
            return False

    def _click_publish_video_entry(self):
        """点击左侧"+"发布按钮，选择"视频"。"""
        # 方案 1: 找"+"按钮点击，再选"视频"
        for sel in [".add-icon", "[class*='create-btn']", "[class*='publish-entry']",
                    "button:has-text('发布')", "a:has-text('发布')"]:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    self.human_pause(1)
                    # 找"视频"选项
                    for v_sel in ["text=视频", "a:has-text('视频')", "[class*='video']:has-text('视频')"]:
                        try:
                            v_el = self.page.query_selector(v_sel)
                            if v_el and v_el.is_visible():
                                v_el.click()
                                self.human_pause(2)
                                logger.info("[%s] clicked publish video entry", self.platform_id)
                                return
                        except Exception:
                            continue
                    logger.info("[%s] clicked publish entry, no video submenu", self.platform_id)
                    return
            except Exception:
                continue

        # 方案 2: 直接导航到 video edit
        try:
            self.page.goto("https://baijiahao.baidu.com/builder/rc/edit?type=video",
                          wait_until="domcontentloaded", timeout=15000)
            self.human_pause(2)
            logger.info("[%s] navigated directly to video edit", self.platform_id)
        except Exception as e:
            logger.warning("[%s] direct nav failed: %s", self.platform_id, e)

    def _upload_video(self, video_path: str):
        selectors = [
            "input[type=file][accept*='mp4']",
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
        """上传封面。"""
        # 方案 1: 点击"上传封面"/"更改封面"
        for sel in ["text=上传封面", "text=更改封面", "text=选择封面",
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
                return
            except Exception:
                continue
        logger.warning("[%s] cover upload skipped", self.platform_id)

    def _fill_title(self, title: str):
        """填写标题。"""
        for sel in ["input[placeholder*='标题']",
                    ".title-input input",
                    "input.title",
                    "[class*='title'] input[type='text']"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click()
                    self.page.keyboard.type(title, delay=50)
                    logger.info("[%s] title filled: %s", self.platform_id, title[:30])
                    return
            except Exception:
                continue

        # 兜底：找第一个可见的 text input
        try:
            inputs = self.page.query_selector_all("input[type='text']:visible")
            if inputs:
                inputs[0].click()
                self.page.keyboard.type(title, delay=50)
                logger.info("[%s] title filled via first text input", self.platform_id)
                return
        except Exception:
            pass
        logger.warning("[%s] title fill skipped", self.platform_id)

    def _fill_description(self, desc: str):
        """填写简介。"""
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

    def _fill_tags(self, tags: list[str]):
        """填写标签。百家号标签无 #，每个回车。"""
        for sel in ["input[placeholder*='标签']",
                    ".tag-input input",
                    "[class*='tag'] input"]:
            try:
                el = self.page.query_selector(sel)
                if el:
                    for tag in tags[:10]:
                        el.click()
                        self.page.keyboard.type(tag.lstrip("#"), delay=50)
                        self.human_pause(0.2)
                        self.page.keyboard.press("Enter")
                        self.human_pause(0.2)
                    logger.info("[%s] %d tags filled", self.platform_id, min(len(tags), 10))
                    return
            except Exception:
                continue
        logger.warning("[%s] tag fill skipped", self.platform_id)

    def _save_draft(self) -> str | None:
        """保存草稿。百家号存草稿按钮 <button><span>存草稿</span></button>。"""
        selectors = [
            "button:has(span:has-text('存草稿'))",
            "button:has-text('存草稿')",
            "text=存草稿",
            "[data-testid='draft-btn']",
            ".cheetah-btn-third:has-text('草稿')",
        ]
        for sel in selectors:
            try:
                el = self.page.query_selector(sel)
                if el:
                    # 检查是否 disabled
                    disabled = el.get_attribute("disabled")
                    if disabled is not None:
                        logger.warning("[%s] draft button disabled, form incomplete", self.platform_id)
                        continue
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
