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

複製 `.streamlit/secrets.toml.example` 為 `.streamlit/secrets.toml` 並填入實際值。必填／常用項：

| 項目 | 說明 |
|------|------|
| `GEMINI_API_KEY` | 發票 OCR、AI 小助理（對獎／CSV／報表可不設） |
| `CONTACT_EMAIL` | 聯絡信箱（隱私政策、反饋收件） |
| `SMTP_APP_PASSWORD` | Gmail 應用程式密碼；設定後「反饋意見」可從站內直接寄信至 `CONTACT_EMAIL` |

Gmail 應用程式密碼：Google 帳戶 → 安全性 → 兩步驟驗證 → 應用程式密碼。

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
