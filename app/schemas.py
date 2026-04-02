from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    user_id: str
    reply: str
    memory_size: int