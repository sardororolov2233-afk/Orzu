from jinja2 import Environment, FileSystemLoader
import os

def render_html(data):
    """
    JSON ma'lumotlarini HTML shabloniga render qilish.
    """
    # templates papkasi ichidan presentation.html ni qidiradi
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    
    try:
        template = env.get_template("presentation.html")
    except Exception:
        # Agar shablon topilmasa, standart shablonni yaratish yoki xato berish
        return "<html><body><h1>Template not found</h1></body></html>"
        
    return template.render(slides=data.get("slides", []))
