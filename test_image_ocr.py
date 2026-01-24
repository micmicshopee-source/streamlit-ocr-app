"""
测试图片 OCR 功能
"""
import requests
import json
import base64
from PIL import Image
import io

API_KEY = "AIzaSyBe4HixC1ImmO5NtJnhjrCKl62J0_ntUGQ"

# 创建一个包含文字的测试图片
img = Image.new('RGB', (400, 200), color='white')
from PIL import ImageDraw, ImageFont

draw = ImageDraw.Draw(img)
# 尝试使用默认字体
try:
    font = ImageFont.truetype("arial.ttf", 40)
except:
    font = ImageFont.load_default()

draw.text((50, 80), "Hello World", fill='black', font=font)

# 转换为 base64
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

print("测试图片 OCR...")
print("=" * 60)

url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"

prompt = """請仔細分析這張圖片，並提取其中的所有文字內容。
請以繁體中文回覆，並按照圖片中文字的出現順序列出。
如果圖片中沒有文字，請回覆「未偵測到文字內容」。"""

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
        "maxOutputTokens": 2048
    }
}

session = requests.Session()
session.proxies = {"http": None, "https": None}
session.trust_env = False

try:
    response = session.post(
        url,
        json=payload,
        timeout=30,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n完整响应结构:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 60)
        print("解析响应:")
        
        # 检查不同的响应结构
        if 'candidates' in result:
            print(f"找到 {len(result['candidates'])} 个候选结果")
            
            for i, candidate in enumerate(result['candidates']):
                print(f"\n候选 {i+1}:")
                print(f"  完整结构: {json.dumps(candidate, indent=2, ensure_ascii=False)[:500]}")
                
                if 'content' in candidate:
                    content = candidate['content']
                    print(f"  有 content 字段")
                    
                    if 'parts' in content:
                        parts = content['parts']
                        print(f"  找到 {len(parts)} 个 parts")
                        
                        for j, part in enumerate(parts):
                            print(f"  Part {j}: {type(part)}")
                            if isinstance(part, dict):
                                if 'text' in part:
                                    text = part['text']
                                    print(f"    [找到文字] {text}")
                                else:
                                    print(f"    Part 键: {list(part.keys())}")
                    else:
                        print(f"  content 中没有 parts 字段")
                        print(f"  content 键: {list(content.keys())}")
                else:
                    print(f"  候选结果中没有 content 字段")
                    print(f"  候选结果键: {list(candidate.keys())}")
        else:
            print("响应中没有 candidates 字段")
            print(f"响应键: {list(result.keys())}")
    else:
        print(f"错误: {response.text}")
        
except Exception as e:
    print(f"请求失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
