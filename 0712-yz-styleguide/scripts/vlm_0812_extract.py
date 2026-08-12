#!/usr/bin/env python3
"""VLM extract data from 0812-test images. Sequential with 8s cooldown."""
import os, subprocess, json, time

IMAGES_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/images"
OUT_DIR = "/home/z/my-project/workspace-clock/0712-yz-styleguide/0812-test/_vlm"
os.makedirs(OUT_DIR, exist_ok=True)

# Only analyze chart images (skip title image 0, separators 1/5/9, QR 13)
TARGETS = [2, 3, 4, 6, 7, 8, 10, 11, 12]

PROMPT = """你是一个数据可视化逆向工程专家。下面给你一张娱乐资本论（微信公众号）文章里的信息图。

请严格按以下结构输出**纯 JSON**（不要 markdown 围栏，不要解释文字），键如下：

{
  "image_summary": "用一句话概括这张图传达的核心信息",
  "chart_type": "图表类型，例如：横向柱状图 / 堆叠柱状图 / 折线图 / 数据表格 / 时间轴 / 多面板对比 / 雷达图 / 散点图 / 文字卡牌 / 双轴图 / 饼图 / 环形图 / 面积图 / 树图 / 气泡图",
  "title_text": "图中显示的完整标题文字",
  "footer_text": "图脚注文字（数据来源、说明等）",
  "axes": {
    "x_label": "x轴标签",
    "y_label": "y轴标签",
    "x_categories": ["x轴类目"],
    "y_range_or_categories": ["y轴类目或范围"]
  },
  "series": [
    {"name": "序列名", "color": "颜色描述", "data_points": [["类目","数值"]], "meaning": "含义"}
  ],
  "table_data": {
    "headers": ["列名"],
    "rows": [["单元格"]]
  },
  "color_encoding": [{"color": "颜色", "meaning": "含义"}],
  "visualization_spec": "详细可视化还原说明(≥200字)：画布比例、布局、色彩深浅含义、柱条/折线/标记点含义、字号字重、装饰元素等",
  "key_data_highlights": ["关键数据点"],
  "data_source_text": "数据来源文字"
}

要求：
1. 表格数据必须完整还原图中所有可见单元格
2. 颜色尽量识别hex值（橙色#fc8166是娱资主色）
3. visualization_spec 至少200字
4. 输出纯 JSON
"""

def call_vlm(img_path, out_path):
    cmd = ["z-ai", "vision", "-p", PROMPT, "-i", img_path, "-o", out_path]
    for attempt in range(4):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return True
            if "429" in (r.stderr or ""):
                wait = 30 * (attempt + 1)
                print(f"    429, wait {wait}s")
                time.sleep(wait)
                continue
            time.sleep(10)
        except subprocess.TimeoutExpired:
            time.sleep(20)
    return False

for idx in TARGETS:
    # Find the image file
    candidates = [f for f in os.listdir(IMAGES_DIR) if f.startswith(f"img{idx}.")]
    if not candidates:
        print(f"[{idx}] no file")
        continue
    img_name = candidates[0]
    img_path = os.path.join(IMAGES_DIR, img_name)
    out_path = os.path.join(OUT_DIR, f"img{idx}.json")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"[{idx}] exists, skip")
        continue
    print(f"[{idx}] {img_name}...")
    ok = call_vlm(img_path, out_path)
    print(f"  {'OK' if ok else 'FAIL'}")
    time.sleep(8)

print("\n=== Done ===")
for idx in TARGETS:
    out_path = os.path.join(OUT_DIR, f"img{idx}.json")
    sz = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"  img{idx}: {sz} bytes")
