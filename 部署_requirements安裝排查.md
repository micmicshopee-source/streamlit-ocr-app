# Streamlit「Error installing requirements」排查說明

## 已做的修正（可直接重新部署）

1. **requirements.txt**
   - **xhtml2pdf**：`>=0.2.13` → `>=0.2.14`  
     - 0.2.13 在 Linux 上常因 pycairo 編譯失敗；0.2.14+ 已將 pycairo 改為選用，雲端安裝較穩定。
   - **bcrypt**：加上上限 `>=4.0.0,<5`，避免 pip 選到不相容版本。

2. **packages.txt（新增）**
   - 若雲端環境沒有預編譯輪子，bcrypt 會從原始碼編譯，需要系統建置工具。
   - 已加入：`build-essential`、`python3-dev`，供編譯 C 擴展使用。
   - 若你確認不需要編譯（例如都有輪子），可刪除或清空此檔。

## 如何查看「真正的錯誤」

Streamlit 只會顯示「Error installing requirements」，具體原因在**建置日誌**裡：

1. 在 **Streamlit Cloud** 上：  
   - 打開你的 App → **Manage app** → **Logs** / **Build logs**（或類似名稱）。
2. 在 **終端機**：  
   - 到專案目錄執行：  
     `pip install -r requirements.txt`  
   - 把完整錯誤貼出來，才能對症下藥。

## 常見錯誤與對應方式

| 錯誤類型 | 可能原因 | 建議處理 |
|----------|----------|----------|
| `No matching distribution` / 找不到某套件 | 套件名稱打錯、或該 Python 版本沒有輪子 | 檢查套件名、或改指定有輪子的版本（例如 `bcrypt==4.1.2`）。 |
| `error: command 'gcc' failed` / 編譯失敗 | 缺少編譯工具或 C 擴展編譯失敗 | 使用本專案已加入的 `packages.txt`（build-essential、python3-dev）。 |
| `Could not find a version that satisfies` | 依賴版本互相衝突 | 放寬或固定版本（例如 `pandas>=2.0,<3`），或暫時移除有問題的那一行做測試。 |
| xhtml2pdf / reportlab 相關錯誤 | 舊版 xhtml2pdf 或 reportlab 不相容 | 已改為 `xhtml2pdf>=0.2.14`；若仍失敗，可暫時註解該行，App 會改用 fpdf2 導出 PDF。 |

## 若仍失敗：暫時精簡依賴

可先註解掉**非必要**的套件，確認是否能通過安裝，再逐個加回：

- **xhtml2pdf**：註解後發票 PDF 會改用 fpdf2（功能仍可用）。
- **bcrypt**：註解後登入會改用 SHA256（較不理想，僅供排查用）。

修改後記得**重新部署**並再次查看 **Build logs** 以確認新錯誤訊息。
