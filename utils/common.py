from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

logger = logging.getLogger(__name__)

# Main menu commands to exclude from state handlers
MAIN_MENU_COMMANDS = [
    "📄 Referat yaratish", 
    "📊 Taqdimot yaratish", 
    "Kurs ishi", 
    "💰 Tayyor ishlar", 
    "💳 Balans", 
    "🆘 Yordam",
    "/start",
    "/menu",
    "/presentation",
    "/ppt"
]

async def delete_last_bot_message(state: FSMContext, message: Message):
    """Oldingi bot xabarini o'chirish"""
    data = await state.get_data()
    last_msg_id = data.get("last_bot_msg_id")
    if last_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_msg_id)
        except Exception as e:
            logger.warning(f"Failed to delete message {last_msg_id}: {e}")
    await state.update_data(last_bot_msg_id=None)
