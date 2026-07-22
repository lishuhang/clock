#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr-v2.py  —  离线 OCR + 二维码识别 (修复版)

修复内容:
1. 修复原 ocr.py 的致命 bug: 把原始路径字符串传给 EasyOCR.readtext(),
   导致 EasyOCR 内部 cv2.imread() 在含空格/中文路径上返回 None,
   进而触发 "'NoneType' object has no attribute 'shape'" 错误。
   修复: 统一用 cv2.imdecode(np.fromfile(...)) 读图, 把 numpy 数组
   直接传给 OCR 引擎, 绕开各引擎内部的 imread 调用。

2. 多引擎自动回退 (均为离线, 不依赖任何大模型 API):
     优先级 1: rapidocr_onnxruntime  (轻量, 中文优秀, ~3s/张)
     优先级 2: easyocr               (原引擎, 已修复路径 bug)
     优先级 3: pytesseract           (需 chi_sim 语言包)
   启动时自动探测可用引擎, 任一可用即可工作。

3. 二维码识别沿用原 sliding-window + zxing-cpp/OpenCV 方案 (此部分原本正常)。

4. 新增断点续扫: 批量模式下若输出文件已存在, 已成功处理 (且 OCR 非错误)
   的图片会被跳过, 避免崩溃重跑。

用法:
    python ocr-v2.py              # 批量模式: 处理当前目录所有图片
    python ocr-v2.py <图片路径>    # 单文件模式
    python ocr-v2.py --force      # 批量模式, 忽略已有结果, 全部重跑
