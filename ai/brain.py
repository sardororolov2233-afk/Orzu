import sys
import logging
import asyncio
from pathlib import Path
from groq import AsyncGroq
from openai import AsyncOpenAI

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import GROQ_API_KEY, OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# GROQ CLIENT (Oddiy tarif uchun)
# ═══════════════════════════════════════════════════════
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY topilmadi! .env faylni tekshiring.")
    groq_client = None
else:
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# ═══════════════════════════════════════════════════════
# OPENROUTER CLIENT (PRO tarif uchun — DeepSeek R1-0528)
# ═══════════════════════════════════════════════════════
if not OPENROUTER_API_KEY:
    logger.warning("OPENROUTER_API_KEY topilmadi! PRO tarif ishlamaydi.")
    openrouter_client = None
else:
    openrouter_client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

# ═══════════════════════════════════════════════════════
# MODEL KONSTANTALARI
# ═══════════════════════════════════════════════════════
MODEL_SMART = "llama-3.3-70b-versatile"           # Oddiy tarif (Groq)
MODEL_RESERVE = "llama-3.1-70b-versatile"          # Zaxira model (Groq)
MODEL_PRO = "deepseek/deepseek-r1-0528"              # PRO tarif (OpenRouter)

def load_prompt(filename, **kwargs):
    """
    Prompts papkasidan faylni o'qiydi va formatlaydi.
    System Core va Context Rules alohida qaytariladi (system_content sifatida).
    """
    try:
        prompts_dir = Path(__file__).parent.parent / "prompts"
        
        # Load System Core and Context Rules
        # Check if there's a course-specific system core
        course_system_path = prompts_dir / "course" / "00_system_core.txt"
        general_system_path = prompts_dir / "00_system_core.txt"
        context_rules_path = prompts_dir / "course" / "01_context_rules.txt"
        general_context_path = prompts_dir / "01_context_rules.txt"
        
        system_content = ""
        context_content = ""
        
        # Prefer course-specific system core if loading course prompts
        if filename.startswith("course/"):
            if course_system_path.exists():
                with open(course_system_path, "r", encoding="utf-8") as f:
                    system_content = f.read() + "\n\n"
            if context_rules_path.exists():
                with open(context_rules_path, "r", encoding="utf-8") as f:
                    context_content = f.read() + "\n\n"
        else:
            if general_system_path.exists():
                with open(general_system_path, "r", encoding="utf-8") as f:
                    system_content = f.read() + "\n\n"
            if general_context_path.exists():
                with open(general_context_path, "r", encoding="utf-8") as f:
                    context_content = f.read() + "\n\n"
        
        # Load Main Prompt
        path = prompts_dir / filename
        if not path.exists():
            logger.error(f"Prompt fayli topilmadi: {path}")
            return ""
            
        with open(path, "r", encoding="utf-8") as f:
            main_content = f.read()
            
        # Agar kwargs bo'lsa, formatlash
        if kwargs:
            try:
                main_content = main_content.format(**kwargs)
            except KeyError as e:
                logger.error(f"Prompt formatlashda kalit yetishmayapti: {e}")
                
        # Combine all parts
        final_prompt = f"{system_content}{context_content}TASK:\n{main_content}"
        return final_prompt
        
    except Exception as e:
        logger.error(f"Prompt yuklashda xatolik ({filename}): {e}")
        return ""

def load_system_prompt():
    """System roleni alohida yuklash (system message uchun)"""
    try:
        prompts_dir = Path(__file__).parent.parent / "prompts"
        course_system_path = prompts_dir / "course" / "00_system_core.txt"
        context_rules_path = prompts_dir / "course" / "01_context_rules.txt"
        
        system_content = ""
        if course_system_path.exists():
            with open(course_system_path, "r", encoding="utf-8") as f:
                system_content = f.read()
        if context_rules_path.exists():
            with open(context_rules_path, "r", encoding="utf-8") as f:
                system_content += "\n\n" + f.read()
        
        return system_content
    except Exception as e:
        logger.error(f"System prompt yuklashda xatolik: {e}")
        return ""

