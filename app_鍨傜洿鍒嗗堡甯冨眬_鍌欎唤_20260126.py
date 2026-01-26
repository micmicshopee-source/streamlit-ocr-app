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

if "db_error" not in st.session_state: st.session_state.db_error = None
if "db_path_mode" not in st.session_state: st.session_state.db_path_mode = "💾 本地磁碟"
if "use_memory_mode" not in st.session_state: st.session_state.use_memory_mode = False
if "local_invoices" not in st.session_state: st.session_state.local_invoices = []
if "image_storage_dir" not in st.session_state: 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    st.session_state.image_storage_dir = os.path.join(base_dir, "invoice_images")
    os.makedirs(st.session_state.image_storage_dir, exist_ok=True)
if "last_edited_df_hash" not in st.session_state: st.session_state.last_edited_df_hash = None

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
            # 測試寫入權限
            test_path = db_file + ".test"
            with open(test_path, "w") as f: 
                f.write("1")
            os.remove(test_path)
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
    """初始化資料表，確保所有必要欄位存在"""
    if st.session_state.use_memory_mode:
        return True  # 使用內存模式，跳過數據庫初始化
    
    path = get_db_path()
    # 判斷是否為URI模式（只有明確包含mode=memory才是URI）
    # 普通文件路徑（如 invoices_v2.db）不是URI
    is_uri = path.startswith("file:") and "mode=memory" in path
    try:
        conn = sqlite3.connect(path, timeout=30, uri=is_uri, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS invoices
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT DEFAULT 'default_user', 
                        file_name TEXT, date TEXT, invoice_number TEXT, seller_name TEXT, seller_ubn TEXT,
                        subtotal REAL, tax REAL, total REAL, category TEXT, subject TEXT, status TEXT,
                        image_path TEXT, image_data BLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        # 補全欄位
        for col, c_type in {'user_id': "TEXT", 'status': "TEXT", 'seller_ubn': "TEXT", 
                            'image_path': "TEXT", 'image_data': "BLOB"}.items():
            try: cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {c_type}")
            except: pass
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.session_state.db_error = f"初始化失敗: {str(e)}"
        return False

def run_query(query, params=(), is_select=True):
    # 如果使用內存模式，使用 session_state 存儲
    if st.session_state.use_memory_mode:
        if is_select:
            # 處理 SELECT 查詢
            if "WHERE user_id" in query.upper():
                user_id = params[0] if params else "default_user"
                df = pd.DataFrame([inv for inv in st.session_state.local_invoices if inv.get('user_id') == user_id])
            else:
                df = pd.DataFrame(st.session_state.local_invoices)
            
            # 簡單的 ORDER BY 處理
            if "ORDER BY id DESC" in query.upper():
                if not df.empty and 'id' in df.columns:
                    df = df.sort_values('id', ascending=False)
            
            return df
        else:
            # INSERT 查詢會在調用處處理
            return True
    
    # 使用數據庫
    path = get_db_path()
    # 判斷是否為URI模式（只有明確包含mode=memory或file:前綴才是URI）
    is_uri = (path.startswith("file:") and "mode=memory" in path) or path.startswith("file:invoice_mem")
    try:
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False, uri=is_uri)
        cursor = conn.cursor()
        
        if is_select:
            try:
                df = pd.read_sql_query(query, conn, params=params)
            except Exception as e:
                # 關鍵修復：如果發現沒表，自動初始化並重試
                if "no such table" in str(e).lower():
                    if init_db():
                        df = pd.read_sql_query(query, conn, params=params)
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
            try:
                cursor.execute(query, params)
                conn.commit()
                # 验证是否真的执行成功
                if "INSERT" in query.upper():
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

def save_invoice_image(image_obj, file_name, user_id):
    """保存發票圖片到文件系統，返回圖片路徑"""
    try:
        # 創建用戶專屬目錄
        user_dir = os.path.join(st.session_state.image_storage_dir, user_id)
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

