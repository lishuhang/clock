#!/usr/bin/env python3
"""
Generate v2.21a-yz-styleguide.html — the精简 skill that固化 all round1.1+1.2 fixes.

Strategy:
  - Read v2.20-styled-template.html (extracted template with @font-face, :root, SVG sprite, CSS, JS)
  - Modify CSS in-place to固化 round1.2 fixes (canvas auto-height, font ×2, watermark ×1.5+z-index, logo ×1.3)
  - Append SHARED_CSS (phase-label, dumbbell-track, chart-legend, etc.)
  - Append example code blocks (6 chart types) as HTML comments for agent reference
  - Write to 0811-test/v2.21a-yz-styleguide.html
"""
import os, re, pathlib

TEMPLATE = "/home/z/my-project/scripts/v2.20-styled-template.html"
OUT = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/v2.21a-yz-styleguide.html"

# ════════════════════════════════════════════════════════════════
# CSS patches — string replacements on v2.20 template
# Each tuple: (old_string, new_string, description)
# ════════════════════════════════════════════════════════════════
CSS_PATCHES = [
    # 1. .chart-container: min-height 1080px → auto, padding 48px 40px → 56px 48px
    (
        ".chart-container{\n  position:relative;\n  width:900px;\n  min-height:1080px;  /* 1.2:1 默认。可改为 900(1:1) 或 1350(1.5:1) */\n  margin:0 auto;\n  background:#fff;\n  padding:48px 40px;",
        ".chart-container{\n  position:relative;\n  width:900px;\n  min-height:auto;  /* v2.21a: auto-fit content height, no bottom blank */\n  height:auto;\n  margin:0 auto;\n  background:#fff;\n  padding:56px 48px;",
        "canvas auto-height"
    ),
    # 2. .yz-watermark svg: 280px → 420px (×1.5)
    (
        ".yz-watermark svg{\n  width:280px;\n  height:auto;\n  opacity:0.1;\n}",
        ".yz-watermark svg{\n  width:420px;  /* v2.21a: ×1.5 from 280px */\n  height:auto;\n  opacity:0.10;\n}\n.yz-watermark{ z-index:9999; }  /* v2.21a: above all content */\n.chart-body{ z-index:auto; }  /* v2.21a: avoid stacking context trap */",
        "watermark ×1.5 + z-index"
    ),
    # 3. .chart-title: 34px → 68px (×2)
    (
        ".chart-title{\n  position:relative;\n  z-index:2;\n  font-size:34px;",
        ".chart-title{\n  position:relative;\n  z-index:2;\n  font-size:68px;  /* v2.21a: ×2 from 34px */",
        "title ×2"
    ),
    # 4. .chart-body: flex:1 1 auto → 0 1 auto, min-height:400px → auto
    (
        ".chart-body{\n  position:relative;\n  z-index:2;\n  flex:1 1 auto;\n  min-height:400px;",
        ".chart-body{\n  position:relative;\n  z-index:auto;  /* v2.21a: auto to avoid stacking context */\n  flex:0 1 auto;  /* v2.21a: don't stretch */\n  min-height:auto;  /* v2.21a: auto-fit */",
        "chart-body flex+min-height"
    ),
    # 5. .chart-source: 13px → 26px (×2)
    (
        ".chart-source{\n  font-size:13px;",
        ".chart-source{\n  font-size:26px;  /* v2.21a: ×2 from 13px */",
        "footer ×2"
    ),
    # 6. .chart-footer: margin-top 24px → 36px, padding-top 16px → 24px
    (
        ".chart-footer{\n  position:relative;\n  z-index:2;\n  display:flex;\n  justify-content:space-between;\n  align-items:flex-end;\n  margin-top:24px;\n  padding-top:16px;",
        ".chart-footer{\n  position:relative;\n  z-index:2;\n  display:flex;\n  justify-content:space-between;\n  align-items:flex-end;\n  margin-top:36px;  /* v2.21a: larger gap */\n  padding-top:24px;  /* v2.21a: larger gap */",
        "footer margin"
    ),
    # 7. .yz-logo-svg: 48px → 62px (×1.3)
    (
        ".yz-logo-svg{\n  height:48px;",
        ".yz-logo-svg{\n  height:62px;  /* v2.21a: ×1.3 from 48px */",
        "logo ×1.3"
    ),
    # 8. .yz-table: 14px → 28px
    (
        ".yz-table{width:100%;border-collapse:collapse;font-size:14px;}",
        ".yz-table{width:100%;border-collapse:collapse;font-size:28px;}  /* v2.21a: ×2 */",
        "table ×2"
    ),
    # 9. .yz-bar-label: 14px → 28px, width 140px → 240px
    (
        ".yz-bar-label{width:140px;font-size:14px;",
        ".yz-bar-label{width:240px;font-size:28px;  /* v2.21a: ×2 */",
        "bar-label ×2"
    ),
    # 10. .yz-bar: 14px → 28px
    (
        ".yz-bar{height:100%;background:var(--c,var(--yz-accent));border-radius:var(--yz-radius);display:flex;align-items:center;justify-content:flex-end;padding-right:8px;color:#111;font-weight:900;font-size:14px;}",
        ".yz-bar{height:100%;background:var(--c,var(--yz-accent));border-radius:var(--yz-radius);display:flex;align-items:center;justify-content:flex-end;padding-right:8px;color:#111;font-weight:900;font-size:28px;}  /* v2.21a: ×2 */",
        "bar ×2"
    ),
    # 11. .yz-bar-value: 14px → 28px
    (
        ".yz-bar-value{margin-left:8px;font-weight:900;font-size:14px;",
        ".yz-bar-value{margin-left:8px;font-weight:900;font-size:28px;  /* v2.21a: ×2 */",
        "bar-value ×2"
    ),
    # 12. .yz-line-chart .axis-text: 12px → 24px
    (
        ".yz-line-chart .axis-text{font-family:var(--yz-font);font-size:12px;",
        ".yz-line-chart .axis-text{font-family:var(--yz-font);font-size:24px;  /* v2.21a: ×2 */",
        "axis-text ×2"
    ),
    # 13. .chart-container inline style: remove min-height:1080px
    (
        '<div class="chart-container" style="width:900px;min-height:1080px;">',
        '<div class="chart-container" style="width:900px;min-height:auto;height:auto;">',
        "inline min-height"
    ),
]

