"""
检查 Gemini API 接口是否可用，并验证调用方式
"""
import requests
import json
import os

API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

print("=" * 60)
print("Gemini API 接口检查工具")
print("=" * 60)
print()

# 1. 检查 API Key 格式
print("步骤 1: 检查 API Key 格式...")
if API_KEY and len(API_KEY) > 20:
    print(f"[OK] API Key 格式看起来正确 (长度: {len(API_KEY)})")
else:
    print("[ERROR] API Key 格式可能不正确")
print()

# 2. 检查网络连接
print("步骤 2: 检查网络连接...")
try:
    session = requests.Session()
    session.proxies = {"http": None, "https": None}
    session.trust_env = False
    
    test_response = session.get("https://www.google.com", timeout=5)
    if test_response.status_code == 200:
        print("[OK] 网络连接正常")
    else:
        print(f"[WARNING] Google 连接返回状态码: {test_response.status_code}")
except Exception as e:
    print(f"[ERROR] 网络连接失败: {e}")
print()

# 3. 测试不同的 API 端点
print("步骤 3: 测试不同的 API 端点...")
print("-" * 60)

api_endpoints = [
    {
        "name": "v1 - gemini-1.5-flash",
        "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    },
    {
        "name": "v1beta - gemini-1.5-flash",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    },
    {
        "name": "v1 - gemini-pro",
        "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={API_KEY}"
    },
    {
        "name": "v1beta - gemini-pro",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
    }
]

payload = {
    "contents": [{
        "parts": [{"text": "Hello, say hi in one sentence"}]
    }]
}

session = requests.Session()
session.proxies = {"http": None, "https": None}
session.trust_env = False

working_endpoint = None

for endpoint in api_endpoints:
    print(f"\n测试: {endpoint['name']}")
    print(f"URL: {endpoint['url'][:80]}...")
    
    try:
        response = session.post(
            endpoint['url'],
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                print(f"  [OK] 成功！响应: {text[:50]}")
                working_endpoint = endpoint
                break
            else:
                print(f"  [WARNING] 响应格式异常: {json.dumps(result, indent=2)[:200]}")
        elif response.status_code == 400:
            error_data = response.json() if response.text else {}
            print(f"  [ERROR] 400 错误: {error_data.get('error', {}).get('message', response.text[:100])}")
        elif response.status_code == 401:
            print(f"  [ERROR] 401 未授权 - API Key 可能无效或已过期")
        elif response.status_code == 403:
            print(f"  [ERROR] 403 禁止访问 - API Key 可能没有权限或配额已用完")
        elif response.status_code == 404:
            print(f"  [WARNING] 404 未找到 - 端点可能不存在或模型名称错误")
        else:
            print(f"  [ERROR] 错误: {response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"  [ERROR] 请求超时")
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] 请求失败: {str(e)[:100]}")
    except Exception as e:
        print(f"  [ERROR] 未知错误: {str(e)[:100]}")

print()
print("-" * 60)

if working_endpoint:
    print(f"\n[SUCCESS] 找到可用的 API 端点: {working_endpoint['name']}")
    print(f"建议使用: {working_endpoint['url']}")
else:
    print("\n[ERROR] 所有 API 端点都不可用")
    print("\n可能的原因:")
    print("1. API Key 无效或已过期")
    print("2. API Key 没有启用 Gemini API")
    print("3. API 配额已用完")
    print("4. 网络连接问题")
    print("\n建议:")
    print("1. 前往 https://aistudio.google.com/apikey 检查 API Key")
    print("2. 确保已启用 Gemini API")
    print("3. 检查 API 使用配额")

print()
print("=" * 60)
print("检查完成")
print("=" * 60)
