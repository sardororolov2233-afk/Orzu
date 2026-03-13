from .brain import ask_ai, load_prompt

async def review_text(text):
    prompt = load_prompt("reviewer.txt", text=text)
    return await ask_ai(prompt)
