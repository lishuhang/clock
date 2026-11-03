#!/usr/bin/env python3
# 素材批量下载(幂等续跑版): plan.json → B站游客 pagelist→playurl(自动qn降档80/64/32)
# 体检: 时长残缺比对 + ffmpeg致命错误(仅NAL/Invalid data/moov/corrupt;dts警告放行)
# 已下载且体检通过的条目直接复用(只补九宫格);失败自动落fallback_bvid一次
import requests, json, os, sys, subprocess, time, glob, shutil
sys.path.insert(0, "/home/z/my-project/clock/1103-agent-downloader/tools")
from lib_media import (log, wentry, now, probe, download, UA_PC, WORK)

MAT = os.path.join(WORK, "materials")
CLIPS = os.path.join(MAT, "clips")
THUMBS = os.path.join(MAT, "thumbs")
for d in (CLIPS, THUMBS):
    os.makedirs(d, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": UA_PC, "Referer": "https://www.bilibili.com/",
                  "Accept": "application/json, text/plain, */*"})
HDR = {"Referer": "https://www.bilibili.com/", "User-Agent": UA_PC}
QN2H = {80: 1080, 74: 720, 64: 720, 32: 480, 16: 360}

def api_pagelist(bvid):
    j = S.get("https://api.bilibili.com/x/player/pagelist",
              params={"bvid": bvid}, timeout=20).json()
    if j.get("code") != 0 or not j.get("data"):
        return None, f"pagelist code={j.get('code')} msg={j.get('message')}"
    return j["data"], None

def api_playurl(bvid, cid, qn):
    j = S.get("https://api.bilibili.com/x/player/playurl",
              params={"bvid": bvid, "cid": cid, "qn": qn, "platform": "html5",
                      "high_quality": 1}, timeout=20).json()
    if j.get("code") != 0 or not (j.get("data") or {}).get("durl"):
        return None, f"playurl qn={qn} code={j.get('code')} msg={j.get('message')}"
    return j["data"], None

def total_size(d):
    return sum(p.get("size") or 0 for p in d["durl"])

def best_playurl(bvid, cid):
    """qn 80→64→32 自动降档, 取首个 ≤260MB 的档"""
    fallback = None
    for qn in (80, 64, 32):
        d, e = api_playurl(bvid, cid, qn)
        if d is None:
            continue
        if fallback is None or total_size(d) < total_size(fallback):
            fallback = d
        if total_size(d) <= 260 * 1e6:
            return d
    return fallback

def health(out, expect_dur, expect_size=None):
    """体检: 字节数比对(±2%,防timeout半截) + 时长比对(±15%) + ffmpeg致命错误; dts警告放行"""
    if not os.path.exists(out) or os.path.getsize(out) < 50000:
        return "文件过小/不存在"
    if expect_size and os.path.getsize(out):
        if abs(os.path.getsize(out) - expect_size) / expect_size > 0.02:
            return f"字节数残缺 {os.path.getsize(out)/1e6:.1f}MB≠{expect_size/1e6:.1f}MB"
    p = probe(out)
    ad = float(p.get("duration") or 0)
    if not ad:
        return "ffprobe无duration"
    if expect_dur and abs(ad - expect_dur) / expect_dur > 0.15:
        return f"时长残缺 {ad:.0f}s≠{expect_dur}s"
    chk = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-f", "null", "-"],
                         capture_output=True, text=True, timeout=600)
    err = (chk.stderr or "").strip()
    for fatal in ("Invalid data", "NAL unit", "moov", "corrupt", "unable to decode",
                  "Error splitting", "EOF"):
        if fatal.lower() in err.lower():
            return "坏包:" + err[:120]
    return None

def grab_parts(d, out):
    parts = d["durl"]
    if len(parts) == 1:
        download(parts[0]["url"], out, HDR, "material", 300)
    else:
        tmp = out + ".parts"
        os.makedirs(tmp, exist_ok=True)
        plist = []
        for i, p in enumerate(parts):
            seg = os.path.join(tmp, f"{i:02d}.mp4")
            download(p["url"], seg, HDR, "material", 300)
            plist.append(seg)
        with open(os.path.join(tmp, "list.txt"), "w") as f:
            for seg in plist:
                f.write(f"file '{seg}'\n")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                            "-i", os.path.join(tmp, "list.txt"), "-c", "copy", out],
                           capture_output=True, text=True, timeout=300)
        shutil.rmtree(tmp, ignore_errors=True)
        if r.returncode != 0 or not os.path.exists(out):
            raise RuntimeError("concat失败: " + (r.stderr or "")[-120:])

