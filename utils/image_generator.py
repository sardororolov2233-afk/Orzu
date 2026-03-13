import os
import aiohttp
import logging
from config import UNSPLASH_API_KEY
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_API_ENDPOINT = "https://api.unsplash.com/photos/random"

async def get_image_path_from_description(description: str, style: str = "modern, professional"):
    """
    Berilgan tavsifga mos rasm generatsiya qiladi yoki topadi (Unsplash orqali).
    """
    # API keyni tekshirish (Config yoki Environment)
    api_key = UNSPLASH_API_KEY or os.getenv("UNSPLASH_API_KEY")
    
    if not api_key:
        logger.warning(f"UNSPLASH_API_KEY topilmadi. Rasm yuklash o'tkazib yuboriladi.")
        return None

    # Temp papkani yaratish
    temp_dir = Path("temp_downloads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Fayl nomini tayyorlash
    safe_desc = "".join([c for c in description if c.isalnum() or c in (' ', '-', '_')]).strip()
    filename = f"{safe_desc[:30].replace(' ', '_')}.jpg"
    file_path = temp_dir / filename

    # Agar rasm allaqachon yuklangan bo'lsa, o'shani qaytarish
    if file_path.exists():
        return str(file_path)

    try:
        headers = {"Authorization": f"Client-ID {api_key}"}
        # Use random endpoint for better variety and direct object result
        params = {
            "query": f"{description}", # Removed style from query to be more precise based on description
            "orientation": "landscape",
            "content_filter": "high",
            "count": 1 # random endpoint returns array if count > 1, or single obj if count omitted. But we want 1.
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(IMAGE_API_ENDPOINT, headers=headers, params=params) as response:
                if response.status != 200:
                    logger.error(f"Unsplash API error: {response.status} - {await response.text()}")
                    return "assets/default_slide_image.jpg"
                
                data = await response.json()
                
                # Random endpoint can return list or dict depending on 'count' param.
                # If count is used, it returns a list.
                results = data if isinstance(data, list) else [data]
                
                if not results:
                    logger.warning(f"Rasm topilmadi: {description}")
                    return "assets/default_slide_image.jpg"
                
                image_url = results[0]["urls"]["regular"]
                
                # Rasmni yuklab olish
                async with session.get(image_url) as img_response:
                    if img_response.status == 200:
                        content = await img_response.read()
                        # Use aiofiles for non-blocking write if possible, or just keep it simple
                        # but check if we can at least avoid potential issues.
                        # For now, standard write is okay for small files, but let's be safe.
                        try:
                            # Rasmni optimallashtirish va siqish
                            from PIL import Image as PILImage
                            import io

                            img = PILImage.open(io.BytesIO(content))
                            # Ranglar modelini tekshirish (RGBA ni RGB ga o'tkazish JPEG uchun)
                            if img.mode in ("RGBA", "P"):
                                img = img.convert("RGB")
                            
                            # Hajmini biroz kichraytirish (masalan, max 1280px kenglik)
                            max_size = (1280, 1280)
                            img.thumbnail(max_size, PILImage.LANCZOS)
                            
                            # Siqilgan holda saqlash (Quality: 80%)
                            img.save(file_path, "JPEG", quality=80, optimize=True)
                            
                            return str(file_path)
                        except Exception as fe:
                            logger.error(f"Rasmni qayta ishlashda xatolik: {fe}")
                            # Agar xatolik bo'lsa, asl nusxasini saqlashga urinish
                            with open(file_path, "wb") as f:
                                f.write(content)
                            return str(file_path)
                    else:
                        logger.error(f"Rasmni yuklab olishda xatolik: {img_response.status}")

    except Exception as e:
        logger.error(f"Rasm olishda umumiy xatolik: {e}")
        
    # Return None instead of non-existent default image
    return None
