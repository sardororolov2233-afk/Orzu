import logging
import asyncio
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states import CourseWorkState
from keyboards import main_menu, course_confirm_inline_kb, course_edit_selection_kb, language_selection_kb, course_plan_approval_kb, get_course_tariff_kb

from ai.brain import ask_ai, ask_ai_pro, load_prompt, load_raw_prompt, MODEL_SMART, MODEL_PRO
from database import save_user_profile, get_user_profile, get_user_balance, update_user_balance, log_user_action, has_used_promo, mark_promo_used
from utils.course_doc import create_course_word_document
from utils.common import MAIN_MENU_COMMANDS

COURSE_PRICE = 15000

logger = logging.getLogger(__name__)

router = Router()

# ═══════════════════════════════════════════════════════
# YORDAMCHI FUNKSIYALAR
# ═══════════════════════════════════════════════════════

async def is_editing(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    return data.get('editing') is True

def extract_chapters_from_plan(plan: str) -> dict:
    """
    Rejadagi fasl sonini dinamik aniqlash.
    Qaytaradi: {1: [fasl_nomlari], 2: [fasl_nomlari]}
    """
    chapters = {1: [], 2: []}
    lines = plan.split('\n')
    
    for line in lines:
        stripped = line.strip()
        # 1.1., 1.2., 1.3. kabi prefiks bilan boshlanuvchi qatorlar
        match = re.match(r'(\d+)\.(\d+)\.?\s+(.*)', stripped)
        if match:
            bob_num = int(match.group(1))
            fasl_title = stripped
            if bob_num in chapters:
                chapters[bob_num].append(fasl_title)
    
    # Agar hech narsa topilmasa, default 3 ta fasl
    if not chapters[1]:
        chapters[1] = ["1.1.", "1.2.", "1.3."]
    if not chapters[2]:
        chapters[2] = ["2.1.", "2.2.", "2.3."]
        
    return chapters

def generate_context_summary(section_name: str, content: str) -> str:
    """Fasl mazmunidan qisqa xulosa generatsiya qilish (kontekst chain uchun)"""
    # Matnning birinchi 500 so'zini olish va oxirini olish
    words = content.split()
    if len(words) > 150:
        summary = " ".join(words[:100]) + " ... " + " ".join(words[-50:])
    else:
        summary = content
    return f"[{section_name} xulosasi]: {summary}"

async def ai_request(prompt_text: str, is_pro: bool = False, **kwargs):
    """Tarif bo'yicha mos AI funksiyasini chaqirish"""
    if is_pro:
        return await ask_ai_pro(prompt_text, **kwargs)
    else:
        return await ask_ai(prompt_text, **kwargs)

async def polish_text(text: str, topic: str, language: str, is_pro: bool = False) -> str:
    """Matnni tahrirlash (polishing) — faqat PRO tarif uchun"""
    if not is_pro:
        return text
    
    try:
        polish_prompt = load_raw_prompt("course/24_derepeat_polish.txt", text=text, language=language)
        polished = await ai_request(polish_prompt, is_pro=is_pro)
        if polished and len(polished) > len(text) * 0.5:  # Matn juda qisqarmagan bo'lsa
            return polished
        else:
            logger.warning("Polishing natijasi juda qisqa, asl matn saqlanadi")
            return text
    except Exception as e:
        logger.error(f"Polishing xatosi: {e}")
        return text


# ═══════════════════════════════════════════════════════
# KURS ISHI GENERATSIYA — ASOSIY FUNKSIYA
# ═══════════════════════════════════════════════════════

async def generate_full_course_work(topic: str, plan: str, lang: str, is_pro: bool = False, status_message: Message = None) -> str:
    """
    Kurs ishini to'liq generatsiya qilish.
    
    PRO tarif:  DeepSeek R1T Chimera + Kontekst Chain + Polishing
    Oddiy tarif: Groq Llama 3.3 (hozirgi kabi)
    """
    full_text = []
    context_chain = []  # Oldingi fasllar xulosasi (C daraja: kontekst chain)
    
    # Mundarijadagi fasl nomlarini aniqlash
    plan_lines = [line.strip() for line in plan.split('\n') if line.strip()]
    
    # Dinamik fasl sonini aniqlash (C daraja)
    chapters = extract_chapters_from_plan(plan)
    total_sections = sum(len(sections) for sections in chapters.values())
    if total_sections == 0:
        total_sections = 6
        
    def get_section_title(prefix):
        for line in plan_lines:
            if line.startswith(prefix):
                return line
        return prefix

    # Til bo'yicha sarlavhalar
    if lang == "Русский":
        chap_prefixes = {1: "ГЛАВА I", 2: "ГЛАВА II"}
        intro_hdr = "ВВЕДЕНИЕ"
        conc_hdr = "ЗАКЛЮЧЕНИЕ"
        refs_hdr = "СПИСОК ИСПОЛЬЗОВАННОЙ ЛИТЕРАТУРЫ"
    elif lang in ("Ingliz", "English"):
        chap_prefixes = {1: "CHAPTER I", 2: "CHAPTER II"}
        intro_hdr = "INTRODUCTION"
        conc_hdr = "CONCLUSION"
        refs_hdr = "REFERENCES"
    else:
        chap_prefixes = {1: "I BOB", 2: "II BOB"}
        intro_hdr = "KIRISH"
        conc_hdr = "XULOSA"
        refs_hdr = "FOYDALANILGAN ADABIYOTLAR RO'YXATI"

    async def update_status(text):
        if status_message:
            try:
                tarif_label = "🔥 PRO" if is_pro else "🔹 Oddiy"
                await status_message.edit_text(f"⏳ {text}\n\n({tarif_label} tarif | Jarayon 3-7 daqiqa davom etadi)")
            except:
                pass
    
    # ═══════════════════════════════════════════
    # 1. KIRISH
    # ═══════════════════════════════════════════
    await update_status("Kirish qismi yozilmoqda...")
    
    p_intro = load_raw_prompt("course/21_0_full_intro.txt", topic=topic, plan=plan, language=lang)
    p_intro += """

MATN FORMATI VA ABZASLAR (MUHIM QOIDALAR):
- Matnni mayda bo'laklarga ajratmang, har bir gapni yangi abzasdan boshlamang! Qator tashlab ketma-ket abzatslar yozish TAQIQLANADI.
- Fasl boshida bitta abzasdan boshlang va butun matnni yaxlit bitta yoki ikkita juda yirik abzas shaklida, fikrlarni uzmasdan (bitta qatorda o'zaro bog'lab, davom ettirib) yozing.
- Faqatgina rasm yoki jadval (table) kiritilgandan keyingina yangi abzasdan boshlashingiz mumkin.
- Matn orasida aslo snoska (footnote) yoki adabiyotga havola (masalan, [1], (Ivanov, 2020) va hokazo) qoldirmang! Barcha adabiyotlar faqatgina ishning eng oxirida "Foydalanilgan adabiyotlar" ro'yxatida yoziladi. Matn ichini toza saqlang.
"""
    intro_content = await ai_request(p_intro, is_pro=is_pro)
    
    if intro_content:
        full_text.append(f"{intro_hdr}\n\n{intro_content}")
        context_chain.append(generate_context_summary("KIRISH", intro_content))
    else:
        full_text.append(f"{intro_hdr}\n\n(Xatolik yuz berdi)")

    # ═══════════════════════════════════════════
    # 2. BOBLARNI GENERATSIYA QILISH (Kontekst Chain bilan)
    # ═══════════════════════════════════════════
    for i in range(1, 3):  # I va II Boblar
        bob_roman = chap_prefixes[i]
        bob_alt = bob_roman.replace("I", "1").replace("II", "2")
        
        bob_full_title = get_section_title(bob_roman)
        if bob_full_title == bob_roman:
            bob_full_title = get_section_title(bob_alt)
            if bob_full_title == bob_alt:
                bob_full_title = bob_roman
        
        full_text.append(f"\n\n{bob_full_title}")
        
        # Dinamik fasl soni (C daraja)
        chapter_sections = chapters.get(i, ["default"])
        num_sections = len(chapter_sections)
        
        for j in range(1, num_sections + 1):
            prefix = f"{i}.{j}."
            section_title = get_section_title(prefix)
            
            await update_status(f"{section_title} kengaytirib yozilmoqda...")
            
            # Oldingi fasllar kontekstini tayyorlash (C daraja: Context Chain)
            if context_chain:
                previous_context = "OLDINGI FASLLAR KONTEKSTI (takrorlamasdan, davom ettiring):\n" + "\n".join(context_chain[-3:])  # Oxirgi 3 ta fasl
            else:
                previous_context = ""
            
            # Fasl promptini yuklash
            prompt_file = f"course/22_{i}_chapter{i}_fasl{j}.txt"
            p_fasl = load_raw_prompt(prompt_file, topic=topic, plan=plan, language=lang, previous_context=previous_context)
            
            # Agar prompt fayl topilmasa (dinamik fasllar uchun), umumiy promptni ishlatish
            if not p_fasl:
                p_fasl = load_raw_prompt("course/21_course_section.txt", 
                    topic=topic, plan=plan, section_name=section_title,
                    volume="Kamida 2500 so'z (6 bet)",
                    instructions="Ilmiy akademik uslubda chuqur tahlil bilan yozing.",
                    language=lang)
            
            # Qat'iy ko'rsatma qo'shish
            p_fasl += f""" 

QAT'IY TIZIM BUYRUG'I (STRICT SYSTEM INSTRUCTION):

Sizning yagona vazifangiz: "{topic}" mavzusining faqat va faqat "{section_title}" qismini yozish.

TAQIQ (FORBIDDEN):
❌ Boshqa boblarga o'tib ketish.
❌ Umumiy gaplar bilan suvlarni ko'paytirish.
❌ Matnni "Ushbu bo'limda..." deb boshlash.
❌ Sarlavhani matn ichida qaytarish.
❌ Bob uchun xulosa yozish (agar 2.3 yoki 1.3 fasl bo'lmasa).

TALAB (MANDATORY):
✅ Matn "{plan}" rejasiga 100% mos bo'lishi shart.
✅ Har bir fikr ilmiy asoslangan bo'lishi kerak.
✅ Asosiy matn majburiy ravishda quyidagi tilda yozilishi shart: {lang}
"""
            
            p_fasl += f"""

HAJM VA SIFAT NAZORATI:
1. Minimal hajm: Kamida 2500 so'z (6 to'liq sahifa) bo'lishi SHART. Chuqur tahlil qiling.

MATN FORMATI, ABZASLAR VA IQTIBOSLAR (QAT'IY QOIDALAR):
- Matnni mayda bo'laklarga ajratmang, har bir yangi gapni yangi abzasdan (qator tashlab) boshlamang! 
- Fasl boshida bitta abzasdan boshlang va butun matnni yaxlit bir necha yirik qismlari shaklida, fikrlarni uzmasdan (yangi fikrni ham uzluksiz, abzasni davomidan) yozib keting.
- Faqatgina jadval kiritilgandan keyingina yangi abzasdan boshlashga ruxsat etiladi. Qolgan holatlarda yirik bloklar shaklida, ilmiy tekstni davom ettirib yozing.
- MATN ORASIGA SNOSKA (FOOTNOTE) VA ADABIYOT MANBALARINI ASLO KIRITMANG. Hech qanday [1], (Ahmedov, 2021) ko'rinishidagi ishoralarni yozmang! Barcha adabiyotlar faqat asosiy ishning eng oxirida yoziladi.
"""
            
            content = await ai_request(p_fasl, is_pro=is_pro)
            
            if content:
                full_text.append(f"\n{section_title}\n{content}")
                # Kontekst chainni yangilash
                context_chain.append(generate_context_summary(section_title, content))
            else:
                full_text.append(f"\n{section_title}\n(Ma'lumot generatsiya qilishda xatolik yuz berdi)")

    # ═══════════════════════════════════════════
    # 3. UMUMIY XULOSA
    # ═══════════════════════════════════════════
    await update_status("Yakuniy xulosa tayyorlanmoqda...")
    
    # Xulosa uchun barcha fasllar kontekstini uzatish
    conclusion_context = ""
    if context_chain:
        conclusion_context = "BARCHA BOBLAR XULOSASI (umumlashtiring):\n" + "\n".join(context_chain)
    
    conclusion_prompt = load_raw_prompt("course/23_1_general_conclusion.txt", 
        topic=topic, plan=plan, language=lang, previous_context=conclusion_context)
    
    conclusion_prompt += """

MATN FORMATI VA ABZASLAR (MUHIM QOIDALAR):
- Matnni mayda bo'laklarga ajratib, har bir fikrni yangi qatordan boshlamang!
- Butun xulosani yaxlit, uzluksiz tekst sifatida davom ettirib yozing. Matn orasida aslo snoska yoki adabiyot manbalarini ko'rsatmang!
"""
    
    conclusion = await ai_request(conclusion_prompt, is_pro=is_pro)
    
    if conclusion:
        full_text.append(f"\n\n{conc_hdr}\n\n{conclusion}")
    else:
        full_text.append(f"\n\n{conc_hdr}\n\n(Xatolik yuz berdi)")
    
    # ═══════════════════════════════════════════
    # 4. ADABIYOTLAR RO'YXATI
    # ═══════════════════════════════════════════
    await update_status("Adabiyotlar ro'yxati tuzilmoqda...")
    
    ref_prompt = load_raw_prompt("course/25_references.txt", topic=topic, language=lang)
    if not ref_prompt:
        # Fallback: agar yangi prompt topilmasa
        ref_prompt = f"Provide a list of 20 academic references for the course work topic: '{topic}' formatted in standard OTM citation style. The references must be aligned with the {lang} language context. Include at least 4-5 textbooks, 3-4 journal articles, 2-3 laws, and 3-4 foreign language sources. Format each reference properly with author, title, publisher, year, and pages."
    
    refs = await ai_request(ref_prompt, is_pro=is_pro)
    full_text.append(f"\n\n{refs_hdr}\n\n{refs}")

    full_raw_text = "\n\n".join(full_text)

    return full_raw_text


# ═══════════════════════════════════════════════════════
# HANDLER FUNKSIYALAR
# ═══════════════════════════════════════════════════════

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
        
    await state.update_data(editing=False)
    
    data = await state.get_data()
    await save_user_profile(message.from_user.id, data)
    
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
            
        clean_content = content.strip()
        if clean_content.lower().startswith(section_name.lower()):
            clean_content = clean_content[len(section_name):].strip()
            if clean_content.startswith(":") or clean_content.startswith("."):
                clean_content = clean_content[1:].strip()
                
        return clean_content
    except Exception as e:
        logger.error(f"Error generating section {section_name}: {e}")
        return "Texnik xatolik."


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
    
    user_data = await get_user_profile(message.from_user.id)
    if user_data:
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
    
    data = await state.get_data()
    data['kurs_guruh'] = f"{data.get('kurs', '')} {data.get('guruh', '')}".strip()
    await save_user_profile(callback.from_user.id, data)
    
    await show_course_confirmation(callback.message, state)

@router.callback_query(CourseWorkState.confirmation, F.data == "course_confirm")
async def ask_course_tariff(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    has_promo = data.get('has_active_promo', False)
    
    msg_text = (
        "<b>Ta'rifni tanlang:</b>\n\n"
        "🔹 <b>Oddiy</b> (15 000 so'm) - Standart sifatdagi kurs ishi.\n"
        "🔥 <b>PRO</b> (29 900 so'm) - Yuqori sifatli, chuqur tahliliy va ilmiy akademik kurs ishi.\n\n"
        "<i>PRO tarif afzalliklari:</i>\n"
        "• 🧠 DeepSeek R1T Chimera — kuchli AI model\n"
        "• 🔗 Fasllar o'rtasida kontekst aloqasi\n"
        "• ✨ Professional tahrirlash (polishing)\n"
        "• 📊 Chuqurroq tahlil va ko'proq manbalar"
    )
    if has_promo:
        msg_text += "\n\n🎁 <i>Sizda 50% lik chegirma faollashtirilgan!</i>"
        
    await callback.message.edit_text(
        msg_text,
        reply_markup=get_course_tariff_kb(has_promo),
        parse_mode="HTML"
    )
    await state.set_state(CourseWorkState.tariff_selection)

@router.callback_query(CourseWorkState.tariff_selection, F.data == "course_promo")
async def ask_course_promo_code(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎁 <b>Promo-kodni kiriting:</b>", parse_mode="HTML")
    await state.set_state(CourseWorkState.promo)

@router.message(CourseWorkState.promo)
async def process_course_promo_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    
    if code == "PROMO50":
        if await has_used_promo(user_id, "PROMO50"):
            await message.answer("❌ Siz bu promo-koddan allaqachon foydalangansiz.")
            await show_course_confirmation(message, state)
        else:
            await state.update_data(has_active_promo=True, promo_code="PROMO50")
            await message.answer("✅ Promo-kod qabul qilindi! Sizga 50% chegirma taqdim etildi.")
            
            data = await state.get_data()
            has_promo = data.get('has_active_promo', False)
            msg_text = (
                "<b>Ta'rifni tanlang:</b>\n\n"
                "🔹 <b>Oddiy</b> (15 000 so'm) - Standart sifatdagi kurs ishi.\n"
                "🔥 <b>PRO</b> (29 900 so'm) - Yuqori sifatli, chuqur tahliliy va ilmiy akademik kurs ishi.\n\n"
                "🎁 <i>Sizda 50% lik chegirma faollashtirilgan!</i>"
            )
            await message.answer(msg_text, reply_markup=get_course_tariff_kb(has_promo), parse_mode="HTML")
            await state.set_state(CourseWorkState.tariff_selection)
    else:
        await message.answer("❌ Noto'g'ri promo-kod kiritildi.")
        await show_course_confirmation(message, state)

@router.callback_query(CourseWorkState.tariff_selection, F.data == "tariff_course_back")
async def course_tariff_back(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await show_course_confirmation(callback.message, state)

@router.callback_query(CourseWorkState.tariff_selection, F.data.in_({"course_tariff_oddiy", "course_tariff_pro"}))
async def start_course_generation(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    is_pro = callback.data == "course_tariff_pro"
    base_price = 29900 if is_pro else 15000
    
    data = await state.get_data()
    has_promo = data.get('has_active_promo', False)
    price = int(base_price * 0.5) if has_promo else base_price
    
    await state.update_data(tariff_price=price, is_pro=is_pro)
    
    # Check balance
    balance = await get_user_balance(user_id)
    if balance < price:
        await callback.answer(f"❌ Balansingizda mablag' yetarli emas!\nKerak: {price} so'm\nMavjud: {balance} so'm", show_alert=True)
        return

    await callback.message.delete()
    
    tarif_label = "🔥 PRO (DeepSeek R1T Chimera)" if is_pro else "🔹 Oddiy (Groq Llama)"
    processing_msg = await callback.message.answer(
        f"⏳ AI Kurs ishingizni yozishni boshladi...\n"
        f"Tarif: {tarif_label}\n"
        f"Bu jarayon {'5-8' if is_pro else '3-5'} daqiqa vaqt oladi. Iltimos kuting.\n"
        f"<i>(Balansingizdan {price} so'm yechiladi)</i>",
        parse_mode="HTML"
    )

    # 1. Generate Plan
    await processing_msg.edit_text("⏳ Reja tuzilmoqda...")
    data = await state.get_data()
    lang = data.get('til', "O'zbek")
    
    prompt_plan = load_raw_prompt("course/20_course_plan.txt", topic=data['tema'], pages=data['sahifa'], language=lang)
    plan_text = await ai_request(prompt_plan, is_pro=is_pro)
    
    if not plan_text:
        await processing_msg.edit_text("❌ Reja tuzishda xatolik.")
        return

    await state.update_data(plan=plan_text)
    await state.set_state(CourseWorkState.waiting_for_plan_approval)
    
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
    is_pro = data.get('is_pro', False)
    
    prompt_plan = load_raw_prompt("course/20_course_plan.txt", topic=data['tema'], pages=data['sahifa'], language=lang)
    plan_text = await ai_request(prompt_plan, is_pro=is_pro)
    
    if not plan_text:
        await callback.message.edit_text("❌ Reja tuzishda xatolik.")
        return

    await state.update_data(plan=plan_text)
    
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
    is_pro = data.get('is_pro', False)
    
    tarif_label = "🔥 PRO" if is_pro else "🔹 Oddiy"
    loading_msg = await callback.message.answer(
        f"⏳ Asosiy qism yozilmoqda ({tarif_label} tarif)...\n"
        f"Bu {'5-8' if is_pro else '3-5'} daqiqa vaqt oladi..."
    )
    
    lang = data.get('til', "O'zbek")
    plan_text = data.get('plan')
    
    course_text = await generate_full_course_work(
        data['tema'], plan_text, lang, 
        is_pro=is_pro, 
        status_message=loading_msg
    )
    
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
        user_id=callback.from_user.id,
        is_pro=is_pro
    )
    
    await loading_msg.delete()
    
    if word_file:
        user_id = callback.from_user.id
        price = data.get('tariff_price', COURSE_PRICE)
        await update_user_balance(user_id, -price)
        await log_user_action(user_id, 'course_work', amount=price)
        
        if data.get('has_active_promo') and data.get('promo_code'):
            await mark_promo_used(user_id, data['promo_code'])
            await state.update_data(has_active_promo=False, promo_code=None)
        
        doc = FSInputFile(word_file)
        await callback.message.answer_document(document=doc, caption=f"🎓 {data['tema']}")
        
        quality_msg = "🔥 PRO sifat — DeepSeek R1T Chimera modeli bilan yaratildi" if is_pro else "✅ Standart sifat"
        await callback.message.answer(
            f"✅ Kurs ishi muvaffaqiyatli yakunlandi!\n{quality_msg}\n\n"
            f"Tanlovingiz uchun minnadormiz. Agar ushbu ishni yanada professional darajada qabul qilmoqchi bo'lsangiz mutahasislarimizga murojat qiling: @sardorbekuralov", 
            reply_markup=main_menu
        )
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