def fetch(bvid, seq, expect_dur):
    out = os.path.join(CLIPS, f"S{seq:03d}_bili_{bvid}.mp4")
    pages, e = api_pagelist(bvid)
    if not pages:
        raise RuntimeError(e)
    page0 = pages[0]
    cid = page0.get("cid")
    exp_dur = page0.get("duration") or expect_dur  # pagelist官方分P时长优先(搜索API的dur不可靠)
    d = best_playurl(bvid, cid)
    if not d:
        raise RuntimeError(f"playurl全档不可得 {bvid}")
    log("material-dl", "playurl", f"S{seq:03d} {bvid} parts={len(d['durl'])} qn={d.get('quality')} "
        f"预估{total_size(d)/1e6:.0f}MB 分P时长{exp_dur}s(plan记{expect_dur}s)")
    for attempt in (1, 2):
        if os.path.exists(out):
            os.remove(out)
        try:
            grab_parts(d, out)
        except Exception as ge:  # 网络中断同坏包处理: 删残留重下一次
            log("material-dl", "badpack", f"S{seq:03d} attempt{attempt} 网络中断: {str(ge)[:120]}")
            continue
        h = health(out, exp_dur, total_size(d))
        if h is None:
            return out, d.get("quality")
        log("material-dl", "badpack", f"S{seq:03d} attempt{attempt}: {h}")
    raise RuntimeError("两次体检均失败: " + h[:100])

def fetch_ytdlp(bvid, seq, exp_dur):
    """换路兕底: yt-dlp免登录(480p档, B11); 文件名与主通路一致以便幂等"""
    url = f"https://www.bilibili.com/video/{bvid}"
    out = os.path.join(CLIPS, f"S{seq:03d}_bili_{bvid}.mp4")
    import lib_media as LM
    info = LM.ytdlp_json(url)
    fmt, height = LM.pick_ytdlp_format(info, 1080, 300)
    r = subprocess.run([LM.YTDLP, "-f", fmt, "--merge-output-format", "mp4", "-o",
                        out + ".%(ext)s", url], capture_output=True, text=True, timeout=560)
    got = LM.find_out_file(CLIPS, f"S{seq:03d}_bili_{bvid}")
    if r.returncode != 0 or not got:
        raise RuntimeError("yt-dlp下载失败: " + ((r.stderr or "").strip().splitlines()[-1:] or ["?"])[0][:150])
    if got != out:
        os.replace(got, out)
    h = health(out, exp_dur, None)
    if h:
        raise RuntimeError("yt-dlp体检: " + h[:100])
    return out, f"ytdlp-{height}p"

def grid(out, seq):
    D = float(probe(out).get("duration") or 0)
    if D <= 0:
        return None
    tmp = os.path.join(THUMBS, f"S{seq:03d}.tmp")
    os.makedirs(tmp, exist_ok=True)
    made = 0
    for k in range(1, 10):
        t = D * k / 10.0 * 0.98
        seg = os.path.join(tmp, f"f{k:02d}.jpg")
        r = subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-ss", f"{t:.1f}", "-i", out,
                            "-frames:v", "1", "-vf", "scale=170:96", "-q:v", "6", seg],
                           capture_output=True, timeout=60)
        if os.path.exists(seg) and os.path.getsize(seg) > 200:
            made += 1
    dst = None
    if made >= 3:
        dst = os.path.join(THUMBS, f"S{seq:03d}_grid.jpg")
        subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-pattern_type", "glob", "-i",
                        os.path.join(tmp, "f*.jpg"),
                        "-vf", ("tile=3x3" if made >= 9 else f"tile={made}x1"),
                        "-q:v", "6", dst], capture_output=True, timeout=60)
    shutil.rmtree(tmp, ignore_errors=True)
    return dst if (dst and os.path.exists(dst)) else None

