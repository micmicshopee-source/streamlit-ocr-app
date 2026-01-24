"""
簡單的 API 測試 - 不使用代理，直接測試連接
"""
import requests
import json
import base64
from PIL import Image
import io

API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

# 創建一個簡單的測試圖片
img = Image.new('RGB', (100, 100), color='white')
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

print("測試 1: 簡單的文字生成（不需要圖片）")
print("-" * 50)

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

payload = {
    "contents": [{
        "parts": [{"text": "請用一句話回答：你好"}]
    }]
}

try:
    session = requests.Session()
    session.proxies = {"http": None, "https": None}
    session.trust_env = False  # 完全禁用環境變數中的代理
    
    response = session.post(
        url,
        json=payload,
        timeout=10
    )
    print(f"狀態碼: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        if 'candidates' in result:
            text = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ 成功！回應: {text[:50]}")
        else:
            print(f"❌ 回應格式錯誤: {json.dumps(result, indent=2)[:200]}")
    else:
        print(f"❌ 錯誤: {response.text[:200]}")
except Exception as e:
    print(f"❌ 請求失敗: {e}")

print("\n測試 2: 圖片 OCR（使用測試圖片）")
print("-" * 50)

payload2 = {
    "contents": [{
        "parts": [
            {"text": "請描述這張圖片"},
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": img_base64
                }
            }
        ]
    }]
}

try:
    session2 = requests.Session()
    session2.proxies = {"http": None, "https": None}
    session2.trust_env = False  # 完全禁用環境變數中的代理
    
    response2 = session2.post(
        url,
        json=payload2,
        timeout=15
    )
    print(f"狀態碼: {response2.status_code}")
    if response2.status_code == 200:
        result2 = response2.json()
        if 'candidates' in result2:
            text2 = result2['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ 成功！回應: {text2[:100]}")
        else:
            print(f"❌ 回應格式錯誤: {json.dumps(result2, indent=2)[:200]}")
    else:
        print(f"❌ 錯誤: {response2.text[:200]}")
except Exception as e:
    print(f"❌ 請求失敗: {e}")

print("\n測試完成")
