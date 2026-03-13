from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
import logging
import os
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

def get_contain_dimensions(max_w, max_h, aspect):
    if (max_w / max_h) > aspect:
        h = max_h
        w = h * aspect
    else:
        w = max_w
        h = w / aspect
    return w, h

def apply_design_elements(slide, design_id, style):
    """
    Slaydga dizaynga mos bezak elementlarini qo'shish.
    """
    shapes = slide.shapes
    width = PptInches(13.333)
    height = PptInches(7.5)

    if design_id == 1: # Modern
        # Moviy doira bezak
        circle = shapes.add_shape(MSO_SHAPE.OVAL, PptInches(-2), PptInches(-2), PptInches(6), PptInches(6))
        circle.fill.solid()
        circle.fill.fore_color.rgb = style["accent"]
        circle.fill.fore_color.theme_color = None
        circle.fill.transparency = 0.8
        circle.line.fill.background()

    elif design_id == 2: # Historical
        # Ramka
        border = shapes.add_shape(MSO_SHAPE.RECTANGLE, PptInches(0.5), PptInches(0.5), width - PptInches(1), height - PptInches(1))
        border.fill.background()
        border.line.color.rgb = style["accent"]
        border.line.width = PptPt(3)

    elif design_id == 3: # Terminal
        # Pastki chiziq
        line = shapes.add_shape(MSO_SHAPE.RECTANGLE, PptInches(0), height - PptInches(0.5), width, PptInches(0.05))
        line.fill.solid()
        line.fill.fore_color.rgb = style["accent"]
        
    elif design_id == 7: # Retro
        # Neon to'rtburchak
        rect = shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, PptInches(1), PptInches(1), width - PptInches(2), height - PptInches(2))
        rect.fill.background()
        rect.line.color.rgb = style["accent"]
        rect.line.width = PptPt(4)
        
    elif design_id == 8: # Premium
        # Oltin separator
        sep = shapes.add_shape(MSO_SHAPE.RECTANGLE, width/2 - PptInches(1.5), PptInches(2), PptInches(3), PptInches(0.05))
        sep.fill.solid()
        sep.fill.fore_color.rgb = style["accent"]

def add_placeholder(slide, design_id, style):
    """
    Rasm yuklanmagan holatda slaydga 'Rasm o'rni' shaklini qo'shish.
    """
    shapes = slide.shapes
    left = PptInches(8.5)
    top = PptInches(2.5)
    width = PptInches(4)
    height = PptInches(4)
    
    # Placeholder shakl (kulrang va shaffof)
    ph = shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    ph.fill.solid()
    ph.fill.fore_color.rgb = style["accent"]
    ph.fill.transparency = 0.9
    ph.line.color.rgb = style["accent"]
    ph.line.dash_style = 4 # MSO_LINE.DASH (taxminan, raqam bilan)
    
    # Ichiga matn
    tf = ph.text_frame
    p = tf.paragraphs[0]
    p.text = "Rasm o'rni"
    p.font.color.rgb = style["accent"]
    p.font.size = PptPt(18)

