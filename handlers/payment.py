"""Retired payment buttons never create payments or subscriptions."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards import access_keyboard

router = Router()
RETIRED_MESSAGE = 'Obuna va to‘lovlar bekor qilingan. Har bir yangi do‘st taklifi uchun 1 kvota oling.'


@router.message(F.text.in_({'💳 Hisobni to\'ldirish', '💳 Hisobni to‘ldirish'}))
@router.message(Command('payments'))
async def balance_handler(message: Message, state=None):
    if state:
        await state.clear()
    await message.answer(RETIRED_MESSAGE, reply_markup=access_keyboard)


@router.callback_query(F.data.in_({'subscribe', 'subscribe_confirm', 'payment', 'send_receipt',
    'pay_subscription', 'payment_cancel'}) | F.data.startswith('pay_') |
    F.data.startswith('approve_') | F.data.startswith('reject_'))
async def payment_start_callback(callback: CallbackQuery, state=None):
    await callback.answer(RETIRED_MESSAGE, show_alert=True)
    if state:
        await state.clear()
    await callback.message.answer(RETIRED_MESSAGE, reply_markup=access_keyboard)


async def _payment_menu(callback, state=None):
    await payment_start_callback(callback, state)
