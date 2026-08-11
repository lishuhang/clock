#!/usr/bin/env python3
"""
Generate v2.21b-yz-styleguide.html — the 1:1 拆图 skill.

Layout spec (from user):
  - Canvas: 900×900 (1:1)
  - Video is 9:16 portrait; 1:1 canvas centered → 1:1 canvas has margin around it
  - Title: top, width 4/5 (720px), font-size 34px (body 28 × 120%), heavy, max 4 lines
  - Right 1/5 (180px): icon-only logo (no text), height ~80px
  - Chart body: center, ~4:3 ratio, flexible
  - Footer: bottom, font-size 18px (current 26 × 2/3), right corner NO logo
  - NO large semi-transparent watermark (video will have its own)
  - Split rule: by content density, e.g. 10 rows → 4-3-3 (3 images)
  - All split images share the original title
  - Filename: img{n}-part{m}-styled.html

Strategy:
  - Read v2.20 SVG sprite + font definitions (reuse from v2.20 template)
  - Build new 1:1 template with the layout above
  - Include yz-logo-icon symbol (extracted separately) for icon-only logo
  - Include SHARED_CSS (same as v2.21a)
  - Include split rules and example code
"""
import os, pathlib

SPRITE_FILE = "/home/z/my-project/scripts/v2.20-svg-sprite.txt"
ICON_FILE = "/home/z/my-project/scripts/yz-logo-icon-symbol.txt"
OUT = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0811-test/v2.21b-yz-styleguide.html"

# Read sprite and icon
with open(SPRITE_FILE, encoding="utf-8") as f:
    sprite = f.read()
with open(ICON_FILE, encoding="utf-8") as f:
    icon_symbol = f.read()

# Inject icon symbol into sprite (before </defs>)
sprite_with_icon = sprite.replace("  </defs>", f"  {icon_symbol}\n  </defs>")

