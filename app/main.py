from fastapi import FastAPI
from app.schemas import ChatRequest, ChatResponse
from app.services.assistant import build_reply

app = FastAPI(title="boran.ai")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return build_reply(req.user_id, req.message)