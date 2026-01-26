import streamlit as st
import google.generativeai as genai
from PIL import Image, ImageEnhance
import pandas as pd
import json
import os
import io
import time
import base64
import requests
import altair as alt
import sqlite3
from datetime import datetime, timedelta
import hashlib
import shutil

# PDF 生成庫 (使用 fpdf2)
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. 系統佈局與初始化 ---
st.set_page_config(page_title="發票報帳小秘笈", page_icon="🧾", layout="wide")

# 添加CSS確保頁面有滾動條並優化樣式（參考Google AI Studio深色主題）
st.markdown("""
<style>
    /* 深色主題背景 - 參考Google AI Studio */
    .stApp {
        background-color: #1F1F1F !important;
        color: #FFFFFF !important;
    }
    
    /* 側邊欄固定，不隨主內容滾動 */
    [data-testid="stSidebar"] {
        background-color: #1A1A1A !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    
    /* 主內容區域可以獨立滾動 */
    .main {
        background-color: #1F1F1F !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    
    .main .block-container {
        max-width: 100% !important;
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        background-color: #1F1F1F !important;
    }
    
    /* 減少標題和內容之間的間距 */
    h1, h2, h3 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* 減少容器之間的間距 */
    [data-testid="stVerticalBlock"] > [data-testid="element-container"] {
        margin-bottom: 0.5rem !important;
    }
    
    /* 圖表卡片樣式 - 參考圖片 */
    .chart-card {
        background-color: #2F2F2F !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    
    /* 減少分隔線的間距 */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* 確保垂直容器可以正常顯示 */
    [data-testid="stVerticalBlock"] {
        overflow: visible !important;
    }
    
    /* 確保Streamlit的根容器可以正常顯示 */
    section[data-testid="stAppViewContainer"] {
        overflow: visible !important;
    }
    
    /* 標題文字顏色 */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
    }
    
    /* 文字顏色 */
    p, span, div, label {
        color: #E0E0E0 !important;
    }
    
    /* 主要按鈕樣式 - 深灰色背景，白色文字，圓角 */
    .stButton > button[kind="primary"] {
        background-color: #3F3F3F !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
        box-shadow: none !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #4F4F4F !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
    }
    
    /* 次要按鈕樣式 */
    .stButton > button:not([kind="primary"]) {
        background-color: #3F3F3F !important;
        color: #FFFFFF !important;
        border: 1px solid #5F5F5F !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        transition: all 0.2s !important;
    }
    
    .stButton > button:not([kind="primary"]):hover {
        background-color: #4F4F4F !important;
        border-color: #6F6F6F !important;
    }
    
    /* 選擇框樣式 - 深色主題 */
    .stSelectbox > div > div {
        background-color: #3F3F3F !important;
        color: #FFFFFF !important;
        border: 1px solid #5F5F5F !important;
        border-radius: 8px !important;
    }
    
    .stSelectbox label {
        color: #E0E0E0 !important;
    }
    
    /* 單選按鈕樣式 - 切換按鈕 */
    .stRadio > div {
        background-color: transparent !important;
    }
    
    .stRadio > div > label {
        color: #FFFFFF !important;
        padding: 6px 12px !important;
        border-radius: 20px !important;
        transition: all 0.2s !important;
    }
    
    .stRadio > div > label:hover {
        background-color: #2F2F2F !important;
    }
    
    /* 選中的單選按鈕 */
    .stRadio > div > label[data-baseweb="radio"] {
        background-color: #3F3F3F !important;
    }
    
    /* 文本輸入框樣式 */
    .stTextInput > div > div > input {
        background-color: #2F2F2F !important;
        color: #FFFFFF !important;
        border: 1px solid #5F5F5F !important;
        border-radius: 8px !important;
    }
    
    .stTextInput label {
        color: #E0E0E0 !important;
    }
    
    /* 表格樣式 - 深色主題 */
    .stDataFrame {
        border-radius: 8px;
        overflow: auto;
        background-color: #2F2F2F !important;
    }
    
    .stDataFrame > div {
        overflow-x: auto !important;
        overflow-y: auto !important;
        background-color: #2F2F2F !important;
    }
    
    /* 表格頭部樣式 - 優化字體大小 */
    .stDataFrame thead th {
        background-color: #2F2F2F !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
        border-bottom: 1px solid #5F5F5F !important;
        padding: 14px 18px !important;
        position: sticky;
        top: 0;
        z-index: 10;
        font-size: 16px !important;  /* 增大表頭字體 */
    }
    
    /* 表格行樣式 */
    .stDataFrame tbody tr {
        border-bottom: 1px solid #3F3F3F !important;
        background-color: #2F2F2F !important;
        transition: background-color 0.2s;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: #3F3F3F !important;
    }
    
    /* 表格單元格樣式 - 優化字體大小 */
    .stDataFrame td {
        padding: 14px 18px !important;
        color: #E0E0E0 !important;
        font-size: 15px !important;  /* 增大表格文字 */
        line-height: 1.5 !important;
    }
    
    /* 數據編輯器字體大小 - 優化 */
    [data-testid="stDataEditor"] {
        font-size: 15px !important;
    }
    
    [data-testid="stDataEditor"] td,
    [data-testid="stDataEditor"] th {
        font-size: 15px !important;  /* 增大編輯器文字 */
        padding: 12px 16px !important;
    }
    
    [data-testid="stDataEditor"] input,
    [data-testid="stDataEditor"] select,
    [data-testid="stDataEditor"] textarea {
        font-size: 15px !important;  /* 增大輸入框文字 */
        padding: 8px 12px !important;
    }
    
    [data-testid="stDataEditor"] label {
        font-size: 15px !important;
    }
    
    /* 表格中的文字元素 */
    .stDataFrame,
    .stDataFrame * {
        font-size: 15px !important;
    }
    
    /* 確保表格容器內所有文字都使用較大字體 */
    [data-testid="stDataFrame"] * {
        font-size: 15px !important;
    }
    
    [data-testid="stDataEditor"] * {
        font-size: 15px !important;
    }
    
    /* 數據編輯器樣式 */
    [data-testid="stDataEditor"] {
        border-radius: 8px;
        overflow: auto;
        background-color: #2F2F2F !important;
    }
    
    [data-testid="stDataEditor"] > div {
        overflow-x: auto !important;
        overflow-y: auto !important;
        max-height: 600px;
        background-color: #2F2F2F !important;
    }
    
    /* 側邊欄樣式 - 已在上面定義為固定 */
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #E0E0E0 !important;
    }
    
    /* 自定義滾動條樣式 - 深色主題 */
    ::-webkit-scrollbar {
        width: 12px !important;
        height: 12px !important;
    }
    
    ::-webkit-scrollbar-track {
        background: #2F2F2F !important;
        border-radius: 6px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #5F5F5F !important;
        border-radius: 6px;
        border: 2px solid #2F2F2F;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #7F7F7F !important;
    }
    
    /* 強制顯示滾動條 */
    html {
        overflow-y: scroll !important;
    }
    
    body {
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    
    /* 確保所有主要容器都可以滾動 */
    div[data-testid="stAppViewContainer"] {
        overflow-y: auto !important;
        height: auto !important;
        min-height: 100vh;
    }
    
    /* 指標卡片樣式 */
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: 500;
    }
    
    [data-testid="stMetricLabel"] {
        color: #B0B0B0 !important;
    }
    
    /* 信息框樣式 */
    .stInfo {
        background-color: #2F2F2F !important;
        border-left: 4px solid #4285F4 !important;
    }
    
    .stSuccess {
        background-color: #2F2F2F !important;
        border-left: 4px solid #34A853 !important;
    }
    
    .stWarning {
        background-color: #2F2F2F !important;
        border-left: 4px solid #FBBC04 !important;
    }
    
    .stError {
        background-color: #2F2F2F !important;
        border-left: 4px solid #EA4335 !important;
    }
    
    /* 標籤頁樣式 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #2F2F2F !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #E0E0E0 !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #FFFFFF !important;
        border-bottom: 2px solid #4285F4 !important;
    }
    
    /* 對話框樣式 */
    [data-baseweb="modal"] {
        background-color: #2F2F2F !important;
    }
    
    /* 分隔線樣式 */
    hr {
        border-color: #3F3F3F !important;
    }
</style>
""", unsafe_allow_html=True)

if "db_error" not in st.session_state: st.session_state.db_error = None
if "db_path_mode" not in st.session_state: st.session_state.db_path_mode = "💾 本地磁碟"
if "use_memory_mode" not in st.session_state: st.session_state.use_memory_mode = False
if "local_invoices" not in st.session_state: st.session_state.local_invoices = []
if "image_storage_dir" not in st.session_state: 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    st.session_state.image_storage_dir = os.path.join(base_dir, "invoice_images")
    os.makedirs(st.session_state.image_storage_dir, exist_ok=True)
if "last_edited_df_hash" not in st.session_state: st.session_state.last_edited_df_hash = None
# 登錄狀態管理（多用戶版本）
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_email" not in st.session_state: st.session_state.user_email = None
# 刪除確認狀態（修復 Bug #2）
if "show_delete_confirm" not in st.session_state: st.session_state.show_delete_confirm = False
# 公司資訊（用於 PDF 導出）
if "company_name" not in st.session_state: st.session_state.company_name = ""
if "company_ubn" not in st.session_state: st.session_state.company_ubn = ""

