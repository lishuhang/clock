import sys
import os
import cv2
import easyocr
import warnings
import datetime
import numpy as np

# 尝试导入 zxing-cpp，这是解决 OpenCV "ECI not supported" 报错的最佳方案
try:
    import zxingcpp
    HAS_ZXING = True
except ImportError:
    HAS_ZXING = False

# 忽略 EasyOCR 的一些用户警告
warnings.filterwarnings("ignore", category=UserWarning)

# 定义支持的图片扩展名
VALID_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

def scan_chunk_with_zxing(img_chunk):
    """使用 zxing-cpp 扫描图片块"""
    results = set()
    try:
        # zxing-cpp 接受 numpy array
        barcodes = zxingcpp.read_barcodes(img_chunk)
        for barcode in barcodes:
            if barcode.text:
                results.add(barcode.text)
    except Exception:
        pass
    return results

def scan_chunk_with_opencv(img_chunk, detector):
    """使用 OpenCV 扫描图片块 (备用方案)"""
    results = set()
    try:
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img_chunk)
        if retval:
            for info in decoded_info:
                if info and info.strip():
                    results.add(info)
    except Exception:
        pass
    return results

def detect_qr_sliding_window(cv_img):
    """
    滑动窗口全图扫描：
    解决长图中间二维码漏扫问题，以及提高高分辨率图片的检测率。
    """
    height, width = cv_img.shape[:2]
    found_codes = set()
    
    # ----------------------------------------------------
    # 策略 1: 全图直接扫 (针对清晰的大图)
    # ----------------------------------------------------
    if HAS_ZXING:
        found_codes.update(scan_chunk_with_zxing(cv_img))
    else:
        qr_detector = cv2.QRCodeDetector()
        found_codes.update(scan_chunk_with_opencv(cv_img, qr_detector))

    # 如果已经找到了，且图片不是特别长，可能就不需要滑动窗口了
    # 但为了保险起见（比如一张图有多个二维码），对于长图还是建议跑一遍滑动窗口

    # ----------------------------------------------------
    # 策略 2: 滑动窗口 (Sliding Window) 
    # ----------------------------------------------------
    # 窗口高度：设为宽度的 1.2 倍，保证能容纳大部分二维码
    # 步长：窗口高度的 70% (30% 重叠)，防止二维码被切断
    window_h = int(width * 1.2) 
    if window_h < 600: window_h = 600 # 最小窗口高度
    if window_h > height: window_h = height

    step = int(window_h * 0.7)
    
    # 如果图片比窗口还小，就不需要滑动了
    if height > window_h:
        # 预初始化 OpenCV 检测器以免重复创建
        detector = cv2.QRCodeDetector() if not HAS_ZXING else None

        for y in range(0, height, step):
            end_y = min(y + window_h, height)
            
            # 裁剪区块
            chunk = cv_img[y:end_y, :]
            
            # 扫描区块
            if HAS_ZXING:
                found_codes.update(scan_chunk_with_zxing(chunk))
            else:
                found_codes.update(scan_chunk_with_opencv(chunk, detector))
            
            # 到底部退出
            if end_y == height:
                break

    return list(found_codes)

def analyze_image(image_path, reader):
    """
    核心处理函数
    """
    if not os.path.exists(image_path):
        return f"错误: 找不到文件 '{image_path}'", []

    # 读取图片 (支持中文路径)
    cv_img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    
    qr_results = []
    ocr_text = ""

    if cv_img is None:
        ocr_text = "[错误: 无法读取图片]"
    else:
        # 1. 二维码识别 (Sliding Window + Zxing/OpenCV)
        qr_results = detect_qr_sliding_window(cv_img)
        
        # 如果还没扫出来，且没有安装 zxing-cpp，提示用户
        if not qr_results and not HAS_ZXING:
            print("  [提示] 未检测到二维码。建议安装 'pip install zxing-cpp' 以大幅提升识别率。")

        # 2. OCR 识别 (EasyOCR)
        try:
            result = reader.readtext(image_path, detail=0)
            if result:
                ocr_text = "\n".join(result)
            else:
                ocr_text = "[未检测到明显文字]"
        except Exception as e:
            ocr_text = f"[OCR 处理错误: {e}]"

    return ocr_text, qr_results

def format_output_string(ocr_text, qr_results):
    output = []
    output.append("========== OCR 文字识别内容 (EasyOCR) ==========")
    output.append(ocr_text)
    output.append("")
    output.append(f"========== 二维码识别内容 (共 {len(qr_results)} 个) ==========")
    if qr_results:
        for index, content in enumerate(qr_results, 1):
            output.append(f"[{index}] {content}")
    else:
        output.append("[未检测到二维码]")
    return "\n".join(output)

def main():
    print(f"正在初始化 EasyOCR 模型... (二维码引擎: {'zxing-cpp (强)' if HAS_ZXING else 'OpenCV (弱)'})")
    
    try:
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    except Exception as e:
        print(f"严重错误: 模型加载失败 - {e}")
        return

    # 模式判断
    if len(sys.argv) < 2:
        # 批量模式
        current_dir = os.getcwd()
        files = [f for f in os.listdir(current_dir) if f.lower().endswith(VALID_EXTENSIONS)]
        files.sort()

        if not files:
            print("当前目录未找到图片。")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        output_filename = f"{timestamp}-ocr.txt"
        print(f"发现 {len(files)} 张图片，结果将保存至: {output_filename}")

        with open(output_filename, "w", encoding="utf-8") as f:
            for idx, filename in enumerate(files, 1):
                print(f"[{idx}/{len(files)}] 正在处理: {filename}")
                ocr_text, qr_results = analyze_image(os.path.join(current_dir, filename), reader)
                
                f.write(f"{'#' * 60}\n文件名: {filename}\n{'#' * 60}\n")
                f.write(format_output_string(ocr_text, qr_results))
                f.write("\n\n\n")

        print(f"\n全部完成! 查看文件: {output_filename}")

    else:
        # 单文件模式
        image_path = sys.argv[1]
        print(f"正在处理: {image_path} ...")
        
        ocr_text, qr_results = analyze_image(image_path, reader)
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_filename = f"{base_name}_ocr.txt"
        
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(format_output_string(ocr_text, qr_results))
            
        print(f"\n成功! 已保存至: {output_filename}")

if __name__ == "__main__":
    main()