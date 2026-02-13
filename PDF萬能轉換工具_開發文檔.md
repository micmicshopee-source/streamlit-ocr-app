# PDF 萬能轉換工具 — 開發文檔

**版本**：v1.0  
**更新日期**：2025-02  
**對象**：後端／前端開發、維運

**相關文件**：`PDF萬能轉換工具_iLovePDF參考分析.md`、`pdf_converter.py`

---

## 一、模組架構

### 1.1 檔案結構

```
streamlit_ocr_app/
├── pdf_converter.py          # 轉換邏輯模組（獨立可測試）
├── app.py                    # 主程式，整合 PDF 工具 UI（約 2631–2760 行）
├── requirements.txt          # 依賴：pdfplumber, python-pptx, pdf2image, pdf2docx, python-docx, fpdf2
└── packages.txt              # 系統依賴：poppler-utils（pdf2image 用）
```

### 1.2 模組職責

| 檔案 | 職責 |
|------|------|
| `pdf_converter.py` | 純轉換邏輯：`pdf_to_excel`、`pdf_to_ppt`、`pdf_to_images`、`pdf_to_word`、`pdf_to_word_with_ai_ocr` |
| `app.py` | 檔案上傳、選項 UI、進度條、下載按鈕、錯誤提示 |

### 1.3 依賴關係

```
pdf_converter.py
├── pdfplumber      → pdf_to_excel
├── python-pptx     → pdf_to_ppt
├── pdf2image       → pdf_to_ppt, pdf_to_images, pdf_to_word_with_ai_ocr
├── Pillow          → pdf_to_ppt, pdf_to_images, pdf_to_word_with_ai_ocr
├── pdf2docx        → pdf_to_word
├── python-docx     → pdf_to_word_with_ai_ocr
├── pandas+openpyxl → pdf_to_excel
└── requests        → pdf_to_word_with_ai_ocr（Gemini API）

系統：poppler-utils（pdf2image 依賴）
```

---

## 二、API 規格

### 2.1 函數簽名與回傳

| 函數 | 輸入 | 回傳 | 說明 |
|------|------|------|------|
| `pdf_to_excel` | `pdf_bytes`, `progress_callback` | `(bytes, str)` | 成功：`.xlsx`；失敗：`(None, error_msg)` |
| `pdf_to_ppt` | `pdf_bytes`, `progress_callback` | `(bytes, str)` | 成功：`.pptx`；失敗：`(None, error_msg)` |
| `pdf_to_images` | `pdf_bytes`, `fmt`, `dpi`, `progress_callback` | `(zip_bytes, first_img_bytes, str)` | 成功：ZIP + 首頁預覽；失敗：`(None, None, error_msg)` |
| `pdf_to_word` | `pdf_bytes`, `progress_callback` | `(bytes, str)` | 成功：`.docx`；失敗：`(None, error_msg)` |
| `pdf_to_word_with_ai_ocr` | `pdf_bytes`, `api_key`, `model_name`, `progress_callback` | `(bytes, str)` | 掃描檔用 Gemini Vision |
| `images_to_pdf` | `image_bytes_list`, `progress_callback` | `(bytes, str)` | JPG/PNG 合併為 PDF |

### 2.2 錯誤處理

- 加密 PDF：回傳 `"PDF 已加密或受密碼保護，無法讀取"`
- 損毀 PDF：回傳 `"PDF 格式損毀或無效"` 或相關訊息
- 無 poppler：回傳 `"pdf2image 需要 poppler。Windows 可安裝 poppler 或使用 conda"`
- 無依賴：回傳 `"未安裝 xxx，請執行：pip install xxx"`

### 2.3 進度回調

```python
progress_callback(progress: float)  # 0.0 ~ 1.0
```

app.py 中範例：`progress_callback=lambda p: progress.progress(0.3 + 0.7 * p)`

---

## 三、擴充開發指南

### 3.1 新增「從 PDF 轉出」功能

1. 在 `pdf_converter.py` 新增函數，例如：

```python
def pdf_to_pdfa(pdf_bytes: bytes, progress_callback=None) -> Tuple[Optional[bytes], Optional[str]]:
    """使用 pikepdf 轉為 PDF/A。"""
    _safe_imports()
    if not _pikepdf:
        return None, "未安裝 pikepdf，請執行：pip install pikepdf"
    # ... 實作
    return result_bytes, None
```

2. 在 `app.py` 的 `conv_target` 選項加入新項目，並在轉換邏輯分支中呼叫：

```python
# 選項
conv_target = st.selectbox(...,
    ["Excel (.xlsx)", "PPT (.pptx)", "圖片 (JPG/PNG) → ZIP", "Word (.docx)", "PDF/A"],
    ...)

# 分支
elif "PDF/A" in conv_target:
    result, err = pdf_to_pdfa(pdf_bytes, ...)
```

3. 更新 `requirements.txt` 與 `requirements-server.txt`。

### 3.2 新增「轉換為 PDF」功能（例如 JPG → PDF）

1. 在 `pdf_converter.py` 新增：

```python
def images_to_pdf(image_bytes_list: list, progress_callback=None) -> Tuple[Optional[bytes], Optional[str]]:
    """多張圖片轉為單一 PDF。"""
    from fpdf import FPDF
    # ... 實作
    return pdf_bytes, None
```

2. 在 `app.py` 的 PDF 工具區塊中，需增加「轉換模式」切換（從 PDF 轉出 / 轉成 PDF），並依模式顯示不同上傳與選項 UI。

### 3.3 雙向分類架構（參考 iLovePDF）

建議在 UI 中增加 Tab 或 Radio：

- **從 PDF 轉換**：PDF → Excel、PPT、圖片、Word、PDF/A
- **轉換為 PDF**：JPG、Word、PPT、Excel、HTML → PDF

對應的 `app.py` 結構可為：

```python
pdf_mode = st.radio("轉換方向", ["從 PDF 轉換", "轉換為 PDF"], horizontal=True)
if pdf_mode == "從 PDF 轉換":
    # 現有邏輯：上傳 PDF → 選目標
else:
    # 新邏輯：選來源格式 → 上傳檔案 → 轉 PDF
```

---

## 四、技術實作要點

### 4.1 檔案大小限制

- 目前限制：50MB（app.py 中 `len(pdf_bytes) > 50 * 1024 * 1024` 時顯示警告）
- 建議：大檔可考慮分頁處理或提示使用者縮小

### 4.2 暫存檔

- `pdf_to_word` 使用 `tempfile.NamedTemporaryFile` 寫入 PDF 與 DOCX，轉換完成後刪除
- 注意：`delete=False` 時需手動 `os.remove`

### 4.3 AI OCR 模式

- 使用 Gemini Vision API，每頁轉為 JPEG 後 base64 傳送
- 圖片縮放：`img.thumbnail((1920, 1920))` 以控制 API 負載
- 需在進階設定或 Secrets 中設定 `GEMINI_API_KEY`

### 4.4 測試

```bash
# 單元測試
python -c "
from pdf_converter import pdf_to_excel, pdf_to_word
with open('test.pdf', 'rb') as f:
    b = f.read()
r, e = pdf_to_excel(b)
print('Excel:', 'OK' if r else e)
```

---

## 五、部署注意事項

| 項目 | 說明 |
|------|------|
| poppler | Ubuntu/Debian：`sudo apt install poppler-utils`；Docker：在 Dockerfile 中加入 |
| pdf2docx | 若安裝失敗，可提示使用者改用手動安裝或 AI OCR 模式 |
| 記憶體 | 大 PDF 會佔用較多記憶體，建議限制單檔大小或頁數 |

---

*文件建立日期：2025-02*
