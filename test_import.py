import sys
print("Python path:", sys.path)

try:
    from config import BOT_TOKEN, GROQ_API_KEY
    print("✅ Import muvaffaqiyat!")
    print("BOT_TOKEN:", BOT_TOKEN is not None)
    print("GROQ_API_KEY:", GROQ_API_KEY is not None)
except ImportError as e:
    print(f"❌ Import xatoligi: {e}")
    import config
    print("Config o'zgaruvchilari:", dir(config))
