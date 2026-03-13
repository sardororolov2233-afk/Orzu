from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states import PresentationState
from keyboards import (
    main_menu, presentation_confirm_inline_kb, language_selection_kb, 
    template_selection_kb, presentation_mode_kb, presentation_img_confirm_kb,
    get_page_selection_kb
)
from database import save_user_profile, get_user_profile, get_user_balance, update_user_balance
from utils.ppt_doc import create_pptx_file
from utils.common import MAIN_MENU_COMMANDS
from utils.image_generator import get_image_path_from_description
import json
import asyncio
import logging
import shutil
from pathlib import Path
from services.ai_service import generate_presentation_data
from services.html_renderer import render_html
from services.pdf_generator import generate_pdf
from services.pptx_generator import generate_pptx

from services.pptx_generator import generate_pptx

# WebApp URL (.env dan yoki to'g'ridan-to'g'ri config dan olish mumkin)
import os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.web_app_info import WebAppInfo
WEBAPP_URL = os.getenv("FRONTEND_URL", "https://yordamchiai.vercel.app")

logger = logging.getLogger(__name__)

router = Router()

@router.message(F.text == "📊 Taqdimot yaratish")
async def presentation_start(message: Message, state: FSMContext):
    logger.info(f"Presentation start (WebApp) triggered by {message.from_user.id}")
    try:
        await state.clear()
        
        # Create inline keyboard with WebApp button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Yordamchi AI App", 
                web_app=WebAppInfo(url=WEBAPP_URL)
            )]
        ])
        
        await message.answer(
            "Yordamchi AI bilan taqdimot yarating 🚀\n\n"
            "Taqdimotingizni to'g'ridan-to'g'ri mini dasturimiz "
            "orqali qulay shaklda yaratishingiz mumkin. "
            "Quyidagi tugmani bosing:", 
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in presentation_start: {e}", exc_info=True)
        await message.answer("⚠️ Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")

