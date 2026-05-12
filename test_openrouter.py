"""OpenRouter API va DeepSeek R1-0528 modelini test qilish"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI

async def test_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY topilmadi .env faylda!")
        return
    
    print(f"✅ API kalit topildi: {api_key[:20]}...")
    
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    model = "deepseek/deepseek-r1-0528"
    print(f"\n🧪 Model: {model}")
    print("📡 So'rov yuborilmoqda...\n")
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Siz akademik yozuvchi siz. O'zbek tilida javob bering."},
                {"role": "user", "content": "Sun'iy intellekt nima? 2-3 gapda qisqacha tushuntiring."}
            ],
            temperature=0.3,
            max_tokens=500,
            extra_headers={
                "HTTP-Referer": "https://t.me/acadai_bot",
                "X-Title": "AcadAI Telegram Bot"
            }
        )
        
        content = response.choices[0].message.content
        
        # <think> taglarini tozalash
        if content and "<think>" in content:
            import re
            raw_thinking = re.findall(r'<think>(.*?)</think>', content, flags=re.DOTALL)
            if raw_thinking:
                print(f"🧠 Thinking (qisqartrilgan): {raw_thinking[0][:200]}...")
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        print(f"✅ JAVOB KELDI!\n")
        print(f"📝 Model javobi:\n{content}")
        print(f"\n📊 Model: {response.model}")
        print(f"📊 Tokenlar: {response.usage}")
        
    except Exception as e:
        print(f"❌ XATOLIK: {e}")
        print(f"\n🔍 Xatolik turi: {type(e).__name__}")
        
        # Model nomi xato bo'lishi mumkin
        if "not found" in str(e).lower() or "404" in str(e):
            print("\n⚠️ Model nomi noto'g'ri bo'lishi mumkin!")
            print("Mavjud DeepSeek modellarini tekshirish...")
            try:
                models = await client.models.list()
                deepseek_models = [m.id for m in models.data if "deepseek" in m.id.lower()]
                if deepseek_models:
                    print(f"\n📋 Mavjud DeepSeek modellari:")
                    for m in deepseek_models[:10]:
                        print(f"   • {m}")
                else:
                    print("   DeepSeek modellari topilmadi")
            except Exception as e2:
                print(f"   Modellar ro'yxatini olishda xatolik: {e2}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
