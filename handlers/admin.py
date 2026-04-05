import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from database import get_admin_stats, get_pending_payments_count, get_all_user_ids
from states import BroadcastState

router = Router()
logger = logging.getLogger(__name__)


# ─── Admin menyusi klaviaturasi ──────────────────────────────────────────────

admin_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Hammaga xabar yuborish", callback_data="admin_broadcast")],
    ]
)

broadcast_confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
        ]
    ]
)

# ─── Yordamchi: admin tekshirish ─────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    admin_id = str(ADMIN_ID).strip() if ADMIN_ID else None
    return str(user_id) == admin_id


# ─── /admin buyrug'i ─────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel_handler(message: Message):
    logger.info(f"Admin command attempt by {message.from_user.id}")
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🔐 <b>Admin Paneli</b>\n\nNimani qilmoqchisiz?",
        reply_markup=admin_menu_kb,
        parse_mode="HTML"
    )


# ─── Statistika callback ──────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await callback.answer()
    try:
        stats = await get_admin_stats()
        pending_count = await get_pending_payments_count()

        if not stats:
            await callback.message.answer("❌ Statistikani yuklashda xatolik yuz berdi.")
            return

        pending_text = ""
        if pending_count > 0:
            pending_text = f"\n⏳ <b>Kutilayotgan to'lovlar: {pending_count} ta</b>\n"

        text = (
            "📊 <b>Admin Paneli — Statistika</b>\n\n"
            f"👥 Umumiy foydalanuvchilar: {stats.get('total_users', 0)}\n"
            f"🆕 Shu oyda qo'shilganlar: {stats.get('monthly_users', 0)}\n"
            f"{pending_text}\n"
            f"<b>Joriy oydagi operatsiyalar:</b>\n"
            f"📄 Yozilgan Referatlar: {stats.get('referat_count', 0)} ta\n"
            f"🎓 Yozilgan Kurs ishlari: {stats.get('course_work_count', 0)} ta\n"
            f"📊 Yaratilgan Taqdimotlar: {stats.get('presentation_count', 0)} ta\n\n"
            f"💰 Shu oyda qilingan to'lovlar ({stats.get('topup_count', 0)} marta): "
            f"{stats.get('topup_sum', 0)} so'm"
        )

        await callback.message.answer(text, parse_mode="HTML", reply_markup=admin_menu_kb)
    except Exception as e:
        logger.error(f"Error in admin_stats_callback: {e}")
        await callback.message.answer(f"❌ Tizimda xatolik: {e}")


# ─── Broadcast boshlash callback ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await callback.answer()
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.answer(
        "📢 <b>Hammaga xabar yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\n"
        "❗ Matn, rasm yoki video yuborishingiz mumkin.\n\n"
        "Bekor qilish uchun /cancel buyrug'ini yuboring.",
        parse_mode="HTML"
    )


# ─── Xabarni qabul qilish (matn) ─────────────────────────────────────────────

@router.message(BroadcastState.waiting_for_message, F.text)
async def broadcast_got_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(
        broadcast_text=message.text,
        broadcast_type="text",
        message_id=message.message_id,
        chat_id=message.chat.id
    )
    await state.set_state(BroadcastState.confirm)

    await message.answer(
        f"📋 <b>Xabar ko'rinishi:</b>\n\n"
        f"{message.text}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Yuborishni tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=broadcast_confirm_kb
    )


# ─── Xabarni qabul qilish (rasm bilan) ───────────────────────────────────────

@router.message(BroadcastState.waiting_for_message, F.photo)
async def broadcast_got_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo_id = message.photo[-1].file_id
    caption = message.caption or ""

    await state.update_data(
        broadcast_type="photo",
        photo_id=photo_id,
        caption=caption,
        message_id=message.message_id,
        chat_id=message.chat.id
    )
    await state.set_state(BroadcastState.confirm)

    confirm_text = (
        f"🖼 <b>Rasm bilan xabar:</b>\n"
        f"Sarlavha: {caption or '(yo\'q)'}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Yuborishni tasdiqlaysizmi?"
    )
    await message.answer(confirm_text, parse_mode="HTML", reply_markup=broadcast_confirm_kb)


# ─── Xabarni qabul qilish (video bilan) ──────────────────────────────────────

@router.message(BroadcastState.waiting_for_message, F.video)
async def broadcast_got_video(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    video_id = message.video.file_id
    caption = message.caption or ""

    await state.update_data(
        broadcast_type="video",
        video_id=video_id,
        caption=caption,
        message_id=message.message_id,
        chat_id=message.chat.id
    )
    await state.set_state(BroadcastState.confirm)

    confirm_text = (
        f"🎬 <b>Video bilan xabar:</b>\n"
        f"Sarlavha: {caption or '(yo\'q)'}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Yuborishni tasdiqlaysizmi?"
    )
    await message.answer(confirm_text, parse_mode="HTML", reply_markup=broadcast_confirm_kb)


# ─── Broadcast tasdiqlash ─────────────────────────────────────────────────────

@router.callback_query(F.data == "broadcast_confirm", BroadcastState.confirm)
async def broadcast_confirmed(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await callback.answer()
    data = await state.get_data()
    await state.clear()

    user_ids = await get_all_user_ids()
    total = len(user_ids)

    if total == 0:
        await callback.message.answer("❌ Foydalanuvchilar topilmadi.")
        return

    status_msg = await callback.message.answer(
        f"⏳ <b>Xabar yuborilmoqda...</b>\n"
        f"Jami foydalanuvchilar: {total} ta",
        parse_mode="HTML"
    )

    sent = 0
    failed = 0
    broadcast_type = data.get("broadcast_type", "text")

    for uid in user_ids:
        try:
            if broadcast_type == "text":
                await bot.send_message(
                    chat_id=uid,
                    text=data["broadcast_text"],
                    parse_mode="HTML"
                )
            elif broadcast_type == "photo":
                await bot.send_photo(
                    chat_id=uid,
                    photo=data["photo_id"],
                    caption=data.get("caption", ""),
                    parse_mode="HTML"
                )
            elif broadcast_type == "video":
                await bot.send_video(
                    chat_id=uid,
                    video=data["video_id"],
                    caption=data.get("caption", ""),
                    parse_mode="HTML"
                )
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for user {uid}: {e}")
            failed += 1

        # Flood limitdan qochish uchun kichik kutish
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Xabar muvaffaqiyatli yuborildi!</b>\n\n"
        f"📤 Yuborildi: {sent} ta\n"
        f"❌ Yuborilmadi: {failed} ta\n"
        f"👥 Jami: {total} ta",
        parse_mode="HTML",
        reply_markup=admin_menu_kb
    )


# ─── Broadcast bekor qilish ───────────────────────────────────────────────────

@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancelled(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    await state.clear()
    await callback.answer("❌ Bekor qilindi", show_alert=False)
    await callback.message.edit_text(
        "❌ Xabar yuborish bekor qilindi.",
        reply_markup=admin_menu_kb
    )


# ─── /cancel buyrug'i ─────────────────────────────────────────────────────────

@router.message(Command("cancel"), BroadcastState.waiting_for_message)
@router.message(Command("cancel"), BroadcastState.confirm)
async def cancel_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=admin_menu_kb)
