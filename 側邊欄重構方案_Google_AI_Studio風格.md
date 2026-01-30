# 側邊欄重構方案 — 參考 Google AI Studio 樣式

**目標**：將現有側邊欄改為簡約、群組化、科技感佈局，並固定底部區塊與用戶資訊。

---

## 一、現狀簡述

- **目前**：`st.sidebar` 內有標題「🛠️ 小工具」、`st.radio` 四項工具、分隔線、用戶 Email 說明、登出按鈕、進階設定 Expander（API Key、模型）。
- **問題**：按鈕感重、層級不明、底部與進階設定未固定、視覺未統一為深色科技風。

---

## 二、重構結構

### 2.1 頂部品牌區 (Header)

| 項目 | 說明 | 實作建議 |
|------|------|----------|
| 主標題 / Logo | 側邊欄最上方，大標題或品牌名 | `st.sidebar.markdown("# 🚀 AI 智慧管家")` 或 `st.sidebar.title("AI 智慧管家")`，可加小圖示 |
| 導航返回 | 緊接標題下方，返回「首頁／儀表板」 | `st.sidebar.markdown('<a href="?">‹ 儀表板</a>', unsafe_allow_html=True)` 或 `st.sidebar.page_link`（若有多頁） |

- **注意**：若本應用為單頁多工具切換，可將「‹ 儀表板」改為「‹ 返回首頁」或預設選中「發票報帳」時不顯示返回，依產品需求調整。

### 2.2 選單群組化 (Menu Grouping)

- **原則**：不以一堆按鈕呈現，改為**簡約文字導航**，選中項有**灰色圓角背景**（Active State）。

| 區塊名稱 | 對應本專案內容 | 實作方式 |
|----------|----------------|----------|
| 主要功能 | 發票報帳、AI 合約比對、AI 客服小秘、AI 會議精華 | 使用 `st.sidebar.radio(..., label_visibility="collapsed")` 或自訂 HTML/CSS 列表 |
| 選中樣式 | 當前選中項目 | 灰色圓角背景（如 `background: rgba(255,255,255,0.1); border-radius: 8px;`）、文字白色 |

- **對照 Google AI Studio**：其為「API 金鑰、專案、使用情況和計費、日誌和資料集」；本專案對應為「發票報帳、合約比對、客服小秘、會議精華」等小工具，結構一致為「單選導航 + 選中態」。

**實作選項**：

- **A. 使用 `st.sidebar.radio`**  
  - 透過 CSS 鎖定 `[data-testid="stSidebar"] .stRadio div` 選中項，加上圓角與背景色。
- **B. 自訂 HTML + `st.markdown`**  
  - 用 `st.markdown` 輸出 `<ul>`／`<div>` 列表，每項帶 `data-tool` 或 `data-page`，點擊透過 `st.query_params` 或 `session_state` 切換工具，再以 CSS 做選中樣式。

建議先採用 **A**，改動小、易維護。

### 2.3 底部固定欄 (Sticky Bottom)

| 項目 | 說明 | 實作建議 |
|------|------|----------|
| 固定區塊 | 設定、取得 API 金鑰、用戶資訊 固定在側邊欄底部 | 用 `st.sidebar.container()` 或一組 `st.sidebar.markdown`／`st.sidebar.button` 包成一個區塊，外層用 CSS `position: sticky; bottom: 0;` 或 `flex + margin-top: auto` 壓在底部 |
| 用戶頭像 | 圓形字母圖示（如橘底白字 'm'）+ 用戶 Email | 頭像：`st.markdown` 寫 `<div class="sidebar-avatar">m</div>`，Email 用 `st.caption` 或同區塊內文字，可截斷為 `micmicshopee@gmail...` |
| 取得 API 金鑰 | 導向設定或外部連結 | `st.sidebar.link_button("取得 API 金鑰", url=...)` 或按鈕設 `use_container_width=True`，樣式改為無粗框（見下方 CSS） |
| 趣味開關 | 如「下雪吧 ❄️」 | `st.sidebar.toggle("下雪吧 ❄️", key="snow_toggle")` 或 checkbox，用於前端下雪動畫等（需另接 JS/CSS 或 Streamlit 組件） |

