"""
vidsync structured logger
=========================
为每次运行创建独立日志目录，按平台分子目录，每步截图 + 失败时 HTML 快照。

目录结构：
  logs/
  └── 2026-08-03_15-10-00/
      ├── run.log               # 主日志
      ├── summary.json          # 各平台结果汇总
      └── <platform>/
          ├── 01_login.png
          ├── 02_upload.png
          ├── ...
          ├── page.html         # 失败时最后页面快照
          └── adapter.log
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class RunLogger:
    """单次运行日志管理器。"""

    def __init__(self, base_logs_dir: str | Path = "logs"):
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_dir = Path(base_logs_dir) / self.timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.summary: dict[str, Any] = {
            "run_id": self.timestamp,
            "start_time": datetime.now().isoformat(),
            "platforms": {},
            "status": "running",
        }
        self._summary_path = self.run_dir / "summary.json"
        self._setup_main_logger()

    def _setup_main_logger(self):
        """配置主日志文件。"""
        log_path = self.run_dir / "run.log"
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
        root = logging.getLogger()
        # 避免重复 handler
        for h in root.handlers[:]:
            if isinstance(h, logging.FileHandler):
                root.removeHandler(h)
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        # 同时输出到 console
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root.addHandler(console)

    def platform_dir(self, platform_id: str) -> Path:
        """获取平台子目录。"""
        d = self.run_dir / platform_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def step_screenshot(self, platform_id: str, page, step_name: str) -> str | None:
        """在某个步骤截图，返回保存路径（相对路径）。"""
        try:
            d = self.platform_dir(platform_id)
            # 找下一个序号
            existing = sorted(d.glob("*.png"))
            seq = len(existing) + 1
            fname = f"{seq:02d}_{step_name}.png"
            fpath = d / fname
            page.screenshot(path=str(fpath), full_page=False)
            logging.info("[%s] screenshot saved: %s", platform_id, fname)
            return str(fpath.relative_to(self.run_dir))
        except Exception as e:
            logging.warning("[%s] screenshot failed at %s: %s", platform_id, step_name, e)
            return None

    def save_html_snapshot(self, platform_id: str, page, name: str = "page") -> str | None:
        """保存当前页面 HTML 快照（失败时调用）。"""
        try:
            d = self.platform_dir(platform_id)
            fpath = d / f"{name}.html"
            content = page.content()
            fpath.write_text(content, encoding="utf-8")
            logging.info("[%s] HTML snapshot saved: %s", platform_id, fpath.name)
            return str(fpath.relative_to(self.run_dir))
        except Exception as e:
            logging.warning("[%s] HTML snapshot failed: %s", platform_id, e)
            return None

    def save_dom_state(self, platform_id: str, page, name: str = "dom_state") -> str | None:
        """保存页面关键状态：URL、title、可见按钮文本列表。供编辑同事描述问题时参照。"""
        try:
            d = self.platform_dir(platform_id)
            fpath = d / f"{name}.json"
            state = {
                "url": page.url,
                "title": page.title(),
                "timestamp": datetime.now().isoformat(),
            }
            # 抓取所有可见按钮的文本（帮助诊断"找不到下一步该点哪"）
            try:
                buttons = page.query_selector_all("button, [role=button], a.btn, .btn")
                state["visible_buttons"] = []
                for btn in buttons[:30]:  # 限制 30 个避免太大
                    txt = (btn.inner_text() or "").strip()[:50]
                    if txt and btn.is_visible():
                        state["visible_buttons"].append(txt)
            except Exception:
                pass
            fpath.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            return str(fpath.relative_to(self.run_dir))
        except Exception as e:
            logging.warning("[%s] DOM state save failed: %s", platform_id, e)
            return None

    def record_platform_result(self, platform_id: str, status: str,
                                draft_url: str | None = None,
                                error: str | None = None,
                                expires_at: str | None = None,
                                extra: dict | None = None):
        """记录某平台的最终结果。"""
        self.summary["platforms"][platform_id] = {
            "status": status,  # "success" | "failed" | "skipped"
            "draft_url": draft_url,
            "error": error,
            "expires_at": expires_at,
            "extra": extra or {},
            "finished_at": datetime.now().isoformat(),
        }
        self._flush_summary()

    def _flush_summary(self):
        self._summary_path.write_text(
            json.dumps(self.summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def finish(self, status: str = "completed"):
        self.summary["end_time"] = datetime.now().isoformat()
        self.summary["status"] = status
        self._flush_summary()
        logging.info("run finished: %s", self.run_dir)

    @property
    def run_dir_str(self) -> str:
        return str(self.run_dir)


# 模块级单例（每次运行新建）
_current: RunLogger | None = None


def get_run_logger() -> RunLogger:
    global _current
    if _current is None:
        _current = RunLogger()
    return _current


def reset_run_logger() -> RunLogger:
    """开始一次新的运行。"""
    global _current
    _current = RunLogger()
    return _current
