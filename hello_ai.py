import os, asyncio, httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_URL     = "https://api.openai.com/v1/chat/completions"

async def ask_ai(user_text: str) -> tuple[str, str]:
    """Return exactly (reply_text, provider_used) where provider_used in {'groq','openai','fake'}."""
    # 1) Groq
    if GROQ_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role":"system","content":"You are a concise, helpful assistant."},
                    {"role":"user","content": user_text}
                ],
                "temperature": 0.7,
                "max_tokens": 512,
                "stream": False
            }
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(GROQ_URL, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                text = data["choices"][0]["message"]["content"]
                return text, "groq"
        except Exception:
            pass  # fall through

    # 2) OpenAI
    if OPENAI_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": OPENAI_MODEL,
                "messages": [
                    {"role":"system","content":"You are a concise, helpful assistant."},
                    {"role":"user","content": user_text}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(OPENAI_URL, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                text = data["choices"][0]["message"]["content"]
                return text, "openai"
        except Exception:
            pass

    # 3) Fake fallback
    return f"(fake) I read: '{user_text[:80]}...' and this is a placeholder reply.", "fake"

if __name__ == "__main__":
    text = input("Say something to the AI: ")
    reply, prov = asyncio.run(ask_ai(text))
    print(f"({prov}) {reply}")
