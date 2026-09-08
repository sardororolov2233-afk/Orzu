from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

logger = logging.getLogger(__name__)

# Main menu commands to exclude from state handlers
MAIN_MENU_COMMANDS = [
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

