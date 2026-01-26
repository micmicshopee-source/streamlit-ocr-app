# 發票報帳系統 - 垂直分層布局版本備份
# 備份日期: 2026-01-26
# 版本說明: 
# - 改為兩欄布局（左側上傳區 + 右側主內容區）
# - 主內容區垂直分層：統計指標 -> 圖表 -> 數據表格
# - 統計指標4個卡片並排顯示
# - 圖表並排顯示（餅圖左，折線圖右）
# - 數據表格全寬顯示
# - 包含所有功能：自動保存、圖片預覽、重複檢測、數據導入等
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

# PDF 鐢熸垚搴?(浣跨敤 fpdf2)
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. 绯荤当浣堝眬鑸囧垵濮嬪寲 ---
st.set_page_config(page_title="鐧肩エ鍫卞赋灏忕绗?, page_icon="馃Ь", layout="wide")

if "db_error" not in st.session_state: st.session_state.db_error = None
if "db_path_mode" not in st.session_state: st.session_state.db_path_mode = "馃捑 鏈湴纾佺"
if "use_memory_mode" not in st.session_state: st.session_state.use_memory_mode = False
if "local_invoices" not in st.session_state: st.session_state.local_invoices = []
if "image_storage_dir" not in st.session_state: 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    st.session_state.image_storage_dir = os.path.join(base_dir, "invoice_images")
    os.makedirs(st.session_state.image_storage_dir, exist_ok=True)
if "last_edited_df_hash" not in st.session_state: st.session_state.last_edited_df_hash = None

# --- 2. 绲傛サ闊屾€ц硣鏂欏韩閫ｇ窔鍣?---
def get_db_path():
    if "current_db_path" not in st.session_state:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 鏀圭敤 invoices_v2.db 浠ヨВ姹鸿垔璩囨枡搴彲鑳界櫦鐢熺殑 Disk I/O Error 閹栧畾鍟忛
        db_file = os.path.join(base_dir, "invoices_v2.db")
        
        # 纰轰繚鐩寗瀛樺湪
        try:
            os.makedirs(base_dir, exist_ok=True)
        except Exception as e:
            st.session_state.db_error = f"鐒℃硶鍓靛缓鐩寗: {str(e)}"
            st.session_state.current_db_path = "file:invoice_mem?mode=memory&cache=shared"
            st.session_state.db_path_mode = "馃 铏涙摤瑷樻喍楂?(閲嶅暉鏈冩竻绌?"
            return st.session_state.current_db_path
        
        try:
            # 娓│瀵叆娆婇檺
            test_path = db_file + ".test"
            with open(test_path, "w") as f: 
                f.write("1")
            os.remove(test_path)
            # 寮峰埗浣跨敤鏂囦欢鏁告摎搴紝涓嶄娇鐢ㄥ収瀛樻ā寮?
            st.session_state.current_db_path = db_file
            st.session_state.db_path_mode = "馃捑 鏈湴纾佺"
            st.session_state.db_error = None
        except PermissionError as e:
            st.session_state.db_error = f"娆婇檺涓嶈冻锛岀劇娉曞鍏? {str(e)}"
            # 鍗充娇娆婇檺涓嶈冻锛屼篃鍢楄│浣跨敤鏂囦欢鏁告摎搴紙鍙兘鍙互璁€鍙栵級
            st.session_state.current_db_path = db_file
            st.session_state.db_path_mode = "鈿狅笍 鍙畝妯″紡"
        except Exception as e:
            st.session_state.db_error = f"鐒℃硶浣跨敤鏂囦欢鏁告摎搴? {str(e)}"
            # 鏈€寰屾墠浣跨敤鍏у瓨妯″紡
            st.session_state.current_db_path = "file:invoice_mem?mode=memory&cache=shared"
            st.session_state.db_path_mode = "馃 铏涙摤瑷樻喍楂?(閲嶅暉鏈冩竻绌?"
    
    return st.session_state.current_db_path

def init_db():
    """鍒濆鍖栬硣鏂欒〃锛岀⒑淇濇墍鏈夊繀瑕佹瑒浣嶅瓨鍦?""
    if st.session_state.use_memory_mode:
        return True  # 浣跨敤鍏у瓨妯″紡锛岃烦閬庢暩鎿氬韩鍒濆鍖?
    
    path = get_db_path()
    # 鍒ゆ柗鏄惁鐐篣RI妯″紡锛堝彧鏈夋槑纰哄寘鍚玬ode=memory鎵嶆槸URI锛?
    # 鏅€氭枃浠惰矾寰戯紙濡?invoices_v2.db锛変笉鏄疷RI
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
        # 瑁滃叏娆勪綅
        for col, c_type in {'user_id': "TEXT", 'status': "TEXT", 'seller_ubn': "TEXT", 
                            'image_path': "TEXT", 'image_data': "BLOB"}.items():
            try: cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {c_type}")
            except: pass
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.session_state.db_error = f"鍒濆鍖栧け鏁? {str(e)}"
        return False

def run_query(query, params=(), is_select=True):
    # 濡傛灉浣跨敤鍏у瓨妯″紡锛屼娇鐢?session_state 瀛樺劜
    if st.session_state.use_memory_mode:
        if is_select:
            # 铏曠悊 SELECT 鏌ヨ
            if "WHERE user_id" in query.upper():
                user_id = params[0] if params else "default_user"
                df = pd.DataFrame([inv for inv in st.session_state.local_invoices if inv.get('user_id') == user_id])
            else:
                df = pd.DataFrame(st.session_state.local_invoices)
            
            # 绨″柈鐨?ORDER BY 铏曠悊
            if "ORDER BY id DESC" in query.upper():
                if not df.empty and 'id' in df.columns:
                    df = df.sort_values('id', ascending=False)
            
            return df
        else:
            # INSERT 鏌ヨ鏈冨湪瑾跨敤铏曡檿鐞?
            return True
    
    # 浣跨敤鏁告摎搴?
    path = get_db_path()
    # 鍒ゆ柗鏄惁鐐篣RI妯″紡锛堝彧鏈夋槑纰哄寘鍚玬ode=memory鎴杅ile:鍓嶇洞鎵嶆槸URI锛?
    is_uri = (path.startswith("file:") and "mode=memory" in path) or path.startswith("file:invoice_mem")
    try:
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False, uri=is_uri)
        cursor = conn.cursor()
        
        if is_select:
            try:
                df = pd.read_sql_query(query, conn, params=params)
            except Exception as e:
                # 闂滈嵉淇京锛氬鏋滅櫦鐝炬矑琛紝鑷嫊鍒濆鍖栦甫閲嶈│
                if "no such table" in str(e).lower():
                    if init_db():
                        df = pd.read_sql_query(query, conn, params=params)
                    else:
                        # 鍒濆鍖栧け鏁楋紝鍒囨彌鍒板収瀛樻ā寮?
                        st.session_state.use_memory_mode = True
                        return run_query(query, params, is_select)
                else: 
                    raise e
            conn.close()
            st.session_state.db_error = None
            return df
        else:
            # 闈濻ELECT鏌ヨ锛欼NSERT, UPDATE, DELETE绛?
            try:
                cursor.execute(query, params)
                conn.commit()
                # 楠岃瘉鏄惁鐪熺殑鎵ц鎴愬姛
                if "INSERT" in query.upper():
                    # 瀵逛簬INSERT锛屾鏌ュ奖鍝嶇殑琛屾暟
                    if cursor.rowcount > 0:
                        conn.close()
                        return True
                    else:
                        conn.close()
                        st.session_state.db_error = "鎻掑叆澶辨晽锛氬奖闊胯鏁哥偤0"
                        return False
                conn.close()
                return True
            except Exception as e:
                conn.rollback()
                conn.close()
                st.session_state.db_error = f"鍩疯澶辨晽: {str(e)}"
                return False
    except Exception as e:
        err_msg = str(e)
        st.session_state.db_error = f"閫ｇ窔鐣板父: {err_msg}"
        # 濡傛灉鏁告摎搴け鏁楋紝鑷嫊鍒囨彌鍒板収瀛樻ā寮?
        if "no such table" in err_msg.lower() or "unable to open" in err_msg.lower():
            st.session_state.use_memory_mode = True
            if is_select:
                return run_query(query, params, is_select)
        return pd.DataFrame() if is_select else False

# 绋嬪紡鍟熷嫊绔嬪嵆鍒濆鍖栵紙濡傛灉浣跨敤鏁告摎搴ā寮忥級
if not st.session_state.use_memory_mode:
    init_db()

import re

# ... (淇濇寔鍓嶉潰鐨?import 涓嶅彉)

# --- 3. 鏍稿績杈ㄨ瓨閭忚集 ---
def extract_json(text):
    """寰炴贩鍚堟枃鏈腑鎻愬彇鏈夋晥鐨?JSON 鐗╀欢"""
    text = text.strip()
    # 鍢楄│ 1: 鐩存帴瑙ｆ瀽
    try:
        return json.loads(text)
    except:
        pass
        
    # 鍢楄│ 2: 灏嬫壘 Markdown 浠ｇ⒓濉?```json ... ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1))
        except: pass
        
    # 鍢楄│ 3: 灏嬫壘鏈€澶栧堡鐨?{}
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1))
        except: pass
        
    return None

def save_invoice_image(image_obj, file_name, user_id):
    """淇濆瓨鐧肩エ鍦栫墖鍒版枃浠剁郴绲憋紝杩斿洖鍦栫墖璺緫"""
    try:
        # 鍓靛缓鐢ㄦ埗灏堝爆鐩寗
        user_dir = os.path.join(st.session_state.image_storage_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # 鐢熸垚鍞竴鏂囦欢鍚嶏紙浣跨敤鏅傞枔鎴?鏂囦欢鍚峢ash锛?
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_name.encode()).hexdigest()[:8]
        safe_filename = f"{timestamp}_{file_hash}_{file_name}"
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")
        
        image_path = os.path.join(user_dir, safe_filename)
        image_obj.save(image_path)
        return image_path
    except Exception as e:
        st.error(f"淇濆瓨鍦栫墖澶辨晽: {str(e)}")
        return None

def check_duplicate_invoice(invoice_number, date, user_id):
    """妾㈡煡鏄惁鐐洪噸瑜囩櫦绁紙鏍规摎鐧肩エ铏熺⒓+鏃ユ湡锛?""
    if not invoice_number or invoice_number == "No" or invoice_number == "N/A":
        return False, None
    
    if st.session_state.use_memory_mode:
        # 鍏у瓨妯″紡妾㈡煡
        for inv in st.session_state.local_invoices:
            if (inv.get('user_id') == user_id and 
                inv.get('invoice_number') == invoice_number and 
                inv.get('date') == date):
                return True, inv.get('id')
    else:
        # 鏁告摎搴ā寮忔鏌?
        query = "SELECT id FROM invoices WHERE user_id = ? AND invoice_number = ? AND date = ?"
        result = run_query(query, (user_id, invoice_number, date), is_select=True)
        if not result.empty:
            return True, result.iloc[0]['id']
    
    return False, None

def save_edited_data(ed_df, original_df, user_id):
    """鑷嫊淇濆瓨绶ㄨ集寰岀殑鏁告摎"""
    saved_count = 0
    errors = []
    
    # 灏囧垪鍚嶆槧灏勫洖鏁告摎搴瓧娈靛悕
    reverse_mapping = {"妾旀鍚嶇ū":"file_name","鏃ユ湡":"date","鐧肩エ铏熺⒓":"invoice_number",
                      "璩ｆ柟鍚嶇ū":"seller_name","璩ｆ柟绲辩法":"seller_ubn","閵峰敭椤?:"subtotal",
                      "绋呴":"tax","绺借▓":"total","椤炲瀷":"category","鏈冭▓绉戠洰":"subject","鐙€鎱?:"status"}
    
    for idx, row in ed_df.iterrows():
        if 'id' not in row or pd.isna(row['id']):
            continue
        
        record_id = int(row['id'])
        
        # 妾㈡煡鏄惁鏈夎畩鏇?
        if idx < len(original_df):
            orig_row = original_df.iloc[idx]
            if orig_row.get('id') == record_id:
                # 姣旇純闂滈嵉瀛楁鏄惁鏈夎畩鍖?
                changed = False
                for col in ed_df.columns:
                    if col not in ['id', '閬稿彇']:
                        orig_val = orig_row.get(col, '')
                        new_val = row.get(col, '')
                        if str(orig_val) != str(new_val):
                            changed = True
                            break
                
                if not changed:
                    continue
        
        # 婧栧倷鏇存柊鏁告摎
        update_data = {}
        for display_col, db_col in reverse_mapping.items():
            if display_col in row:
                update_data[db_col] = row[display_col]
        
        # 铏曠悊鏁稿€煎瓧娈?
        for num_col in ['subtotal', 'tax', 'total']:
            if num_col in update_data:
                try:
                    val = str(update_data[num_col]).replace(',', '').replace('$', '')
                    update_data[num_col] = float(val) if val else 0.0
                except:
                    update_data[num_col] = 0.0
        
        # 淇濆瓨鍒版暩鎿氬韩鎴栧収瀛?
        try:
            if st.session_state.use_memory_mode:
                # 鏇存柊鍏у瓨涓殑瑷橀寗
                for i, inv in enumerate(st.session_state.local_invoices):
                    if inv.get('id') == record_id:
                        for key, val in update_data.items():
                            st.session_state.local_invoices[i][key] = val
                        saved_count += 1
                        break
            else:
                # 鏇存柊鏁告摎搴?
                set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
                query = f"UPDATE invoices SET {set_clause} WHERE id = ? AND user_id = ?"
                params = list(update_data.values()) + [record_id, user_id]
                result = run_query(query, tuple(params), is_select=False)
                if result:
                    saved_count += 1
                else:
                    errors.append(f"瑷橀寗 ID {record_id} 鏇存柊澶辨晽")
        except Exception as e:
            errors.append(f"瑷橀寗 ID {record_id} 鏇存柊閷: {str(e)}")
    
    return saved_count, errors

def process_ocr(image_obj, file_name, model_name, api_key_val):
    try:
        if image_obj.mode != "RGB": image_obj = image_obj.convert("RGB")
        # 绋嶅井闄嶄綆瑙ｆ瀽搴︿互鍔犲揩閫熷害涓︽笡灏?Token锛屼絾淇濇寔瓒冲娓呮櫚搴?
        image_obj.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        img_byte = io.BytesIO(); image_obj.save(img_byte, format="JPEG", quality=85)
        img_base64 = base64.b64encode(img_byte.getvalue()).decode()
        
        # 鍎寲 Prompt锛氭槑纰鸿姹傜磾 JSON锛屼笉瑕?Markdown
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
        - type (Invoice type, e.g., "闆诲瓙鐧肩エ", "鏀舵摎")
        - category_suggest (Category, e.g., "椁愰２", "浜ら€?, "杈﹀叕鐢ㄥ搧")
        
        If a field is missing, use null or 0.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}]}], 
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024}
        }
        
        # 鍎厛闋嗗簭瑾挎暣锛氬厛瑭?v1beta (鏀彺杓冩柊妯″瀷)锛屽啀瑭?v1
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
            # 鏅鸿兘铏曠悊 models/ 鍓嶇洞
            final_model_name = m_name if "models/" in m_name else f"models/{m_name}"
            # 淇 URL 绲愭锛歷1beta/models/gemini-pro:generateContent
            # 绉婚櫎澶氶鐨?models/ 濡傛灉 API 鐗堟湰璺緫宸茬稉闅卞惈
            if ver == "v1beta" or ver == "v1":
                 # Google API 瑕忕瘎: https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent
                 # 濡傛灉 m_name 宸茬稉鍖呭惈 models/锛屽墖鐩存帴浣跨敤
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
                            last_err = "API 鍥炲偝绲愭鐣板父 (鐒?candidates)"
                            continue
                            
                        text = resp_json['candidates'][0]['content']['parts'][0]['text']
                        raw = extract_json(text)
                        
                        if raw:
                            data = {
                                "file_name": file_name,
                                "date": raw.get("date") or raw.get("鏃ユ湡") or datetime.now().strftime("%Y/%m/%d"),
                                "invoice_no": raw.get("invoice_no") or raw.get("invoice_number") or "N/A",
                                "seller_name": raw.get("seller_name") or "N/A",
                                "seller_ubn": raw.get("seller_ubn") or "N/A",
                                "subtotal": raw.get("subtotal") or 0, "tax": raw.get("tax") or 0, "total": raw.get("total") or 0,
                                "type": raw.get("type") or "鍏朵粬", "category_suggest": raw.get("category_suggest") or "闆滈爡"
                            }
                            data["status"] = "鉁?姝ｅ父" if data["total"] else "鈿狅笍 缂烘紡"
                            return data, None
                        else:
                            last_err = f"JSON 瑙ｆ瀽澶辨晽. 鍘熷鏂囨湰: {text[:100]}..."
                            debug_info.append(f"{ver}/{m_name}: {last_err}")
                    except Exception as parse_err:
                        last_err = f"瑙ｆ瀽鐣板父: {str(parse_err)}"
                        debug_info.append(f"{ver}/{m_name}: {last_err}")
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text[:100]}"
                    debug_info.append(f"{ver}/{m_name}: {last_err}")
            except Exception as e: 
                last_err = str(e)
                debug_info.append(f"{ver}/{m_name}: {last_err}")
                continue
                
        return None, f"鎵€鏈夊槜瑭︾殕澶辨晽銆傛渶寰岄尟瑾? {last_err} | 姝风▼: {'; '.join(debug_info)}"
    except Exception as e: return None, f"绯荤当閷: {str(e)}"

