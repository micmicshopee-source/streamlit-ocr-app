# 上班族小工具

發票報帳・辦公小幫手 — 使用 Streamlit 與 Google Gemini API 開發。

---

## 功能特色

### 📑 發票報帳小秘笈
- 上傳發票圖片，AI OCR 辨識（Gemini）
- CSV 批次導入
- 發票對獎（財政部開獎號碼）
- 導出 CSV、Excel、PDF 報表

### 📄 PDF 萬能轉換工具
- PDF → Excel（表格提取）
- PDF → PPT（每頁轉圖片）
- PDF → 圖片 ZIP（JPG/PNG）
- PDF → Word（含 AI OCR 掃描檔）

### 📅 AI 會議精華
- 貼上逐字稿或上傳錄音
- AI 產出結論與待辦事項

### ⚖️ AI 合約比對
- 上傳兩份合約（PDF/Word/文字）
- AI 標示差異與重點

### 🛡️ Google 登錄診斷工具
- 檢查 OAuth 設定是否正確

---

## 安裝與部署

### 本機開發

```bash
pip install -r requirements.txt
# 伺服器完整版：pip install -r requirements-server.txt

streamlit run app.py
```

### 系統依賴（PDF 轉換）

- **poppler-utils**：`sudo apt install poppler-utils`（Ubuntu/Debian）

### 設定

建立 `.streamlit/secrets.toml`：

```toml
GEMINI_API_KEY = "你的Gemini金鑰"
```

### AI PDF→Word 高品質版面還原（指令列 Prototype）

使用 Gemini Vision 解析 PDF 版面並重建可編輯 Word（標題、段落、表格、圖片皆可編輯）：

```bash
# 需先設定 GEMINI_API_KEY（環境變數或 .streamlit/secrets.toml）
python ai_pdf_to_word_prototype.py "路徑/檔案.pdf" [輸出.docx路徑]
```

未指定輸出路徑時，會在同目錄產生 `檔名_ai_layout.docx`。依賴：`pdf2image`、`python-docx`、`Pillow`、`pymupdf`、`requests`；系統需安裝 poppler。

---

## 部署指南

- **VPS 部署**：見 `部署到VPS指南.md`
- **上線檢查**：見 `上線前整體檢查清單.md`
- **Docker**：`docker compose -f docker-compose.prod.yml up -d --build`

---

## 技術棧

- Streamlit、Google Generative AI (Gemini)
- Pandas、OpenPyXL、FPDF2、PyMuPDF
- pdfplumber、python-pptx、pdf2image、pdf2docx

---

## 授權

此專案僅供學習和個人使用。
