# 診斷頁面不呼叫 set_page_config（由主 app 設定）
import streamlit as st

st.title("🛡️ Google 登錄診斷工具")

# 1. 檢查 Secrets 是否設定成功
if "google_auth" in st.secrets:
    st.success("✅ Streamlit Secrets 讀取成功！")

    # 從 Secrets 獲取設定
    try:
        client_id = st.secrets["google_auth"]["client_id"]
        redirect_uri = st.secrets["google_auth"]["redirect_uri"]

        st.write(f"**目前設定的 Client ID:** `{client_id[:15]}...` (隱藏部分)")
        st.write(f"**目前設定的 Redirect URI:** `{redirect_uri}`")

        # 2. 生成測試連結
        test_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile"
        )

        st.markdown(f"### [👉 點擊這裡測試 Google 授權連結]({test_url})")

        st.warning("""
        **點開後請觀察：**
        1. 如果顯示 **400: redirect_uri_mismatch**：代表你在 Google 後台填的網址，跟上面顯示的 `Redirect URI` **完全不一樣**。
        2. 如果顯示 **403: access_denied**：代表你沒有在 Google 後台的「測試使用者」加入你的 Gmail。
        3. 如果進入了選擇帳號頁面：恭喜你，設定正確！
        """)

    except KeyError as e:
        st.error(f"❌ Secrets 格式不對，缺少欄位: {e}")
else:
    st.error("❌ 找不到 `[google_auth]` Secrets 設定。請前往 Streamlit Cloud 後台設定。")

st.divider()