# ════════════════════════════════════════════════════════════════
# SHARED_CSS — reusable classes for all chart types
# Appended after the template's existing CSS
# ════════════════════════════════════════════════════════════════
SHARED_CSS = """
/* ════════════════════════════════════════════════════════════════
   v2.21a SHARED CSS — reusable classes for all chart types
   Agent: use these classes instead of defining new ones.
   ════════════════════════════════════════════════════════════════ */

/* ── 阶段名 + 圆形数字徽章 ── */
.phase-label{
  font-size:30px; font-weight:900; color:#312e2e;
  display:flex; align-items:center; gap:14px;
}
.phase-label .phase-badge{
  display:inline-flex; align-items:center; justify-content:center;
  width:44px; height:44px; background:#fc8166; color:#fff;
  border-radius:50%; font-size:26px; font-weight:900; flex-shrink:0;
}

/* ── 哑铃轨道 ── */
.dumbbell-track{
  position:relative; height:64px; background:#fafafa; border-radius:32px;
}
.dumbbell-track::before{
  content:""; position:absolute; top:50%; left:0; right:0;
  height:3px; background:#eee; transform:translateY(-50%);
}

/* ── 圆点 ── */
.dumbbell-dot{
  position:absolute; top:50%; transform:translate(-50%,-50%);
  width:34px; height:34px; border-radius:50%;
  border:5px solid #fff; box-shadow:0 0 0 3px currentColor; z-index:2;
}

/* ── 圆点数值标签 ── */
/* above: top:-50px; pair with parent gap ≥70px to avoid overlap */
.dumbbell-tag{
  position:absolute; font-size:22px; font-weight:700;
  white-space:nowrap; transform:translateX(-50%);
}
.dumbbell-tag.above{ top:-50px; }
.dumbbell-tag.below{ bottom:-50px; }

/* ── 连接线 ── */
.dumbbell-line{
  position:absolute; top:50%; height:6px; transform:translateY(-50%); z-index:1;
}

/* ── x 轴刻度 ── */
.axis-scale{
  display:flex; justify-content:space-between;
  font-size:18px; color:#9a9595; margin-top:14px; padding:0 4px;
}

/* ── 图例 ── */
.chart-legend{
  display:flex; flex-wrap:wrap; gap:18px 32px;
  margin-top:14px; font-size:22px; color:#6b6666;
}
.chart-legend .legend-item{ display:flex; align-items:center; gap:10px; }
.chart-legend .legend-swatch{ width:24px; height:24px; border-radius:50%; }
.chart-legend .legend-swatch.bar{ width:32px; height:8px; border-radius:4px; }

/* ── 热力图表格 ── */
.hm-table{width:100%;border-collapse:separate;border-spacing:6px;font-size:28px;}
.hm-table th{padding:18px 10px;text-align:center;font-weight:900;color:#312e2e;background:#fafafa;border-radius:6px;font-size:24px;}
.hm-table th.row-head{background:transparent;text-align:left;padding-left:14px;color:#fc8166;}
.hm-table td{padding:22px 8px;text-align:center;border-radius:6px;font-weight:700;color:#312e2e;min-width:110px;font-size:26px;}
.hm-table td.row-label{text-align:left;padding-left:14px;font-weight:700;color:#fc8166;background:#fff;font-size:24px;}
.hm-legend{display:flex;align-items:center;gap:20px;margin-top:24px;font-size:22px;color:#6b6666;}
.hm-legend .grad{display:inline-block;width:240px;height:16px;background:linear-gradient(to right,rgba(252,129,102,0.05),rgba(252,129,102,1));border-radius:3px;}

/* ── 堆叠柱状图 ── */
.sb-wrap{display:flex;flex-direction:column;gap:36px;}
.sb-row{display:flex;flex-direction:column;gap:12px;}
.sb-bar{display:flex;width:100%;height:80px;border-radius:8px;overflow:hidden;background:#fafafa;}
.sb-seg{display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;color:#fff;}

/* ── 文字卡牌 2×2 ── */
.tc-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;position:relative;z-index:2;}
.tc-card{
  border:1px solid #f0f0f0; border-left:8px solid #fc8166;
  border-radius:8px; padding:28px 32px;
  background:rgba(255,255,255,0.92);  /* semi-transparent for watermark */
  display:flex; flex-direction:column; gap:14px; position:relative;
}
.tc-card-head{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;}
.tc-phase{font-size:24px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:10px;}
.tc-phase .phase-badge{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;background:#fc8166;color:#fff;border-radius:50%;font-size:22px;font-weight:900;}
.tc-work{font-size:30px;font-weight:900;color:#312e2e;}
.tc-meta{font-size:24px;color:#9a9595;margin-left:auto;display:flex;gap:18px;}
.tc-meta b{color:#312e2e;font-weight:900;}
.tc-quote{font-size:26px;line-height:1.65;color:#312e2e;font-weight:500;}
.tc-quote .qmark{color:#fc8166;font-weight:900;font-size:36px;line-height:0;vertical-align:-6px;}
"""

