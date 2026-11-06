#!/usr/bin/env python3
"""logo 白底→透明 + 自动裁切到字形 + 方形画布居中。
处理 assets/logos 下所有不透明白底 logo（xiaoyunque_w 已是透明版，跳过）。
"""
import os

import numpy as np
from PIL import Image

LOGOS = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/assets/logos"


def process(f):
    path = f"{LOGOS}/{f}"
    im = Image.open(path).convert("RGBA")
    a = np.array(im).astype(float)
    r, g, b, alpha = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    # 距白色的欧氏距离
    d = np.sqrt((255 - r) ** 2 + (255 - g) ** 2 + (255 - b) ** 2)
    # 新 alpha：纯白→透明(d<8)，d>=30 全不透明，中间线性过渡；原透明处保持
    new_alpha = np.clip((d - 8) * (255 / 22.0), 0, 255)
    keep = alpha > 0
    out_alpha = np.where(keep, np.maximum(alpha * (new_alpha / 255.0), np.where(keep, new_alpha, 0)), 0)
    out_alpha = np.where(keep, new_alpha, 0)
    out = np.dstack([r, g, b, out_alpha]).astype(np.uint8)
    # 自动裁切到内容
    ys, xs = np.where(out[..., 3] > 24)
    if len(xs) < 20:
        print(f"  {f}: 无可辨内容，跳过")
        return
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = 12
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(out.shape[1] - 1, x1 + pad), min(out.shape[0] - 1, y1 + pad)
    crop = out[y0:y1 + 1, x0:x1 + 1]
    # 方形画布居中（保持宽高比）
    h, w = crop.shape[:2]
    side = int(max(h, w) * 1.12)
    canvas = np.zeros((side, side, 4), dtype=np.uint8)
    oy, ox = (side - h) // 2, (side - w) // 2
    canvas[oy:oy + h, ox:ox + w] = crop
    Image.fromarray(canvas, "RGBA").save(path)
    print(f"  {f}: 字形区 {w}x{h} → {side}x{side} 透明版")


if __name__ == "__main__":
    for f in sorted(os.listdir(LOGOS)):
        if f.endswith(".png") and f != "xiaoyunque_w.png":
            process(f)
