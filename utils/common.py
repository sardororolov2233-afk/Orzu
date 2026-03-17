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