def check_duplicate_invoice(invoice_number, date, user_id):
    """檢查是否為重複發票（根據發票號碼+日期）"""
    if not invoice_number or invoice_number == "No" or invoice_number == "N/A":
        return False, None
    
    if st.session_state.use_memory_mode:
        # 內存模式檢查
        for inv in st.session_state.local_invoices:
            if (inv.get('user_id') == user_id and 
                inv.get('invoice_number') == invoice_number and 
                inv.get('date') == date):
                return True, inv.get('id')
    else:
        # 數據庫模式檢查
        query = "SELECT id FROM invoices WHERE user_id = ? AND invoice_number = ? AND date = ?"
        result = run_query(query, (user_id, invoice_number, date), is_select=True)
        if not result.empty:
            return True, result.iloc[0]['id']
    
    return False, None

def save_edited_data(ed_df, original_df, user_id):
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
                # 更新數據庫
                set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
                query = f"UPDATE invoices SET {set_clause} WHERE id = ? AND user_id = ?"
                params = list(update_data.values()) + [record_id, user_id]
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
# 這裡不再硬編碼 Key，防止洩漏。預設為空，強迫使用 Secrets 或手動輸入。
DEFAULT_KEY = "" 

with st.sidebar:
    st.title("⚙️ 系統狀態")
    user = st.text_input("登入帳號", "default_user")
    
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
    
    # 存儲模式選擇
    storage_mode = st.radio(
        "💾 存儲模式",
        ["🗄️ 數據庫模式", "🧠 內存模式（測試用）"],
        index=0 if not st.session_state.use_memory_mode else 1,
        help="內存模式：數據僅存在 session 中，刷新頁面會清空。適合測試功能。"
    )
    if storage_mode == "🧠 內存模式（測試用）":
        st.session_state.use_memory_mode = True
        st.info("💡 當前使用內存模式，數據不會持久化")
    else:
        st.session_state.use_memory_mode = False
    
    # 顯示資料庫狀態（僅在數據庫模式下）
    if not st.session_state.use_memory_mode:
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
    else:
        st.success("✅ 內存模式（測試用）")
    
    if st.session_state.use_memory_mode:
        count = len([inv for inv in st.session_state.local_invoices if inv.get('user_id') == user])
        if count > 0:
            st.success(f"📊 已存數據: {count} 筆（內存模式）")
        else:
            st.info("💡 提示：內存模式下，數據在刷新頁面後會清空")
    else:
        db_count_df = run_query("SELECT count(*) as count FROM invoices WHERE user_id = ?", (user,))
        if not db_count_df.empty:
            st.success(f"📊 已存數據: {db_count_df['count'][0]} 筆")
        else:
            db_path = get_db_path()
            if "mode=memory" in db_path:
                st.info("💡 提示：記憶體模式下，數據在應用重啟後會清空")
    
    if st.button("🗑️ 清空暫存資料庫 (僅 SQLite)"):
        try:
            # 嘗試刪除多個可能的數據庫文件
            for db_name in ["invoices.db", "invoices_v2.db"]:
                if os.path.exists(db_name):
                    os.remove(db_name)
            st.success("已清除！")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"清除失敗: {str(e)}")


st.title("📑 發票收據報帳小秘笈 Pro")
# 改為兩欄布局：左側上傳區 + 右側主內容區（垂直分層：統計->圖表->數據）
col_upload, col_main = st.columns([1.2, 2.8])

