"""Referral onboarding, account allowance and explicit subscription purchase."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from commerce import rpc, status, CommerceError, POLICY_TEXT, quote
from database import get_supabase
from keyboards import access_keyboard, subscription_confirm_kb

router = Router()
logger = logging.getLogger(__name__)


async def account_text(user_id):
    account = await status(get_supabase(), user_id)
    expiry = (account.get('subscription_end') or '')[:10]
    sub = f"{account['subscription_remaining']} ta ({expiry} gacha)" if account['subscription_active'] else 'faol emas'
    return (
        f"💳 Balans: {int(account.get('balance') or 0):,} so‘m\n"
        f"👥 Tasdiqlangan takliflar: {account['confirmed_referrals']} ta\n"
        f"🎁 Keyingi mukofotgacha: {account['next_reward_in']} ta yangi do‘st\n"
        f"📊 Bepul taqdimotlar: {account['referral_presentations']} ta\n"
        f"📚 Bepul kurs ishlari: {account['course_credits']} ta\n"
        f"🗓 Obuna: {sub}\n\n{POLICY_TEXT}"
    )


@router.message(F.text == '🎁 Do‘stlarni taklif qilish')
async def invite_message(message: Message):
    await show_invite(message, message.from_user.id, message.bot)


async def show_invite(message, user_id, bot):
    username = (await bot.get_me()).username
    account = await status(get_supabase(), user_id)
    link = f"https://t.me/{username}?start=ref_{user_id}"
    await message.answer(
        f"🎁 Do‘stlaringizga shu havolani yuboring:\n{link}\n\n"
        f"Tasdiqlangan: {account['confirmed_referrals']} ta. Keyingi mukofotgacha: {account['next_reward_in']} ta.\n\n"
        "Har 5 ta yangi do‘st uchun bir oyga 5 ta taqdimot va 1 ta kurs ishi bepul. "
        "Do‘st havola orqali /start bosib, kanal a’zoligini tasdiqlashi kerak. "
        "O‘zingiz va avval ro‘yxatdan o‘tgan foydalanuvchilar hisoblanmaydi.",
        reply_markup=access_keyboard)


@router.callback_query(F.data == 'invite')
async def invite_callback(callback: CallbackQuery):
    await callback.answer()
    await show_invite(callback.message, callback.from_user.id, callback.bot)


@router.message(F.text == '👤 Hisob va limitlar')
async def account_message(message: Message):
    try:
        await message.answer(await account_text(message.from_user.id), reply_markup=access_keyboard)
    except CommerceError as exc:
        await message.answer(str(exc))


@router.callback_query(F.data == 'account')
async def account_callback(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.answer(await account_text(callback.from_user.id), reply_markup=access_keyboard)
    except CommerceError as exc:
        await callback.message.answer(str(exc))


@router.callback_query(F.data == 'subscribe')
async def subscription_offer(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "🗓 Bir oylik obuna — 25 000 so‘m.\n10 ta taqdimot, har bir qo‘shimchasi 10 000 so‘m.\n"
        "Yana 5 ta do‘st taklif qilib 5 ta qo‘shimcha bepul taqdimot olishingiz ham mumkin.\n"
        "Kurs ishi, referat va maqola obunaga kirmaydi.\n\n"
        "Balansingizda mablag‘ bo‘lsa, quyidagi tugma bilan xaridni tasdiqlang. "
        "Aks holda karta orqali 25 000 so‘m to‘lab, chek yuborishingiz mumkin.",
        reply_markup=subscription_confirm_kb)


@router.callback_query(F.data == 'subscribe_confirm')
async def subscription_purchase(callback: CallbackQuery):
    try:
        await rpc(get_supabase(), 'commerce_subscribe', p_user_id=callback.from_user.id)
    except CommerceError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.answer('Obuna faollashdi!')
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(await account_text(callback.from_user.id), reply_markup=access_keyboard)


async def check_access(message, user_id, service):
    try:
        offer = quote(await status(get_supabase(), user_id), service)
        if offer['allowed']:
            return True
        from commerce import ERROR_MESSAGES
        await message.answer(ERROR_MESSAGES[offer['reason']], reply_markup=access_keyboard)
    except CommerceError as exc:
        await message.answer(str(exc))
    return False
