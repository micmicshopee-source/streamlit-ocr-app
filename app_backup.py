import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import time
import threading
import base64
import json
import re
import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# 嘗試載入環境變數（可選）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果沒有安裝 python-dotenv，跳過

# 預設 API Key（如果環境變數中沒有）
DEFAULT_API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

# 页面配置
st.set_page_config(
    page_title="台灣發票 OCR 辨識工具",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"  # 確保側邊欄展開
)

# 添加自定義 CSS 以改善滾動和顯示
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stImage > img {
        max-height: 500px;
        object-fit: contain;
    }
    /* 確保列可以滾動 */
    [data-testid="column"] {
        overflow-y: auto !important;
        overflow-x: hidden !important;
        max-height: calc(100vh - 150px) !important;
        padding-right: 1rem;
    }
    /* 確保內容區域可以滾動 */
    .element-container {
        overflow: visible !important;
    }
    /* 改善文字區域顯示 */
    .stTextArea textarea {
        max-height: 400px;
        overflow-y: auto !important;
    }
    /* 確保表格可以滾動 */
    .stDataFrame {
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

# 標題
st.title("📷 台灣發票 OCR 辨識工具")
st.markdown("**專為台灣發票設計的智能辨識系統，支援二聯式、三聯式、電子發票及收據**")
st.markdown("---")

# 側邊欄 - API 設定
with st.sidebar:
    st.header("⚙️ API 設定")
    
    # 從環境變數讀取 API Key（如果存在），否則使用預設值
    default_api_key = os.getenv("GEMINI_API_KEY", DEFAULT_API_KEY)
    
    api_key = st.text_input(
        "Gemini API Key",
        value=default_api_key,
        type="password",
        help="請輸入您的 Google Gemini API Key（或使用 .env 檔案設定）"
    )
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.success("✅ API Key 已設定")
        except Exception as e:
            st.error(f"API Key 設定失敗: {str(e)}")
    else:
        st.warning("⚠️ 請先輸入 API Key")
    
    st.markdown("---")
    st.markdown("### 📖 使用說明")
    st.markdown("""
    1. 在側邊欄輸入您的 Gemini API Key
    2. 上傳要辨識的圖片
    3. 點擊「開始 OCR 辨識」按鈕
    4. 查看辨識結果
    """)

# 主內容區
col1, col2 = st.columns(2)

with col1:
    st.header("📤 圖片上傳")
    
    uploaded_file = st.file_uploader(
        "選擇圖片檔案",
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'],
        help="支援 PNG, JPG, JPEG, GIF, BMP, WEBP 格式"
    )
    
    if uploaded_file is not None:
        # 讀取圖片數據並保存到 session_state（避免重複讀取問題）
        if 'image_bytes' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
            # 重置文件指針到開頭
            uploaded_file.seek(0)
            st.session_state.image_bytes = uploaded_file.read()
            st.session_state.uploaded_file_name = uploaded_file.name
        
        # 顯示上傳的圖片
        image = Image.open(io.BytesIO(st.session_state.image_bytes))
        
        # 優化圖片顯示：如果圖片太大，先縮放預覽
        max_display_size = 800  # 最大顯示尺寸
        display_image = image.copy()
        
        if image.size[0] > max_display_size or image.size[1] > max_display_size:
            # 計算縮放比例
            ratio = min(max_display_size / image.size[0], max_display_size / image.size[1])
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            display_image = image.resize(new_size, Image.Resampling.LANCZOS)
            st.info(f"📊 圖片已縮放顯示（原始尺寸：{image.size[0]} x {image.size[1]} 像素）")
        
        # 使用容器顯示圖片，允許滾動
        with st.container():
            st.image(display_image, caption="上傳的圖片", use_container_width=True)
        
        # 顯示圖片資訊
        st.info(f"📊 圖片資訊：{image.size[0]} x {image.size[1]} 像素，檔案大小：{len(st.session_state.image_bytes) / 1024:.1f} KB")

with col2:
    st.header("🔍 OCR 辨識結果")
    
    if uploaded_file is not None:
        # OCR 辨識按鈕
        if st.button("🚀 開始 OCR 辨識", type="primary", use_container_width=True):
            if not api_key:
                st.error("❌ 請先在側邊欄輸入 Gemini API Key")
            else:
                try:
                    # 配置 Gemini API
                    genai.configure(api_key=api_key)
                    
                    # 準備圖片（使用 session_state 中保存的圖片數據）
                    if 'image_bytes' in st.session_state:
                        image_pil = Image.open(io.BytesIO(st.session_state.image_bytes))
                        # 確保圖片是 RGB 模式（某些格式可能是 RGBA 或其他）
                        if image_pil.mode != 'RGB':
                            image_pil = image_pil.convert('RGB')
                    else:
                        # 如果 session_state 中沒有，則重新讀取
                        uploaded_file.seek(0)
                        image_bytes = uploaded_file.read()
                        image_pil = Image.open(io.BytesIO(image_bytes))
                        if image_pil.mode != 'RGB':
                            image_pil = image_pil.convert('RGB')
                    
                    # 顯示處理進度
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("🔄 正在初始化模型...")
                    progress_bar.progress(20)
                    
                    # 初始化模型（使用支援視覺的模型）
                    # 根據測試，正確的模型名稱是 gemini-2.5-flash
                    model = None
                    model_name = None
                    
                    # 嘗試不同的模型（使用正確的模型名稱）
                    models_to_try = [
                        'gemini-2.5-flash',  # 最新且最快的模型
                        'gemini-2.5-pro',    # 更強大的模型
                        'gemini-2.0-flash',  # 備選模型
                        'gemini-1.5-flash',  # 舊版本（可能不可用）
                        'gemini-1.5-pro'     # 舊版本（可能不可用）
                    ]
                    
                    for model_name in models_to_try:
                        try:
                            status_text.text(f"🔄 嘗試使用模型: {model_name}...")
                            model = genai.GenerativeModel(model_name)
                            # 測試模型是否可用（簡單測試）
                            break
                        except Exception as e:
                            status_text.text(f"⚠️ 模型 {model_name} 不可用，嘗試下一個...")
                            continue
                    
                    if model is None:
                        raise Exception("無法初始化任何可用的模型，請檢查 API Key 是否正確")
                    
                    status_text.text(f"✅ 已使用模型: {model_name}")
                    progress_bar.progress(40)
                    
                    # 呼叫 Gemini API 進行 OCR 辨識
                    status_text.text("🔄 正在發送請求到 Gemini API...")
                    progress_bar.progress(60)
                    
                    prompt = """你是一位精通台灣稅務格式的會計助手。請分析這張圖片，並以 JSON 格式回傳以下資訊：
{
  "date": "YYYY/MM/DD",
  "invoice_number": "發票號碼",
  "seller_ubn": "賣方統編",
  "buyer_ubn": "買方統編 (若無則回傳null)",
  "total_amount": "總金額",
  "tax_amount": "稅額 (若無則回傳0)",
  "type": "二聯式/三聯式/電子發票/收據",
  "category": "餐飲/文具/交通/其他"
}
請注意，台灣發票常有民國年份（如113年），請自動轉換為西元年。如果圖片不是發票，請回傳完整的文字內容。"""
                    
                    # 優化圖片大小（如果太大可能會導致超時）
                    max_size = (2048, 2048)
                    if image_pil.size[0] > max_size[0] or image_pil.size[1] > max_size[1]:
                        status_text.text("🔄 圖片較大，正在壓縮...")
                        image_pil.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # 使用 REST API 直接調用（更好的超時控制）
                    start_time = time.time()
                    status_text.text("🔄 正在準備圖片數據...")
                    
                    # 將圖片轉換為 base64
                    img_byte_arr = io.BytesIO()
                    image_pil.save(img_byte_arr, format='PNG')
                    img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                    
                    status_text.text("🔄 正在發送請求到 Gemini API（最多等待 30 秒）...")
                    progress_bar.progress(65)
                    
                    # 使用 REST API 調用（使用正確的 API 端點和模型名稱）
                    # 根據測試，正確的模型名稱是 gemini-2.5-flash（不是 gemini-1.5-flash）
                    api_urls = [
                        f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}",
                        f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent?key={api_key}",
                        f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}",
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                    ]
                    api_url = api_urls[0]  # 優先使用 gemini-2.5-flash
                    
                    # 臨時禁用代理環境變數（避免代理連接問題）
                    original_proxies = {}
                    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
                    for var in proxy_vars:
                        if var in os.environ:
                            original_proxies[var] = os.environ[var]
                            del os.environ[var]
                    
                    payload = {
                        "contents": [{
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": "image/png",
                                        "data": img_base64
                                    }
                                }
                            ]
                        }],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 4096  # 增加 token 限制以支持 JSON 格式
                        }
                    }
                    
                    response = None
                    result_text = ""
                    
                    try:
                        # 使用 requests 調用，設置 30 秒超時
                        # 創建一個新的 Session，完全禁用代理
                        status_text.text("🔄 方法 1: 使用 REST API 調用（無代理）...")
                        
                        session = requests.Session()
                        session.proxies = {
                            "http": None,
                            "https": None
                        }
                        # 確保不使用環境變數中的代理
                        session.trust_env = False
                        
                        # 嘗試多個 API 端點
                        http_response = None
                        last_error = None
                        for i, url in enumerate(api_urls):
                            try:
                                status_text.text(f"🔄 嘗試 API 端點 {i+1}/{len(api_urls)}...")
                                http_response = session.post(
                                    url,
                                    json=payload,
                                    timeout=30,  # 30 秒超時
                                    headers={"Content-Type": "application/json"},
                                    verify=True  # 驗證 SSL 證書
                                )
                                if http_response.status_code == 200:
                                    break  # 成功，跳出循環
                                elif http_response.status_code == 404 and i < len(api_urls) - 1:
                                    continue  # 404 錯誤，嘗試下一個 URL
                                else:
                                    last_error = f"狀態碼 {http_response.status_code}: {http_response.text[:100]}"
                            except Exception as url_err:
                                if i < len(api_urls) - 1:
                                    last_error = str(url_err)
                                    continue  # 嘗試下一個 URL
                                else:
                                    raise url_err
                        
                        # 恢復代理環境變數
                        for var, value in original_proxies.items():
                            os.environ[var] = value
                        
                        if http_response is None:
                            raise Exception(f"所有 API 端點都失敗，最後錯誤: {last_error}")
                        
                        if http_response.status_code == 200:
                            result = http_response.json()
                            if 'candidates' in result and len(result['candidates']) > 0:
                                candidate = result['candidates'][0]
                                if 'content' in candidate and 'parts' in candidate['content']:
                                    parts = candidate['content']['parts']
                                    if len(parts) > 0:
                                        # 查找包含 text 的 part
                                        for part in parts:
                                            if isinstance(part, dict) and 'text' in part:
                                                result_text = part['text'].strip()
                                                status_text.text("✅ API 回應成功")
                                                break
                                        if not result_text:
                                            raise Exception("API 回應中沒有文字內容")
                                    else:
                                        raise Exception("API 回應中 parts 為空")
                                else:
                                    # 調試：顯示實際的響應結構
                                    debug_info = json.dumps(candidate, indent=2, ensure_ascii=False)[:300]
                                    raise Exception(f"API 回應格式不正確。實際結構: {debug_info}")
                            else:
                                raise Exception("API 未返回候選結果")
                        else:
                            error_detail = http_response.text[:200] if http_response.text else "無詳細錯誤信息"
                            raise Exception(f"API 返回錯誤狀態碼 {http_response.status_code}: {error_detail}")
                            
                    except requests.exceptions.Timeout as timeout_err:
                        # 恢復代理環境變數
                        for var, value in original_proxies.items():
                            os.environ[var] = value
                        elapsed_time = time.time() - start_time
                        raise Exception(f"API 調用超時（超過 30 秒，實際耗時 {elapsed_time:.1f} 秒）。請檢查網路連線或稍後再試。")
                    except requests.exceptions.RequestException as e:
                        # 恢復代理環境變數
                        for var, value in original_proxies.items():
                            os.environ[var] = value
                        elapsed_time = time.time() - start_time
                        raise Exception(f"網路請求失敗（耗時 {elapsed_time:.1f} 秒）: {str(e)}")
                    except Exception as e:
                        # 恢復代理環境變數
                        for var, value in original_proxies.items():
                            os.environ[var] = value
                        # 如果 REST API 失敗，嘗試使用 SDK
                        elapsed_time = time.time() - start_time
                        status_text.text(f"⚠️ REST API 失敗，嘗試使用 SDK（已耗時 {elapsed_time:.1f} 秒）...")
                        
                        try:
                            # 方法2: 使用 SDK，但設置較短的超時
                            status_text.text(f"🔄 SDK 方法: 正在調用 Gemini API（最多等待 20 秒）...")
                            progress_bar.progress(70)
                            
                            def call_sdk():
                                """在線程中調用 SDK"""
                                try:
                                    # 嘗試多種調用方式
                                    try:
                                        # 方式1: 最簡單的方式
                                        return model.generate_content([prompt, image_pil])
                                    except:
                                        # 方式2: 使用配置
                                        return model.generate_content(
                                            [prompt, image_pil],
                                            generation_config={
                                                'temperature': 0.1,
                                                'max_output_tokens': 2048,
                                            }
                                        )
                                except Exception as sdk_err:
                                    raise sdk_err
                            
                            with ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(call_sdk)
                                try:
                                    response = future.result(timeout=20)  # 20 秒超時
                                    if response and hasattr(response, 'text') and response.text:
                                        result_text = response.text.strip()
                                        status_text.text("✅ SDK 調用成功")
                                    else:
                                        raise Exception("SDK 返回空回應")
                                except FutureTimeoutError:
                                    raise Exception("SDK 調用超時（超過 20 秒），請檢查網路連線")
                        except Exception as sdk_error:
                            total_time = time.time() - start_time
                            raise Exception(f"""
所有方法都失敗（總耗時 {total_time:.1f} 秒）

REST API 錯誤: {str(e)[:150]}
SDK 錯誤: {str(sdk_error)[:150]}

可能的原因：
1. API Key 無效或已過期
2. 網路連線問題或防火牆阻擋
3. API 配額已用完
4. Gemini API 服務暫時不可用

建議：
- 檢查 API Key 是否正確（在 Google AI Studio 驗證）
- 檢查網路連線和防火牆設置
- 嘗試使用更小的圖片（小於 1MB）
- 稍後再試或聯繫 Google 支援
                            """.strip())
                    
                    # 如果 REST API 成功，result_text 已經被設置，直接顯示結果
                    # 如果使用 SDK，result_text 也會在 SDK 部分被設置
                    
                    elapsed_time = time.time() - start_time
                    progress_bar.progress(100)
                    status_text.empty()
                    progress_bar.empty()
                    
                    # 確保 result_text 有值
                    if not result_text:
                        # 如果 result_text 為空，可能是 SDK 路徑的問題
                        # 檢查是否有 response 對象（SDK 返回的）
                        if 'response' in locals() and response:
                            if hasattr(response, 'text') and response.text:
                                result_text = response.text.strip()
                            elif hasattr(response, 'candidates') and response.candidates:
                                if len(response.candidates) > 0:
                                    candidate = response.candidates[0]
                                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                        if len(candidate.content.parts) > 0:
                                            result_text = candidate.content.parts[0].text.strip()
                    
                    if result_text:
                        st.success("✅ 辨識完成！")
                        st.markdown("### 📝 辨識結果：")
                        
                        # 嘗試解析 JSON（如果是發票格式）
                        try:
                            # 嘗試從結果中提取 JSON（可能包含其他文字）
                            # 使用更智能的 JSON 提取方法
                            json_match = None
                            # 先嘗試找到第一個 { 和最後一個 }
                            start_idx = result_text.find('{')
                            if start_idx != -1:
                                # 從後往前找匹配的 }
                                brace_count = 0
                                for i in range(start_idx, len(result_text)):
                                    if result_text[i] == '{':
                                        brace_count += 1
                                    elif result_text[i] == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            json_str = result_text[start_idx:i+1]
                                            json_match = json_str
                                            break
                            if json_match:
                                json_str = json_match
                                invoice_data = json.loads(json_str)
                                
                                # 顯示結構化的發票資訊
                                st.markdown("#### 🧾 發票資訊（結構化）")
                                col_info1, col_info2 = st.columns(2)
                                
                                with col_info1:
                                    st.metric("📅 日期", invoice_data.get("date", "N/A"))
                                    st.metric("🧾 發票號碼", invoice_data.get("invoice_number", "N/A"))
                                    st.metric("🏢 賣方統編", invoice_data.get("seller_ubn", "N/A"))
                                    st.metric("🏢 買方統編", invoice_data.get("buyer_ubn", "N/A") or "無")
                                
                                with col_info2:
                                    st.metric("💰 總金額", f"${invoice_data.get('total_amount', 'N/A')}")
                                    st.metric("💵 稅額", f"${invoice_data.get('tax_amount', '0')}")
                                    st.metric("📋 類型", invoice_data.get("type", "N/A"))
                                    st.metric("📂 類別", invoice_data.get("category", "N/A"))
                                
                                st.markdown("---")
                                st.markdown("#### 📄 JSON 格式資料")
                                st.json(invoice_data)
                                
                                # 導出功能
                                st.markdown("---")
                                st.markdown("#### 💾 匯出資料")
                                
                                # 準備 DataFrame
                                export_data = {
                                    "日期": [invoice_data.get("date", "N/A")],
                                    "發票號碼": [invoice_data.get("invoice_number", "N/A")],
                                    "賣方統編": [invoice_data.get("seller_ubn", "N/A")],
                                    "買方統編": [invoice_data.get("buyer_ubn", "N/A") or "無"],
                                    "總金額": [invoice_data.get("total_amount", "N/A")],
                                    "稅額": [invoice_data.get("tax_amount", "0")],
                                    "類型": [invoice_data.get("type", "N/A")],
                                    "類別": [invoice_data.get("category", "N/A")],
                                    "辨識時間": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                                }
                                df = pd.DataFrame(export_data)
                                
                                # 導出功能
                                st.markdown("---")
                                st.markdown("#### 💾 匯出資料")
                                
                                # 準備 DataFrame
                                export_data = {
                                    "日期": [invoice_data.get("date", "N/A")],
                                    "發票號碼": [invoice_data.get("invoice_number", "N/A")],
                                    "賣方統編": [invoice_data.get("seller_ubn", "N/A")],
                                    "買方統編": [invoice_data.get("buyer_ubn", "N/A") or "無"],
                                    "總金額": [invoice_data.get("total_amount", "N/A")],
                                    "稅額": [invoice_data.get("tax_amount", "0")],
                                    "類型": [invoice_data.get("type", "N/A")],
                                    "類別": [invoice_data.get("category", "N/A")],
                                    "辨識時間": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                                }
                                df = pd.DataFrame(export_data)
                                
                                # 顯示預覽表格
                                st.markdown("#### 📋 資料預覽")
                                st.dataframe(df, use_container_width=True)
                                
                                # 匯出按鈕
                                col_export1, col_export2 = st.columns(2)
                                
                                with col_export1:
                                    # 匯出為 CSV（總是可用）
                                    csv_buffer = io.StringIO()
                                    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')  # 使用 utf-8-sig 以支援 Excel 正確顯示中文
                                    csv_data = csv_buffer.getvalue()
                                    
                                    st.download_button(
                                        label="📄 下載 CSV (.csv)",
                                        data=csv_data.encode('utf-8-sig'),
                                        file_name=f"發票_{invoice_data.get('invoice_number', '資料')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv",
                                        use_container_width=True
                                    )
                                
                                with col_export2:
                                    # 匯出為 Excel（如果 openpyxl 可用）
                                    try:
                                        excel_buffer = io.BytesIO()
                                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                            df.to_excel(writer, index=False, sheet_name='發票資料')
                                        excel_buffer.seek(0)
                                        
                                        st.download_button(
                                            label="📊 下載 Excel (.xlsx)",
                                            data=excel_buffer,
                                            file_name=f"發票_{invoice_data.get('invoice_number', '資料')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            use_container_width=True
                                        )
                                    except Exception as e:
                                        st.info("💡 Excel 匯出功能需要安裝 openpyxl：`pip install openpyxl`")
                                        st.code("pip install openpyxl", language="bash")
                                
                                # 也顯示原始文字
                                st.markdown("---")
                                st.markdown("#### 📝 原始辨識文字")
                                st.text_area(
                                    "完整文字內容",
                                    value=result_text,
                                    height=200,
                                    label_visibility="collapsed"
                                )
                            else:
                                # 不是 JSON 格式，顯示原始文字
                                st.text_area(
                                    "文字內容",
                                    value=result_text,
                                    height=300,
                                    label_visibility="collapsed"
                                )
                                st.code(result_text, language=None)
                        except json.JSONDecodeError:
                            # JSON 解析失敗，顯示原始文字
                            st.text_area(
                                "文字內容",
                                value=result_text,
                                height=300,
                                label_visibility="collapsed"
                            )
                            st.code(result_text, language=None)
                    else:
                        st.warning("⚠️ 未偵測到文字內容或 API 未返回有效結果")
                            
                except Exception as e:
                    st.error(f"❌ OCR 辨識失敗：{str(e)}")
                    st.markdown("### 🔍 詳細錯誤信息：")
                    st.exception(e)
                    st.info("💡 **提示**：請檢查：\n1. API Key 是否正確\n2. 網路連線是否正常\n3. 圖片格式是否支援")
    else:
        st.info("👆 請先上傳圖片")

# 頁腳
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "使用 Google Gemini API 進行 OCR 辨識 | "
    "Streamlit 應用程式"
    "</div>",
    unsafe_allow_html=True
)
