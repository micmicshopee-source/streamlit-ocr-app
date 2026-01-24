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

# --- 1. 系統佈局與初始化 ---
st.set_page_config(page_title="發票報帳小秘笈", page_icon="🧾", layout="wide")

if "db_error" not in st.session_state: st.session_state.db_error = None
if "db_path_mode" not in st.session_state: st.session_state.db_path_mode = "💾 本地磁碟"

# --- 2. 終極韌性資料庫連線器 ---
def get_db_path():
    if "current_db_path" not in st.session_state:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 改用 invoices_v2.db 以解決舊資料庫可能發生的 Disk I/O Error 鎖定問題
        db_file = os.path.join(base_dir, "invoices_v2.db")
        try:
            # 測試寫入權限
            test_path = db_file + ".test"
            with open(test_path, "w") as f: f.write("1")
            os.remove(test_path)
            st.session_state.current_db_path = db_file
            st.session_state.db_path_mode = "💾 本地磁碟"
        except:
            # 失敗則進入共用記憶體模式
            st.session_state.current_db_path = "file:invoice_mem?mode=memory&cache=shared"
            st.session_state.db_path_mode = "🧠 虛擬記憶體 (重啟會清空)"
    return st.session_state.current_db_path

def init_db():
    """初始化資料表，確保所有必要欄位存在"""
    path = get_db_path()
    is_uri = "mode=memory" in path
    try:
        conn = sqlite3.connect(path, timeout=30, uri=is_uri)
        conn.execute('''CREATE TABLE IF NOT EXISTS invoices
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT DEFAULT 'default_user', 
                        file_name TEXT, date TEXT, invoice_number TEXT, seller_name TEXT, seller_ubn TEXT,
                        subtotal REAL, tax REAL, total REAL, category TEXT, subject TEXT, status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        # 補全欄位
        for col, c_type in {'user_id': "TEXT", 'status': "TEXT", 'seller_ubn': "TEXT"}.items():
            try: conn.execute(f"ALTER TABLE invoices ADD COLUMN {col} {c_type}")
            except: pass
        conn.commit()
        conn.close()
    except Exception as e:
        st.session_state.db_error = f"初始化失敗: {str(e)}"

def run_query(query, params=(), is_select=True):
    path = get_db_path()
    is_uri = "mode=memory" in path
    try:
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False, uri=is_uri)
        if is_select:
            try:
                df = pd.read_sql_query(query, conn, params=params)
            except Exception as e:
                # 關鍵修復：如果發現沒表，自動初始化並重試
                if "no such table" in str(e):
                    init_db()
                    df = pd.read_sql_query(query, conn, params=params)
                else: raise e
            conn.close()
            st.session_state.db_error = None
            return df
        else:
            conn.execute(query, params)
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        err_msg = str(e)
        st.session_state.db_error = f"連線異常: {err_msg}"
        return pd.DataFrame() if is_select else False

# 程式啟動立即初始化
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
            except Exception as e: 
                last_err = str(e)
                debug_info.append(f"{ver}/{m_name}: {last_err}")
                continue
                
        return None, f"所有嘗試皆失敗。最後錯誤: {last_err} | 歷程: {'; '.join(debug_info)}"
    except Exception as e: return None, f"系統錯誤: {str(e)}"

# --- 4. 介面渲染 ---
DEFAULT_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

with st.sidebar:
    st.title("⚙️ 系統狀態")
    user = st.text_input("登入帳號", "default_user")
    
    # 優先使用 Streamlit Secrets
    if "GEMINI_API_KEY" in st.secrets:
        st.success("🔑 已使用 Secrets 金鑰")
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.text_input("Gemini API Key", DEFAULT_KEY, type="password")
        st.caption("建議在 Streamlit Secrets 設定 GEMINI_API_KEY")

    model = st.selectbox("辨識模型", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"])
    
    st.divider()
    # 這裡會觸發 run_query，若沒表會自動建表
    db_count_df = run_query("SELECT count(*) as count FROM invoices WHERE user_id = ?", (user,))
    if not db_count_df.empty:
        st.success(f"📊 已存數據: {db_count_df['count'][0]} 筆")
    
    if st.button("🗑️ 清空暫存資料庫"):
        try:
            os.remove("invoices.db")
            st.success("已清除！")
            time.sleep(1)
            st.rerun()
        except: pass


st.title("📑 發票收據報帳小秘笈 Pro")
col_up, col_main, col_stat = st.columns([1, 2.5, 1])

with col_up:
    st.subheader("📤 上傳辨識")
    files = st.file_uploader("批次選擇照片", type=["jpg","png","jpeg"], accept_multiple_files=True)
    if files and st.button("開始辨識 🚀", type="primary", use_container_width=True):
        
        # 初始化 session_state 用於存儲結果報告（如果還沒有的話）
        if "ocr_report" not in st.session_state: st.session_state.ocr_report = []
        
        success_count = 0
        fail_count = 0
        
        with st.status("AI 正在分析發票中...", expanded=True) as status:
            prog = st.progress(0)
            
            for idx, f in enumerate(files):
                st.write(f"正在處理: {f.name} ...")
                data, err = process_ocr(Image.open(f), f.name, model, api_key)
                
                if data:
                    def clean_n(v):
                        try: return float(str(v).replace(',','').replace('$',''))
                        except: return 0.0
                    q = "INSERT INTO invoices (user_id, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
                    run_query(q, (user, data["file_name"], data["date"], data["invoice_no"], data["seller_name"], data["seller_ubn"], 
                                clean_n(data["subtotal"]), clean_n(data["tax"]), clean_n(data["total"]), data["type"], data["category_suggest"], data["status"]), is_select=False)
                    st.write(f"✅ {f.name}: 成功 (${data.get('total', 0)})")
                    success_count += 1
                else:
                    st.error(f"❌ {f.name} 失敗: {err}")
                    st.session_state.ocr_report.append(f"{f.name}: {err}")
                    fail_count += 1
                
                prog.progress((idx+1)/len(files))
            
            status.update(label=f"處理完成! 成功: {success_count}, 失敗: {fail_count}", state="complete", expanded=True)
            
        if success_count > 0:
            time.sleep(1) # 讓使用者稍微看一下結果
            st.rerun()

with col_main:
    sc1, sc2 = st.columns([2, 1])
    search = sc1.text_input("🔍 關鍵字搜尋", placeholder="號碼/賣方/檔名...")
    t_filter = sc2.selectbox("🕒 時間範圍", ["全部", "今天", "本週", "本月"])
    
    df = run_query("SELECT * FROM invoices WHERE user_id = ? ORDER BY id DESC", (user,))
    # 手動在記憶體中篩選（避免 SQL 過於複雜出錯）
    if not df.empty:
        if search:
            df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        if t_filter != "全部":
            # 簡單日期過濾
            pass 
        
        st.subheader("📋 數據稽核報表")
        if not df.empty:
            mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態"}
            df = df.rename(columns=mapping)
            if "選取" not in df.columns: df.insert(0, "選取", False)
            
            if st.button("🗑️ 刪除選中數據"):
                ids = df[df["選取"]==True]["id"].tolist()
                for i in ids: run_query("DELETE FROM invoices WHERE id=?", (i,), is_select=False)
                st.rerun()
            
            ed_df = st.data_editor(df, use_container_width=True, hide_index=True, height=500, 
                                   column_config={"id": None, "選取": st.column_config.CheckboxColumn("選取", default=False)})
            df["選取"] = ed_df["選取"]
        else: st.warning("⚠️ 查無數據。")
    else: st.warning("⚠️ 目前無數據。請先嘗試上傳並辨識。")

with col_stat:
    st.subheader("📊 統計報表")
    if not df.empty and "總計" in df.columns:
        for c in ["總計", "稅額"]: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        m1, m2 = st.columns(2)
        m1.metric("累計金額", f"${df['總計'].sum():,.0f}")
        m2.metric("累計稅額", f"${df['稅額'].sum():,.0f}")
        st.divider()
        st.download_button("📥 導出 CSV", df.to_csv(index=False).encode('utf-8-sig'), "invoice_report.csv", use_container_width=True)
        chart = alt.Chart(df).mark_arc(innerRadius=40).encode(theta="count()", color="類型", tooltip=["類型", "count()"]).properties(height=200)
        st.altair_chart(chart, use_container_width=True)
