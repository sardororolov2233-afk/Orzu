"""Card receipts are reviewed by an admin; image analysis never credits money."""
import hashlib
import io
import logging
from html import escape
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import payment_keyboard, send_receipt_kb, get_admin_approval_kb, main_menu, access_keyboard
from config import ADMIN_IDS
from commerce import PAYMENT_CARD, CommerceError
from database import (get_user_balance, create_pending_payment, approve_pending_payment,
    reject_pending_payment, get_pending_payments_list)
from ai.receipt_verifier import verify_receipt_image
from handlers.access import account_text

router = Router()
logger = logging.getLogger(__name__)


class PaymentState(StatesGroup):
    amount_selection = State()
    waiting_receipt = State()
    reviewing = State()


@router.message(F.text == "💳 Hisobni to'ldirish")
async def balance_handler(message: Message, state: FSMContext):
    await state.clear()
    balance = await get_user_balance(message.from_user.id)
    await message.answer(f"💳 Balans: {int(balance):,} so‘m.\n\nTo‘lov turini tanlang. "
        "Obuna — 25 000 so‘mga bir oy va 10 ta taqdimot. Boshqa summalar balansga qo‘shiladi.", reply_markup=payment_keyboard)


@router.callback_query(F.data == 'payment')
async def payment_start_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await _payment_menu(callback, state)


async def _payment_menu(callback, state):
    await state.clear()
    balance = await get_user_balance(callback.from_user.id)
    await callback.message.answer(f"💳 Balans: {int(balance):,} so‘m. To‘lovni tanlang:", reply_markup=payment_keyboard)


@router.callback_query(F.data.startswith('pay_'))
async def payment_amount_selected(callback: CallbackQuery, state: FSMContext):
    options = {'pay_8000': 8000, 'pay_10000': 10000, 'pay_30000': 30000, 'pay_50000': 50000,
        'pay_subscription': 25000}
    amount = options.get(callback.data)
    if amount is None:
        await callback.answer('Bu to‘lov tugmasi eskirgan. Hisob menyusini oching.', show_alert=True)
        return
    purpose = 'subscription' if callback.data == 'pay_subscription' else 'topup'
    await state.update_data(payment_amount=amount, payment_purpose=purpose)
    await state.set_state(PaymentState.amount_selection)
    await callback.answer()
    label = 'Bir oylik obuna (10 ta taqdimot)' if purpose == 'subscription' else 'Balansni to‘ldirish'
    await callback.message.answer(
        f"💳 <b>{label}</b>\nSumma: {amount:,} so‘m\n"
        f"Karta: <code>{PAYMENT_CARD}</code>\nKarta egasi: O‘ralov Sardorbek\n\n"
        "To‘lovdan so‘ng chek rasmini yuboring. Mablag‘ kelib tushgani admin tomonidan "
        "tekshirilgach obuna yoki balans faollashadi.", parse_mode='HTML', reply_markup=send_receipt_kb)


@router.callback_query(PaymentState.amount_selection, F.data == 'send_receipt')
async def ask_receipt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PaymentState.waiting_receipt)
    await callback.message.answer('📸 To‘lov chekining rasmini yuboring:')


@router.callback_query(F.data.in_({'payment_cancel', 'back_main'}))
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer('Asosiy menyu:', reply_markup=main_menu)


