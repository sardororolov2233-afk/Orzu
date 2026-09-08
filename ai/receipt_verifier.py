import os
import json
import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from database import is_receipt_duplicate

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TARGET_CARD_LAST4 = "4623"
TARGET_CARD_FULL = "9860020144204623"
TARGET_HOLDER_NAMES = ["oralov", "o'ralov", "uralov", "sardorbek", "sardor"]

def get_openrouter_client() -> Optional[AsyncOpenAI]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY topilmadi!")
        return None
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

def compute_image_hash(image_bytes: bytes) -> str:
    """Compute SHA256 hex digest of image bytes."""
    return hashlib.sha256(image_bytes).hexdigest()

async def verify_receipt_image(image_bytes: bytes, expected_amount: int) -> Dict[str, Any]:
    """
    To'lov chekini AI orqali tekshirish.
    
    Qaytariladigan ma'lumotlar:
    {
        "is_valid": bool,
        "is_receipt": bool,
        "transaction_id": Optional[str],
        "date_time": Optional[str],
        "detected_amount": Optional[int],
        "expected_amount": int,
        "image_hash": str,
        "rejection_reason": Optional[str],
        "raw_ai_response": Dict[str, Any]
    }
    """
    image_hash = compute_image_hash(image_bytes)
    
    # 1. Rasm dublikatligini tekshirish (hash orqali)
    is_dup, dup_reason = await is_receipt_duplicate(image_hash=image_hash)
    if is_dup:
        return {
            "is_valid": False,
            "is_receipt": True,
            "transaction_id": None,
            "date_time": None,
            "detected_amount": None,
            "expected_amount": expected_amount,
            "image_hash": image_hash,
            "rejection_reason": dup_reason or "Ushbu to'lov cheki (rasm) allaqachon botda ishlatilgan!",
            "raw_ai_response": {}
        }

    client = get_openrouter_client()
    if not client:
        return {
            "is_valid": False,
            "is_receipt": False,
            "transaction_id": None,
            "date_time": None,
            "detected_amount": None,
            "expected_amount": expected_amount,
            "image_hash": image_hash,
            "rejection_reason": "AI tizimida texnik xatolik. Iltimos admin bilan bog'laning: @sardorbekuralov",
            "raw_ai_response": {}
        }

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    current_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    system_prompt = (
        "Siz O'zbekistondagi to'lov cheklarini (Payme, Click, Uzum Bank, Anorbank, Milliy, TBC, bank terminali cheklari va h.k.) "
        "tekshiruvchi professional sun'iy intellektsiz.\n\n"
        f"Joriy vaqt: {current_utc_str}\n"
        f"To'lov kutilayotgan karta: {TARGET_CARD_FULL} (oxirgi 4 ta raqami: {TARGET_CARD_LAST4})\n"
        f"Karta egasi: O'ralov Sardorbek\n"
        f"Kutilayotgan summa: {expected_amount} so'm\n\n"
        "VAZIFA:\n"
        "Foydalanuvchi yuborgan rasmni diqqat bilan tekshiring va FAQAT quyidagi JSON formatida javob qaytaring:\n"
        "{\n"
        '  "is_receipt": true/false,\n'
        '  "transaction_id": "tranzaksiya ID si, kvitansiya raqami, chek raqami yoki shifr (agar aniqlansa, aks holda null)",\n'
        '  "date_time": "chekdagi sana va vaqt matni (masalan: 2026-09-08 18:30, topilmasa null)",\n'
        '  "detected_amount": to\'langan summa faqat son shaklida (masalan: 20000, topilmasa null),\n'
        '  "recipient_card": "qabul qiluvchi karta raqami yoki oxirgi 4 ta raqami (agar ko\'rinsa, aks holda null)",\n'
        '  "recipient_name": "qabul qiluvchi shaxs ismi (agar ko\'rinsa, aks holda null)",\n'
        '  "status": "success / failed / pending / unknown",\n'
        '  "rejection_reason": "agar chek bo\'lmasa yoki to\'lov rad etilishi kerak bo\'lsa sababi o\'zbek tilida, aks holda null"\n'
        "}\n\n"
        "MUHIM QOIDALAR:\n"
        "1. Agar rasm to'lov cheki bo'lmasa (masalan: selfie, tabiat, kitob, boshqa oddiy yozuvlar, mem, boshqa chat skrinshoti): "
        'is_receipt = false va rejection_reason = "Yuborilgan rasm to\'lov cheki emas. Iltimos, haqiqiy to\'lov chekini yuboring." qilib belgilang.\n'
        "2. Chekdagi tranzaksiya shifri / ID raqamini aniqlashga harakat qiling.\n"
        "3. Holat (status): agar chekda to'lov muvaffaqiyatli o'tgan bo'lsa (Muvaffaqiyatli, Bajarildi, O'tkazildi, To'landi, Oplacheno, Success) -> 'success'. "
        "Agar rad etilgan, bekor qilingan yoki xatolik bo'lsa -> 'failed'.\n"
        "4. Agar chekda qabul qiluvchi karta yoki ism boshqa notanish shaxsga tegishli bo'lsa va 4623 / O'ralov Sardorbekka aloqasi bo'lmasa, buni rejection_reason da qayd eting.\n"
        "5. Javobda faqat toza JSON bo'lsin, hech qanday qo'shimcha matnsiz."
    )

    try:
        response = await client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Ushbu to'lov chekini tahlil qiling va JSON formatida natijani bering:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.1
        )
        
        raw_text = response.choices[0].message.content or "{}"
        data = json.loads(raw_text)
    except Exception as e:
        logger.error(f"Error during AI receipt analysis: {e}")
        return {
            "is_valid": False,
            "is_receipt": False,
            "transaction_id": None,
            "date_time": None,
            "detected_amount": None,
            "expected_amount": expected_amount,
            "image_hash": image_hash,
            "rejection_reason": "Chekni AI tahlil qilishda xatolik yuz berdi. Iltimos qayta urinib ko'ring yoki adminga murojaat qiling.",
            "raw_ai_response": {}
        }

    is_receipt = bool(data.get("is_receipt", False))
    transaction_id = data.get("transaction_id")
    date_time = data.get("date_time")
    detected_amount = data.get("detected_amount")
    recipient_card = str(data.get("recipient_card") or "").lower()
    recipient_name = str(data.get("recipient_name") or "").lower()
    status = str(data.get("status") or "").lower()
    ai_rejection = data.get("rejection_reason")

    # Clean transaction ID
    if transaction_id and str(transaction_id).strip().lower() in ["null", "none", "yo'q", "topilmadi"]:
        transaction_id = None
    else:
        transaction_id = str(transaction_id).strip() if transaction_id else None

    # Normalization of amount
    parsed_amount = None
    if detected_amount is not None:
        try:
            if isinstance(detected_amount, (int, float)):
                parsed_amount = int(detected_amount)
            elif isinstance(detected_amount, str):
                digits = "".join(ch for ch in detected_amount if ch.isdigit())
                if digits:
                    parsed_amount = int(digits)
        except Exception:
            parsed_amount = None

    # TEKSHIRUVLAR (VALIDATION RULES):
    
    # 1. Chek emasligi
    if not is_receipt:
        reason = ai_rejection or "Yuborilgan rasm to'lov cheki emas. Iltimos, haqiqiy to'lov chekini yuboring."
        return {
            "is_valid": False,
            "is_receipt": False,
            "transaction_id": transaction_id,
            "date_time": date_time,
            "detected_amount": parsed_amount,
            "expected_amount": expected_amount,
            "image_hash": image_hash,
            "rejection_reason": reason,
            "raw_ai_response": data
        }

    # 2. To'lov holati muvaffaqiyatlimi?
    if status in ["failed", "rejected", "canceled", "cancelled"]:
        return {
            "is_valid": False,
            "is_receipt": True,
            "transaction_id": transaction_id,
            "date_time": date_time,
            "detected_amount": parsed_amount,
            "expected_amount": expected_amount,
            "image_hash": image_hash,
            "rejection_reason": "Chekdagi to'lov holati muvaffaqiyatsiz yoki bekor qilingan.",
            "raw_ai_response": data
        }

    # 3. Dublikat tranzaksiya ID (shifr) tekshirish
    if transaction_id and len(transaction_id) >= 4:
        is_tx_dup, tx_dup_reason = await is_receipt_duplicate(tx_id=transaction_id)
        if is_tx_dup:
            return {
                "is_valid": False,
                "is_receipt": True,
                "transaction_id": transaction_id,
                "date_time": date_time,
                "detected_amount": parsed_amount,
                "expected_amount": expected_amount,
                "image_hash": image_hash,
                "rejection_reason": tx_dup_reason or f"Ushbu to'lov cheki (ID: {transaction_id}) allaqachon botda ishlatilgan!",
                "raw_ai_response": data
            }

    # 4. Summa yetarliligini tekshirish (agar AI summani aniqlay olgan bo'lsa)
    if parsed_amount is not None:
        if parsed_amount < (expected_amount * 0.9):
            return {
                "is_valid": False,
                "is_receipt": True,
                "transaction_id": transaction_id,
                "date_time": date_time,
                "detected_amount": parsed_amount,
                "expected_amount": expected_amount,
                "image_hash": image_hash,
                "rejection_reason": f"To'lov summasi kam: Chekda {parsed_amount:,} so'm, tanlangan summa esa {expected_amount:,} so'm.",
                "raw_ai_response": data
            }

    # 5. Qabul qiluvchi karta/ism chekda yaqqol boshqa shaxs ko'rsatilgan bo'lsa
    if recipient_card:
        clean_card = "".join(ch for ch in recipient_card if ch.isdigit())
        if len(clean_card) >= 4 and not clean_card.endswith(TARGET_CARD_LAST4) and TARGET_CARD_FULL not in clean_card:
            if not any(name in recipient_name for name in TARGET_HOLDER_NAMES):
                return {
                    "is_valid": False,
                    "is_receipt": True,
                    "transaction_id": transaction_id,
                    "date_time": date_time,
                    "detected_amount": parsed_amount,
                    "expected_amount": expected_amount,
                    "image_hash": image_hash,
                    "rejection_reason": f"Chekdagi qabul qiluvchi karta bizning kartamizga mos kelmadi (Kutilgan: 9860 **** **** {TARGET_CARD_LAST4}).",
                    "raw_ai_response": data
                }

    # Agar AI ning o'zi rad etish sababini aniq ko'rsatgan bo'lsa
    if ai_rejection and ("soxta" in ai_rejection.lower() or "noto'g'ri" in ai_rejection.lower() or "eskirgan" in ai_rejection.lower()):
        return {
            "is_valid": False,
            "is_receipt": True,
            "transaction_id": transaction_id,
            "date_time": date_time,
            "detected_amount": parsed_amount,
            "expected_amount": expected_amount,
            "image_hash": image_hash,
            "rejection_reason": ai_rejection,
            "raw_ai_response": data
        }

    # Barcha tekshiruvlardan muvaffaqiyatli o'tdi!
    return {
        "is_valid": True,
        "is_receipt": True,
        "transaction_id": transaction_id,
        "date_time": date_time,
        "detected_amount": parsed_amount or expected_amount,
        "expected_amount": expected_amount,
        "image_hash": image_hash,
        "rejection_reason": None,
        "raw_ai_response": data
    }
