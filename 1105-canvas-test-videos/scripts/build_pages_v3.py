#!/usr/bin/env python3
"""重写 S02/S03/S14/S23 四个 canvas 页面（v3：黑底 + B站真实素材）。
S02/S03 = 透明叠层（视频背景由 ffmpeg 合成）；S14/S23 = 完整暗色页。
"""
import re

from PIL import Image, ImageDraw

CANVAS = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/canvas"
ASSETS = ".."

TPL = open(f"{CANVAS}/S01.html", encoding="utf-8").read()


def mark_slogan():
    """在原文截图上给口号画红框。"""
    p = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/assets/bili/origin_yiyimiao.png"
    im = Image.open(p).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    w, h = im.size
    # 第2行 30%-46%，横跨全行（口号在中部）
    y0, y1 = int(h * 0.28), int(h * 0.48)
    d.rectangle([int(w*0.04), y0, int(w*0.96), y1], outline=(229, 91, 70, 255), width=6)
    im = Image.alpha_composite(im, ov).convert("RGB")
    im.save("/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/assets/bili/origin_yiyimiao_marked.png")
    print("[ok] origin_yiyimiao_marked.png 红框已画")


def build_page(sid, bg_html, stage_html, page_css, dense, transparent=False):
    html = TPL
    # 1) 替换 BG
    html = re.sub(r"(YZ_EDIT_BG_BEGIN ======== -->).*?(<!-- ======== YZ_EDIT_BG_END)",
                  lambda m: m.group(1) + "\n    " + bg_html + "\n    " + m.group(2),
                  html, flags=re.S)
    # 2) 替换 STAGE
    html = re.sub(r"(YZ_EDIT_STAGE_BEGIN（每镜内容只改这里） ======== -->).*?(<!-- ======== YZ_EDIT_STAGE_END ======== -->)",
                  lambda m: m.group(1) + "\n    " + stage_html + "\n    " + m.group(2),
                  html, flags=re.S)
    # 3) 替换第二个 <style>（页面级）
    parts = html.split("<style>")
    assert len(parts) == 3, f"style块数异常 {len(parts)}"
    tail = parts[2]
    tail = re.sub(r"^.*?</style>", lambda m: page_css + "</style>", tail, count=1, flags=re.S)
    html = parts[0] + "<style>" + parts[1] + "<style>" + tail
    # 4) SHOOT_DENSE/KEYS：替换尾部声明 script（S01模板为 window.SHOOT_KEYS=[..];window.SHOOT_DENSE=window.SHOOT_DENSE||[];）
    html = re.sub(
        r"<script>\s*window\.SHOOT_KEYS=\[[^\]]*\];\s*window\.SHOOT_DENSE=window\.SHOOT_DENSE\|\|\[\];.*?</script>",
        lambda m: f"<script>window.SHOOT_DENSE={dense};</script>",
        html, flags=re.S)
    # 5) 透明模式
    if transparent:
        html = html.replace("background: #131110;\n", "background: transparent;\n")
        html = html.replace("background: #131110; }", "background: transparent; }")
        html = html.replace("#bg-layer { position: absolute; inset: 0; overflow: hidden; background: #131110; }",
                            "#bg-layer { position: absolute; inset: 0; overflow: hidden; background: transparent; }")
    open(f"{CANVAS}/{sid}.html", "w", encoding="utf-8").write(html)
    print(f"[ok] {sid}.html 写入 ({'透明叠层' if transparent else '暗色整页'}, dense={dense})")


