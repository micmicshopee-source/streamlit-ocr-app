# Google 登入測試說明

**您的 Google Client ID 已寫入** `.streamlit/secrets.toml`，並已通過本機測試（授權 URL 可正確組裝）。

---

## 1. 已完成的設定

- **GOOGLE_CLIENT_ID**：`99650804426-h68n12ue8ql66tbfnehm94mmdp17nmil.apps.googleusercontent.com`（已寫入 secrets.toml）
- **授權 URL 測試**：執行 `python test_google_oauth.py` 可驗證 Client ID 是否被讀取、授權網址是否正確。

---

## 2. 您還需要做的兩件事

### ① 在 Google Cloud Console 設定「已授權的重新導向 URI」

1. 開啟 [Google Cloud Console](https://console.cloud.google.com/) → 選取您的專案。
2. 左側 **「API 和服務」** → **「憑證」**。
3. 點選您的 **OAuth 2.0 用戶端 ID**（對應上述 Client ID）。
4. 在 **「已授權的重新導向 URI」** 中新增：
   - 本機測試：`http://localhost:8501/`
   - 若日後有正式網域：`https://您的網域/`（須與本應用實際網址一致）
5. 儲存。

**重要**：網址必須與本應用實際使用的回調網址完全一致（含尾端 `/`、http/https）。

### ② 在本機填入「用戶端密鑰」（Client Secret）

1. 在同一個 OAuth 用戶端畫面，複製 **「用戶端密鑰」**（Client Secret）。
2. 開啟 `.streamlit/secrets.toml`，新增或修改為：

```toml
GOOGLE_CLIENT_SECRET = "您複製的密鑰"
```

3. 儲存後**不要**將此檔案提交到 Git（應已在 .gitignore）。

---

## 3. 如何測試完整登入流程

1. 確認已完成上述 ①、②。
2. 在專案目錄執行：
   ```bash
   streamlit run app.py
   ```
3. 瀏覽器開啟 `http://localhost:8501`。
4. 在登入頁點 **「🔵 Google」**。
5. 點 **「以 Google 登入」** 連結，應會導向 Google 授權頁。
6. 選擇 Google 帳號並同意授權後，應會導回本應用並完成登入。

若未設定 `GOOGLE_CLIENT_SECRET`，授權後導回時會出現「無法取得存取權杖」或「未設定 Google 登入參數」；補上密鑰後即可完成登入。
