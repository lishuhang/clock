"""
vidsync cover image processor
==============================
从主封面派生各平台所需规格。

输入：
- horizontal_cover (16:9) - 主横屏封面
- vertical_cover (1080×1260) - 主竖屏封面（视频号规格）

派生规格（从左上角对齐裁剪）：
- B站: 1146×717 (16:9 landscape)
- 抖音: 1080×1440 (3:4 vertical)
- 小红书: 1080×1440 (3:4 vertical)
- 快手: 1080×1920 (9:16 vertical)
- 视频号: 1080×1260 (6:7 vertical, 原始即用)
- 百家号: 1280×720 (16:9 landscape)
- 企鹅号: 1280×720 (16:9 landscape)
- 腾讯视频: 1280×720 (16:9 landscape)
- 微博: 1080×1920 (9:16 vertical) 或 1920×1080
- 虎嗅: 800×450 (16:9 landscape)
- 36氪: 1280×720 (16:9 landscape)
- 喜马拉雅: 1400×1400 (square, album cover)
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


# 各平台封面规格
COVER_SPECS = {
    "bilibili":      {"size": (1146, 717),   "ratio": "16:9",  "orient": "landscape"},
    "douyin":        {"size": (1080, 1440),  "ratio": "3:4",   "orient": "vertical"},
    "xiaohongshu":   {"size": (1080, 1440),  "ratio": "3:4",   "orient": "vertical"},
    "kuaishou":      {"size": (1080, 1920),  "ratio": "9:16",  "orient": "vertical"},
    "wechat_channels": {"size": (1080, 1260), "ratio": "6:7",  "orient": "vertical"},
    "baijiahao":     {"size": (1280, 720),   "ratio": "16:9",  "orient": "landscape"},
    "qq_shizi":      {"size": (1280, 720),   "ratio": "16:9",  "orient": "landscape"},
    "tencent_video": {"size": (1280, 720),   "ratio": "16:9",  "orient": "landscape"},
    "weibo":         {"size": (1080, 1920),  "ratio": "9:16",  "orient": "vertical"},
    "huxiu":         {"size": (800, 450),    "ratio": "16:9",  "orient": "landscape"},
    "kr36":          {"size": (1280, 720),   "ratio": "16:9",  "orient": "landscape"},
    "ximalaya":      {"size": (1400, 1400),  "ratio": "1:1",   "orient": "square"},
}


def crop_top_left(src_path: str, dst_path: str, target_w: int, target_h: int) -> str:
    """
    从左上角对齐裁剪到目标尺寸（不拉伸，直接裁剪）。
    如果源图比目标小，会先放大到至少目标尺寸再裁剪。
    """
    with Image.open(src_path) as img:
        # 转换为 RGB（避免 mode 问题）
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        src_w, src_h = img.size
        # 如果源图比目标小，按比例放大到刚好覆盖目标
        if src_w < target_w or src_h < target_h:
            scale = max(target_w / src_w, target_h / src_h)
            new_w = int(src_w * scale)
            new_h = int(src_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            logger.info("upscaled %s from (%d,%d) to (%d,%d)",
                        Path(src_path).name, src_w, src_h, new_w, new_h)

        # 从左上角裁剪
        left = 0
        top = 0
        right = min(target_w, img.width)
        bottom = min(target_h, img.height)
        cropped = img.crop((left, top, right, bottom))

        # 如果裁剪后还不到目标尺寸（理论上不会），补黑边
        if cropped.size != (target_w, target_h):
            final = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            final.paste(cropped, (0, 0))
            cropped = final

        Path(dst_path).parent.mkdir(parents=True, exist_ok=True)
        cropped.save(dst_path, "PNG", quality=95)
        logger.info("cover saved: %s (%dx%d)", Path(dst_path).name, target_w, target_h)
        return dst_path


def derive_all_covers(horizontal_path: str | None, vertical_path: str | None,
                       out_dir: str | Path) -> dict[str, str]:
    """
    从主横屏和主竖屏封面，派生所有平台的封面。

    Args:
        horizontal_path: 横屏封面路径（16:9），可为 None
        vertical_path: 竖屏封面路径（1080×1260 或 9:16），可为 None
        out_dir: 输出目录

    Returns:
        {platform_id: cover_path}
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, str] = {}
    for platform_id, spec in COVER_SPECS.items():
        try:
            # 决定源图：横屏规格用横屏源，竖屏/方形用竖屏源
            if spec["orient"] == "landscape":
                src = horizontal_path
            elif spec["orient"] == "vertical":
                src = vertical_path or horizontal_path  # 竖屏源缺失时用横屏裁剪
            else:  # square
                src = vertical_path or horizontal_path

            if not src:
                logger.warning("[%s] no source cover available (need %s)",
                               platform_id, spec["orient"])
                continue

            dst = out_dir / f"{platform_id}_cover.png"
            crop_top_left(src, str(dst), spec["size"][0], spec["size"][1])
            result[platform_id] = str(dst)
        except Exception as e:
            logger.error("[%s] cover derivation failed: %s", platform_id, e)

    return result


if __name__ == "__main__":
    # 自测：假设有 master 横屏封面
    import sys
    if len(sys.argv) >= 3:
        h, v = sys.argv[1], sys.argv[2]
        out = sys.argv[3] if len(sys.argv) > 3 else "/tmp/vidsync_covers"
        r = derive_all_covers(h, v, out)
        print(f"Generated {len(r)} covers:")
        for pid, path in r.items():
            print(f"  {pid}: {path}")
    else:
        print("Usage: python cover.py <horizontal_path> <vertical_path> [out_dir]")
