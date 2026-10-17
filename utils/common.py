from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

logger = logging.getLogger(__name__)


async def show_plan(message, title, plan, keyboard):
    """Long plans use plain text; AI markup cannot break Telegram HTML parsing."""
    text = f"📝 {title}\n\n{plan}\n\nRejani tasdiqlaysizmi?"
    chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)]
    for index, chunk in enumerate(chunks):
        await message.answer(chunk, reply_markup=keyboard if index == len(chunks) - 1 else None)

# Main menu commands to exclude from state handlers
MAIN_MENU_COMMANDS = [
    "🎁 Do‘stlarni taklif qilish", "👤 Hisob va limitlar", "📝 Maqola yaratish",
    "📋 Obyektivka tayyorlash",
    "Obyektivka tayyorlash",
    "📄 Referat yaratish", 
    "📊 Taqdimot yaratish", 
    "Kurs ishi", 
    "💰 Tayyor ishlar", 
    "💳 Hisobni to'ldirish", 
    "🆘 Yordam",
    "💵 Narxlar",
    "📝 Buyurtma asosida yaratish",
    "🎓 Bitiruv Malakaviy ishi",
    "🎨 Grafik dizayn tayyorlash",
    "/start",
    "/menu",
    "/presentation",
    "/ppt"
]

