from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from keyboards import WEBAPP_URL, FRONTEND_URL, access_keyboard
from handlers.access import check_access

router = Router()


@router.message(F.text == '📊 Taqdimot yaratish')
async def presentation_start(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(message, message.from_user.id, 'presentation'):
        return
    await message.answer('📊 Taqdimot yarating. Mavzu, fan shabloni va tilni mini ilovada tanlang. '
        'Bitta taqdimot — 1 taklif kvotasi. Ko‘pi bilan 3 ta AI rasm yaratiladi va shablonda qayta ishlatiladi.',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='📊 Taqdimot yaratish', web_app=WebAppInfo(url=f'{WEBAPP_URL}?tab=presentations'))]]))


@router.message(F.text == '📝 Maqola yaratish')
async def article_start(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(message, message.from_user.id, 'article'):
        return
    await message.answer('📝 Standart oynasida maqola yarating. Jami 3 ta bepul standart foydalanish, keyin har biri — 1 kvota.',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='📝 Maqola yaratish', web_app=WebAppInfo(url=f'{FRONTEND_URL}?tab=standard'))]]))


@router.message(F.text == '🎨 Dizayn yaratish')
async def design_start(message: Message, state: FSMContext):
    await state.clear()
    if not await check_access(message, message.from_user.id, 'design'):
        return
    await message.answer('🎨 Dizayn yaratish — 1 taklif kvotasi. Tavsif, format va uslubni tanlang.',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='🎨 Dizayn yaratish', web_app=WebAppInfo(url=f'{WEBAPP_URL}?tab=designs'))]]))
