import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import os
import io
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

# 1. 初始化設定 - 嘗試載入環境變數（可選）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果沒有安裝 python-dotenv，跳過

# 預設 API Key（如果環境變數中沒有）
DEFAULT_API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

# 嘗試載入環境變數
try:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or DEFAULT_API_KEY
except:
    api_key = DEFAULT_API_KEY

st.set_page_config(
    page_title="發票報帳小秘笈",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📑 發票/收據報帳小秘笈")
st.markdown("**上傳您的台灣發票或收據，AI 自動幫您整理成帳表！**")
st.markdown("---")

# 2. 側邊欄設定
with st.sidebar:
    st.header("⚙️ 設定")
    
    # API Key 設定
    api_key_input = st.text_input(
        "Gemini API Key",
        value=api_key,
        type="password",
        help="請輸入您的 Google Gemini API Key"
    )
    
    if api_key_input:
        try:
            genai.configure(api_key=api_key_input)
            api_key = api_key_input
            st.success("✅ API Key 已設定")
        except Exception as e:
            st.error(f"API Key 設定失敗: {str(e)}")
    else:
        try:
            genai.configure(api_key=api_key)
        except:
            pass
    
    st.markdown("---")
    
    # 模型選擇
    model_choice = st.selectbox(
        "選擇模型",
        ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        help="Flash 速度快，Pro 辨識更精準（尤其是手寫發票）"
    )
    
    st.info("💡 提示：Flash 速度快，Pro 辨識更精準（尤其是手寫發票）。")
    
    st.markdown("---")
    st.markdown("### 📖 使用說明")
    st.markdown("""
    1. 上傳發票或收據照片
    2. 選擇 AI 模型
    3. 點擊「開始辨識」
    4. 下載報帳 CSV 檔案
    """)

# 3. 上傳功能
uploaded_file = st.file_uploader(
    "選擇發票照片...",
    type=["jpg", "jpeg", "png", "gif", "bmp", "webp"],
    help="支援 JPG, JPEG, PNG, GIF, BMP, WEBP 格式"
)

if uploaded_file is not None:
    # 讀取並保存圖片
    if 'image_bytes' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
        uploaded_file.seek(0)
        st.session_state.image_bytes = uploaded_file.read()
        st.session_state.uploaded_file_name = uploaded_file.name
    
    image = Image.open(io.BytesIO(st.session_state.image_bytes))
    
    # 優化圖片顯示
    max_display_size = 800
    display_image = image.copy()
    if image.size[0] > max_display_size or image.size[1] > max_display_size:
        ratio = min(max_display_size / image.size[0], max_display_size / image.size[1])
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        display_image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(display_image, caption="已上傳的發票", use_container_width=True)
        st.info(f"📊 圖片資訊：{image.size[0]} x {image.size[1]} 像素")

    with col2:
        st.header("🔍 辨識結果")
        
        if st.button("🚀 開始辨識", type="primary", use_container_width=True):
            if not api_key:
                st.error("❌ 請先在側邊欄輸入 Gemini API Key")
            else:
                # 顯示進度
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # 配置 API
                    status_text.text("🔄 正在配置 API...")
                    progress_bar.progress(10)
                    genai.configure(api_key=api_key)
                    
                    # 定義專門針對台灣發票的 Prompt
                    prompt = """
                    你是一個精通台灣稅務的會計助手。請分析這張圖片，並以純 JSON 格式回傳資訊。
                    請注意：
                    1. 將民國年(如113年)轉換為西元年(如2024)。
                    2. 移除數字中的逗號。
                    3. 辨識欄位包含：發票號碼、日期、賣方統編、買方統編、銷售額、稅額、總計、發票類型(二聯/三聯/電子/收據)。
                    
                    回傳格式範例：
                    {
                      "發票號碼": "ZP12345678",
                      "日期": "2024/06/06",
                      "買方統編": "88888888",
                      "賣方名稱": "XXX公司",
                      "賣方統編": "12345678",
                      "銷售額": 1000,
                      "稅額": 50,
                      "總計": 1050,
                      "類型": "三聯式"
                    }
                    """
                    
                    # 確保圖片是 RGB 模式
                    status_text.text("🔄 正在處理圖片...")
                    progress_bar.progress(20)
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # 優化圖片大小（如果太大）
                    max_size = (2048, 2048)
                    if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                        image.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # 初始化模型
                    status_text.text(f"🔄 正在初始化模型 ({model_choice})...")
                    progress_bar.progress(30)
                    model = genai.GenerativeModel(model_choice)
                    
                    # 調用 API - 使用更可靠的方式
                    status_text.text("🔄 AI 正在努力閱讀中...（這可能需要 10-30 秒）")
                    progress_bar.progress(50)
                    
                    start_time = time.time()
                    response = None
                    
                    # 方法1: 直接調用（最快）
                    try:
                        status_text.text("🔄 方法1: 直接調用 API...")
                        response = model.generate_content([prompt, image])
                        elapsed_time = time.time() - start_time
                        status_text.text(f"✅ API 回應成功（耗時 {elapsed_time:.1f} 秒）")
                        progress_bar.progress(80)
                    except Exception as direct_error:
                        # 方法2: 使用線程執行，添加超時
                        status_text.text("🔄 方法2: 使用線程調用 API（最多等待 45 秒）...")
                        progress_bar.progress(55)
                        
                        def call_api():
                            return model.generate_content([prompt, image])
                        
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(call_api)
                            try:
                                response = future.result(timeout=45)  # 45 秒超時
                                elapsed_time = time.time() - start_time
                                status_text.text(f"✅ API 回應成功（耗時 {elapsed_time:.1f} 秒）")
                                progress_bar.progress(80)
                            except FutureTimeoutError:
                                elapsed_time = time.time() - start_time
                                raise Exception(f"API 調用超時（超過 45 秒，實際耗時 {elapsed_time:.1f} 秒）。請檢查網路連線或稍後再試。")
                            except Exception as thread_error:
                                raise Exception(f"API 調用失敗: {str(thread_error)}")
                    
                    if response is None:
                        raise Exception("API 未返回任何回應")
                        
                    # 清理 AI 回傳的字串並轉為 JSON
                    status_text.text("🔄 正在處理辨識結果...")
                    progress_bar.progress(90)
                    
                    result_text = response.text.strip()
                    
                    # 嘗試提取 JSON
                    json_str = None
                    start_idx = result_text.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        for i in range(start_idx, len(result_text)):
                            if result_text[i] == '{':
                                brace_count += 1
                            elif result_text[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_str = result_text[start_idx:i+1]
                                    break
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    progress_bar.empty()
                    
                    if json_str:
                        # 清理 JSON 字串
                        clean_json = json_str.replace('```json', '').replace('```', '').strip()
                        data = json.loads(clean_json)
                        
                        # 顯示結果
                        st.success("✅ 辨識完成！")
                        
                        # 顯示結構化資訊
                        col_info1, col_info2 = st.columns(2)
                        
                        with col_info1:
                            st.metric("📅 日期", data.get("日期", "N/A"))
                            st.metric("🧾 發票號碼", data.get("發票號碼", "N/A"))
                            st.metric("🏢 賣方統編", data.get("賣方統編", "N/A"))
                            st.metric("🏢 買方統編", data.get("買方統編", "N/A") or "無")
                        
                        with col_info2:
                            st.metric("💰 銷售額", f"${data.get('銷售額', 0):,}")
                            st.metric("💵 稅額", f"${data.get('稅額', 0):,}")
                            st.metric("💳 總計", f"${data.get('總計', 0):,}")
                            st.metric("📋 類型", data.get("類型", "N/A"))
                        
                        # 表格顯示
                        st.markdown("---")
                        st.markdown("#### 📋 完整資料")
                        df = pd.DataFrame([data])
                        st.dataframe(df, use_container_width=True)
                        
                        # 報帳驗證邏輯
                        sales = data.get("銷售額", 0)
                        tax = data.get("稅額", 0)
                        total = data.get("總計", 0)
                        
                        if isinstance(sales, str):
                            sales = float(sales.replace(',', '')) if sales.replace(',', '').replace('.', '').isdigit() else 0
                        if isinstance(tax, str):
                            tax = float(tax.replace(',', '')) if tax.replace(',', '').replace('.', '').isdigit() else 0
                        if isinstance(total, str):
                            total = float(total.replace(',', '')) if total.replace(',', '').replace('.', '').isdigit() else 0
                        
                        if abs((sales + tax) - total) > 0.01:  # 允許小數誤差
                            st.warning(f"⚠️ 注意：銷售額 (${sales:,.0f}) + 稅額 (${tax:,.0f}) = ${sales+tax:,.0f}，但總計為 ${total:,.0f}，請檢查圖片內容。")
                        else:
                            st.success("✅ 金額驗證通過：銷售額 + 稅額 = 總計")
                        
                        # 下載按鈕
                        st.markdown("---")
                        col_dl1, col_dl2 = st.columns(2)
                        
                        with col_dl1:
                            # CSV 下載
                            csv = df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                "📥 下載報帳 CSV",
                                data=csv.encode('utf-8-sig'),
                                file_name=f"發票_{data.get('發票號碼', '資料')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        with col_dl2:
                            # Excel 下載（如果可用）
                            try:
                                excel_buffer = io.BytesIO()
                                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                    df.to_excel(writer, index=False, sheet_name='發票資料')
                                excel_buffer.seek(0)
                                
                                st.download_button(
                                    "📊 下載 Excel",
                                    data=excel_buffer,
                                    file_name=f"發票_{data.get('發票號碼', '資料')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            except:
                                st.info("💡 Excel 功能需要安裝 openpyxl")
                        
                        # 顯示原始 JSON
                        with st.expander("📄 查看原始 JSON 資料", expanded=False):
                            st.json(data)
                            
                    else:
                        st.error("無法解析 JSON 格式，顯示原始回應：")
                        st.text(result_text)
                            
                except json.JSONDecodeError as e:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"JSON 解析錯誤：{e}")
                    st.text("原始回應：")
                    st.text(result_text if 'result_text' in locals() else "無回應")
                except Exception as e:
                    progress_bar.empty()
                    status_text.empty()
                    st.error(f"錯誤：{e}")
                    import traceback
                    st.code(traceback.format_exc())
                    st.info("💡 **提示**：如果持續出現錯誤，請檢查：\n1. API Key 是否正確\n2. 網路連線是否正常\n3. 圖片格式是否支援")
else:
    st.info("👆 請上傳發票或收據照片開始辨識")