# ============ S02 牌子 ============
S02_BG = '<div style="position:absolute;inset:0;background:rgba(0,0,0,.82);"></div>'
S02_STAGE = """
<div style="position:absolute;inset:0;display:flex;flex-direction:column;padding:26px 30px;">
  <div style="display:flex;align-items:center;gap:20px;" data-anim="up" data-t="0.1" data-d="0.4">
    <div style="font-size:44px;font-weight:900;color:#f2efec;">AI短片《牌子》</div>
    <div class="chip">UP主 DiDi_OK</div>
    <div class="chip chip-o">B站AI创作大赛 · 一等奖</div>
  </div>
  <div class="evi" data-anim="up" data-t="0.5" data-d="0.45">
    <div class="evi-lab">▶ B站播放量（视频页截图）</div>
    <div class="shotbox"><img src="../assets/bili/paizi_playcount_x3.png"></div>
    <div class="bignum">2152.1<span class="unit">万次</span></div>
  </div>
  <div style="display:flex;gap:24px;margin-top:26px;">
    <div class="evi" style="flex:1.15;" data-anim="up" data-t="1.5" data-d="0.45">
      <div class="evi-lab">👍 点赞（B站播放器截图）</div>
      <div class="shotbox"><img src="../assets/bili/paizi_like_x2.png"></div>
    </div>
    <div style="flex:1;display:flex;flex-direction:column;gap:18px;justify-content:center;">
      <div class="goldstamp" data-anim="stamp" data-t="3.0" data-d="0.35">23天</div>
      <div class="goldstamp" data-anim="stamp" data-t="3.7" data-d="0.35">业余时间</div>
      <div class="goldstamp" data-anim="stamp" data-t="4.4" data-d="0.35">¥100万奖金</div>
    </div>
  </div>
  <div class="evi" style="margin-top:26px;flex:1;display:flex;flex-direction:column;justify-content:center;" data-anim="up" data-t="5.4" data-d="0.5">
    <div class="evi-lab">名人背书 · 新闻报道截图</div>
    <div class="shotbox"><img src="../assets/bili/news_guofan_crop.png"></div>
    <div class="src2">——《流浪地球》导演郭帆转发点赞 · 腾讯新闻/差评 2026-02-13</div>
  </div>
</div>
"""
S02_CSS = """
.tt{font-size:64px;font-weight:900;color:#f2efec;}
.chip{display:inline-block;background:#2a2624;color:#b5aea9;border:1.5px solid #3a3634;
      border-radius:999px;padding:8px 24px;font-size:26px;font-weight:700;}
.chip-o{background:rgba(252,129,102,.14);color:#fc8166;border-color:rgba(252,129,102,.4);}
.evi{background:#1e1b19;border:1.5px solid #3a3634;border-radius:22px;padding:20px 24px;}
.evi-lab{font-size:24px;color:#8f8984;margin-bottom:12px;font-weight:700;letter-spacing:1px;}
.shotbox{background:#131110;border-radius:12px;padding:10px;display:flex;justify-content:center;align-items:center;}
.shotbox img{max-width:100%;max-height:150px;object-fit:contain;border-radius:6px;}
.bignum{font-size:74px;font-weight:900;color:#fc8166;margin-top:8px;text-align:center;letter-spacing:2px;}
.unit{font-size:30px;color:#b5aea9;margin-left:10px;font-weight:700;}
.goldstamp{background:linear-gradient(160deg,#3a2f1d,#28200f);border:2px solid #8a6d3b;color:#e8c07a;
           border-radius:14px;padding:14px 26px;font-size:38px;font-weight:900;text-align:center;
           transform:rotate(-1.5deg);box-shadow:0 6px 24px rgba(0,0,0,.5);}
.src2{font-size:22px;color:#a8a19b;margin-top:12px;text-align:right;}
"""

