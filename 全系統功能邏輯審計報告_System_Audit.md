# 全系統功能邏輯審計報告 (System Audit)

**對照文件**：`發票管理系統_邏輯架構說明書.md`  
**審計範圍**：邊界案例、資料一致性、台灣在地化、漏掉的功能模組  
**審計日期**：2026-01-30  
**程式碼基準**：`app.py` 及現有資料庫結構

---

## 審計摘要

| 類別 | 發現 | 嚴重度 |
|------|------|--------|
| 邊界案例 | Batch 尚未實作；OCR 失敗不影響其他張；搜尋 None 不 Crash 但有意外匹配風險；無 Batch 故無 Cascade Delete | 中～高 |
| 資料一致性 | 無 `modified_at`；無 Batch 統計連動 | 高 |
| 台灣在地化 | 統編無 8 位數驗證；稅率僅 5%，無免稅/零稅率 | 中 |
| 漏掉功能 | 導出已有（CSV/Excel/PDF）；重複上傳偵測已有 | 無缺漏（此二項） |

---

## 一、邊界案例檢查 (Edge Cases)

### 1.1 OCR 辨識失敗（返回空值）時，batch_id 產出流程是否會中斷？

**現狀**：  
- 目前程式碼**沒有** `batch_id` 與 `batches` 表，邏輯說明書中的「上傳時產生 Batch ID」尚未實作。  
- OCR 流程為：對每張圖片呼叫 `process_ocr()`；若回傳 `(None, err)`，則進入 `else` 分支：`st.error(...)`、`fail_count += 1`、`continue`，**該張不寫入任何 Invoice**，下一張繼續處理。  
- 因此：**現有流程**不會「中斷」整批處理，單張失敗不影響其他張的寫入。

**若未來依說明書實作 Batch**：  
- 建議在「開始處理多張圖片前」先 `INSERT INTO batches` 取得 `batch_id`，再在迴圈內：成功則 `INSERT INTO invoices (..., batch_id)`，失敗則不寫入該張，**不應**因單張失敗而回滾或刪除已建立的 Batch。  
- 結論：**未來實作時**應設計為「Batch 先建立，單張失敗不影響已寫入之 Invoice 與 Batch 本身」，目前無此流程故無中斷問題。

---

### 1.2 當用戶刪除一個 Batch 時，下屬所有 Invoices 是否有連帶處理（Cascade Delete）？

**現狀**：  
- 系統**沒有** Batch 概念，也沒有「刪除 Batch」的 UI 或 API。  
- 刪除功能僅針對**單筆或多筆勾選的 Invoice**（`delete_records` 為 Invoice 列表），依 `id` 或「發票號碼+日期+user_email」刪除。  
- 因此：**目前沒有** Cascade Delete，因為沒有 Batch 實體可刪。

**若未來實作 Batch**：  
- 必須在「刪除 Batch」時一併處理下屬 Invoice，二選一：  
  - **Cascade Delete**：`DELETE FROM invoices WHERE batch_id = ?` 再 `DELETE FROM batches WHERE id = ?`；或  
  - 將該 Batch 下 Invoice 的 `batch_id` 設為 NULL（軟刪除 Batch），依產品需求決定。  
- 建議在 DB 層或應用層明確定義順序，避免遺留孤兒 Invoice 或違反外鍵（若未來加 FK）。

---

### 1.3 搜尋關鍵字時，若該欄位為 None，程式碼是否會 Crash？

**現狀**：  
- 搜尋邏輯在約 2989–2998 行：  
  ```python
  def match_row(row):
      text = " ".join([
          str(row.get(col, "")) for col in ["發票號碼", "賣方名稱", "檔案名稱"]
      ]).lower()
      return search_term in text
  df = df[df.apply(match_row, axis=1)]
  ```  
- `row.get(col, "")` 在欄位缺失時回傳 `""`；若值為 `None`，`str(None)` 為 `"None"`；若為 `pd.NA`/`np.nan`，`str()` 多為 `"nan"` 或 `"<NA>"`，**不會拋錯**，故**不會 Crash**。

