"""One charge per Telegram confirmation message, with heartbeat and failure refund."""
import asyncio
import contextlib
from functools import wraps
import logging
from uuid import uuid5, NAMESPACE_URL
from commerce import rpc, CommerceError
from database import get_supabase
from keyboards import access_keyboard

logger = logging.getLogger(__name__)


async def heartbeat(user_id, request_id):
    while True:
        await asyncio.sleep(30)
        try:
            await rpc(get_supabase(), 'commerce_heartbeat', p_user_id=user_id, p_request_id=request_id)
        except CommerceError:
            logger.exception('Generation heartbeat failed')


def charged_generation(service):
    def decorate(handler):
        @wraps(handler)
        async def wrapped(callback, state, **kwargs):
            user_id = callback.from_user.id
            request_id = str(uuid5(NAMESPACE_URL,
                f"orzu:{service}:{user_id}:{callback.message.chat.id}:{callback.message.message_id}"))
            try:
                charge = await rpc(get_supabase(), 'commerce_reserve', p_user_id=user_id,
                    p_service=service, p_request_id=request_id)
            except CommerceError as exc:
                await callback.answer()
                await callback.message.answer(str(exc), reply_markup=access_keyboard)
                return
            if not charge['created']:
                await callback.answer('Bu buyurtma allaqachon qabul qilingan. Yangi ishni menyudan boshlang.', show_alert=True)
                return
            task = asyncio.create_task(heartbeat(user_id, request_id))
            try:
                await callback.answer()
                await state.set_state(f'{service}:generating')
                await state.update_data(generation_charge=charge, generation_request=request_id)
                await handler(callback, state, **kwargs)
            except BaseException as exc:
                # Cancellation also releases the reservation; durable recovery covers a lost process.
                refunded = False
                try:
                    await asyncio.shield(rpc(get_supabase(), 'commerce_finish', p_user_id=user_id,
                        p_request_id=request_id, p_success=False))
                    refunded = True
                except CommerceError:
                    logger.exception('Refund pending recovery for %s', request_id)
                if isinstance(exc, asyncio.CancelledError):
                    raise
                logger.exception('Document generation failed')
                note = 'Band qilingan kvota qaytarildi.' if refunded else 'Hisob tizimi tiklangach band qilingan kvota avtomatik qaytariladi.'
                await callback.message.answer('Ishni tayyorlash yakunlanmadi. ' + note +
                    ' Yangi buyurtmani menyudan boshlang.', reply_markup=access_keyboard)
            else:
                # A completed file must never be refunded merely because an acknowledgement failed.
                for attempt in range(3):
                    try:
                        await rpc(get_supabase(), 'commerce_finish', p_user_id=user_id,
                            p_request_id=request_id, p_success=True)
                        break
                    except CommerceError:
                        logger.exception('Could not finalize delivered document %s', request_id)
                        await asyncio.sleep(attempt + 1)
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                if (await state.get_data()).get('generation_request') == request_id:
                    await state.clear()
        return wrapped
    return decorate
