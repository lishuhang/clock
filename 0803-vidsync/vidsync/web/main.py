"""
vidsync Web UI 主入口
======================
FastAPI 服务，端口 8765。
编辑同事浏览器访问 http://localhost:8765 操作。

路由：
- GET  /               主表单页面
- GET  /api/platforms  列出支持的平台及 cookie 状态
- GET  /api/cookies/scan  扫描 cookies 目录
- POST /api/publish    启动发布任务（异步）
- GET  /api/status/{task_id}  查询任务进度
- WS   /ws/progress/{task_id}  WebSocket 实时进度
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

import uvicorn
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# 把项目根加入 sys.path（运行 python -m vidsync.web.main 时不需要，直接运行需要）
HERE = Path(__file__).parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vidsync.processors.cookies import (
    discover_cookies_dir, map_cookies_to_platforms, filter_expired,
    PLATFORM_DOMAIN_MAP,
)
from vidsync.processors.logger import RunLogger, reset_run_logger

app = FastAPI(title="vidsync", version="0.1.0")

# 静态文件
STATIC_DIR = HERE / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 全局状态
CONFIG_PATH = ROOT / "config.yaml"
COOKIES_DIR = ROOT / "vidsync" / "cookies" if (ROOT / "vidsync" / "cookies").exists() else ROOT / "cookies"
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 任务状态
_tasks: dict[str, dict] = {}
_tasks_lock = threading.Lock()


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return {}


def get_cookies_dir() -> Path:
    cfg = load_config()
    p = cfg.get("paths", {}).get("cookies_dir", "cookies")
    # 相对路径相对于项目根
    if not Path(p).is_absolute():
        p = ROOT / p
    return Path(p)


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页面。"""
    index_html = STATIC_DIR / "index.html"
    return HTMLResponse(index_html.read_text(encoding="utf-8"))


@app.get("/api/platforms")
async def list_platforms():
    """列出支持的平台及 cookie 状态。"""
    cookies_dir = get_cookies_dir()
    raw = discover_cookies_dir(cookies_dir)
    mapped = map_cookies_to_platforms(raw)

    platforms = []
    for pid, name in [
        ("bilibili", "哔哩哔哩"),
        ("douyin", "抖音"),
        ("xiaohongshu", "小红书"),
        ("kuaishou", "快手"),
        ("wechat_channels", "微信视频号"),
        ("baijiahao", "百家号"),
        ("qq_shizi", "企鹅号"),
        ("tencent_video", "腾讯视频"),
        ("weibo", "微博"),
        ("huxiu", "虎嗅"),
        ("kr36", "36氪"),
        ("alipay", "支付宝生活号"),
    ]:
        cookies = mapped.get(pid, [])
        valid = filter_expired(cookies)
        platforms.append({
            "id": pid,
            "name": name,
            "cookie_total": len(cookies),
            "cookie_valid": len(valid),
            "ready": len(valid) > 0,
            "supported_in_v01": pid == "bilibili",
        })
    return {"platforms": platforms, "cookies_dir": str(cookies_dir)}


@app.post("/api/cookies/scan")
async def scan_cookies():
    """重新扫描 cookies 目录。"""
    cookies_dir = get_cookies_dir()
    if not cookies_dir.exists():
        return JSONResponse(
            {"ok": False, "error": f"cookies dir not found: {cookies_dir}"},
            status_code=404,
        )
    raw = discover_cookies_dir(cookies_dir)
    mapped = map_cookies_to_platforms(raw)
    return {
        "ok": True,
        "cookies_dir": str(cookies_dir),
        "discovered": {k: len(v) for k, v in raw.items()},
        "mapped": {k: len(v) for k, v in mapped.items()},
    }


@app.post("/api/publish")
async def start_publish(
    video: UploadFile = File(...),
    vertical_cover: UploadFile = File(...),
    horizontal_cover: UploadFile = File(...),
    short_title: str = Form(...),
    long_title: str = Form(...),
    keywords: str = Form(...),
    description: str = Form(""),
    platforms: str = Form("bilibili"),
):
    """启动发布任务。"""
    # 保存上传文件
    task_id = str(uuid.uuid4())[:8]
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    video_path = task_dir / video.filename
    with open(video_path, "wb") as f:
        f.write(await video.read())

    vert_path = task_dir / vertical_cover.filename
    with open(vert_path, "wb") as f:
        f.write(await vertical_cover.read())

    horiz_path = task_dir / horizontal_cover.filename
    with open(horiz_path, "wb") as f:
        f.write(await horizontal_cover.read())

    # 平台列表
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]

    # 任务状态
    with _tasks_lock:
        _tasks[task_id] = {
            "status": "starting",
            "platforms": {p: {"status": "pending"} for p in platform_list},
            "video_path": str(video_path),
            "vertical_cover": str(vert_path),
            "horizontal_cover": str(horiz_path),
            "short_title": short_title,
            "long_title": long_title,
            "keywords": keywords,
            "description": description,
            "progress_log": [],
        }

    # 启动后台任务
    t = threading.Thread(target=_run_publish_task, args=(task_id,), daemon=True)
    t.start()

    return {"task_id": task_id, "status": "started"}


