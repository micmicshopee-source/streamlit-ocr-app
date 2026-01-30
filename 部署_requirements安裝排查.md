# Streamlit「Error installing requirements」排查說明

## ⚠️ 若 Streamlit Cloud 使用 Python 3.13 — 請先改版本（最常見原因）

**Python 3.13 太新，許多套件尚無預編譯輪子，雲端建置會失敗。**

### 正確做法（在 Streamlit Cloud 上）

1. **刪除現有 App**  
   - 進入你的 App → **Manage app** → **Delete app**（先記下 repo、branch、entrypoint、Secrets、自訂網域等）。
2. **重新部署**  
   - 從同一個 repo 再部署一次。
3. **在部署時選 Python 3.11 或 3.12**  
   - 在部署頁面點 **Advanced settings**（進階設定）。  
   - 在 **Python version** 下拉選單選擇 **3.11** 或 **3.12**（不要選 3.13）。  
   - 儲存後再按 **Deploy**。

官方說明：部署後無法再改 Python 版本，只能「刪除 App → 重新部署」時在 Advanced settings 選擇版本。  
本專案已加入 `runtime.txt`（內容為 `python-3.11.9`）作為建議版本；若平台有讀取此檔，會優先使用 3.11。

---

## 目前已做的修正

- **requirements.txt**：已移除 xhtml2pdf、bcrypt，僅保留 fpdf2 與常用依賴，減少編譯與相容性問題。
- **runtime.txt**：已加入 `python-3.11.9`，建議雲端使用 Python 3.11。

---

## 如何查看「真正的錯誤」

Streamlit 只會顯示「Error installing requirements」，具體原因在**建置日誌**裡：

1. **Streamlit Cloud**：App → **Manage app** → **Logs** / **Build logs**。  
2. **本機**：在專案目錄執行 `pip install -r requirements.txt`，把完整錯誤貼出來。

---

## 常見錯誤與對應方式

| 錯誤類型 | 可能原因 | 建議處理 |
|----------|----------|----------|
| Python 3.13 / 找不到輪子 | 3.13 太新，許多套件尚無 wheel | 在 Advanced settings 改選 **Python 3.11 或 3.12** 後重新部署。 |
| `No matching distribution` | 套件名稱錯、或該 Python 版本無輪子 | 檢查套件名、或指定有輪子的版本。 |
| `error: command 'gcc' failed` | C 擴展需編譯、缺少建置工具 | 已移除 bcrypt；若未來加回，可搭配 `packages.txt`（build-essential、python3-dev）。 |
| `Could not find a version that satisfies` | 依賴版本衝突 | 放寬或固定版本（例如 `pandas>=2.0,<3`）。 |

修改後記得**重新部署**，並查看 **Build logs** 確認是否還有新錯誤。
