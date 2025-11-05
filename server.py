from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Dict, List
from collections import defaultdict, deque
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from hello_ai import ask_ai  # we reuse your Groq-aware function

app = FastAPI(title="Baby AI API (Groq-powered)")

# ========= Simple in-memory conversation memory =========
MAX_TURNS = 10  # keep last N user/assistant pairs
HistoryItem = Dict[str, str]  # {"role": "user"|"assistant", "content": str}
sessions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_TURNS * 2))

# ========= Schemas =========
class ChatIn(BaseModel):
    message: str
    session_id: str = "default"  # enable multiple chats

class ChatOut(BaseModel):
    reply: str
    provider_used: Literal["groq", "openai", "fake"]
    turns_kept: int

@app.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn):
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(400, "message cannot be empty")

    # build short context from recent history
    hist = sessions[body.session_id]
    context_lines: List[str] = []
    for m in hist:
        who = "User" if m["role"] == "user" else "Assistant"
        context_lines.append(f"{who}: {m['content']}")
    context_block = "\n".join(context_lines)

    prompt = (
        "You are a concise, helpful assistant.\n"
        "Here is the recent chat history (if any):\n"
        f"{context_block}\n\n"
        f"User: {msg}\n"
        "Assistant:"
    )

    result = await ask_ai(prompt)

    # Accept either a 2-tuple or a plain string (defensive)
    if isinstance(result, tuple) and len(result) >= 2:
        reply, provider = result[0], result[1]
    else:
        reply = str(result)
        provider = "fake" if reply.startswith("(fake)") else "groq"

    # update memory
    hist.append({"role": "user", "content": msg})
    hist.append({"role": "assistant", "content": reply})

    return ChatOut(reply=reply, provider_used=provider, turns_kept=len(hist) // 2)

# --- Feature endpoints (stateless) ---

class SummarizeIn(BaseModel):
    text: str
    style: Literal["bullet", "short", "detailed"] = "bullet"

class SummarizeOut(BaseModel):
    summary: str
    provider_used: Literal["groq", "openai", "fake"]

@app.post("/summarize", response_model=SummarizeOut)
async def summarize(body: SummarizeIn):
    if not body.text.strip():
        raise HTTPException(400, "text required")
    prompt = (
        "Summarize the following text.\n"
        f"Style: {body.style}.\n"
        "Be clear and concise. Preserve key facts.\n\n"
        f"TEXT:\n{body.text}"
    )
    try:
        reply, provider = await ask_ai(prompt)
        return SummarizeOut(summary=reply, provider_used=provider)
    except Exception as e:
        raise HTTPException(500, str(e))

class RewriteIn(BaseModel):
    text: str
    tone: Literal["formal", "casual", "friendly", "concise"] = "formal"

class RewriteOut(BaseModel):
    rewritten: str
    provider_used: Literal["groq", "openai", "fake"]

@app.post("/rewrite", response_model=RewriteOut)
async def rewrite(body: RewriteIn):
    if not body.text.strip():
        raise HTTPException(400, "text required")
    prompt = (
        f"Rewrite the following text in a {body.tone} tone. "
        "Keep meaning. Improve clarity. Avoid adding new info.\n\n"
        f"TEXT:\n{body.text}"
    )
    try:
        reply, provider = await ask_ai(prompt)
        return RewriteOut(rewritten=reply, provider_used=provider)
    except Exception as e:
        raise HTTPException(500, str(e))

# ===== Clear a session =====
class ResetIn(BaseModel):
    session_id: str = "default"

class ResetOut(BaseModel):
    ok: bool
    cleared_turns: int

@app.post("/reset", response_model=ResetOut)
async def reset(body: ResetIn):
    turns = len(sessions[body.session_id]) // 2
    sessions.pop(body.session_id, None)
    return ResetOut(ok=True, cleared_turns=turns)

# ===== History endpoint =====
@app.get("/history")
async def get_history(session_id: str = Query("default")):
    """Return stored conversation for a session."""
    hist = sessions.get(session_id)
    if not hist:
        return {"session_id": session_id, "messages": []}
    return {"session_id": session_id, "messages": list(hist)}

# ===== Serve static frontend =====
app.mount("/chat-ui", StaticFiles(directory="frontend", html=True), name="chat-ui")

# To run:
# python -m uvicorn server:app --reload --host 127.0.0.1 --port 8001
# Then open: http://127.0.0.1:8001/docs or http://127.0.0.1:8001/chat-ui
