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
from openpyxl.styles import Alignment, Font

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
    
    /* 數據卡片樣式 - 專業 SaaS 介面 */
    .metric-card {
        background: linear-gradient(135deg, #2F2F2F 0%, #3A3A3A 100%) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 2px 4px rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        transition: all 0.3s ease !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #4285F4, #34A853, #FBBC04, #EA4335);
        opacity: 0.6;
    }
    
    .metric-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4), 0 4px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    .metric-card-title {
        font-size: 0.875rem !important;
        color: #B0B0B0 !important;
        font-weight: 500 !important;
        margin-bottom: 0.5rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    .metric-card-value {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
        margin: 0 !important;
        line-height: 1.2 !important;
    }
    
    .metric-card-icon {
        font-size: 2rem !important;
        margin-bottom: 0.5rem !important;
        opacity: 0.8 !important;
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
    
    /* 列對齊由JavaScript動態設置，這裡只保留基礎樣式 */
    
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
    
    /* 固定位置刪除按鈕容器 */
    .delete-button-fixed {
        position: sticky !important;
        top: 0 !important;
        z-index: 100 !important;
        background-color: #1F1F1F !important;
        padding: 12px 0 !important;
        margin-bottom: 10px !important;
        border-bottom: 2px solid #5F5F5F !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    
    /* 問題行高亮樣式（發票號碼為 "No" 或狀態為 "缺失"） */
    /* 使用 CSS 選擇器來高亮包含警示圖示的單元格所在的行 */
    [data-testid="stDataEditor"] tbody tr td:contains("⚠️"),
    [data-testid="stDataEditor"] tbody tr:has(td:contains("⚠️")) {
        background-color: rgba(234, 67, 53, 0.15) !important;
    }
    
    [data-testid="stDataEditor"] tbody tr:has(td:contains("❌ 缺失")),
    [data-testid="stDataEditor"] tbody tr:has(td:contains("❌ 缺漏")) {
        background-color: rgba(234, 67, 53, 0.15) !important;
        border-left: 4px solid #EA4335 !important;
    }
    
    /* 警示圖示樣式 */
    .warning-icon {
        color: #EA4335 !important;
        font-weight: bold !important;
        margin-right: 4px !important;
    }
    
    /* 確保固定按鈕容器內的按鈕樣式正常 */
    .delete-button-fixed .stButton {
        margin: 0 auto !important;
    }
    
    /* 固定按鈕容器的背景遮罩效果 */
    .delete-button-fixed::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(to bottom, rgba(31,31,31,0.95), rgba(31,31,31,0.98));
        z-index: -1;
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
# 注意：Streamlit的session_state在頁面刷新時應該保持（同一瀏覽器會話）
# 如果刷新後登出，可能是因為瀏覽器會話結束或應用重啟
if "authenticated" not in st.session_state: 
    st.session_state.authenticated = False
if "user_email" not in st.session_state: 
    st.session_state.user_email = None
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
                        note TEXT,
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
        
        # 添加 note 欄位（備註）（如果不存在）
        try:
            cursor.execute("ALTER TABLE invoices ADD COLUMN note TEXT")
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
                      "稅額":"tax","總計":"total","類型":"category","會計科目":"subject","狀態":"status","備註":"note"}
    
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
    
    st.markdown("---")

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

# ========== 1. 統計指標區（最頂部）- 專業儀表板 ==========
with st.container():
    df_stats = df_raw.copy()
    if not df_stats.empty:
        # 先重命名列以便統計報表使用
        mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態","note":"備註","created_at":"建立時間"}
        df_stats = df_stats.rename(columns=mapping)
        
        if "總計" in df_stats.columns:
            for c in ["總計", "稅額"]: 
                if c in df_stats.columns:
                    df_stats[c] = pd.to_numeric(df_stats[c].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            
            # 計算「本月」數據
            today = datetime.now().date()
            month_start = today.replace(day=1)
            
            # 篩選本月的發票
            if "日期" in df_stats.columns:
                try:
                    df_stats['日期_parsed'] = pd.to_datetime(df_stats['日期'], errors='coerce', format='%Y/%m/%d')
                    df_month = df_stats[df_stats['日期_parsed'].dt.date >= month_start].copy()
                except:
                    # 如果日期解析失敗，使用字符串匹配
                    month_str = today.strftime("%Y/%m")
                    df_month = df_stats[df_stats['日期'].astype(str).str.contains(month_str, na=False)].copy()
            else:
                df_month = df_stats.copy()
            
            # 計算本月統計數據
            month_total = pd.to_numeric(df_month['總計'], errors='coerce').fillna(0).sum() if not df_month.empty else 0
            month_tax = pd.to_numeric(df_month['稅額'], errors='coerce').fillna(0).sum() if not df_month.empty else 0
            month_invoice_count = len(df_month) if not df_month.empty else 0
            month_missing_count = len(df_month[df_month['狀態'].astype(str).str.contains('缺失', na=False)]) if not df_month.empty and '狀態' in df_month.columns else 0
            
            # 四個數據卡片（並排顯示）
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            
            # 卡片 1: 本月總計
            with stat_col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-icon">💰</div>
                    <div class="metric-card-title">本月總計</div>
                    <div class="metric-card-value">${month_total:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 卡片 2: 預計稅額
            with stat_col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-icon">📊</div>
                    <div class="metric-card-title">預計稅額</div>
                    <div class="metric-card-value">${month_tax:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 卡片 3: 發票總數
            with stat_col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-icon">📄</div>
                    <div class="metric-card-title">發票總數</div>
                    <div class="metric-card-value">{month_invoice_count:,} 筆</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 卡片 4: 缺失件數
            with stat_col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-card-icon">⚠️</div>
                    <div class="metric-card-title">缺失件數</div>
                    <div class="metric-card-value">{month_missing_count:,} 筆</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        # 無數據時顯示空卡片
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        with stat_col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-card-icon">💰</div>
                <div class="metric-card-title">本月總計</div>
                <div class="metric-card-value">$0</div>
            </div>
            """, unsafe_allow_html=True)
        with stat_col2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-card-icon">📊</div>
                <div class="metric-card-title">預計稅額</div>
                <div class="metric-card-value">$0</div>
            </div>
            """, unsafe_allow_html=True)
        with stat_col3:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-card-icon">📄</div>
                <div class="metric-card-title">發票總數</div>
                <div class="metric-card-value">0 筆</div>
            </div>
            """, unsafe_allow_html=True)
        with stat_col4:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-card-icon">⚠️</div>
                <div class="metric-card-title">缺失件數</div>
                <div class="metric-card-value">0 筆</div>
            </div>
            """, unsafe_allow_html=True)

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
                        'note': safe_value(data.get("note") or data.get("備註"), ""),
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
                    q = "INSERT INTO invoices (user_email, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status, note, image_path, image_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
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
                        safe_value(data.get("note") or data.get("備註"), ""),
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
                            'note': safe_value(data.get("note") or data.get("備註"), ""),
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
                "會計科目": ["會計科目", "subject", "Subject", "科目"],
                "備註": ["備註", "note", "Note", "备注", "備注"]
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
                                    'note': safe_str(row.get("備註"), ""),
                                    'image_path': None,
                                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                st.session_state.local_invoices.append(invoice_record)
                                imported_count += 1
                            else:
                                init_db()
                                # 多用戶版本：使用 user_email
                                q = "INSERT INTO invoices (user_email, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
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
                                    "✅ 正常",
                                    safe_str(row.get("備註"), "")
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
            mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態","note":"備註","created_at":"建立時間"}
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
                        x=alt.X('類型:N', title='', sort='-y', axis=alt.Axis(labelAngle=0)),
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
        # 保存帶ID的副本用於刪除功能（僅後端使用，不在前端顯示）
        df_with_id = df.copy() if 'id' in df.columns else None
    else:
        df = df_raw.copy()
        # 保存帶ID的副本用於刪除功能（在重命名前，僅後端使用）
        df_with_id = df.copy() if 'id' in df.columns else None
        # 如果使用df_raw，需要重命名列
        if not df.empty:
            mapping = {
                "file_name":"檔案名稱",
                "date":"日期",
                "invoice_number":"發票號碼",
                "seller_name":"賣方名稱",
                "seller_ubn":"賣方統編",
                "subtotal":"銷售額",
                "tax":"稅額",
                "total":"總計",
                "category":"類型",
                "subject":"會計科目",
                "status":"狀態",
                "note":"備註",
                "created_at":"建立時間"
            }
            df = df.rename(columns=mapping)
            # 同時重命名df_with_id的列（如果存在）
            if df_with_id is not None and not df_with_id.empty:
                df_with_id = df_with_id.rename(columns=mapping)

    # 確保主資料表一定有「總計」欄位（由銷售額 + 稅額計算）
    if not df.empty:
        has_subtotal = "銷售額" in df.columns
        has_tax = "稅額" in df.columns
        has_total = "總計" in df.columns

        # 若沒有總計，但有銷售額或稅額，則自動計算：總計 = 銷售額 + 稅額
        if not has_total and (has_subtotal or has_tax):
            subtotal_series = pd.to_numeric(df["銷售額"], errors="coerce").fillna(0) if has_subtotal else pd.Series(0, index=df.index)
            tax_series = pd.to_numeric(df["稅額"], errors="coerce").fillna(0) if has_tax else pd.Series(0, index=df.index)
            df["總計"] = (subtotal_series + tax_series).round(0)
    
    # 列表過濾增強：在表格上方增加搜尋框和狀態標籤切換
    if not df.empty:
        # 搜尋框和狀態標籤（並排顯示）
        filter_search_col1, filter_search_col2 = st.columns([2, 1])
        
        with filter_search_col1:
            # 專門過濾「賣方名稱」或「發票號碼」的搜尋框
            invoice_search = st.text_input(
                "🔍 搜尋賣方名稱或發票號碼",
                placeholder="輸入賣方名稱或發票號碼...",
                label_visibility="visible",
                key="invoice_search_input"
            )
        
        with filter_search_col2:
            # 狀態標籤切換（st.pills）
            status_filter = st.pills(
                "狀態篩選",
                options=["全部", "正常", "缺失"],
                default="全部",
                label_visibility="visible",
                key="status_filter_pills"
            )
    
    # 查詢條件、導出與刪除按鈕（並排顯示）
    if "preview_selected_count" not in st.session_state:
        st.session_state.preview_selected_count = 0
    delete_button_top = False  # 預設為未點擊

    filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([2, 1, 1, 1, 1])
    with filter_col1:
        search = st.text_input("🔍 關鍵字搜尋", placeholder="號碼/賣方/檔名...", label_visibility="hidden")
        # 刪除按鈕：放在搜尋欄下方，貼近查詢操作
        if not df.empty:
            preview_selected = st.session_state.get("preview_selected_count", 0)
            st.write("")  # 與輸入框拉開距離
            if preview_selected > 0:
                delete_button_top = st.button(
                    f"🗑️ 刪除 {preview_selected} 條",
                    type="primary",
                    use_container_width=True,
                    help="刪除已選中的數據",
                    key="delete_button_top"
                )
            else:
                st.button(
                    "🗑️ 刪除",
                    disabled=True,
                    use_container_width=True,
                    help="請先勾選要刪除的記錄",
                    key="delete_button_top_disabled"
                )
                delete_button_top = False
    with filter_col2:
        # 初始化日期區間狀態
        if "date_range_start" not in st.session_state:
            st.session_state.date_range_start = None
        if "date_range_end" not in st.session_state:
            st.session_state.date_range_end = None
        
        # 準備日期區間值（避免傳入 None 元組）
        date_start_val = st.session_state.get("date_range_start")
        date_end_val = st.session_state.get("date_range_end")
        
        # 日期區間選擇器（自定義日期區間，默認顯示全部）
        if date_start_val is not None and date_end_val is not None:
            # 兩個日期都有值，傳入元組
            date_range = st.date_input(
                "🕒 時間範圍（按發票日期）",
                value=(date_start_val, date_end_val),
                help="選擇開始日期和結束日期。不選擇日期時默認顯示全部數據。",
                label_visibility="visible"
            )
        else:
            # 至少有一個是 None，不傳 value 參數（默認顯示全部）
            date_range = st.date_input(
                "🕒 時間範圍（按發票日期）",
                help="選擇開始日期和結束日期。不選擇日期時默認顯示全部數據。",
                label_visibility="visible"
            )
        
        # 處理日期區間（date_input 可能返回單一日期或元組）
        if isinstance(date_range, tuple) and len(date_range) == 2:
            date_start, date_end = date_range
            st.session_state.date_range_start = date_start
            st.session_state.date_range_end = date_end
        elif isinstance(date_range, tuple) and len(date_range) == 1:
            # 只選了一個日期，設為開始和結束都是同一天
            date_start = date_range[0]
            date_end = date_range[0]
            st.session_state.date_range_start = date_start
            st.session_state.date_range_end = date_end
        elif date_range is not None:
            # 單一日期對象
            date_start = date_range
            date_end = date_range
            st.session_state.date_range_start = date_start
            st.session_state.date_range_end = date_end
        else:
            # 用戶清空了日期選擇，恢復為默認顯示全部
            date_start = None
            date_end = None
            st.session_state.date_range_start = None
            st.session_state.date_range_end = None
    with filter_col3:
        st.write("")  # 空白行用於對齊
        if not df.empty:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 導出CSV", csv_data, "invoice_report.csv", 
                             mime="text/csv", use_container_width=True, help="導出當前數據為CSV文件")
    with filter_col4:
        st.write("")  # 空白行用於對齊
        if not df.empty:
            def generate_excel():
                # 使用統計結果（如有），否則使用當前表格數據
                export_df = df_stats.copy() if 'df_stats' in locals() and not df_stats.empty else df.copy()
                if export_df.empty:
                    return b""

                # 構建符合國稅局欄位結構的表格
                # 優先使用現有「銷售額」「稅額」「總計」，若缺失則由總計推算
                total_series = pd.to_numeric(export_df.get('總計', 0), errors='coerce').fillna(0)
                subtotal_series = pd.to_numeric(export_df.get('銷售額', 0), errors='coerce').fillna(0)
                tax_series = pd.to_numeric(export_df.get('稅額', 0), errors='coerce').fillna(0)

                # 如果「銷售額」或「稅額」為 0，依據總計自動計算
                need_recalc = ((subtotal_series == 0) | (tax_series == 0)) & (total_series > 0)
                if need_recalc.any():
                    calc_tax = (total_series - (total_series / 1.05)).round(0)
                    calc_subtotal = (total_series - calc_tax).round(0)
                    tax_series = tax_series.where(~need_recalc, calc_tax)
                    subtotal_series = subtotal_series.where(~need_recalc, calc_subtotal)

                export_df['銷售額(未稅)'] = subtotal_series
                export_df['稅額'] = tax_series
                export_df['總計'] = total_series

                # 按常見報帳格式排列列順序
                desired_order = [
                    "日期", "發票號碼", "賣方名稱", "賣方統編",
                    "銷售額(未稅)", "稅額", "總計",
                    "會計科目", "類型", "備註"
                ]
                columns = [c for c in desired_order if c in export_df.columns]
                export_df = export_df[columns].copy()

                # 導出為 Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    export_df.to_excel(writer, index=False, sheet_name="發票報表")
                    ws = writer.sheets["發票報表"]

                    # 標題樣式與列寬
                    header_font = Font(bold=True)
                    for col_cells in ws.iter_cols(min_row=1, max_row=1):
                        for cell in col_cells:
                            cell.font = header_font
                            # 自動列寬（簡化處理）
                            col_letter = cell.column_letter
                            ws.column_dimensions[col_letter].width = max(12, len(str(cell.value)) + 4)

                    # 金額欄位右對齊並加入千分位
                    amount_headers = {"銷售額(未稅)", "稅額", "總計"}
                    header_map = {cell.value: cell.column for cell in ws[1] if cell.value}
                    for header in amount_headers:
                        col_idx = header_map.get(header)
                        if col_idx is None:
                            continue
                        for cell in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                            c = cell[0]
                            c.number_format = '#,##0'
                            c.alignment = Alignment(horizontal='right')

                return output.getvalue()

            excel_data = generate_excel()
            st.download_button(
                "📊 導出Excel",
                excel_data,
                f"invoice_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="導出符合國稅局欄位結構的 Excel 報表"
            )
    with filter_col5:
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
                    
                    # 詳細數據表格 - 修改表格 Header（包含銷售額(未稅)、稅額、總計）
                    export_df = df.copy()
                    # 調整列寬以適應新的列：日期、發票號碼、賣方統編、銷售額(未稅)、稅額、總計、備註
                    col_widths = [25, 30, 30, 30, 25, 25, 25]
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 10)
                        headers = ["日期", "發票號碼", "賣方統編", "銷售額(未稅)", "稅額", "總計", "備註"]
                    else:
                        pdf.set_font('Arial', 'B', 10)
                        headers = ["Date", "Invoice No", "Seller UBN", "Net Amount (Excl. Tax)", "Tax", "Total", "Note"]
                    
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
                    
                    # 每一行數據自動計算銷售額(未稅)、稅額、總計
                    for _, row in export_df.iterrows():
                        # 優先使用現有欄位，否則由總計推算
                        total_val = pd.to_numeric(row.get('總計', row.get('total', 0)), errors='coerce')
                        subtotal_val = pd.to_numeric(row.get('銷售額', row.get('subtotal', 0)), errors='coerce')
                        tax_val = pd.to_numeric(row.get('稅額', row.get('tax', 0)), errors='coerce')

                        if pd.isna(total_val):
                            total_val = 0

                        if (pd.isna(subtotal_val) or subtotal_val == 0) or (pd.isna(tax_val) or tax_val == 0):
                            if total_val > 0:
                                # 依據總計反推稅額與未稅金額（預設稅率 5%）
                                tax_val = round(total_val - (total_val / 1.05))
                                subtotal_val = total_val - tax_val
                            else:
                                subtotal_val = 0
                                tax_val = 0
                        
                        # 獲取其他字段
                        date_str = pdf_safe_value(row.get('日期', ''), 'No')[:10]
                        invoice_no = pdf_safe_value(row.get('發票號碼', ''), 'No')[:15]
                        seller_ubn = pdf_safe_value(row.get('賣方統編', ''), 'No')[:15]
                        note = pdf_safe_value(row.get('備註', '') or row.get('會計科目', '') or row.get('類型', ''), '')[:15]
                        
                        # 格式化金額
                        net_amount_str = f"${subtotal_val:,.0f}"
                        tax_str = f"${tax_val:,.0f}"
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
                st.download_button(
                    "📄 導出PDF",
                    pdf_data,
                    f"invoice_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="導出當前數據為PDF報告"
                )
            else:
                st.info("📄 PDF", help="需要安裝 fpdf2")
    
    # 在移除image相關的列之前，先保存image_path用於圖片預覽
    image_path_col = None
    if not df.empty and 'image_path' in df.columns:
        image_path_col = df['image_path'].copy()
    
    # 移除image相關的列（不在表格中直接顯示，但用於圖片預覽）
    if not df.empty:
        columns_to_drop = ['image_data', 'imageData']  # 只移除大數據列，保留image_path用於預覽
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])
            if df_with_id is not None and col in df_with_id.columns:
                df_with_id = df_with_id.drop(columns=[col])
        
        # 移除ID列、user_id列與檔案名稱列（不在表格中顯示，但保留在df_with_id中）
        # 「銷售額(未稅)」「稅額」「總計」保留在前端表格中顯示
        columns_to_hide = ['id', 'user_id', 'user_email', '檔案名稱']
        for col in columns_to_hide:
            if col in df.columns:
                df = df.drop(columns=[col])
    
    # 修復 Bug #3: 在篩選前保存原始索引映射，以便刪除功能正常工作
    # 將df_with_id保存到session_state，確保刪除功能可以訪問
    if 'df_with_id' in locals() and df_with_id is not None:
        # 創建索引到ID的映射，保存到session_state
        if 'id' in df_with_id.columns:
            # 創建一個映射：df的索引 -> id
            index_to_id_map = {}
            for idx in df_with_id.index:
                if idx in df.index:
                    index_to_id_map[idx] = df_with_id.loc[idx, 'id']
            st.session_state.index_to_id_map = index_to_id_map
        st.session_state.df_with_id = df_with_id.copy()
    
    if not df.empty and df_with_id is not None:
        # 保存原始索引到df中（在篩選前），用於刪除功能
        df['_original_index'] = df.index
    
    # 手動在記憶體中篩選（避免 SQL 過於複雜出錯）
    if not df.empty:
        # 1. 通用關鍵字搜尋（保留原有功能）
        if search:
            df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        
        # 2. 專門搜尋「賣方名稱」或「發票號碼」
        invoice_search = st.session_state.get("invoice_search_input", "")
        if invoice_search and invoice_search.strip():
            search_term = invoice_search.strip().lower()
            if "賣方名稱" in df.columns and "發票號碼" in df.columns:
                # 同時搜尋賣方名稱和發票號碼
                df = df[
                    df["賣方名稱"].astype(str).str.lower().str.contains(search_term, na=False) |
                    df["發票號碼"].astype(str).str.lower().str.contains(search_term, na=False)
                ]
            elif "賣方名稱" in df.columns:
                df = df[df["賣方名稱"].astype(str).str.lower().str.contains(search_term, na=False)]
            elif "發票號碼" in df.columns:
                df = df[df["發票號碼"].astype(str).str.lower().str.contains(search_term, na=False)]
        
        # 3. 狀態標籤過濾（正常/缺失）
        status_filter = st.session_state.get("status_filter_pills", "全部")
        if status_filter != "全部" and "狀態" in df.columns:
            if status_filter == "正常":
                # 過濾出狀態為「正常」的發票（包含 ✅ 正常）
                df = df[df["狀態"].astype(str).str.contains("正常", na=False)]
            elif status_filter == "缺失":
                # 過濾出狀態為「缺失」的發票（包含 ❌ 缺失、缺漏等）
                df = df[df["狀態"].astype(str).str.contains("缺失|缺漏|❌", na=False, regex=True)]
        
        # 4. 日期區間過濾（使用 session_state 中的日期範圍）
        date_start = st.session_state.get("date_range_start")
        date_end = st.session_state.get("date_range_end")
        
        if date_start is not None and date_end is not None and "日期" in df.columns:
            date_col = "日期"
            
            try:
                # 將日期列轉換為日期格式
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce', format='%Y/%m/%d')
                df = df.dropna(subset=[date_col])  # 移除無法解析的日期
                
                # 使用日期區間篩選（包含開始和結束日期）
                df = df[(df[date_col].dt.date >= date_start) & (df[date_col].dt.date <= date_end)]
            except Exception as e:
                # 如果日期格式不正確，嘗試字符串匹配
                date_start_str = date_start.strftime("%Y/%m/%d")
                date_end_str = date_end.strftime("%Y/%m/%d")
                
                # 轉換為字符串後進行範圍比較（較不精確，但作為備選方案）
                def date_in_range(date_str):
                    try:
                        date_val = datetime.strptime(str(date_str), "%Y/%m/%d").date()
                        return date_start <= date_val <= date_end
                    except:
                        return False
                
                df = df[df[date_col].astype(str).apply(date_in_range)]
    
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
        
        # 再次確保移除image相關的大數據列（防止遺漏），但保留image_path用於預覽
        columns_to_drop = ['image_data', 'imageData']  # 只移除大數據列
        for col in columns_to_drop:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # 添加圖片預覽列（如果image_path存在）
        if 'image_path' in df.columns:
            # 創建圖片預覽列，將image_path轉換為可用的URL或路徑
            def get_image_path(x):
                """獲取有效的圖片路徑"""
                if pd.isna(x) or not x:
                    return None
                path_str = str(x).strip()
                if path_str and os.path.exists(path_str):
                    return path_str
                return None
            
            df['圖片預覽'] = df['image_path'].apply(get_image_path)
            # 暫時保留image_path列，稍後在column_config中配置為ImageColumn
        elif image_path_col is not None:
            # 如果image_path被移除了，但我們有備份，則恢復它
            try:
                # 確保長度匹配
                if len(image_path_col) == len(df):
                    df['image_path'] = image_path_col.values
                else:
                    # 如果長度不匹配，嘗試通過索引對齊
                    df['image_path'] = None
                    for idx in df.index:
                        if idx in image_path_col.index:
                            df.loc[idx, 'image_path'] = image_path_col.loc[idx]
                
                def get_image_path(x):
                    """獲取有效的圖片路徑"""
                    if pd.isna(x) or not x:
                        return None
                    path_str = str(x).strip()
                    if path_str and os.path.exists(path_str):
                        return path_str
                    return None
                
                df['圖片預覽'] = df['image_path'].apply(get_image_path)
            except Exception as e:
                # 如果恢復失敗，創建空列
                df['圖片預覽'] = None
        
        # 將狀態列轉換為帶顏色的小圓點標籤
        if "狀態" in df.columns:
            def format_status_with_dot(status):
                """將狀態轉換為帶顏色小圓點的格式"""
                if pd.isna(status):
                    return "⚪ 未知"
                status_str = str(status).strip()
                if "正常" in status_str or "✅" in status_str:
                    return "🟢 正常"
                elif "缺失" in status_str or "缺漏" in status_str or "❌" in status_str:
                    return "🔴 缺失"
                else:
                    return f"⚪ {status_str}"
            
            df['狀態'] = df['狀態'].apply(format_status_with_dot)
        
        # 確保ID列保留在df中（用於刪除功能），但不在顯示中顯示
        # 從df_with_id中獲取id列（如果存在）
        if df_with_id is not None and 'id' in df_with_id.columns:
            # 確保df中有id列（用於刪除功能）
            if 'id' not in df.columns:
                # 通過索引匹配，將id從df_with_id複製到df
                df = df.copy()
                df['id'] = None
                for idx in df.index:
                    if idx in df_with_id.index:
                        df.loc[idx, 'id'] = df_with_id.loc[idx, 'id']
        
        # 移除其他不需要顯示的列（保留「總計」供前端表格使用）
        columns_to_hide = ['user_id', 'user_email', '檔案名稱']
        for col in columns_to_hide:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # 自動計算「未稅金額」與「稅額 (5%)」
        if "總計" in df.columns:
            # 將總計轉換為數值
            total_series = pd.to_numeric(df["總計"], errors="coerce").fillna(0)
            
            # 計算稅額 (5%)：如果已有稅額欄位且不為0，使用現有值；否則從總計反推
            if "稅額" in df.columns:
                existing_tax = pd.to_numeric(df["稅額"], errors="coerce").fillna(0)
                # 如果稅額為0但總計不為0，則計算稅額
                tax_series = existing_tax.where((existing_tax > 0) | (total_series == 0), 
                                                (total_series - (total_series / 1.05)).round(0))
            else:
                # 沒有稅額欄位，從總計反推
                tax_series = (total_series - (total_series / 1.05)).round(0)
            
            # 計算未稅金額 = 總計 - 稅額
            subtotal_series = (total_series - tax_series).round(0)
            
            # 添加到 DataFrame（保持為數值，以便在 column_config 中使用 NumberColumn）
            df["未稅金額"] = subtotal_series
            df["稅額 (5%)"] = tax_series
            
            # 計算「總計」與上一行的變化百分比（仿照廣告看板）
            def calculate_change_percentage(current, previous):
                """計算變化百分比"""
                if pd.isna(current) or current == 0:
                    return None
                if pd.isna(previous) or previous == 0:
                    return None
                change = ((current - previous) / previous) * 100
                return round(change, 1)
            
            # 計算變化百分比（與上一行對比）
            change_percentages = []
            for i in range(len(total_series)):
                if i == 0:
                    change_percentages.append(None)  # 第一行沒有上一行可比較
                else:
                    prev_total = total_series.iloc[i-1]
                    curr_total = total_series.iloc[i]
                    change_pct = calculate_change_percentage(curr_total, prev_total)
                    change_percentages.append(change_pct)
            
            # 創建變化百分比列（格式化為帶顏色的字符串）
            def format_change_pct(change_pct):
                """格式化變化百分比，帶顏色標記"""
                if change_pct is None or pd.isna(change_pct):
                    return ""
                if change_pct > 0:
                    return f"🟢 +{change_pct}%"
                elif change_pct < 0:
                    return f"🔴 {change_pct}%"
                else:
                    return "⚪ 0%"
            
            df["總計變化"] = [format_change_pct(cp) for cp in change_percentages]
        
        # 為問題行添加警示圖示（發票號碼為 "No" 或狀態為 "缺失"）
        if "發票號碼" in df.columns:
            def add_warning_icon(invoice_no, status):
                """為問題行添加警示圖示"""
                invoice_str = str(invoice_no).strip() if pd.notna(invoice_no) else ""
                status_str = str(status).strip() if pd.notna(status) else ""
                
                is_problem = (invoice_str == "No" or invoice_str == "" or 
                             "缺失" in status_str or "❌" in status_str or "缺漏" in status_str)
                
                if is_problem:
                    return "⚠️ " + str(invoice_no) if invoice_str != "No" else "⚠️ No"
                return str(invoice_no)
            
            df["發票號碼"] = df.apply(
                lambda row: add_warning_icon(row.get("發票號碼", ""), row.get("狀態", "")), 
                axis=1
            )
        
        # 調整列順序：選取 -> 圖片預覽 -> 狀態 -> 其他列（id列保留但不顯示）
        if "選取" not in df.columns: 
            df.insert(0, "選取", False)
        
        # 將圖片預覽列移到選取列之後（如果存在）
        if "圖片預覽" in df.columns:
            cols = df.columns.tolist()
            cols.remove("圖片預覽")
            select_idx = cols.index("選取") if "選取" in cols else 0
            cols.insert(select_idx + 1, "圖片預覽")
            df = df[cols]
        
        # 將狀態列移到圖片預覽列之後（如果圖片預覽存在）或選取列之後
        if "狀態" in df.columns:
            cols = df.columns.tolist()
            cols.remove("狀態")
            # 找到圖片預覽或選取列的位置，在其後插入狀態
            if "圖片預覽" in cols:
                preview_idx = cols.index("圖片預覽")
                cols.insert(preview_idx + 1, "狀態")
            elif "選取" in cols:
                select_idx = cols.index("選取")
                cols.insert(select_idx + 1, "狀態")
            else:
                cols.insert(0, "狀態")
            df = df[cols]
        
        # 調整金額相關欄位的順序：銷售額 -> 未稅金額 -> 稅額 -> 稅額 (5%) -> 總計
        if "未稅金額" in df.columns and "稅額 (5%)" in df.columns:
            cols = df.columns.tolist()
            # 移除這些欄位
            for col in ["銷售額", "未稅金額", "稅額", "稅額 (5%)", "總計"]:
                if col in cols:
                    cols.remove(col)
            
            # 找到合適的位置插入（在「狀態」之後，其他欄位之前）
            try:
                status_idx = cols.index("狀態")
                insert_pos = status_idx + 1
            except:
                insert_pos = 1
            
            # 按順序插入金額欄位（包含總計變化）
            amount_cols = ["銷售額", "未稅金額", "稅額", "稅額 (5%)", "總計"]
            for i, col in enumerate(amount_cols):
                if col in df.columns:
                    cols.insert(insert_pos + i, col)
            
            # 在「總計」之後插入「總計變化」列
            if "總計" in cols and "總計變化" in df.columns:
                total_idx = cols.index("總計")
                cols.insert(total_idx + 1, "總計變化")
            
            df = df[cols]
        
        # 在刪除功能使用後，移除 _original_index 列（如果存在）
        if '_original_index' in df.columns:
            df = df.drop(columns=['_original_index'])
        
        # 不再顯示標題和選中數量
        if st.session_state.get("show_delete_confirm", False):
            delete_records = st.session_state.get("delete_records", [])
            delete_count = st.session_state.get("delete_count", 0)
            
            # 使用裝飾器方式定義刪除確認對話框
            @st.dialog("⚠️ 確認刪除")
            def delete_confirm_dialog():
                st.warning(f"確定要刪除選中的 {delete_count} 條數據嗎？")
                st.error("⚠️ 此操作不可恢復！")
                
                # 顯示要刪除的記錄預覽（顯示id、發票號碼和日期）
                if delete_records:
                    with st.expander("查看要刪除的記錄", expanded=False):
                        # 準備預覽數據，將id、發票號碼、日期格式化顯示
                        preview_data = []
                        for rec in delete_records:
                            preview_row = {}
                            if 'id' in rec and rec['id'] is not None:
                                preview_row['ID'] = rec['id']
                            if 'invoice_number' in rec and rec.get('invoice_number'):
                                preview_row['發票號碼'] = rec['invoice_number']
                            else:
                                preview_row['發票號碼'] = '(空)'
                            if 'date' in rec and rec.get('date'):
                                preview_row['日期'] = rec['date']
                            else:
                                preview_row['日期'] = '(空)'
                            preview_data.append(preview_row)
                        
                        if preview_data:
                            preview_df = pd.DataFrame(preview_data)
                            st.dataframe(preview_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("無法顯示記錄詳情")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ 確認刪除", type="primary", use_container_width=True):
                        # 執行刪除：使用發票號碼+日期+用戶郵箱組合刪除（最可靠的方式）
                        user_email = st.session_state.get('user_email', 'default_user')
                        deleted_count = 0
                        errors = []
                        
                        if st.session_state.use_memory_mode:
                            # 內存模式：從列表中刪除（優先使用id，否則使用發票號碼+日期）
                            original_count = len(st.session_state.local_invoices)
                            
                            def should_delete_invoice(inv):
                                """判斷是否應該刪除此發票"""
                                for rec in delete_records:
                                    # 優先使用id匹配
                                    if 'id' in rec and rec['id'] is not None:
                                        if inv.get('id') == rec['id'] and inv.get('user_email', inv.get('user_id', 'default_user')) == user_email:
                                            return True
                                    # 如果沒有id，使用發票號碼+日期組合
                                    elif 'invoice_number' in rec and 'date' in rec:
                                        inv_num = str(inv.get('invoice_number', '')).strip()
                                        inv_date = str(inv.get('date', '')).strip()
                                        rec_num = str(rec.get('invoice_number', '')).strip()
                                        rec_date = str(rec.get('date', '')).strip()
                                        
                                        if (inv_num == rec_num or (not inv_num and not rec_num)) and \
                                           (inv_date == rec_date or (not inv_date and not rec_date)) and \
                                           inv.get('user_email', inv.get('user_id', 'default_user')) == user_email:
                                            return True
                                    # 如果只有發票號碼（數據不完整）
                                    elif 'invoice_number' in rec and rec.get('invoice_number'):
                                        inv_num = str(inv.get('invoice_number', '')).strip()
                                        rec_num = str(rec.get('invoice_number', '')).strip()
                                        inv_date = str(inv.get('date', '')).strip()
                                        
                                        if inv_num == rec_num and (not inv_date or inv_date in ['', 'No', 'N/A']) and \
                                           inv.get('user_email', inv.get('user_id', 'default_user')) == user_email:
                                            return True
                                    # 如果只有日期（數據不完整）
                                    elif 'date' in rec and rec.get('date'):
                                        inv_date = str(inv.get('date', '')).strip()
                                        rec_date = str(rec.get('date', '')).strip()
                                        inv_num = str(inv.get('invoice_number', '')).strip()
                                        
                                        if inv_date == rec_date and (not inv_num or inv_num in ['', 'No', 'N/A']) and \
                                           inv.get('user_email', inv.get('user_id', 'default_user')) == user_email:
                                            return True
                                return False
                            
                            st.session_state.local_invoices = [
                                inv for inv in st.session_state.local_invoices 
                                if not should_delete_invoice(inv)
                            ]
                            deleted_count = original_count - len(st.session_state.local_invoices)
                        else:
                            # 數據庫模式：優先使用id刪除（支持數據不完整），否則使用發票號碼+日期+用戶郵箱組合
                            try:
                                path = get_db_path()
                                is_uri = path.startswith("file:") and "mode=memory" in path
                                conn = sqlite3.connect(path, timeout=30, uri=is_uri, check_same_thread=False)
                                cursor = conn.cursor()
                                
                                # 逐條刪除
                                for rec in delete_records:
                                    try:
                                        # 優先使用id刪除（最可靠，支持數據不完整）
                                        if 'id' in rec and rec['id'] is not None:
                                            cursor.execute(
                                                "DELETE FROM invoices WHERE id=? AND user_email=?",
                                                (rec['id'], user_email)
                                            )
                                        # 如果沒有id，使用發票號碼+日期+用戶郵箱組合
                                        elif 'invoice_number' in rec and 'date' in rec and rec.get('invoice_number') and rec.get('date'):
                                            cursor.execute(
                                                "DELETE FROM invoices WHERE user_email=? AND invoice_number=? AND date=?",
                                                (user_email, rec['invoice_number'], rec['date'])
                                            )
                                        # 如果只有發票號碼（數據不完整）
                                        elif 'invoice_number' in rec and rec.get('invoice_number'):
                                            cursor.execute(
                                                "DELETE FROM invoices WHERE user_email=? AND invoice_number=? AND (date IS NULL OR date='' OR date='No')",
                                                (user_email, rec['invoice_number'])
                                            )
                                        # 如果只有日期（數據不完整）
                                        elif 'date' in rec and rec.get('date'):
                                            cursor.execute(
                                                "DELETE FROM invoices WHERE user_email=? AND date=? AND (invoice_number IS NULL OR invoice_number='' OR invoice_number='No')",
                                                (user_email, rec['date'])
                                            )
                                        else:
                                            errors.append("無法確定要刪除的記錄（缺少必要的標識信息）")
                                            continue
                                        
                                        if cursor.rowcount > 0:
                                            deleted_count += cursor.rowcount
                                        else:
                                            # 記錄未找到的記錄信息
                                            rec_info = f"ID: {rec.get('id', 'N/A')}, 發票號碼: {rec.get('invoice_number', 'N/A')}, 日期: {rec.get('date', 'N/A')}"
                                            errors.append(f"未找到記錄: {rec_info}")
                                    except Exception as e:
                                        rec_info = f"ID: {rec.get('id', 'N/A')}, 發票號碼: {rec.get('invoice_number', 'N/A')}, 日期: {rec.get('date', 'N/A')}"
                                        errors.append(f"刪除失敗（{rec_info}）: {str(e)}")
                                
                                conn.commit()
                                conn.close()
                                
                                if deleted_count == 0 and not errors:
                                    errors.append("未找到要刪除的記錄，可能已被刪除或數據不匹配")
                                    
                            except Exception as e:
                                errors.append(f"刪除失敗: {str(e)}")
                        
                        # 清理狀態
                        st.session_state.show_delete_confirm = False
                        if "delete_records" in st.session_state:
                            del st.session_state.delete_records
                        if "delete_count" in st.session_state:
                            del st.session_state.delete_count
                        
                        if deleted_count > 0:
                            st.success(f"✅ 已刪除 {deleted_count} 條數據")
                        else:
                            st.warning("⚠️ 未找到要刪除的記錄，可能已被刪除或數據不匹配")
                        
                        if errors:
                            for err in errors:
                                st.error(err)
                        
                        time.sleep(0.5)
                        st.rerun()
                
                with col2:
                    if st.button("❌ 取消", use_container_width=True):
                        # 取消刪除，清理狀態
                        st.session_state.show_delete_confirm = False
                        if "delete_records" in st.session_state:
                            del st.session_state.delete_records
                        if "delete_count" in st.session_state:
                            del st.session_state.delete_count
                        st.rerun()
            
            # 調用對話框函數
            delete_confirm_dialog()
        
        # 保存原始數據的副本用於比較（不包含ID列）
        original_df_copy = df.copy()
        
        # 處理日期列：嘗試轉換為日期類型（先創建 df_for_editor）
        df_for_editor = df.copy()
        
        # 準備列配置（不包含ID列、user_id列、檔案名稱列）
        # 金額類數字右對齊，文字類左對齊
        column_config = { 
            "選取": st.column_config.CheckboxColumn("選取", default=False),
            "銷售額": st.column_config.NumberColumn("銷售額", format="$%d"),
            "稅額": st.column_config.NumberColumn("稅額", format="$%d"),
            "未稅金額": st.column_config.NumberColumn("未稅金額", format="$%d"),
            "稅額 (5%)": st.column_config.NumberColumn("稅額 (5%)", format="$%d"),
            "總計": st.column_config.NumberColumn("總計", format="$%d"),
            "總計變化": st.column_config.TextColumn("總計變化", width="small", help="與上一行對比變化百分比"),
            "備註": st.column_config.TextColumn("備註", width="medium"),
            "建立時間": st.column_config.DatetimeColumn("建立時間", format="YYYY/MM/DD HH:mm")
        }
        
        # 文字類欄位左對齊配置
        text_columns = ["賣方名稱", "發票號碼", "賣方統編", "類型", "會計科目", "狀態", "備註"]
        for col in text_columns:
            if col in df_for_editor.columns and col not in column_config:
                column_config[col] = st.column_config.TextColumn(col, width="medium")
        
        # 添加圖片預覽列配置（如果存在）
        if "圖片預覽" in df_for_editor.columns:
            column_config["圖片預覽"] = st.column_config.ImageColumn(
                "圖片預覽",
                help="發票圖片預覽",
                width="small"
            )
        
        # 添加狀態列配置（帶顏色小圓點）
        if "狀態" in df_for_editor.columns:
            column_config["狀態"] = st.column_config.TextColumn(
                "狀態",
                help="🟢 正常 | 🔴 缺失",
                width="small"
            )
        
        # 確保id列在df_for_editor中（用於刪除功能），但不在column_config中配置（隱藏顯示）
        # 注意：如果列不在column_config中，Streamlit會自動隱藏它
        # 但為了確保ID列可用於刪除功能，我們需要確保它在df_for_editor中
        if "id" in df_for_editor.columns:
            # id列保留但不配置，這樣它會隱藏顯示但仍然可用於刪除功能
            # 不添加id到column_config，這樣它會被隱藏
            pass
        
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
        
        # 添加 JavaScript 來高亮問題行並設置列對齊（在表格渲染後執行）
        st.markdown("""
        <script>
        (function() {
            function formatTable() {
                const editor = document.querySelector('[data-testid="stDataEditor"]');
                if (editor) {
                    const rows = editor.querySelectorAll('tbody tr');
                    const headerRow = editor.querySelector('thead tr');
                    
                    // 獲取表頭列名，用於確定列索引
                    const headers = [];
                    if (headerRow) {
                        headerRow.querySelectorAll('th').forEach(function(th) {
                            headers.push(th.textContent.trim());
                        });
                    }
                    
                    // 定義金額類欄位（需要右對齊）
                    const amountColumns = ['銷售額', '稅額', '未稅金額', '稅額 (5%)', '總計'];
                    // 定義變化百分比欄位（需要居中對齊）
                    const changeColumns = ['總計變化'];
                    
                    rows.forEach(function(row) {
                        const cells = row.querySelectorAll('td');
                        let isWarning = false;
                        
                        cells.forEach(function(cell, index) {
                            const text = cell.textContent || cell.innerText || '';
                            
                            // 檢查是否為問題行
                            if (text.includes('⚠️') || text.includes('❌ 缺失') || text.includes('❌ 缺漏')) {
                                isWarning = true;
                            }
                            
                            // 設置列對齊
                            const columnName = headers[index] || '';
                            
                            // 金額類欄位右對齊
                            if (amountColumns.includes(columnName)) {
                                cell.style.textAlign = 'right';
                            }
                            // 變化百分比欄位居中對齊
                            else if (changeColumns.includes(columnName)) {
                                cell.style.textAlign = 'center';
                                cell.style.fontSize = '13px';
                            }
                            // 文字類欄位左對齊（默認）
                            else {
                                cell.style.textAlign = 'left';
                            }
                        });
                        
                        // 高亮問題行
                        if (isWarning) {
                            row.style.backgroundColor = 'rgba(234, 67, 53, 0.15)';
                            row.style.borderLeft = '4px solid #EA4335';
                            row.addEventListener('mouseenter', function() {
                                this.style.backgroundColor = 'rgba(234, 67, 53, 0.25)';
                            });
                            row.addEventListener('mouseleave', function() {
                                this.style.backgroundColor = 'rgba(234, 67, 53, 0.15)';
                            });
                        }
                    });
                }
            }
            
            // 等待表格渲染完成後執行
            setTimeout(formatTable, 500);
            // 監聽表格更新
            const observer = new MutationObserver(formatTable);
            const targetNode = document.querySelector('[data-testid="stDataEditor"]');
            if (targetNode) {
                observer.observe(targetNode, { childList: true, subtree: true });
            }
        })();
        </script>
        """, unsafe_allow_html=True)
        
        # 檢查並清理 DataFrame 的列名（確保沒有重複或無效列名）
        if df_for_editor.empty:
            # 如果 DataFrame 為空，創建一個空的 DataFrame 用於顯示
            ed_df = st.data_editor(
                pd.DataFrame(),
                use_container_width=True,
                hide_index=True,
                height=500,
                key="data_editor"
            )
        else:
            # 檢查並修復重複的列名
            if df_for_editor.columns.duplicated().any():
                # 如果有重複的列名，重命名它們
                cols = pd.Series(df_for_editor.columns)
                for dup in cols[cols.duplicated()].unique():
                    cols[cols[cols == dup].index.values.tolist()] = [dup if i == 0 else f"{dup}_{i}" 
                                                                     for i in range(sum(cols == dup))]
                df_for_editor.columns = cols
            
            # 清理列名：移除 None、空字符串或無效字符
            def clean_column_name(name):
                """清理列名"""
                if name is None:
                    return "unnamed"
                if not isinstance(name, str):
                    name = str(name)
                name = name.strip()
                if name == "":
                    return "unnamed"
                # 移除可能導致問題的特殊字符
                name = name.replace('\x00', '').replace('\n', ' ').replace('\r', ' ')
                return name
            
            # 清理所有列名
            df_for_editor.columns = [clean_column_name(col) for col in df_for_editor.columns]
            
            # 確保沒有重複（再次檢查）
            if df_for_editor.columns.duplicated().any():
                # 手動處理重複列名
                cols = list(df_for_editor.columns)
                seen = {}
                new_cols = []
                for col in cols:
                    if col in seen:
                        seen[col] += 1
                        new_cols.append(f"{col}_{seen[col]}")
                    else:
                        seen[col] = 0
                        new_cols.append(col)
                df_for_editor.columns = new_cols
            
            # 使用 column_order 隱藏 id 欄位，但在返回的資料中仍保留 id（供後端更新使用）
            visible_columns = [c for c in df_for_editor.columns if c != "id"]
            
            # 驗證列名：確保沒有 None、空字符串或無效字符
            def is_valid_column_name(name):
                """檢查列名是否有效"""
                if name is None:
                    return False
                if not isinstance(name, str):
                    return False
                if name.strip() == "":
                    return False
                return True
            
            visible_columns = [c for c in visible_columns if is_valid_column_name(c)]
            visible_columns = list(dict.fromkeys(visible_columns))  # 移除重複，保持順序
            
            # 確保 column_config 中的列也在 df_for_editor 中存在，且列名有效
            valid_column_config = {}
            for k, v in column_config.items():
                cleaned_key = clean_column_name(k)
                if cleaned_key in df_for_editor.columns and is_valid_column_name(cleaned_key):
                    valid_column_config[cleaned_key] = v
            
            # 如果沒有有效的列，使用默認行為（不傳 column_order）
            ed_df = st.data_editor(
                df_for_editor,
                use_container_width=True,
                hide_index=True,
                height=500,
                column_config=valid_column_config if valid_column_config else None,
                column_order=visible_columns if visible_columns else None,
                key="data_editor"
            )
        
        # 如果日期被轉換為日期類型，需要轉回字符串格式以便保存
        if "日期" in ed_df.columns and ed_df["日期"].dtype != object:
            ed_df["日期"] = ed_df["日期"].dt.strftime("%Y/%m/%d").fillna(df["日期"])
        
        df["選取"] = ed_df["選取"]
        
        # 檢查是否有選中的行
        selected_count = ed_df["選取"].sum() if "選取" in ed_df.columns else 0
        # 保存到session_state，用於下次顯示（如果數量改變，會觸發rerun更新按鈕）
        if st.session_state.get("preview_selected_count", 0) != selected_count:
            st.session_state.preview_selected_count = int(selected_count)
            # 如果選中數量改變且沒有點擊刪除按鈕，自動更新按鈕顯示
            if not delete_button_top:
                st.rerun()
        
        # 統一處理刪除邏輯（使用當前的選中數量）
        delete_button = delete_button_top
        
        if selected_count > 0 and delete_button:
            selected_rows = ed_df[ed_df["選取"]==True]
            # 收集要刪除的記錄信息（使用發票號碼+日期）
            records_to_delete = []
            user_email = st.session_state.get('user_email', 'default_user')
            
            for idx, row in selected_rows.iterrows():
                # 優先從df_with_id獲取原始數據（未經過fill_empty處理，避免"No"值）
                record_id = None
                invoice_number = None
                date = None
                
                # 方法1: 優先從df_with_id獲取id（最可靠的方式，支持數據不完整的記錄）
                if df_with_id is not None and idx in df_with_id.index:
                    # 優先獲取id字段（如果存在）
                    if 'id' in df_with_id.columns:
                        record_id = df_with_id.loc[idx, 'id']
                        if pd.isna(record_id):
                            record_id = None
                        else:
                            record_id = int(record_id) if record_id else None
                    
                    # 同時獲取發票號碼和日期（用於備選刪除方式）
                    if 'invoice_number' in df_with_id.columns:
                        invoice_number = df_with_id.loc[idx, 'invoice_number']
                    elif '發票號碼' in df_with_id.columns:
                        invoice_number = df_with_id.loc[idx, '發票號碼']
                    
                    if 'date' in df_with_id.columns:
                        date = df_with_id.loc[idx, 'date']
                    elif '日期' in df_with_id.columns:
                        date = df_with_id.loc[idx, '日期']
                
                # 方法2: 如果df_with_id中沒有，從df獲取（df已經重命名為中文列名）
                if record_id is None and df_with_id is not None and idx in df_with_id.index:
                    # 嘗試從df獲取id（如果df中有id列）
                    if 'id' in df.columns and idx in df.index:
                        record_id = df.loc[idx, 'id']
                        if pd.isna(record_id):
                            record_id = None
                        else:
                            record_id = int(record_id) if record_id else None
                
                if (not invoice_number or pd.isna(invoice_number) or str(invoice_number).strip() in ['', 'No', 'N/A', 'nan', 'None']):
                    if idx in df.index and '發票號碼' in df.columns:
                        invoice_number = df.loc[idx, '發票號碼']
                
                if (not date or pd.isna(date) or str(date).strip() in ['', 'No', 'N/A', 'nan', 'None']):
                    if idx in df.index and '日期' in df.columns:
                        date = df.loc[idx, '日期']
                
                # 方法3: 如果還是沒有，從ed_df獲取（最後備選）
                if (not invoice_number or pd.isna(invoice_number) or str(invoice_number).strip() in ['', 'No', 'N/A', 'nan', 'None']):
                    if '發票號碼' in row.index:
                        invoice_number = row.get('發票號碼')
                
                if (not date or pd.isna(date) or str(date).strip() in ['', 'No', 'N/A', 'nan', 'None']):
                    if '日期' in row.index:
                        date = row.get('日期')
                
                # 轉換為字符串並清理
                if invoice_number is not None and not pd.isna(invoice_number):
                    invoice_number = str(invoice_number).strip()
                    invoice_number = invoice_number.replace('No', '').replace('N/A', '').replace('nan', '').replace('None', '').strip()
                else:
                    invoice_number = ''
                
                if date is not None and not pd.isna(date):
                    # 如果日期是日期類型，轉換為字符串
                    if isinstance(date, pd.Timestamp) or hasattr(date, 'strftime'):
                        try:
                            date = date.strftime("%Y/%m/%d")
                        except:
                            date = str(date).strip()
                    else:
                        date = str(date).strip()
                    date = date.replace('No', '').replace('N/A', '').replace('nan', '').replace('None', '').strip()
                else:
                    date = ''
                
                # 允許刪除數據不完整的記錄：優先使用id，如果沒有id則使用發票號碼+日期組合
                # 如果都沒有，仍然嘗試添加（使用空值），讓刪除邏輯處理
                delete_record = {}
                if record_id is not None:
                    delete_record['id'] = record_id
                if invoice_number:
                    delete_record['invoice_number'] = invoice_number
                if date:
                    delete_record['date'] = date
                
                # 只要有任何一個標識符（id、發票號碼+日期、或至少一個字段），就允許刪除
                if delete_record:
                    records_to_delete.append(delete_record)
            
            if records_to_delete:
                # 顯示刪除確認對話框
                st.session_state.show_delete_confirm = True
                st.session_state.delete_records = records_to_delete
                st.session_state.delete_count = len(records_to_delete)
                st.rerun()
            else:
                st.warning("⚠️ 無法確定要刪除的記錄。請確保數據已正確加載。")
                # 調試信息
                with st.expander("🔍 調試信息", expanded=False):
                    st.write("**選中的行數:**", len(selected_rows))
                    st.write("**ed_df的列名:**", list(ed_df.columns))
                    st.write("**df的列名:**", list(df.columns) if 'df' in locals() else 'df未定義')
                    st.write("**df_with_id的列名:**", list(df_with_id.columns) if df_with_id is not None and not df_with_id.empty else 'df_with_id為None或空')
                    st.write("**選中的行數據（前3行）:**")
                    if not selected_rows.empty:
                        # 只顯示前3行，避免過多數據
                        display_cols = ['發票號碼', '日期'] if '發票號碼' in selected_rows.columns and '日期' in selected_rows.columns else list(selected_rows.columns)[:5]
                        st.dataframe(selected_rows[display_cols].head(3))
                    st.write("**提示:** 現在支持刪除數據不完整的記錄（即使發票號碼或日期為空）。如果仍然無法刪除，請檢查調試信息。")
        
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

