# 圖片 OCR 辨識工具

這是一個使用 Streamlit 和 Google Gemini API 開發的圖片 OCR（光學字元辨識）工具。

## 功能特色

- 📤 支援多種圖片格式上傳（PNG, JPG, JPEG, GIF, BMP, WEBP）
- 🖼️ 即時預覽上傳的圖片
- 🔍 使用 Google Gemini API 進行 OCR 文字辨識
- 📝 清晰顯示辨識結果
- 🎨 現代化的使用者介面

## 安裝步驟

1. 確保已安裝 Python 3.8 或更高版本

2. 安裝所需的套件：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 啟動應用程式：
```bash
streamlit run app.py
```

2. 在瀏覽器中開啟顯示的網址（通常是 http://localhost:8501）

3. 在側邊欄輸入您的 Google Gemini API Key

4. 上傳要辨識的圖片

5. 點擊「開始 OCR 辨識」按鈕

6. 查看辨識結果

## 取得 Gemini API Key

1. 前往 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 登入您的 Google 帳號
3. 建立新的 API Key
4. 複製 API Key 並在應用程式中使用

## 注意事項

- 請妥善保管您的 API Key，不要分享給他人
- API 使用可能會產生費用，請參考 Google 的定價方案
- 建議在穩定的網路環境下使用

## 技術棧

- **Streamlit**: Web 應用程式框架
- **Google Generative AI**: Gemini API 客戶端
- **Pillow (PIL)**: 圖片處理

## 授權

此專案僅供學習和個人使用。
