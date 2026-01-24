import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import json
import io

# --- 0. AI 模型設定 ---
# 用戶提供的 API Key
API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error(f"API Key 設定失敗: {e}")

def process_image_with_gemini(uploaded_file):
    """呼叫 Gemini API 進行辨識"""
    try:
        # 讀取圖片
        image = Image.open(uploaded_file)
        
        # 定義 Prompt
        prompt = """
        請分析這張發票或收據圖片，並輸出純 JSON 格式資料（不要 Markdown）。
        需包含以下欄位：
        - date: 日期 (格式 YYYY-MM-DD，民國年請轉西元)
        - invoice_no: 發票號碼 (若無則填 N/A)
        - seller_name: 賣方名稱/店名
        - seller_ubn: 賣方統編 (若無則填 N/A)
        - amount: 銷售額 (未稅金額，數字)
        - tax: 稅額 (數字)
        - total: 總金額 (數字)
        - category: 支出類別建議 (如：餐飲、交通、辦公用品、住宿、其他)
        - status: 若資訊清晰完整回傳 "✅ 正常"，若模糊或有缺漏回傳 "⚠️ 需檢查"
        
        若無法辨識某些欄位，請填入預設值 (0 或 "")。
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt, image])
        
        # 解析回傳的文字
        text = response.text.strip()
        # 去除可能的 markdown 標記
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        return data
        
    except Exception as e:
        st.error(f"辨識錯誤 ({uploaded_file.name}): {str(e)}")
        return None

# --- 1. 資料庫安全初始化 (解決 disk I/O error) ---
def get_db_connection():
    db_path = os.path.join(os.getcwd(), 'invoices.db')
    try:
        # 嘗試建立實體檔案連線
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return conn
    except sqlite3.OperationalError:
        # 如果磁碟無法寫入，改用記憶體模式 (確保用戶不報錯)
        return sqlite3.connect(':memory:', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            invoice_no TEXT,
            seller_name TEXT,
            seller_ubn TEXT,
            amount REAL,
            tax REAL,
            total REAL,
            category TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    return conn

# --- 2. 頁面配置 ---
st.set_page_config(layout="wide", page_title="AI 報帳小秘笈")
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# 初始化資料庫與 Session State
conn = init_db()
if 'temp_data' not in st.session_state: st.session_state.temp_data = []

# --- 3. UI 佈局 ---
col_left, col_mid, col_right = st.columns([1, 3, 1])

# --- 左欄：上傳與操作 ---
with col_left:
    st.header("📤 上傳發票")
    uploaded_files = st.file_uploader("支援 JPG, PNG, WEBP", type=["jpg", "png", "jpeg", "webp"], accept_multiple_files=True)
    
    if st.button("開始 AI 辨識 ⚡", use_container_width=True, type="primary"):
        if not uploaded_files:
            st.warning("請先上傳圖片！")
        else:
            with st.spinner("AI 正在努力閱讀您的發票..."):
                progress_bar = st.progress(0)
                new_results = []
                
                for idx, file in enumerate(uploaded_files):
                    result = process_image_with_gemini(file)
                    if result:
                        new_results.append(result)
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                
                if new_results:
                    st.session_state.temp_data.extend(new_results)
                    st.success(f"成功辨識 {len(new_results)} 張發票！")
                else:
                    st.error("辨識失敗，請重試。")

# --- 中欄：數據報表 ---
with col_mid:
    mode = st.radio("檢視模式", ["🆕 當前辨識", "📜 歷史紀錄"], horizontal=True)
    
    if mode == "🆕 當前辨識":
        st.subheader("待確認數據 (可直接編輯)")
        if st.session_state.temp_data:
            # 顯示可編輯的表格
            df_temp = pd.DataFrame(st.session_state.temp_data)
            
            # 調整欄位順序
            cols_order = ["date", "invoice_no", "seller_name", "total", "tax", "category", "status", "seller_ubn", "amount"]
            # 確保欄位存在
            for c in cols_order:
                if c not in df_temp.columns: df_temp[c] = ""
            df_temp = df_temp[cols_order]
            
            edited_df = st.data_editor(df_temp, num_rows="dynamic", use_container_width=True)
            
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if st.button("💾 確認並保存到資料庫", use_container_width=True, type="primary"):
                    try:
                        edited_df.to_sql('invoices', conn, if_exists='append', index=False)
                        st.toast("✅ 已成功存入資料庫！")
                        st.session_state.temp_data = [] # 清空暫存
                        st.rerun()
                    except Exception as e:
                        st.error(f"儲存失敗: {e}")
            with col_act2:
                if st.button("🗑️ 清除暫存", use_container_width=True):
                    st.session_state.temp_data = []
                    st.rerun()
        else:
            st.info("👈 請從左側上傳圖片並點擊「開始辨識」")
            
    else:
        st.subheader("歷史發票檢索")
        try:
            df_history = pd.read_sql('SELECT * FROM invoices ORDER BY id DESC', conn)
            
            # 簡單篩選器
            col_s1, col_s2 = st.columns([2, 1])
            with col_s1:
                search = st.text_input("🔍 搜尋賣方名稱、統編或備註")
            with col_s2:
                if st.button("🗑️ 刪除全部歷史資料", use_container_width=True):
                    conn.execute("DELETE FROM invoices")
                    conn.commit()
                    st.rerun()

            if not df_history.empty:
                if search:
                    mask = df_history.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                    df_history = df_history[mask]
                
                st.dataframe(df_history, use_container_width=True, height=500)
            else:
                st.write("目前資料庫中沒有資料。")
        except Exception as e:
            st.error(f"讀取資料庫錯誤: {e}")

# --- 右欄：統計與導出 ---
with col_right:
    st.header("📊 數據統計")
    # 從資料庫抓取最新總額
    try:
        all_data = pd.read_sql('SELECT * FROM invoices', conn)
        total_sum = all_data['total'].sum() if not all_data.empty else 0
        count = len(all_data)
        
        # 本月支出
        current_month = datetime.now().strftime("%Y-%m")
        if not all_data.empty and 'date' in all_data.columns:
            # 簡單過濾日期字串包含本月的
            month_data = all_data[all_data['date'].astype(str).str.contains(current_month, na=False)]
            month_sum = month_data['total'].sum()
        else:
            month_sum = 0
            
    except:
        all_data = pd.DataFrame()
        total_sum = 0
        month_sum = 0
        count = 0
    
    st.metric("累計總報帳金額", f"${total_sum:,.0f}")
    st.metric("本月支出 (預估)", f"${month_sum:,.0f}")
    st.metric("發票總張數", count)
    
    st.divider()
    st.subheader("📤 導出報表")
    if not all_data.empty:
        csv = all_data.to_csv(index=False).encode('utf-8-sig')
        st.download_button("下載 Excel (CSV)", data=csv, file_name=f"invoice_report_{datetime.now().strftime('%Y%m%d')}.csv", use_container_width=True)
