# iLovePDF 可編輯轉換 — 技術分析與免費方案

---

## 一、iLovePDF 用什麼技術？

iLovePDF 使用的是 **OCR（光學字元辨識）**，不是 AI 大語言模型。

| 技術類型 | 說明 | 成本 |
|----------|------|------|
| **OCR** | 從圖片中辨識文字，產出可選取、可編輯的文字 | 可完全免費（如 Tesseract） |
| **AI / LLM** | 如 Gemini Vision，用大模型理解圖片內容 | 按次付費（API 呼叫） |

OCR 是傳統／經典的電腦視覺技術，用來「認字」，不涉及理解語意或生成內容，因此可以完全用開源、免費方案實作。

---

## 二、常見 OCR 引擎對照

| 引擎 | 類型 | 成本 | 準確度 | 備註 |
|------|------|------|--------|------|
| **Tesseract** | 開源 | 免費 | 中高（印刷體佳） | Google 維護，100+ 語言 |
| **ABBYY** | 商業 | 付費 | 高 | iLovePDF 等服務可能採用 |
| **OCRmyPDF** | 開源 | 免費 | 依 Tesseract | 專為 PDF 設計，內建 Tesseract |
| **PaddleOCR** | 開源 | 免費 | 高（中文佳） | 百度開源，中文辨識強 |

iLovePDF 可能使用 ABBYY 或自研 OCR，但**同樣的流程**可以用免費的 Tesseract 或 PaddleOCR 達成。

---

## 三、免費 OCR 實作流程（PDF → 可編輯 Word）

```
PDF 檔案
   ↓
pdf2image：每頁轉成圖片
   ↓
Tesseract / PaddleOCR：對每張圖做 OCR，得到文字
   ↓
python-docx：把文字寫入 Word
   ↓
可編輯的 .docx
```

**所需套件（皆免費）：**

- `pdf2image`：PDF → 圖片（需系統安裝 poppler）
- `pytesseract`：Tesseract 的 Python 介面
- `Tesseract`：系統層 OCR 引擎（需另外安裝）
- `python-docx`：產生 Word 檔

---

## 四、Tesseract 安裝

### Windows

```bash
# 1. 下載安裝檔
# https://github.com/UB-Mannheim/tesseract/wiki

# 2. 安裝後，將 Tesseract 路徑加入環境變數，或於程式中指定
# 例如：C:\Program Files\Tesseract-OCR\tesseract.exe

# 3. 安裝中文語言包（可選）
# 安裝時勾選 chi_tra（繁體）、chi_sim（簡體）
```

### Ubuntu / Debian

```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-tra
```

### macOS

```bash
brew install tesseract tesseract-lang
```

### Python 套件

```bash
pip install pytesseract pdf2image python-docx
```

---

## 五、與 AI OCR（Gemini）的差異

| 項目 | Tesseract OCR | Gemini AI OCR |
|------|---------------|---------------|
| 成本 | 免費 | 按 API 呼叫計費 |
| 部署 | 本地執行 | 需網路、API 金鑰 |
| 表格 | 需額外處理 | 可較好保留結構 |
| 手寫 | 較弱 | 較強 |
| 複雜版面 | 一般 | 較佳 |
| 隱私 | 資料不離開本機 | 需上傳至雲端 |

**建議：**

- 一般掃描檔、印刷體：優先使用 **Tesseract**，成本為零。
- 手寫、複雜版面、表格：可保留 **Gemini** 作為進階選項。

---

## 六、在 pdf_converter 中的實作建議

1. **新增 `pdf_to_word_with_tesseract`**
   - 使用 `pdf2image` + `pytesseract` + `python-docx`
   - 作為「免費 OCR 模式」

2. **UI 選項**
   - 「一般模式」：pdf2docx（僅文字型 PDF）
   - 「OCR 模式（Tesseract）」：掃描檔，免費
   - 「AI OCR 模式（Gemini）」：進階，需 API 金鑰

3. **依賴**
   - `pytesseract`
   - 系統安裝 Tesseract
   - 現有：`pdf2image`、`python-docx`

---

## 七、參考程式碼架構

```python
def pdf_to_word_with_tesseract(pdf_bytes, lang="chi_tra+eng", progress_callback=None):
    """使用 Tesseract OCR 將掃描檔 PDF 轉為可編輯 Word。"""
    import pytesseract
    from pdf2image import convert_from_bytes
    from docx import Document

    images = convert_from_bytes(pdf_bytes, dpi=200)
    doc = Document()
    for i, img in enumerate(images):
        if progress_callback:
            progress_callback((i + 1) / len(images))
        text = pytesseract.image_to_string(img, lang=lang)
        for para in text.split("\n\n"):
            if para.strip():
                doc.add_paragraph(para.strip())
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read(), None
```

---

## 八、結論

- iLovePDF 的「可編輯轉換」主要依賴 **OCR**，不是付費 AI。
- 使用 **Tesseract** 可在本地、免費達成類似效果。
- 已於 `pdf_converter` 中實作 Tesseract OCR 模式（`pdf_to_word_with_tesseract`），作為掃描檔的預設免費方案。

---

## 九、已實作項目

- [x] `pdf_to_word_with_tesseract` 函數
- [x] PDF→Word 三種模式：OCR（Tesseract）、一般（pdf2docx）、AI（Gemini）
- [x] 預設使用 OCR 模式（免費）
- [x] 依賴：`pytesseract`、系統 Tesseract、`tesseract-ocr-chi-tra`（繁體中文）
