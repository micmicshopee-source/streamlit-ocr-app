# 發票報帳小幫手

上傳辨識・對獎・報表導出 — 使用 Streamlit 與 Google Gemini API。

---

## 功能

- **📷 上傳發票**：上傳發票圖片，AI OCR 辨識（Gemini）
- **📥 CSV 導入**：批次導入發票資料
- **🎫 發票對獎**：財政部開獎號碼自動對獎
- **📊 報表導出**：CSV、Excel、PDF 報表
- **🤖 AI 小助理**：發票相關問答（需 Gemini API 金鑰）

---

## 安裝與部署

### 本機開發

```bash
pip install -r requirements.txt
streamlit run app.py
```

### 設定

建立 `.streamlit/secrets.toml`：

```toml
GEMINI_API_KEY = "你的Gemini金鑰"
```

發票 OCR 與 AI 小助理需此金鑰；對獎、CSV 導入與報表導出可不設定。

---

## 部署指南

- **VPS 部署**：見 `部署到VPS指南.md`
- **Docker**：`docker compose -f docker-compose.prod.yml up -d --build`

---

## 技術棧

- Streamlit、Google Generative AI (Gemini)
- Pandas、OpenPyXL、FPDF2、SQLite

---

## 授權

此專案僅供學習和個人使用。