# --- 1.4. 密碼哈希函數 ---
def hash_password(password: str) -> str:
    """使用 SHA256 產生密碼雜湊"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# --- 1.5. 註冊函數 ---
def register_user(email: str, password: str):
    """註冊新用戶（寫入 SQLite users 表）"""
    import re
    
    email = email.strip()
    if not email or not password:
        return False, "郵箱與密碼不可為空"
    
    # 簡單 email 格式檢查
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "郵箱格式不正確"
    
    if len(password) < 6:
        return False, "密碼至少需要 6 個字元"
    
    # 初始化資料庫（確保 users 表存在）
    init_db()
    path = get_db_path()
    is_uri = path.startswith("file:") and "mode=memory" in path
    
    try:
        conn = sqlite3.connect(path, timeout=30, uri=is_uri, check_same_thread=False)
        cursor = conn.cursor()
        
        # 檢查是否已存在
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return False, "此郵箱已註冊，請直接登入"
        
        # 寫入新用戶
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, hash_password(password)),
        )
        conn.commit()
        conn.close()
        return True, "註冊成功，請使用此帳號登入"
    except Exception as e:
        return False, f"註冊失敗: {str(e)}"

# --- 1.6. 用戶驗證函數（多用戶版本：優先查資料庫）---
def verify_user(email, password):
    """
    驗證用戶登錄
    優先順序：
    1. 查詢 SQLite users 表（註冊用戶）
    2. Streamlit Secrets
    3. 環境變數
    """
    import re
    
    # 驗證郵箱格式
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "郵箱格式不正確"
    
    email = email.strip()
    
    # ① 優先查詢 SQLite users 表（註冊用戶）
    try:
        init_db()
        path = get_db_path()
        is_uri = path.startswith("file:") and "mode=memory" in path
        conn = sqlite3.connect(path, timeout=30, uri=is_uri, check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (email,)
        )
        row = cursor.fetchone()
        if row:
            user_id, stored_hash = row
            if not stored_hash:
                conn.close()
                return False, "此帳號僅支援 Google 登入，請使用 Google 登入"
            
            # 計算輸入密碼的哈希值
            input_hash = hash_password(password)
            
            if input_hash == stored_hash:
                # 更新最後登入時間
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now().isoformat(), user_id),
                )
                conn.commit()
                conn.close()
                return True, "登錄成功"
            else:
                conn.close()
                return False, "郵箱或密碼錯誤"
        conn.close()
    except Exception as e:
        # 資料庫查詢失敗，繼續使用其他方式
        pass
    
    # ② 使用 Streamlit Secrets
    if "USERS" in st.secrets:
        users = st.secrets["USERS"]
        if isinstance(users, dict):
            # 格式：{"user@example.com": "password", ...}
            if email in users:
                if users[email] == password or users[email] == "":
                    return True, "登錄成功"
        elif isinstance(users, str):
            # 格式：字符串，每行一個 "email:password"
            for line in users.strip().split('\n'):
                if ':' in line:
                    user_email, user_password = line.split(':', 1)
                    if user_email.strip() == email:
                        if user_password.strip() == password or user_password.strip() == "":
                            return True, "登錄成功"
    
    # 其次使用環境變數
    env_users = os.getenv("USERS")
    if env_users:
        for line in env_users.strip().split('\n'):
            if ':' in line:
                user_email, user_password = line.split(':', 1)
                if user_email.strip() == email:
                    if user_password.strip() == password or user_password.strip() == "":
                        return True, "登錄成功"
    
    # 生產環境：不提供默認測試帳號，必須通過註冊或 Secrets 配置
    return False, "郵箱或密碼錯誤"

# --- 1.7. 登錄頁面（多用戶版本：含註冊功能）---
def login_page():
    """顯示登錄頁面（多用戶版本：含註冊和 Google 登入）"""
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        st.markdown('<div style="text-align: center; padding: 2rem;">', unsafe_allow_html=True)
        st.title("🔐 發票報帳後台")
        st.markdown('<p style="text-align: center; color: #B0B0B0;">多用戶隔離版本</p>', unsafe_allow_html=True)
        
        # 選擇登入或註冊模式
        if "login_mode" not in st.session_state:
            st.session_state.login_mode = "登入"
        
        mode = st.radio(
            "選擇操作", 
            ["登入", "註冊"], 
            horizontal=True,
            key="mode_selector",
            index=0 if st.session_state.login_mode == "登入" else 1
        )
        st.session_state.login_mode = mode
        
        st.markdown("---")
        
        if mode == "登入":
            email = st.text_input("📧 郵箱", key="login_email", label_visibility="visible", 
                                 placeholder="user@example.com")
            password = st.text_input("🔑 密碼", type="password", key="login_password", 
                                    label_visibility="visible")
            
            
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("🔑 登錄", type="primary", use_container_width=True):
                    if not email:
                        st.error("❌ 請輸入郵箱")
                    elif not password:
                        st.error("❌ 請輸入密碼")
                    else:
                        success, message = verify_user(email.strip(), password)
                        if success:
                            st.session_state.authenticated = True
                            st.session_state.user_email = email.strip()
                            st.success(f"✅ {message}")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                            # 提供更多帮助信息
                            if "郵箱或密碼錯誤" in message:
                                st.info("💡 提示：如果忘記密碼，請使用「註冊」功能創建新帳號。")
            
            with col_btn2:
                # Google 登入按鈕（預留功能）
                if st.button("🔵 Google 登入", use_container_width=True):
                    st.info("💡 Google 登入功能開發中，目前請使用郵箱密碼登入")
                    # TODO: 實作 Google OAuth 登入
                    # 需要設定 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET
                    # 並實作 OAuth 2.0 流程
            
        else:  # 註冊模式
            email = st.text_input("📧 新帳號郵箱", key="reg_email", label_visibility="visible", 
                                 placeholder="you@example.com")
            password = st.text_input("🔒 密碼（至少 6 碼）", type="password", key="reg_password", 
                                    label_visibility="visible")
            confirm = st.text_input("🔒 再輸入一次密碼", type="password", key="reg_confirm", 
                                   label_visibility="visible")
            
            if st.button("✅ 建立帳號", type="primary", use_container_width=True):
                if not email:
                    st.error("❌ 請輸入郵箱")
                elif not password:
                    st.error("❌ 請輸入密碼")
                elif password != confirm:
                    st.error("❌ 兩次密碼不一致")
                else:
                    success, message = register_user(email, password)
                    if success:
                        # 註冊成功後自動登錄（提升用戶體驗）
                        st.session_state.authenticated = True
                        st.session_state.user_email = email.strip()
                        st.success(f"✅ {message}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- 2. 終極韌性資料庫連線器 ---
def get_db_path():
    if "current_db_path" not in st.session_state:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 改用 invoices_v2.db 以解決舊資料庫可能發生的 Disk I/O Error 鎖定問題
        db_file = os.path.join(base_dir, "invoices_v2.db")
        
        # 確保目錄存在
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception as e:
            st.session_state.db_error = f"無法創建目錄: {str(e)}"
            st.session_state.current_db_path = "file:invoice_mem?mode=memory&cache=shared"
            st.session_state.db_path_mode = "🧠 虛擬記憶體 (重啟會清空)"
            return st.session_state.current_db_path
        
        try:
            # 檢查寫入權限（不創建測試文件，直接嘗試創建目錄）
            # 強制使用文件數據庫，不使用內存模式
            st.session_state.current_db_path = db_file
            st.session_state.db_path_mode = "💾 本地磁碟"
            st.session_state.db_error = None
        except PermissionError as e:
            st.session_state.db_error = f"權限不足，無法寫入: {str(e)}"
            # 即使權限不足，也嘗試使用文件數據庫（可能可以讀取）
            st.session_state.current_db_path = db_file
            st.session_state.db_path_mode = "⚠️ 只讀模式"
        except Exception as e:
            st.session_state.db_error = f"無法使用文件數據庫: {str(e)}"
            # 最後才使用內存模式
            st.session_state.current_db_path = "file:invoice_mem?mode=memory&cache=shared"
            st.session_state.db_path_mode = "🧠 虛擬記憶體 (重啟會清空)"
    
    return st.session_state.current_db_path

def init_db():
    """初始化資料表，確保所有必要欄位存在（多用戶版本：含 users 表）"""
    if st.session_state.use_memory_mode:
        return True  # 使用內存模式，跳過數據庫初始化
    
    path = get_db_path()
    # 判斷是否為URI模式（只有明確包含mode=memory才是URI）
    # 普通文件路徑（如 invoices_v2.db）不是URI
    is_uri = path.startswith("file:") and "mode=memory" in path
    try:
        conn = sqlite3.connect(path, timeout=30, uri=is_uri, check_same_thread=False)
        cursor = conn.cursor()
        
        # ① 創建 users 表（多用戶版本）
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         email TEXT UNIQUE NOT NULL,
                         password_hash TEXT,
                         google_id TEXT,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         last_login TIMESTAMP)''')
        
        # ② 創建 invoices 表（多用戶版本：使用 user_email）
        cursor.execute('''CREATE TABLE IF NOT EXISTS invoices
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        user_email TEXT NOT NULL,
                        file_name TEXT, date TEXT, invoice_number TEXT, seller_name TEXT, seller_ubn TEXT,
                        subtotal REAL, tax REAL, total REAL, category TEXT, subject TEXT, status TEXT,
                        image_path TEXT, image_data BLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # ③ 補全欄位（兼容舊版本）
        # 檢查是否有 user_id 欄位，如果有則遷移到 user_email
        try:
            cursor.execute("SELECT user_id FROM invoices LIMIT 1")
            # 如果有 user_id，嘗試遷移數據
            cursor.execute("UPDATE invoices SET user_email = user_id WHERE user_email IS NULL OR user_email = ''")
            # 刪除舊的 user_id 欄位（SQLite不支持直接刪除，但可以忽略）
        except:
            pass
        
        # 添加 user_email 欄位（如果不存在）
        try:
            cursor.execute("ALTER TABLE invoices ADD COLUMN user_email TEXT")
        except:
            pass
        
        # 為 user_email 創建索引（提高查詢效率）
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON invoices(user_email)")
        except:
            pass
        
        # 補全其他欄位
        for col, c_type in {'status': "TEXT", 'seller_ubn': "TEXT", 
                            'image_path': "TEXT", 'image_data': "BLOB"}.items():
            try: 
                cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {c_type}")
            except: 
                pass
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.session_state.db_error = f"初始化失敗: {str(e)}"
        return False

def run_query(query, params=(), is_select=True):
    """
    執行資料庫查詢（多用戶版本：自動添加 user_email 隔離）
    - SELECT: 自動添加 WHERE user_email = ? 條件（如果查詢 invoices 表且沒有 user_email 條件）
    - INSERT: 自動添加 user_email 參數（如果插入 invoices 表）
    """
    user_email = st.session_state.get('user_email')
    if not user_email:
        user_email = "default_user"  # 未登錄時使用默認用戶
    
    # 如果使用內存模式，使用 session_state 存儲
    if st.session_state.use_memory_mode:
        if is_select:
            # 處理 SELECT 查詢 - 自動過濾 user_email
            # 修復 Bug #1: 使用安全的字符串比較，避免 SQL 注入風險
            # 雖然是內存模式，但保持一致的編碼風格和安全性
            df = pd.DataFrame([inv for inv in st.session_state.local_invoices 
                             if inv.get('user_email', inv.get('user_id', 'default_user')) == user_email])
            
            # 簡單的 ORDER BY 處理
            if "ORDER BY id DESC" in query.upper():
                if not df.empty and 'id' in df.columns:
                    df = df.sort_values('id', ascending=False)
            
            return df
        else:
            # INSERT 查詢會在調用處處理，確保包含 user_email
            return True
    
    # 使用數據庫
    path = get_db_path()
    # 判斷是否為URI模式（只有明確包含mode=memory或file:前綴才是URI）
    is_uri = (path.startswith("file:") and "mode=memory" in path) or path.startswith("file:invoice_mem")
    try:
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False, uri=is_uri)
        cursor = conn.cursor()
        
        if is_select:
            # 多用戶隔離：自動添加 user_email 條件（僅對 invoices 表）
            modified_query = query
            modified_params = list(params)
            
            if "FROM invoices" in query.upper() and "user_email" not in query.upper() and "WHERE" not in query.upper():
                # 如果查詢 invoices 表且沒有 WHERE 條件，添加 user_email 過濾
                modified_query = query + " WHERE user_email = ?"
                modified_params = [user_email] + list(params)
            elif "FROM invoices" in query.upper() and "user_email" not in query.upper() and "WHERE" in query.upper():
                # 如果有 WHERE 條件但沒有 user_email，添加 AND user_email = ?
                # 找到 WHERE 的位置，在其後添加
                where_pos = query.upper().find("WHERE")
                modified_query = query[:where_pos+5] + " user_email = ? AND " + query[where_pos+5:]
                modified_params = [user_email] + list(params)
            
            try:
                df = pd.read_sql_query(modified_query, conn, params=tuple(modified_params))
            except Exception as e:
                # 關鍵修復：如果發現沒表，自動初始化並重試
                if "no such table" in str(e).lower():
                    if init_db():
                        df = pd.read_sql_query(modified_query, conn, params=tuple(modified_params))
                    else:
                        # 初始化失敗，切換到內存模式
                        st.session_state.use_memory_mode = True
                        return run_query(query, params, is_select)
                else: 
                    raise e
            conn.close()
            st.session_state.db_error = None
            return df
        else:
            # 非SELECT查询：INSERT, UPDATE, DELETE等
            # 對於 INSERT invoices，確保包含 user_email
            modified_query = query
            modified_params = list(params)
            
            if "INSERT INTO invoices" in query.upper() and "user_email" not in query.upper():
                # 自動添加 user_email 到 INSERT 語句
                # 找到 VALUES 的位置
                values_pos = query.upper().find("VALUES")
                if values_pos > 0:
                    # 在列名中添加 user_email
                    insert_part = query[:values_pos]
                    values_part = query[values_pos:]
                    
                    # 在列名列表中添加 user_email
                    if "(" in insert_part:
                        last_paren = insert_part.rfind(")")
                        insert_part = insert_part[:last_paren] + ", user_email" + insert_part[last_paren:]
                    
                    # 在 VALUES 中添加 user_email 值
                    if "(" in values_part:
                        first_paren = values_part.find("(")
                        last_paren = values_part.rfind(")")
                        values_part = values_part[:first_paren+1] + "?, " + values_part[first_paren+1:last_paren] + ", ?" + values_part[last_paren:]
                    
                    modified_query = insert_part + values_part
                    modified_params = [user_email] + list(params)
            
            # 對於 UPDATE 和 DELETE，確保包含 user_email 條件
            if ("UPDATE invoices" in query.upper() or "DELETE FROM invoices" in query.upper()) and "user_email" not in query.upper():
                if "WHERE" in query.upper():
                    where_pos = query.upper().find("WHERE")
                    modified_query = query[:where_pos+5] + " user_email = ? AND " + query[where_pos+5:]
                    modified_params = [user_email] + list(params)
                else:
                    # 如果沒有 WHERE，添加 WHERE user_email = ?
                    modified_query = query + " WHERE user_email = ?"
                    modified_params = [user_email] + list(params)
            
            try:
                cursor.execute(modified_query, tuple(modified_params))
                conn.commit()
                # 验证是否真的执行成功
                if "INSERT" in modified_query.upper():
                    # 对于INSERT，检查影响的行数
                    if cursor.rowcount > 0:
                        conn.close()
                        return True
                    else:
                        conn.close()
                        st.session_state.db_error = "插入失敗：影響行數為0"
                        return False
                conn.close()
                return True
            except Exception as e:
                conn.rollback()
                conn.close()
                st.session_state.db_error = f"執行失敗: {str(e)}"
                return False
    except Exception as e:
        err_msg = str(e)
        st.session_state.db_error = f"連線異常: {err_msg}"
        # 如果數據庫失敗，自動切換到內存模式
        if "no such table" in err_msg.lower() or "unable to open" in err_msg.lower():
            st.session_state.use_memory_mode = True
            if is_select:
                return run_query(query, params, is_select)
        return pd.DataFrame() if is_select else False

# 程式啟動立即初始化（如果使用數據庫模式）
if not st.session_state.use_memory_mode:
    init_db()

import re

# ... (保持前面的 import 不变)

# --- 3. 核心辨識邏輯 ---
def extract_json(text):
    """從混合文本中提取有效的 JSON 物件"""
    text = text.strip()
    # 嘗試 1: 直接解析
    try:
        return json.loads(text)
    except:
        pass
        
    # 嘗試 2: 尋找 Markdown 代碼塊 ```json ... ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1))
        except: pass
        
    # 嘗試 3: 尋找最外層的 {}
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1))
        except: pass
        
    return None

def save_invoice_image(image_obj, file_name, user_email=None):
    """保存發票圖片到文件系統，返回圖片路徑"""
    try:
        # 創建用戶專屬目錄
        user_email = user_email or st.session_state.get('user_email', 'default_user')
        user_dir = os.path.join(st.session_state.image_storage_dir, user_email)
        os.makedirs(user_dir, exist_ok=True)
        
        # 生成唯一文件名（使用時間戳+文件名hash）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_name.encode()).hexdigest()[:8]
        safe_filename = f"{timestamp}_{file_hash}_{file_name}"
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")
        
        image_path = os.path.join(user_dir, safe_filename)
        image_obj.save(image_path)
        return image_path
    except Exception as e:
        st.error(f"保存圖片失敗: {str(e)}")
        return None

def check_duplicate_invoice(invoice_number, date, user_email=None):
    """檢查是否為重複發票（根據發票號碼+日期）"""
    if not invoice_number or invoice_number == "No" or invoice_number == "N/A":
        return False, None
    
    user_email = user_email or st.session_state.get('user_email', 'default_user')
    if st.session_state.use_memory_mode:
        # 內存模式檢查（多用戶版本：使用 user_email）
        for inv in st.session_state.local_invoices:
            inv_user = inv.get('user_email', inv.get('user_id', 'default_user'))
            if (inv_user == user_email and 
                inv.get('invoice_number') == invoice_number and 
                inv.get('date') == date):
                return True, inv.get('id')
    else:
        # 數據庫模式檢查（多用戶版本：使用 user_email）
        query = "SELECT id FROM invoices WHERE user_email = ? AND invoice_number = ? AND date = ?"
        result = run_query(query, (user_email, invoice_number, date), is_select=True)
        if not result.empty:
            return True, result.iloc[0]['id']
    
    return False, None

def save_edited_data(ed_df, original_df, user_email=None):
    """自動保存編輯後的數據"""
    saved_count = 0
    errors = []
    
    # 將列名映射回數據庫字段名
    reverse_mapping = {"檔案名稱":"file_name","日期":"date","發票號碼":"invoice_number",
                      "賣方名稱":"seller_name","賣方統編":"seller_ubn","銷售額":"subtotal",
                      "稅額":"tax","總計":"total","類型":"category","會計科目":"subject","狀態":"status"}
    
    for idx, row in ed_df.iterrows():
        if 'id' not in row or pd.isna(row['id']):
            continue
        
        record_id = int(row['id'])
        
        # 檢查是否有變更
        if idx < len(original_df):
            orig_row = original_df.iloc[idx]
            if orig_row.get('id') == record_id:
                # 比較關鍵字段是否有變化
                changed = False
                for col in ed_df.columns:
                    if col not in ['id', '選取']:
                        orig_val = orig_row.get(col, '')
                        new_val = row.get(col, '')
                        if str(orig_val) != str(new_val):
                            changed = True
                            break
                
                if not changed:
                    continue
        
        # 準備更新數據
        update_data = {}
        for display_col, db_col in reverse_mapping.items():
            if display_col in row:
                update_data[db_col] = row[display_col]
        
        # 處理數值字段
        for num_col in ['subtotal', 'tax', 'total']:
            if num_col in update_data:
                try:
                    val = str(update_data[num_col]).replace(',', '').replace('$', '')
                    update_data[num_col] = float(val) if val else 0.0
                except:
                    update_data[num_col] = 0.0
        
        # 保存到數據庫或內存
        try:
            if st.session_state.use_memory_mode:
                # 更新內存中的記錄
                for i, inv in enumerate(st.session_state.local_invoices):
                    if inv.get('id') == record_id:
                        for key, val in update_data.items():
                            st.session_state.local_invoices[i][key] = val
                        saved_count += 1
                        break
            else:
                # 更新數據庫（多用戶版本：使用 user_email）
                set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
                user_email = st.session_state.get('user_email', 'default_user')
                query = f"UPDATE invoices SET {set_clause} WHERE id = ? AND user_email = ?"
                params = list(update_data.values()) + [record_id, user_email]
                result = run_query(query, tuple(params), is_select=False)
                if result:
                    saved_count += 1
                else:
                    errors.append(f"記錄 ID {record_id} 更新失敗")
        except Exception as e:
            errors.append(f"記錄 ID {record_id} 更新錯誤: {str(e)}")
    
    return saved_count, errors

def process_ocr(image_obj, file_name, model_name, api_key_val):
    try:
        if image_obj.mode != "RGB": image_obj = image_obj.convert("RGB")
        # 稍微降低解析度以加快速度並減少 Token，但保持足夠清晰度
        image_obj.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        img_byte = io.BytesIO(); image_obj.save(img_byte, format="JPEG", quality=85)
        img_base64 = base64.b64encode(img_byte.getvalue()).decode()
        
        # 優化 Prompt：明確要求純 JSON，不要 Markdown
        prompt = """You are a receipt OCR assistant. Extract data from this image.
        Output ONLY a valid JSON object. Do NOT use Markdown code blocks.
        Fields required:
        - date (Format: YYYY/MM/DD, convert ROC year to AD if needed)
        - invoice_no (Invoice number)
        - seller_name (Store name)
        - seller_ubn (Unified Business Number / Tax ID)
        - subtotal (Amount before tax, number only)
        - tax (Tax amount, number only)
        - total (Total amount, number only)
        - type (Invoice type, e.g., "電子發票", "收據")
        - category_suggest (Category, e.g., "餐飲", "交通", "辦公用品")
        
        If a field is missing, use null or 0.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}]}], 
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024}
        }
        
        # 優先順序調整：先試 v1beta (支援較新模型)，再試 v1
        configs = [
            ("v1beta", model_name),
            ("v1beta", f"models/{model_name}"),
            ("v1", model_name),
            ("v1", f"models/{model_name}")
        ]
        
        session = requests.Session(); session.trust_env = False
        os.environ.pop('HTTP_PROXY', None); os.environ.pop('HTTPS_PROXY', None)
        
        # 修復 Bug #5: 添加重試機制
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # 配置重試策略
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
        except ImportError:
            # 如果 urllib3 版本不支持，跳過重試配置
            pass
        
        last_err = ""
        debug_info = []
        
        for ver, m_name in configs:
            # 智能處理 models/ 前綴
            final_model_name = m_name if "models/" in m_name else f"models/{m_name}"
            # 修正 URL 結構：v1beta/models/gemini-pro:generateContent
            # 移除多餘的 models/ 如果 API 版本路徑已經隱含
            if ver == "v1beta" or ver == "v1":
                 # Google API 規範: https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent
                 # 如果 m_name 已經包含 models/，則直接使用
                 pass

            url = f"https://generativelanguage.googleapis.com/{ver}/{m_name}:generateContent?key={api_key_val}"
            if "models/" not in m_name:
                 url = f"https://generativelanguage.googleapis.com/{ver}/models/{m_name}:generateContent?key={api_key_val}"
            
            try:
                # 修復 Bug #5: 使用帶重試的請求
                resp = session.post(url, json=payload, timeout=25)
                if resp.status_code == 200:
                    try:
                        resp_json = resp.json()
                        if 'candidates' not in resp_json or not resp_json['candidates']:
                            last_err = "API 回傳結構異常 (無 candidates)"
                            continue
                            
                        text = resp_json['candidates'][0]['content']['parts'][0]['text']
                        raw = extract_json(text)
                        
                        if raw:
                            data = {
                                "file_name": file_name,
                                "date": raw.get("date") or raw.get("日期") or datetime.now().strftime("%Y/%m/%d"),
                                "invoice_no": raw.get("invoice_no") or raw.get("invoice_number") or "N/A",
                                "seller_name": raw.get("seller_name") or "N/A",
                                "seller_ubn": raw.get("seller_ubn") or "N/A",
                                "subtotal": raw.get("subtotal") or 0, "tax": raw.get("tax") or 0, "total": raw.get("total") or 0,
                                "type": raw.get("type") or "其他", "category_suggest": raw.get("category_suggest") or "雜項"
                            }
                            data["status"] = "✅ 正常" if data["total"] else "⚠️ 缺漏"
                            return data, None
                        else:
                            last_err = f"JSON 解析失敗. 原始文本: {text[:100]}..."
                            debug_info.append(f"{ver}/{m_name}: {last_err}")
                    except Exception as parse_err:
                        last_err = f"解析異常: {str(parse_err)}"
                        debug_info.append(f"{ver}/{m_name}: {last_err}")
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
                    debug_info.append(f"{ver}/{m_name}: {last_err}")
            except requests.exceptions.RequestException as e:
                # 修復 Bug #5: 區分網絡錯誤和其他錯誤
                last_err = f"網絡錯誤: {str(e)}"
                debug_info.append(f"{ver}/{m_name}: {last_err}")
                continue
            except Exception as e: 
                last_err = str(e)
                debug_info.append(f"{ver}/{m_name}: {last_err}")
                continue
                
        return None, f"所有嘗試皆失敗。最後錯誤: {last_err} | 歷程: {'; '.join(debug_info)}"
    except Exception as e: return None, f"系統錯誤: {str(e)}"

