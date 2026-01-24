"""
测试 API Key 是否有效，并检查正确的调用方式
"""
import requests
import json

API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

print("=" * 60)
print("测试 Gemini API Key 和调用方式")
print("=" * 60)
print()

# 创建 session，禁用代理
session = requests.Session()
session.proxies = {"http": None, "https": None}
session.trust_env = False

# 测试 1: 检查 API Key 是否有效（通过列出模型）
print("测试 1: 检查 API Key 是否有效（列出可用模型）...")
print("-" * 60)

list_models_urls = [
    "https://generativelanguage.googleapis.com/v1/models?key=" + API_KEY,
    "https://generativelanguage.googleapis.com/v1beta/models?key=" + API_KEY,
]

for url in list_models_urls:
    print(f"\n尝试: {url[:70]}...")
    try:
        response = session.get(url, timeout=10)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            models = response.json()
            if 'models' in models:
                print(f"  [OK] 成功！找到 {len(models['models'])} 个模型")
                print("\n  可用的模型列表:")
                for model in models['models'][:10]:  # 只显示前10个
                    name = model.get('name', 'N/A')
                    display_name = model.get('displayName', 'N/A')
                    supported = model.get('supportedGenerationMethods', [])
                    print(f"    - {name}")
                    print(f"      显示名: {display_name}")
                    print(f"      支持方法: {', '.join(supported)}")
                break
        elif response.status_code == 401:
            print(f"  [ERROR] 401 未授权 - API Key 无效")
        elif response.status_code == 403:
            print(f"  [ERROR] 403 禁止访问 - API Key 可能没有权限")
        else:
            print(f"  [ERROR] 错误: {response.text[:200]}")
    except Exception as e:
        print(f"  [ERROR] 请求失败: {str(e)[:100]}")

print()
print("-" * 60)

# 测试 2: 尝试调用 generateContent（使用正确的模型名称）
print("\n测试 2: 尝试调用 generateContent...")
print("-" * 60)

# 常见的模型名称
model_names = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
    "gemini-1.0-pro",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro",
]

payload = {
    "contents": [{
        "parts": [{"text": "Say hello in one sentence"}]
    }]
}

for model_name in model_names:
    for version in ['v1', 'v1beta']:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{model_name}:generateContent?key={API_KEY}"
        print(f"\n尝试: {version}/{model_name}")
        
        try:
            response = session.post(
                url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    print(f"  [SUCCESS] 成功！响应: {text}")
                    print(f"\n[找到可用的端点]")
                    print(f"  URL: {url}")
                    print(f"  模型: {model_name}")
                    print(f"  版本: {version}")
                    exit(0)  # 找到可用的，退出
            elif response.status_code == 400:
                error = response.json().get('error', {})
                message = error.get('message', response.text[:100])
                print(f"  [ERROR] 400: {message}")
            elif response.status_code == 404:
                print(f"  [WARNING] 404 - 模型或端点不存在")
            else:
                print(f"  [ERROR] {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print(f"  [ERROR] 请求失败: {str(e)[:100]}")
        
        # 如果找到可用的，就不继续了
        if response.status_code == 200:
            break
    
    # 如果找到可用的，就不继续了
    if response.status_code == 200:
        break

print()
print("-" * 60)
print("\n[结论]")
print("如果所有测试都失败，可能的原因:")
print("1. API Key 无效或已过期")
print("2. API Key 没有启用 Gemini API 服务")
print("3. 需要前往 https://aistudio.google.com/apikey 重新生成 API Key")
print("=" * 60)
