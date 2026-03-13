import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def test_bot():
    print(f"Testing bot with token: {BOT_TOKEN[:10]}...")
    bot = Bot(token=BOT_TOKEN)
    try:
        me = await bot.get_me()
        print(f"✅ Bot is alive!")
        print(f"Name: {me.full_name}")
        print(f"Username: @{me.username}")
        print(f"ID: {me.id}")
    except Exception as e:
        print(f"❌ Bot error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_bot())