@router.message(PaymentState.waiting_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount = data.get('payment_amount')
    if amount is None:
        await state.clear()
        await message.answer('To‘lov summasini qayta tanlang.', reply_markup=payment_keyboard)
        return
    await state.set_state(PaymentState.reviewing)
    receipt_file_id = message.photo[-1].file_id
    progress = await message.answer('⏳ Chek qabul qilinmoqda...')
    try:
        photo = await bot.get_file(receipt_file_id)
        if (photo.file_size or 0) > 10 * 1024 * 1024:
            raise ValueError('Rasm 10 MB dan katta')
        stream = io.BytesIO()
        await bot.download_file(photo.file_path, destination=stream)
        image_bytes = stream.getvalue()
        try:
            review = await verify_receipt_image(image_bytes, amount)
        except Exception:
            logger.exception('Receipt analysis unavailable')
            review = {'is_valid': False, 'rejection_reason': 'AI tahlili mavjud emas; qo‘lda tekshiring.'}
        payment_id = await create_pending_payment(message.from_user.id, amount, receipt_file_id,
            username=message.from_user.username, full_name=message.from_user.full_name,
            purpose=data.get('payment_purpose', 'topup'), receipt_hash=hashlib.sha256(image_bytes).hexdigest(),
            receipt_tx=review.get('transaction_id'), review=review)
        if not payment_id:
            raise RuntimeError('To‘lov saqlanmadi')
    except Exception:
        logger.exception('Receipt could not be saved')
        await state.clear()
        await progress.edit_text('Chek saqlanmadi yoki oldin yuborilgan. Hisob menyusidan qayta urinib ko‘ring. '
            'Takroriy chek yangi to‘lov bermaydi.')
        return
    await state.clear()
    await progress.edit_text(f"✅ Chek saqlandi. Buyurtma #{payment_id}. Admin to‘lovni tekshiradi.")
    note = 'AI: mos' if review.get('is_valid') else f"AI: {review.get('rejection_reason') or 'qo‘lda tekshiring'}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(admin_id, receipt_file_id, caption=(
                f"💳 To‘lov #{escape(payment_id)}\n"
                f"Foydalanuvchi: {escape(message.from_user.full_name)}\nID: {message.from_user.id}\n"
                f"Summa: {amount:,} so‘m\nTuri: {data.get('payment_purpose', 'topup')}\n"
                f"{escape(note[:350])}\n\nKartaga pul kelganini tekshirib tasdiqlang."),
                parse_mode='HTML', reply_markup=get_admin_approval_kb(payment_id))
        except Exception:
            logger.exception('Admin notification failed; payment remains in /payments')


@router.message(PaymentState.waiting_receipt)
async def process_non_photo_receipt(message: Message):
    await message.answer('📸 Chekni rasm ko‘rinishida yuboring.')


@router.message(Command('payments'))
async def pending_payments(message: Message, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return
    pending = await get_pending_payments_list()
    if not pending:
        await message.answer('Kutilayotgan to‘lovlar yo‘q.')
    for payment in pending[:30]:
        await bot.send_photo(message.chat.id, payment['receipt_file_id'],
            caption=f"To‘lov #{payment['id']} | {payment['user_id']} | {payment['amount']} so‘m | {payment.get('purpose', 'topup')}",
            reply_markup=get_admin_approval_kb(payment['id']))


@router.callback_query(F.data.startswith('approve_'))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer('Ruxsat yo‘q.', show_alert=True)
        return
    try:
        payment = await approve_pending_payment(callback.data[len('approve_'):])
    except CommerceError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    if not payment:
        await callback.answer('Bu to‘lov allaqachon ko‘rib chiqilgan.', show_alert=True)
        return
    await callback.answer('To‘lov tasdiqlandi.')
    await callback.message.edit_reply_markup(reply_markup=None)
    try:
        await bot.send_message(payment['user_id'], '✅ To‘lov tasdiqlandi.\n\n' + await account_text(payment['user_id']),
            reply_markup=access_keyboard)
    except Exception:
        logger.exception('Payment confirmation notification failed')


@router.callback_query(F.data.startswith('reject_'))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer('Ruxsat yo‘q.', show_alert=True)
        return
    try:
        payment = await reject_pending_payment(callback.data[len('reject_'):])
    except CommerceError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    if not payment:
        await callback.answer('Bu to‘lov allaqachon ko‘rib chiqilgan.', show_alert=True)
        return
    await callback.answer('To‘lov rad etildi.')
    await callback.message.edit_reply_markup(reply_markup=None)
    try:
        await bot.send_message(payment['user_id'], f"❌ {int(payment['amount']):,} so‘mlik to‘lov tasdiqlanmadi. "
            'Savollar uchun: @sardorbekuralov', reply_markup=payment_keyboard)
    except Exception:
        logger.exception('Payment rejection notification failed')
