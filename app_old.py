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

# --- 1. 绯荤当浣堝眬鑸囧垵濮嬪寲 ---
st.set_page_config(page_title="鐧肩エ鍫卞赋灏忕绗?, page_icon="馃Ь", layout="wide")

if "db_error" not in st.session_state: st.session_state.db_error = None
if "db_path_mode" not in st.session_state: st.session_state.db_path_mode = "馃捑 鏈湴纾佺"

# --- 2. 绲傛サ闊屾€ц硣鏂欏韩閫ｇ窔鍣?---
def get_db_path():
    if "current_db_path" not in st.session_state:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 鏀圭敤 invoices_v2.db 浠ヨВ姹鸿垔璩囨枡搴彲鑳界櫦鐢熺殑 Disk I/O Error 閹栧畾鍟忛
        db_file = os.path.join(base_dir, "invoices_v2.db")
        try:
            # 娓│瀵叆娆婇檺
            test_path = db_file + ".test"
            with open(test_path, "w") as f: f.write("1")
            os.remove(test_path)
            st.session_state.current_db_path = db_file
            st.session_state.db_path_mode = "馃捑 鏈湴纾佺"
        except:
            # 澶辨晽鍓囬€插叆鍏辩敤瑷樻喍楂旀ā寮?            st.session_state.current_db_path = "file:invoice_mem?mode=memory&cache=shared"
            st.session_state.db_path_mode = "馃 铏涙摤瑷樻喍楂?(閲嶅暉鏈冩竻绌?"
    return st.session_state.current_db_path

def init_db():
    """鍒濆鍖栬硣鏂欒〃锛岀⒑淇濇墍鏈夊繀瑕佹瑒浣嶅瓨鍦?""
    path = get_db_path()
    is_uri = "mode=memory" in path
    try:
        conn = sqlite3.connect(path, timeout=30, uri=is_uri)
        conn.execute('''CREATE TABLE IF NOT EXISTS invoices
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT DEFAULT 'default_user', 
                        file_name TEXT, date TEXT, invoice_number TEXT, seller_name TEXT, seller_ubn TEXT,
                        subtotal REAL, tax REAL, total REAL, category TEXT, subject TEXT, status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        # 瑁滃叏娆勪綅
        for col, c_type in {'user_id': "TEXT", 'status': "TEXT", 'seller_ubn': "TEXT"}.items():
            try: conn.execute(f"ALTER TABLE invoices ADD COLUMN {col} {c_type}")
            except: pass
        conn.commit()
        conn.close()
    except Exception as e:
        st.session_state.db_error = f"鍒濆鍖栧け鏁? {str(e)}"

def run_query(query, params=(), is_select=True):
    path = get_db_path()
    is_uri = "mode=memory" in path
    try:
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False, uri=is_uri)
        if is_select:
            try:
                df = pd.read_sql_query(query, conn, params=params)
            except Exception as e:
                # 闂滈嵉淇京锛氬鏋滅櫦鐝炬矑琛紝鑷嫊鍒濆鍖栦甫閲嶈│
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
        st.session_state.db_error = f"閫ｇ窔鐣板父: {err_msg}"
        return pd.DataFrame() if is_select else False

# 绋嬪紡鍟熷嫊绔嬪嵆鍒濆鍖?init_db()

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

def process_ocr(image_obj, file_name, model_name, api_key_val):
    try:
        if image_obj.mode != "RGB": image_obj = image_obj.convert("RGB")
        # 绋嶅井闄嶄綆瑙ｆ瀽搴︿互鍔犲揩閫熷害涓︽笡灏?Token锛屼絾淇濇寔瓒冲娓呮櫚搴?        image_obj.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
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
DEFAULT_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

with st.sidebar:
    st.title("鈿欙笍 绯荤当鐙€鎱?)
    user = st.text_input("鐧诲叆甯宠櫉", "default_user")
    
    # 鍎厛浣跨敤 Streamlit Secrets
    if "GEMINI_API_KEY" in st.secrets:
        st.success("馃攽 宸蹭娇鐢?Secrets 閲戦懓")
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.text_input("Gemini API Key", DEFAULT_KEY, type="password")
        st.caption("寤鸿鍦?Streamlit Secrets 瑷畾 GEMINI_API_KEY")

    model = st.selectbox("杈ㄨ瓨妯″瀷", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"])
    
    st.divider()
    # 閫欒！鏈冭Ц鐧?run_query锛岃嫢娌掕〃鏈冭嚜鍕曞缓琛?    
    st.info(f"鐣跺墠妯″紡: {st.session_state.get('db_mode', '鏈煡')}")
    
    db_count_df = run_query("SELECT count(*) as count FROM invoices WHERE user_id = ?", (user,))
    if not db_count_df.empty:
        st.success(f"馃搳 宸插瓨鏁告摎: {db_count_df['count'][0]} 绛?)
    
    if st.button("馃棏锔?娓呯┖鏆瓨璩囨枡搴?(鍍?SQLite)"):
        try:
            os.remove("invoices.db")
            st.success("宸叉竻闄わ紒")
            time.sleep(1)
            st.rerun()
        except: pass


st.title("馃搼 鐧肩エ鏀舵摎鍫卞赋灏忕绗?Pro")
col_up, col_main, col_stat = st.columns([1, 2.5, 1])

with col_up:
    st.subheader("馃摛 涓婂偝杈ㄨ瓨")
    files = st.file_uploader("鎵规閬告搰鐓х墖", type=["jpg","png","jpeg"], accept_multiple_files=True)
    if files and st.button("闁嬪杈ㄨ瓨 馃殌", type="primary", use_container_width=True):
        
        # 鍒濆鍖?session_state 鐢ㄦ柤瀛樺劜绲愭灉鍫卞憡锛堝鏋滈倓娌掓湁鐨勮┍锛?        if "ocr_report" not in st.session_state: st.session_state.ocr_report = []
        
        success_count = 0
        fail_count = 0
        
        with st.status("AI 姝ｅ湪鍒嗘瀽鐧肩エ涓?..", expanded=True) as status:
            prog = st.progress(0)
            
            for idx, f in enumerate(files):
                st.write(f"姝ｅ湪铏曠悊: {f.name} ...")
                data, err = process_ocr(Image.open(f), f.name, model, api_key)
                
                if data:
                    def clean_n(v):
                        try: return float(str(v).replace(',','').replace('$',''))
                        except: return 0.0
                    q = "INSERT INTO invoices (user_id, file_name, date, invoice_number, seller_name, seller_ubn, subtotal, tax, total, category, subject, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
                    run_query(q, (user, data["file_name"], data["date"], data["invoice_no"], data["seller_name"], data["seller_ubn"], 
                                clean_n(data["subtotal"]), clean_n(data["tax"]), clean_n(data["total"]), data["type"], data["category_suggest"], data["status"]), is_select=False)
                    st.write(f"鉁?{f.name}: 鎴愬姛 (${data.get('total', 0)})")
                    success_count += 1
                else:
                    st.error(f"鉂?{f.name} 澶辨晽: {err}")
                    st.session_state.ocr_report.append(f"{f.name}: {err}")
                    fail_count += 1
                
                prog.progress((idx+1)/len(files))
            
            status.update(label=f"铏曠悊瀹屾垚! 鎴愬姛: {success_count}, 澶辨晽: {fail_count}", state="complete", expanded=True)
            
        if success_count > 0:
            time.sleep(1) # 璁撲娇鐢ㄨ€呯◢寰湅涓€涓嬬祼鏋?            st.rerun()

with col_main:
    sc1, sc2 = st.columns([2, 1])
    search = sc1.text_input("馃攳 闂滈嵉瀛楁悳灏?, placeholder="铏熺⒓/璩ｆ柟/妾斿悕...")
    t_filter = sc2.selectbox("馃晵 鏅傞枔绡勫湇", ["鍏ㄩ儴", "浠婂ぉ", "鏈€?, "鏈湀"])
    
    df = run_query("SELECT * FROM invoices WHERE user_id = ? ORDER BY id DESC", (user,))
    # 鎵嬪嫊鍦ㄨ鎲堕珨涓閬革紙閬垮厤 SQL 閬庢柤瑜囬洔鍑洪尟锛?    if not df.empty:
        if search:
            df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        if t_filter != "鍏ㄩ儴":
            # 绨″柈鏃ユ湡閬庢烤
            pass 
        
        st.subheader("馃搵 鏁告摎绋芥牳鍫辫〃")
        if not df.empty:
            mapping = {"file_name":"妾旀鍚嶇ū","date":"鏃ユ湡","invoice_number":"鐧肩エ铏熺⒓","seller_name":"璩ｆ柟鍚嶇ū","seller_ubn":"璩ｆ柟绲辩法","subtotal":"閵峰敭椤?,"tax":"绋呴","total":"绺借▓","category":"椤炲瀷","subject":"鏈冭▓绉戠洰","status":"鐙€鎱?}
            df = df.rename(columns=mapping)
            if "閬稿彇" not in df.columns: df.insert(0, "閬稿彇", False)
            
            if st.button("馃棏锔?鍒櫎閬镐腑鏁告摎"):
                ids = df[df["閬稿彇"]==True]["id"].tolist()
                for i in ids: run_query("DELETE FROM invoices WHERE id=?", (i,), is_select=False)
                st.rerun()
            
            ed_df = st.data_editor(df, use_container_width=True, hide_index=True, height=500, 
                                   column_config={"id": None, "閬稿彇": st.column_config.CheckboxColumn("閬稿彇", default=False)})
            df["閬稿彇"] = ed_df["閬稿彇"]
        else: st.warning("鈿狅笍 鏌ョ劇鏁告摎銆?)
    else: st.warning("鈿狅笍 鐩墠鐒℃暩鎿氥€傝珛鍏堝槜瑭︿笂鍌充甫杈ㄨ瓨銆?)

with col_stat:
    st.subheader("馃搳 绲辫▓鍫辫〃")
    if not df.empty and "绺借▓" in df.columns:
        for c in ["绺借▓", "绋呴"]: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',',''), errors='coerce').fillna(0)
        m1, m2 = st.columns(2)
        m1.metric("绱▓閲戦", f"${df['绺借▓'].sum():,.0f}")
        m2.metric("绱▓绋呴", f"${df['绋呴'].sum():,.0f}")
        st.divider()
        st.download_button("馃摜 灏庡嚭 CSV", df.to_csv(index=False).encode('utf-8-sig'), "invoice_report.csv", use_container_width=True)
        chart = alt.Chart(df).mark_arc(innerRadius=40).encode(theta="count()", color="椤炲瀷", tooltip=["椤炲瀷", "count()"]).properties(height=200)
        st.altair_chart(chart, use_container_width=True)
