from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_ID
from database import get_admin_stats, get_pending_payments_count
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("admin"))
async def admin_panel_handler(message: Message):
    # ADMIN_ID ni tekshirish
    user_id = str(message.from_user.id)
    admin_id = str(ADMIN_ID).strip() if ADMIN_ID else None
    
    logger.info(f"Admin command attempt by {user_id}. Registered ADMIN_ID: {admin_id}")

    if user_id != admin_id:
        return

    try:
        stats = await get_admin_stats()
        pending_count = await get_pending_payments_count()
        
        if not stats:
            await message.answer("❌ Statistikani yuklashda xatolik yuz berdi (bazadan ma'lumot kelmadi).")
            return

        pending_text = ""
        if pending_count > 0:
            pending_text = f"\n⏳ <b>Kutilayotgan to'lovlar: {pending_count} ta</b>\n"

        text = (
            "📊 <b>Admin Paneli - Statistika</b>\n\n"
            f"👥 Umumiy foydalanuvchilar: {stats.get('total_users', 0)}\n"
            f"🆕 Shu oyda qo'shilganlar: {stats.get('monthly_users', 0)}\n"
            f"{pending_text}\n"
            f"<b>Joriy oydagi operatsiyalar:</b>\n"
            f"📄 Yozilgan Referatlar: {stats.get('referat_count', 0)} ta\n"
            f"🎓 Yozilgan Kurs ishlari: {stats.get('course_work_count', 0)} ta\n"
            f"📊 Yaratilgan Taqdimotlar: {stats.get('presentation_count', 0)} ta\n\n"
            f"💰 Shu oyda qilingan to'lovlar ({stats.get('topup_count', 0)} marta): {stats.get('topup_sum', 0)} so'm"
        )
        
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in admin_panel_handler: {e}")
        await message.answer(f"❌ Tizimda xatolik: {e}")