# --- 4. 介面渲染 ---
# 這裡不再硬編碼 Key，防止洩漏。預設為空，強迫使用 Secrets 或手動輸入。
DEFAULT_KEY = "" 

# --- 主應用入口：檢查登錄狀態（多用戶版本）---
if not st.session_state.authenticated or not st.session_state.user_email:
    login_page()
    st.stop()  # 未登錄時停止執行後續代碼

# 已登錄，顯示側邊欄系統狀態
with st.sidebar:
    st.title("⚙️ 系統狀態")
    # 顯示當前登錄用戶（多用戶版本）
    user_email = st.session_state.get('user_email', '未登錄')
    st.info(f"👤 當前用戶: {user_email}")
    
    # 登出按鈕
    if st.button("🚪 登出", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.rerun()
    
    st.markdown("---")
    
    # 優先使用 Streamlit Secrets
    if "GEMINI_API_KEY" in st.secrets:
        st.success("🔑 已使用 Secrets 金鑰")
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.text_input("Gemini API Key", DEFAULT_KEY, type="password")
        if not api_key:
            st.warning("請輸入 API Key 或設定 Secrets")

    model = st.selectbox("辨識模型", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"])
    
    st.divider()
    
    # 生產環境：僅使用數據庫模式，移除內存模式選項
    st.session_state.use_memory_mode = False
    
    # 顯示資料庫狀態
    db_path = get_db_path()
    if "mode=memory" in db_path:
        st.warning(f"⚠️ {st.session_state.db_path_mode}")
        if st.session_state.db_error:
            st.error(f"❌ {st.session_state.db_error}")
        # 提供重置按鈕，嘗試切換到文件模式
        if st.button("🔄 嘗試切換到文件模式", help="清除當前設置，重新嘗試使用文件數據庫"):
            if "current_db_path" in st.session_state:
                del st.session_state.current_db_path
            if "db_error" in st.session_state:
                del st.session_state.db_error
            st.rerun()
    else:
        st.success(f"✅ {st.session_state.db_path_mode}")
    
    # 查詢當前用戶的數據
    user_email = st.session_state.get('user_email', 'default_user')
    db_count_df = run_query("SELECT count(*) as count FROM invoices WHERE user_email = ?", (user_email,))
    if not db_count_df.empty:
        st.success(f"📊 已存數據: {db_count_df['count'][0]} 筆")
    
    # 生產環境：移除數據庫清理功能，避免誤操作

# 已登錄，顯示主應用
# 標題和上傳按鈕（並排顯示）
title_col1, title_col2 = st.columns([2.5, 1.5])
with title_col1:
    st.title("📑 發票收據報帳小秘笈 Pro")
with title_col2:
    st.write("")  # 空白行用於對齊
    btn_row1, btn_row2 = st.columns(2)
    with btn_row1:
        if st.button("📷 上傳發票圖", type="primary", use_container_width=True):
            st.session_state.show_upload_dialog = True
            st.session_state.upload_mode = "ocr"
    with btn_row2:
        if st.button("📥 CSV數據導入", type="primary", use_container_width=True):
            st.session_state.show_upload_dialog = True
            st.session_state.upload_mode = "import"

# 查詢當前用戶的數據（多用戶版本：使用 user_email）
user_email = st.session_state.get('user_email', 'default_user')
df_raw = run_query("SELECT * FROM invoices WHERE user_email = ? ORDER BY id DESC", (user_email,))

# ========== 1. 統計指標區（最頂部）==========
with st.container():
    # st.markdown("### 📊 統計報表")  # 隱藏表頭
    df_stats = df_raw.copy()
    if not df_stats.empty:
        # 先重命名列以便統計報表使用
        mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態","created_at":"建立時間"}
        df_stats = df_stats.rename(columns=mapping)
        
        if "總計" in df_stats.columns:
            for c in ["總計", "稅額"]: 
                if c in df_stats.columns:
                    df_stats[c] = pd.to_numeric(df_stats[c].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            
            # 統計指標卡片（並排顯示）
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            total_sum = pd.to_numeric(df_stats['總計'], errors='coerce').fillna(0).sum()
            tax_sum = pd.to_numeric(df_stats['稅額'], errors='coerce').fillna(0).sum()
            invoice_count = len(df_stats)
            missing_count = len(df_stats[df_stats['狀態'].astype(str).str.contains('缺失', na=False)]) if '狀態' in df_stats.columns else 0
            
            with stat_col1:
                st.metric("累計金額", f"${total_sum:,.0f}")
            with stat_col2:
                st.metric("累計稅額", f"${tax_sum:,.0f}")
            with stat_col3:
                st.metric("發票總數", f"{invoice_count} 筆")
            with stat_col4:
                st.metric("缺失數據", f"{missing_count} 筆", delta=f"-{invoice_count - missing_count} 正常" if invoice_count > 0 else None)
    else:
        st.info("📊 目前無統計數據")

# 初始化 dialog 狀態
if "show_upload_dialog" not in st.session_state:
    st.session_state.show_upload_dialog = False

# 上傳對話框函數
@st.dialog("📤 上傳辨識", width="medium")
def upload_dialog():
    # 根據模式顯示不同內容
    upload_mode = st.session_state.get("upload_mode", "ocr")
    
    if upload_mode == "ocr":
        # OCR識別區域
        st.markdown("### 📷 上傳發票圖")
        files = st.file_uploader("批次選擇照片", type=["jpg","png","jpeg"], accept_multiple_files=True)
        if files:
            st.caption(f"已選擇 {len(files)} 個文件")
        
        if files and st.button("開始辨識 🚀", type="primary", use_container_width=True):
            st.session_state.upload_files = files
            st.session_state.start_ocr = True
            st.rerun()
    else:
        # 數據導入區域
        st.markdown("### 📥 CSV數據導入")
        st.info("💡 支持導入 Excel (.xlsx) 或 CSV (.csv) 格式的發票數據")
        
        # 下載導入模板
        template_data = {
            "檔案名稱": ["範例1.jpg", "範例2.jpg"],
            "日期": ["2025/01/01", "2025/01/02"],
            "發票號碼": ["AB12345678", "CD87654321"],
            "賣方名稱": ["範例商店", "範例公司"],
            "賣方統編": ["12345678", "87654321"],
            "銷售額": [1000, 2000],
            "稅額": [50, 100],
            "總計": [1050, 2100],
            "類型": ["餐飲", "交通"],
            "會計科目": ["餐飲費", "交通費"]
        }
        template_df = pd.DataFrame(template_data)
        template_csv = template_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載導入模板 (CSV)", template_csv, "invoice_import_template.csv", 
                         mime="text/csv", use_container_width=True)
        
        uploaded_file = st.file_uploader("選擇要導入的文件", type=["csv", "xlsx"], key="import_file_dialog")
        
        if uploaded_file and st.button("開始導入", type="primary", use_container_width=True, key="import_btn_dialog"):
            st.session_state.import_file = uploaded_file
            st.session_state.start_import = True
            st.rerun()

# 顯示對話框
if st.session_state.show_upload_dialog:
    upload_dialog()
    st.session_state.show_upload_dialog = False

# 處理 OCR 識別（從 dialog 觸發）
if st.session_state.get("start_ocr", False) and "upload_files" in st.session_state:
    files = st.session_state.upload_files
    st.session_state.start_ocr = False
    del st.session_state.upload_files
    
    # 初始化 session_state 用於存儲結果報告
    if "ocr_report" not in st.session_state: 
        st.session_state.ocr_report = []
    
    success_count = 0
    fail_count = 0
    
    with st.status("AI 正在分析發票中...", expanded=False) as status:
        prog = st.progress(0)
        
        for idx, f in enumerate(files):
            status.update(label=f"正在處理: {f.name} ({idx+1}/{len(files)})", state="running")
            image_obj = Image.open(f)
            data, err = process_ocr(image_obj, f.name, model, api_key)
            
            if data:
                def clean_n(v):
                    try: return float(str(v).replace(',','').replace('$',''))
                    except: return 0.0
                
                # 處理空值：確保所有字段都有值
                def safe_value(val, default='No'):
                    if val is None or val == '' or val == 'N/A':
                        return default
                    return str(val)
                
                # 檢查數據是否完整，用於設置狀態
                def check_data_complete(data):
                    key_fields = ['date', 'invoice_no', 'seller_name', 'total']
                    for field in key_fields:
                        val = data.get(field, '')
                        if not val or val == 'N/A' or val == '' or (isinstance(val, (int, float)) and val == 0 and field == 'total'):
                            return False
                    return True
                
                # 檢查重複發票
                invoice_no = safe_value(data.get("invoice_no"), "No")
                invoice_date = safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d"))
                # 多用戶版本：使用 user_email
                user_email = st.session_state.get('user_email', 'default_user')
                is_duplicate, dup_id = check_duplicate_invoice(invoice_no, invoice_date, user_email)
                
                if is_duplicate:
                    st.warning(f"⚠️ {f.name}: 疑似重複發票（發票號碼: {invoice_no}, 日期: {invoice_date}，記錄ID: {dup_id}）")
                    fail_count += 1
                    continue
                
                # 保存圖片（多用戶版本：使用 user_email）
                image_path = save_invoice_image(image_obj.copy(), f.name, user_email)
                
                # 根據存儲模式選擇不同的保存方式
                if st.session_state.use_memory_mode:
                    # 使用內存模式
                    invoice_record = {
                        'id': len(st.session_state.local_invoices) + 1,
                        'user_email': st.session_state.get('user_email', 'default_user'),
                        'file_name': safe_value(data.get("file_name"), "未命名"),
                        'date': safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d")),
                        'invoice_number': safe_value(data.get("invoice_no"), "No"),
                        'seller_name': safe_value(data.get("seller_name"), "No"),
                        'seller_ubn': safe_value(data.get("seller_ubn"), "No"),
                        'subtotal': clean_n(data.get("subtotal", 0)),
                        'tax': clean_n(data.get("tax", 0)),
                        'total': clean_n(data.get("total", 0)),
                        'category': safe_value(data.get("type"), "其他"),
                        'subject': safe_value(data.get("category_suggest"), "雜項"),
                        'status': "❌ 缺失" if not check_data_complete(data) else safe_value(data.get("status"), "✅ 正常"),
                        'image_path': image_path,
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.local_invoices.append(invoice_record)
                    st.session_state.data_saved = True
                else:
                    # 使用數據庫 - 確保數據保存
                    init_db()
                    
                    # 讀取圖片數據（如果圖片路徑存在）
                    image_data = None
                    if image_path and os.path.exists(image_path):
                        try:
                            with open(image_path, 'rb') as img_file:
                                image_data = img_file.read()
                        except:
                            pass
                    
                    # 多用戶版本：使用 user_email
                    user_email = st.session_state.get('user_email', 'default_user')
                    q = "INSERT INTO invoices (user_email, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status, image_path, image_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                    insert_params = (
                        user_email, 
                        safe_value(data.get("file_name"), "未命名"),
                        safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d")),
                        safe_value(data.get("invoice_no"), "No"),
                        safe_value(data.get("seller_name"), "No"),
                        safe_value(data.get("seller_ubn"), "No"),
                        clean_n(data.get("subtotal", 0)),
                        clean_n(data.get("tax", 0)),
                        clean_n(data.get("total", 0)),
                        safe_value(data.get("type"), "其他"),
                        safe_value(data.get("category_suggest"), "雜項"),
                        "❌ 缺失" if not check_data_complete(data) else safe_value(data.get("status"), "✅ 正常"),
                        image_path,
                        image_data
                    )
                    
                    result = run_query(q, insert_params, is_select=False)
                    
                    if not result:
                        st.error(f"⚠️ 數據保存失敗，請檢查資料庫連線")
                        if st.session_state.db_error:
                            st.error(f"錯誤詳情: {st.session_state.db_error}")
                        # 如果數據庫保存失敗，嘗試切換到內存模式
                        st.warning("💡 嘗試切換到內存模式保存數據...")
                        invoice_record = {
                            'id': len(st.session_state.local_invoices) + 1,
                            'user_email': user_email,
                            'file_name': safe_value(data.get("file_name"), "未命名"),
                            'date': safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d")),
                            'invoice_number': safe_value(data.get("invoice_no"), "No"),
                            'seller_name': safe_value(data.get("seller_name"), "No"),
                            'seller_ubn': safe_value(data.get("seller_ubn"), "No"),
                            'subtotal': clean_n(data.get("subtotal", 0)),
                            'tax': clean_n(data.get("tax", 0)),
                            'total': clean_n(data.get("total", 0)),
                            'category': safe_value(data.get("type"), "其他"),
                            'subject': safe_value(data.get("category_suggest"), "雜項"),
                            'status': "❌ 缺失" if not check_data_complete(data) else safe_value(data.get("status"), "✅ 正常"),
                            'image_path': image_path,
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state.local_invoices.append(invoice_record)
                        st.session_state.use_memory_mode = True
                        st.session_state.data_saved = True
                    else:
                        st.session_state.data_saved = True
                success_count += 1
            else:
                st.error(f"❌ {f.name} 失敗: {err}")
                st.session_state.ocr_report.append(f"{f.name}: {err}")
                fail_count += 1
            
            prog.progress((idx+1)/len(files))
        
        status.update(label=f"處理完成! 成功: {success_count}, 失敗: {fail_count}", state="complete", expanded=True)
    
    # 簡化顯示識別結果（只顯示摘要，不顯示圖片預覽）
    if success_count > 0:
        st.success(f"✅ 成功辨識 {success_count} 張發票")
        if fail_count > 0:
            st.warning(f"⚠️ {fail_count} 張辨識失敗")
        # 自動清空圖片預覽，節省空間
        if "ocr_images" in st.session_state:
            st.session_state.ocr_images = []
        time.sleep(0.5)
        st.rerun()

# 處理數據導入（從 dialog 觸發）
if st.session_state.get("start_import", False) and "import_file" in st.session_state:
    uploaded_file = st.session_state.import_file
    st.session_state.start_import = False
    del st.session_state.import_file
    
    try:
        # 讀取文件
        if uploaded_file.name.endswith('.csv'):
            import_df = pd.read_csv(uploaded_file)
        else:
            try:
                import_df = pd.read_excel(uploaded_file)
            except:
                st.error("請安裝 openpyxl 庫以支持 Excel 文件: pip install openpyxl")
                st.stop()
        
        if import_df.empty:
            st.error("文件為空，請檢查文件內容")
        else:
            # 列名映射（支持多種可能的列名）
            column_mapping = {
                "檔案名稱": ["檔案名稱", "file_name", "檔名", "文件名"],
                "日期": ["日期", "date", "Date"],
                "發票號碼": ["發票號碼", "invoice_number", "invoice_no", "發票號"],
                "賣方名稱": ["賣方名稱", "seller_name", "賣方", "商家名稱"],
                "賣方統編": ["賣方統編", "seller_ubn", "統編", "統一編號"],
                "銷售額": ["銷售額", "subtotal", "未稅金額"],
                "稅額": ["稅額", "tax", "Tax"],
                "總計": ["總計", "total", "Total", "金額"],
                "類型": ["類型", "category", "Category"],
                "會計科目": ["會計科目", "subject", "Subject", "科目"]
            }
            
            # 標準化列名
            for standard_name, possible_names in column_mapping.items():
                for possible_name in possible_names:
                    if possible_name in import_df.columns:
                        import_df.rename(columns={possible_name: standard_name}, inplace=True)
                        break
            
            # 檢查必填字段
            required_fields = ["日期", "發票號碼", "總計"]
            missing_fields = [f for f in required_fields if f not in import_df.columns]
            if missing_fields:
                st.error(f"缺少必填字段: {', '.join(missing_fields)}")
            else:
                # 開始導入
                imported_count = 0
                duplicate_count = 0
                error_count = 0
                
                with st.status("正在導入數據...", expanded=False) as status:
                    for idx, row in import_df.iterrows():
                        try:
                            # 檢查重複
                            invoice_no = str(row.get("發票號碼", "No"))
                            invoice_date = str(row.get("日期", ""))
                            # 多用戶版本：使用 user_email
                            user_email = st.session_state.get('user_email', 'default_user')
                            is_dup, _ = check_duplicate_invoice(invoice_no, invoice_date, user_email)
                            
                            if is_dup:
                                duplicate_count += 1
                                continue
                            
                            # 處理數值
                            def safe_float(val):
                                try:
                                    return float(str(val).replace(',', '').replace('$', ''))
                                except:
                                    return 0.0
                            
                            def safe_str(val, default="No"):
                                val_str = str(val) if not pd.isna(val) else ""
                                return val_str if val_str.strip() else default
                            
                            # 保存數據（多用戶版本：使用 user_email）
                            if st.session_state.use_memory_mode:
                                invoice_record = {
                                    'id': len(st.session_state.local_invoices) + 1,
                                    'user_email': user_email,
                                    'file_name': safe_str(row.get("檔案名稱"), "導入數據"),
                                    'date': safe_str(row.get("日期"), datetime.now().strftime("%Y/%m/%d")),
                                    'invoice_number': safe_str(row.get("發票號碼"), "No"),
                                    'seller_name': safe_str(row.get("賣方名稱"), "No"),
                                    'seller_ubn': safe_str(row.get("賣方統編"), "No"),
                                    'subtotal': safe_float(row.get("銷售額", 0)),
                                    'tax': safe_float(row.get("稅額", 0)),
                                    'total': safe_float(row.get("總計", 0)),
                                    'category': safe_str(row.get("類型"), "其他"),
                                    'subject': safe_str(row.get("會計科目"), "雜項"),
                                    'status': "✅ 正常",
                                    'image_path': None,
                                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                st.session_state.local_invoices.append(invoice_record)
                                imported_count += 1
                            else:
                                init_db()
                                # 多用戶版本：使用 user_email
                                q = "INSERT INTO invoices (user_email, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
                                params = (
                                    user_email,
                                    safe_str(row.get("檔案名稱"), "導入數據"),
                                    safe_str(row.get("日期"), datetime.now().strftime("%Y/%m/%d")),
                                    safe_str(row.get("發票號碼"), "No"),
                                    safe_str(row.get("賣方名稱"), "No"),
                                    safe_str(row.get("賣方統編"), "No"),
                                    safe_float(row.get("銷售額", 0)),
                                    safe_float(row.get("稅額", 0)),
                                    safe_float(row.get("總計", 0)),
                                    safe_str(row.get("類型"), "其他"),
                                    safe_str(row.get("會計科目"), "雜項"),
                                    "✅ 正常"
                                )
                                if run_query(q, params, is_select=False):
                                    imported_count += 1
                                else:
                                    error_count += 1
                        
                        except Exception as e:
                            error_count += 1
                
                # 顯示結果
                if imported_count > 0:
                    st.success(f"✅ 成功導入 {imported_count} 筆數據")
                if duplicate_count > 0:
                    st.warning(f"⚠️ 跳過 {duplicate_count} 筆重複數據")
                if error_count > 0:
                    st.error(f"❌ {error_count} 筆數據導入失敗")
                
                if imported_count > 0:
                    time.sleep(1)
                    st.rerun()
                    
    except Exception as e:
        st.error(f"導入失敗: {str(e)}")

# ========== 3. 圖表展示區 ==========
with st.container():
    # st.markdown("### 📈 數據分析")  # 隱藏表頭
    
    # 準備數據（如果df_stats已定義，使用它；否則使用df_raw並重命名）
    if 'df_stats' in locals() and not df_stats.empty:
        df_chart = df_stats.copy()
    else:
        df_chart = df_raw.copy()
        if not df_chart.empty:
            mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態","created_at":"建立時間"}
            df_chart = df_chart.rename(columns=mapping)
    
    if not df_chart.empty:
        # 三列布局，使图表更紧凑
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        
        # 图表高度调整为更紧凑（参考图片样式）
        chart_height = 220
            
        with chart_col1:
            # 圓餅圖 - 會計科目分布
            st.markdown("**會計科目分布**")
            if "會計科目" in df_chart.columns:
                df_pie = df_chart[df_chart['會計科目'].notna() & (df_chart['會計科目'] != 'No')].copy()
                if not df_pie.empty:
                    # 使用参考图片的颜色方案（蓝色系）
                    chart = alt.Chart(df_pie).mark_arc(innerRadius=25).encode(
                        theta=alt.Theta("count()", type="quantitative"),
                        color=alt.Color("會計科目", type="nominal", 
                                       scale=alt.Scale(scheme='blues')),
                        tooltip=["會計科目", "count()"]
                    ).properties(
                        height=chart_height,
                        background='#2F2F2F'
                    ).configure_legend(
                        labelFontSize=14,
                        titleFontSize=14,
                        labelColor='#E0E0E0',
                        titleColor='#FFFFFF'
                    ).configure_axis(
                        labelFontSize=14,
                        titleFontSize=0,
                        labelColor='#E0E0E0',
                        titleColor='#FFFFFF',
                        gridColor='#3F3F3F',
                        domainColor='#5F5F5F'
                    ).configure_text(
                        fontSize=14
                    )
                    st.altair_chart(chart, use_container_width=True, theme='streamlit')
                else:
                    st.info("📊 暫無數據", icon="ℹ️")
            elif "subject" in df_raw.columns:
                df_pie = df_raw[df_raw['subject'].notna() & (df_raw['subject'] != 'No')].copy()
                if not df_pie.empty:
                    chart = alt.Chart(df_pie).mark_arc(innerRadius=30).encode(
                        theta=alt.Theta("count()", type="quantitative"),
                        color=alt.Color("subject", type="nominal"),
                        tooltip=["subject", "count()"]
                    ).properties(height=chart_height).configure_legend(
                        labelFontSize=9,
                        titleFontSize=10
                    ).configure_axis(
                        labelFontSize=9,
                        titleFontSize=10
                    )
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("📊 暫無數據", icon="ℹ️")
            else:
                st.info("📊 暫無數據", icon="ℹ️")
        
        with chart_col2:
            # 折線圖 - 每日支出趨勢
            st.markdown("**每日支出趨勢**")
            if "日期" in df_chart.columns and "總計" in df_chart.columns:
                df_line = df_chart.copy()
                df_line['日期'] = pd.to_datetime(df_line['日期'], errors='coerce', format='%Y/%m/%d')
                df_line = df_line.dropna(subset=['日期'])
                
                if not df_line.empty:
                    df_line_grouped = df_line.groupby('日期')['總計'].sum().reset_index()
                    df_line_grouped = df_line_grouped.sort_values('日期')
                    
                    # 使用参考图片的颜色（绿色线条）
                    line_chart = alt.Chart(df_line_grouped).mark_line(
                        point=True, 
                        strokeWidth=3,
                        color='#34A853'  # 绿色，参考图片
                    ).encode(
                        x=alt.X('日期:T', title='', axis=alt.Axis(format='%Y/%m/%d')),
                        y=alt.Y('總計:Q', title='', axis=alt.Axis(format='$,.0f')),
                        tooltip=[alt.Tooltip('日期:T', format='%Y/%m/%d', title='日期'), alt.Tooltip('總計:Q', format='$,.0f', title='金額')]
                    ).properties(
                        height=chart_height,
                        background='#2F2F2F'
                    ).configure_axis(
                        labelFontSize=14,
                        titleFontSize=0,
                        labelColor='#E0E0E0',
                        titleColor='#FFFFFF',
                        gridColor='#3F3F3F',
                        domainColor='#5F5F5F'
                    ).configure_text(
                        fontSize=14
                    ).configure_legend(
                        labelFontSize=14,
                        titleFontSize=14
                    )
                    st.altair_chart(line_chart, use_container_width=True, theme='streamlit')
                else:
                    st.info("📈 暫無數據", icon="ℹ️")
            else:
                st.info("📈 暫無數據", icon="ℹ️")
        
        with chart_col3:
            # 柱狀圖 - 類型分布
            st.markdown("**類型分布**")
            if "類型" in df_chart.columns:
                df_bar = df_chart[df_chart['類型'].notna() & (df_chart['類型'] != 'No')].copy()
                if not df_bar.empty:
                    df_bar_grouped = df_bar.groupby('類型').size().reset_index(name='數量')
                    df_bar_grouped = df_bar_grouped.sort_values('數量', ascending=False).head(10)  # 只顯示前10個
                    
                    # 使用参考图片的颜色（蓝色/青色柱状图）
                    bar_chart = alt.Chart(df_bar_grouped).mark_bar(
                        color='#4285F4',  # 蓝色，参考图片
                        cornerRadiusTopLeft=2,
                        cornerRadiusTopRight=2
                    ).encode(
                        x=alt.X('類型:N', title='', sort='-y', axis=alt.Axis(labelAngle=-45)),
                        y=alt.Y('數量:Q', title=''),
                        tooltip=[alt.Tooltip('類型:N', title='類型'), alt.Tooltip('數量:Q', title='數量')]
                    ).properties(
                        height=chart_height,
                        background='#2F2F2F'
                    ).configure_axis(
                        labelFontSize=14,
                        titleFontSize=0,
                        labelColor='#E0E0E0',
                        titleColor='#FFFFFF',
                        gridColor='#3F3F3F',
                        domainColor='#5F5F5F'
                    ).configure_text(
                        fontSize=14
                    ).configure_legend(
                        labelFontSize=14,
                        titleFontSize=14
                    )
                    st.altair_chart(bar_chart, use_container_width=True, theme='streamlit')
                else:
                    st.info("📊 暫無數據", icon="ℹ️")
            elif "category" in df_raw.columns:
                df_bar = df_raw[df_raw['category'].notna() & (df_raw['category'] != 'No')].copy()
                if not df_bar.empty:
                    df_bar_grouped = df_bar.groupby('category').size().reset_index(name='數量')
                    df_bar_grouped = df_bar_grouped.sort_values('數量', ascending=False).head(10)
                    
                    bar_chart = alt.Chart(df_bar_grouped).mark_bar().encode(
                        x=alt.X('category:N', title='類型', sort='-y'),
                        y=alt.Y('數量:Q', title='數量'),
                        color=alt.Color('category:N', legend=None),
                        tooltip=['category', '數量']
                    ).properties(
                        height=chart_height
                    ).configure_axis(
                        labelFontSize=9,
                        titleFontSize=10
                    )
                    st.altair_chart(bar_chart, use_container_width=True)
                else:
                    st.info("📊 暫無數據", icon="ℹ️")
            else:
                st.info("📊 暫無數據", icon="ℹ️")
    else:
        st.info("📊 目前無數據可顯示圖表")

# ========== 4. 數據表格區 ==========
with st.container():
    # st.markdown("### 📋 數據稽核報表")  # 隱藏表頭
    
    # 使用原始查詢結果（如果df_stats已定義，使用它；否則使用df_raw並重命名）
    if 'df_stats' in locals() and not df_stats.empty:
        df = df_stats.copy()
        # 保存帶ID的副本用於刪除功能
        df_with_id = df.copy() if 'id' in df.columns else None
    else:
        df = df_raw.copy()
        # 保存帶ID的副本用於刪除功能（在重命名前）
        df_with_id = df.copy() if 'id' in df.columns else None
        # 如果使用df_raw，需要重命名列
        if not df.empty:
            mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態","created_at":"建立時間"}
            df = df.rename(columns=mapping)
            # 同時重命名df_with_id的列（如果存在）
            if df_with_id is not None and not df_with_id.empty:
                df_with_id = df_with_id.rename(columns=mapping)
    
    # 查詢條件和導出按鈕（並排顯示）
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1, 1, 1])
    with filter_col1:
        search = st.text_input("🔍 關鍵字搜尋", placeholder="號碼/賣方/檔名...", label_visibility="hidden")
    with filter_col2:
        t_filter = st.selectbox("🕒 時間範圍（按發票日期）", ["全部", "今天", "本週", "本月"], label_visibility="visible", help="篩選條件基於發票日期，而非上傳時間")
    with filter_col3:
        st.write("")  # 空白行用於對齊
        if not df.empty:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 導出CSV", csv_data, "invoice_report.csv", 
                             mime="text/csv", use_container_width=True, help="導出當前數據為CSV文件")
    with filter_col4:
        st.write("")  # 空白行用於對齊
        if not df.empty:
            if PDF_AVAILABLE:
                def generate_pdf():
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    
                    # 嘗試載入中文字體
                    font_path = "NotoSansTC-Regular.ttf"
                    font_loaded = False
                    font_name = "NotoSansTC"
                    
                    if os.path.exists(font_path):
                        try:
                            pdf.add_font(font_name, '', font_path, uni=True)
                            pdf.add_font(font_name, 'B', font_path, uni=True)
                            font_loaded = True
                        except:
                            font_loaded = False
                    
                    def safe_cell(pdf, w, h, txt, border=0, ln=0, align='', fill=False, link='', font_name_override=None):
                        try:
                            if font_name_override:
                                pdf.set_font(font_name_override[0], font_name_override[1], font_name_override[2])
                            pdf.cell(w, h, txt, border, ln, align, fill, link)
                        except:
                            pdf.set_font('Arial', '', 10)
                            pdf.cell(w, h, str(txt)[:50], border, ln, align, fill, link)
                    
                    # 標題
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 16)
                        safe_cell(pdf, 0, 10, '發票報帳統計報表', ln=1, align='C')
                    else:
                        pdf.set_font('Arial', 'B', 16)
                        safe_cell(pdf, 0, 10, 'Invoice Report', ln=1, align='C')
                    pdf.ln(5)
                    
                    # 生成時間
                    if font_loaded:
                        pdf.set_font(font_name, '', 10)
                        safe_cell(pdf, 0, 5, f'生成時間: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}', ln=1, align='R')
                    else:
                        pdf.set_font('Arial', '', 10)
                        safe_cell(pdf, 0, 5, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ln=1, align='R')
                    pdf.ln(5)
                    
                    # 核心邏輯：增加公司資訊
                    if font_loaded:
                        pdf.set_font(font_name, '', 10)
                        company_name = st.session_state.get('company_name', '')
                        company_ubn = st.session_state.get('company_ubn', '')
                        if company_name:
                            safe_cell(pdf, 200, 10, txt=f"報支公司：{company_name}", ln=1)
                        if company_ubn:
                            safe_cell(pdf, 200, 10, txt=f"公司統編：{company_ubn}", ln=1)
                    else:
                        pdf.set_font('Arial', '', 10)
                        company_name = st.session_state.get('company_name', '')
                        company_ubn = st.session_state.get('company_ubn', '')
                        if company_name:
                            safe_cell(pdf, 200, 10, txt=f"Company: {company_name}", ln=1)
                        if company_ubn:
                            safe_cell(pdf, 200, 10, txt=f"UBN: {company_ubn}", ln=1)
                    pdf.ln(5)
                    
                    # 統計摘要
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 12)
                        safe_cell(pdf, 0, 8, '統計摘要', ln=1)
                        pdf.set_font(font_name, '', 10)
                        safe_cell(pdf, 90, 6, '累計金額:', 1)
                        # 計算統計數據 - 使用df_stats或df
                        export_df_for_stats = df_stats.copy() if 'df_stats' in locals() and not df_stats.empty else df.copy()
                        if "總計" in export_df_for_stats.columns:
                            total_sum = pd.to_numeric(export_df_for_stats['總計'], errors='coerce').fillna(0).sum()
                        else:
                            total_sum = 0
                        safe_cell(pdf, 90, 6, f"${total_sum:,.0f}", 1, ln=1)
                        safe_cell(pdf, 90, 6, '累計稅額:', 1)
                        if "稅額" in export_df_for_stats.columns:
                            tax_sum = pd.to_numeric(export_df_for_stats['稅額'], errors='coerce').fillna(0).sum()
                        else:
                            tax_sum = 0
                        safe_cell(pdf, 90, 6, f"${tax_sum:,.0f}", 1, ln=1)
                        safe_cell(pdf, 90, 6, '發票總數:', 1)
                        safe_cell(pdf, 90, 6, f"{len(export_df_for_stats)} 筆", 1, ln=1)
                    pdf.ln(5)
                    
                    # 詳細數據表格 - 修改表格 Header
                    export_df = df.copy()
                    # 調整列寬以適應新的列：日期、發票號碼、賣方統編、未稅金額、稅額、總計、備註
                    col_widths = [25, 30, 30, 30, 25, 25, 25]
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 10)
                        headers = ["日期", "發票號碼", "賣方統編", "未稅金額", "稅額", "總計", "備註"]
                    else:
                        pdf.set_font('Arial', 'B', 10)
                        headers = ["Date", "Invoice No", "Seller UBN", "Net Amount", "Tax", "Total", "Note"]
                    
                    for i, header in enumerate(headers):
                        safe_cell(pdf, col_widths[i], 7, header, 1, align='C')
                    pdf.ln()
                    
                    if font_loaded:
                        pdf.set_font(font_name, '', 8)
                    else:
                        pdf.set_font('Arial', '', 8)
                    
                    def pdf_safe_value(val, default='No'):
                        if pd.isna(val) or val == '' or val == 'N/A' or str(val).strip() == '':
                            return default
                        return str(val)
                    
                    # 每一行數據自動計算
                    for _, row in export_df.iterrows():
                        # 獲取總計
                        total_val = pd.to_numeric(row.get('總計', 0), errors='coerce')
                        if pd.isna(total_val) or total_val == 0:
                            total_val = 0
                            tax = 0
                            net_amount = 0
                        else:
                            # 計算稅額：round(total - (total / 1.05))
                            tax = round(total_val - (total_val / 1.05))
                            # 計算未稅金額：total - tax
                            net_amount = total_val - tax
                        
                        # 獲取其他字段
                        date_str = pdf_safe_value(row.get('日期', ''), 'No')[:10]
                        invoice_no = pdf_safe_value(row.get('發票號碼', ''), 'No')[:15]
                        seller_ubn = pdf_safe_value(row.get('賣方統編', ''), 'No')[:15]
                        note = pdf_safe_value(row.get('備註', '') or row.get('會計科目', '') or row.get('類型', ''), '')[:15]
                        
                        # 格式化金額
                        net_amount_str = f"${net_amount:,.0f}"
                        tax_str = f"${tax:,.0f}"
                        total_str = f"${total_val:,.0f}"
                        
                        # 寫入 PDF
                        safe_cell(pdf, col_widths[0], 6, date_str, 1)
                        safe_cell(pdf, col_widths[1], 6, invoice_no, 1)
                        safe_cell(pdf, col_widths[2], 6, seller_ubn, 1)
                        safe_cell(pdf, col_widths[3], 6, net_amount_str, 1, align='R')
                        safe_cell(pdf, col_widths[4], 6, tax_str, 1, align='R')
                        safe_cell(pdf, col_widths[5], 6, total_str, 1, align='R')
                        safe_cell(pdf, col_widths[6], 6, note, 1, ln=1)
                        
                        if pdf.get_y() > 270:
                            pdf.add_page()
                            if font_loaded:
                                pdf.set_font(font_name, 'B', 10)
                            else:
                                pdf.set_font('Arial', 'B', 10)
                            for i, header in enumerate(headers):
                                safe_cell(pdf, col_widths[i], 7, header, 1, align='C')
                            pdf.ln()
                            if font_loaded:
                                pdf.set_font(font_name, '', 8)
                            else:
                                pdf.set_font('Arial', '', 8)
                    
                    pdf_bytes = pdf.output(dest='S')
                    if isinstance(pdf_bytes, bytearray):
                        return bytes(pdf_bytes)
                    return pdf_bytes
                
                pdf_data = generate_pdf()
                st.download_button("📄 導出PDF", pdf_data, f"invoice_report_{datetime.now().strftime('%Y%m%d')}.pdf", 
                                 mime="application/pdf", use_container_width=True, help="導出當前數據為PDF報告")
            else:
                st.info("📄 PDF", help="需要安裝 fpdf2")
    
    # 移除image相關的列（不在表格中顯示）
    if not df.empty:
        columns_to_drop = ['image_path', 'image_data', 'imagePath', 'imageData']
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])
            if df_with_id is not None and col in df_with_id.columns:
                df_with_id = df_with_id.drop(columns=[col])
        
        # 移除ID列、user_id列、檔案名稱列和總計列（不在表格中顯示，但保留在df_with_id中）
        columns_to_hide = ['id', 'user_id', 'user_email', '檔案名稱', '總計']
        for col in columns_to_hide:
            if col in df.columns:
                df = df.drop(columns=[col])
    
    # 修復 Bug #3: 在篩選前保存原始索引映射，以便刪除功能正常工作
    # 將df_with_id保存到session_state，確保刪除功能可以訪問
    if 'df_with_id' in locals() and df_with_id is not None:
        st.session_state.df_with_id = df_with_id.copy()
    
    if not df.empty and df_with_id is not None:
        # 保存原始索引到df中（在篩選前）
        df['_original_index'] = df.index
    
    # 手動在記憶體中篩選（避免 SQL 過於複雜出錯）
    if not df.empty:
        if search:
            df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        if t_filter != "全部":
            # 實現日期過濾功能（使用已重命名的列名）
            if "日期" in df.columns:
                date_col = "日期"
                today = datetime.now().date()
                
                try:
                    # 將日期列轉換為日期格式
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce', format='%Y/%m/%d')
                    df = df.dropna(subset=[date_col])  # 移除無法解析的日期
                    
                    if t_filter == "今天":
                        df = df[df[date_col].dt.date == today]
                    elif t_filter == "本週":
                        # 計算本週的開始日期（週一）
                        days_since_monday = today.weekday()
                        week_start = today - timedelta(days=days_since_monday)
                        df = df[df[date_col].dt.date >= week_start]
                    elif t_filter == "本月":
                        # 本月
                        month_start = today.replace(day=1)
                        df = df[df[date_col].dt.date >= month_start]
                except Exception as e:
                    # 如果日期格式不正確，嘗試字符串匹配
                    if t_filter == "今天":
                        today_str = today.strftime("%Y/%m/%d")
                        df = df[df[date_col].astype(str).str.contains(today_str, na=False)]
                    elif t_filter == "本月":
                        month_str = today.strftime("%Y/%m")
                        df = df[df[date_col].astype(str).str.contains(month_str, na=False)]
    
    # 數據表格顯示（df已經重命名過，直接使用）
    if not df.empty:
        # 處理空值：用"No"替換
        def fill_empty(val):
            if pd.isna(val) or val == '' or val == 'N/A' or str(val).strip() == '':
                return 'No'
            return str(val)
        
        # 對所有列應用空值處理（除了狀態列，狀態列需要特殊處理）
        for col in df.columns:
            if col not in ['選取', '狀態']:  # 跳過選取和狀態列
                df[col] = df[col].apply(fill_empty)
        
        # 處理狀態列：檢查是否有缺失數據，如果有則顯示"缺失"
        if "狀態" in df.columns:
            def check_status(row):
                # 檢查關鍵字段是否為空或"No"
                key_fields = ['日期', '發票號碼', '賣方名稱', '總計']
                has_missing = False
                for field in key_fields:
                    if field in row:
                        val = str(row[field]).strip()
                        if pd.isna(row[field]) or val == '' or val == 'N/A' or val == 'No' or val == '未填':
                            has_missing = True
                            break
                
                # 如果原本的狀態已經是錯誤狀態，保持原樣（但確保有紅色X）
                original_status = str(row.get('狀態', '')).strip()
                if '缺漏' in original_status or '缺失' in original_status or '錯誤' in original_status:
                    # 如果已經有❌，保持原樣；如果沒有，添加❌
                    if '❌' not in original_status and '⚠️' not in original_status:
                        return f'❌ {original_status}'
                    return original_status
                
                # 如果有缺失，返回帶紅色X的"缺失"
                if has_missing:
                    return '❌ 缺失'
                
                # 否則返回原狀態或"正常"
                return original_status if original_status else '✅ 正常'
            
            df['狀態'] = df.apply(check_status, axis=1)
        
        # 再次確保移除image相關的列（防止遺漏）
        columns_to_drop = ['image_path', 'image_data', 'imagePath', 'imageData']
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # 確保ID列、user_id列、檔案名稱列和總計列已移除（如果還存在）
        columns_to_hide = ['id', 'user_id', 'user_email', '檔案名稱', '總計', '_original_index']
        for col in columns_to_hide:
            if col in df.columns:
                # 在移除前，確保df_with_id有這些列（用於刪除功能）
                if 'df_with_id' not in locals() or df_with_id is None:
                    df_with_id = df.copy()
                    # 同時保存到session_state
                    st.session_state.df_with_id = df_with_id.copy()
                df = df.drop(columns=[col])
        
        # 調整列順序：選取 -> 狀態 -> 其他列
        if "選取" not in df.columns: 
            df.insert(0, "選取", False)
        
        # 將狀態列移到選取列之後
        if "狀態" in df.columns:
            cols = df.columns.tolist()
            cols.remove("狀態")
            # 找到選取列的位置，在其後插入狀態
            select_idx = cols.index("選取") if "選取" in cols else 0
            cols.insert(select_idx + 1, "狀態")
            df = df[cols]
        
        # 修復 Bug #2 和 #3: 添加刪除確認對話框，並修復篩選後刪除失效問題
        if st.button("🗑️ 刪除選中數據", help="刪除已選中的數據（請先勾選要刪除的記錄）"):
            selected_indices = df[df["選取"]==True].index.tolist()
            if len(selected_indices) > 0:
                # 獲取要刪除的記錄ID
                ids = []
                # 確保df_with_id在作用域內
                if 'df_with_id' not in locals():
                    # 如果df_with_id不在作用域，嘗試從session_state獲取或重新創建
                    if 'df_with_id' in st.session_state:
                        df_with_id = st.session_state.df_with_id
                    else:
                        st.warning("⚠️ 無法確定要刪除的記錄ID，請刷新頁面後重試")
                        st.stop()
                
                if df_with_id is not None and 'id' in df_with_id.columns:
                    # 修復 Bug #3: 使用原始索引映射獲取ID
                    if '_original_index' in df.columns:
                        # 使用原始索引獲取ID
                        try:
                            original_indices = df.loc[selected_indices, '_original_index'].tolist()
                            ids = df_with_id.loc[original_indices, "id"].tolist()
                        except Exception as e:
                            # 如果索引映射失敗，嘗試直接使用當前索引
                            try:
                                ids = df_with_id.loc[selected_indices, "id"].tolist()
                            except:
                                st.warning(f"⚠️ 無法確定要刪除的記錄ID: {str(e)}")
                                st.stop()
                    else:
                        # 如果沒有原始索引，直接使用當前索引（未篩選的情況）
                        try:
                            ids = df_with_id.loc[selected_indices, "id"].tolist()
                        except Exception as e:
                            st.warning(f"⚠️ 無法確定要刪除的記錄ID: {str(e)}")
                            st.stop()
                
                if ids and len(ids) > 0:
                    # 修復 Bug #2: 添加刪除確認對話框
                    st.session_state.show_delete_confirm = True
                    st.session_state.delete_ids = ids
                    st.session_state.delete_count = len(ids)
                    st.rerun()
                else:
                    st.warning("⚠️ 無法確定要刪除的記錄ID，請刷新頁面後重試")
            else:
                st.info("💡 請先勾選要刪除的數據（使用左側的選取框）")
        
        # 顯示刪除確認對話框
        if st.session_state.get("show_delete_confirm", False):
            ids_to_delete = st.session_state.get("delete_ids", [])
            delete_count = st.session_state.get("delete_count", 0)
            
            with st.dialog("⚠️ 確認刪除"):
                st.warning(f"確定要刪除選中的 {delete_count} 條數據嗎？")
                st.error("⚠️ 此操作不可恢復！")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 確認刪除", type="primary", use_container_width=True):
                        # 執行刪除
                        if st.session_state.use_memory_mode:
                            # 內存模式：從列表中刪除（多用戶版本：只刪除當前用戶的數據）
                            user_email = st.session_state.get('user_email', 'default_user')
                            st.session_state.local_invoices = [
                                inv for inv in st.session_state.local_invoices 
                                if not (inv.get('id') in ids_to_delete and inv.get('user_email', inv.get('user_id', 'default_user')) == user_email)
                            ]
                        else:
                            # 數據庫模式
                            for i in ids_to_delete:
                                run_query("DELETE FROM invoices WHERE id=? AND user_email=?", (i, st.session_state.get('user_email', 'default_user')), is_select=False)
                        
                        # 清理狀態
                        st.session_state.show_delete_confirm = False
                        if "delete_ids" in st.session_state:
                            del st.session_state.delete_ids
                        if "delete_count" in st.session_state:
                            del st.session_state.delete_count
                        st.success(f"✅ 已刪除 {delete_count} 條數據")
                        time.sleep(0.5)
                        st.rerun()
                
                with col2:
                    if st.button("❌ 取消", use_container_width=True):
                        # 取消刪除，清理狀態
                        st.session_state.show_delete_confirm = False
                        if "delete_ids" in st.session_state:
                            del st.session_state.delete_ids
                        if "delete_count" in st.session_state:
                            del st.session_state.delete_count
                        st.rerun()
        
        # 保存原始數據的副本用於比較（不包含ID列）
        original_df_copy = df.copy()
        
        # 準備列配置（不包含ID列、user_id列、檔案名稱列和總計列）
        column_config = { 
            "選取": st.column_config.CheckboxColumn("選取", default=False),
            "銷售額": st.column_config.NumberColumn("銷售額", format="$%d"),
            "稅額": st.column_config.NumberColumn("稅額", format="$%d"),
            "建立時間": st.column_config.DatetimeColumn("建立時間", format="YYYY/MM/DD HH:mm")
        }
        
        # 處理日期列：嘗試轉換為日期類型
        df_for_editor = df.copy()
        if "日期" in df_for_editor.columns:
            try:
                # 嘗試將日期字符串轉換為日期類型
                df_for_editor["日期"] = pd.to_datetime(df_for_editor["日期"], errors='coerce', format='%Y/%m/%d')
                # 如果轉換成功（沒有全部為NaT），使用DateColumn
                if not df_for_editor["日期"].isna().all():
                    column_config["日期"] = st.column_config.DateColumn("日期", format="YYYY/MM/DD")
                else:
                    # 轉換失敗，使用TextColumn
                    column_config["日期"] = st.column_config.TextColumn("日期", width="medium")
                    df_for_editor["日期"] = df["日期"]  # 恢復原始字符串
            except:
                # 轉換失敗，使用TextColumn
                column_config["日期"] = st.column_config.TextColumn("日期", width="medium")
                df_for_editor["日期"] = df["日期"]  # 確保使用原始字符串
        
        # 處理建立時間列（created_at）
        if "建立時間" in df_for_editor.columns:
            try:
                # 嘗試將建立時間轉換為日期時間類型
                df_for_editor["建立時間"] = pd.to_datetime(df_for_editor["建立時間"], errors='coerce')
                if not df_for_editor["建立時間"].isna().all():
                    column_config["建立時間"] = st.column_config.DatetimeColumn("建立時間", format="YYYY/MM/DD HH:mm")
                else:
                    column_config["建立時間"] = st.column_config.TextColumn("建立時間", width="medium")
                    df_for_editor["建立時間"] = df["建立時間"]
            except:
                column_config["建立時間"] = st.column_config.TextColumn("建立時間", width="medium")
                df_for_editor["建立時間"] = df["建立時間"]
        
        ed_df = st.data_editor(df_for_editor, use_container_width=True, hide_index=True, height=500, 
                               column_config=column_config,
                               key="data_editor")
        
        # 如果日期被轉換為日期類型，需要轉回字符串格式以便保存
        if "日期" in ed_df.columns and ed_df["日期"].dtype != object:
            ed_df["日期"] = ed_df["日期"].dt.strftime("%Y/%m/%d").fillna(df["日期"])
        
        df["選取"] = ed_df["選取"]
        
        # 檢測是否有變更並自動保存（比較關鍵字段）
        has_changes = False
        try:
            # 比較關鍵字段是否有變化（不包含ID和選取列）
            for col in ed_df.columns:
                if col not in ['選取']:  # ID列已經被移除，不需要檢查
                    if col in original_df_copy.columns:
                        if not ed_df[col].equals(original_df_copy[col]):
                            has_changes = True
                            break
                    else:
                        has_changes = True
                        break
        except:
            # 如果比較失敗，使用hash方法
            try:
                original_hash = hashlib.md5(str(original_df_copy.values.tobytes()).encode()).hexdigest()
                edited_hash = hashlib.md5(str(ed_df.values.tobytes()).encode()).hexdigest()
                has_changes = (original_hash != edited_hash)
            except:
                has_changes = False
        
        if has_changes:
            # 有變更，自動保存
            # 多用戶版本：使用 user_email
            user_email = st.session_state.get('user_email', 'default_user')
            saved_count, errors = save_edited_data(ed_df, original_df_copy, user_email)
            if saved_count > 0:
                st.success(f"✅ 已自動保存 {saved_count} 筆數據變更")
                # 修復 Bug #4: 改進錯誤顯示，使用 expander 顯示所有錯誤
                if errors:
                    if len(errors) > 3:
                        with st.expander(f"⚠️ 發現 {len(errors)} 個錯誤（點擊查看詳情）", expanded=False):
                            for err in errors:
                                st.error(err)
                    else:
                        for err in errors:
                            st.error(err)
                time.sleep(0.5)
                st.rerun()
            elif errors:
                # 如果全部失敗，顯示所有錯誤
                if len(errors) > 3:
                    st.error(f"保存失敗: {errors[0]}")
                    with st.expander(f"查看所有 {len(errors)} 個錯誤", expanded=False):
                        for err in errors:
                            st.error(err)
                else:
                    for err in errors:
                        st.error(f"保存失敗: {err}")
    else: 
        # 如果df為空（篩選後或原始數據為空）
        if not df_raw.empty:
            st.warning("⚠️ 查無數據。")
        else:
            st.warning("⚠️ 目前無數據。請先嘗試上傳並辨識。")

