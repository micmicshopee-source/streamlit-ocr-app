#!/usr/bin/env python3
"""
視頻演示生成腳本 — 上班族小工具
將宣傳圖與系統介面圖組合成演示視頻
"""
from __future__ import annotations

import os
import sys

# 可能的圖片路徑（依序嘗試）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_PATHS = [
    os.path.join(SCRIPT_DIR, "assets"),
    os.path.join(SCRIPT_DIR, "demo_assets"),
    os.path.join(os.path.expanduser("~"), ".cursor", "projects", "d-streamlit-ocr-app", "assets"),
    os.path.join(os.path.expanduser("~"), ".cursor", "projects", "d-streamlit-ocr-app", "streamlit_ocr_app", "assets"),
]

# 演示順序：開場 → 登入 → 發票 → PDF → 宣傳圖收尾
IMAGE_ORDER = [
    "promo_main_banner.png",
    "demo_app_login_screen.png",
    "demo_app_invoice_screen.png",
    "demo_app_pdf_screen.png",
    "promo_invoice_feature.png",
    "promo_pdf_tool.png",
]

# 每張圖顯示秒數
DURATION_PER_IMAGE = 4
FPS = 24
OUTPUT_FILE = "demo_video.mp4"


def find_assets_dir() -> str | None:
    """找到包含所需圖片的目錄"""
    for path in ASSET_PATHS:
        if not os.path.isdir(path):
            continue
        found = sum(1 for name in IMAGE_ORDER if os.path.isfile(os.path.join(path, name)))
        if found >= 1:  # 至少找到一張
            return path
    return None


def collect_images(assets_dir: str) -> list[tuple[str, str]]:
    """收集存在的圖片路徑，回傳 (路徑, 檔名)"""
    result = []
    for name in IMAGE_ORDER:
        path = os.path.join(assets_dir, name)
        if os.path.isfile(path):
            result.append((path, name))
    return result


def create_video_with_imageio(images: list[tuple[str, str]], output_path: str) -> bool:
    """使用 imageio 建立視頻"""
    try:
        import imageio.v2 as iio
    except ImportError:
        try:
            import imageio as iio
        except ImportError:
            print("請安裝 imageio: pip install imageio imageio-ffmpeg")
            return False

    from PIL import Image
    import numpy as np

    frames = []
    target_w, target_h = 1920, 1080

    for img_path, _ in images:
        img = Image.open(img_path).convert("RGB")
        # 等比例縮放並置中裁切
        img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        w, h = img.size
        canvas = Image.new("RGB", (target_w, target_h), (15, 15, 15))
        x = (target_w - w) // 2
        y = (target_h - h) // 2
        canvas.paste(img, (x, y))
        arr = np.array(canvas)
        n_frames = DURATION_PER_IMAGE * FPS
        for _ in range(n_frames):
            frames.append(arr.copy())

    if not frames:
        print("沒有可用的圖片")
        return False

    print(f"正在輸出視頻：{len(frames)} 幀，{len(frames)/FPS:.1f} 秒...")
    try:
        iio.mimwrite(output_path, frames, fps=FPS, codec="libx264", quality=8)
    except TypeError:
        iio.mimwrite(output_path, frames, fps=FPS)
    return True


def create_video_with_opencv(images: list[tuple[str, str]], output_path: str) -> bool:
    """使用 OpenCV 建立視頻（備選）"""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return False

    from PIL import Image

    target_w, target_h = 1920, 1080
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, FPS, (target_w, target_h))

    for img_path, _ in images:
        img = Image.open(img_path).convert("RGB")
        img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        w, h = img.size
        canvas = Image.new("RGB", (target_w, target_h), (15, 15, 15))
        x = (target_w - w) // 2
        y = (target_h - h) // 2
        canvas.paste(img, (x, y))
        frame = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
        for _ in range(DURATION_PER_IMAGE * FPS):
            out.write(frame)

    out.release()
    return True


def create_placeholder_images(assets_dir: str) -> list[tuple[str, str]]:
    """若圖片不足，用 PIL 產生佔位圖"""
    from PIL import Image, ImageDraw, ImageFont

    os.makedirs(assets_dir, exist_ok=True)
    result = []
    w, h = 1920, 1080
    bg = (30, 30, 46)
    text_color = (255, 255, 255)

    titles = [
        "上班族小工具 | 發票報帳・辦公小幫手",
        "登入介面",
        "發票報帳小秘笈",
        "PDF 萬能轉換工具",
        "AI 辨識・對獎・導出",
        "一鍵轉換・辦公效率 UP",
    ]

    for i, name in enumerate(IMAGE_ORDER):
        path = os.path.join(assets_dir, name)
        if os.path.isfile(path):
            result.append((path, name))
            continue
        img = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(img)
        title = titles[i] if i < len(titles) else name
        try:
            font = ImageFont.truetype("arial.ttf", 72)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), title, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((w - tw) // 2, (h - th) // 2), title, fill=text_color, font=font)
        img.save(path)
        result.append((path, name))
        print(f"  已建立佔位圖: {name}")

    return result


def main():
    assets_dir = find_assets_dir()
    if not assets_dir:
        assets_dir = os.path.join(SCRIPT_DIR, "demo_assets")
        print(f"未找到現有圖片，將在 {assets_dir} 建立佔位圖...")
        images = create_placeholder_images(assets_dir)
    else:
        print(f"使用圖片目錄: {assets_dir}")
        images = collect_images(assets_dir)
        if len(images) < len(IMAGE_ORDER):
            print(f"  找到 {len(images)} 張圖，缺少的將建立佔位圖")
            images = create_placeholder_images(assets_dir)

    if not images:
        print("錯誤：無法取得任何圖片")
        sys.exit(1)

    output_path = os.path.join(SCRIPT_DIR, OUTPUT_FILE)
    print(f"圖片數量: {len(images)}")
    for _, name in images:
        print(f"  - {name}")

    if create_video_with_imageio(images, output_path):
        print(f"\n完成！視頻已儲存至: {output_path}")
        return
    if create_video_with_opencv(images, output_path):
        print(f"\n完成！視頻已儲存至: {output_path}")
        return

    print("\n請安裝以下任一方案以產生視頻：")
    print("  1. pip install imageio imageio-ffmpeg")
    print("  2. pip install opencv-python")
    sys.exit(1)


if __name__ == "__main__":
    main()