# ════════════════════════════════════════════════════════════════
# Example code blocks — appended as HTML comments for agent reference
# ════════════════════════════════════════════════════════════════
EXAMPLES = """
<!--
═══════════════════════════════════════════════════════════════
  图表类型示例代码（agent 参考，替换【CHART_BODY_HERE】时使用）
═══════════════════════════════════════════════════════════════

  以下示例展示 6 种常见图表类型的 chart-body HTML 写法。
  所有示例都使用 v2.21a 的 SHARED CSS 类。
  Agent 复制对应类型的代码，替换数据即可。

  ─────────────────────────────────────────────────────────────
  示例 1：热力图表格（10行×6列，颜色深浅=数值）
  ─────────────────────────────────────────────────────────────
  <table class="hm-table">
    <thead><tr>
      <th class="row-head"></th>
      <th>列1</th><th>列2</th><th>列3</th>
    </tr></thead>
    <tbody>
      <tr>
        <td class="row-label">行名1</td>
        <td style="background:rgba(252,129,102,0.71);color:#fff;">71%</td>
        <td style="background:rgba(252,129,102,0.03);">3%</td>
        <td style="background:rgba(252,129,102,0.22);">22%</td>
      </tr>
    </tbody>
  </table>
  <div class="hm-legend"><span>低占比</span><span class="grad"></span><span>高占比</span></div>

  注意：单元格背景色用 rgba(252,129,102, opacity)，opacity = 百分比/100。
  数值>55%时文字改白色，否则深色。

  ─────────────────────────────────────────────────────────────
  示例 2：堆叠横向柱状图（4阶段×6维度）
  ─────────────────────────────────────────────────────────────
  <div class="sb-wrap">
    <div class="sb-row">
      <div class="phase-label"><span class="phase-badge">1</span>阶段名</div>
      <div class="sb-bar">
        <div class="sb-seg" style="background:#fc8166;flex:86.08 0 0;">86.08%</div>
        <div class="sb-seg" style="background:#e74c3c;flex:9.16 0 0;">9.16%</div>
        <div class="sb-seg" style="background:#a569bd;flex:2.03 0 0;" title="社会文化/性别: 2.03%"></div>
      </div>
    </div>
  </div>
  <div class="chart-legend">
    <div class="legend-item"><span class="legend-swatch bar" style="background:#fc8166"></span>专业能力</div>
    <div class="legend-item"><span class="legend-swatch bar" style="background:#e74c3c"></span>民族国家</div>
  </div>

  颜色映射：专业能力#fc8166 / 道德人格#7dd3f9 / 民族国家#e74c3c /
  商业资本#f39c12 / 社会文化/性别#a569bd / 身份符号#a8d08d

  ─────────────────────────────────────────────────────────────
  示例 3：哑铃图（4阶段，每阶段双点）
  ─────────────────────────────────────────────────────────────
  <div style="display:flex;flex-direction:column;gap:90px;padding:8px 0;">
    <div style="display:flex;flex-direction:column;gap:70px;">
      <div class="phase-label"><span class="phase-badge">1</span>阶段名</div>
      <div class="dumbbell-track">
        <div class="dumbbell-line" style="left:14.8%;width:67.7%;background:#dcdcdc;"></div>
        <div class="dumbbell-dot" style="left:14.8%;background:#fc8166;color:#fc8166;"></div>
        <div class="dumbbell-tag above" style="left:14.8%;color:#fc8166;">14.8%</div>
        <div class="dumbbell-dot" style="left:82.5%;background:#6cb0f9;color:#6cb0f9;"></div>
        <div class="dumbbell-tag below" style="left:82.5%;color:#6cb0f9;">82.5%</div>
      </div>
    </div>
  </div>
  <div class="axis-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
  <div class="chart-legend">
    <div class="legend-item"><span class="legend-swatch" style="background:#fc8166"></span>序列A</div>
    <div class="legend-item"><span class="legend-swatch" style="background:#6cb0f9"></span>序列B</div>
  </div>

  注意：行间距 gap:90px，行内 phase-label 到 track gap:70px，
  above 标签 top:-50px，below 标签 bottom:-50px。
  圆点 left 值要 clamp 在 2%~98% 避免边缘裁切。

  ─────────────────────────────────────────────────────────────
  示例 4：文字卡牌 2×2（4张引言卡）
  ─────────────────────────────────────────────────────────────
  <div class="tc-grid">
    <div class="tc-card">
      <div class="tc-card-head">
        <span class="tc-phase"><span class="phase-badge">1</span>阶段名</span>
        <span class="tc-work">作品名</span>
        <span class="tc-meta"><span>年份 <b>2017</b></span><span>评分 <b>4星</b></span></span>
      </div>
      <div class="tc-quote"><span class="qmark">"</span>引言内容<span class="qmark">"</span></div>
    </div>
  </div>

  注意：引号用真实 UTF-8 字符 " "（U+201C/U+201D），
  不要用 CSS content:"\\201C"（会乱码）。
  卡片背景 rgba(255,255,255,0.92) 半透明，让水印穿透。

  ─────────────────────────────────────────────────────────────
  示例 5：多序列哑铃（3子图，每个10行）
  ─────────────────────────────────────────────────────────────
  参考 round1.2 img5 的结构：3个子图垂直堆叠，每个子图10行哑铃。
  每行：电影名(240px) | 哑铃轨道(1fr) | 差值(110px)
  白心圆点=上映初期，实心圆点=当下，半透明线连接。

  ─────────────────────────────────────────────────────────────
  示例 6：散点对比哑铃（5部×2评分）
  ─────────────────────────────────────────────────────────────
  参考 round1.2 img6 的结构：5行，每行电影名+差值在上一行，
  哑铃轨道在下一行。橙色点=性别批评评分，蓝色点=电影总分，
  虚线连接。x轴 1星~5星。

═══════════════════════════════════════════════════════════════
  v2.21a 固化规则速查（agent 无需额外处理，模板已内置）
═══════════════════════════════════════════════════════════════

  1. 画布高度自适应 — .chart-container min-height:auto, .chart-body flex:0 1 auto
  2. 字号 ×2 — 标题68px, 正文28px, footer26px, 表格28px
  3. 水印 ×1.5 — svg width:420px, opacity:0.10, z-index:9999
  4. logo ×1.3 — .yz-logo-svg height:62px
  5. 阶段名去重 — phase_name_only() JS 函数（在 yzSelfCheck 中调用）
  6. 引号用 UTF-8 — 用 " " 不用 CSS content
  7. 通用 CSS 类 — phase-label/dumbbell-track/chart-legend 等
  8. 布局丰满 — 6块可2×3或3×2，不强制1×6
  9. 标签防重叠 — dumbbell-tag.above top:-50px, 父gap≥70px
  10. 水印穿透 — 卡片 bg 用 rgba(255,255,255,0.92)
  11. VLM 双值兼容 — data_points 可能是 [initial, current] list

═══════════════════════════════════════════════════════════════
-->
"""

