"""Referral wallet, invitation links and service quota previews."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from commerce import status, CommerceError, POLICY_TEXT, quote, ERROR_MESSAGES
from database import get_supabase
from keyboards import access_keyboard

router = Router()
logger = logging.getLogger(__name__)


async def account_text(user_id):
    account = await status(get_supabase(), user_id)
    return (
        f"👥 Tasdiqlangan takliflar: {account['confirmed_referrals']} ta\n"
        f"🎁 Qolgan umumiy kvota: {account['referral_credits']} ta\n"
        f"📊 Taqdimot yoki dizayn: {account['referral_credits']} martagacha\n"
        f"📚 Yoki kurs ishi: {account['course_credits']} martagacha\n"
        f"📄 Qolgan bepul standart foydalanish: {account.get('standard_free_remaining', 0)}/3.\n"
        "Bu imkoniyatlar bitta umumiy kvotadan sarflanadi.\n\n" + POLICY_TEXT
    )


@router.message(F.text == '🎁 Do‘stlarni taklif qilish')
async def invite_message(message: Message):
    await show_invite(message, message.from_user.id, message.bot)


async def show_invite(message, user_id, bot):
    username = (await bot.get_me()).username
    account = await status(get_supabase(), user_id)
    link = f'https://t.me/{username}?start=ref_{user_id}'
    await message.answer(
        f"🎁 Do‘stlaringizga shu havolani yuboring:\n{link}\n\n"
        f"Tasdiqlangan: {account['confirmed_referrals']} ta. Qolgan kvota: {account['referral_credits']} ta.\n\n"
        "Har bir yangi do‘st — 1 kvota. Taqdimot yoki dizayn — 1 kvota; kurs ishi — 2 kvota. "
        "Do‘st havola orqali /start bosib, kanal a’zoligini tasdiqlashi kerak. "
        "O‘zingiz, botlar va avval ro‘yxatdan o‘tgan foydalanuvchilar hisoblanmaydi.",
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
    await callback.message.answer(await account_text(callback.from_user.id), reply_markup=access_keyboard)


async def check_access(message, user_id, service):
    try:
        offer = quote(await status(get_supabase(), user_id), service)
        if offer['allowed']:
            return True
        await message.answer(ERROR_MESSAGES[offer['reason']], reply_markup=access_keyboard)
    except CommerceError as exc:
        await message.answer(str(exc))
    return False