with col_upload:
    st.subheader("📤 上傳辨識")
    
    # 添加數據導入選項
    import_tab1, import_tab2 = st.tabs(["📷 OCR識別", "📥 數據導入"])
    
    with import_tab1:
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
                    is_duplicate, dup_id = check_duplicate_invoice(invoice_no, invoice_date, user)
                    
                    if is_duplicate:
                        st.warning(f"⚠️ {f.name}: 疑似重複發票（發票號碼: {invoice_no}, 日期: {invoice_date}，記錄ID: {dup_id}）")
                        fail_count += 1
                        continue
                    
                    # 保存圖片
                    image_path = save_invoice_image(image_obj.copy(), f.name, user)
                    
                    # 保存圖片信息到session_state用於後續顯示
                    if "ocr_images" not in st.session_state:
                        st.session_state.ocr_images = []
                    st.session_state.ocr_images.append({
                        'file_name': f.name,
                        'image_path': image_path,
                        'image_obj': image_obj.copy(),
                        'total': data.get('total', 0),
                        'status': "✅ 正常" if check_data_complete(data) else "❌ 缺失"
                    })
                    
                    # 根據存儲模式選擇不同的保存方式
                    if st.session_state.use_memory_mode:
                        # 使用內存模式
                        invoice_record = {
                            'id': len(st.session_state.local_invoices) + 1,
                            'user_id': user,
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
                        # 確保數據已保存到 session_state
                        st.session_state.data_saved = True
                    else:
                        # 使用數據庫 - 確保數據保存
                        # 先確保資料表存在
                        init_db()
                        
                        # 讀取圖片數據（如果圖片路徑存在）
                        image_data = None
                        if image_path and os.path.exists(image_path):
                            try:
                                with open(image_path, 'rb') as img_file:
                                    image_data = img_file.read()
                            except:
                                pass
                        
                        q = "INSERT INTO invoices (user_id, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status, image_path, image_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                        insert_params = (
                            user, 
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
                        
                        # 立即驗證數據是否真的保存了
                        if result:
                            # 嘗試立即查詢驗證
                            verify_query = "SELECT COUNT(*) as cnt FROM invoices WHERE user_id = ? AND file_name = ?"
                            verify_result = run_query(verify_query, (user, safe_value(data.get("file_name"), "未命名")), is_select=True)
                            if debug_mode:
                                st.write(f"🔍 驗證查詢結果: {verify_result}")
                        
                        # 驗證數據是否成功保存
                        if not result:
                            st.error(f"⚠️ 數據保存失敗，請檢查資料庫連線")
                            if st.session_state.db_error:
                                st.error(f"錯誤詳情: {st.session_state.db_error}")
                            # 如果數據庫保存失敗，嘗試切換到內存模式
                            st.warning("💡 嘗試切換到內存模式保存數據...")
                            invoice_record = {
                                'id': len(st.session_state.local_invoices) + 1,
                                'user_id': user,
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
                            st.write(f"✅ {f.name}: 成功 (${data.get('total', 0)}) - 已保存到內存")
                        else:
                            # 數據保存成功
                            st.session_state.data_saved = True
                    success_count += 1
                else:
                    st.error(f"❌ {f.name} 失敗: {err}")
                    st.session_state.ocr_report.append(f"{f.name}: {err}")
                    fail_count += 1
                
                prog.progress((idx+1)/len(files))
            
            status.update(label=f"處理完成! 成功: {success_count}, 失敗: {fail_count}", state="complete", expanded=True)
            
        # 顯示識別成功的圖片預覽（小圖，點擊放大）
        if success_count > 0 and "ocr_images" in st.session_state and st.session_state.ocr_images:
            st.divider()
            st.subheader("📷 識別結果預覽")
            # 使用列顯示多張圖片
            num_cols = 3
            cols = st.columns(num_cols)
            for idx, img_info in enumerate(st.session_state.ocr_images):
                col_idx = idx % num_cols
                with cols[col_idx]:
                    # 顯示縮略圖
                    thumbnail = img_info['image_obj'].copy()
                    thumbnail.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    st.image(thumbnail, caption=f"{img_info['file_name']}\n${img_info['total']} {img_info['status']}", use_container_width=True)
                    
                    # 點擊按鈕放大
                    zoom_key = f"zoom_img_{idx}"
                    if st.button("🔍 放大", key=zoom_key, use_container_width=True):
                        st.session_state[f"show_full_{idx}"] = not st.session_state.get(f"show_full_{idx}", False)
                    
                    # 如果點擊了放大，顯示大圖
                    if st.session_state.get(f"show_full_{idx}", False):
                        if img_info['image_path'] and os.path.exists(img_info['image_path']):
                            st.image(img_info['image_path'], caption=img_info['file_name'], use_container_width=True)
                            # 提供下載按鈕
                            with open(img_info['image_path'], 'rb') as img_file:
                                img_bytes = img_file.read()
                                st.download_button("📥 下載", img_bytes, 
                                                 file_name=os.path.basename(img_info['image_path']),
                                                 mime="image/jpeg", key=f"download_{idx}")
            
            # 清空臨時圖片數據（在rerun前）
            if st.button("✅ 完成，查看數據列表", use_container_width=True, type="primary"):
                st.session_state.ocr_images = []
                st.rerun()
        
        if success_count > 0:
            # 不清空ocr_images，讓用戶可以先預覽
            # time.sleep(1) # 讓使用者稍微看一下結果
            # st.rerun()  # 改為手動觸發rerun
            pass
    
    with import_tab2:
        st.info("💡 支持導入 Excel (.xlsx) 或 CSV (.csv) 格式的發票數據")
        
        # 下載導入模板
        template_data = {
            "檔案名稱": ["發票1.jpg", "發票2.jpg"],
            "日期": ["2025/01/01", "2025/01/02"],
            "發票號碼": ["AB12345678", "CD87654321"],
            "賣方名稱": ["測試商店", "測試公司"],
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
        
        uploaded_file = st.file_uploader("選擇要導入的文件", type=["csv", "xlsx"], key="import_file")
        
        if uploaded_file and st.button("開始導入", type="primary", use_container_width=True):
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
                    # 顯示預覽
                    st.subheader("📋 導入數據預覽（前5筆）")
                    st.dataframe(import_df.head(5), use_container_width=True)
                    
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
                        
                        with st.status("正在導入數據...", expanded=True) as status:
                            for idx, row in import_df.iterrows():
                                try:
                                    # 檢查重複
                                    invoice_no = str(row.get("發票號碼", "No"))
                                    invoice_date = str(row.get("日期", ""))
                                    is_dup, _ = check_duplicate_invoice(invoice_no, invoice_date, user)
                                    
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
                                    
                                    # 保存數據
                                    if st.session_state.use_memory_mode:
                                        invoice_record = {
                                            'id': len(st.session_state.local_invoices) + 1,
                                            'user_id': user,
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
                                        q = "INSERT INTO invoices (user_id, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
                                        params = (
                                            user,
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
                                    if debug_mode:
                                        st.write(f"第 {idx+1} 筆導入失敗: {str(e)}")
                        
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
                if debug_mode:
                    st.exception(e)

# 查詢數據（在兩個列之外，確保作用域正確）
# 添加調試信息（可選，用於排查問題）- 必須在查詢之前定義
debug_mode = st.sidebar.checkbox("🔍 顯示調試信息", value=False)

df_raw = run_query("SELECT * FROM invoices WHERE user_id = ? ORDER BY id DESC", (user,))
if debug_mode:
    st.sidebar.write(f"📊 原始查詢結果筆數: {len(df_raw)}")
    st.sidebar.write(f"📋 用戶ID: {user}")
    db_path = get_db_path()
    st.sidebar.write(f"📁 資料庫路徑: {db_path}")
    st.sidebar.write(f"💾 存儲模式: {'內存模式' if st.session_state.use_memory_mode else '數據庫模式'}")
    if "mode=memory" in db_path:
        st.sidebar.error("⚠️ 使用內存數據庫！刷新頁面會清空數據")
    if not st.session_state.use_memory_mode:
        # 檢查數據庫文件是否存在
        if os.path.exists(db_path):
            file_size = os.path.getsize(db_path)
            st.sidebar.write(f"📦 數據庫文件大小: {file_size} bytes")
        else:
            st.sidebar.warning("⚠️ 數據庫文件不存在")
    if not df_raw.empty:
        st.sidebar.write(f"📝 欄位名稱: {list(df_raw.columns)}")
        st.sidebar.write(f"📄 前3筆數據預覽:")
        st.sidebar.dataframe(df_raw.head(3))
    else:
        st.sidebar.warning("⚠️ 查詢結果為空")
        if not st.session_state.use_memory_mode:
            # 嘗試查詢所有數據（不按user_id過濾）
            all_data = run_query("SELECT COUNT(*) as cnt FROM invoices", (), is_select=True)
            if not all_data.empty:
                total_count = all_data.iloc[0, 0] if 'cnt' in all_data.columns else all_data.iloc[0, 0]
                st.sidebar.write(f"📊 數據庫總記錄數: {total_count}")
                if total_count > 0:
                    st.sidebar.info(f"💡 數據庫中有 {total_count} 筆數據，但當前用戶 '{user}' 沒有數據")

with col_main:
    # ========== 頂部：統計指標卡片區 ==========
    st.subheader("📊 統計報表")
    df_stats = df_raw.copy()
    if not df_stats.empty:
        # 先重命名列以便統計報表使用
        mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態"}
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
            
            st.divider()
            
            # ========== 中間：圖表展示區（並排顯示）==========
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # 圓餅圖 - 會計科目分布
                if "會計科目" in df_stats.columns:
                    df_chart = df_stats[df_stats['會計科目'].notna() & (df_stats['會計科目'] != 'No')].copy()
                    if not df_chart.empty:
                        chart = alt.Chart(df_chart).mark_arc(innerRadius=40).encode(
                            theta=alt.Theta("count()", type="quantitative"),
                            color=alt.Color("會計科目", type="nominal"),
                            tooltip=["會計科目", "count()"]
                        ).properties(height=300, title="會計科目分布")
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("📊 暫無會計科目數據")
                elif "subject" in df_raw.columns:
                    df_stats_chart = df_raw.copy()
                    df_stats_chart = df_stats_chart[df_stats_chart['subject'].notna() & (df_stats_chart['subject'] != 'No')]
                    if not df_stats_chart.empty:
                        chart = alt.Chart(df_stats_chart).mark_arc(innerRadius=40).encode(
                            theta=alt.Theta("count()", type="quantitative"),
                            color=alt.Color("subject", type="nominal"),
                            tooltip=["subject", "count()"]
                        ).properties(height=300, title="會計科目分布")
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("📊 暫無會計科目數據")
                else:
                    st.info("📊 暫無會計科目數據")
            
            with chart_col2:
                # 折線圖 - 每日支出趨勢
                if "日期" in df_stats.columns and "總計" in df_stats.columns:
                    df_line = df_stats.copy()
                    df_line['日期'] = pd.to_datetime(df_line['日期'], errors='coerce', format='%Y/%m/%d')
                    df_line = df_line.dropna(subset=['日期'])
                    
                    if not df_line.empty:
                        df_line_grouped = df_line.groupby('日期')['總計'].sum().reset_index()
                        df_line_grouped = df_line_grouped.sort_values('日期')
                        
                        line_chart = alt.Chart(df_line_grouped).mark_line(point=True, strokeWidth=2).encode(
                            x=alt.X('日期:T', title='日期', axis=alt.Axis(format='%Y/%m/%d')),
                            y=alt.Y('總計:Q', title='金額 ($)', axis=alt.Axis(format='$,.0f')),
                            tooltip=[alt.Tooltip('日期:T', format='%Y/%m/%d'), alt.Tooltip('總計:Q', format='$,.0f')]
                        ).properties(
                            height=300,
                            title="每日支出趨勢"
                        ).configure_axis(
                            labelFontSize=10,
                            titleFontSize=12
                        ).configure_title(
                            fontSize=14
                        )
                        st.altair_chart(line_chart, use_container_width=True)
                    else:
                        st.info("📈 無有效的日期數據可顯示折線圖")
                else:
                    st.info("📈 需要日期和總計欄位才能顯示折線圖")
            
            st.divider()
    else:
        # 如果沒有數據，顯示提示
        st.info("📊 目前無統計數據")
    
    # ========== 底部：數據報表區 ==========
    st.subheader("📋 數據稽核報表")
    
    # 查詢條件（簡化版，不折疊）
    sc1, sc2 = st.columns([2, 1])
    search = sc1.text_input("🔍 關鍵字搜尋", placeholder="號碼/賣方/檔名...")
    t_filter = sc2.selectbox("🕒 時間範圍", ["全部", "今天", "本週", "本月"])
    
    # 使用原始查詢結果（如果df_stats已定義，使用它；否則使用df_raw並重命名）
    if 'df_stats' in locals() and not df_stats.empty:
        df = df_stats.copy()
    else:
        df = df_raw.copy()
        # 如果使用df_raw，需要重命名列
        if not df.empty:
            mapping = {"file_name":"檔案名稱","date":"日期","invoice_number":"發票號碼","seller_name":"賣方名稱","seller_ubn":"賣方統編","subtotal":"銷售額","tax":"稅額","total":"總計","category":"類型","subject":"會計科目","status":"狀態"}
            df = df.rename(columns=mapping)
    
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
                    if debug_mode:
                        st.warning(f"日期過濾錯誤: {str(e)}")
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
            if col not in ['選取', 'id', '狀態']:  # 跳過選取、id和狀態列
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
        
        if st.button("🗑️ 刪除選中數據"):
            ids = df[df["選取"]==True]["id"].tolist()
            if st.session_state.use_memory_mode:
                # 內存模式：從列表中刪除
                st.session_state.local_invoices = [inv for inv in st.session_state.local_invoices if inv.get('id') not in ids]
            else:
                # 數據庫模式
                for i in ids: run_query("DELETE FROM invoices WHERE id=?", (i,), is_select=False)
            st.rerun()
        
        # 保存原始數據的副本用於比較
        original_df_copy = df.copy()
        
        # 準備列配置
        column_config = {
            "id": None, 
            "選取": st.column_config.CheckboxColumn("選取", default=False),
            "檔案名稱": st.column_config.TextColumn("檔案名稱", width="medium"),
            "總計": st.column_config.NumberColumn("總計", format="$%d"),
            "銷售額": st.column_config.NumberColumn("銷售額", format="$%d"),
            "稅額": st.column_config.NumberColumn("稅額", format="$%d")
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
            # 比較關鍵字段是否有變化
            for col in ed_df.columns:
                if col not in ['id', '選取']:
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
            saved_count, errors = save_edited_data(ed_df, original_df_copy, user)
            if saved_count > 0:
                st.success(f"✅ 已自動保存 {saved_count} 筆數據變更")
                if errors:
                    for err in errors[:3]:  # 只顯示前3個錯誤
                        st.warning(err)
                time.sleep(0.5)
                st.rerun()
            elif errors:
                st.error(f"保存失敗: {errors[0] if errors else '未知錯誤'}")
    else: 
        # 如果df為空（篩選後或原始數據為空）
        if not df_raw.empty:
            st.warning("⚠️ 查無數據。")
            if debug_mode:
                st.info(f"🔍 調試：搜索關鍵字 '{search}' 後無匹配結果。原始數據筆數: {len(df_raw)}")
        else:
            st.warning("⚠️ 目前無數據。請先嘗試上傳並辨識。")
            if debug_mode:
                st.info(f"🔍 調試：資料庫中沒有 user_id='{user}' 的數據。請檢查：\n1. 是否已上傳並辨識發票\n2. 側邊欄的「登入帳號」是否正確")

    # 導出功能（放在數據表格下方）
    if not df.empty and "總計" in df.columns:
        st.divider()
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            # CSV 導出
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 導出 CSV", csv_data, "invoice_report.csv", use_container_width=True)
        
        with export_col2:
            # PDF 導出 (使用 fpdf2)
            if PDF_AVAILABLE:
                def generate_pdf():
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    
                    # 設置中文字體支持
                    font_loaded = False
                    font_name = 'NotoSansTC'
                    font_path = 'NotoSansTC-Regular.ttf'
                    
                    try:
                        if os.path.exists(font_path):
                            pdf.add_font(font_name, '', font_path, uni=True)
                            pdf.add_font(font_name, 'B', font_path, uni=True)
                            font_loaded = True
                    except Exception as e:
                        font_loaded = False
                    
                    def safe_cell(pdf, w, h, txt, border=0, ln=0, align='', fill=False, link='', font_name_override=None):
                        if not font_loaded:
                            txt = ''.join(c for c in str(txt) if ord(c) < 128)
                        if font_name_override:
                            pdf.set_font(font_name_override[0], font_name_override[1], font_name_override[2])
                        pdf.cell(w, h, txt, border, ln, align, fill, link)
                    
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
                    
                    # 統計摘要
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 12)
                        safe_cell(pdf, 0, 8, '統計摘要', ln=1)
                        pdf.set_font(font_name, '', 10)
                        safe_cell(pdf, 90, 6, '累計金額:', 1)
                        # 計算統計數據
                        if "總計" in df.columns:
                            total_sum = pd.to_numeric(df['總計'], errors='coerce').fillna(0).sum()
                        else:
                            total_sum = 0
                        safe_cell(pdf, 90, 6, f"${total_sum:,.0f}", 1, ln=1)
                        safe_cell(pdf, 90, 6, '累計稅額:', 1)
                        if "稅額" in df.columns:
                            tax_sum = pd.to_numeric(df['稅額'], errors='coerce').fillna(0).sum()
                        else:
                            tax_sum = 0
                        safe_cell(pdf, 90, 6, f"${tax_sum:,.0f}", 1, ln=1)
                        safe_cell(pdf, 90, 6, '發票總數:', 1)
                        safe_cell(pdf, 90, 6, f"{len(df)} 筆", 1, ln=1)
                    pdf.ln(5)
                    
                    # 詳細數據表格
                    export_df = df.copy()
                    col_widths = [20, 30, 35, 50, 30, 25]
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 10)
                        headers = ['狀態', '日期', '發票號碼', '賣方名稱', '總計', '類型']
                    else:
                        pdf.set_font('Arial', 'B', 10)
                        headers = ['Status', 'Date', 'Invoice No', 'Seller', 'Total', 'Type']
                    
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
                    
                    for _, row in export_df.iterrows():
                        status = pdf_safe_value(row.get('狀態', ''), '❌ 缺失')[:10]
                        date_str = pdf_safe_value(row.get('日期', ''), 'No')[:10]
                        invoice_no = pdf_safe_value(row.get('發票號碼', ''), 'No')[:15]
                        seller = pdf_safe_value(row.get('賣方名稱', ''), 'No')[:20]
                        total_val = pd.to_numeric(row.get('總計', 0), errors='coerce')
                        if pd.isna(total_val):
                            total_val = 0
                        total = f"${total_val:,.0f}"
                        category = pdf_safe_value(row.get('類型', ''), 'No')[:10]
                        
                        safe_cell(pdf, col_widths[0], 6, status, 1)
                        safe_cell(pdf, col_widths[1], 6, date_str, 1)
                        safe_cell(pdf, col_widths[2], 6, invoice_no, 1)
                        safe_cell(pdf, col_widths[3], 6, seller, 1)
                        safe_cell(pdf, col_widths[4], 6, total, 1, align='R')
                        safe_cell(pdf, col_widths[5], 6, category, 1, ln=1)
                        
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
                st.download_button("📄 導出 PDF", pdf_data, f"invoice_report_{datetime.now().strftime('%Y%m%d')}.pdf", 
                                 mime="application/pdf", use_container_width=True)
            else:
                st.info("📄 PDF 功能需要安裝 fpdf2")