# --- 4. 浠嬮潰娓叉煋 ---
# 閫欒！涓嶅啀纭法纰?Key锛岄槻姝㈡穿婕忋€傞爯瑷偤绌猴紝寮疯揩浣跨敤 Secrets 鎴栨墜鍕曡几鍏ャ€?
DEFAULT_KEY = "" 

with st.sidebar:
    st.title("鈿欙笍 绯荤当鐙€鎱?)
    user = st.text_input("鐧诲叆甯宠櫉", "default_user")
    
    # 鍎厛浣跨敤 Streamlit Secrets
    if "GEMINI_API_KEY" in st.secrets:
        st.success("馃攽 宸蹭娇鐢?Secrets 閲戦懓")
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.text_input("Gemini API Key", DEFAULT_KEY, type="password")
        if not api_key:
            st.warning("璜嬭几鍏?API Key 鎴栬ō瀹?Secrets")

    model = st.selectbox("杈ㄨ瓨妯″瀷", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"])
    
    st.divider()
    
    # 瀛樺劜妯″紡閬告搰
    storage_mode = st.radio(
        "馃捑 瀛樺劜妯″紡",
        ["馃梽锔?鏁告摎搴ā寮?, "馃 鍏у瓨妯″紡锛堟脯瑭︾敤锛?],
        index=0 if not st.session_state.use_memory_mode else 1,
        help="鍏у瓨妯″紡锛氭暩鎿氬儏瀛樺湪 session 涓紝鍒锋柊闋侀潰鏈冩竻绌恒€傞仼鍚堟脯瑭﹀姛鑳姐€?
    )
    if storage_mode == "馃 鍏у瓨妯″紡锛堟脯瑭︾敤锛?:
        st.session_state.use_memory_mode = True
        st.info("馃挕 鐣跺墠浣跨敤鍏у瓨妯″紡锛屾暩鎿氫笉鏈冩寔涔呭寲")
    else:
        st.session_state.use_memory_mode = False
    
    # 椤ず璩囨枡搴媭鎱嬶紙鍍呭湪鏁告摎搴ā寮忎笅锛?
    if not st.session_state.use_memory_mode:
        db_path = get_db_path()
        if "mode=memory" in db_path:
            st.warning(f"鈿狅笍 {st.session_state.db_path_mode}")
            if st.session_state.db_error:
                st.error(f"鉂?{st.session_state.db_error}")
            # 鎻愪緵閲嶇疆鎸夐垥锛屽槜瑭﹀垏鎻涘埌鏂囦欢妯″紡
            if st.button("馃攧 鍢楄│鍒囨彌鍒版枃浠舵ā寮?, help="娓呴櫎鐣跺墠瑷疆锛岄噸鏂板槜瑭︿娇鐢ㄦ枃浠舵暩鎿氬韩"):
                if "current_db_path" in st.session_state:
                    del st.session_state.current_db_path
                if "db_error" in st.session_state:
                    del st.session_state.db_error
                st.rerun()
        else:
            st.success(f"鉁?{st.session_state.db_path_mode}")
    else:
        st.success("鉁?鍏у瓨妯″紡锛堟脯瑭︾敤锛?)
    
    if st.session_state.use_memory_mode:
        count = len([inv for inv in st.session_state.local_invoices if inv.get('user_id') == user])
        if count > 0:
            st.success(f"馃搳 宸插瓨鏁告摎: {count} 绛嗭紙鍏у瓨妯″紡锛?)
        else:
            st.info("馃挕 鎻愮ず锛氬収瀛樻ā寮忎笅锛屾暩鎿氬湪鍒锋柊闋侀潰寰屾渻娓呯┖")
    else:
        db_count_df = run_query("SELECT count(*) as count FROM invoices WHERE user_id = ?", (user,))
        if not db_count_df.empty:
            st.success(f"馃搳 宸插瓨鏁告摎: {db_count_df['count'][0]} 绛?)
        else:
            db_path = get_db_path()
            if "mode=memory" in db_path:
                st.info("馃挕 鎻愮ず锛氳鎲堕珨妯″紡涓嬶紝鏁告摎鍦ㄦ噳鐢ㄩ噸鍟熷緦鏈冩竻绌?)
    
    if st.button("馃棏锔?娓呯┖鏆瓨璩囨枡搴?(鍍?SQLite)"):
        try:
            # 鍢楄│鍒櫎澶氬€嬪彲鑳界殑鏁告摎搴枃浠?
            for db_name in ["invoices.db", "invoices_v2.db"]:
                if os.path.exists(db_name):
                    os.remove(db_name)
            st.success("宸叉竻闄わ紒")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"娓呴櫎澶辨晽: {str(e)}")


st.title("馃搼 鐧肩エ鏀舵摎鍫卞赋灏忕绗?Pro")
# 鏀圭偤鍏╂瑒甯冨眬锛氬乏鍋翠笂鍌冲崁 + 鍙冲伌涓诲収瀹瑰崁锛堝瀭鐩村垎灞わ細绲辫▓->鍦栬〃->鏁告摎锛?
col_upload, col_main = st.columns([1.2, 2.8])

with col_upload:
    st.subheader("馃摛 涓婂偝杈ㄨ瓨")
    
    # 娣诲姞鏁告摎灏庡叆閬搁爡
    import_tab1, import_tab2 = st.tabs(["馃摲 OCR璀樺垾", "馃摜 鏁告摎灏庡叆"])
    
    with import_tab1:
        files = st.file_uploader("鎵规閬告搰鐓х墖", type=["jpg","png","jpeg"], accept_multiple_files=True)
    if files and st.button("闁嬪杈ㄨ瓨 馃殌", type="primary", use_container_width=True):
        
        # 鍒濆鍖?session_state 鐢ㄦ柤瀛樺劜绲愭灉鍫卞憡锛堝鏋滈倓娌掓湁鐨勮┍锛?
        if "ocr_report" not in st.session_state: st.session_state.ocr_report = []
        
        success_count = 0
        fail_count = 0
        
        with st.status("AI 姝ｅ湪鍒嗘瀽鐧肩エ涓?..", expanded=True) as status:
            prog = st.progress(0)
            
            for idx, f in enumerate(files):
                st.write(f"姝ｅ湪铏曠悊: {f.name} ...")
                image_obj = Image.open(f)
                data, err = process_ocr(image_obj, f.name, model, api_key)
                
                if data:
                    def clean_n(v):
                        try: return float(str(v).replace(',','').replace('$',''))
                        except: return 0.0
                    
                    # 铏曠悊绌哄€硷細纰轰繚鎵€鏈夊瓧娈甸兘鏈夊€?
                    def safe_value(val, default='No'):
                        if val is None or val == '' or val == 'N/A':
                            return default
                        return str(val)
                    
                    # 妾㈡煡鏁告摎鏄惁瀹屾暣锛岀敤鏂艰ō缃媭鎱?
                    def check_data_complete(data):
                        key_fields = ['date', 'invoice_no', 'seller_name', 'total']
                        for field in key_fields:
                            val = data.get(field, '')
                            if not val or val == 'N/A' or val == '' or (isinstance(val, (int, float)) and val == 0 and field == 'total'):
                                return False
                        return True
                    
                    # 妾㈡煡閲嶈鐧肩エ
                    invoice_no = safe_value(data.get("invoice_no"), "No")
                    invoice_date = safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d"))
                    is_duplicate, dup_id = check_duplicate_invoice(invoice_no, invoice_date, user)
                    
                    if is_duplicate:
                        st.warning(f"鈿狅笍 {f.name}: 鐤戜技閲嶈鐧肩エ锛堢櫦绁ㄨ櫉纰? {invoice_no}, 鏃ユ湡: {invoice_date}锛岃閷処D: {dup_id}锛?)
                        fail_count += 1
                        continue
                    
                    # 淇濆瓨鍦栫墖
                    image_path = save_invoice_image(image_obj.copy(), f.name, user)
                    
                    # 淇濆瓨鍦栫墖淇℃伅鍒皊ession_state鐢ㄦ柤寰岀簩椤ず
                    if "ocr_images" not in st.session_state:
                        st.session_state.ocr_images = []
                    st.session_state.ocr_images.append({
                        'file_name': f.name,
                        'image_path': image_path,
                        'image_obj': image_obj.copy(),
                        'total': data.get('total', 0),
                        'status': "鉁?姝ｅ父" if check_data_complete(data) else "鉂?缂哄け"
                    })
                    
                    # 鏍规摎瀛樺劜妯″紡閬告搰涓嶅悓鐨勪繚瀛樻柟寮?
                    if st.session_state.use_memory_mode:
                        # 浣跨敤鍏у瓨妯″紡
                        invoice_record = {
                            'id': len(st.session_state.local_invoices) + 1,
                            'user_id': user,
                            'file_name': safe_value(data.get("file_name"), "鏈懡鍚?),
                            'date': safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d")),
                            'invoice_number': safe_value(data.get("invoice_no"), "No"),
                            'seller_name': safe_value(data.get("seller_name"), "No"),
                            'seller_ubn': safe_value(data.get("seller_ubn"), "No"),
                            'subtotal': clean_n(data.get("subtotal", 0)),
                            'tax': clean_n(data.get("tax", 0)),
                            'total': clean_n(data.get("total", 0)),
                            'category': safe_value(data.get("type"), "鍏朵粬"),
                            'subject': safe_value(data.get("category_suggest"), "闆滈爡"),
                            'status': "鉂?缂哄け" if not check_data_complete(data) else safe_value(data.get("status"), "鉁?姝ｅ父"),
                            'image_path': image_path,
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        st.session_state.local_invoices.append(invoice_record)
                        # 纰轰繚鏁告摎宸蹭繚瀛樺埌 session_state
                        st.session_state.data_saved = True
                    else:
                        # 浣跨敤鏁告摎搴?- 纰轰繚鏁告摎淇濆瓨
                        # 鍏堢⒑淇濊硣鏂欒〃瀛樺湪
                        init_db()
                        
                        # 璁€鍙栧湒鐗囨暩鎿氾紙濡傛灉鍦栫墖璺緫瀛樺湪锛?
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
                            safe_value(data.get("file_name"), "鏈懡鍚?),
                            safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d")),
                            safe_value(data.get("invoice_no"), "No"),
                            safe_value(data.get("seller_name"), "No"),
                            safe_value(data.get("seller_ubn"), "No"),
                            clean_n(data.get("subtotal", 0)),
                            clean_n(data.get("tax", 0)),
                            clean_n(data.get("total", 0)),
                            safe_value(data.get("type"), "鍏朵粬"),
                            safe_value(data.get("category_suggest"), "闆滈爡"),
                            "鉂?缂哄け" if not check_data_complete(data) else safe_value(data.get("status"), "鉁?姝ｅ父"),
                            image_path,
                            image_data
                        )
                        
                        result = run_query(q, insert_params, is_select=False)
                        
                        # 绔嬪嵆椹楄瓑鏁告摎鏄惁鐪熺殑淇濆瓨浜?
                        if result:
                            # 鍢楄│绔嬪嵆鏌ヨ椹楄瓑
                            verify_query = "SELECT COUNT(*) as cnt FROM invoices WHERE user_id = ? AND file_name = ?"
                            verify_result = run_query(verify_query, (user, safe_value(data.get("file_name"), "鏈懡鍚?)), is_select=True)
                            if debug_mode:
                                st.write(f"馃攳 椹楄瓑鏌ヨ绲愭灉: {verify_result}")
                        
                        # 椹楄瓑鏁告摎鏄惁鎴愬姛淇濆瓨
                        if not result:
                            st.error(f"鈿狅笍 鏁告摎淇濆瓨澶辨晽锛岃珛妾㈡煡璩囨枡搴€ｇ窔")
                            if st.session_state.db_error:
                                st.error(f"閷瑭虫儏: {st.session_state.db_error}")
                            # 濡傛灉鏁告摎搴繚瀛樺け鏁楋紝鍢楄│鍒囨彌鍒板収瀛樻ā寮?
                            st.warning("馃挕 鍢楄│鍒囨彌鍒板収瀛樻ā寮忎繚瀛樻暩鎿?..")
                            invoice_record = {
                                'id': len(st.session_state.local_invoices) + 1,
                                'user_id': user,
                                'file_name': safe_value(data.get("file_name"), "鏈懡鍚?),
                                'date': safe_value(data.get("date"), datetime.now().strftime("%Y/%m/%d")),
                                'invoice_number': safe_value(data.get("invoice_no"), "No"),
                                'seller_name': safe_value(data.get("seller_name"), "No"),
                                'seller_ubn': safe_value(data.get("seller_ubn"), "No"),
                                'subtotal': clean_n(data.get("subtotal", 0)),
                                'tax': clean_n(data.get("tax", 0)),
                                'total': clean_n(data.get("total", 0)),
                                'category': safe_value(data.get("type"), "鍏朵粬"),
                                'subject': safe_value(data.get("category_suggest"), "闆滈爡"),
                                'status': "鉂?缂哄け" if not check_data_complete(data) else safe_value(data.get("status"), "鉁?姝ｅ父"),
                                'image_path': image_path,
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            st.session_state.local_invoices.append(invoice_record)
                            st.session_state.use_memory_mode = True
                            st.session_state.data_saved = True
                            st.write(f"鉁?{f.name}: 鎴愬姛 (${data.get('total', 0)}) - 宸蹭繚瀛樺埌鍏у瓨")
                        else:
                            # 鏁告摎淇濆瓨鎴愬姛
                            st.session_state.data_saved = True
                    success_count += 1
                else:
                    st.error(f"鉂?{f.name} 澶辨晽: {err}")
                    st.session_state.ocr_report.append(f"{f.name}: {err}")
                    fail_count += 1
                
                prog.progress((idx+1)/len(files))
            
            status.update(label=f"铏曠悊瀹屾垚! 鎴愬姛: {success_count}, 澶辨晽: {fail_count}", state="complete", expanded=True)
            
        # 椤ず璀樺垾鎴愬姛鐨勫湒鐗囬爯瑕斤紙灏忓湒锛岄粸鎿婃斁澶э級
        if success_count > 0 and "ocr_images" in st.session_state and st.session_state.ocr_images:
            st.divider()
            st.subheader("馃摲 璀樺垾绲愭灉闋愯")
            # 浣跨敤鍒楅’绀哄寮靛湒鐗?
            num_cols = 3
            cols = st.columns(num_cols)
            for idx, img_info in enumerate(st.session_state.ocr_images):
                col_idx = idx % num_cols
                with cols[col_idx]:
                    # 椤ず绺暐鍦?
                    thumbnail = img_info['image_obj'].copy()
                    thumbnail.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    st.image(thumbnail, caption=f"{img_info['file_name']}\n${img_info['total']} {img_info['status']}", use_container_width=True)
                    
                    # 榛炴搳鎸夐垥鏀惧ぇ
                    zoom_key = f"zoom_img_{idx}"
                    if st.button("馃攳 鏀惧ぇ", key=zoom_key, use_container_width=True):
                        st.session_state[f"show_full_{idx}"] = not st.session_state.get(f"show_full_{idx}", False)
                    
                    # 濡傛灉榛炴搳浜嗘斁澶э紝椤ず澶у湒
                    if st.session_state.get(f"show_full_{idx}", False):
                        if img_info['image_path'] and os.path.exists(img_info['image_path']):
                            st.image(img_info['image_path'], caption=img_info['file_name'], use_container_width=True)
                            # 鎻愪緵涓嬭級鎸夐垥
                            with open(img_info['image_path'], 'rb') as img_file:
                                img_bytes = img_file.read()
                                st.download_button("馃摜 涓嬭級", img_bytes, 
                                                 file_name=os.path.basename(img_info['image_path']),
                                                 mime="image/jpeg", key=f"download_{idx}")
            
            # 娓呯┖鑷ㄦ檪鍦栫墖鏁告摎锛堝湪rerun鍓嶏級
            if st.button("鉁?瀹屾垚锛屾煡鐪嬫暩鎿氬垪琛?, use_container_width=True, type="primary"):
                st.session_state.ocr_images = []
                st.rerun()
        
        if success_count > 0:
            # 涓嶆竻绌簅cr_images锛岃畵鐢ㄦ埗鍙互鍏堥爯瑕?
            # time.sleep(1) # 璁撲娇鐢ㄨ€呯◢寰湅涓€涓嬬祼鏋?
            # st.rerun()  # 鏀圭偤鎵嬪嫊瑙哥櫦rerun
            pass
    
    with import_tab2:
        st.info("馃挕 鏀寔灏庡叆 Excel (.xlsx) 鎴?CSV (.csv) 鏍煎紡鐨勭櫦绁ㄦ暩鎿?)
        
        # 涓嬭級灏庡叆妯℃澘
        template_data = {
            "妾旀鍚嶇ū": ["鐧肩エ1.jpg", "鐧肩エ2.jpg"],
            "鏃ユ湡": ["2025/01/01", "2025/01/02"],
            "鐧肩エ铏熺⒓": ["AB12345678", "CD87654321"],
            "璩ｆ柟鍚嶇ū": ["娓│鍟嗗簵", "娓│鍏徃"],
            "璩ｆ柟绲辩法": ["12345678", "87654321"],
            "閵峰敭椤?: [1000, 2000],
            "绋呴": [50, 100],
            "绺借▓": [1050, 2100],
            "椤炲瀷": ["椁愰２", "浜ら€?],
            "鏈冭▓绉戠洰": ["椁愰２璨?, "浜ら€氳不"]
        }
        template_df = pd.DataFrame(template_data)
        template_csv = template_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("馃摜 涓嬭級灏庡叆妯℃澘 (CSV)", template_csv, "invoice_import_template.csv", 
                         mime="text/csv", use_container_width=True)
        
        uploaded_file = st.file_uploader("閬告搰瑕佸皫鍏ョ殑鏂囦欢", type=["csv", "xlsx"], key="import_file")
        
        if uploaded_file and st.button("闁嬪灏庡叆", type="primary", use_container_width=True):
            try:
                # 璁€鍙栨枃浠?
                if uploaded_file.name.endswith('.csv'):
                    import_df = pd.read_csv(uploaded_file)
                else:
                    try:
                        import_df = pd.read_excel(uploaded_file)
                    except:
                        st.error("璜嬪畨瑁?openpyxl 搴互鏀寔 Excel 鏂囦欢: pip install openpyxl")
                        st.stop()
                
                if import_df.empty:
                    st.error("鏂囦欢鐐虹┖锛岃珛妾㈡煡鏂囦欢鍏у")
                else:
                    # 椤ず闋愯
                    st.subheader("馃搵 灏庡叆鏁告摎闋愯锛堝墠5绛嗭級")
                    st.dataframe(import_df.head(5), use_container_width=True)
                    
                    # 鍒楀悕鏄犲皠锛堟敮鎸佸绋彲鑳界殑鍒楀悕锛?
                    column_mapping = {
                        "妾旀鍚嶇ū": ["妾旀鍚嶇ū", "file_name", "妾斿悕", "鏂囦欢鍚?],
                        "鏃ユ湡": ["鏃ユ湡", "date", "Date"],
                        "鐧肩エ铏熺⒓": ["鐧肩エ铏熺⒓", "invoice_number", "invoice_no", "鐧肩エ铏?],
                        "璩ｆ柟鍚嶇ū": ["璩ｆ柟鍚嶇ū", "seller_name", "璩ｆ柟", "鍟嗗鍚嶇ū"],
                        "璩ｆ柟绲辩法": ["璩ｆ柟绲辩法", "seller_ubn", "绲辩法", "绲变竴绶ㄨ櫉"],
                        "閵峰敭椤?: ["閵峰敭椤?, "subtotal", "鏈▍閲戦"],
                        "绋呴": ["绋呴", "tax", "Tax"],
                        "绺借▓": ["绺借▓", "total", "Total", "閲戦"],
                        "椤炲瀷": ["椤炲瀷", "category", "Category"],
                        "鏈冭▓绉戠洰": ["鏈冭▓绉戠洰", "subject", "Subject", "绉戠洰"]
                    }
                    
                    # 妯欐簴鍖栧垪鍚?
                    for standard_name, possible_names in column_mapping.items():
                        for possible_name in possible_names:
                            if possible_name in import_df.columns:
                                import_df.rename(columns={possible_name: standard_name}, inplace=True)
                                break
                    
                    # 妾㈡煡蹇呭～瀛楁
                    required_fields = ["鏃ユ湡", "鐧肩エ铏熺⒓", "绺借▓"]
                    missing_fields = [f for f in required_fields if f not in import_df.columns]
                    if missing_fields:
                        st.error(f"缂哄皯蹇呭～瀛楁: {', '.join(missing_fields)}")
                    else:
                        # 闁嬪灏庡叆
                        imported_count = 0
                        duplicate_count = 0
                        error_count = 0
                        
                        with st.status("姝ｅ湪灏庡叆鏁告摎...", expanded=True) as status:
                            for idx, row in import_df.iterrows():
                                try:
                                    # 妾㈡煡閲嶈
                                    invoice_no = str(row.get("鐧肩エ铏熺⒓", "No"))
                                    invoice_date = str(row.get("鏃ユ湡", ""))
                                    is_dup, _ = check_duplicate_invoice(invoice_no, invoice_date, user)
                                    
                                    if is_dup:
                                        duplicate_count += 1
                                        continue
                                    
                                    # 铏曠悊鏁稿€?
                                    def safe_float(val):
                                        try:
                                            return float(str(val).replace(',', '').replace('$', ''))
                                        except:
                                            return 0.0
                                    
                                    def safe_str(val, default="No"):
                                        val_str = str(val) if not pd.isna(val) else ""
                                        return val_str if val_str.strip() else default
                                    
                                    # 淇濆瓨鏁告摎
                                    if st.session_state.use_memory_mode:
                                        invoice_record = {
                                            'id': len(st.session_state.local_invoices) + 1,
                                            'user_id': user,
                                            'file_name': safe_str(row.get("妾旀鍚嶇ū"), "灏庡叆鏁告摎"),
                                            'date': safe_str(row.get("鏃ユ湡"), datetime.now().strftime("%Y/%m/%d")),
                                            'invoice_number': safe_str(row.get("鐧肩エ铏熺⒓"), "No"),
                                            'seller_name': safe_str(row.get("璩ｆ柟鍚嶇ū"), "No"),
                                            'seller_ubn': safe_str(row.get("璩ｆ柟绲辩法"), "No"),
                                            'subtotal': safe_float(row.get("閵峰敭椤?, 0)),
                                            'tax': safe_float(row.get("绋呴", 0)),
                                            'total': safe_float(row.get("绺借▓", 0)),
                                            'category': safe_str(row.get("椤炲瀷"), "鍏朵粬"),
                                            'subject': safe_str(row.get("鏈冭▓绉戠洰"), "闆滈爡"),
                                            'status': "鉁?姝ｅ父",
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
                                            safe_str(row.get("妾旀鍚嶇ū"), "灏庡叆鏁告摎"),
                                            safe_str(row.get("鏃ユ湡"), datetime.now().strftime("%Y/%m/%d")),
                                            safe_str(row.get("鐧肩エ铏熺⒓"), "No"),
                                            safe_str(row.get("璩ｆ柟鍚嶇ū"), "No"),
                                            safe_str(row.get("璩ｆ柟绲辩法"), "No"),
                                            safe_float(row.get("閵峰敭椤?, 0)),
                                            safe_float(row.get("绋呴", 0)),
                                            safe_float(row.get("绺借▓", 0)),
                                            safe_str(row.get("椤炲瀷"), "鍏朵粬"),
                                            safe_str(row.get("鏈冭▓绉戠洰"), "闆滈爡"),
                                            "鉁?姝ｅ父"
                                        )
                                        if run_query(q, params, is_select=False):
                                            imported_count += 1
                                        else:
                                            error_count += 1
                                    
                                except Exception as e:
                                    error_count += 1
                                    if debug_mode:
                                        st.write(f"绗?{idx+1} 绛嗗皫鍏ュけ鏁? {str(e)}")
                        
                        # 椤ず绲愭灉
                        if imported_count > 0:
                            st.success(f"鉁?鎴愬姛灏庡叆 {imported_count} 绛嗘暩鎿?)
                        if duplicate_count > 0:
                            st.warning(f"鈿狅笍 璺抽亷 {duplicate_count} 绛嗛噸瑜囨暩鎿?)
                        if error_count > 0:
                            st.error(f"鉂?{error_count} 绛嗘暩鎿氬皫鍏ュけ鏁?)
                        
                        if imported_count > 0:
                            time.sleep(1)
                            st.rerun()
                            
            except Exception as e:
                st.error(f"灏庡叆澶辨晽: {str(e)}")
                if debug_mode:
                    st.exception(e)

# 鏌ヨ鏁告摎锛堝湪鍏╁€嬪垪涔嬪锛岀⒑淇濅綔鐢ㄥ煙姝ｇ⒑锛?
# 娣诲姞瑾胯│淇℃伅锛堝彲閬革紝鐢ㄦ柤鎺掓煡鍟忛锛? 蹇呴爤鍦ㄦ煡瑭箣鍓嶅畾缇?
debug_mode = st.sidebar.checkbox("馃攳 椤ず瑾胯│淇℃伅", value=False)

df_raw = run_query("SELECT * FROM invoices WHERE user_id = ? ORDER BY id DESC", (user,))
if debug_mode:
    st.sidebar.write(f"馃搳 鍘熷鏌ヨ绲愭灉绛嗘暩: {len(df_raw)}")
    st.sidebar.write(f"馃搵 鐢ㄦ埗ID: {user}")
    db_path = get_db_path()
    st.sidebar.write(f"馃搧 璩囨枡搴矾寰? {db_path}")
    st.sidebar.write(f"馃捑 瀛樺劜妯″紡: {'鍏у瓨妯″紡' if st.session_state.use_memory_mode else '鏁告摎搴ā寮?}")
    if "mode=memory" in db_path:
        st.sidebar.error("鈿狅笍 浣跨敤鍏у瓨鏁告摎搴紒鍒锋柊闋侀潰鏈冩竻绌烘暩鎿?)
    if not st.session_state.use_memory_mode:
        # 妾㈡煡鏁告摎搴枃浠舵槸鍚﹀瓨鍦?
        if os.path.exists(db_path):
            file_size = os.path.getsize(db_path)
            st.sidebar.write(f"馃摝 鏁告摎搴枃浠跺ぇ灏? {file_size} bytes")
        else:
            st.sidebar.warning("鈿狅笍 鏁告摎搴枃浠朵笉瀛樺湪")
    if not df_raw.empty:
        st.sidebar.write(f"馃摑 娆勪綅鍚嶇ū: {list(df_raw.columns)}")
        st.sidebar.write(f"馃搫 鍓?绛嗘暩鎿氶爯瑕?")
        st.sidebar.dataframe(df_raw.head(3))
    else:
        st.sidebar.warning("鈿狅笍 鏌ヨ绲愭灉鐐虹┖")
        if not st.session_state.use_memory_mode:
            # 鍢楄│鏌ヨ鎵€鏈夋暩鎿氾紙涓嶆寜user_id閬庢烤锛?
            all_data = run_query("SELECT COUNT(*) as cnt FROM invoices", (), is_select=True)
            if not all_data.empty:
                total_count = all_data.iloc[0, 0] if 'cnt' in all_data.columns else all_data.iloc[0, 0]
                st.sidebar.write(f"馃搳 鏁告摎搴附瑷橀寗鏁? {total_count}")
                if total_count > 0:
                    st.sidebar.info(f"馃挕 鏁告摎搴腑鏈?{total_count} 绛嗘暩鎿氾紝浣嗙暥鍓嶇敤鎴?'{user}' 娌掓湁鏁告摎")

with col_main:
    # ========== 闋傞儴锛氱当瑷堟寚妯欏崱鐗囧崁 ==========
    st.subheader("馃搳 绲辫▓鍫辫〃")
    df_stats = df_raw.copy()
    if not df_stats.empty:
        # 鍏堥噸鍛藉悕鍒椾互渚跨当瑷堝牨琛ㄤ娇鐢?
        mapping = {"file_name":"妾旀鍚嶇ū","date":"鏃ユ湡","invoice_number":"鐧肩エ铏熺⒓","seller_name":"璩ｆ柟鍚嶇ū","seller_ubn":"璩ｆ柟绲辩法","subtotal":"閵峰敭椤?,"tax":"绋呴","total":"绺借▓","category":"椤炲瀷","subject":"鏈冭▓绉戠洰","status":"鐙€鎱?}
        df_stats = df_stats.rename(columns=mapping)
        
        if "绺借▓" in df_stats.columns:
            for c in ["绺借▓", "绋呴"]: 
                if c in df_stats.columns:
                    df_stats[c] = pd.to_numeric(df_stats[c].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            
            # 绲辫▓鎸囨鍗＄墖锛堜甫鎺掗’绀猴級
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            total_sum = pd.to_numeric(df_stats['绺借▓'], errors='coerce').fillna(0).sum()
            tax_sum = pd.to_numeric(df_stats['绋呴'], errors='coerce').fillna(0).sum()
            invoice_count = len(df_stats)
            missing_count = len(df_stats[df_stats['鐙€鎱?].astype(str).str.contains('缂哄け', na=False)]) if '鐙€鎱? in df_stats.columns else 0
            
            with stat_col1:
                st.metric("绱▓閲戦", f"${total_sum:,.0f}")
            with stat_col2:
                st.metric("绱▓绋呴", f"${tax_sum:,.0f}")
            with stat_col3:
                st.metric("鐧肩エ绺芥暩", f"{invoice_count} 绛?)
            with stat_col4:
                st.metric("缂哄け鏁告摎", f"{missing_count} 绛?, delta=f"-{invoice_count - missing_count} 姝ｅ父" if invoice_count > 0 else None)
            
            st.divider()
            
            # ========== 涓枔锛氬湒琛ㄥ睍绀哄崁锛堜甫鎺掗’绀猴級==========
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # 鍦撻鍦?- 鏈冭▓绉戠洰鍒嗗竷
                if "鏈冭▓绉戠洰" in df_stats.columns:
                    df_chart = df_stats[df_stats['鏈冭▓绉戠洰'].notna() & (df_stats['鏈冭▓绉戠洰'] != 'No')].copy()
                    if not df_chart.empty:
                        chart = alt.Chart(df_chart).mark_arc(innerRadius=40).encode(
                            theta=alt.Theta("count()", type="quantitative"),
                            color=alt.Color("鏈冭▓绉戠洰", type="nominal"),
                            tooltip=["鏈冭▓绉戠洰", "count()"]
                        ).properties(height=300, title="鏈冭▓绉戠洰鍒嗗竷")
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("馃搳 鏆劇鏈冭▓绉戠洰鏁告摎")
                elif "subject" in df_raw.columns:
                    df_stats_chart = df_raw.copy()
                    df_stats_chart = df_stats_chart[df_stats_chart['subject'].notna() & (df_stats_chart['subject'] != 'No')]
                    if not df_stats_chart.empty:
                        chart = alt.Chart(df_stats_chart).mark_arc(innerRadius=40).encode(
                            theta=alt.Theta("count()", type="quantitative"),
                            color=alt.Color("subject", type="nominal"),
                            tooltip=["subject", "count()"]
                        ).properties(height=300, title="鏈冭▓绉戠洰鍒嗗竷")
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("馃搳 鏆劇鏈冭▓绉戠洰鏁告摎")
                else:
                    st.info("馃搳 鏆劇鏈冭▓绉戠洰鏁告摎")
            
            with chart_col2:
                # 鎶樼窔鍦?- 姣忔棩鏀嚭瓒ㄥ嫝
                if "鏃ユ湡" in df_stats.columns and "绺借▓" in df_stats.columns:
                    df_line = df_stats.copy()
                    df_line['鏃ユ湡'] = pd.to_datetime(df_line['鏃ユ湡'], errors='coerce', format='%Y/%m/%d')
                    df_line = df_line.dropna(subset=['鏃ユ湡'])
                    
                    if not df_line.empty:
                        df_line_grouped = df_line.groupby('鏃ユ湡')['绺借▓'].sum().reset_index()
                        df_line_grouped = df_line_grouped.sort_values('鏃ユ湡')
                        
                        line_chart = alt.Chart(df_line_grouped).mark_line(point=True, strokeWidth=2).encode(
                            x=alt.X('鏃ユ湡:T', title='鏃ユ湡', axis=alt.Axis(format='%Y/%m/%d')),
                            y=alt.Y('绺借▓:Q', title='閲戦 ($)', axis=alt.Axis(format='$,.0f')),
                            tooltip=[alt.Tooltip('鏃ユ湡:T', format='%Y/%m/%d'), alt.Tooltip('绺借▓:Q', format='$,.0f')]
                        ).properties(
                            height=300,
                            title="姣忔棩鏀嚭瓒ㄥ嫝"
                        ).configure_axis(
                            labelFontSize=10,
                            titleFontSize=12
                        ).configure_title(
                            fontSize=14
                        )
                        st.altair_chart(line_chart, use_container_width=True)
                    else:
                        st.info("馃搱 鐒℃湁鏁堢殑鏃ユ湡鏁告摎鍙’绀烘姌绶氬湒")
                else:
                    st.info("馃搱 闇€瑕佹棩鏈熷拰绺借▓娆勪綅鎵嶈兘椤ず鎶樼窔鍦?)
            
            st.divider()
    else:
        # 濡傛灉娌掓湁鏁告摎锛岄’绀烘彁绀?
        st.info("馃搳 鐩墠鐒＄当瑷堟暩鎿?)
    
    # ========== 搴曢儴锛氭暩鎿氬牨琛ㄥ崁 ==========
    st.subheader("馃搵 鏁告摎绋芥牳鍫辫〃")
    
    # 鏌ヨ姊濅欢锛堢啊鍖栫増锛屼笉鎶樼枈锛?
    sc1, sc2 = st.columns([2, 1])
    search = sc1.text_input("馃攳 闂滈嵉瀛楁悳灏?, placeholder="铏熺⒓/璩ｆ柟/妾斿悕...")
    t_filter = sc2.selectbox("馃晵 鏅傞枔绡勫湇", ["鍏ㄩ儴", "浠婂ぉ", "鏈€?, "鏈湀"])
    
    # 浣跨敤鍘熷鏌ヨ绲愭灉锛堝鏋渄f_stats宸插畾缇╋紝浣跨敤瀹冿紱鍚﹀墖浣跨敤df_raw涓﹂噸鍛藉悕锛?
    if 'df_stats' in locals() and not df_stats.empty:
        df = df_stats.copy()
    else:
        df = df_raw.copy()
        # 濡傛灉浣跨敤df_raw锛岄渶瑕侀噸鍛藉悕鍒?
        if not df.empty:
            mapping = {"file_name":"妾旀鍚嶇ū","date":"鏃ユ湡","invoice_number":"鐧肩エ铏熺⒓","seller_name":"璩ｆ柟鍚嶇ū","seller_ubn":"璩ｆ柟绲辩法","subtotal":"閵峰敭椤?,"tax":"绋呴","total":"绺借▓","category":"椤炲瀷","subject":"鏈冭▓绉戠洰","status":"鐙€鎱?}
            df = df.rename(columns=mapping)
    
    # 鎵嬪嫊鍦ㄨ鎲堕珨涓閬革紙閬垮厤 SQL 閬庢柤瑜囬洔鍑洪尟锛?
    if not df.empty:
        if search:
            df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        if t_filter != "鍏ㄩ儴":
            # 瀵︾従鏃ユ湡閬庢烤鍔熻兘锛堜娇鐢ㄥ凡閲嶅懡鍚嶇殑鍒楀悕锛?
            if "鏃ユ湡" in df.columns:
                date_col = "鏃ユ湡"
                today = datetime.now().date()
                
                try:
                    # 灏囨棩鏈熷垪杞夋彌鐐烘棩鏈熸牸寮?
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce', format='%Y/%m/%d')
                    df = df.dropna(subset=[date_col])  # 绉婚櫎鐒℃硶瑙ｆ瀽鐨勬棩鏈?
                    
                    if t_filter == "浠婂ぉ":
                        df = df[df[date_col].dt.date == today]
                    elif t_filter == "鏈€?:
                        # 瑷堢畻鏈€辩殑闁嬪鏃ユ湡锛堥€变竴锛?
                        days_since_monday = today.weekday()
                        week_start = today - timedelta(days=days_since_monday)
                        df = df[df[date_col].dt.date >= week_start]
                    elif t_filter == "鏈湀":
                        # 鏈湀
                        month_start = today.replace(day=1)
                        df = df[df[date_col].dt.date >= month_start]
                except Exception as e:
                    if debug_mode:
                        st.warning(f"鏃ユ湡閬庢烤閷: {str(e)}")
                    # 濡傛灉鏃ユ湡鏍煎紡涓嶆纰猴紝鍢楄│瀛楃涓插尮閰?
                    if t_filter == "浠婂ぉ":
                        today_str = today.strftime("%Y/%m/%d")
                        df = df[df[date_col].astype(str).str.contains(today_str, na=False)]
                    elif t_filter == "鏈湀":
                        month_str = today.strftime("%Y/%m")
                        df = df[df[date_col].astype(str).str.contains(month_str, na=False)]
    
    # 鏁告摎琛ㄦ牸椤ず锛坉f宸茬稉閲嶅懡鍚嶉亷锛岀洿鎺ヤ娇鐢級
    if not df.empty:
        # 铏曠悊绌哄€硷細鐢?No"鏇挎彌
        def fill_empty(val):
            if pd.isna(val) or val == '' or val == 'N/A' or str(val).strip() == '':
                return 'No'
            return str(val)
        
        # 灏嶆墍鏈夊垪鎳夌敤绌哄€艰檿鐞嗭紙闄や簡鐙€鎱嬪垪锛岀媭鎱嬪垪闇€瑕佺壒娈婅檿鐞嗭級
        for col in df.columns:
            if col not in ['閬稿彇', 'id', '鐙€鎱?]:  # 璺抽亷閬稿彇銆乮d鍜岀媭鎱嬪垪
                df[col] = df[col].apply(fill_empty)
        
        # 铏曠悊鐙€鎱嬪垪锛氭鏌ユ槸鍚︽湁缂哄け鏁告摎锛屽鏋滄湁鍓囬’绀?缂哄け"
        if "鐙€鎱? in df.columns:
            def check_status(row):
                # 妾㈡煡闂滈嵉瀛楁鏄惁鐐虹┖鎴?No"
                key_fields = ['鏃ユ湡', '鐧肩エ铏熺⒓', '璩ｆ柟鍚嶇ū', '绺借▓']
                has_missing = False
                for field in key_fields:
                    if field in row:
                        val = str(row[field]).strip()
                        if pd.isna(row[field]) or val == '' or val == 'N/A' or val == 'No' or val == '鏈～':
                            has_missing = True
                            break
                
                # 濡傛灉鍘熸湰鐨勭媭鎱嬪凡缍撴槸閷鐙€鎱嬶紝淇濇寔鍘熸ǎ锛堜絾纰轰繚鏈夌磪鑹瞂锛?
                original_status = str(row.get('鐙€鎱?, '')).strip()
                if '缂烘紡' in original_status or '缂哄け' in original_status or '閷' in original_status:
                    # 濡傛灉宸茬稉鏈夆潓锛屼繚鎸佸師妯ｏ紱濡傛灉娌掓湁锛屾坊鍔犫潓
                    if '鉂? not in original_status and '鈿狅笍' not in original_status:
                        return f'鉂?{original_status}'
                    return original_status
                
                # 濡傛灉鏈夌己澶憋紝杩斿洖甯剁磪鑹瞂鐨?缂哄け"
                if has_missing:
                    return '鉂?缂哄け'
                
                # 鍚﹀墖杩斿洖鍘熺媭鎱嬫垨"姝ｅ父"
                return original_status if original_status else '鉁?姝ｅ父'
            
            df['鐙€鎱?] = df.apply(check_status, axis=1)
        
        # 瑾挎暣鍒楅爢搴忥細閬稿彇 -> 鐙€鎱?-> 鍏朵粬鍒?
        if "閬稿彇" not in df.columns: 
            df.insert(0, "閬稿彇", False)
        
        # 灏囩媭鎱嬪垪绉诲埌閬稿彇鍒椾箣寰?
        if "鐙€鎱? in df.columns:
            cols = df.columns.tolist()
            cols.remove("鐙€鎱?)
            # 鎵惧埌閬稿彇鍒楃殑浣嶇疆锛屽湪鍏跺緦鎻掑叆鐙€鎱?
            select_idx = cols.index("閬稿彇") if "閬稿彇" in cols else 0
            cols.insert(select_idx + 1, "鐙€鎱?)
            df = df[cols]
        
        if st.button("馃棏锔?鍒櫎閬镐腑鏁告摎"):
            ids = df[df["閬稿彇"]==True]["id"].tolist()
            if st.session_state.use_memory_mode:
                # 鍏у瓨妯″紡锛氬緸鍒楄〃涓埅闄?
                st.session_state.local_invoices = [inv for inv in st.session_state.local_invoices if inv.get('id') not in ids]
            else:
                # 鏁告摎搴ā寮?
                for i in ids: run_query("DELETE FROM invoices WHERE id=?", (i,), is_select=False)
            st.rerun()
        
        # 淇濆瓨鍘熷鏁告摎鐨勫壇鏈敤鏂兼瘮杓?
        original_df_copy = df.copy()
        
        # 婧栧倷鍒楅厤缃?
        column_config = {
            "id": None, 
            "閬稿彇": st.column_config.CheckboxColumn("閬稿彇", default=False),
            "妾旀鍚嶇ū": st.column_config.TextColumn("妾旀鍚嶇ū", width="medium"),
            "绺借▓": st.column_config.NumberColumn("绺借▓", format="$%d"),
            "閵峰敭椤?: st.column_config.NumberColumn("閵峰敭椤?, format="$%d"),
            "绋呴": st.column_config.NumberColumn("绋呴", format="$%d")
        }
        
        # 铏曠悊鏃ユ湡鍒楋細鍢楄│杞夋彌鐐烘棩鏈熼鍨?
        df_for_editor = df.copy()
        if "鏃ユ湡" in df_for_editor.columns:
            try:
                # 鍢楄│灏囨棩鏈熷瓧绗︿覆杞夋彌鐐烘棩鏈熼鍨?
                df_for_editor["鏃ユ湡"] = pd.to_datetime(df_for_editor["鏃ユ湡"], errors='coerce', format='%Y/%m/%d')
                # 濡傛灉杞夋彌鎴愬姛锛堟矑鏈夊叏閮ㄧ偤NaT锛夛紝浣跨敤DateColumn
                if not df_for_editor["鏃ユ湡"].isna().all():
                    column_config["鏃ユ湡"] = st.column_config.DateColumn("鏃ユ湡", format="YYYY/MM/DD")
                else:
                    # 杞夋彌澶辨晽锛屼娇鐢═extColumn
                    column_config["鏃ユ湡"] = st.column_config.TextColumn("鏃ユ湡", width="medium")
                    df_for_editor["鏃ユ湡"] = df["鏃ユ湡"]  # 鎭㈠京鍘熷瀛楃涓?
            except:
                # 杞夋彌澶辨晽锛屼娇鐢═extColumn
                column_config["鏃ユ湡"] = st.column_config.TextColumn("鏃ユ湡", width="medium")
                df_for_editor["鏃ユ湡"] = df["鏃ユ湡"]  # 纰轰繚浣跨敤鍘熷瀛楃涓?
        
        ed_df = st.data_editor(df_for_editor, use_container_width=True, hide_index=True, height=500, 
                               column_config=column_config,
                               key="data_editor")
        
        # 濡傛灉鏃ユ湡琚綁鎻涚偤鏃ユ湡椤炲瀷锛岄渶瑕佽綁鍥炲瓧绗︿覆鏍煎紡浠ヤ究淇濆瓨
        if "鏃ユ湡" in ed_df.columns and ed_df["鏃ユ湡"].dtype != object:
            ed_df["鏃ユ湡"] = ed_df["鏃ユ湡"].dt.strftime("%Y/%m/%d").fillna(df["鏃ユ湡"])
        
        df["閬稿彇"] = ed_df["閬稿彇"]
        
        # 妾㈡脯鏄惁鏈夎畩鏇翠甫鑷嫊淇濆瓨锛堟瘮杓冮棞閸靛瓧娈碉級
        has_changes = False
        try:
            # 姣旇純闂滈嵉瀛楁鏄惁鏈夎畩鍖?
            for col in ed_df.columns:
                if col not in ['id', '閬稿彇']:
                    if col in original_df_copy.columns:
                        if not ed_df[col].equals(original_df_copy[col]):
                            has_changes = True
                            break
                    else:
                        has_changes = True
                        break
        except:
            # 濡傛灉姣旇純澶辨晽锛屼娇鐢╤ash鏂规硶
            try:
                original_hash = hashlib.md5(str(original_df_copy.values.tobytes()).encode()).hexdigest()
                edited_hash = hashlib.md5(str(ed_df.values.tobytes()).encode()).hexdigest()
                has_changes = (original_hash != edited_hash)
            except:
                has_changes = False
        
        if has_changes:
            # 鏈夎畩鏇达紝鑷嫊淇濆瓨
            saved_count, errors = save_edited_data(ed_df, original_df_copy, user)
            if saved_count > 0:
                st.success(f"鉁?宸茶嚜鍕曚繚瀛?{saved_count} 绛嗘暩鎿氳畩鏇?)
                if errors:
                    for err in errors[:3]:  # 鍙’绀哄墠3鍊嬮尟瑾?
                        st.warning(err)
                time.sleep(0.5)
                st.rerun()
            elif errors:
                st.error(f"淇濆瓨澶辨晽: {errors[0] if errors else '鏈煡閷'}")
    else: 
        # 濡傛灉df鐐虹┖锛堢閬稿緦鎴栧師濮嬫暩鎿氱偤绌猴級
        if not df_raw.empty:
            st.warning("鈿狅笍 鏌ョ劇鏁告摎銆?)
            if debug_mode:
                st.info(f"馃攳 瑾胯│锛氭悳绱㈤棞閸靛瓧 '{search}' 寰岀劇鍖归厤绲愭灉銆傚師濮嬫暩鎿氱瓎鏁? {len(df_raw)}")
        else:
            st.warning("鈿狅笍 鐩墠鐒℃暩鎿氥€傝珛鍏堝槜瑭︿笂鍌充甫杈ㄨ瓨銆?)
            if debug_mode:
                st.info(f"馃攳 瑾胯│锛氳硣鏂欏韩涓矑鏈?user_id='{user}' 鐨勬暩鎿氥€傝珛妾㈡煡锛歕n1. 鏄惁宸蹭笂鍌充甫杈ㄨ瓨鐧肩エ\n2. 鍋撮倞娆勭殑銆岀櫥鍏ュ赋铏熴€嶆槸鍚︽纰?)

    # 灏庡嚭鍔熻兘锛堟斁鍦ㄦ暩鎿氳〃鏍间笅鏂癸級
    if not df.empty and "绺借▓" in df.columns:
        st.divider()
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            # CSV 灏庡嚭
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("馃摜 灏庡嚭 CSV", csv_data, "invoice_report.csv", use_container_width=True)
        
        with export_col2:
            # PDF 灏庡嚭 (浣跨敤 fpdf2)
            if PDF_AVAILABLE:
                def generate_pdf():
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    
                    # 瑷疆涓枃瀛楅珨鏀寔
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
                    
                    # 妯欓
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 16)
                        safe_cell(pdf, 0, 10, '鐧肩エ鍫卞赋绲辫▓鍫辫〃', ln=1, align='C')
                    else:
                        pdf.set_font('Arial', 'B', 16)
                        safe_cell(pdf, 0, 10, 'Invoice Report', ln=1, align='C')
                    pdf.ln(5)
                    
                    # 鐢熸垚鏅傞枔
                    if font_loaded:
                        pdf.set_font(font_name, '', 10)
                        safe_cell(pdf, 0, 5, f'鐢熸垚鏅傞枔: {datetime.now().strftime("%Y骞?m鏈?d鏃?%H:%M:%S")}', ln=1, align='R')
                    else:
                        pdf.set_font('Arial', '', 10)
                        safe_cell(pdf, 0, 5, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ln=1, align='R')
                    pdf.ln(5)
                    
                    # 绲辫▓鎽樿
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 12)
                        safe_cell(pdf, 0, 8, '绲辫▓鎽樿', ln=1)
                        pdf.set_font(font_name, '', 10)
                        safe_cell(pdf, 90, 6, '绱▓閲戦:', 1)
                        # 瑷堢畻绲辫▓鏁告摎
                        if "绺借▓" in df.columns:
                            total_sum = pd.to_numeric(df['绺借▓'], errors='coerce').fillna(0).sum()
                        else:
                            total_sum = 0
                        safe_cell(pdf, 90, 6, f"${total_sum:,.0f}", 1, ln=1)
                        safe_cell(pdf, 90, 6, '绱▓绋呴:', 1)
                        if "绋呴" in df.columns:
                            tax_sum = pd.to_numeric(df['绋呴'], errors='coerce').fillna(0).sum()
                        else:
                            tax_sum = 0
                        safe_cell(pdf, 90, 6, f"${tax_sum:,.0f}", 1, ln=1)
                        safe_cell(pdf, 90, 6, '鐧肩エ绺芥暩:', 1)
                        safe_cell(pdf, 90, 6, f"{len(df)} 绛?, 1, ln=1)
                    pdf.ln(5)
                    
                    # 瑭崇窗鏁告摎琛ㄦ牸
                    export_df = df.copy()
                    col_widths = [20, 30, 35, 50, 30, 25]
                    if font_loaded:
                        pdf.set_font(font_name, 'B', 10)
                        headers = ['鐙€鎱?, '鏃ユ湡', '鐧肩エ铏熺⒓', '璩ｆ柟鍚嶇ū', '绺借▓', '椤炲瀷']
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
                        status = pdf_safe_value(row.get('鐙€鎱?, ''), '鉂?缂哄け')[:10]
                        date_str = pdf_safe_value(row.get('鏃ユ湡', ''), 'No')[:10]
                        invoice_no = pdf_safe_value(row.get('鐧肩エ铏熺⒓', ''), 'No')[:15]
                        seller = pdf_safe_value(row.get('璩ｆ柟鍚嶇ū', ''), 'No')[:20]
                        total_val = pd.to_numeric(row.get('绺借▓', 0), errors='coerce')
                        if pd.isna(total_val):
                            total_val = 0
                        total = f"${total_val:,.0f}"
                        category = pdf_safe_value(row.get('椤炲瀷', ''), 'No')[:10]
                        
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
                st.download_button("馃搫 灏庡嚭 PDF", pdf_data, f"invoice_report_{datetime.now().strftime('%Y%m%d')}.pdf", 
                                 mime="application/pdf", use_container_width=True)
            else:
                st.info("馃搫 PDF 鍔熻兘闇€瑕佸畨瑁?fpdf2")
