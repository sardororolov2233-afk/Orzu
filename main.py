import asyncio
import sys
import logging
import os
from pathlib import Path
from aiohttp import web

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from config import BOT_TOKEN, ADMIN_ID
from keyboards import main_menu

# Import routers
from handlers import referat, presentation, course, ready_works, payment, admin

# Logging konfiguratsiyasi
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set aiogram logger to DEBUG to see polling details
logging.getLogger("aiogram").setLevel(logging.DEBUG)

from database import init_db

async def start_handler_local(message: Message):
    logger.info(f"🔵 /start buyrugu. Foydalanuvchi: {message.from_user.id}")
    try:
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "📚 Referat, taqdimot, kurs va diplom ishlarini "
            "sun'iy intellekt yordamida tayyorlab beramiz.\n\n"
            "Quyidagilardan birini tanlang 👇",
            reply_markup=main_menu
        )
    except Exception as e:
        logger.error(f"❌ /start handler xatosi: {str(e)}")

async def help_handler_local(message: Message):
    await message.answer(
        "ℹ️ Yordam:\n\n"
        "/start - Botni qayta boshlash\n"
        "/help - Bu yordam xabari",
        reply_markup=main_menu
    )

async def handle_ping(request):
    logger.debug("Received ping request")
    return web.Response(text="Bot is running!")

async def start_web_server():
    """Simple web server to keep the bot alive on cloud platforms"""
    try:
        app = web.Application()
        app.router.add_get('/', handle_ping)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.getenv("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"🌐 Web server started on port {port}")
    except Exception as e:
        logger.error(f"❌ Web server start error: {e}")

async def main():
    """Bot-ni ishga tushirish"""
    try:
        logger.info("🎬 Bot startup sequence started...")
        # Initialize Database
        logger.info("🗄 Initializing database...")
        try:
           init_db()
           logger.info("✅ Database initialized.")
        except Exception as db_e:
           logger.error(f"❌ Database error: {db_e}")
        
        # Bot va Dispatcher yaratish
        logger.info("🤖 Creating bot and dispatcher instances...")
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        # Handlerlarni ro'yxatdan o'tkazish
        logger.info("📝 Registering handlers...")
        dp.message.register(start_handler_local, CommandStart())
        dp.message.register(help_handler_local, Command("help"))
        
        @dp.message(F.text.in_({"⬅️ Asosiy menyu", "/start"}))
        async def back_to_main(message: Message):
            await message.answer("Asosiy menyu:", reply_markup=main_menu)

        @dp.message(F.text == "⚙️ Sozlamalar")
        async def settings_handler(message: Message):
             await message.answer("Sozlamalar bo'limi tez orada ishga tushadi.", reply_markup=main_menu)

        # Routerni ulash
        dp.include_router(admin.router)
        dp.include_router(referat.router)
        dp.include_router(presentation.router)
        dp.include_router(course.router)
        dp.include_router(ready_works.router)
        dp.include_router(payment.router)
        
        logger.info("✅ Bot va Dispatcher muvaffaqiyat bilan tayyorlandi")
        
        # Start Web Server
        asyncio.create_task(start_web_server())

        # Start Polling with Retry Logic
        while True:
            try:
                # Delete webhook to ensure polling works
                logger.info("🎬 Polling loop starting: Clearing webhooks...")
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info("🚀 Polling started. Waiting for updates...")
                await dp.start_polling(bot)
            except Exception as e:
                logger.error(f"⚠️ Polling xatosi: {e}. 5 soniyadan keyin qayta ulanadi...")
                await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"Bot ishga tushishda xatolik: {e}")

if __name__ == "__main__":
    asyncio.run(main())
