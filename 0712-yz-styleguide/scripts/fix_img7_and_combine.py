#!/usr/bin/env python3
"""Generate img7 as single 1:1 image (no split), inject animation, record MP4."""
import os, json, re, pathlib, html, subprocess, asyncio, shutil
from playwright.async_api import async_playwright

BASE = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test"
ROUND2 = os.path.join(BASE, "round2")
ROUND3 = os.path.join(BASE, "round3")

def load_vlm(idx):
    path = os.path.join(BASE, f"_vlm/img{idx}.json")
    with open(path, encoding="utf-8") as f:
        outer = json.load(f)
    content = outer["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.split("\n",1)[1].rsplit("```",1)[0]
    return json.loads(content)

def esc(s):
    return html.escape(str(s) if s is not None else "")

# Load sprite
with open("/home/z/my-project/scripts/v2.20-svg-sprite.txt", encoding="utf-8") as f:
    sprite = f.read()
with open("/home/z/my-project/scripts/yz-logo-icon-symbol.txt", encoding="utf-8") as f:
    icon = f.read()
sprite_full = sprite.replace("  </defs>", f"  {icon}\n  </defs>")

# 1:1 template (same as round2)
TEMPLATE_1x1 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1080">
<title>__TITLE__</title>
<style>
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap;}
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap;}
@font-face{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap;}
:root{--yz-accent:#fc8166;--yz-text:#312e2e;--yz-text-muted:#9a9595;--yz-border-soft:#e5e5e5;--yz-radius:6px;--yz-font:'AliPuHui',sans-serif;--yz-fs-body:40px;--yz-fs-title:48px;--yz-fs-footer:27px;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:var(--yz-font);background:#fff;padding:0;margin:0;}
.chart-container-1x1{position:relative;width:1080px;height:1080px;margin:0 auto;background:#fff;padding:32px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;}
.chart-header-1x1{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:24px;gap:24px;}
.chart-title-1x1{width:80%;font-size:var(--yz-fs-title);font-weight:900;color:var(--yz-text);line-height:1.35;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
.chart-logo-1x1{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}
.chart-logo-1x1 svg{height:96px;width:auto;}
.chart-body-1x1{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}
.chart-footer-1x1{flex-shrink:0;margin-top:20px;padding-top:14px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}
.chart-source-1x1{font-size:var(--yz-fs-footer);color:var(--yz-text-muted);text-align:left;line-height:1.5;flex:1;}
.chart-part-num{font-size:24px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:20px;}
.data-table-1x1{width:100%;border-collapse:collapse;font-size:28px;margin-top:10px;}
.data-table-1x1 th{background:#fafafa;padding:12px 8px;text-align:center;font-weight:900;color:#312e2e;border-bottom:2px solid #dcdcdc;font-size:24px;}
.data-table-1x1 td{padding:10px 8px;text-align:center;border-bottom:1px solid #f0f0f0;color:#312e2e;font-size:26px;}
.data-table-1x1 td:first-child{text-align:left;font-weight:700;color:#fc8166;}
.data-table-1x1 tr.section-header td{background:#fff5f0;font-weight:900;color:#fc8166;font-size:24px;}
.data-table-1x1 tr.total-row td{font-weight:900;background:#fafafa;}
#yz-selfcheck-banner{position:absolute;top:8px;right:8px;padding:8px 16px;border-radius:6px;font-size:14px;font-weight:700;z-index:99999;display:none;}
#yz-selfcheck-banner.pass{background:#50c885;color:#fff;display:block;}
#yz-selfcheck-banner.fail{background:#e60012;color:#fff;display:block;}
</style>
</head>
<body>
__SPRITE__
<div id="yz-selfcheck-banner"></div>
<div class="chart-container-1x1">
  <div class="chart-header-1x1">
    <h1 class="chart-title-1x1">__TITLE__</h1>
    <div class="chart-logo-1x1"><svg viewBox="0 0 199 231"><use href="#yz-logo-icon"/></svg></div>
  </div>
  <div class="chart-body-1x1">
__BODY__
  </div>
  <div class="chart-footer-1x1">
    <div class="chart-source-1x1">__FOOTER__</div>
    <div class="chart-part-num">__PART__</div>
  </div>
</div>
<script>
function yzSelfCheck1x1(){var errors=[];var cc=document.querySelector('.chart-container-1x1');if(cc){var w=cc.offsetWidth,h=cc.offsetHeight;if(Math.abs(w-1080)>5||Math.abs(h-1080)>5)errors.push('画布尺寸：'+w+'x'+h);}var banner=document.getElementById('yz-selfcheck-banner');if(errors.length===0){if(banner){banner.className='pass';banner.textContent='✅ 通过';}return true;}else{if(banner){banner.className='fail';banner.textContent='❌ '+errors.length+'项';}return false;}}
if(document.fonts){document.fonts.ready.then(function(){setTimeout(yzSelfCheck1x1,200);});}
</script>
</body>
</html>"""

ANIMATION_CSS = """
<style data-purpose="round3-animations">
.chart-logo-1x1, .chart-title-1x1, .chart-source-1x1, .chart-part-num,
.chart-body-1x1 .data-table-1x1 { opacity:0; }
.chart-body-1x1 .data-table-1x1 tbody tr { opacity:0; }
.chart-logo-1x1{ animation: fadeIn 1.2s ease-out 0s forwards; }
.chart-title-1x1{ animation: fadeIn 1.2s ease-out 1.5s forwards; }
.chart-source-1x1{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-part-num{ animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-body-1x1 .data-table-1x1{ animation: fadeIn 1.5s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1 thead{ animation: fadeIn 0.6s ease-out 4.5s forwards; opacity:0; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(1){ animation: rowFade 0.4s ease-out 4.5s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(2){ animation: rowFade 0.4s ease-out 4.7s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(3){ animation: rowFade 0.4s ease-out 4.9s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(4){ animation: rowFade 0.4s ease-out 5.1s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(5){ animation: rowFade 0.4s ease-out 5.3s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(6){ animation: rowFade 0.4s ease-out 5.5s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(7){ animation: rowFade 0.4s ease-out 5.7s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(8){ animation: rowFade 0.4s ease-out 5.9s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(9){ animation: rowFade 0.4s ease-out 6.1s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(10){ animation: rowFade 0.4s ease-out 6.3s forwards; }
.chart-body-1x1 .data-table-1x1 tbody tr:nth-child(11){ animation: rowFade 0.4s ease-out 6.5s forwards; }
@keyframes fadeIn{ to{ opacity:1; } }
@keyframes rowFade{ to{ opacity:1; } }
#yz-selfcheck-banner{ display:none !important; }
body{ background:#fff !important; padding:0 !important; margin:0 !important; }
</style>
"""

def build_img7_full():
    d = load_vlm(7)
    td = d.get("table_data", {})
    headers = td.get("headers", [])
    rows = td.get("rows", [])
    title = d.get("title_text", "")
    footer = d.get("data_source_text") or d.get("footer_text") or "数据来源：公司公告，娱乐资本论整理"
    
    parts = ['<table class="data-table-1x1"><thead><tr>']
    for h in headers:
        parts.append(f'<th>{esc(h)}</th>')
    parts.append('</tr></thead><tbody>')
    # Section headers are rows with empty cells (like "收入", "成本")
    section_headers = {"收入", "成本"}
    total_rows = {"总收入", "总成本", "营业利润", "营业利润率（OPM）"}
    for r in rows:
        first_cell = str(r[0]) if r else ""
        if first_cell in section_headers:
            parts.append('<tr class="section-header">')
        elif first_cell in total_rows:
            parts.append('<tr class="total-row">')
        else:
            parts.append('<tr>')
        for c in r:
            parts.append(f'<td>{esc(c)}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table>')
    body = "\n".join(parts)
    
    # Build round2 HTML
    html_out = TEMPLATE_1x1
    html_out = html_out.replace("__SPRITE__", sprite_full)
    html_out = html_out.replace("__TITLE__", esc(title))
    html_out = html_out.replace("__BODY__", body)
    html_out = html_out.replace("__FOOTER__", esc(footer))
    html_out = html_out.replace("__PART__", "1/1")
    
    r2_path = os.path.join(ROUND2, "img7-part1-styled.html")
    pathlib.Path(r2_path).write_text(html_out, encoding="utf-8")
    print(f"Wrote round2/img7-part1-styled.html ({len(html_out)} bytes)")
    
    # Build round3 HTML (inject animation)
    html_anim = html_out.replace("</head>", ANIMATION_CSS + "\n</head>", 1)
    r3_path = os.path.join(ROUND3, "img7-part1-styled.html")
    pathlib.Path(r3_path).write_text(html_anim, encoding="utf-8")
    print(f"Wrote round3/img7-part1-styled.html ({len(html_anim)} bytes)")
    
    return r3_path

async def record_mp4(html_path, mp4_path):
    name = "img7-full"
    frames_dir = f"/tmp/{name}"
    os.makedirs(frames_dir, exist_ok=True)
    for f in os.listdir(frames_dir): os.remove(os.path.join(frames_dir, f))
    FPS = 30; DUR = 6.0
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width":1100,"height":1100})
        await page.goto("file://"+html_path, wait_until="domcontentloaded")
        try: await page.evaluate("() => document.fonts.ready")
        except: pass
        await page.wait_for_timeout(50)
        container = await page.query_selector(".chart-container-1x1")
        if not container: await browser.close(); return False
        total = int(FPS*DUR)
        for i in range(total):
            await container.screenshot(path=os.path.join(frames_dir, f"frame_{i:04d}.png"))
            await asyncio.sleep(1.0/FPS)
        await browser.close()
    entrance = os.path.join(frames_dir, "entrance.mp4")
    static = os.path.join(frames_dir, "static.mp4")
    exit_v = os.path.join(frames_dir, "exit.mp4")
    last = os.path.join(frames_dir, f"frame_{total-1:04d}.png")
    subprocess.run(["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(frames_dir,"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",entrance], capture_output=True, timeout=120)
    subprocess.run(["ffmpeg","-y","-loop","1","-i",last,"-t","4","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",static], capture_output=True, timeout=120)
    subprocess.run(["ffmpeg","-y","-i",entrance,"-vf","reverse","-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",exit_v], capture_output=True, timeout=120)
    concat_txt = os.path.join(frames_dir, "concat.txt")
    with open(concat_txt, "w") as f:
        f.write(f"file '{entrance}'\n"); f.write(f"file '{static}'\n"); f.write(f"file '{exit_v}'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_txt,"-c:v","libx264","-pix_fmt","yuv420p","-preset","ultrafast",mp4_path], capture_output=True, timeout=120)
    ok = os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 50000
    shutil.rmtree(frames_dir, ignore_errors=True)
    return ok

async def main():
    # Step 1: Build img7 full HTML (round2 + round3)
    print("=== Step 1: Build img7 full HTML ===")
    r3_html = build_img7_full()
    
    # Step 2: Record img7 full MP4
    print("\n=== Step 2: Record img7 full MP4 ===")
    mp4_path = os.path.join(ROUND3, "img7-part1.mp4")
    ok = await record_mp4(r3_html, mp4_path)
    print(f"  {'OK' if ok else 'FAIL'} {os.path.getsize(mp4_path)//1024 if ok else 0}KB")
    
    # Step 3: Delete old img7-part1/2/3 (keep only img7-part1 which is now the full version)
    print("\n=== Step 3: Delete old split parts ===")
    for f in ["img7-part2-styled.html", "img7-part3-styled.html", "img7-part2.mp4", "img7-part3.mp4"]:
        for d in [ROUND2, ROUND3]:
            p = os.path.join(d, f)
            if os.path.exists(p):
                os.remove(p)
                print(f"  deleted {d}/{f}")
    # Also delete round2 img7-part2/3 if exist
    for f in ["img7-part2-styled.png", "img7-part3-styled.png"]:
        p = os.path.join(ROUND2, f)
        if os.path.exists(p):
            os.remove(p)
            print(f"  deleted round2/{f}")

asyncio.run(main())
