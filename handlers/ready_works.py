from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
import os
import logging
import asyncio

router = Router()
logger = logging.getLogger(__name__)

READY_WORKS_DIR = "data/ready_works"

@router.message(F.text == "💰 Tayyor ishlar")
async def send_ready_works(message: Message, bot: Bot):
    """
    Tayyor ishlar papkasidagi barcha fayllarni foydalanuvchiga yuboradi
    """
    if not os.path.exists(READY_WORKS_DIR):
        os.makedirs(READY_WORKS_DIR, exist_ok=True)
        await message.answer("📂 Tayyor ishlar bo'limi hozircha bo'sh.")
        return

    files = os.listdir(READY_WORKS_DIR)
    valid_files = [f for f in files if os.path.isfile(os.path.join(READY_WORKS_DIR, f))]

    if not valid_files:
        await message.answer("📂 Tayyor ishlar bo'limi hozircha bo'sh.")
        return

    await message.answer(f"📂 Tayyor ishlar ({len(valid_files)} ta fayl):")

    for file_name in valid_files:
        file_path = os.path.join(READY_WORKS_DIR, file_name)
        try:
            document = FSInputFile(file_path)
            await message.answer_document(document, caption=f"📄 {file_name}")
            # Telegram API limitlariga tushmaslik uchun biroz kutamiz
            await asyncio.sleep(0.5) 
        except Exception as e:
            logger.error(f"Fayl yuborishda xatolik: {file_name} - {e}")
            await message.answer(f"❌ {file_name} faylini yuborishda xatolik yuz berdi.")
    
    await message.answer("✅ Barcha tayyor ishlar yuborildi.\n\nTanlovingiz uchun minnadormiz. Agar ushbu ishni yanada professional darajada qabul qilmoqchi bo'lsangiz mutahasislarimizga murojat qiling: @sardorbekuralov")

