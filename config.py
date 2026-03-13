import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Backend app.db yoʻli (balans sinxronizatsiyasi uchun)
BACKEND_DB_PATH = Path(os.getenv("BACKEND_DB_PATH", r"d:\Новая папка\backend\app.db"))

BOT_TOKEN = os.getenv('BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
UNSPLASH_API_KEY = os.getenv('UNSPLASH_API_KEY')
if UNSPLASH_API_KEY:
    UNSPLASH_API_KEY = UNSPLASH_API_KEY.strip()

if not BOT_TOKEN:
    raise ValueError('BOT_TOKEN topilmadi!')
# if not GROQ_API_KEY:
#     raise ValueError('GROQ_API_KEY topilmadi!')

# Admin ID (Agar .env da bo'lmasa, logga yozadi va ishlamasligi mumkin)
ADMIN_ID = os.getenv('ADMIN_ID')
if not ADMIN_ID:
    print("⚠️ DIQQAT: ADMIN_ID topilmadi! To'lovlarni tasdiqlash ishlamaydi.")

print('Token va API Keylar yuklandi')