def load_raw_prompt(filename, **kwargs):
    """
    Faqat prompt faylini o'qiydi, system core qo'shmasdan.
    Bu system/user role ajratish uchun ishlatiladi.
    """
    try:
        prompts_dir = Path(__file__).parent.parent / "prompts"
        path = prompts_dir / filename
        if not path.exists():
            logger.error(f"Prompt fayli topilmadi: {path}")
            return ""
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if kwargs:
            try:
                content = content.format(**kwargs)
            except KeyError as e:
                logger.error(f"Prompt formatlashda kalit yetishmayapti: {e}")
                
        return content
    except Exception as e:
        logger.error(f"Raw prompt yuklashda xatolik ({filename}): {e}")
        return ""


# ═══════════════════════════════════════════════════════
# ODDIY TARIF — Groq API (ask_ai)
# ═══════════════════════════════════════════════════════
async def ask_ai(prompt_text, model=MODEL_SMART, retries=3, temperature=0.5, max_tokens=8192):
    """
    Groq API ga so'rov yuborish (Oddiy tarif uchun).
    System/User rollarini ajratib yuboradi.
    """
    if not groq_client:
        logger.error("Groq client mavjud emas")
        return None
        
    current_model = model
    system_prompt = load_system_prompt()
    
    for attempt in range(retries):
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt_text})
            
            response = await groq_client.chat.completions.create(
                model=current_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            if content:
                return content
            else:
                logger.warning(f"Bo'sh javob qaytdi (Urinish {attempt + 1})")
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Groq API xatosi ({current_model}, Urinish {attempt + 1}): {e}")
            
            should_switch = any(x in error_msg for x in ["rate limit", "too many requests", "429", "not found", "404", "model"])
            
            if should_switch:
                if current_model == MODEL_SMART:
                    logger.warning(f"⚠️ {MODEL_SMART} muammosi. {MODEL_RESERVE} ga o'tilmoqda...")
                    current_model = MODEL_RESERVE
                elif current_model == MODEL_RESERVE:
                    logger.warning(f"⚠️ {MODEL_RESERVE} muammosi. {MODEL_SMART} ga qaytilmoqda...")
                    current_model = MODEL_SMART
                
                await asyncio.sleep(1)
                continue
            
            await asyncio.sleep(2)
                
    return None


# ═══════════════════════════════════════════════════════
# PRO TARIF — OpenRouter API (ask_ai_pro) — DeepSeek R1-0528
# ═══════════════════════════════════════════════════════
async def ask_ai_pro(prompt_text, model=MODEL_PRO, retries=3, temperature=0.3, max_tokens=16384):
    """
    OpenRouter API ga so'rov yuborish (PRO tarif uchun).
    DeepSeek R1-0528 — advanced reasoning model.
    System/User rollarini ajratib yuboradi.
    """
    if not openrouter_client:
        logger.error("OpenRouter client mavjud emas. OPENROUTER_API_KEY ni tekshiring.")
        # Fallback to Groq
        logger.warning("PRO model mavjud emas, Groq ga fallback qilinmoqda...")
        return await ask_ai(prompt_text, temperature=temperature, max_tokens=max_tokens)
    
    system_prompt = load_system_prompt()
    
    for attempt in range(retries):
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt_text})
            
            response = await openrouter_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_headers={
                    "HTTP-Referer": "https://t.me/acadai_bot",
                    "X-Title": "AcadAI Telegram Bot"
                }
            )
            
            content = response.choices[0].message.content
            
            # DeepSeek R1-0528 <think>...</think> taglarini tozalash
            if content and "<think>" in content:
                import re
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            if content:
                return content
            else:
                logger.warning(f"PRO: Bo'sh javob qaytdi (Urinish {attempt + 1})")
                
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"OpenRouter API xatosi ({model}, Urinish {attempt + 1}): {e}")
            
            if attempt == retries - 1:
                # Oxirgi urinishda Groq ga fallback
                logger.warning("PRO model muvaffaqiyatsiz. Groq ga fallback...")
                return await ask_ai(prompt_text, temperature=0.5, max_tokens=8192)
            
            await asyncio.sleep(2)
    
    # Agar barcha urinishlar muvaffaqiyatsiz bo'lsa — Groq fallback
    logger.warning("PRO model barcha urinishlardan o'tmadi. Groq fallback...")
    return await ask_ai(prompt_text, temperature=0.5, max_tokens=8192)
