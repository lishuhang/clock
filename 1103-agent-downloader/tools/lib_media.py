#!/usr/bin/env python3
# 1103-agent-downloader 通用库
# 结构化日志 / worklog W条目 / meta落盘 / yt-dlp格式选择 / 通用下载 / ffprobe
import os, sys, json, subprocess, shutil, datetime, zoneinfo
import requests

WORK = "/home/z/my-project/clock/1103-agent-downloader"
YTDLP = "/home/z/.venv/bin/yt-dlp"
UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/131.0.0.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
UA_IOS = UA_MOBILE

def now():
    return datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Hong_Kong")).isoformat(timespec="seconds")

def log(platform, stage, detail):
    """单行事实日志(追加到 worklog.md)"""
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, "worklog.md"), "a", encoding="utf-8") as f:
        for line in (str(detail).splitlines() or ["(空)"]):
            f.write(f"`{now()}` **[{platform}][{stage}]** {line}\n")

def wentry(task, status, cmd, raw, key_facts, conclusion, nxt):
    """按 findings/04 规范追加 W 条目块, 返回编号"""
    p = os.path.join(WORK, "worklog.md")
    n = 1
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            n = f.read().count("## [W") + 1
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"\n## [W{n:03d}] {now()} | task={task} | status={status}\n")
        f.write(f"- cmd: `{cmd}`\n- raw: {raw}\n- key_facts (verbatim):\n")
        for k in key_facts:
            f.write(f"  - `{str(k)[:400]}`\n")
        f.write(f"- conclusion: {conclusion}\n- next: {nxt}\n")
    return f"W{n:03d}"

def save_meta(platform, meta):
    d = os.path.join(WORK, "downloads", platform)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def upsert_state(platform, patch):
    p = os.path.join(WORK, "state.json")
    st = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    st.setdefault("platform_status", {}).setdefault(platform, {})
    st["platform_status"][platform]["result_1103"] = patch
    st["phase"] = "download_round_running"
    st["updated"] = now()
    json.dump(st, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def probe(path):
    info = {"size": os.path.getsize(path) if os.path.exists(path) else 0}
    try:
        if shutil.which("ffprobe"):
            out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                                  "-show_streams", "-show_format", path],
                                 capture_output=True, text=True, timeout=60)
            j = json.loads(out.stdout or "{}")
            v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
            info.update({"width": v.get("width"), "height": v.get("height"),
                         "duration": j.get("format", {}).get("duration"),
                         "codec": v.get("codec_name")})
        else:
            info["note"] = "ffprobe不可用"
    except Exception as e:
        info["error"] = str(e)[:200]
    return info

def download(url, out_path, headers=None, platform="", max_mb=110):
    h = {"User-Agent": UA_PC}
    if headers:
        h.update(headers)
    with requests.get(url, headers=h, stream=True, timeout=(20, 180), allow_redirects=True) as r:
        r.raise_for_status()
        total = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(256 * 1024):
                f.write(chunk)
                total += len(chunk)
                if total > max_mb * 1024 * 1024:
                    raise RuntimeError(f"超过{max_mb}MB上限")
    return os.path.getsize(out_path)

def pick_ytdlp_format(info, max_h=1080, max_mb=90):
    """从 yt-dlp -J 的 info 选 ≤max_h 且 ≤max_mb 的最优格式, 返回 (选择器, 高度)"""
    fmts = info.get("formats") or []
    def sz(f):
        s = f.get("filesize") or f.get("filesize_approx")
        return s if s else (f.get("tbr") or 0) * 1000 * (info.get("duration") or 0) / 8
    prog = [f for f in fmts if f.get("vcodec") not in (None, "none")
            and f.get("acodec") not in (None, "none") and (f.get("height") or 0) <= max_h]
    prog.sort(key=lambda f: ((f.get("height") or 0), f.get("tbr") or 0), reverse=True)
    for f in prog:
        if sz(f) <= max_mb * 1e6:
            return f["format_id"], f.get("height") or 0
    vonly = [f for f in fmts if f.get("vcodec") not in (None, "none")
             and f.get("acodec") in (None, "none") and (f.get("height") or 0) <= max_h]
    vonly.sort(key=lambda f: ((f.get("height") or 0), f.get("tbr") or 0), reverse=True)
    aonly = [f for f in fmts if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")]
    aonly.sort(key=lambda f: f.get("tbr") or 0, reverse=True)
    if vonly and aonly and shutil.which("ffmpeg"):
        v, a = vonly[0], aonly[0]
        if sz(v) + sz(a) <= max_mb * 1e6:
            return f'{v["format_id"]}+{a["format_id"]}', v.get("height") or 0
    if prog:
        return prog[0]["format_id"], prog[0].get("height") or 0
    if vonly and aonly:
        return f'{vonly[0]["format_id"]}+{aonly[0]["format_id"]}', vonly[0].get("height") or 0
    return "best", 0

def ytdlp_json(url, extra_args=None, timeout=300):
    args = [YTDLP, "-J", "--no-warnings"]
    if extra_args:
        args += extra_args
    args.append(url)
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        lines = (r.stderr or r.stdout or "").strip().splitlines()
        raise RuntimeError("yt-dlp -J 失败: " + (lines[-1][:300] if lines else "empty output"))
    return json.loads(r.stdout)

def find_out_file(out_dir, stem):
    for ext in (".mp4", ".webm", ".mkv", ".mov", ".m4v"):
        p = os.path.join(out_dir, stem + ext)
        if os.path.exists(p):
            return p
    for f in sorted(os.listdir(out_dir)):
        if f.startswith(stem) and os.path.splitext(f)[1] in (".mp4", ".webm", ".mkv", ".mov", ".m4v"):
            return os.path.join(out_dir, f)
    return None

def finish(platform, ok, msg):
    print(f"RESULT[{platform}] {'OK' if ok else 'FAIL'}: {msg}", flush=True)
