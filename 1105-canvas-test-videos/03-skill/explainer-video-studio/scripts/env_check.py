#!/usr/bin/env python3
"""解说视频管线 · 环境自检（Step -1）：一次性探测全部能力，输出能力清单。
用法: python3 env_check.py [--netdisk] [--tts]
退出码 0=可开工；1=有硬缺项。禁止运行期盲试（防踩坑指南铁律②）。"""
import json
import os
import shutil
import subprocess
import sys

result = {"ok": True, "hard_missing": [], "soft_missing": [], "detail": {}}


def probe(name, hard, fn):
    try:
        info = fn()
        result["detail"][name] = info or "ok"
    except Exception as e:  # noqa: BLE001
        result["detail"][name] = f"FAIL: {e}"
        (result["hard_missing"] if hard else result["soft_missing"]).append(name)
        if hard:
            result["ok"] = False


def _py(mod):
    def f():
        __import__(mod)
        return f"py:{mod} ok"
    return f


def _bin(cmd, pattern=""):
    def f():
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = (r.stdout + r.stderr).splitlines()[0] if (r.stdout or r.stderr) else ""
        if r.returncode != 0:
            raise RuntimeError(out[:120])
        return out[:100]
    return f


def _font():
    def f():
        import glob
        hits = glob.glob("/usr/share/fonts/truetype/chinese/NotoSansSC*") + \
               glob.glob("/usr/share/fonts/**/AlibabaPuHuiTi*", recursive=True) + \
               glob.glob("assets/**/alipuhui*.ttf", recursive=True)
        if not hits:
            raise RuntimeError("无中文字体（NotoSansSC/阿里普惠体）")
        return f"{len(hits)} 个字体，例 {hits[0]}"
    return f


def _chromium():
    def f():
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        b = p.chromium.launch()
        ver = f"chromium {b.version}"
        b.close()
        p.stop()
        return ver
    return f


probe("ffmpeg", True, _bin(["ffmpeg", "-version"]))
probe("ffprobe", True, _bin(["ffprobe", "-version"]))
probe("node", False, _bin(["node", "--version"]))
probe("python-playwright", True, _py("playwright"))
probe("chromium", True, _chromium())
probe("chinese-fonts", True, _font())
probe("pip-pillow", False, _py("PIL"))

if "--netdisk" in sys.argv:
    tok = os.environ.get("BAIDU_NETDISK_ACCESS_TOKEN", "")
    result["detail"]["netdisk-token"] = "set" if tok else "MISSING（请用户提供，获取链接见 SKILL.md references）"
    if not tok:
        result["soft_missing"].append("netdisk-token")

if "--tts" in sys.argv:
    import urllib.request
    try:
        req = urllib.request.Request("https://tts.lishuhang.com",
                                     headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/143 Safari/537.36"})
        urllib.request.urlopen(req, timeout=6)
        result["detail"]["tts-service"] = "tts.lishuhang.com reachable"
    except Exception as e:  # noqa: BLE001
        result["detail"]["tts-service"] = f"FAIL: {e}（回退：用户浏览器手工合成上传，或本地 edge-tts）"
        result["soft_missing"].append("tts-service")

print(json.dumps(result, ensure_ascii=False, indent=1))
sys.exit(0 if result["ok"] else 1)