def main():
    plan = json.load(open(os.path.join(MAT, "plan.json"), encoding="utf-8"))
    metas = json.load(open(os.path.join(MAT, "materials.json"), encoding="utf-8")).get("materials", []) \
        if os.path.exists(os.path.join(MAT, "materials.json")) else []
    metas = {m["seq"]: m for m in metas}
    for it in plan["items"]:
        seq, bvid, exp = it["seq"], it["bvid"], it.get("dur")
        out = os.path.join(CLIPS, f"S{seq:03d}_bili_{bvid}.mp4")
        use_bvid, note, quality = bvid, None, None
        # 幂等: 主目标文件在且体检过(含字节数比对) → 直接复用
        out_ok = False
        if os.path.exists(out):
            pages0, _e0 = api_pagelist(bvid)
            if pages0:
                d0 = best_playurl(bvid, (pages0 or [{}])[0].get("cid"))
                exp0 = (pages0 or [{}])[0].get("duration") or exp
                if d0 and health(out, exp0, total_size(d0)) is None:
                    note, out_ok = "cached(体检通过复用)", True
        if not out_ok:
            try:
                out, quality = fetch(bvid, seq, exp)
                note = "primary"
            except Exception as e:
                msg = str(e)[:180]
                log("material-dl", "fail", f"S{seq:03d} {bvid} primary失败: {msg}")
                out, use_bvid = None, bvid
                fb = it.get("fallback_bvid")
                if fb:
                    fbout = os.path.join(CLIPS, f"S{seq:03d}_bili_{fb}.mp4")
                    if os.path.exists(fbout) and health(fbout, it.get("fallback_dur") or exp) is None:
                        out, use_bvid, note = fbout, fb, "cached-fallback"
                    else:
                        try:
                            time.sleep(2)
                            out, quality = fetch(fb, seq, it.get("fallback_dur") or exp)
                            use_bvid, note = fb, "fallback"
                        except Exception as e2:
                            log("material-dl", "fail", f"S{seq:03d} fallback也失败: {str(e2)[:150]}")
                if not out:  # 最后换路: yt-dlp免登录(每素材仅此1次)
                    try:
                        time.sleep(2)
                        out, quality = fetch_ytdlp(bvid, seq, exp)
                        note = "ytdlp换路"
                    except Exception as e3:
                        log("material-dl", "fail", f"S{seq:03d} yt-dlp兕底也失败: {str(e3)[:150]}")
        if not out:
            metas[seq] = {"seq": seq, "bvid": use_bvid, "status": "fail", "points": it["points"]}
            print(f"S{seq:03d} FAIL {bvid}->{use_bvid}")
            continue
        # 清理同seq其他残留(旧fallback/半截文件)
        for f in glob.glob(os.path.join(CLIPS, f"S{seq:03d}_bili_*.mp4")):
            if os.path.basename(f) != os.path.basename(out):
                os.remove(f)
                log("material-dl", "clean", f"删除残留 {os.path.basename(f)}")
        p = probe(out)
        g = os.path.join(THUMBS, f"S{seq:03d}_grid.jpg")
        if note not in ("cached(体检通过复用)", "cached-fallback") and os.path.exists(g):
            os.remove(g)  # 刚重新下载的条目,旧九宫格作废
            log("material-dl", "grid", f"S{seq:03d} 重做九宫格(文件更新)")
        if not os.path.exists(g):
            g = grid(out, seq) or ""
        metas[seq] = {
            "seq": seq, "bvid": use_bvid, "status": "ok", "note": note,
            "source_url": f"https://www.bilibili.com/video/{use_bvid}",
            "author": it["author"], "title": it["title"],
            "duration_sec": round(float(p.get("duration") or 0), 1),
            "resolution": f"{p.get('width')}x{p.get('height')}",
            "size_mb": round(p["size"] / 1e6, 1), "quality": QN2H.get(quality, quality),
            "file": os.path.basename(out),
            "grid": os.path.basename(g) if g else None,
            "points": it["points"],
            "method": "B站游客 html5 playurl durl(qn自动降档80/64/32)",
        }
        print(f"S{seq:03d} OK {use_bvid} {metas[seq]['size_mb']}MB {metas[seq]['resolution']} "
              f"dur={metas[seq]['duration_sec']}s {note or ''}")
        time.sleep(2)
    metas = [metas[k] for k in sorted(metas)]
    json.dump({"updated": now(), "materials": metas},
              open(os.path.join(MAT, "materials.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ok = sum(1 for m in metas if m["status"] == "ok")
    tot = sum(m.get("size_mb", 0) for m in metas)
    stat = f"{ok}/{len(metas)} ok, total {tot:.0f}MB"
    print("RESULT:", stat)
    if ok == len(metas):
        wentry("material-download", "OK", "dl_materials.py (plan.json驱动, 幂等续跑)",
               "materials/materials.json",
               [f"S{m['seq']:03d} {m['bvid']} {m['size_mb']}MB {m['resolution']} {m['note']}"
                for m in metas], f"素材下载 {stat}", "九宫格抽帧已完成 → 大模型复判 → 分镜表")

if __name__ == "__main__":
    main()