# ============ S03 丧尸清道夫 ============
S03_BG = '<div style="position:absolute;inset:0;background:rgba(0,0,0,.82);"></div>'
S03_STAGE = """
<div style="position:absolute;inset:0;display:flex;flex-direction:column;padding:26px 30px;">
  <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;" data-anim="up" data-t="0.1" data-d="0.4">
    <div style="font-size:42px;font-weight:900;color:#f2efec;">漫剧《丧尸清道夫》</div>
    <div class="chip">UP主 Mx-Shell</div>
    <div class="chip">云南县城 · 婚纱摄影师</div>
  </div>
  <div class="evi" data-anim="up" data-t="0.6" data-d="0.45">
    <div class="evi-lab">▶ B站播放量（重制版 · 视频页截图）</div>
    <div class="shotbox"><img src="../assets/bili/sss_playcount_x3.png"></div>
    <div class="bignum">424<span class="unit">万次</span></div>
  </div>
  <div style="display:flex;gap:24px;margin-top:26px;">
    <div class="evi" style="flex:1.15;" data-anim="up" data-t="1.8" data-d="0.45">
      <div class="evi-lab">👍 点赞（B站播放器截图）</div>
      <div class="shotbox"><img src="../assets/bili/sss_like_x2.png"></div>
    </div>
    <div style="flex:1;display:flex;flex-direction:column;gap:18px;justify-content:center;">
      <div class="goldstamp" data-anim="stamp" data-t="3.2" data-d="0.35">中专学历</div>
      <div class="goldstamp" data-anim="stamp" data-t="4.0" data-d="0.35">今年1月自学AI</div>
      <div class="goldstamp" data-anim="stamp" data-t="4.8" data-d="0.35">成本不到3000元</div>
    </div>
  </div>
  <div class="evi" style="margin-top:26px;flex:1;display:flex;flex-direction:column;justify-content:center;" data-anim="up" data-t="5.8" data-d="0.5">
    <div class="evi-lab">全网传播</div>
    <div style="font-size:88px;font-weight:900;color:#fc8166;text-align:center;letter-spacing:4px;">
      全网播放<span style="font-size:120px;">破亿</span></div>
    <div class="src2" style="text-align:center;">——口径：全网多平台累计 · B站重制版424万为截图实证</div>
  </div>
</div>
"""
S03_CSS = S02_CSS

# ============ S14 一元一秒 ============
S14_BG = '<div style="position:absolute;inset:0;background:#131110;"></div>' \
         '<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 38%,rgba(252,129,102,.07),transparent 62%);"></div>'
S14_STAGE = """
<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px 40px;">
  <div class="slogan" data-anim="pop" data-t="0.2" data-d="0.6">
    <div class="sl-main">一元一秒 · 百元造梦</div>
    <div class="sl-sub">—— 2026年初 · Seedance 2.0 时代的行业口号</div>
  </div>
  <div class="evi" style="margin-top:56px;width:100%;" data-anim="up" data-t="2.2" data-d="0.5">
    <div class="evi-lab">口号出处 · 原文截图（红框）</div>
    <div class="shotbox"><img src="../assets/bili/origin_yiyimiao_marked.png"></div>
    <div class="src2">——娱乐资本论《画布横评·价格篇》2026-10-08 · 腾讯新闻</div>
  </div>
  <div class="q" data-anim="up" data-t="4.2" data-d="0.5">到了质量更高的 Seedance 2.5 时代，成本还能维持「一元一秒」吗？</div>
</div>
"""
S14_CSS = """
.slogan{border:3px solid #8a6d3b;border-radius:18px;padding:36px 56px;transform:rotate(-1deg);
        background:linear-gradient(160deg,#332a1a,#28200f);box-shadow:0 10px 40px rgba(0,0,0,.55);}
.sl-main{font-size:86px;font-weight:900;color:#e8c07a;letter-spacing:6px;text-align:center;}
.sl-sub{font-size:26px;color:#b5aea9;margin-top:16px;text-align:center;letter-spacing:2px;}
.evi{background:#1e1b19;border:1.5px solid #3a3634;border-radius:22px;padding:20px 24px;}
.evi-lab{font-size:24px;color:#8f8984;margin-bottom:12px;font-weight:700;letter-spacing:1px;}
.shotbox{background:#131110;border-radius:12px;padding:10px;display:flex;justify-content:center;}
.shotbox img{max-width:100%;max-height:300px;object-fit:contain;border-radius:6px;}
.src2{font-size:22px;color:#a8a19b;margin-top:12px;text-align:right;}
.q{margin-top:46px;font-size:40px;font-weight:900;color:#f2efec;text-align:center;line-height:1.5;}
.q em{color:#fc8166;font-style:normal;}
"""

