"""
測試 Gemini API 是否正常工作
"""
import sys
import os

# 設置 UTF-8 編碼
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')

try:
    import google.generativeai as genai
except ImportError:
    print("錯誤: 無法導入 google.generativeai")
    print("請運行: pip install google-generativeai")
    sys.exit(1)

# API Key
API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

print("=" * 50)
print("Gemini API 測試工具")
print("=" * 50)
print()

# 1. 測試 API Key 配置
print("步驟 1: 配置 API Key...")
try:
    genai.configure(api_key=API_KEY)
    print("[OK] API Key 配置成功")
except Exception as e:
    print(f"[ERROR] API Key 配置失敗: {e}")
    sys.exit(1)

print()

# 2. 測試列出可用模型
print("步驟 2: 檢查可用模型...")
try:
    models = genai.list_models()
    vision_models = []
    for model in models:
        if 'vision' in model.name.lower() or 'gemini' in model.name.lower():
            if 'generateContent' in model.supported_generation_methods:
                vision_models.append(model.name)
    
    print(f"[OK] 找到 {len(vision_models)} 個支援視覺的模型:")
    for model_name in vision_models[:5]:  # 只顯示前5個
        print(f"   - {model_name}")
    
    if not vision_models:
        print("[WARNING] 未找到支援視覺的模型")
except Exception as e:
    print(f"[ERROR] 無法列出模型: {e}")
    print("   這可能是因為 API Key 無效或網路問題")

print()

# 3. 測試簡單的文字生成（不需要圖片）
print("步驟 3: 測試簡單的文字生成...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("請用一句話回答：你好")
    if response and response.text:
        print(f"[OK] 文字生成測試成功")
        print(f"   回應: {response.text[:50]}...")
    else:
        print("[WARNING] API 返回了空回應")
except Exception as e:
    print(f"[ERROR] 文字生成測試失敗: {e}")
    print(f"   錯誤類型: {type(e).__name__}")

print()

# 4. 測試模型初始化（不同模型）
print("步驟 4: 測試不同模型的初始化...")
models_to_test = [
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-pro-vision',
    'gemini-1.0-pro-vision'
]

for model_name in models_to_test:
    try:
        model = genai.GenerativeModel(model_name)
        print(f"[OK] {model_name}: 初始化成功")
    except Exception as e:
        print(f"[ERROR] {model_name}: 初始化失敗 - {str(e)[:50]}")

print()

# 5. 檢查 API 配額和限制
print("步驟 5: 檢查 API 狀態...")
try:
    # 嘗試獲取模型信息
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("[OK] API 連接正常")
    print("[TIP] 提示: 如果圖片 OCR 仍然失敗，可能是:")
    print("   - 圖片格式或大小問題")
    print("   - 網路連線不穩定")
    print("   - API 配額已用完")
except Exception as e:
    print(f"[ERROR] API 連接失敗: {e}")

print()
print("=" * 50)
print("測試完成")
print("=" * 50)
