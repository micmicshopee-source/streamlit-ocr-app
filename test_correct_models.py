"""
测试正确的模型名称
"""
import requests
import json

API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

session = requests.Session()
session.proxies = {"http": None, "https": None}
session.trust_env = False

# 根据测试结果，可用的模型是：
# models/gemini-2.5-flash
# models/gemini-2.5-pro
# models/gemini-2.0-flash
# 等等

# 测试不同的模型名称格式
test_models = [
    "models/gemini-2.5-flash",
    "gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "gemini-2.5-pro",
    "models/gemini-2.0-flash",
    "gemini-2.0-flash",
]

payload = {
    "contents": [{
        "parts": [{"text": "Say hello in one sentence"}]
    }]
}

print("测试正确的模型名称格式...")
print("=" * 60)

for model_name in test_models:
    for version in ['v1', 'v1beta']:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{model_name}:generateContent?key={API_KEY}"
        
        try:
            response = session.post(
                url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result['candidates'][0]['content']['parts'][0]['text']
                print(f"\n[SUCCESS] 找到可用的模型！")
                print(f"  模型名称: {model_name}")
                print(f"  API 版本: {version}")
                print(f"  响应: {text}")
                print(f"  完整 URL: {url}")
                print("\n" + "=" * 60)
                exit(0)
            elif response.status_code != 404:
                print(f"{version}/{model_name}: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            pass

print("\n[ERROR] 未找到可用的模型端点")