- **結構建議**：  
  - 上方：品牌區 + 導航返回 + 主選單（radio 或自訂列表）。  
  - 中間：可留空或放次要說明，以 `flex-grow` 或 spacer 撐開。  
  - 底部：`st.sidebar.markdown("---")` 後，依序：設定（連結或 Expander 入口）、取得 API 金鑰、下雪開關、用戶頭像 + Email、登出（無框樣式）。

### 2.4 視覺樣式 (CSS Customization)

| 項目 | 說明 | CSS 建議 |
|------|------|----------|
| 側邊欄背景 | 深黑 | `[data-testid="stSidebar"] { background-color: #1e1e1e !important; }`（與現有 #1E1E1E 一致可保留） |
| 字體顏色 | 預設淺灰、選中白色 | 側邊欄內文字 `color: #b0b0b0`；選中項 `color: #fff` |
| 選中項背景 | 灰色圓角塊 | 如 `.stRadio label[data-checked="true"]` 或對應選中元素 `background: rgba(255,255,255,0.1); border-radius: 8px; padding: 8px 12px;` |
| 按鈕 | 無粗框、字體排版感 | `[data-testid="stSidebar"] button { border: none !important; box-shadow: none !important; background: transparent !important; }`，hover 可略變色 |
| 連結／返回 | 無底線、淺灰 | `[data-testid="stSidebar"] a { color: #b0b0b0; text-decoration: none; }` |

- **字體**：可統一為系統無襯線或微軟正黑體，與主站一致。

---

## 三、實作順序建議

1. **CSS 先行**  
   - 在 `theme_m3_responsive.css`（或專用 sidebar CSS）中：  
     - 側邊欄背景 #1e1e1e、字色淺灰、選中項白字+灰底圓角、按鈕無框。
2. **頂部品牌區**  
   - 將現有 `st.sidebar.title("🛠️ 小工具")` 改為大標題 + 「‹ 儀表板」返回。
3. **選單群組化**  
   - 維持 `st.sidebar.radio` 四項工具，或改為自訂 HTML 列表；確保選中態有對應 class／屬性供 CSS 使用。
4. **底部固定**  
   - 將「進階設定」入口、取得 API 金鑰、用戶頭像+Email、登出、下雪開關移到同一區塊，並用 CSS 做 sticky bottom。
5. **用戶頭像**  
   - 用 Email 首字（如 `m`）做圓形頭像，橘底白字，與 Email 並排。
6. **趣味開關**  
   - 加入「下雪吧 ❄️」toggle，若要做實際下雪效果再接前端資源。

---

## 四、與現有程式對應

- **現有**：`with st.sidebar:` → `st.title`、`st.radio`、`st.markdown("---")`、`st.caption`（Email）、`st.button`（登出）、`st.expander`（進階設定）。
- **重構後**：  
  - 頂部：大標題 + 返回連結。  
  - 主體：radio（或自訂選單）四項，選中態由 CSS 控制。  
  - 底部：分隔線 + 設定／API 金鑰／下雪開關 + 頭像+Email + 登出；進階設定可保留在 Expander 或改為「設定」連結展開。  
  - 所有按鈕在側邊欄內改為無框樣式。

---

## 五、驗收要點

- [ ] 側邊欄背景為深黑 #1e1e1e，字體為淺灰、選中為白。  
- [ ] 頂部有明顯品牌標題與「‹ 儀表板」類返回。  
- [ ] 主選單為簡約文字導航，選中項有灰色圓角背景。  
- [ ] 底部固定：設定、取得 API 金鑰、用戶頭像+Email、登出、下雪開關。  
- [ ] 按鈕無粗框、整體為字體排版科技感。  
- [ ] 用戶頭像為圓形字母（如橘底白字），Email 可截斷顯示。

此方案可直接作為開發規格，依「實作順序建議」分步改動 `app.py` 與 `theme_m3_responsive.css`（或專用 sidebar 樣式檔）。
