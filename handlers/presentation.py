from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from keyboards import WEBAPP_URL, access_keyboard
from handlers.access import check_access

router = Router()


@router.message(F.text == '📊 Taqdimot yaratish')
async def presentation_start(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(message, message.from_user.id, 'presentation'):
        return
    await message.answer('📊 Taqdimot yarating. Mavzu, fan shabloni va tilni mini ilovada tanlang. '
        'Bitta tayyor taqdimot — bitta limit. Limitdan tashqari narx — 10 000 so‘m.',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='📊 Taqdimot yaratish', web_app=WebAppInfo(url=f'{WEBAPP_URL}?tab=presentations'))]]))


@router.message(F.text == '📝 Maqola yaratish')
async def article_start(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(message, message.from_user.id, 'article'):
        return
    await message.answer('📝 Maqola DeepSeek R1 yordamida yaratiladi. Narxi — 10 000 so‘m.',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='📝 Maqola yaratish', web_app=WebAppInfo(url=f'{WEBAPP_URL}?tab=articles'))]]))