# ============ S23 Higgsfield ============
S23_BG = '<div style="position:absolute;inset:0;background:#131110;"></div>'
S23_STAGE = """
<div style="position:absolute;inset:0;display:flex;flex-direction:column;padding:24px 30px;">
  <div style="display:flex;align-items:center;gap:18px;" data-anim="up" data-t="0.1" data-d="0.4">
    <div style="font-size:40px;font-weight:900;color:#f2efec;">海外平台 Higgsfield · S2.5 「45折」核查</div>
    <div class="tag45" data-anim="stamp" data-t="1.0" data-d="0.3">宣称45折</div>
  </div>
  <div style="display:flex;gap:26px;margin-top:22px;flex:1;">
    <div class="evi" style="flex:1.05;display:flex;flex-direction:column;" data-anim="up" data-t="1.6" data-d="0.5">
      <div class="evi-lab">higgsfield.com/pricing 实截（2026-11）</div>
      <div class="shotbox" style="flex:1;position:relative;">
        <img src="../assets/bili/higgsfield_ultra.png" style="max-height:1000px;">
        <div class="rediv" data-anim="fade" data-t="4.0" data-d="0.4"></div>
      </div>
      <div class="src2">跑满240秒生成量 → 只能选最高档 Ultra</div>
    </div>
    <div style="flex:1;display:flex;flex-direction:column;gap:20px;">
      <div class="calc" data-anim="stamp" data-t="5.2" data-d="0.4">
        <div class="c-lab">Ultra 月付</div>
        <div class="c-big">$129<span class="c-unit">/月</span></div>
        <div class="c-eq">≈ ¥864 / 月</div>
      </div>
      <div class="calc warn" data-anim="stamp" data-t="7.0" data-d="0.4">
        <div class="c-lab">长期年付高档位</div>
        <div class="c-big">一次付费</div>
        <div class="c-eq" style="color:#e55b46;">轻松破万元</div>
      </div>
      <div class="verdict" data-anim="up" data-t="9.0" data-d="0.5">
        <span class="no">✗</span> 对国内个人创作者并不划算
      </div>
    </div>
  </div>
</div>
"""
S23_CSS = """
.evi{background:#1e1b19;border:1.5px solid #3a3634;border-radius:22px;padding:18px 22px;}
.evi-lab{font-size:22px;color:#8f8984;margin-bottom:10px;font-weight:700;letter-spacing:1px;}
.shotbox{background:#131110;border-radius:12px;padding:8px;display:flex;justify-content:center;align-items:flex-start;position:relative;}
.shotbox img{max-width:100%;object-fit:contain;border-radius:6px;}
.src2{font-size:21px;color:#a8a19b;margin-top:10px;text-align:center;}
.tag45{background:rgba(252,129,102,.16);border:2px solid #fc8166;color:#fc8166;border-radius:999px;
       padding:8px 26px;font-size:30px;font-weight:900;transform:rotate(2deg);}
.rediv{position:absolute;top:17%;left:12%;width:64%;height:8.5%;border:4px solid #e55b46;border-radius:10px;
       box-shadow:0 0 0 3000px rgba(0,0,0,.25);}
.calc{background:#1e1b19;border:1.5px solid #3a3634;border-radius:20px;padding:22px 28px;text-align:center;}
.calc.warn{border-color:rgba(229,91,70,.55);background:rgba(229,91,70,.08);}
.c-lab{font-size:24px;color:#8f8984;font-weight:700;}
.c-big{font-size:72px;font-weight:900;color:#f2efec;margin-top:6px;}
.c-unit{font-size:28px;color:#b5aea9;font-weight:700;margin-left:8px;}
.c-eq{font-size:36px;font-weight:900;color:#fc8166;margin-top:6px;}
.verdict{background:#1e1b19;border-radius:20px;padding:20px 24px;font-size:34px;font-weight:900;color:#f2efec;
         text-align:center;border:1.5px solid #3a3634;}
.no{color:#e55b46;font-size:44px;margin-right:10px;}
"""


def main():
    mark_slogan()
    build_page("S02", S02_BG, S02_STAGE, S02_CSS, "[[0, 6.5, 12]]", transparent=True)
    build_page("S03", S03_BG, S03_STAGE, S03_CSS, "[[0, 6.8, 12]]", transparent=True)
    build_page("S14", S14_BG, S14_STAGE, S14_CSS, "[[0, 5.5, 8]]")
    build_page("S23", S23_BG, S23_STAGE, S23_CSS, "[[0.8, 10.0, 10]]")


if __name__ == "__main__":
    main()