"""

import sys
import os
import re
import time
import warnings
import datetime
import numpy as np
import cv2

# ---------------------------------------------------------------------------
# 二维码引擎: zxing-cpp (强) 优先, 否则退回 OpenCV (弱)
# ---------------------------------------------------------------------------
try:
    import zxingcpp
    HAS_ZXING = True
except ImportError:
    HAS_ZXING = False

warnings.filterwarnings("ignore", category=UserWarning)

VALID_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')


# ===========================================================================
# OCR 引擎封装层 — 统一接口 ocr_engine.recognize(cv_img) -> (text, err)
# ===========================================================================

class RapidOCREngine:
    """优先引擎: 轻量, 中文优秀, 基于 ONNX, 完全离线"""
    name = "RapidOCR (ONNXRuntime)"

    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self._ocr = RapidOCR()

    def recognize(self, cv_img):
        try:
            result, _ = self._ocr(cv_img)
            if not result:
                return "[未检测到明显文字]", None
            # result: list of [box, text, conf]
            lines = [item[1] for item in result if item and item[1]]
            return "\n".join(lines) if lines else "[未检测到明显文字]", None
        except Exception as e:
            return "", f"RapidOCR 错误: {e}"


class EasyOCREngine:
    """备用引擎 1: 原脚本使用的引擎, 已修复路径 bug"""
    name = "EasyOCR"

    def __init__(self):
        import easyocr
        # ch_sim + en; gpu=False 保证离线 & 通用
        self._reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

    def recognize(self, cv_img):
        try:
            # ★关键修复: 传 numpy 数组而非路径, 避免内部 cv2.imread 在
            # 含空格/中文路径上返回 None 导致 .shape 崩溃
            result = self._reader.readtext(cv_img, detail=0)
            if result:
                return "\n".join(result), None
            return "[未检测到明显文字]", None
        except Exception as e:
            return "", f"EasyOCR 错误: {e}"


class TesseractEngine:
    """备用引擎 2: pytesseract (需安装 chi_sim 语言包)"""
    name = "Tesseract"

    def __init__(self):
        import pytesseract
        self._pytesseract = pytesseract
        # 探测可用语言
        langs = self._pytesseract.get_languages()
        candidates = []
        for lang in ('chi_sim+eng', 'chi_sim', 'eng'):
            # 拆开逐个验证, 因为 get_languages 可能不返回组合
            if all(part in langs for part in lang.split('+')):
                candidates.append(lang)
                break
        if not candidates:
            raise RuntimeError("Tesseract 未安装中文语言包 (chi_sim)")
        self._lang = candidates[0]

    def recognize(self, cv_img):
        try:
            text = self._pytesseract.image_to_string(cv_img, lang=self._lang)
            text = text.strip()
            return (text if text else "[未检测到明显文字]"), None
        except Exception as e:
            return "", f"Tesseract 错误: {e}"


def init_ocr_engine():
    """按优先级尝试初始化, 返回第一个可用的引擎实例"""
    for cls in (RapidOCREngine, EasyOCREngine, TesseractEngine):
        try:
            eng = cls()
            print(f"[OCR 引擎] 使用 {eng.name}")
            return eng
        except Exception as e:
            print(f"[OCR 引擎] {cls.__name__} 不可用: {e}")
    print("[OCR 引擎] 严重: 没有可用的离线 OCR 引擎。")
    print("           建议安装: pip install rapidocr-onnxruntime")
    print("                   或: pip install easyocr")
    print("                   或: apt install tesseract-ocr-chi-sim + pip install pytesseract")
    return None


# ===========================================================================
# 二维码识别 (沿用原 sliding-window 方案)
# ===========================================================================

def scan_chunk_with_zxing(img_chunk):
    results = set()
    try:
        barcodes = zxingcpp.read_barcodes(img_chunk)
        for b in barcodes:
            if b.text:
                results.add(b.text)
    except Exception:
        pass
    return results


def scan_chunk_with_opencv(img_chunk, detector):
    results = set()
    try:
        retval, decoded_info, _, _ = detector.detectAndDecodeMulti(img_chunk)
        if retval:
            for info in decoded_info:
                if info and info.strip():
                    results.add(info)
    except Exception:
        pass
    return results


def detect_qr_sliding_window(cv_img):
    """滑动窗口全图扫描, 解决长图中间二维码漏扫问题"""
    h, w = cv_img.shape[:2]
    found = set()

    if HAS_ZXING:
        found.update(scan_chunk_with_zxing(cv_img))
    else:
        det = cv2.QRCodeDetector()
        found.update(scan_chunk_with_opencv(cv_img, det))

    # 窗口高度 = 宽度 × 1.2 (最小 600), 70% 重叠
    window_h = max(600, int(w * 1.2))
    if window_h > h:
        window_h = h
    step = int(window_h * 0.7)

    if h > window_h:
        det = None if HAS_ZXING else cv2.QRCodeDetector()
        for y in range(0, h, step):
            end_y = min(y + window_h, h)
            chunk = cv_img[y:end_y, :]
            if HAS_ZXING:
                found.update(scan_chunk_with_zxing(chunk))
            else:
                found.update(scan_chunk_with_opencv(chunk, det))
            if end_y == h:
                break
    return list(found)


# ===========================================================================
# 主处理流程
# ===========================================================================

def load_image(image_path):
    """用 cv2.imdecode + np.fromfile 读取图片, 支持中文/空格路径"""
    return cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)


def analyze_image(image_path, ocr_engine):
    if not os.path.exists(image_path):
        return f"错误: 找不到文件 '{image_path}'", [], None

    t0 = time.time()
    cv_img = load_image(image_path)
    if cv_img is None:
        return "[错误: 无法读取图片]", [], None

    # 1. 二维码识别
    qr_results = detect_qr_sliding_window(cv_img)
    if not qr_results and not HAS_ZXING:
        print("  [提示] 未检测到二维码。建议 pip install zxing-cpp 提升识别率。")

    # 2. OCR 识别 — 传 numpy 数组, 不传路径
    ocr_text, err = ocr_engine.recognize(cv_img)
    if err:
        ocr_text = f"[OCR 处理错误: {err}]"

    elapsed = time.time() - t0
    return ocr_text, qr_results, elapsed


def format_output(ocr_text, qr_results):
    lines = [
        "========== OCR 文字识别内容 ==========",
        ocr_text,
        "",
        f"========== 二维码识别内容 (共 {len(qr_results)} 个) ==========",
    ]
    if qr_results:
        for i, c in enumerate(qr_results, 1):
            lines.append(f"[{i}] {c}")
    else:
        lines.append("[未检测到二维码]")
    return "\n".join(lines)


# ===========================================================================
# 批量模式: 断点续扫
# ===========================================================================

def parse_existing_results(output_path):
    """
    解析已有输出文件, 返回 {filename: True} 表示该文件 OCR 结果非错误
    (用于断点续扫判断是否跳过)。
    """
    done = set()
    if not os.path.exists(output_path):
        return done
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return done

    # 用文件名分隔块
    pattern = re.compile(r"^文件名:\s*(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(content))
    for i, m in enumerate(matches):
        fname = m.group(1).strip()
        # 取该文件名到下一个文件名之间的内容
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        block = content[start:end]
        # 必须包含 OCR 段且不含错误标记才算完成
        if "OCR 文字识别内容" in block and "OCR 处理错误" not in block:
            done.add(fname)
    return done


# ===========================================================================
# 主入口
# ===========================================================================

def main():
    print(f"ocr-v2 启动 @ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"二维码引擎: {'zxing-cpp (强)' if HAS_ZXING else 'OpenCV (弱, 建议 pip install zxing-cpp)'}")

    ocr_engine = init_ocr_engine()
    if ocr_engine is None:
        sys.exit(1)

    force = '--force' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--force']

    if not args:
        # ---------- 批量模式 ----------
        current_dir = os.getcwd()
        files = sorted(f for f in os.listdir(current_dir)
                       if f.lower().endswith(VALID_EXTENSIONS))
        if not files:
            print("当前目录未找到图片。")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        output_filename = f"{timestamp}-ocr.txt"

        # 断点续扫: 查找同目录已存在的 *-ocr.txt (取最新一个)
        existing_outputs = sorted(
            f for f in os.listdir(current_dir) if f.endswith("-ocr.txt")
        )
        resume_from = None
        if existing_outputs and not force:
            resume_from = os.path.join(current_dir, existing_outputs[-1])
            done = parse_existing_results(resume_from)
            skipped = sum(1 for f in files if f in done)
            if skipped > 0:
                print(f"[断点续扫] 检测到 {resume_from}")
                print(f"           已完成 {skipped}/{len(files)} 张, 将追加未完成项。")
            else:
                resume_from = None  # 没有可续扫的, 走全新流程

        if resume_from:
            output_path = resume_from
            mode = "a"
        else:
            output_path = os.path.join(current_dir, output_filename)
            mode = "w"

        print(f"发现 {len(files)} 张图片, 输出: {output_path}")
        print("-" * 60)

        done = parse_existing_results(output_path) if mode == "a" else set()
        total_t0 = time.time()
        processed = 0

        with open(output_path, mode, encoding="utf-8") as f:
            for idx, filename in enumerate(files, 1):
                if filename in done and not force:
                    print(f"[{idx}/{len(files)}] 跳过(已完成): {filename}")
                    continue

                print(f"[{idx}/{len(files)}] 处理: {filename} ...", end=" ", flush=True)
                ocr_text, qr_results, elapsed = analyze_image(
                    os.path.join(current_dir, filename), ocr_engine
                )
                processed += 1
                t_str = f"{elapsed:.1f}s" if elapsed else "?"
                print(f"完成 ({t_str})")

                f.write(f"{'#' * 60}\n文件名: {filename}\n{'#' * 60}\n")
                f.write(format_output(ocr_text, qr_results))
                f.write("\n\n\n")
                f.flush()  # 实时落盘, 防中途崩溃丢失

        total_t = time.time() - total_t0
        print("-" * 60)
        print(f"完成! 本次处理 {processed} 张, 耗时 {total_t:.1f}s")
        print(f"结果文件: {output_path}")

    else:
        # ---------- 单文件模式 ----------
        image_path = args[0]
        print(f"处理: {image_path} ...")
        ocr_text, qr_results, elapsed = analyze_image(image_path, ocr_engine)
        if elapsed:
            print(f"耗时: {elapsed:.1f}s")

        base = os.path.splitext(os.path.basename(image_path))[0]
        out = f"{base}_ocr.txt"
        with open(out, "w", encoding="utf-8") as f:
            f.write(format_output(ocr_text, qr_results))

        print(f"\n已保存: {out}")
        print("-" * 60)
        print(format_output(ocr_text, qr_results))


if __name__ == "__main__":
    main()