**潛在問題**：  
- 使用者搜尋 `"no"` 時，會匹配到 `str(None)` 的 `"None"`；搜尋 `"nan"` 可能匹配到空值轉成的字串，造成**意外匹配**。  
- **建議**：搜尋前將欄位統一正規化，例如 `str(val) if pd.notna(val) and val is not None else ""`，再參與 `" ".join(...)`，可避免「空值當成字串」被搜到。

---

## 二、數據流與一致性 (Data Integrity)

### 2.1 modified_at 的更新機制：用戶改兩次，時間是否準確紀錄？

**現狀**：  
- 資料庫 **invoices 表沒有 `modified_at` 欄位**，`save_edited_data()` 的 UPDATE 語句（約 1256–1258 行）只更新業務欄位（file_name, date, invoice_number, …），**沒有**寫入任何修改時間。  
- 因此：**無法**記錄「最後修改時間」，改兩次也無法區分先後。

**建議**（與邏輯說明書一致）：  
- 在 `invoices` 表新增 `modified_at TIMESTAMP NULL`。  
- 在 `save_edited_data()` 中，對每一筆要寫回的列執行：  
  `UPDATE invoices SET ..., modified_at = CURRENT_TIMESTAMP WHERE id = ? AND user_email = ?`  
- 這樣每次儲存都會更新為「最後一次修改時間」，準確紀錄。

---

### 2.2 是否缺少「批次統計」的自動更新？（Batch 總金額等是否連動？）

**現狀**：  
- 系統**沒有** Batch 實體，沒有「Batch 總金額」或「Batch 發票數」等彙總欄位。  
- 本期數據總覽（本月總計、稅額、發票數、缺失件數）是**每次從查詢結果即時計算**（例如 `df_month`、`df_stats`），沒有預存彙總表。

**若未來實作 Batch 與批次統計**：  
- **方案 A**：Batch 不存「總金額／張數」，每次查詢時用 `SELECT SUM(total), COUNT(*) FROM invoices WHERE batch_id = ?` 計算（與現有總覽邏輯一致），優點簡單、永遠與明細一致。  
- **方案 B**：在 `batches` 表存 `total_amount`、`invoice_count`，在「新增/更新/刪除 Invoice」時觸發 Batch 彙總更新；需注意交易一致性與漏更新風險。  
- **建議**：優先採用方案 A；若效能有需求再考慮方案 B，並在寫入/更新/刪除 Invoice 時一律更新對應 Batch 的統計欄位。

---

## 三、台灣在地化邏輯 (Localization Logic)

### 3.1 「統編」辨識邏輯：是否有處理 8 位數驗證？

**現狀**：  
- 統編（賣方統編 `seller_ubn`、公司統編 `company_ubn`）在程式中為**純文字儲存與顯示**，沒有長度或格式驗證。  
- OCR 回傳的 `seller_ubn` 直接寫入；公司統編由使用者在「設定公司資訊」輸入，未檢查是否為 8 位數字。  
- **結論**：**沒有** 8 位數驗證，也沒有台灣統編檢查碼邏輯。

**建議**：  
- 可新增輔助函數 `validate_ubn(val) -> (bool, str)`：  
  - 長度為 8、皆為數字；可選：依經濟部統編檢查碼規則驗證。  
- 在「儲存發票」（OCR 結果寫入、表格編輯儲存、公司統編儲存）時可選擇：  
  - 僅前端提示「統編應為 8 位數字」；或  
  - 後端拒絕非法統編並回傳錯誤訊息。  

---

### 3.2 「稅額」檢查機制：是否預留非 5% 稅率（免稅、零稅率）的判斷空間？

**現狀**：  
- 稅額計算在多處**固定為 5%**：  
  - 例如：`tax = round(total / 1.05 * 0.05, 2)`、`calc_tax = (total_series - (total_series / 1.05)).round(0)`、PDF/Excel 導出時「依據總計反推稅額與未稅金額（預設稅率 5%）」。  
- 沒有「稅率類型」或「免稅/零稅率」欄位，也沒有依發票類型（B2B/B2C/免稅）切換公式的邏輯。  
- **結論**：**沒有**預留非 5% 稅率或免稅/零稅率的判斷空間，一律以 5% 反推。

