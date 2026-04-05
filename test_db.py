"""
Supabase jadvallarini tekshirish uchun test skript.
Ishlatish: python test_db.py
"""
import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def check():
    print("=" * 50)
    print("SUPABASE JADVAL TEKSHIRUVI")
    print("=" * 50)

    # 1. users jadvali
    try:
        r = await asyncio.to_thread(supabase.table("users").select("*").limit(5).execute)
        print(f"\n✅ 'users' jadvali mavjud")
        print(f"   Namuna ma'lumotlar: {r.data}")
        r2 = await asyncio.to_thread(supabase.table("users").select("count", count="exact").execute)
        print(f"   Jami foydalanuvchilar (count): {r2.count}")
    except Exception as e:
        print(f"\n❌ 'users' jadvali xatosi: {e}")

    # 2. statistics jadvali
    try:
        r = await asyncio.to_thread(supabase.table("statistics").select("*").limit(5).execute)
        print(f"\n✅ 'statistics' jadvali mavjud")
        print(f"   Namuna ma'lumotlar: {r.data}")
    except Exception as e:
        print(f"\n❌ 'statistics' jadvali xatosi: {e}")

    # 3. payments jadvali
    try:
        r = await asyncio.to_thread(supabase.table("payments").select("*").limit(5).execute)
        print(f"\n✅ 'payments' jadvali mavjud")
        print(f"   Namuna ma'lumotlar: {r.data}")
    except Exception as e:
        print(f"\n❌ 'payments' jadvali xatosi: {e}")

    print("\n" + "=" * 50)

asyncio.run(check())
