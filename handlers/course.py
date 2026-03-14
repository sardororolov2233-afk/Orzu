import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states import CourseWorkState
from keyboards import main_menu, course_confirm_inline_kb, course_edit_selection_kb, language_selection_kb, course_plan_approval_kb

from ai.brain import ask_ai, load_prompt, MODEL_SMART, MODEL_RESERVE
from database import save_user_profile, get_user_profile, get_user_balance, update_user_balance, log_user_action
from utils.course_doc import create_course_word_document
from utils.common import MAIN_MENU_COMMANDS

COURSE_PRICE = 15000

logger = logging.getLogger(__name__)

router = Router()

# Filter to check if user is in editing mode
async def is_editing(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    return data.get('editing') is True

# Interceptor Handler for text inputs during edit mode
@router.message(is_editing, F.state.in_({
    CourseWorkState.tema, CourseWorkState.sahifa, CourseWorkState.uslub,
    CourseWorkState.universitet, CourseWorkState.fakultet, CourseWorkState.muallif,
    CourseWorkState.kurs, CourseWorkState.guruh
}))
async def update_field_and_return(message: Message, state: FSMContext):
    current_state = await state.get_state()
    value = message.text
    
    if current_state == CourseWorkState.tema:
        await state.update_data(tema=value)
    elif current_state == CourseWorkState.sahifa:
        if not value.isdigit():
            await message.answer("❌ Iltimos, faqat raqam kiriting!")
            return
        await state.update_data(sahifa=int(value))
    elif current_state == CourseWorkState.uslub:
        await state.update_data(uslub=value)
    elif current_state == CourseWorkState.universitet:
        await state.update_data(universitet=value)
    elif current_state == CourseWorkState.fakultet:
        await state.update_data(fakultet=value)
    elif current_state == CourseWorkState.muallif:
        await state.update_data(muallif=value)
    elif current_state == CourseWorkState.kurs:
        await state.update_data(kurs=value)
    elif current_state == CourseWorkState.guruh:
        await state.update_data(guruh=value)
        
    # Reset editing flag
    await state.update_data(editing=False)
    
    # Save updated profile
    data = await state.get_data()
    # No need to combine kurs_guruh manually, save_user_profile handles separate fields now
    await save_user_profile(message.from_user.id, data)
    
    # Return to confirmation
    await show_course_confirmation(message, state)

async def generate_section(section_name: str, topic: str, plan: str, instructions: str, lang: str) -> str:
    """Helper to generate a single section using SMART model"""
    try:
        p = load_prompt("course/21_course_section.txt", 
                        topic=topic, 
                        plan=plan, 
                        section_name=section_name, 
                        volume="Detailed academic content (approx. 1000 words)",
                        instructions=instructions, 
                        language=lang)
        
        content = await ask_ai(p, model=MODEL_SMART)
        if not content:
            logger.error(f"Failed to generate content for section: {section_name}")
            return f"{section_name} bo'yicha ma'lumot topilmadi."
            
        # Remove title if AI added it
        clean_content = content.strip()
        if clean_content.lower().startswith(section_name.lower()):
            clean_content = clean_content[len(section_name):].strip()
            if clean_content.startswith(":") or clean_content.startswith("."):
                clean_content = clean_content[1:].strip()
                
        return clean_content
    except Exception as e:
        logger.error(f"Error generating section {section_name}: {e}")
        return "Texnik xatolik."

async def generate_full_course_work(topic: str, plan: str, lang: str, status_message: Message = None) -> str:
    """Kurs ishini 10 ta mikro-bo'limga bo'lib generatsiya qilish"""
    full_text = []
    
    # Mundarijani qatorlarga bo'lib, fasl nomlarini aniq ajratib olish
    plan_lines = [line.strip() for line in plan.split('\n') if line.strip()]
    
    # Fasl nomlarini filtrlab olish
    def get_section_title(prefix):
        for line in plan_lines:
            if line.startswith(prefix):
                return line
        return prefix

    async def update_status(text):
        if status_message:
            try:
                await status_message.edit_text(f"⏳ {text}\n\n(Jarayon 3-5 daqiqa davom etadi)")
            except:
                pass
    
    # 1. KIRISH (Yaxlit bitta so'rov)
    await update_status("Kirish qismi yozilmoqda...")
    
    # Yangi yaxlit promptni yuklaymiz
    p_intro = load_prompt("course/21_0_full_intro.txt", topic=topic, plan=plan)
    intro_content = await ask_ai(p_intro, model=MODEL_SMART)
    
    if intro_content:
        full_text.append(f"KIRISH\n\n{intro_content}")
    else:
        full_text.append("KIRISH\n\n(Kirish qismini yaratishda xatolik yuz berdi)")

    # 2. BOBLARNI GENERATSIYA QILISH (Xulosalarsiz)
    for i in range(1, 3): # I va II Boblar
        # Statik nomni olib tashlab, rejadagi aniq nomni olamiz
        bob_full_title = get_section_title(f"{i} BOB")
        if bob_full_title == f"{i} BOB": # Agar topilmasa, rim raqamini tekshiramiz
             bob_full_title = get_section_title("I BOB" if i==1 else "II BOB")
        
        full_text.append(f"\n\n{bob_full_title}")
        
        for j in range(1, 4): # 1.1, 1.2, 1.3 fasllar
            prefix = f"{i}.{j}."
            section_title = get_section_title(prefix) # Mundarijadagi asl nomni oladi
            
            if status_message:
                await status_message.edit_text(f"⏳ {section_title} kengaytirib yozilmoqda...")
            
            # AIga yuboriladigan kengaytirilgan promt
            p_fasl = load_prompt(f"course/22_{i}_chapter{i}_fasl{j}.txt", topic=topic, plan=plan)
            
            # AIga qat'iy yo'riqnoma qo'shish
            p_fasl += f""" 
            \n\nQAT'IY TIZIM BUYRUG'I (STRICT SYSTEM INSTRUCTION):
            
            Sizning yagona vazifangiz: "{topic}" mavzusining faqat va faqat "{section_title}" qismini yozish.
            
            TAQIQ (FORBIDDEN):
            ❌ Boshqa boblarga o'tib ketish.
            ❌ Umumiy gaplar bilan suvlarni ko'paytirish.
            ❌ Matnni "Ushbu bo'limda..." deb boshlash.
            ❌ Sarlavhani matn ichida qaytarish.
            ❌ Bob uchun xulosa yozish.
            
            TALAB (MANDATORY):
            ✅ Matn "{plan}" rejasiga 100% mos bo'lishi shart.
            ✅ Har bir fikr ilmiy asoslangan bo'lishi kerak.
            """
            
            # MUVOFIQLIK VA HAJM UCHUN QAT'IY BUYRUQ:
            p_fasl += f"""
            \n\nHAJM VA SIFAT NAZORATI:
            1. Minimal hajm: Ushbu faslning o'zi uchun kamida 2000-2500 so'z (4-5 to'liq sahifa) bo'lishi SHART.
            2. Ilmiy chuqurlik: Mavzuni yuzaki emas, tubdan tahlil qiling. Har bir fikrni kengaytirib yozing.
            3. Ma'lumotlar: Aniq faktlar, sanalar, olimlarning ismlari va nazariyalarni keltiring.
            4. Jadval: Agar imkoni bo'lsa, ma'lumotlarni tahlil qilish uchun Markdown jadval ishlating.
            
            O'zingizdan hech narsa to'qimang, faqat so'ralgan qismni yozing.
            """
            
            content = await ask_ai(p_fasl, model=MODEL_SMART)
            if content:
                full_text.append(f"\n{section_title}\n{content}") # Sarlavha Python tomonidan qo'shiladi
            else:
                full_text.append(f"\n{section_title}\n(Ma'lumot generatsiya qilishda xatolik yuz berdi)")

    # 3. UMUMIY XULOSA (Faqat bitta)
    if status_message:
        try:
            await status_message.edit_text("⏳ Yakuniy xulosa tayyorlanmoqda...")
        except:
            pass
    conclusion = await ask_ai(load_prompt("course/23_1_general_conclusion.txt", topic=topic, plan=plan), model=MODEL_SMART)
    full_text.append(f"\n\nXULOSA\n\n{conclusion}")
    
    # 5. ADABIYOTLAR RO'YXATI
    refs = await ask_ai(f"{topic} mavzusidagi kurs ishi uchun 15 ta ilmiy adabiyot ro'yxatini OTM standartida bering.", model=MODEL_SMART)
    full_text.append(f"\n\nFOYDALANILGAN ADABIYOTLAR RO'YXATI\n\n{refs}")

    full_raw_text = "\n\n".join(full_text)

    # 6. YAKUNIY NATIJA (Polishing olib tashlandi - sababi ma'lumot yo'qolishi)
    # Biz to'g'ridan-to'g'ri yig'ilgan matnni qaytaramiz.
    
    return full_raw_text

async def show_course_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('til', "O'zbek")
    
    text = (
        f"🌟 Ma'lumotlarni tekshiring:\n\n"
        f"KURS ISHI\n"
        f"Mavzu: {data.get('tema')}\n"
        f"Institut: {data.get('universitet')}\n"
        f"Fakultet: {data.get('fakultet')}\n"
        f"Muallif: {data.get('muallif')}\n"
        f"Kurs/Guruh: {data.get('kurs')} / {data.get('guruh')}\n"
        f"Sahifalar soni: {data.get('sahifa')}\n"
        f"Uslub: {data.get('uslub')}\n"
        f"Til: {lang}\n\n"
        f"• Tasdiqlash: \"✅ Tayyorlash\"\n"
        f"• Tahrirlash: \"✏️ O'zgartirish\"\n"
        f"• Bekor qilish: \"🚫 Rad etish\"\n"
    )
    try:
        await message.edit_text(text, reply_markup=course_confirm_inline_kb)
    except:
        await message.answer(text, reply_markup=course_confirm_inline_kb)
    await state.set_state(CourseWorkState.confirmation)

@router.message(F.text == "Kurs ishi")
async def start_course_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Iltimos, mavzuni kiriting:")
    await state.set_state(CourseWorkState.tema)

@router.message(CourseWorkState.tema)
async def get_tema(message: Message, state: FSMContext):
    await state.update_data(tema=message.text)
    
    # Check for existing profile data
    user_data = await get_user_profile(message.from_user.id)
    if user_data:
        # Get separate fields or split kurs_guruh if needed
        kurs = user_data.get('kurs')
        guruh = user_data.get('guruh')
        
        if not kurs and not guruh:
            kg = user_data.get('kurs_guruh', '')
            if kg:
                parts = kg.split()
                if len(parts) >= 1:
                    kurs = parts[0]
                if len(parts) >= 2:
                    guruh = " ".join(parts[1:])
        
        # Autofill everything but keep current tema
        await state.update_data(
            universitet=user_data.get('universitet'),
            fakultet=user_data.get('fakultet'),
            muallif=user_data.get('muallif'),
            kurs=kurs,
            guruh=guruh,
            uslub=user_data.get('uslub'),
            sahifa=user_data.get('sahifa'),
            til=user_data.get('til')
        )
        
        await show_course_confirmation(message, state)
    else:
        await message.answer("🔸 2️⃣ Sahifalar sonini kiriting (raqamda, masalan: 25):")
        await state.set_state(CourseWorkState.sahifa)

@router.message(CourseWorkState.sahifa, ~F.text.in_(MAIN_MENU_COMMANDS))
async def get_sahifa(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting!")
        return
    await state.update_data(sahifa=int(message.text))
    await message.answer("🔸 3️⃣ Yozilish uslubini kiriting (Masalan: Ilmiy):")
    await state.set_state(CourseWorkState.uslub)

@router.message(CourseWorkState.uslub, ~F.text.in_(MAIN_MENU_COMMANDS))
async def get_uslub(message: Message, state: FSMContext):
    await state.update_data(uslub=message.text)
    await message.answer("🔸 4️⃣ Universitet nomini kiriting:")
    await state.set_state(CourseWorkState.universitet)

@router.message(CourseWorkState.universitet, ~F.text.in_(MAIN_MENU_COMMANDS))
async def get_universitet(message: Message, state: FSMContext):
    await state.update_data(universitet=message.text)
    await message.answer("🔸 5️⃣ Fakultet nomini kiriting:")
    await state.set_state(CourseWorkState.fakultet)

@router.message(CourseWorkState.fakultet, ~F.text.in_(MAIN_MENU_COMMANDS))
async def get_fakultet(message: Message, state: FSMContext):
    await state.update_data(fakultet=message.text)
    await message.answer("🔸 6️⃣ Muallif ism-familiyasini kiriting:")
    await state.set_state(CourseWorkState.muallif)

@router.message(CourseWorkState.muallif, ~F.text.in_(MAIN_MENU_COMMANDS))
async def get_muallif(message: Message, state: FSMContext):
    await state.update_data(muallif=message.text)
    await message.answer("🔸 7️⃣ Kursingizni kiriting (masalan: 2-kurs):")
    await state.set_state(CourseWorkState.kurs)

@router.message(CourseWorkState.kurs, ~F.text.in_(MAIN_MENU_COMMANDS))
async def get_kurs(message: Message, state: FSMContext):
    await state.update_data(kurs=message.text)
    await message.answer("🔸 8️⃣ Guruhingizni kiriting (masalan: 204-guruh):")
    await state.set_state(CourseWorkState.guruh)

@router.message(CourseWorkState.guruh, ~F.text.in_(MAIN_MENU_COMMANDS))
async def get_guruh(message: Message, state: FSMContext):
    await state.update_data(guruh=message.text)
    await message.answer("🔸 9️⃣ Tilni tanlang:", reply_markup=language_selection_kb)
    await state.set_state(CourseWorkState.til)

@router.callback_query(CourseWorkState.til, F.data.startswith("lang_"))
async def get_til(callback: CallbackQuery, state: FSMContext):
    lang_map = {"lang_uz": "O'zbek", "lang_en": "Ingliz", "lang_ru": "Rus", "lang_fr": "Fransuz"}
    await state.update_data(til=lang_map.get(callback.data, "O'zbek"))
    await callback.message.delete()
    
    # Save to DB
    data = await state.get_data()
    data['kurs_guruh'] = f"{data.get('kurs', '')} {data.get('guruh', '')}".strip()
    await save_user_profile(callback.from_user.id, data)
    
    await show_course_confirmation(callback.message, state)

@router.callback_query(CourseWorkState.confirmation, F.data == "course_confirm")
async def start_course_generation(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # Check balance
    balance = await get_user_balance(user_id)
    if balance < COURSE_PRICE:
        await callback.answer(f"❌ Balansingizda mablag' yetarli emas!\nKerak: {COURSE_PRICE} so'm\nMavjud: {balance} so'm", show_alert=True)
        return

    await callback.message.delete()
    
    processing_msg = await callback.message.answer(
        f"⏳ AI Kurs ishingizni yozishni boshladi...\n"
        f"Bu jarayon 3-5 daqiqa vaqt oladi. Iltimos kuting.\n"
        f"<i>(Balansingizdan {COURSE_PRICE} so'm yechiladi)</i>",
        parse_mode="HTML"
    )

    # 1. Generate Plan
    await processing_msg.edit_text("⏳ Reja tuzilmoqda...")
    data = await state.get_data()
    lang = data.get('til', "O'zbek")
    
    prompt_plan = load_prompt("course/20_course_plan.txt", topic=data['tema'], pages=data['sahifa'], language=lang)
    plan_text = await ask_ai(prompt_plan, model=MODEL_SMART)
    
    if not plan_text:
        await processing_msg.edit_text("❌ Reja tuzishda xatolik.")
        return

    await state.update_data(plan=plan_text)
    await state.set_state(CourseWorkState.waiting_for_plan_approval)
    
    # Delete loading message before showing plan to keep chat clean
    await processing_msg.delete()
    
    await callback.message.answer(
        f"📝 <b>KURS ISHI REJASI:</b>\n\n{plan_text}\n\nRejani tasdiqlaysizmi?",
        reply_markup=course_plan_approval_kb,
        parse_mode="HTML"
    )

@router.callback_query(CourseWorkState.waiting_for_plan_approval, F.data == "course_plan_regenerate")
async def regenerate_course_plan(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔄 Yangi reja tuzilmoqda...")
    data = await state.get_data()
    lang = data.get('til', "O'zbek")
    
    prompt_plan = load_prompt("course/20_course_plan.txt", topic=data['tema'], pages=data['sahifa'], language=lang)
    plan_text = await ask_ai(prompt_plan, model=MODEL_SMART)
    
    if not plan_text:
        await callback.message.edit_text("❌ Reja tuzishda xatolik.")
        return

    await state.update_data(plan=plan_text)
    
    # Delete loading message before showing plan
    await callback.message.delete()
    
    await callback.message.answer(
        f"📝 <b>YANGI KURS ISHI REJASI:</b>\n\n{plan_text}\n\nRejani tasdiqlaysizmi?",
        reply_markup=course_plan_approval_kb,
        parse_mode="HTML"
    )

@router.callback_query(CourseWorkState.waiting_for_plan_approval, F.data == "course_plan_cancel")
async def cancel_course_plan(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("🚫 Bekor qilindi.", reply_markup=main_menu)
    await state.clear()

@router.callback_query(CourseWorkState.waiting_for_plan_approval, F.data == "course_plan_approve")
async def approve_course_plan(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    data = await state.get_data()
    
    loading_msg = await callback.message.answer("⏳ Asosiy qism yozilmoqda (bu 3-5 daqiqa vaqt oladi)...")
    
    lang = data.get('til', "O'zbek")
    plan_text = data.get('plan')
    
    course_text = await generate_full_course_work(data['tema'], plan_text, lang, status_message=loading_msg)
    
    # 3. Create Document
    kurs_guruh_str = f"{data.get('kurs', '')} {data.get('guruh', '')}"
    
    word_file = await asyncio.to_thread(
        create_course_word_document,
        tema=data['tema'],
        sahifa=data['sahifa'],
        uslub=data['uslub'],
        text=course_text,
        universitet=data.get('universitet', '-'),
        fakultet=data.get('fakultet', '-'),
        muallif=data.get('muallif', '-'),
        kurs_guruh=kurs_guruh_str,
        doc_type="KURS ISHI",
        plan=plan_text,
        user_id=callback.from_user.id
    )
    
    await loading_msg.delete()
    
    if word_file:
        user_id = callback.from_user.id
        # Deduct balance and log action
        await update_user_balance(user_id, -COURSE_PRICE)
        await log_user_action(user_id, 'course_work', amount=COURSE_PRICE)
        
        # Send document
        doc = FSInputFile(word_file)
        await callback.message.answer_document(document=doc, caption=f"🎓 {data['tema']}", reply_markup=main_menu)
    else:
        await callback.message.answer("❌ Fayl yaratishda xatolik.", reply_markup=main_menu)
    
    await state.clear()

@router.callback_query(CourseWorkState.confirmation, F.data == "course_cancel")
async def cancel_course(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("🚫 Bekor qilindi.", reply_markup=main_menu)
    await state.clear()

@router.callback_query(CourseWorkState.confirmation, F.data == "course_edit")
async def edit_course_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Qaysi ma'lumotni o'zgartirmoqchisiz?", reply_markup=course_edit_selection_kb)
    await state.set_state(CourseWorkState.edit_mode)

@router.callback_query(CourseWorkState.edit_mode)
async def edit_field_selected(callback: CallbackQuery, state: FSMContext):
    field_map = {
        "edit_course_tema": (CourseWorkState.tema, "Yangi mavzuni kiriting:"),
        "edit_course_sahifa": (CourseWorkState.sahifa, "Yangi sahifa sonini kiriting:"),
        "edit_course_uni": (CourseWorkState.universitet, "Yangi universitet nomini kiriting:"),
        "edit_course_fakultet": (CourseWorkState.fakultet, "Yangi fakultet nomini kiriting:"),
        "edit_course_muallif": (CourseWorkState.muallif, "Yangi muallifni kiriting:"),
        "edit_course_kurs": (CourseWorkState.kurs, "Yangi kursni kiriting (masalan: 2-kurs):"),
        "edit_course_guruh": (CourseWorkState.guruh, "Yangi guruhni kiriting (masalan: 204-guruh):"),
        "edit_course_uslub": (CourseWorkState.uslub, "Yangi uslubni kiriting:"),
    }
    
    if callback.data in field_map:
        new_state, prompt = field_map[callback.data]
        await state.set_state(new_state)
        await callback.message.answer(prompt)
        await state.update_data(editing=True)
    elif callback.data == "edit_course_lang":
        await state.set_state(CourseWorkState.til)
        await callback.message.answer("Tilni tanlang:", reply_markup=language_selection_kb)
        await state.update_data(editing=True)
    elif callback.data == "edit_course_back":
        await callback.message.delete()
        await show_course_confirmation(callback.message, state)