def main():
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()

    # Apply CSS patches
    applied = 0
    failed = []
    for old, new, desc in CSS_PATCHES:
        if old in tpl:
            tpl = tpl.replace(old, new, 1)
            applied += 1
            print(f"  ✓ patched: {desc}")
        else:
            failed.append(desc)
            print(f"  ✗ NOT FOUND: {desc}")

    # Append SHARED_CSS before </style>
    style_end = tpl.rfind("</style>")
    if style_end > 0:
        tpl = tpl[:style_end] + SHARED_CSS + "\n" + tpl[style_end:]
        print("  ✓ appended SHARED_CSS")
    else:
        print("  ✗ </style> not found")

    # Append examples before </body> (but after the template)
    body_end = tpl.rfind("</body>")
    if body_end > 0:
        tpl = tpl[:body_end] + EXAMPLES + "\n" + tpl[body_end:]
        print("  ✓ appended EXAMPLES")
    else:
        print("  ✗ </body> not found")

    # Update the top comment to v2.21a
    tpl = tpl.replace(
        '<title>娱资信息图排版规范 v2.20</title>',
        '<title>娱资信息图排版规范 v2.21a</title>'
    )

    # Write output
    pathlib.Path(OUT).write_text(tpl, encoding="utf-8")
    sz = os.path.getsize(OUT)
    print(f"\nWrote {OUT} ({sz} bytes, {sz/1024:.0f} KB)")
    print(f"Patches applied: {applied}/{len(CSS_PATCHES)}")
    if failed:
        print(f"Failed: {failed}")

if __name__ == "__main__":
    main()
