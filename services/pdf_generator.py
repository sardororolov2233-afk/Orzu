import logging

logger = logging.getLogger(__name__)

def generate_pdf(html_content, output_path):
    """
    HTML kontentni PDF faylga aylantirish (xhtml2pdf orqali).
    Windowsda GTK+ talab qilmaydi.
    """
    try:
        try:
            from xhtml2pdf import pisa
        except ModuleNotFoundError:
            logger.error("xhtml2pdf topilmadi. Iltimos: pip install xhtml2pdf")
            return False
        
        with open(output_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html_content, dest=f)
            
        return not pisa_status.err
    except Exception as e:
        logger.error(f"PDF yaratishda xatolik: {e}")
        return False
