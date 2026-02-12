# -*- coding: utf-8 -*-
"""
PDF 萬能轉換工具模組
支援：PDF → Excel, PPT, 圖片 (JPG/PNG), Word
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from typing import Optional, Tuple

# 可選依賴：按需導入
_pdfplumber = None
_pptx = None
_pdf2image = None
_pdf2docx = None
_pandas = None
_openpyxl = None
_pil = None


def _safe_imports():
    """延遲導入，避免 import 時即失敗。"""
    global _pdfplumber, _pptx, _pdf2image, _pdf2docx, _pandas, _openpyxl, _pil
    if _pdfplumber is None:
        try:
            import pdfplumber
            _pdfplumber = pdfplumber
        except ImportError:
            _pdfplumber = False
    if _pptx is None:
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            _pptx = (Presentation, Inches, Pt)
        except ImportError:
            _pptx = False
    if _pdf2image is None:
        try:
            from pdf2image import convert_from_bytes
            _pdf2image = convert_from_bytes
        except ImportError:
            _pdf2image = False
    if _pdf2docx is None:
        try:
            from pdf2docx import Converter
            _pdf2docx = Converter
        except ImportError:
            _pdf2docx = False
    if _pandas is None:
        try:
            import pandas as pd
            _pandas = pd
        except ImportError:
            _pandas = False
    if _openpyxl is None:
        try:
            from openpyxl import load_workbook
            from openpyxl.styles import Alignment, Font, Border, Side
            _openpyxl = (load_workbook, Alignment, Font, Border, Side)
        except ImportError:
            _openpyxl = False
    if _pil is None:
        try:
            from PIL import Image
            _pil = Image
        except ImportError:
            _pil = False


def pdf_to_excel(pdf_bytes: bytes, progress_callback=None) -> Tuple[Optional[bytes], Optional[str]]:
    """
    使用 pdfplumber 提取 PDF 表格，導出為 .xlsx。
    多個表格分別放在不同 Sheet。
    Returns: (xlsx_bytes, error_message)
    """
    _safe_imports()
    if not _pdfplumber:
        return None, "未安裝 pdfplumber，請執行：pip install pdfplumber"
    if not _pandas:
        return None, "未安裝 pandas"
    if not _openpyxl:
        return None, "未安裝 openpyxl"

    try:
        import pandas as pd
        with io.BytesIO(pdf_bytes) as f:
            pdf = _pdfplumber.open(f)
            tables_by_page = []
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                if progress_callback:
                    progress_callback((i + 1) / total_pages)
                tables = page.extract_tables()
                if tables:
                    for t_idx, tbl in enumerate(tables):
                        if tbl and len(tbl) > 0:
                            df = pd.DataFrame(tbl[1:], columns=tbl[0] if tbl[0] else None)
                            if df.empty and tbl:
                                df = pd.DataFrame(tbl)
                            tables_by_page.append((f"Page{i+1}_Table{t_idx+1}", df))
            pdf.close()

        if not tables_by_page:
            return None, "PDF 中未偵測到表格數據"

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            for sheet_name, df in tables_by_page:
                safe_name = sheet_name[:31]  # Excel sheet 名稱限制 31 字元
                df.to_excel(writer, sheet_name=safe_name, index=False)
        buf.seek(0)
        return buf.read(), None
    except Exception as e:
        err_msg = str(e)
        if "encrypted" in err_msg.lower() or "password" in err_msg.lower():
            return None, "PDF 已加密或受密碼保護，無法讀取"
        if "corrupt" in err_msg.lower() or "invalid" in err_msg.lower():
            return None, "PDF 格式損毀或無效"
        return None, f"轉換失敗：{err_msg}"


def pdf_to_ppt(pdf_bytes: bytes, progress_callback=None) -> Tuple[Optional[bytes], Optional[str]]:
    """
    將 PDF 每頁轉為圖片，嵌入 PPT 幻燈片（等比例縮放填滿）。
    Returns: (pptx_bytes, error_message)
    """
    _safe_imports()
    if not _pptx:
        return None, "未安裝 python-pptx，請執行：pip install python-pptx"
    if not _pdf2image:
        return None, "未安裝 pdf2image（需同時安裝 poppler）。請執行：pip install pdf2image"
    if not _pil:
        return None, "未安裝 Pillow"

    try:
        Presentation, Inches, Pt = _pptx
        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)

        images = _pdf2image(pdf_bytes, dpi=150)
        total = len(images)
        slide_w_inch = 10.0
        slide_h_inch = 7.5
        for i, img in enumerate(images):
            if progress_callback:
                progress_callback((i + 1) / total)

            slide_layout = prs.slide_layouts[6]  # 空白
            slide = prs.slides.add_slide(slide_layout)
            img_w, img_h = img.size
            # 等比例縮放以填滿頁面（使用 max scale）
            img_w_inch = img_w / 96.0
            img_h_inch = img_h / 96.0
            scale_w = slide_w_inch / img_w_inch
            scale_h = slide_h_inch / img_h_inch
            scale = max(scale_w, scale_h)
            new_w_inch = img_w_inch * scale
            new_h_inch = img_h_inch * scale
            left_inch = (slide_w_inch - new_w_inch) / 2
            top_inch = (slide_h_inch - new_h_inch) / 2
            buf_img = io.BytesIO()
            img.save(buf_img, format="PNG")
            buf_img.seek(0)
            slide.shapes.add_picture(buf_img, Inches(left_inch), Inches(top_inch), width=Inches(new_w_inch), height=Inches(new_h_inch))

        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.read(), None
    except Exception as e:
        err_msg = str(e)
        if "encrypted" in err_msg.lower() or "password" in err_msg.lower():
            return None, "PDF 已加密或受密碼保護，無法讀取"
        if "poppler" in err_msg.lower() or "convert" in err_msg.lower():
            return None, "pdf2image 需要 poppler。Windows 可安裝 poppler 或使用 conda：conda install -c conda-forge poppler"
        return None, f"轉換失敗：{err_msg}"


def pdf_to_images(
    pdf_bytes: bytes,
    fmt: str = "png",
    dpi: int = 200,
    progress_callback=None
) -> Tuple[Optional[bytes], Optional[bytes], Optional[str]]:
    """
    將 PDF 每頁轉為圖片，壓縮為 ZIP。
    Returns: (zip_bytes, first_image_bytes_for_preview, error_message)
    """
    _safe_imports()
    if not _pdf2image:
        return None, None, "未安裝 pdf2image（需同時安裝 poppler）。請執行：pip install pdf2image"
    if not _pil:
        return None, None, "未安裝 Pillow"

    try:
        images = _pdf2image(pdf_bytes, dpi=dpi)
        total = len(images)
        first_img_bytes = None
        zip_buf = io.BytesIO()
        ext = "png" if fmt.lower() == "png" else "jpg"
        save_fmt = "PNG" if ext == "png" else "JPEG"

        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, img in enumerate(images):
                if progress_callback:
                    progress_callback((i + 1) / total)
                img_buf = io.BytesIO()
                if ext == "jpg":
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(img_buf, format=save_fmt, quality=90)
                else:
                    img.save(img_buf, format=save_fmt)
                img_buf.seek(0)
                data = img_buf.read()
                zf.writestr(f"page_{i+1:04d}.{ext}", data)
                if i == 0:
                    first_img_bytes = data

        zip_buf.seek(0)
        return zip_buf.read(), first_img_bytes, None
    except Exception as e:
        err_msg = str(e)
        if "encrypted" in err_msg.lower() or "password" in err_msg.lower():
            return None, None, "PDF 已加密或受密碼保護，無法讀取"
        if "poppler" in err_msg.lower():
            return None, None, "pdf2image 需要 poppler。Windows 可安裝 poppler 或使用 conda"
        return None, None, f"轉換失敗：{err_msg}"


def pdf_to_word(pdf_bytes: bytes, progress_callback=None) -> Tuple[Optional[bytes], Optional[str]]:
    """
    使用 pdf2docx 將 PDF 轉為 Word。
    Returns: (docx_bytes, error_message)
    """
    _safe_imports()
    if not _pdf2docx:
        return None, "未安裝 pdf2docx，請執行：pip install pdf2docx"

    try:
        Converter = _pdf2docx
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_tmp:
            pdf_tmp.write(pdf_bytes)
            pdf_path = pdf_tmp.name
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as docx_tmp:
                docx_path = docx_tmp.name
            try:
                cv = Converter(pdf_path, docx_path)
                cv.convert()
                cv.close()
                with open(docx_path, "rb") as f:
                    return f.read(), None
            finally:
                try:
                    os.remove(docx_path)
                except Exception:
                    pass
        finally:
            try:
                os.remove(pdf_path)
            except Exception:
                pass
    except Exception as e:
        err_msg = str(e)
        if "encrypted" in err_msg.lower() or "password" in err_msg.lower():
            return None, "PDF 已加密或受密碼保護，無法讀取"
        return None, f"轉換失敗：{err_msg}"
