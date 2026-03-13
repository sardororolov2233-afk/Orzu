from .brain import ask_ai, load_prompt

async def format_text(text):
    prompt = load_prompt("formatter.txt", MATN=text)
    return await ask_ai(prompt)