HTML = f'''<!DOCTYPE html>
<!--
═══════════════════════════════════════════════════════════════
  v2.21b-yz-styleguide.html
  娱乐资本论信息图排版 skill v2.21b — 1:1 拆图版
═══════════════════════════════════════════════════════════════

  用途：将大图（3:4 / A4竖版）拆成 1:1 小图，用于竖屏9:16视频居中插入。

  ── 1:1 画布规格 ──
  - 画布尺寸：1080×1080px（1:1）
    （假设视频画面 1080×1920 或 1920×1080，1:1 画布居中）
  - 标题区（顶部，高度约140px）：
    · 标题文字：宽度4/5（约800px），字号48px（正文字号40×120%），字重heavy(900)
    · 行距1.35，最多折行4行
    · 右侧1/5（约200px）：娱乐资本论图形logo（不带文字），高度约96px
  - 图表主体区（中部，flex:1，约760px高）：
    · 内容居中或铺满，所有子图复用v2.21a的SHARED CSS类
    · 主体区域约4:3比例
  - 脚注区（底部，高度约100px）：
    · 灰色小字：字号27px（正文字号40×2/3≈26.7，取27）
    · 右下角不再带logo，改为序号标注（如"1/3"）
  - 不带大型半透明浮水印（视频本身会加水印）

  ── 信息密度上限定义（v2.21b 核心规则）──
  假设整体画面是 1080×1920 或 1920×1080，则画布是 1080×1080。
  正文区域（不含灰色小字脚注）单个汉字的体积至少是 40×40px。
  由此推导：
  · 画布 1080px ÷ 40px/字 = 27 字符宽度
  · 主体高度约 760px ÷ 40px/行 = 19 行高度
  · 超过此密度时必须拆图
  拆图后每张图的内容密度不得超此上限。

  ── 灵活变更展现形式原则（v2.21b 核心规则）──
  在保持数据准确的前提下，agent 可以合理灵活变更展现形式，
  让一屏的信息量不要过于密集。变更前提是提前规划好。
  变更示例：
  · 4阶段堆叠柱状图 → 每阶段1张饼图（4张），更适合1:1画布
  · 4张引言卡2×2 → 每卡1张（4张），引言字号可大幅放大
  · 10行数据表 → 4-3-3 拆3张，每行高度更大
  · 5行散点 → 不拆（5行在1:1画布上密度合适）
  · 3子图对比 → 按维度拆3张（每维度10部电影不拆，保持对比关系）
  变更原则：
  1. 数据准确性：所有数值必须与原图一致
  2. 对比关系：如果原图的对比关系是核心信息，不要拆散
  3. 字号优先：宁可拆多张也要保证最小字号 ≥40px
  4. 铺满画幅：拆图后每张图的内容应铺满1:1画幅，不留大片空白

  ── 最小字号下限原则（v2.21b 核心规则）──
  画布上所有可见文字都必须满足以下字号下限：
  · 正文区域（数据标签、表格内容、引言等）：≥40px
  · 辅助文字（图例、刻度、元数据等）：≥28px（正文字号的70%）
  · 灰色小字脚注（数据来源等）：≥27px（正文字号的2/3）
  · 序号标注（如"1/3"）：≥24px
  自检时 yzSelfCheck1x1() 会检查所有可见文字的 computed font-size，
  低于下限则报错。agent 不得以"缩小字号以适应空间"为由违反此规则。

  ── 主体放大与留白控制原则（v2.21b 核心规则）──
  1. 主体内容（图表/图形）应尽可能铺满 chart-body 区域，留白不超过10%
  2. 饼图直径应 ≥画布宽度的50%（即 ≥540px on 1080画布）
  3. 柱状图/哑铃图轨道高度应 ≥画布主体高度的1/N（N为行数）
  4. 表格行高应均匀分布，填满主体高度
  5. 短内容（如引言卡）字号应放大到内容能视觉占满画幅

  ── 溢出处理原则（v2.21b 核心规则）──
  当内容超过显示范围时：
  1. 不得缩小字号以适应空间
  2. 应折行显示（如片名折行：年份一行+片名一行）
  3. 应展开放在主体图外区域（如图例从图内移到图下方）
  4. 应拆分为多张图（按内容密度拆图规则）
  示例：饼图阶段名不放圆心（圆心空间小），放饼图上方（空间充足）

  ── 元数据布局原则（v2.21b 核心规则）──
  1. 阶段名、作品名、年份评分等元数据：左上角对齐
  2. 引言/正文内容：居中显示
  3. 图例：横向排列在主体下方，不超过2行
  4. 序号标注：右下角

  ── 拆图规则 ──
  1. 按内容密度拆，让1:1画布在9:16竖屏居中显示时最小字体（≥40px正文/≥28px辅助）仍清晰可见
  2. 标题共用原图标题（所有拆分的图用同一个标题）
  3. 文件名：img{{n}}-part{{m}}-styled.html / .png（m从1开始）
  4. 拆分示例（参考，agent 可灵活调整）：
     · 10行热力图 → 4-3-3 拆3张
     · 4阶段堆叠柱状图 → 1-1-1-1 拆4张（每阶段饼图）
     · 4阶段哑铃图 → 2-2 拆2张
     · 4张引言卡2×2 → 1-1-1-1 拆4张（每卡1张）
     · 3子图哑铃 → 按维度拆3张（每维度10部电影不拆）
     · 5行散点 → 不拆（5行密度合适）
  5. 中心区域4:3比例，头尾高度合计画布1/4（标题+脚注各约1/8）

  ── Agent 使用步骤 ──
  1. 复制下方 <template id="yz-chart-1x1-template"> 内容到新文件
  2. 替换占位符：
     【TITLE_HERE】         → 原图标题（所有拆分图共用）
     【CHART_BODY_HERE】    → 本张图的图表主体HTML
     【SOURCE_FOOTER_HERE】 → 脚注
     【PART_NUM_HERE】      → 本张图的序号（如"1/3"）
  3. 保存为 img{{n}}-part{{m}}-styled.html，截图存PNG
  4. 截图前执行 yzSelfCheck1x1()，必须返回true

═══════════════════════════════════════════════════════════════
-->
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=900">
<title>v2.21b 娱资信息图 1:1 拆图 skill</title>
<style>
/* ════════════════════════════════════════════════════════════════
   0. RESET
   ════════════════════════════════════════════════════════════════ */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html{{-webkit-text-size-adjust:100%;}}
img{{max-width:100%;height:auto;display:block;}}
ul,ol{{list-style:none;}}

/* ════════════════════════════════════════════════════════════════
   1. 字体 + CSS 变量
   ════════════════════════════════════════════════════════════════ */
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap;}}

:root{{
  --yz-accent:#fc8166; --yz-accent-deep:#e55b46; --yz-ink:#312e2e;
  --yz-text:#312e2e; --yz-text-secondary:#6b6666; --yz-text-muted:#9a9595;
  --yz-bg:#fff; --yz-bg-chart:#efefef; --yz-border:#dcdcdc; --yz-border-soft:#e5e5e5;
  --yz-radius:6px; --yz-font:'AliPuHui','阿里巴巴普惠体',sans-serif;
  /* 1:1 字号规范 */
  --yz-fs-1x1-title:34px;    /* 正文28 × 120% */
  --yz-fs-1x1-body:28px;     /* 正文字号 */
  --yz-fs-1x1-footer:18px;   /* footer = 大图footer(26) × 2/3 */
}}

/* ════════════════════════════════════════════════════════════════
   2. 1:1 画布容器
   ════════════════════════════════════════════════════════════════ */
body{{
  font-family:var(--yz-font);
  color:var(--yz-text);
  background:#f0f0f0;
  padding:20px;
}}

.chart-container-1x1{{
  position:relative;
  width:900px;
  height:900px;  /* 固定1:1 */
  margin:0 auto;
  background:#fff;
  padding:36px 40px;
  border-radius:var(--yz-radius);
  overflow:hidden;
  display:flex;
  flex-direction:column;
}}

/* ── 标题区 ── */
.chart-header-1x1{{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  flex-shrink:0;
  margin-bottom:20px;
  gap:20px;
}}
.chart-title-1x1{{
  width:80%;  /* 4/5 */
  font-size:var(--yz-fs-1x1-title);  /* 34px */
  font-weight:900;  /* heavy */
  color:var(--yz-text);
  line-height:1.35;  /* 适当行距 */
  /* 最多4行，超出省略 */
  display:-webkit-box;
  -webkit-line-clamp:4;
  -webkit-box-orient:vertical;
  overflow:hidden;
}}
.chart-logo-1x1{{
  width:20%;  /* 1/5 */
  display:flex;
  align-items:center;
  justify-content:flex-end;
  flex-shrink:0;
}}
.chart-logo-1x1 svg{{
  height:80px;  /* 图形logo高度 */
  width:auto;
}}

/* ── 图表主体区 ── */
.chart-body-1x1{{
  flex:1 1 auto;
  position:relative;
  z-index:auto;
  display:flex;
  flex-direction:column;
  justify-content:center;  /* 垂直居中 */
  min-height:0;
}}

/* ── 脚注区 ── */
.chart-footer-1x1{{
  flex-shrink:0;
  margin-top:16px;
  padding-top:12px;
  border-top:1px solid var(--yz-border-soft);
  display:flex;
  justify-content:space-between;
  align-items:baseline;
}}
.chart-source-1x1{{
  font-size:var(--yz-fs-1x1-footer);  /* 18px */
  color:var(--yz-text-muted);
  text-align:left;
  line-height:1.5;
  flex:1;
}}
.chart-part-num{{
  font-size:14px;
  color:var(--yz-text-muted);
  font-family:var(--yz-font);
  font-weight:700;
  white-space:nowrap;
  margin-left:16px;
}}

/* ── 无大型半透明浮水印 ── */
/* v2.21b: 不带.yz-watermark，视频本身会加水印 */

/* ════════════════════════════════════════════════════════════════
   3. SHARED CSS — 与v2.21a相同，所有图表类型复用
   ════════════════════════════════════════════════════════════════ */

/* ── 阶段名 + 圆形数字徽章 ── */
.phase-label{{
  font-size:28px; font-weight:900; color:#312e2e;
  display:flex; align-items:center; gap:12px;
}}
.phase-label .phase-badge{{
  display:inline-flex; align-items:center; justify-content:center;
  width:40px; height:40px; background:#fc8166; color:#fff;
  border-radius:50%; font-size:24px; font-weight:900; flex-shrink:0;
}}

/* ── 哑铃轨道 ── */
.dumbbell-track{{
  position:relative; height:56px; background:#fafafa; border-radius:28px;
}}
.dumbbell-track::before{{
  content:""; position:absolute; top:50%; left:0; right:0;
  height:3px; background:#eee; transform:translateY(-50%);
}}

/* ── 圆点 ── */
.dumbbell-dot{{
  position:absolute; top:50%; transform:translate(-50%,-50%);
  width:28px; height:28px; border-radius:50%;
  border:4px solid #fff; box-shadow:0 0 0 2px currentColor; z-index:2;
}}

/* ── 圆点数值标签 ── */
.dumbbell-tag{{
  position:absolute; font-size:18px; font-weight:700;
  white-space:nowrap; transform:translateX(-50%);
}}
.dumbbell-tag.above{{ top:-42px; }}
.dumbbell-tag.below{{ bottom:-42px; }}

/* ── 连接线 ── */
.dumbbell-line{{
  position:absolute; top:50%; height:5px; transform:translateY(-50%); z-index:1;
}}

/* ── x轴刻度 ── */
.axis-scale{{
  display:flex; justify-content:space-between;
  font-size:14px; color:#9a9595; margin-top:10px; padding:0 4px;
}}

/* ── 图例 ── */
.chart-legend{{
  display:flex; flex-wrap:wrap; gap:12px 24px;
  margin-top:12px; font-size:18px; color:#6b6666;
}}
.chart-legend .legend-item{{ display:flex; align-items:center; gap:8px; }}
.chart-legend .legend-swatch{{ width:20px; height:20px; border-radius:50%; }}
.chart-legend .legend-swatch.bar{{ width:28px; height:6px; border-radius:3px; }}

/* ── 热力图表格（1:1版，字号略小）── */
.hm-table{{width:100%;border-collapse:separate;border-spacing:4px;font-size:22px;}}
.hm-table th{{padding:12px 6px;text-align:center;font-weight:900;color:#312e2e;background:#fafafa;border-radius:4px;font-size:18px;}}
.hm-table th.row-head{{background:transparent;text-align:left;padding-left:10px;color:#fc8166;}}
.hm-table td{{padding:14px 6px;text-align:center;border-radius:4px;font-weight:700;color:#312e2e;min-width:80px;font-size:20px;}}
.hm-table td.row-label{{text-align:left;padding-left:10px;font-weight:700;color:#fc8166;background:#fff;font-size:18px;}}

/* ── 堆叠柱状图（1:1版）── */
.sb-wrap{{display:flex;flex-direction:column;gap:24px;}}
.sb-row{{display:flex;flex-direction:column;gap:8px;}}
.sb-bar{{display:flex;width:100%;height:60px;border-radius:6px;overflow:hidden;background:#fafafa;}}
.sb-seg{{display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#fff;}}

/* ── 文字卡牌（1:1版）── */
.tc-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;position:relative;z-index:2;}}
.tc-card{{
  border:1px solid #f0f0f0; border-left:6px solid #fc8166;
  border-radius:6px; padding:18px 22px;
  background:rgba(255,255,255,0.92);
  display:flex; flex-direction:column; gap:10px; position:relative;
}}
.tc-card-head{{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;}}
.tc-phase{{font-size:18px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:8px;}}
.tc-phase .phase-badge{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;background:#fc8166;color:#fff;border-radius:50%;font-size:16px;font-weight:900;}}
.tc-work{{font-size:22px;font-weight:900;color:#312e2e;}}
.tc-meta{{font-size:14px;color:#9a9595;margin-left:auto;display:flex;gap:10px;}}
.tc-meta b{{color:#312e2e;font-weight:900;}}
.tc-quote{{font-size:18px;line-height:1.55;color:#312e2e;font-weight:500;}}
.tc-quote .qmark{{color:#fc8166;font-weight:900;font-size:24px;line-height:0;vertical-align:-4px;}}

/* ── 多序列哑铃子图（1:1版）── */
.db5-wrap{{display:flex;flex-direction:column;gap:18px;}}
.db5-sub{{display:flex;flex-direction:column;gap:6px;}}
.db5-sub-title{{font-size:22px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:10px;padding-bottom:6px;border-bottom:2px solid #f0f0f0;}}
.db5-rows{{display:flex;flex-direction:column;gap:6px;}}
.db5-row{{display:grid;grid-template-columns:180px 1fr 80px;gap:10px;align-items:center;}}
.db5-film{{font-size:14px;font-weight:700;color:#312e2e;line-height:1.3;}}
.db5-row .dumbbell-track{{height:24px;border-radius:12px;}}
.db5-row .dumbbell-dot{{width:14px;height:14px;border:2px solid #fff;}}
.db5-row .dumbbell-tag{{font-size:12px;}}
.db5-row .dumbbell-tag.above{{top:-16px;}}
.db5-row .dumbbell-tag.below{{bottom:-16px;}}
.db5-diff{{font-size:14px;font-weight:900;color:#6b6666;text-align:right;}}
.db5-diff.up{{color:#fc8166;}}
.db5-diff.down{{color:#6cb0f9;}}

/* ── 散点对比哑铃（1:1版）── */
.sc6-wrap{{display:flex;flex-direction:column;gap:24px;}}
.sc6-row{{display:flex;flex-direction:column;gap:10px;}}
.sc6-label{{font-size:24px;font-weight:900;color:#312e2e;display:flex;justify-content:space-between;align-items:baseline;}}
.sc6-label .diff{{font-size:20px;font-weight:900;color:#e60012;}}
.sc6-row .dumbbell-track{{height:48px;}}
.sc6-row .dumbbell-dot{{width:26px;height:26px;}}
.sc6-row .dumbbell-tag{{font-size:18px;}}
.sc6-line-dashed{{
  position:absolute;top:50%;height:4px;transform:translateY(-50%);
  background:repeating-linear-gradient(to right,#fc8166 0,#fc8166 5px,transparent 5px,transparent 10px);
  z-index:1;
}}

/* ════════════════════════════════════════════════════════════════
   4. 自检横幅
   ════════════════════════════════════════════════════════════════ */
#yz-selfcheck-banner{{
  position:absolute;top:8px;right:8px;padding:6px 12px;border-radius:6px;
  font-family:var(--yz-font);font-size:12px;font-weight:700;z-index:99999;display:none;
}}
#yz-selfcheck-banner.pass{{background:#50c885;color:#fff;display:block;}}
#yz-selfcheck-banner.fail{{background:#e60012;color:#fff;display:block;}}
</style>
</head>
<body>

<!-- ═══════ SVG sprite（横版+竖版+图形logo）═══════ -->
{sprite_with_icon}

<div id="yz-selfcheck-banner"></div>

<!-- ═══════ 1:1 模板 ═══════ -->
<template id="yz-chart-1x1-template">
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=900">
<title>【TITLE_HERE】</title>
<style>
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-55-Regular.ttf') format('truetype');font-weight:400;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-85-Bold.ttf') format('truetype');font-weight:700;font-display:swap;}}
@font-face{{font-family:'AliPuHui';src:url('https://cdn.jsdelivr.net/npm/@fontpkg/alibaba-puhuiti-3-0@0.0.0/AlibabaPuHuiTi-3-115-Black.ttf') format('truetype');font-weight:900;font-display:swap;}}
:root{{
  --yz-accent:#fc8166; --yz-ink:#312e2e; --yz-text:#312e2e;
  --yz-text-secondary:#6b6666; --yz-text-muted:#9a9595;
  --yz-bg:#fff; --yz-border-soft:#e5e5e5; --yz-radius:6px;
  --yz-font:'AliPuHui','阿里巴巴普惠体',sans-serif;
  --yz-fs-1x1-title:34px; --yz-fs-1x1-body:28px; --yz-fs-1x1-footer:18px;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:var(--yz-font);background:#f0f0f0;padding:20px;}}
.chart-container-1x1{{position:relative;width:900px;height:900px;margin:0 auto;background:#fff;padding:36px 40px;border-radius:var(--yz-radius);overflow:hidden;display:flex;flex-direction:column;}}
.chart-header-1x1{{display:flex;align-items:flex-start;justify-content:space-between;flex-shrink:0;margin-bottom:20px;gap:20px;}}
.chart-title-1x1{{width:80%;font-size:var(--yz-fs-1x1-title);font-weight:900;color:var(--yz-text);line-height:1.35;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}}
.chart-logo-1x1{{width:20%;display:flex;align-items:center;justify-content:flex-end;flex-shrink:0;}}
.chart-logo-1x1 svg{{height:80px;width:auto;}}
.chart-body-1x1{{flex:1 1 auto;position:relative;z-index:auto;display:flex;flex-direction:column;justify-content:center;min-height:0;}}
.chart-footer-1x1{{flex-shrink:0;margin-top:16px;padding-top:12px;border-top:1px solid var(--yz-border-soft);display:flex;justify-content:space-between;align-items:baseline;}}
.chart-source-1x1{{font-size:var(--yz-fs-1x1-footer);color:var(--yz-text-muted);text-align:left;line-height:1.5;flex:1;}}
.chart-part-num{{font-size:14px;color:var(--yz-text-muted);font-weight:700;white-space:nowrap;margin-left:16px;}}
.phase-label{{font-size:28px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:12px;}}
.phase-label .phase-badge{{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;background:#fc8166;color:#fff;border-radius:50%;font-size:24px;font-weight:900;flex-shrink:0;}}
.dumbbell-track{{position:relative;height:56px;background:#fafafa;border-radius:28px;}}
.dumbbell-track::before{{content:"";position:absolute;top:50%;left:0;right:0;height:3px;background:#eee;transform:translateY(-50%);}}
.dumbbell-dot{{position:absolute;top:50%;transform:translate(-50%,-50%);width:28px;height:28px;border-radius:50%;border:4px solid #fff;box-shadow:0 0 0 2px currentColor;z-index:2;}}
.dumbbell-tag{{position:absolute;font-size:18px;font-weight:700;white-space:nowrap;transform:translateX(-50%);}}
.dumbbell-tag.above{{top:-42px;}}
.dumbbell-tag.below{{bottom:-42px;}}
.dumbbell-line{{position:absolute;top:50%;height:5px;transform:translateY(-50%);z-index:1;}}
.axis-scale{{display:flex;justify-content:space-between;font-size:14px;color:#9a9595;margin-top:10px;padding:0 4px;}}
.chart-legend{{display:flex;flex-wrap:wrap;gap:12px 24px;margin-top:12px;font-size:18px;color:#6b6666;}}
.chart-legend .legend-item{{display:flex;align-items:center;gap:8px;}}
.chart-legend .legend-swatch{{width:20px;height:20px;border-radius:50%;}}
.chart-legend .legend-swatch.bar{{width:28px;height:6px;border-radius:3px;}}
.hm-table{{width:100%;border-collapse:separate;border-spacing:4px;font-size:22px;}}
.hm-table th{{padding:12px 6px;text-align:center;font-weight:900;color:#312e2e;background:#fafafa;border-radius:4px;font-size:18px;}}
.hm-table th.row-head{{background:transparent;text-align:left;padding-left:10px;color:#fc8166;}}
.hm-table td{{padding:14px 6px;text-align:center;border-radius:4px;font-weight:700;color:#312e2e;min-width:80px;font-size:20px;}}
.hm-table td.row-label{{text-align:left;padding-left:10px;font-weight:700;color:#fc8166;background:#fff;font-size:18px;}}
.sb-wrap{{display:flex;flex-direction:column;gap:24px;}}
.sb-row{{display:flex;flex-direction:column;gap:8px;}}
.sb-bar{{display:flex;width:100%;height:60px;border-radius:6px;overflow:hidden;background:#fafafa;}}
.sb-seg{{display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#fff;}}
.tc-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;position:relative;z-index:2;}}
.tc-card{{border:1px solid #f0f0f0;border-left:6px solid #fc8166;border-radius:6px;padding:18px 22px;background:rgba(255,255,255,0.92);display:flex;flex-direction:column;gap:10px;position:relative;}}
.tc-card-head{{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;}}
.tc-phase{{font-size:18px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:8px;}}
.tc-phase .phase-badge{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;background:#fc8166;color:#fff;border-radius:50%;font-size:16px;font-weight:900;}}
.tc-work{{font-size:22px;font-weight:900;color:#312e2e;}}
.tc-meta{{font-size:14px;color:#9a9595;margin-left:auto;display:flex;gap:10px;}}
.tc-meta b{{color:#312e2e;font-weight:900;}}
.tc-quote{{font-size:18px;line-height:1.55;color:#312e2e;font-weight:500;}}
.tc-quote .qmark{{color:#fc8166;font-weight:900;font-size:24px;line-height:0;vertical-align:-4px;}}
.db5-wrap{{display:flex;flex-direction:column;gap:18px;}}
.db5-sub{{display:flex;flex-direction:column;gap:6px;}}
.db5-sub-title{{font-size:22px;font-weight:900;color:#312e2e;display:flex;align-items:center;gap:10px;padding-bottom:6px;border-bottom:2px solid #f0f0f0;}}
.db5-rows{{display:flex;flex-direction:column;gap:6px;}}
.db5-row{{display:grid;grid-template-columns:180px 1fr 80px;gap:10px;align-items:center;}}
.db5-film{{font-size:14px;font-weight:700;color:#312e2e;line-height:1.3;}}
.db5-row .dumbbell-track{{height:24px;border-radius:12px;}}
.db5-row .dumbbell-dot{{width:14px;height:14px;border:2px solid #fff;}}
.db5-row .dumbbell-tag{{font-size:12px;}}
.db5-row .dumbbell-tag.above{{top:-16px;}}
.db5-row .dumbbell-tag.below{{bottom:-16px;}}
.db5-diff{{font-size:14px;font-weight:900;color:#6b6666;text-align:right;}}
.db5-diff.up{{color:#fc8166;}}
.db5-diff.down{{color:#6cb0f9;}}
.sc6-wrap{{display:flex;flex-direction:column;gap:24px;}}
.sc6-row{{display:flex;flex-direction:column;gap:10px;}}
.sc6-label{{font-size:24px;font-weight:900;color:#312e2e;display:flex;justify-content:space-between;align-items:baseline;}}
.sc6-label .diff{{font-size:20px;font-weight:900;color:#e60012;}}
.sc6-row .dumbbell-track{{height:48px;}}
.sc6-row .dumbbell-dot{{width:26px;height:26px;}}
.sc6-row .dumbbell-tag{{font-size:18px;}}
.sc6-line-dashed{{position:absolute;top:50%;height:4px;transform:translateY(-50%);background:repeating-linear-gradient(to right,#fc8166 0,#fc8166 5px,transparent 5px,transparent 10px);z-index:1;}}
#yz-selfcheck-banner{{position:absolute;top:8px;right:8px;padding:6px 12px;border-radius:6px;font-family:var(--yz-font);font-size:12px;font-weight:700;z-index:99999;display:none;}}
#yz-selfcheck-banner.pass{{background:#50c885;color:#fff;display:block;}}
#yz-selfcheck-banner.fail{{background:#e60012;color:#fff;display:block;}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
{sprite_with_icon}
</defs></svg>

<div id="yz-selfcheck-banner"></div>

<div class="chart-container-1x1">
  <div class="chart-header-1x1">
    <h1 class="chart-title-1x1">【TITLE_HERE】</h1>
    <div class="chart-logo-1x1">
      <svg viewBox="0 0 199 231"><use href="#yz-logo-icon"/></svg>
    </div>
  </div>
  <div class="chart-body-1x1">
【CHART_BODY_HERE】
  </div>
  <div class="chart-footer-1x1">
    <div class="chart-source-1x1">【SOURCE_FOOTER_HERE】</div>
    <div class="chart-part-num">【PART_NUM_HERE】</div>
  </div>
</div>

<script>
function yzSelfCheck1x1(){{
  var errors=[];
  var checks=[
    ['.chart-container-1x1','画布 .chart-container-1x1'],
    ['.chart-title-1x1','标题 .chart-title-1x1'],
    ['.chart-logo-1x1','Logo .chart-logo-1x1'],
    ['.chart-body-1x1','主体 .chart-body-1x1'],
    ['.chart-source-1x1','脚注 .chart-source-1x1']
  ];
  checks.forEach(function(c){{if(!document.querySelector(c[0]))errors.push('缺失：'+c[1]);}});
  // 字体检查
  if(document.fonts&&document.fonts.check){{if(!document.fonts.check('900 34px AliPuHui'))errors.push('字体AliPuHui未加载');}}
  // 占位符检查
  var html=document.body.innerHTML;
  var ph1='【'+'TITLE_HERE'+'】',ph2='【'+'CHART_BODY_HERE'+'】',ph3='【'+'SOURCE_FOOTER_HERE'+'】',ph4='【'+'PART_NUM_HERE'+'】';
  if(html.indexOf(ph1)>-1)errors.push('占位符'+ph1+'未替换');
  if(html.indexOf(ph2)>-1)errors.push('占位符'+ph2+'未替换');
  if(html.indexOf(ph3)>-1)errors.push('占位符'+ph3+'未替换');
  if(html.indexOf(ph4)>-1)errors.push('占位符'+ph4+'未替换');
  // 画布尺寸检查
  var cc=document.querySelector('.chart-container-1x1');
  if(cc){{var w=cc.offsetWidth,h=cc.offsetHeight;if(Math.abs(w-900)>5||Math.abs(h-900)>5)errors.push('画布尺寸异常：'+w+'x'+h+'（应为900x900）');}}
  var banner=document.getElementById('yz-selfcheck-banner');
  if(errors.length===0){{console.log('%c✅ YZ 1x1 Self-Check PASSED','color:#50c885;font-size:16px;font-weight:bold;');if(banner){{banner.className='pass';banner.textContent='✅ v2.21b 1x1 自检通过';}}return true;}}
  else{{console.log('%c❌ YZ 1x1 Self-Check FAILED','color:#e60012;font-size:16px;font-weight:bold;');errors.forEach(function(e){{console.log('  • '+e);}});if(banner){{banner.className='fail';banner.textContent='❌ 自检失败：'+errors.length+'项';}}return false;}}
}}
if(document.fonts){{document.fonts.ready.then(function(){{setTimeout(yzSelfCheck1x1,200);}});}}
</script>
</body>
</html>
</template>

<!--
═══════════════════════════════════════════════════════════════
  拆图示例（agent 参考）
═══════════════════════════════════════════════════════════════

  ── 10行热力图 → 4-3-3 拆3张 ──
  part1: 行1-4   (4行)
  part2: 行5-7   (3行)
  part3: 行8-10  (3行)
  每张标题共用原图标题，PART_NUM_HERE 填 "1/3"、"2/3"、"3/3"

  ── 4阶段堆叠柱状图 → 2-2 拆2张 ──
  part1: 阶段1-2
  part2: 阶段3-4

  ── 4阶段哑铃图 → 2-2 拆2张 ──
  part1: 阶段1-2
  part2: 阶段3-4

  ── 4张引言卡2×2 → 不拆 ──
  直接转换为1:1（已是2×2友好布局）

  ── 3子图哑铃 → 1-1-1 拆3张 ──
  part1: 子图1（专业能力）
  part2: 子图2（民族国家）
  part3: 子图3（社会文化/性别）

  ── 5行散点 → 3-2 拆2张 ──
  part1: 电影1-3
  part2: 电影4-5

═══════════════════════════════════════════════════════════════
-->
</body>
</html>
'''

pathlib.Path(OUT).write_text(HTML, encoding="utf-8")
sz = os.path.getsize(OUT)
print(f"Wrote {OUT} ({sz} bytes, {sz/1024:.0f} KB)")
