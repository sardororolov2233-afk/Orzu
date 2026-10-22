import asyncio
import contextlib
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, BaseMiddleware, Router
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from config import BOT_TOKEN, ADMIN_IDS, CHANNEL_USERNAME, OPENROUTER_API_KEY
from database import get_supabase
from commerce import register, rpc, parse_referrer, CommerceError, POLICY_TEXT
from keyboards import main_menu, subscribe_channel_kb, access_keyboard, obyektivka_link_kb
from handlers import access, payment, referat, presentation, course, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in {'member', 'administrator', 'creator'} or (
            member.status == 'restricted' and getattr(member, 'is_member', False))
    except Exception:
        logger.exception('Channel membership check failed')
        return False


async def confirm_referral(user_id, bot):
    result = await rpc(get_supabase(), 'commerce_confirm_referral', p_user_id=user_id)
    if result.get('awarded'):
        with contextlib.suppress(Exception):
            await bot.send_message(result['referrer_id'], '🎉 Yangi do‘stingiz tasdiqlandi! '
                'Umumiy hisobingizga 1 kvota qo‘shildi. Taqdimot/dizayn — 1, kurs ishi — 2 kvota.',
                reply_markup=access_keyboard)


async def show_welcome(message):
    await message.answer('👋 Xush kelibsiz! Bepul xizmatdan foydalaning yoki do‘st taklif qilib kvota oling.\n\n'
        + POLICY_TEXT, reply_markup=access_keyboard)
    await message.answer('Kerakli xizmatni tanlang:', reply_markup=main_menu)


async def start_handler_local(message: Message, bot: Bot, state: FSMContext, command: CommandObject):
    if message.from_user.is_bot:
        return
    try:
        await state.clear()
        # Attribution is saved BEFORE the channel join screen; a later click cannot steal it.
        await register(get_supabase(), message.from_user.model_dump(), parse_referrer(command.args))
        await state.update_data(start_action=command.args or '')
        if not await check_user_subscription(bot, message.from_user.id):
            await message.answer('Avval rasmiy kanalga a’zo bo‘ling va Tasdiqlash tugmasini bosing.', reply_markup=subscribe_channel_kb)
            return
        await confirm_referral(message.from_user.id, bot)
        if command.args == 'payment':
            await payment.balance_handler(message, state)
        else:
            await show_welcome(message)
    except CommerceError as exc:
        await message.answer(str(exc))


class MembershipMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        is_start = isinstance(event, Message) and (event.text or '').split('@')[0].split(' ')[0] == '/start'
        if is_start or (isinstance(event, CallbackQuery) and event.data == 'check_subscription'):
            return await handler(event, data)
        if user.id in ADMIN_IDS:
            return await handler(event, data)
        if user.is_bot:
            return
        target = event.message if isinstance(event, CallbackQuery) else event
        try:
            await register(get_supabase(), user.model_dump())
            if not await check_user_subscription(data['bot'], user.id):
                if isinstance(event, CallbackQuery):
                    await event.answer()
                await target.answer('Kanal a’zoligini tasdiqlang:', reply_markup=subscribe_channel_kb)
                return
            await confirm_referral(user.id, data['bot'])
            return await handler(event, data)
        except CommerceError as exc:
            if isinstance(event, CallbackQuery):
                await event.answer()
            await target.answer(str(exc))


def build_dispatcher():
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(MembershipMiddleware())
    dp.callback_query.outer_middleware(MembershipMiddleware())
    dp.message.register(start_handler_local, CommandStart())

    @dp.callback_query(F.data == 'check_subscription')
    async def check_sub_callback(callback: CallbackQuery, bot: Bot, state: FSMContext):
        if not await check_user_subscription(bot, callback.from_user.id):
            await callback.answer('Hali kanalga a’zo bo‘lmadingiz.', show_alert=True)
            return
        try:
            await register(get_supabase(), callback.from_user.model_dump())
            await confirm_referral(callback.from_user.id, bot)
        except CommerceError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        action = (await state.get_data()).get('start_action')
        await state.clear()
        await callback.answer('A’zolik tasdiqlandi!')
        await callback.message.edit_reply_markup(reply_markup=None)
        if action == 'payment':
            await payment._payment_menu(callback, state)
        else:
            await show_welcome(callback.message)

    @dp.message(Command('help'))
    @dp.message(F.text == '🆘 Yordam')
    async def help_handler(message: Message, state: FSMContext):
        await state.clear()
        await message.answer('Yordam: @sardorbekuralov\n/start — menyu\n'
            'Takliflar va qolgan limitlar: 👤 Hisob va limitlar.', reply_markup=main_menu)

    @dp.message(F.text.in_({'💵 Narxlar', '📌 Foydalanish qoidalari'}))
    async def prices_handler(message: Message, state: FSMContext):
        await state.clear()
        await message.answer(POLICY_TEXT, reply_markup=access_keyboard)

    @dp.message(F.text.in_({'⬅️ Asosiy menyu', '/menu'}))
    async def back_to_main(message: Message, state: FSMContext):
        await state.clear()
        await message.answer('Asosiy menyu:', reply_markup=main_menu)

    @dp.message(F.text.in_({'📋 Obyektivka tayyorlash', 'Obyektivka tayyorlash'}))
    async def obyektivka_handler(message: Message, state: FSMContext):
        await state.clear()
        await message.answer('📋 Obyektivka tayyorlash:', reply_markup=obyektivka_link_kb)

    dp.include_router(admin.router)
    dp.include_router(access.router)
    dp.include_router(payment.router)
    dp.include_router(presentation.router)
    dp.include_router(referat.router)
    dp.include_router(course.router)
    fallback = Router()

    @fallback.callback_query()
    async def expired_button(callback: CallbackQuery):
        await callback.answer('Bu tugma eskirgan yoki buyurtma qabul qilingan. Menyudan qayta boshlang.', show_alert=True)

    dp.include_router(fallback)
    return dp


async def recover_reservations():
    while True:
        try:
            await rpc(get_supabase(), 'commerce_recover_expired')
        except CommerceError:
            logger.exception('Reservation recovery failed')
        await asyncio.sleep(60)


async def main():
    if os.getenv('BOT_TRANSPORT', 'polling').strip().lower() != 'polling':
        raise RuntimeError('Bot Telegram Serverless rejimida; polling servisini ishga tushirmang.')
    if not OPENROUTER_API_KEY:
        raise RuntimeError('OPENROUTER_API_KEY sozlanishi kerak')
    if not (os.getenv('BACKEND_URL') or os.getenv('MINI_APP_URL')):
        raise RuntimeError('Yangi mini ilova uchun BACKEND_URL yoki MINI_APP_URL kerak')
    # Missing migration/service credentials must fail before accepting orders.
    policy = await rpc(get_supabase(), 'commerce_policy')
    if policy.get('access_mode') != 'referral_only':
        raise RuntimeError('20261022_referral_only.sql migratsiyasini qo‘llang')
    await rpc(get_supabase(), 'commerce_recover_expired')
    bot = Bot(BOT_TOKEN)
    dp = build_dispatcher()
    app = web.Application()
    app.router.add_get('/', lambda request: web.json_response({'status': 'ok', 'service': 'orzu-bot'}))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', '8080'))).start()
    recovery = asyncio.create_task(recover_reservations())
    try:
        # Orzu is the sole Telegram update consumer. Never run the API webhook alongside it.
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        recovery.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await recovery
        await runner.cleanup()
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
