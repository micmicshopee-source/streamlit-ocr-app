# PDF 萬能轉換工具 — 改版方案

---

## 一、問題診斷

### 1.1 轉換後無法編輯的原因

| 轉換類型 | 現有邏輯 | 問題 |
|----------|----------|------|
| **PDF → Word** | 使用 `pdf2docx` 解析 PDF 結構 | **掃描檔／圖片型 PDF** 無文字層，pdf2docx 只能輸出空白或嵌入圖片，無法產生可編輯文字 |
| **PDF → Excel** | 使用 `pdfplumber` 提取表格 | 僅能辨識**文字型表格**；掃描檔無文字層則偵測不到表格 |
| **PDF → PPT** | 每頁轉圖片嵌入 | 本來就是圖片，無可編輯文字（設計如此） |
| **PDF → 圖片** | 每頁轉圖 | 預期為圖片，無編輯需求 |

**結論**：掃描檔、截圖、圖片型 PDF 缺乏文字層，現有工具（pdf2docx、pdfplumber）無法直接提取可編輯內容。

### 1.2 既有解法（未對外開放）

`pdf_converter.py` 已實作 `pdf_to_word_with_ai_ocr()`，使用 **Gemini Vision** 對每頁做 OCR，可產出可編輯 Word，但**未在 UI 中提供**。

---

## 二、UI 風格改版（參考圖片）

目標：深色主題、卡片式轉換選項、拖放上傳。

### 2.1 佈局結構

```
┌─────────────────────────────────────────────────────────┐
│  PDF 萬能轉換                                            │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │         ↑ 拖放文件或點擊上傳 PDF                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ PDF→Excel │ │ PDF→Word │ │ PDF→PPT  │ │ PDF→圖片 │  │
│  │   (綠)    │ │   (藍)   │ │  (橘)    │ │  (紫)    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                         │
│  [ 開始轉換 ]                                            │
└─────────────────────────────────────────────────────────┘
```

### 2.2 實作方式

- **深色主題**：使用 `.streamlit/config.toml` 或自訂 CSS（`premium_dark.css` 等）
- **卡片式選項**：以 `st.columns` + 自訂按鈕樣式，或 `st.radio` 搭配 CSS
- **拖放上傳**：`st.file_uploader` 已支援，可加 CSS 優化視覺
- **顏色區分**：Excel 綠、Word 藍、PPT 橘、圖片紫

### 2.3 需調整的檔案

- `app.py`：PDF 轉換區塊佈局與樣式
- `.streamlit/config.toml` 或自訂 CSS：深色主題

---

## 三、轉換功能增強

### 3.1 PDF → Word：加入 AI OCR 模式

| 模式 | 適用情境 | 實作 |
|------|----------|------|
| **一般模式** | 文字型 PDF（含文字層） | 現有 `pdf_to_word`（pdf2docx） |
| **AI OCR 模式** | 掃描檔、圖片型 PDF | 現有 `pdf_to_word_with_ai_ocr`（Gemini Vision） |

**建議 UI**：

- 預設「一般模式」
- 提供「掃描檔／圖片型 PDF」勾選或切換按鈕
- 勾選時改用 AI OCR 模式（需 Gemini API 金鑰）

**自動檢測（選用）**：

- 先用 pdf2docx 轉換
- 若輸出文字極少（如 < 50 字），提示「可能為掃描檔，建議改用 AI OCR 模式」

### 3.2 PDF → Excel：掃描檔處理

| 方案 | 說明 |
|------|------|
| **A. 維持現狀** | 僅支援文字型表格，掃描檔無表格時提示 |
| **B. AI OCR 擴充** | 新增 `pdf_to_excel_with_ai_ocr`：每頁 OCR → 解析表格結構 → 寫入 Excel |
| **C. 先 Word 再 Excel** | 先以 AI OCR 轉 Word，再從 Word 提取表格轉 Excel（需額外邏輯） |

建議優先實作 **3.1**，再視需求決定是否做 **3.2 B**。

### 3.3 PDF → PPT 與圖片

- 維持現狀：PPT 為圖片嵌入，圖片為圖片輸出，無需 OCR。

---

## 四、實作檢查清單

### 階段一：轉換功能修正（優先）

- [ ] 在 PDF→Word 區塊加入「AI OCR 模式（掃描檔適用）」選項
- [ ] 勾選時呼叫 `pdf_to_word_with_ai_ocr`，傳入 Gemini API 金鑰
- [ ] 一般模式失敗或輸出幾乎無文字時，提示「建議改用 AI OCR 模式」

### 階段二：UI 風格改版

- [ ] 套用深色主題（config 或 CSS）
- [ ] 卡片式轉換選項（Excel、Word、PPT、圖片）
- [ ] 拖放上傳區塊樣式優化
- [ ] 「開始轉換」按鈕置於底部

### 階段三：進階（選用）

- [ ] PDF→Excel 的 AI OCR 模式
- [ ] 轉換前自動偵測是否為掃描檔

---

## 五、程式碼修改要點

### 5.1 匯入 AI OCR 函數

```python
from pdf_converter import (
    pdf_to_excel,
    pdf_to_ppt,
    pdf_to_images,
    pdf_to_word,
    pdf_to_word_with_ai_ocr,  # 新增
    images_to_pdf,
)
```

### 5.2 Word 轉換邏輯

```python
# 若為 AI OCR 模式
if use_ai_ocr and api_key:
    result, err = pdf_to_word_with_ai_ocr(
        pdf_bytes, api_key=api_key, model_name=model,
        progress_callback=...
    )
else:
    result, err = pdf_to_word(pdf_bytes, progress_callback=...)
```

### 5.3 深色主題 CSS 範例

```css
/* 轉換選項卡片 */
[data-testid="stRadio"] {
    /* 自訂卡片樣式 */
}
.stPdfCard { border: 2px solid #4CAF50; border-radius: 8px; padding: 1rem; }
```

---

## 六、建議執行順序

1. **先修轉換**：加入 AI OCR 模式，解決掃描檔無法編輯問題
2. **再改 UI**：深色主題、卡片式選項、拖放上傳樣式
