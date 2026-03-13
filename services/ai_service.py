import json
import logging
import re
from ai.brain import ask_ai, load_prompt

logger = logging.getLogger(__name__)

async def generate_presentation_data(topic, pages, language="Uzbek", design_id=None):
    """
    AI dan strukturaviy JSON ma'lumotlarini olish.
    """
    plan_instruction = "Generate a structured JSON for a presentation."
    
    design_info = f"Use design_id: {design_id} for all slides." if design_id else "Select appropriate design_id (1-10) for each slide based on its tone."
    
    prompt = load_prompt("ppt/50_ppt_generator.txt", 
                         topic=topic, 
                         pages=pages, 
                         plan=plan_instruction, 
                         language=language)
    
    prompt += f"\n\nIMPORTANT: Return ONLY valid JSON. No conversational text. {design_info}"
    
    try:
        response = await ask_ai(prompt)
        
        # Regex orqali JSON qismini ajratib olish (eng mustahkam usul)
        json_match = re.search(r'(\{[\s\S]*\})', response)
        if json_match:
            clean_content = json_match.group(1)
        else:
            clean_content = response.strip()
            # Markdown kod bloklarini tozalash (zaxira varianti)
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
        
        data = json.loads(clean_content)
        
        if design_id and "slides" in data:
            for slide in data["slides"]:
                slide["design_id"] = design_id
                
        return data
    except Exception as e:
        logger.error(f"AI dan JSON parsingda xatolik: {e}. Response: {response[:200]}...")
        return None
