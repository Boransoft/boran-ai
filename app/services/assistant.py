import requests
from app.config import settings
from app.services.memory import memory_store
from app.rag.search import search_docs
from app.rag.conversation_memory import save_conversation, search_conversations


def call_lm_studio(message: str, context: str) -> str:
    prompt = f"""
Aşağıdaki bağlamı kullanarak soruyu cevapla.
Bağlam yetersizse bunu açıkça söyle.
Cevabı Türkçe ver.

Bağlam:
{context}

Soru:
{message}
"""

    response = requests.post(
        f"{settings.lm_studio_base_url}/chat/completions",
        json={
            "model": settings.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "Sen boran.ai adlı yerel çalışan yapay zeka asistanısın. Türkçe, net, doğru ve pratik cevap ver."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.4,
            "max_tokens": 600
        },
        timeout=120
    )

    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def build_reply(user_id: str, message: str):
    pdf_context = []
    conv_context = []

    try:
        pdf_context = search_docs(message, n_results=3)
    except Exception as e:
        print(f"PDF arama hatası: {e}")

    try:
        conv_context = search_conversations(message, user_id=user_id, n_results=3)
    except Exception as e:
        print(f"Konuşma hafıza arama hatası: {e}")

    context_parts = []

    if pdf_context:
        context_parts.append("PDF BAĞLAMI:\n" + "\n\n".join(pdf_context))

    if conv_context:
        context_parts.append("KONUŞMA HAFIZASI:\n" + "\n\n".join(conv_context))

    context = "\n\n".join(context_parts)

    try:
        reply = call_lm_studio(message, context)
    except Exception as e:
        reply = f"LM Studio veya RAG hatası: {str(e)}"

    memory_store.add_message(user_id, message)

    save_conversation(user_id, "user", message)
    save_conversation(user_id, "assistant", reply)

    return {
        "user_id": user_id,
        "reply": reply,
        "memory_size": memory_store.count(user_id),
    }