"""Mini RAG service for testing the evaluation platform.

OpenAI-compatible /chat/completions endpoint backed by DeepSeek.
Knowledge base loaded from tests/fixtures/test_doc.txt.
"""

import json
import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Load knowledge base ──
_KB_PATH = os.path.join(os.path.dirname(__file__), "tests", "fixtures", "test_doc.txt")
with open(_KB_PATH, "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

# ── DeepSeek config ──
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_BASE = "https://api.deepseek.com"
MODEL = "deepseek-v4-flash"


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = MODEL
    messages: list[Message]
    temperature: float = 0.0


def _find_relevant_chunks(question: str) -> list[str]:
    """Naive chunking: split doc into paragraphs, return all as context."""
    paragraphs = [p.strip() for p in KNOWLEDGE_BASE.split("\n\n") if p.strip()]
    return [p for p in paragraphs if len(p) > 20][:5]


def _build_prompt(question: str, contexts: list[str]) -> str:
    context_text = "\n\n---\n\n".join(contexts)
    return f"""You are a helpful assistant. Answer the question based ONLY on the provided context.
If the answer cannot be found in the context, say "I don't have enough information."

Context:
{context_text}

Question: {question}

Answer:"""


@app.post("/chat/completions")
async def chat_completions(req: ChatRequest):
    question = req.messages[-1].content if req.messages else ""
    contexts = _find_relevant_chunks(question)

    # Call DeepSeek with RAG-enhanced prompt
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": _build_prompt(question, contexts)}],
                "temperature": req.temperature,
            },
        )

    if resp.status_code != 200:
        return JSONResponse({"error": resp.text}, status_code=502)

    data = resp.json()
    answer = data["choices"][0]["message"]["content"]

    return {
        "choices": [{
            "message": {
                "content": answer,
                "contexts": contexts,  # ← deepeval metrics use this!
            }
        }]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
