# PDF 萬能轉換工具 — iLovePDF 參考分析

> 參考來源：[iLovePDF 官網](https://www.ilovepdf.com/zh-tw)  
> 分析範圍：**僅格式轉換功能**（不含合併、拆分、壓縮、編輯、簽名等）

---

## 一、iLovePDF 格式轉換功能矩陣

### 1.1 從 PDF 轉換（PDF → 其他格式）

| 功能 | 目標格式 | 說明 |
|------|----------|------|
| PDF 轉 JPG | JPG | 提取 PDF 中的圖片，或將每一頁轉為 JPG |
| PDF 轉 Word | DOC/DOCX | 轉為可編輯的 Word 文檔，宣稱幾乎 100% 正確 |
| PDF 轉 PowerPoint | PPT/PPTX | 轉為可編輯的簡報 |
| PDF 轉 Excel | XLS/XLSX | 將表格數據提取至 Excel |
| PDF 轉 PDF/A | PDF/A | 轉為 ISO 長期存檔標準格式 |

### 1.2 轉換為 PDF（其他格式 → PDF）

| 功能 | 來源格式 | 說明 |
|------|----------|------|
| JPG 轉 PDF | JPG | 將圖片轉為 PDF，可調整方向與邊距 |
| Word 轉 PDF | DOC/DOCX | 保持原樣與質量 |
| PowerPoint 轉 PDF | PPT/PPTX | 保持原樣與質量 |
| Excel 轉 PDF | XLS/XLSX | 方便查看 |
| HTML 轉 PDF | URL/網頁 | 貼上網址一鍵轉換 |

---

## 二、與本專案 pdf_converter 對照

### 2.1 功能覆蓋對照表

| 轉換方向 | iLovePDF | 本專案 pdf_converter | 備註 |
|----------|----------|----------------------|------|
| **PDF → Excel** | ✅ | ✅ | 使用 pdfplumber 提取表格 |
| **PDF → PowerPoint** | ✅ | ✅ | 每頁轉圖片嵌入 PPT |
| **PDF → Word** | ✅ | ✅ | pdf2docx + AI OCR 掃描檔 |
| **PDF → JPG/圖片** | ✅ | ✅ | 輸出為 ZIP 包（JPG/PNG） |
| **PDF → PDF/A** | ✅ | ❌ | 尚未實作 |
| **JPG → PDF** | ✅ | ✅ | images_to_pdf，多張合併 |
| **Word → PDF** | ✅ | ❌ | 尚未實作 |
| **PPT → PDF** | ✅ | ❌ | 尚未實作 |
| **Excel → PDF** | ✅ | ❌ | 尚未實作 |
| **HTML → PDF** | ✅ | ❌ | 尚未實作 |

### 2.2 本專案優勢

- **AI OCR 模式**：掃描檔 PDF 轉 Word 使用 Gemini Vision，iLovePDF 需付費進階 OCR
- **本地處理**：無需上傳至第三方伺服器，隱私較佳
- **開源可自架**：可部署於自有 VPS

### 2.3 本專案缺口

1. **單向轉換**：目前僅支援「PDF → 其他」，缺少「其他 → PDF」
2. **PDF/A**：無長期存檔格式轉換
3. **HTML → PDF**：無網頁轉 PDF 功能

---

## 三、iLovePDF 產品設計觀察

### 3.1 分類結構

iLovePDF 將轉換功能分為兩大類：

```
轉換為 PDF 文檔
├── JPG 轉 PDF
├── Word 轉 PDF
├── PPT 轉 PDF
├── Excel 轉 PDF
└── HTML 轉換至 PDF

從 PDF 格式轉換
├── PDF 轉 JPG
├── PDF 轉 Word
├── PDF 轉 PowerPoint
├── PDF 轉 Excel
└── PDF 轉換至 PDF/A
```

### 3.2 使用者流程

1. **選擇工具**：從首頁或分類進入單一轉換工具
2. **上傳檔案**：拖曳或點選上傳（支援多檔）
3. **轉換**：自動或手動觸發
4. **下載**：單檔或 ZIP 打包下載

### 3.3 UI 特點

- 每個轉換工具為獨立頁面，功能單一明確
- 首頁以卡片式展示，圖示 + 標題 + 一句說明
- 強調「幾秒鐘完成」「100% 正確」等賣點
- 免費版有每日/每小時限制，進階功能需付費

---

## 四、技術實作建議

### 4.1 優先補齊：其他格式 → PDF

| 功能 | 建議技術方案 | 依賴 |
|------|--------------|------|
| **JPG/PNG → PDF** | Pillow 疊圖 + reportlab 或 fpdf2 | Pillow, fpdf2 |
| **Word → PDF** | python-docx 讀取 + docx2pdf（Windows）或 LibreOffice 無頭模式 | docx2pdf / unoconv |
| **PPT → PDF** | python-pptx 讀取 + comtypes（Windows）或 LibreOffice | 依平台 |
| **Excel → PDF** | openpyxl 讀取 + xlsxwriter / reportlab 繪製 | openpyxl |
| **HTML → PDF** | weasyprint 或 pdfkit（wkhtmltopdf） | weasyprint |

**實務建議**：  
- **JPG → PDF**：最易實作，fpdf2 已在本專案，可直接擴充  
- **Word/PPT/Excel → PDF**：跨平台較複雜，可考慮 weasyprint 或呼叫 LibreOffice 指令列  
- **HTML → PDF**：weasyprint 純 Python，部署較簡單

### 4.2 PDF → PDF/A

- 需使用 **pikepdf** 或 **pypdf** 進行 PDF 結構轉換
- PDF/A 為 ISO 標準，適合長期存檔（嵌入字型、禁止外部依賴等）
- 實作難度中等，可列為後續擴充

### 4.3 本專案 UI 優化建議

參考 iLovePDF 的雙向分類：

```
[ 從 PDF 轉換 ]          [ 轉換為 PDF ]
├── PDF → Excel         ├── JPG → PDF
├── PDF → Word          ├── Word → PDF
├── PDF → PPT           ├── PPT → PDF
├── PDF → 圖片 (ZIP)    ├── Excel → PDF
└── (未來) PDF → PDF/A  └── (未來) HTML → PDF
```

可於側邊欄或 Tab 切換「從 PDF 轉出」與「轉成 PDF」，讓使用者快速找到對應功能。

---

## 五、總結與建議優先順序

| 優先級 | 功能 | 理由 |
|--------|------|------|
| **P0** | JPG/PNG → PDF | 實作簡單，fpdf2 已有，需求高 |
| **P1** | Word → PDF | 辦公常用，可評估 weasyprint 或 LibreOffice |
| **P1** | Excel → PDF | 報表匯出常用 |
| **P2** | PPT → PDF | 簡報匯出 |
| **P2** | HTML → PDF | 網頁存檔，weasyprint 可支援 |
| **P3** | PDF → PDF/A | 進階存檔需求 |

---

*文件建立日期：2025-02*  
*參考：https://www.ilovepdf.com/zh-tw*
