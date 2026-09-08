import io
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import payment_keyboard, send_receipt_kb, get_admin_approval_kb, main_menu
from config import ADMIN_IDS
from database import (
    update_user_balance, get_user_balance, log_user_action,
    create_pending_payment, approve_pending_payment,
    reject_pending_payment, record_verified_receipt
)
from ai.receipt_verifier import verify_receipt_image

router = Router()
logger = logging.getLogger(__name__)

class PaymentState(StatesGroup):
    amount_selection = State()
    waiting_receipt = State()

@router.message(F.text == "💳 Hisobni to'ldirish")
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
    
    bonus_note = "\n🎁 <i>20,000 so'm va undan ortiq to'lovlar uchun +50% BONUS qo'shiladi!</i>\n" if amount >= 20000 else ""

    text = (
        f"💳 <b>To'lov summasi:</b> {amount:,} so'm\n{bonus_note}\n"
        f"💳 <b>Karta raqami:</b> <code>9860020144204623</code>\n"
        f"👤 <b>Karta egasi:</b> O'ralov sardorbek\n\n"
        f"📋 <i>Karta raqami ustiga bossangiz avtomatik nusxa olinadi.</i>\n\n"
        f"⚠️ <b>DIQQAT:</b> To'lov cheki sun'iy intellekt (AI) orqali avtomatik tekshiriladi. "
        f"Soxta yoki dublikat chek yuborish taqiqlanadi!\n\n"
        f"To'lov qilganingizdan so'ng, <b>Chekni yuborish</b> tugmasini bosing."
    )
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=send_receipt_kb)

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
    data = await state.get_data()
    amount = data.get("payment_amount")
    if not amount:
        await message.answer("❌ Summa topilmadi. Iltimos, /start buyrug'ini yuboring va qaytadan to'lov qiling.")
        await state.clear()
        return

    user = message.from_user
    receipt_file_id = message.photo[-1].file_id
    username_str = f"@{user.username}" if user.username else "yo'q"
    
    # 1. Bildirishnoma: chek tasdiqlanmoqda
    status_msg = await message.answer(
        "⏳ <b>Chek tasdiqlanmoqda...</b>\n\n"
        "Sun'iy intellekt (AI) to'lov chekini tahlil qilmoqda, iltimos kuting...",
        parse_mode="HTML"
    )
    
    await state.clear()

    # 2. Rasmni yuklab olish
    try:
        photo_file = await bot.get_file(receipt_file_id)
        photo_io = io.BytesIO()
        await bot.download_file(photo_file.file_path, destination=photo_io)
        image_bytes = photo_io.getvalue()
    except Exception as e:
        logger.error(f"Rasmni yuklab olishda xatolik: {e}")
        await status_msg.edit_text(
            "❌ Rasmni yuklab olishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring yoki administratorga murojaat qiling: @sardorbekuralov"
        )
        return

    # 3. AI orqali chekni tahlil qilish
    try:
        verify_result = await verify_receipt_image(image_bytes=image_bytes, expected_amount=amount)
    except Exception as e:
        logger.error(f"AI tekshiruvida xatolik: {e}")
        verify_result = {
            "is_valid": False,
            "rejection_reason": "Tizimda texnik xatolik yuz berdi. Iltimos administrator bilan bog'laning: @sardorbekuralov"
        }

    # 4. Agar AI chekni TASDIQLASA:
    if verify_result.get("is_valid"):
        tx_id = verify_result.get("transaction_id")
        image_hash = verify_result.get("image_hash")

        # Bazaga to'lovni yozish
        payment_id = await create_pending_payment(
            user_id=user.id,
            amount=amount,
            receipt_file_id=receipt_file_id,
            username=user.username,
            full_name=user.full_name
        )

        approved = None
        if payment_id:
            approved = await approve_pending_payment(payment_id)

        # Dublikatlarni oldini olish uchun yozib qo'yish
        await record_verified_receipt(
            user_id=user.id,
            tx_id=tx_id,
            image_hash=image_hash,
            amount=amount
        )

        new_balance = await get_user_balance(user.id)
        new_balance_int = int(new_balance)
        final_amount = approved["amount"] if approved else amount
        bonus_msg = f"\n🎁 <i>20,000+ so'm uchun 50% bonus qo'shildi!</i>" if final_amount > amount else ""
        tx_msg = f"\n🧾 <b>Tranzaksiya ID:</b> <code>{tx_id}</code>" if tx_id else ""
        date_msg = f"\n📅 <b>Vaqt:</b> {verify_result.get('date_time')}" if verify_result.get('date_time') else ""

        # Foydalanuvchiga muvaffaqiyat bildirishnomasi
        success_text = (
            f"✅ <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
            f"💰 <b>Qo'shilgan summa:</b> {final_amount:,} so'm{bonus_msg}\n"
            f"💳 <b>Joriy balansingiz:</b> <b>{new_balance_int:,} so'm</b>"
            f"{tx_msg}"
            f"{date_msg}\n\n"
            f"🎉 Bot xizmatlaridan to'liq foydalanishingiz mumkin!",
        )

        try:
            await status_msg.edit_text(success_text[0], parse_mode="HTML", reply_markup=main_menu)
        except Exception:
            await message.answer(success_text[0], parse_mode="HTML", reply_markup=main_menu)

        # Adminga xabarnoma yuborish
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🤖 <b>AI to'lovni avtomatik tasdiqladi!</b>\n\n"
                        f"👤 <b>Foydalanuvchi:</b> {user.full_name} ({username_str})\n"
                        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                        f"💰 <b>Summa:</b> {amount:,} so'm (Balansga: {final_amount:,} so'm)\n"
                        f"🧾 <b>Tranzaksiya:</b> <code>{tx_id or 'yo\'q'}</code>\n"
                        f"💳 <b>Yangi balans:</b> {new_balance_int:,} so'm\n"
                        f"🔑 <b>Payment ID:</b> {payment_id}"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Admin {admin_id} ga bildirishnoma yuborishda xatolik: {e}")

    # 5. Agar AI chekni RAD ETGAN bo'lsa:
    else:
        reason = verify_result.get("rejection_reason") or "To'lov cheki tasdiqlanmadi."
        
        # Bazada rad etilgan to'lov sifatida qayd qilish
        await create_pending_payment(
            user_id=user.id,
            amount=amount,
            receipt_file_id=f"REJECTED_{receipt_file_id[:30]}",
            username=user.username,
            full_name=user.full_name
        )

        rejection_text = (
            f"❌ <b>To'lov cheki qabul qilinmadi!</b>\n\n"
            f"⚠️ <b>Sabab:</b> {reason}\n\n"
            f"Iltimos, qaytadan urinib ko'ring yoki karta rekvizitlarini to'g'ri tekshirib to'lang.\n"
            f"Agar bu xatolik deb hisoblasangiz, administrator bilan bog'laning: @sardorbekuralov"
        )

        try:
            await status_msg.edit_text(rejection_text, parse_mode="HTML", reply_markup=main_menu)
        except Exception:
            await message.answer(rejection_text, parse_mode="HTML", reply_markup=main_menu)

        # Adminga rasm bilan birga xabarnoma yuborish
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=receipt_file_id,
                    caption=(
                        f"⚠️ <b>AI to'lov chekini rad etdi!</b>\n\n"
                        f"👤 <b>Foydalanuvchi:</b> {user.full_name} ({username_str})\n"
                        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                        f"💰 <b>Tanlangan summa:</b> {amount:,} so'm\n"
                        f"❌ <b>Sabab:</b> {reason}"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Admin {admin_id} ga rad etilgan chekni yuborishda xatolik: {e}")

@router.message(PaymentState.waiting_receipt)
async def process_non_photo_receipt(message: Message):
    await message.answer(
        "📸 Iltimos, to'lov chekini faqat <b>rasm (skrinshot)</b> ko'rinishida yuboring.",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    try:
        payment_id = int(callback.data[len("approve_"):])
    except ValueError:
        await callback.answer("❌ Noto'g'ri to'lov ID!", show_alert=True)
        return
    
    result = await approve_pending_payment(payment_id)
    if not result:
        await callback.answer("❌ Bu to'lov allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    
    user_id = result["user_id"]
    amount = result["amount"]
    
    new_balance = await get_user_balance(user_id)
    new_balance_int = int(new_balance)
    
    await log_user_action(user_id, 'topup', amount=amount)
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n✅ QO'LDA TASDIQLANDI ✅\n💰 Yangi balans: {new_balance_int:,} so'm"
        )
    except Exception:
        pass
    try:
        await bot.send_message(
            user_id,
            f"✅ To'lovingiz admin tomonidan tasdiqlandi!\n\n"
            f"💰 Hisobingizga <b>{amount:,} so'm</b> qo'shildi.\n"
            f"💳 Joriy balans: <b>{new_balance_int:,} so'm</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Foydalanuvchiga xabar yuborib bo'lmadi {user_id}: {e}")
    await callback.answer("✅ To'lov tasdiqlandi!", show_alert=True)

@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
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
    
    try:
        await callback.message.edit_caption(
            caption=f"{callback.message.caption}\n\n❌ QO'LDA RAD ETILDI"
        )
    except Exception:
        pass
    try:
        await bot.send_message(
            user_id,
            f"❌ Sizning {amount} so'mlik to'lovingiz admin tomonidan rad etildi.\n"
            f"Sabab: Chek noto'g'ri yoki to'lov tushmagan.\n"
            f"Murojaat uchun: @sardorbekuralov"
        )
    except:
        pass
    await callback.answer("❌ To'lov rad etildi!", show_alert=True)
