import logging

REFERAT_PRICE = 8000
import asyncio
import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states import ReferatState
from keyboards import (
    main_menu, referat_type_kb, referat_confirm_inline_kb, 
    referat_edit_selection_kb, language_selection_kb, 
    referat_plan_approval_kb, referat_tariff_kb
)
from utils.referat_doc import create_referat_document
from database import save_user_referat_data, get_user_referat_data, get_user_balance, update_user_balance, log_user_action
from ai.brain import ask_ai, load_prompt, MODEL_SMART, MODEL_RESERVE

router = Router()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# 1. Start Flow & Edit Interceptor
# ---------------------------------------------------------

# Filter to check if user is in editing mode
async def is_editing(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    return data.get('editing') is True

@router.message(F.text == "📄 Referat yaratish")
async def cmd_referat(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Iltimos mavzuni to'g'ri va qisqartirishlarsiz kiriting")
    await state.set_state(ReferatState.tema)

# Interceptor Handler for text inputs during edit mode
# This MUST be registered before normal state handlers to catch the edit flow
@router.message(is_editing, F.state.in_({
    ReferatState.tema, ReferatState.universitet, ReferatState.fakultet, 
    ReferatState.muallif, ReferatState.kurs_guruh, ReferatState.sahifa
}))
async def update_field_and_return(message: Message, state: FSMContext):
    # Update data based on state
    current_state = await state.get_state()
    value = message.text
    
    if current_state == ReferatState.tema:
        await state.update_data(tema=value)
    elif current_state == ReferatState.universitet:
        await state.update_data(universitet=value)
    elif current_state == ReferatState.fakultet:
        await state.update_data(fakultet=value)
    elif current_state == ReferatState.muallif:
        await state.update_data(muallif=value)
    elif current_state == ReferatState.kurs_guruh:
        await state.update_data(kurs_guruh=value)
    elif current_state == ReferatState.sahifa:
        if value.isdigit():
            await state.update_data(sahifa=int(value))
        else:
             await message.answer("Iltimos, faqat raqam yozing (masalan: 15).")
             return # Keep in edit mode for this field
    
    # Reset editing flag
    await state.update_data(editing=False)
    
    # Save updated profile
    new_data = await state.get_data()
    await save_user_referat_data(message.from_user.id, new_data)
    
    # Return to confirmation
    await show_confirmation(message, state)

@router.message(ReferatState.tema)
async def process_tema(message: Message, state: FSMContext):
    tema = message.text
    await state.update_data(tema=tema)
    
    # Ask for Document Type (Referat / Mustaqil Ish)
    await message.answer(
        "📄 Ish turini tanlang:\n"
        "(Bu titul varag'ida ko'rsatiladi)", 
        reply_markup=referat_type_kb
    )
    await state.set_state(ReferatState.ish_turi)

@router.callback_query(ReferatState.ish_turi)
async def process_ish_turi(callback: CallbackQuery, state: FSMContext):
    ish_turi = "REFERAT"
    if callback.data == "type_mustaqil":
        ish_turi = "MUSTAQIL ISH"
    
    await state.update_data(ish_turi=ish_turi)
    
    # Auto-fill check
    user_data = get_user_referat_data(callback.from_user.id)
    if user_data:
        # Fill data from DB
        await state.update_data(**user_data)
        # Go to confirmation
        await show_confirmation(callback.message, state)
    else:
        # Start data collection
        await callback.message.edit_text("🏛 O'qish joyingiz (Universitet) nomini yozing:")
        await state.set_state(ReferatState.universitet)

# ---------------------------------------------------------
# 2. Data Collection (if not auto-filled)
# ---------------------------------------------------------

@router.message(ReferatState.universitet)
async def process_uni(message: Message, state: FSMContext):
    await state.update_data(universitet=message.text)
    await message.answer("🏢 Fakultetingiz nomini yozing:")
    await state.set_state(ReferatState.fakultet)

@router.message(ReferatState.fakultet)
async def process_fakultet(message: Message, state: FSMContext):
    await state.update_data(fakultet=message.text)
    await message.answer("👤 Ish muallifi (Ism Familiya)ni yozing:")
    await state.set_state(ReferatState.muallif)

@router.message(ReferatState.muallif)
async def process_muallif(message: Message, state: FSMContext):
    await state.update_data(muallif=message.text)
    await message.answer("👨‍🎓 Kurs va guruhingizni yozing (masalan: 2-kurs, 204-guruh):")
    await state.set_state(ReferatState.kurs_guruh)

@router.message(ReferatState.kurs_guruh)
async def process_kurs_guruh(message: Message, state: FSMContext):
    await state.update_data(kurs_guruh=message.text)
    await message.answer("📄 Taxminan necha sahifa bo'lsin? (faqat raqam, masalan: 15)")
    await state.set_state(ReferatState.sahifa)

@router.message(ReferatState.sahifa)
async def process_sahifa(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam yozing (masalan: 15).")
        return
    
    await state.update_data(sahifa=int(message.text))
    await message.answer("🌐 Referat qaysi tilda yozilsin?", reply_markup=language_selection_kb)
    await state.set_state(ReferatState.til)

@router.callback_query(ReferatState.til)
async def process_lang(callback: CallbackQuery, state: FSMContext):
    lang_map = {
        "lang_uz": "O'zbek",
        "lang_en": "English",
        "lang_ru": "Русский",
        "lang_fr": "Français"
    }
    lang = lang_map.get(callback.data, "O'zbek")
    await state.update_data(til=lang)
    
    # Save to DB for future auto-fill
    data = await state.get_data()
    await save_user_referat_data(callback.from_user.id, data)
    
    await show_confirmation(callback.message, state)

# ---------------------------------------------------------
# 3. Confirmation & Editing
# ---------------------------------------------------------

async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    text, markup = get_confirmation_details(data)
    
    # Check if message is editable (from callback) or new (from text)
    try:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except:
        await message.answer(text, reply_markup=markup, parse_mode="HTML")
    
    await state.set_state(ReferatState.confirmation)

def get_confirmation_details(data):
    text = (
        f"📋 <b>MA'LUMOTLARNI TEKSHIRING:</b>\n\n"
        f"📝 <b>Mavzu:</b> {data.get('tema')}\n"
        f"📄 <b>Ish turi:</b> {data.get('ish_turi', 'REFERAT')}\n"
        f"🏛 <b>Universitet:</b> {data.get('universitet')}\n"
        f"🏢 <b>Fakultet:</b> {data.get('fakultet')}\n"
        f"👤 <b>Muallif:</b> {data.get('muallif')}\n"
        f"👨‍🎓 <b>Kurs/Guruh:</b> {data.get('kurs_guruh')}\n"
        f"📄 <b>Sahifa:</b> {data.get('sahifa')}\n"
        f"🌐 <b>Til:</b> {data.get('til')}\n\n"
        "Barchasi to'g'rimi?"
    )
    return text, referat_confirm_inline_kb

@router.callback_query(ReferatState.confirmation, F.data == "referat_cancel")
async def cancel_referat(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("🚫 Bekor qilindi.", reply_markup=main_menu)
    await state.clear()

@router.callback_query(ReferatState.confirmation, F.data == "referat_confirm")
async def ask_referat_tariff(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "<b>Ta'rifni tanlang:</b>\n\n"
        "🔹 <b>Oddiy</b> (8 000 so'm) - Standart sifatdagi referat yoki mustaqil ish.\n"
        "🔥 <b>PRO</b> (14 900 so'm) - Yuqori sifatli, chuqur tahliliy referat.",
        reply_markup=referat_tariff_kb,
        parse_mode="HTML"
    )
    await state.set_state(ReferatState.tariff_selection)

@router.callback_query(ReferatState.tariff_selection, F.data == "tariff_referat_back")
async def referat_tariff_back(callback: CallbackQuery, state: FSMContext):
    await show_confirmation(callback.message, state)

@router.callback_query(ReferatState.tariff_selection, F.data.in_({"ref_tariff_oddiy", "ref_tariff_pro"}))
async def start_plan_generation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.fromuser.id if hasattr(callback, 'fromuser') else callback.from_user.id
    
    price = 8000 if callback.data == "ref_tariff_oddiy" else 14900
    await state.update_data(tariff_price=price)
    
    # Check balance
    balance = await get_user_balance(user_id)
    if balance < price:
        await callback.answer(f"❌ Balansingizda mablag' yetarli emas!\nKerak: {price} so'm\nMavjud: {balance} so'm", show_alert=True)
        return

    await callback.message.edit_text("⏳ <b>REJA TUZILMOQDA...</b>\n\nIltimos kuting, bu 10-15 soniya vaqt olishi mumkin.", parse_mode="HTML")
    
    data = await state.get_data()
    lang = data.get('til', "O'zbek")
    topic = data.get('tema')
    
    prompt = load_prompt("referat/10_referat_plan.txt", topic=topic, language=lang)
    plan_text = await ask_ai(prompt, model=MODEL_SMART)
    
    if not plan_text:
        await callback.message.answer("❌ Reja tuzishda xatolik yuz berdi. Qaytadan urinib ko'ring.")
        return

    await state.update_data(plan=plan_text)
    
    # Save plan to DB for recovery
    current_data = await state.get_data()
    await save_user_referat_data(callback.from_user.id, current_data)
    
    await state.set_state(ReferatState.waiting_for_plan_approval)
    
    await callback.message.answer(
        f"📝 <b>REFERAT REJASI:</b>\n\n{plan_text}\n\nRejani tasdiqlaysizmi?", 
        reply_markup=referat_plan_approval_kb,
        parse_mode="HTML"
    )

@router.callback_query(ReferatState.confirmation, F.data == "referat_edit")
async def edit_referat_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Qaysi ma'lumotni o'zgartirmoqchisiz?", reply_markup=referat_edit_selection_kb)
    await state.set_state(ReferatState.edit_mode)

@router.callback_query(ReferatState.edit_mode)
async def edit_field_selected(callback: CallbackQuery, state: FSMContext):
    field_map = {
        "edit_referat_tema": (ReferatState.tema, "Yangi mavzuni kiriting:"),
        "edit_referat_sahifa": (ReferatState.sahifa, "Yangi sahifa sonini kiriting:"),
        "edit_referat_uni": (ReferatState.universitet, "Yangi universitet nomini kiriting:"),
        "edit_referat_fakultet": (ReferatState.fakultet, "Yangi fakultet nomini kiriting:"),
        "edit_referat_muallif": (ReferatState.muallif, "Yangi muallifni kiriting:"),
        "edit_referat_kurs_guruh": (ReferatState.kurs_guruh, "Yangi kurs va guruhni kiriting:"),
    }
    
    if callback.data in field_map:
        new_state, prompt = field_map[callback.data]
        await state.set_state(new_state)
        await callback.message.answer(prompt)
        # We need to know we are editing to return to confirmation
        await state.update_data(editing=True)
    elif callback.data == "edit_referat_ish_turi":
        await state.set_state(ReferatState.ish_turi)
        await callback.message.answer("📝 Ish turini tanlang:", reply_markup=referat_type_kb)
        await state.update_data(editing=True)
    elif callback.data == "edit_referat_lang":
        await state.set_state(ReferatState.til)
        await callback.message.answer("Tilni tanlang:", reply_markup=language_selection_kb)
        await state.update_data(editing=True)
    elif callback.data == "edit_referat_back":
        await show_confirmation(callback.message, state)

# ---------------------------------------------------------
# 4. Plan Generation & Approval
# ---------------------------------------------------------

@router.callback_query(ReferatState.waiting_for_plan_approval, F.data == "plan_regenerate")
async def regenerate_plan(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔄 Yangi reja tuzilmoqda...")
    data = await state.get_data()
    lang = data.get('til', "O'zbek")
    
    prompt = load_prompt("referat/10_referat_plan.txt", topic=data['tema'], language=lang)
    plan_text = await ask_ai(prompt)
    
    if not plan_text:
        await callback.message.answer("❌ Reja tuzishda xatolik.", reply_markup=main_menu)
        return

    await state.update_data(plan=plan_text)
    await callback.message.answer(
        f"📝 <b>YANGI REFERAT REJASI:</b>\n\n{plan_text}\n\nRejani tasdiqlaysizmi?", 
        reply_markup=referat_plan_approval_kb,
        parse_mode="HTML"
    )

@router.callback_query(ReferatState.waiting_for_plan_approval, F.data == "plan_cancel")
async def cancel_plan(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("🚫 Bekor qilindi.", reply_markup=main_menu)
    await state.clear()

# ---------------------------------------------------------
# 5. Content Generation (Approved Plan)
# ---------------------------------------------------------

@router.callback_query(ReferatState.waiting_for_plan_approval, F.data == "plan_approve")
async def generate_full_content(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Referat generation started for user {callback.from_user.id}")
    user_id = callback.from_user.id
    data = await state.get_data()
    price = data.get('tariff_price', REFERAT_PRICE)
    
    await callback.message.edit_text(
        f"Ishingiz tayyor bo'lishini kuting, taxminiy vaqt 5 daqiqa.\n"
        f"<i>(Balansingizdan {price} so'm yechiladi)</i>", 
        parse_mode="HTML"
    )
    
    plan = data.get('plan')
    tema = data.get('tema')
    lang = data.get('til', "O'zbek")
    
    # Deduct balance and log action
    await update_user_balance(user_id, -price)
    await log_user_action(user_id, 'referat', amount=price)

    # --- Logic Analysis & Improvement ---
    # User Feedback: Strict page calculation causes logical issues and poor quality.
    # Solution: Remove rigid "X pages" prompts. Rely on "Deep Academic Content" instructions.
    # Logic: 
    # 1. Intro (Comprehensive)
    # 2. Chapters (Detailed, no subsections, pure content)
    # 3. Conclusion (Summary)
    # 4. Refs (Standard)
    
    full_text = []
    
    # Helper for delay
    async def smart_delay():
        seconds = random.randint(2, 5)
        await asyncio.sleep(seconds)

    # Helper to generate section
    async def generate_section(section_name, instruction):
        try:
            p = load_prompt("referat/11_referat_section.txt", 
                            topic=tema, 
                            plan=plan, 
                            section_name=section_name, 
                            volume="Maximum academic depth and detail (approx. 1500-1800 words)",
                            instructions=instruction, 
                            language=lang)
            
            # Use SMART model for generation to ensure high quality
            content = await ask_ai(p, model=MODEL_SMART)
            
            if not content:
                logger.error(f"Failed to generate content for section: {section_name}")
                return "Ushbu qismni yaratishda xatolik yuz berdi."
                
            return content
        except Exception as e:
            logger.error(f"Error in generate_section ({section_name}): {e}")
            return "Texnik xatolik."

    # Helper to safe add section (Prevents Header Duplication)
    def format_section_safe(title, content):
        clean_content = content.strip()
        # Remove header if it exists at the start
        if clean_content.upper().startswith(title.upper()):
            clean_content = clean_content[len(title):].strip(" \n.:-")
        return f"{title}\n\n{clean_content}"

    # ---------------------------------------------------------
    # 2-BOSQICH: BOBLAR (Chapters)
    # Sarlavhani faqat AI matni bilan birga, bir marta qo'shing.
    # ---------------------------------------------------------
    
    chapters = ["I BOB", "II BOB", "III BOB"]
    
    for i, chapter_title in enumerate(chapters, 1):
        # Bob sarlavhasini qo'shamiz
        full_text.append(f"\n\n{chapter_title}")
        
        # Har bir bob ichidagi 3 ta faslni alohida so'ratamiz
        for sub in range(1, 2):
            sub_title = f"{i}.{sub}-fasl"
            instruction = (
                f"Mavzuni tahliliy yozing. Kamida 500-600 so'z bo'lsin.\n"
                f"Faqat {chapter_title}, {sub_title} haqida yozing."
            )
            
            # Har bir fasl uchun alohida AI so'rovi
            content = await generate_section(sub_title, instruction)
            
            # Sarlavhani (1.1-fasl) matn ichiga qo'shish
            full_text.append(f"\n{sub_title}\n{content}")
            
            # Delay after each subsection
            await smart_delay()

    # ---------------------------------------------------------
    # 3-BOSQICH: KIRISH va XULOSA (Alohida)
    # ---------------------------------------------------------
    
    # KIRISH
    intro = await generate_section("KIRISH", 
        "Write a strong, comprehensive introduction. Relevance, goals, tasks. No conclusion. No subsections. Content-rich without literary digressions.")
    full_text.insert(0, format_section_safe("KIRISH", intro))
    
    await smart_delay()
    
    # XULOSA
    # Sarlavhani faqat AI matni bilan birga, bir marta qo'shing
    conc = await generate_section("XULOSA", 
        "Write a comprehensive conclusion. Summarizing findings and suggestions. Do not repeat Intro. No subsections. Content-rich without literary digressions.")
    full_text.append(format_section_safe("XULOSA", conc))
    
    await smart_delay()
    
    # ADABIYOTLAR
    # Sarlavhani faqat AI matni bilan birga, bir marta qo'shing
    refs = await generate_section("FOYDALANILGAN ADABIYOTLAR", 
        "List 10-15 real sources in alphabetical order. No subsections. Content-rich without literary digressions.")
    full_text.append(format_section_safe("FOYDALANILGAN ADABIYOTLAR RO‘YXATI", refs))
    
    await smart_delay()

    final_text = "\n\n".join(full_text)
    
    # ---------------------------------------------------------
    # 4-BOSQICH: Finalizing
    # ---------------------------------------------------------
    
    # Note: We skip global rewriting to preserve the strict page count structure.
    # The sections were already generated with MODEL_SMART for high quality.
    
    await smart_delay()

    # Create Document
    
    word_file = await asyncio.to_thread(
        create_referat_document,
        tema=tema,
        sahifa=data.get('sahifa'),
        uslub=data.get('uslub', 'Akademik'),
        text=final_text,
        plan=plan, # Pass the plan for Page 2
        universitet=data.get('universitet', '-'),
        fakultet=data.get('fakultet', '-'),
        muallif=data.get('muallif', '-'),
        kurs_guruh=data.get('kurs_guruh', '-'),
        doc_type=data.get('ish_turi', 'REFERAT'),
        user_id=callback.from_user.id
    )
    
    if word_file:
        doc = FSInputFile(word_file)
        
        # Retry logic for sending document (handling network issues)
        sent_success = False
        for attempt in range(3):
            try:
                await callback.message.answer_document(document=doc, caption=f"📄 {tema}")
                sent_success = True
                break
            except Exception as e:
                logger.error(f"❌ Fayl yuborishda xatolik (Urinish {attempt+1}): {e}")
                await asyncio.sleep(3)
        
        if sent_success:
            try:
                await callback.message.answer("✅ Referat muvaffaqiyatli yakunlandi!", reply_markup=main_menu)
            except:
                pass # Ignore error on success message if doc is sent
        else:
            await callback.message.answer(
                "⚠️ Internet bilan aloqa yo'qolganligi sababli faylni yubora olmadim.\n"
                "Birozdan so'ng qayta urinib ko'ring yoki /start ni bosing."
            )
    else:
        await callback.message.answer("❌ Fayl yaratishda xatolik bo'ldi.", reply_markup=main_menu)
        
    await state.clear()

# ---------------------------------------------------------
# 6. Fallback / Expired Session
# ---------------------------------------------------------

# Handle expired sessions (when state is lost but user clicks buttons)
@router.callback_query(F.data.in_({"plan_approve", "plan_regenerate", "plan_cancel", "referat_confirm", "referat_edit", "referat_cancel", "ref_tariff_oddiy", "ref_tariff_pro", "tariff_referat_back"}))
async def handle_expired_session(callback: CallbackQuery, state: FSMContext):
    # Try to recover from DB
    user_data = get_user_referat_data(callback.from_user.id)
    
    if user_data and user_data.get('last_topic'):
        # Restore profile data
        await state.update_data(**user_data)
        
        # Restore crucial context
        if user_data.get('last_plan'):
             await state.update_data(plan=user_data['last_plan'])
             await state.update_data(tema=user_data['last_topic'])
        
        # Restore specific state based on button context (best effort)
        if callback.data in ["plan_approve", "plan_regenerate", "plan_cancel"]:
            await state.set_state(ReferatState.waiting_for_plan_approval)
        elif callback.data in ["referat_confirm", "referat_edit", "referat_cancel", "tariff_referat_back"]:
            await state.set_state(ReferatState.confirmation)
        elif callback.data in ["ref_tariff_oddiy", "ref_tariff_pro"]:
            await state.set_state(ReferatState.tariff_selection)
            
        await callback.message.answer(
            "🔄 <b>Sessiya qayta tiklandi!</b>\n\n"
            "Bot yangilangan bo'lishi mumkin. Iltimos, tugmani <b>QAYTA BOSING</b>.",
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.message.answer(
            "⚠️ Sessiya vaqti tugagan.\n"
            "Iltimos, /start buyrug'ini bosing va qaytadan boshlang."
        )
        await callback.answer()
