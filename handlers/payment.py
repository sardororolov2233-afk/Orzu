from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import payment_keyboard, send_receipt_kb, get_admin_approval_kb, main_menu
from config import ADMIN_ID
from database import (
    update_user_balance, get_user_balance, log_user_action,
    create_pending_payment, approve_pending_payment,
    reject_pending_payment
)
import logging

router = Router()
logger = logging.getLogger(__name__)

class PaymentState(StatesGroup):
    amount_selection = State()
    waiting_receipt = State()

@router.message(F.text == "💳 Balans")
async def balance_handler(message: Message):
    balance = await get_user_balance(message.from_user.id)
    balance_int = int(balance)
    
    await message.answer(
        f"💳 Sizning hisobingizda: <b>{balance_int:,} so'm</b>\n\n"
        "Hisobni to'ldirish uchun summani tanlang:",
        parse_mode="HTML",
        reply_markup=payment_keyboard
    )

@router.callback_query(F.data == "payment")
async def payment_start_callback(callback: CallbackQuery):
    balance = await get_user_balance(callback.from_user.id)
    balance_int = int(balance)
    
    await callback.message.edit_text(
        f"💳 Sizning hisobingizda: <b>{balance_int:,} so'm</b>\n\n"
        "Hisobni to'ldirish uchun summani tanlang:",
        parse_mode="HTML",
        reply_markup=payment_keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"))
async def payment_amount_selected(callback: CallbackQuery, state: FSMContext):
    amount_map = {
        "pay_5000": 5000,
        "pay_10000": 10000,
        "pay_15000": 15000,
        "pay_20000": 20000,
        "pay_25000": 25000,
        "pay_30000": 30000,
        "pay_50000": 50000,
    }
    
    amount = amount_map.get(callback.data)
    if not amount:
        return

    await state.update_data(payment_amount=amount)
    
    text = (
        f"💳 To'lov summasi: {amount} so'm\n\n"
        f"💳 Karta raqami: `9860 0201 4420 4623`\n"
        f"👤 Karta egasi: O'ralov Sardor\n\n"
        f"⚠️ DIQQAT: Soxta chek yuborish BAN ga olib kelishi mumkin!\n"
        f"To'lov qilganingizdan so'ng, chekni yuborish tugmasini bosing."
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=send_receipt_kb)

@router.callback_query(F.data == "send_receipt")
async def ask_receipt(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("📸 Iltimos, to'lov chekini rasm ko'rinishida yuboring:")
    await state.set_state(PaymentState.waiting_receipt)

@router.callback_query(F.data == "payment_cancel")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("To'lov bekor qilindi.", reply_markup=main_menu)

@router.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu)

@router.message(PaymentState.waiting_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    if not ADMIN_ID:
        await message.answer("❌ Tizimda xatolik: Admin sozlanmagan. Iltimos keyinroq urinib ko'ring.")
        await state.clear()
        return

    data = await state.get_data()
    amount = data.get("payment_amount")
    if not amount:
        await message.answer("❌ Summa topilmadi. Iltimos qaytadan boshlang.")
        await state.clear()
        return

    user = message.from_user
    receipt_file_id = message.photo[-1].file_id
    username_str = f"@{user.username}" if user.username else "yo'q"
    
    # Bazaga pending payment sifatida saqlash
    payment_id = await create_pending_payment(
        user_id=user.id,
        amount=amount,
        receipt_file_id=receipt_file_id,
        username=user.username,
        full_name=user.full_name
    )
    
    if not payment_id:
        await message.answer("❌ Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
        await state.clear()
        return
    
    # Admin ga yuborish
    caption = (
        f"📩 Yangi to'lov cheki!\n\n"
        f"👤 Foydalanuvchi: {user.full_name} ({username_str})\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Summa: {amount:,} so'm\n"
        f"🔑 Payment ID: {payment_id}"
    )
    
    try:
        await bot.send_photo(
            chat_id=int(ADMIN_ID),
            photo=receipt_file_id,
            caption=caption,
            reply_markup=get_admin_approval_kb(payment_id)
        )
        await message.answer(
            "✅ Chek muvaffaqiyatli yuborildi!\n\n"
            "⏳ Admin tasdiqlaganidan so'ng hisobingiz to'ldiriladi.\n"
            "Iltimos, kuting...",
            reply_markup=main_menu
        )
    except Exception as e:
        logger.error(f"Admin ga yuborishda xatolik: {e}")
        await message.answer(
            "❌ Chekni admin ga yuborishda xatolik yuz berdi.\n"
            "Iltimos @sardorbekuralov bilan bog'laning."
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    # Format: approve_123  (payments.id = int8)
    try:
        payment_id = int(callback.data[len("approve_"):])
    except ValueError:
        await callback.answer("❌ Noto'g'ri to'lov ID!", show_alert=True)
        return
    
    # Bazadan to'lov ma'lumotlarini olish va statusni yangilash
    result = await approve_pending_payment(payment_id)
    
    if not result:
        await callback.answer("❌ Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    
    user_id = result["user_id"]
    amount = result["amount"]
    
    # Balansni yangilash database.py ichida approve_pending_payment da qilingan!
    new_balance = await get_user_balance(user_id)
    new_balance_int = int(new_balance)
    
    await log_user_action(user_id, 'topup', amount=amount)
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ TASDIQLANDI ✅\n💰 Yangi balans: {new_balance_int:,} so'm"
        )
    except Exception:
        pass
    try:
        await bot.send_message(
            user_id,
            f"✅ To'lovingiz tasdiqlandi!\n\n"
            f"💰 Hisobingizga <b>{amount:,} so'm</b> qo'shildi.\n"
            f"💳 Joriy balans: <b>{new_balance_int:,} so'm</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Foydalanuvchiga xabar yuborib bo'lmadi {user_id}: {e}")
    await callback.answer("✅ To'lov tasdiqlandi!", show_alert=True)

@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    # Format: reject_123  (payments.id = int8)
    try:
        payment_id = int(callback.data[len("reject_"):])
    except ValueError:
        await callback.answer("❌ Noto'g'ri to'lov ID!", show_alert=True)
        return
    
    result = await reject_pending_payment(payment_id)
    
    if not result:
        await callback.answer("❌ Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    
    user_id = result["user_id"]
    amount = result["amount"]
    
    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n❌ RAD ETILDI"
    )
    try:
        await bot.send_message(
            user_id,
            f"❌ Sizning {amount} so'mlik to'lovingiz rad etildi.\n"
            f"Sabab: Chek noto'g'ri yoki to'lov tushmagan."
        )
    except:
        pass