def _run_publish_task(task_id: str):
    """后台执行发布任务。"""
    from vidsync.browser.launcher import BrowserLauncher
    from vidsync.adapters.base import Material
    from vidsync.adapters.bilibili import BilibiliAdapter

    with _tasks_lock:
        task = _tasks[task_id]
        task["status"] = "running"

    run_logger = reset_run_logger()
    run_logger.summary["task_id"] = task_id
    task["run_dir"] = run_logger.run_dir_str

    # 加载配置
    cfg = load_config()
    browser_cfg = cfg.get("browser", {})

    # 浏览器启动器
    launcher = BrowserLauncher(browser_cfg)
    try:
        ctx = launcher.launch()
    except Exception as e:
        logging.exception("browser launch failed")
        with _tasks_lock:
            task["status"] = "failed"
            task["error"] = f"browser launch failed: {e}"
        return

    # cookies
    cookies_dir = get_cookies_dir()
    raw = discover_cookies_dir(cookies_dir)
    mapped = map_cookies_to_platforms(raw)

    # 物料
    material = Material(
        video_path=task["video_path"],
        vertical_cover_path=task["vertical_cover"],
        horizontal_cover_path=task["horizontal_cover"],
        short_title=task["short_title"],
        long_title=task["long_title"],
        keywords=task["keywords"],
        description=task["description"],
    )

    platform_list = list(task["platforms"].keys())
    for pid in platform_list:
        with _tasks_lock:
            task["platforms"][pid]["status"] = "running"
            task["progress_log"].append(f"[{pid}] 开始处理...")

        try:
            if pid == "bilibili":
                adapter = BilibiliAdapter(
                    cookies=mapped.get(pid, []),
                    run_logger=run_logger,
                    browser_context=ctx,
                    config=cfg,
                )
            else:
                # v0.1 只支持 bilibili，其他平台标记为 not_implemented
                with _tasks_lock:
                    task["platforms"][pid] = {
                        "status": "skipped",
                        "error": "v0.1 暂未实现，等待后续版本",
                    }
                    task["progress_log"].append(f"[{pid}] ⏸ v0.1 暂未实现")
                continue

            result = adapter.save_draft(material)
            with _tasks_lock:
                task["platforms"][pid] = {
                    "status": result.status,
                    "draft_url": result.draft_url,
                    "error": result.error,
                    "expires_at": result.expires_at,
                    "extra": result.extra,
                }
                emoji = "✅" if result.status == "success" else "❌"
                task["progress_log"].append(
                    f"[{pid}] {emoji} {result.status}: {result.draft_url or result.error or ''}"
                )
        except Exception as e:
            logging.exception("[%s] adapter failed", pid)
            with _tasks_lock:
                task["platforms"][pid] = {"status": "failed", "error": str(e)}
                task["progress_log"].append(f"[{pid}] ❌ failed: {e}")

    launcher.close()
    run_logger.finish()
    with _tasks_lock:
        task["status"] = "completed"


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """查询任务状态。"""
    with _tasks_lock:
        if task_id not in _tasks:
            raise HTTPException(status_code=404, detail="task not found")
        return _tasks[task_id]


@app.websocket("/ws/progress/{task_id}")
async def ws_progress(ws: WebSocket, task_id: str):
    """WebSocket 推送进度。"""
    await ws.accept()
    try:
        import time
        last_log_len = 0
        while True:
            with _tasks_lock:
                if task_id not in _tasks:
                    await ws.send_json({"type": "error", "msg": "task not found"})
                    break
                task = _tasks[task_id]
                # 增量推送 progress_log
                new_logs = task["progress_log"][last_log_len:]
                last_log_len = len(task["progress_log"])
                for log in new_logs:
                    await ws.send_json({"type": "log", "msg": log})
                if task["status"] in ("completed", "failed"):
                    await ws.send_json({"type": "done", "status": task["status"],
                                        "platforms": task["platforms"]})
                    break
            await ws.send_json({"type": "heartbeat"})
            import asyncio
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


@app.get("/api/logs/{task_id}")
async def get_logs(task_id: str):
    """获取任务日志目录。"""
    with _tasks_lock:
        if task_id not in _tasks:
            raise HTTPException(status_code=404, detail="task not found")
        run_dir = _tasks[task_id].get("run_dir")
    if not run_dir or not Path(run_dir).exists():
        raise HTTPException(status_code=404, detail="logs not ready")
    # 列出日志目录内容
    files = []
    for p in Path(run_dir).rglob("*"):
        if p.is_file():
            files.append({
                "path": str(p.relative_to(run_dir)),
                "size": p.stat().st_size,
            })
    return {"run_dir": run_dir, "files": files}


@app.get("/api/log-file")
async def get_log_file(path: str):
    """下载单个日志文件。"""
    # 安全检查：路径必须在某个 run_dir 下
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(str(p))


def main():
    """主入口。"""
    cfg = load_config()
    server_cfg = cfg.get("server", {})
    port = server_cfg.get("port", 8765)
    host = server_cfg.get("host", "127.0.0.1")

    print(f"""
╔══════════════════════════════════════════╗
║  vidsync v0.1.0                          ║
║  视频多平台草稿一键发布系统              ║
╚══════════════════════════════════════════╝

  浏览器打开: http://{host}:{port}
  日志目录:   {ROOT}/logs/
  cookies 目录: {get_cookies_dir()}

  按 Ctrl+C 退出
""")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
