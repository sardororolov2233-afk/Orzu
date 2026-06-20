import asyncio
import sys
import logging
import os
from pathlib import Path
from aiohttp import web

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery
from config import BOT_TOKEN, ADMIN_ID
from keyboards import main_menu, subscribe_channel_kb, design_link_kb

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

from database import create_or_update_user

CHANNEL_USERNAME = "@yordamch_AI"

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to check subscription for {user_id}: {e}")
        return False

async def start_handler_local(message: Message, bot: Bot):
    logger.info(f"🔵 /start buyrugu. Foydalanuvchi: {message.from_user.id}")
    try:
        is_subbed = await check_user_subscription(bot, message.from_user.id)
        if not is_subbed:
            await message.answer(
                "❌ Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'lishingiz majburiy!\n\n"
                "Iltimos, avval kanalga obuna bo'ling, so'ng 'Tasdiqlash' tugmasini bosing.",
                reply_markup=subscribe_channel_kb
            )
            return

        # Register/Update user in Supabase
        user_data = {
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "username": message.from_user.username,
        }
        await create_or_update_user(message.from_user.id, user_data)
        
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
        # Database initialization removed (using Supabase)
        logger.info("🗄 Unified Supabase database module loaded.")
        
        # Bot va Dispatcher yaratish
        logger.info("🤖 Creating bot and dispatcher instances...")
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())

        # Handlerlarni ro'yxatdan o'tkazish
        logger.info("📝 Registering handlers...")
        dp.message.register(start_handler_local, CommandStart())
        dp.message.register(help_handler_local, Command("help"))
        
        @dp.message(F.text.in_({"⬅️ Asosiy menyu", "/start"}))
        async def back_to_main(message: Message):
            await message.answer("Asosiy menyu:", reply_markup=main_menu)

        @dp.callback_query(F.data == "check_subscription")
        async def check_sub_callback(callback: CallbackQuery, bot: Bot):
            is_subbed = await check_user_subscription(bot, callback.from_user.id)
            if is_subbed:
                await callback.message.delete()
                # Run the normal start flow
                user_data = {
                    "first_name": callback.from_user.first_name,
                    "last_name": callback.from_user.last_name,
                    "username": callback.from_user.username,
                }
                await create_or_update_user(callback.from_user.id, user_data)
                await callback.message.answer(
                    "✅ Obuna tasdiqlandi!\n\n"
                    "👋 Assalomu alaykum!\n\n"
                    "📚 Referat, taqdimot, kurs va diplom ishlarini sun'iy intellekt yordamida tayyorlab beramiz.\n\n"
                    "Quyidagilardan birini tanlang 👇",
                    reply_markup=main_menu
                )
            else:
                await callback.answer("❌ Hali obuna bo'lmadingiz. Iltimos kanalga o'tib obuna bo'ling!", show_alert=True)

        @dp.message(F.text == "🆘 Yordam")
        async def settings_handler(message: Message):
             await message.answer(
                "💬 Yordam xizmati\n\n"
                "Qo'shimcha savollar yoki muammolar yuzasidan administrator bilan bog'laning:\n"
                "👨‍💻 @Gulroz_7711", 
                reply_markup=main_menu
             )

        @dp.message(F.text == "💵 Narxlar")
        async def prices_handler(message: Message):
             await message.answer(
                "💰 <b>Xizmatlarimiz narxlari bilan tanishing:</b>\n\n"
                "📄 <b>Referat va Mustaqil ishlar:</b>\n"
                "🔹 Oddiy tarif: 8 000 so'm <i>(Promo-kod bilan: 2 400 so'm)</i>\n"
                "🔥 PRO tarif: 14 900 so'm <i>(Promo-kod bilan: 4 470 so'm)</i>\n\n"
                "📚 <b>Kurs ishlari:</b>\n"
                "🔹 Oddiy tarif: 15 000 so'm <i>(Promo-kod bilan: 4 500 so'm)</i>\n"
                "🔥 PRO tarif: 29 900 so'm <i>(Promo-kod bilan: 8 970 so'm)</i>\n\n"
                "📊 <b>Taqdimot (Slaydlar):</b>\n"
                "🔹 Web dasturimiz orqali narxlanadi (slaydlar soniga qarab).\n\n"
                "🎁 <i>Eslatma: Promo-kodlarni botimiz va @yordamch_AI kanalimiz orqali olishingiz mumkin!</i>",
                reply_markup=main_menu,
                parse_mode="HTML"
             )

        @dp.message(F.text == "📝 Buyurtma asosida yaratish")
        async def order_handler(message: Message):
             await message.answer(
                "📝 <b>Maxsus buyurtma asosida yaratish</b>\n\n"
                "Sizda o'ziga xos talablar bormi? Yoki bot funksiyalari doirasidan tashqari maxsus murakkab ish kerakmi?\n"
                "Batafsil ma'lumot va kelishuv uchun to'g'ridan-to'g'ri administratorimizga murojaat qiling:\n\n"
                "👨‍💻 <b>Adminga murojaat qiling:</b> @Gulroz_7711",
                reply_markup=main_menu,
                parse_mode="HTML"
             )

        @dp.message(F.text == "🎓 Bitiruv Malakaviy ishi")
        async def bmi_handler(message: Message):
             await message.answer(
                "🎓 <b>Bitiruv Malakaviy Ishi (BMI)</b>\n\n"
                "Bitiruv malakaviy ishlari va magistrlik dissertatsiyalarini tayyorlash bo'yicha maxsus rahbarlik va yordam ko'rsatamiz.\n"
                "Talablaringizni muhokama qilish uchun biz bilan bog'laning:\n\n"
                "👨‍💻 <b>Bizga murojat qiling:</b> @Gulroz_7711",
                reply_markup=main_menu,
                parse_mode="HTML"
             )

        @dp.message(F.text == "🎨 Grafik dizayn tayyorlash")
        async def design_handler(message: Message):
             await message.answer(
                "🎨 <b>Grafik dizayn tayyorlash</b>\n\n"
                "Quyidagi tugma orqali grafik dizayn tayyorlash sahifasiga o'ting:",
                reply_markup=design_link_kb,
                parse_mode="HTML"
             )

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