def generate_pptx(data, output_path):
    """
    JSON ma'lumotlarini PPTX fayliga aylantirish.
    Dizaynga qarab ranglar va uslublarni tanlaydi.
    """
    try:
        prs = Presentation()
        prs.slide_width = PptInches(13.333)
        prs.slide_height = PptInches(7.5)

        # Dizaynlar uchun ranglar va fontlar xaritasi
        design_styles = {
            1: {"bg": RGBColor(2, 6, 23), "text": RGBColor(255, 255, 255), "accent": RGBColor(37, 99, 235), "font": "Arial"}, # Modern
            2: {"bg": RGBColor(244, 236, 207), "text": RGBColor(69, 26, 3), "accent": RGBColor(120, 53, 15), "font": "Times New Roman"}, # Historical
            3: {"bg": RGBColor(23, 23, 23), "text": RGBColor(163, 230, 53), "accent": RGBColor(163, 230, 53), "font": "Courier New"}, # Terminal
            4: {"bg": RGBColor(255, 255, 255), "text": RGBColor(236, 72, 153), "accent": RGBColor(249, 168, 212), "font": "Comic Sans MS"}, # Playful
            5: {"bg": RGBColor(0, 0, 0), "text": RGBColor(255, 255, 255), "accent": RGBColor(6, 182, 212), "font": "Courier New"}, # Cybernetic
            6: {"bg": RGBColor(240, 253, 250), "text": RGBColor(6, 78, 59), "accent": RGBColor(16, 185, 129), "font": "Calibri"}, # Eco
            7: {"bg": RGBColor(26, 11, 46), "text": RGBColor(255, 255, 255), "accent": RGBColor(255, 0, 255), "font": "Impact"}, # Retro
            8: {"bg": RGBColor(10, 10, 10), "text": RGBColor(224, 170, 62), "accent": RGBColor(224, 170, 62), "font": "Times New Roman"}, # Premium
            9: {"bg": RGBColor(255, 255, 255), "text": RGBColor(30, 41, 59), "accent": RGBColor(37, 99, 235), "font": "Arial"}, # Simple
            10: {"bg": RGBColor(9, 9, 11), "text": RGBColor(255, 255, 255), "accent": RGBColor(161, 161, 170), "font": "Georgia"}, # Elegance
        }

        for slide_data in data.get("slides", []):
            design_id = slide_data.get("design_id", 9)
            style = design_styles.get(design_id, design_styles[9])
            
            slide_layout = prs.slide_layouts[6] # Blank layout
            slide = prs.slides.add_slide(slide_layout)
            
            # Fonni bo'yash
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = style["bg"]
            
            # Dizayn elementlarini qo'llash
            apply_design_elements(slide, design_id, style)

            # Sarlavha qo'shish
            title_box = slide.shapes.add_textbox(PptInches(1), PptInches(0.5), PptInches(11), PptInches(1.5))
            tf = title_box.text_frame
            p = tf.paragraphs[0]
            p.text = slide_data.get("title", "").upper()
            p.font.bold = True
            p.font.size = PptPt(44)
            p.font.color.rgb = style["text"]
            p.font.name = style["font"]
            
            # Rasmni joylashtirish (agar mavjud bo'lsa)
            image_url = slide_data.get("image_url")
            content_box_width = PptInches(10) # Default width
            
            if image_url and os.path.exists(image_url):
                try:
                    # Rasm o'lchamlarini olish
                    img = PILImage.open(image_url)
                    img_w, img_h = img.size
                    aspect = img_w / img_h
                    
                    # Maksimal rasm joyi (slaydning o'ng qismi)
                    max_w = PptInches(4)
                    max_h = PptInches(4)
                    
                    w, h = get_contain_dimensions(max_w, max_h, aspect)
                    
                    # Rasmni slaydning o'ng tomoniga joylashtirish
                    left = PptInches(8.5)
                    top = PptInches(2.5)
                    
                    # Rasm uchun ramka (ixtiyoriy)
                    pic = slide.shapes.add_picture(image_url, left, top, width=w, height=h)
                    
                    # Agar rasm bo'lsa, matn qutisini biroz qisqartirish (o'ng tomonda joy ochish)
                    content_box_width = PptInches(6.5)
                except Exception as img_err:
                    logger.error(f"Slaydga rasm qo'shishda xatolik ({image_url}): {img_err}")
            elif design_id in [1, 2, 8, 10]: # Ba'zi dizaynlarda rasm yo'q bo'lsa ham joy qoldiramiz yoki bezak qo'yamiz
                 add_placeholder(slide, design_id, style)
                 content_box_width = PptInches(6.5)

            # Bandlar (Bullets)
            bullets = slide_data.get("bullets", [])
            if bullets:
                content_box = slide.shapes.add_textbox(PptInches(1.5), PptInches(2.5), content_box_width, PptInches(4))
                ctf = content_box.text_frame
                ctf.word_wrap = True
                
                for i, bullet in enumerate(bullets):
                    cp = ctf.paragraphs[0] if i == 0 else ctf.add_paragraph()
                    cp.text = f"• {bullet}"
                    cp.font.size = PptPt(24)
                    cp.font.color.rgb = style["text"]
                    cp.font.name = style["font"]
                    cp.space_after = PptPt(15)

            # Speaker Notes (Ma'ruza matni)
            speaker_notes = slide_data.get("speaker_notes")
            if speaker_notes:
                notes_slide = slide.notes_slide
                text_frame = notes_slide.notes_text_frame
                text_frame.text = speaker_notes

        prs.save(output_path)
        return True
    except Exception as e:
        logger.error(f"PPTX yaratishda xatolik: {e}")
        return False
