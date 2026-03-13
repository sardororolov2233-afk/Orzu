import sys
import logging
import asyncio
from pathlib import Path
from groq import AsyncGroq

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY topilmadi! .env faylni tekshiring.")
    client = None
else:
    client = AsyncGroq(api_key=GROQ_API_KEY)

def load_prompt(filename, **kwargs):
    """
    Prompts papkasidan faylni o'qiydi va formatlaydi.
    Avtomatik ravishda tizim va kontekst qoidalarini qo'shadi.
    """
    try:
        prompts_dir = Path(__file__).parent.parent / "prompts"
        
        # Load System Core and Context Rules
        system_core_path = prompts_dir / "00_system_core.txt"
        context_rules_path = prompts_dir / "01_context_rules.txt"
        
        system_content = ""
        context_content = ""
        
        if system_core_path.exists():
            # Standard synchronous reading is okay here as this is usually called once per request
            # and is very small. But we can keep it as is.
            with open(system_core_path, "r", encoding="utf-8") as f:
                system_content = f.read() + "\n\n"
                
        if context_rules_path.exists():
            with open(context_rules_path, "r", encoding="utf-8") as f:
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
                # IMPORTANT: Escaping curly braces in the content to avoid KeyError if the content itself
                # contains JSON-like structures that are not part of kwargs
                # But here we assume the prompt file uses {key} for formatting.
                # If there are literal { } in the file, they should be double {{ }} in the source file.
                main_content = main_content.format(**kwargs)
            except KeyError as e:
                logger.error(f"Prompt formatlashda kalit yetishmayapti: {e}")
                
        # Combine all parts
        final_prompt = f"{system_content}{context_content}TASK:\n{main_content}"
        return final_prompt
        
    except Exception as e:
        logger.error(f"Prompt yuklashda xatolik ({filename}): {e}")
        return ""

# Models
MODEL_SMART = "llama-3.3-70b-versatile"    # Asosiy model (Smart)
MODEL_RESERVE = "llama-3.1-70b-versatile"  # Zaxira model (Reserve)

async def ask_ai(prompt_text, model=MODEL_SMART, retries=3):
    """
    Groq API ga so'rov yuborish (Smart <-> Reserve Fallback mexanizmi bilan)
    Agar asosiy modelda limit tugasa yoki xatolik bo'lsa, avtomatik zaxira modelga o'tadi.
    """
    if not client:
        logger.error("Groq client mavjud emas")
        return None
        
    current_model = model
    
    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.5,
                max_tokens=8192
            )
            content = response.choices[0].message.content
            if content:
                return content
            else:
                logger.warning(f"Bo'sh javob qaytdi (Urinish {attempt + 1})")
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Groq API xatosi ({current_model}, Urinish {attempt + 1}): {e}")
            
            # Rate limit yoki Model Not Found (404) yoki Bad Request (400) xatolari
            # Agar model topilmasa yoki limit tugasa, zaxiraga o'tamiz
            should_switch = any(x in error_msg for x in ["rate limit", "too many requests", "429", "not found", "404", "model"])
            
            if should_switch:
                # Modelni almashtirish (Smart <-> Reserve)
                if current_model == MODEL_SMART:
                    logger.warning(f"⚠️ {MODEL_SMART} muammosi ({error_msg}). {MODEL_RESERVE} ga o'tilmoqda...")
                    current_model = MODEL_RESERVE
                    
                elif current_model == MODEL_RESERVE:
                    logger.warning(f"⚠️ {MODEL_RESERVE} muammosi ({error_msg}). {MODEL_SMART} ga qaytilmoqda...")
                    current_model = MODEL_SMART
                
                # Qisqa tanaffus va keyingi urinishda yangi model ishlatiladi
                await asyncio.sleep(1)
                continue
            
            # Boshqa jiddiy xatolar uchun biroz kutish
            await asyncio.sleep(2)
                
    return None
