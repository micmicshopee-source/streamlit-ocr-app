# Google OAuth 品牌驗證問題 — 解決方案

您遇到的錯誤與對應解法如下。

---

## 一、問題對照

| 錯誤訊息 | 原因 | 解法 |
|---------|------|------|
| 首頁網址沒有回應 | 網站無法連線或回傳非 200 | 確認服務正常、防火牆與 DNS 正確 |
| 網站未註冊給您 | 未在 Google 驗證網域擁有權 | 使用 Google Search Console 驗證 |
| 隱私權政策網址沒有回應 | 可能使用錯誤或相同網址 | 提供獨立、可正常回應的隱私政策 URL |
| 隱私權政策與首頁相同 | 兩者必須為不同 URL | 首頁與隱私政策使用不同路徑 |

---

## 二、建議 URL 結構

| 用途 | 建議 URL | 說明 |
|------|----------|------|
| 首頁 | `https://getaiinvoice.com/` | 應用主頁 |
| 隱私權政策 | `https://getaiinvoice.com/privacy` | 獨立隱私政策頁面 |

---

## 三、實作方案（擇一）

### 方案 A：Nginx 靜態頁面（推薦）

**優點**：載入快、穩定、不依賴 Streamlit，適合 Google 爬蟲。

**步驟**：

1. **建立靜態 HTML 檔**

   在專案中建立 `static/` 目錄，新增：
   - `index.html`：簡短首頁（可含「進入應用」連結）
   - `privacy.html`：隱私政策完整內容

2. **修改 Nginx 設定**

   在 `/etc/nginx/sites-available/streamlit-ocr` 中，在 `location /` 之前加入：

   ```nginx
   # 隱私政策（獨立 URL，供 Google 驗證）
   location = /privacy {
       alias /opt/streamlit_ocr_app/static/privacy.html;
       default_type text/html;
       add_header Cache-Control "public, max-age=3600";
   }

   # 首頁（可選：若希望首頁為靜態歡迎頁）
   # location = / {
   #     alias /opt/streamlit_ocr_app/static/index.html;
   #     default_type text/html;
   # }

   location / {
       proxy_pass http://127.0.0.1:8501;
       # ... 其餘 proxy 設定保持不變
   }
   ```

3. **Google Cloud Console 設定**

   - 首頁網址：`https://getaiinvoice.com/`
   - 隱私權政策網址：`https://getaiinvoice.com/privacy`

---

### 方案 B：Streamlit 多頁面

**優點**：不需改 Nginx，全部在 Streamlit 內完成。

**步驟**：

1. **建立 `pages/` 目錄**（若尚未存在）

2. **新增 `pages/Privacy_Policy.py`**

   Streamlit 會產生 URL：`https://getaiinvoice.com/Privacy_Policy`

3. **Google Cloud Console 設定**

   - 首頁網址：`https://getaiinvoice.com/`
   - 隱私權政策網址：`https://getaiinvoice.com/Privacy_Policy`

**注意**：若 Streamlit 未啟動，此 URL 會無法存取，較不適合作為驗證用隱私政策。

---

### 方案 C：首頁與隱私政策皆為靜態（最穩）

**適用**：希望首頁與隱私政策都穩定、快速回應。

**結構**：

- `https://getaiinvoice.com/` → 靜態首頁（含「進入應用」連結到 `/app`）
- `https://getaiinvoice.com/privacy` → 靜態隱私政策
- `https://getaiinvoice.com/app` → Streamlit 應用

需調整 Nginx 與 OAuth `redirect_uri` 為 `https://getaiinvoice.com/app/`。

---

## 四、網域擁有權驗證（必做）

不論採用哪個方案，都需在 **Google Search Console** 驗證網域：

1. 前往 [Google Search Console](https://search.google.com/search-console)
2. 新增資源 → 選擇「網域」→ 輸入 `getaiinvoice.com`
3. 依指示驗證（常見方式）：
   - **DNS TXT 紀錄**：在網域 DNS 新增指定 TXT
   - **HTML 檔案**：上傳指定檔案到網站根目錄
   - **HTML meta 標籤**：在首頁加入指定 meta 標籤

4. 驗證完成後，Google 會確認您擁有該網域。

---

## 五、檢查清單

- [ ] 網站可從外網存取：`curl -I https://getaiinvoice.com/` 回傳 200
- [ ] 隱私政策 URL 可存取：`curl -I https://getaiinvoice.com/privacy` 回傳 200
- [ ] 首頁與隱私政策為不同 URL
- [ ] 在 Google Search Console 完成網域驗證
- [ ] Google Cloud Console OAuth 設定：
  - 授權網域：`getaiinvoice.com`
  - 首頁：`https://getaiinvoice.com/`
  - 隱私權政策：`https://getaiinvoice.com/privacy`（或 `/Privacy_Policy`）

---

## 六、建議執行順序

1. **先確認服務與 DNS**：`https://getaiinvoice.com/` 可正常開啟
2. **實作隱私政策頁面**：採用方案 A 或 B
3. **驗證網域**：在 Google Search Console 完成驗證
4. **更新 OAuth 設定**：在 Google Cloud Console 填寫正確首頁與隱私政策 URL
5. **重新提交品牌審核**

---

若採用 **方案 A**，可再提供 `static/privacy.html` 與 Nginx 完整設定範例。