**建議**：  
- 在 `invoices` 表新增可選欄位，例如 `tax_type TEXT`（值如 `'5%' | '0%' | 'exempt'`），或 `tax_rate REAL`（0, 0.05 等）。  
- 在「計算稅額/未稅」的共用邏輯中，依 `tax_type`/`tax_rate` 分支：  
  - 5%：維持現有 `total/1.05` 反推；  
  - 0% / 免稅：稅額 = 0，未稅 = 總計。  
- 前端（表格/導出）可顯示稅率類型，避免所有發票都被當成 5% 計算。

---

## 四、漏掉的功能模組 (Missing Features)

### 4.1 目前是否有「導出 (Export)」功能？

**現狀**：  
- **有**。導出功能完整：  
  - **CSV**：依當前篩選結果導出（約 2663–2669 行）。  
  - **Excel**：依國稅局欄位結構導出（約 2729–2765 行），含「銷售額(未稅)」「稅額」「總計」等。  
  - **PDF**：含公司名稱/統編、累計稅額、發票筆數與明細表（約 2769–2947 行），需 `fpdf2`。  
- 導出皆以**當前登入用戶**與**當前篩選結果**為範圍，符合多用戶隔離。

**結論**：導出功能存在，可提供會計使用；若需「依 Batch 導出」或「依日期區間一鍵導出」可再擴充。

---

### 4.2 是否有處理「重複上傳」的偵測機制？（同一張發票號碼是否允許重複入帳？）

**現狀**：  
- **有**。`check_duplicate_invoice(invoice_number, date, user_email)`（約 1172–1192 行）依「發票號碼 + 日期 + user_email」檢查是否已存在。  
- **OCR 流程**（約 2044–2078 行）：每張辨識成功後先檢查重複；若為重複則 `st.warning(...)`、`duplicate_count += 1`、`continue`，**不寫入**該筆。  
- **CSV/Excel 導入**（約 2262–2271 行）：每列同樣呼叫 `check_duplicate_invoice`，重複則跳過不寫入。  
- 發票號碼為 "No"/"N/A" 時，改以「日期 + 賣方名稱 + 檔案名稱」檢查，避免同一檔案重複匯入。

**結論**：同一張發票（發票號碼+日期）不允許重複入帳；重複時跳過並提示，邏輯完整。

---

## 五、對照邏輯說明書的缺口彙總

| 說明書項目 | 目前狀態 | 審計結論 |
|------------|----------|----------|
| Batch 與 batch_id | 未實作 | 需新增 `batches` 表與 `invoices.batch_id`；上傳前建立 Batch，單張失敗不影響 Batch。 |
| 按組 / 按單張顯示 | 未實作 | 目前僅「單張」表格；搜尋為空時改「按組顯示」需新 UI 與查詢。 |
| modified_at | 未實作 | 需新增欄位並在 `save_edited_data()` 寫入 `modified_at = CURRENT_TIMESTAMP`。 |
| 搜尋欄位 None 正規化 | 未處理 | 建議搜尋前將 None/NaN 轉成空字串，避免 "no"/"nan" 意外匹配。 |
| 統編 8 位數驗證 | 未實作 | 建議新增驗證（長度 8、數字；可選檢查碼）。 |
| 稅率類型（免稅/零稅率） | 未實作 | 建議新增 `tax_type`/`tax_rate` 及分支計算邏輯。 |
| 刪除 Batch 的 Cascade | 不適用（無 Batch） | 未來實作 Batch 時必須一併實作 Cascade 或軟刪除。 |
| 導出 | 已有 CSV/Excel/PDF | 無缺漏。 |
| 重複上傳偵測 | 已有 | 無缺漏。 |

---

## 六、建議修復優先順序

1. **高**：新增 `modified_at` 欄位與 `save_edited_data()` 更新邏輯，以符合說明書並利於稽核。  
2. **高**：搜尋時將 None/NaN 正規化為空字串，避免意外匹配。  
3. **中**：若產品確定採用 Batch，依說明書實作 Batch 建立、batch_id 寫入、刪除時 Cascade（或軟刪除）。  
4. **中**：統編 8 位數驗證（至少長度與數字）。  
5. **中**：稅率類型（5%/0%/免稅）欄位與計算分支。  
6. **低**：Batch 統計若採用預存欄位，需在 Invoice 增刪改時連動更新。

完成上述審計後，可依此報告與邏輯說明書進行實作與驗收。
