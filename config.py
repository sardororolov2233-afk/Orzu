import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv('BOT_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
UNSPLASH_API_KEY = os.getenv('UNSPLASH_API_KEY')
if UNSPLASH_API_KEY:
    UNSPLASH_API_KEY = UNSPLASH_API_KEY.strip()

if not BOT_TOKEN:
    raise ValueError('BOT_TOKEN topilmadi!')
# if not GROQ_API_KEY:
#     raise ValueError('GROQ_API_KEY topilmadi!')

# Admin IDs
ADMIN_IDS = []
raw_admin_ids = os.getenv('ADMIN_ID', '')
if raw_admin_ids:
    for x in raw_admin_ids.split(','):
        x = x.strip()
        if x.isdigit():
            ADMIN_IDS.append(int(x))

# Backwards compatibility for single main ADMIN_ID
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else None

if not ADMIN_IDS:
    print("⚠️ DIQQAT: ADMIN_ID topilmadi! To'lovlarni tasdiqlash ishlamaydi.")

print('Token va API Keylar yuklandi')
