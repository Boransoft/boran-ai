import requests

from app.config import settings
from app.db.sync import sync_conversation_message, sync_knowledge_edges, sync_memory_item
from app.learning.corrections import search_corrections
from app.learning.graph import learning_graph_store
from app.learning.pipeline import learning_pipeline
from app.learning.reflection import reflection_engine
from app.memory.long_term import long_term_memory
from app.rag.conversation_memory import save_conversation, search_conversations
from app.rag.search import search_docs
from app.services.memory import memory_store


def _db_sync_enabled() -> bool:
    return bool(settings.database_url)


def call_lm_studio(message: str, context: str) -> str:
    prompt = f"""
Use the context to answer the question.
If context is insufficient, state that clearly.
Answer in Turkish.

Context:
{context}

Question:
{message}
"""

    response = requests.post(
        f"{settings.lm_studio_base_url}/chat/completions",
        json={
            "model": settings.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Sen boran.ai adli yerel calisan asistanisin. "
                        "Kisa, net, dogru ve pratik yanit ver."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.4,
            "max_tokens": 700,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def build_local_fallback_reply(
    message: str,
    pdf_context: list[str],
    conv_context: list[str],
    correction_context: list[str],
    long_term_context: list[str],
    graph_context: list[str],
    reflection_context: list[str],
    error: Exception,
) -> str:
    context_candidates = (
        pdf_context
        + correction_context
        + conv_context
        + long_term_context
        + graph_context
        + reflection_context
    )
    if not context_candidates:
        return (
            "LM Studio su an bagli degil. "
            "Yerel bellekte ilgili baglam bulunamadi. "
            "Model acildiginda daha iyi yanit verebilirim."
        )

    snippet = context_candidates[0]
    if len(snippet) > 700:
        snippet = snippet[:700] + "..."

    return (
        "LM Studio baglantisi kurulamadigi icin yerel fallback yanit uretiyorum.\n\n"
        f"Soru: {message}\n"
        "Ilgili baglamdan kisa ozet:\n"
        f"{snippet}\n\n"
        f"Hata: {error}"
    )


def _format_long_term_context(user_id: str, message: str, limit: int = 3) -> list[str]:
    memory_items = long_term_memory.search(user_id=user_id, query=message, limit=limit)
    formatted: list[str] = []
    for item in memory_items:
        kind = item.get("kind", "memory")
        text = item.get("text", "")
        formatted.append(f"[LongTerm kind={kind}]\n{text}")
    return formatted


def build_reply(
    user_id: str,
    message: str,
    save_to_long_term: bool = True,
    include_reflection_context: bool = False,
) -> dict[str, object]:
    pdf_context: list[str] = []
    conv_context: list[str] = []
    correction_context: list[str] = []
    long_term_context: list[str] = []
    graph_context: list[str] = []
    reflection_context: list[str] = []

    try:
        pdf_context = search_docs(message, n_results=3)
    except Exception as exc:
        print(f"PDF search error: {exc}")

    try:
        conv_context = search_conversations(message, user_id=user_id, n_results=3)
    except Exception as exc:
        print(f"Conversation search error: {exc}")

    try:
        correction_context = search_corrections(user_id=user_id, query=message, n_results=2)
    except Exception as exc:
        print(f"Correction search error: {exc}")

    long_term_context = _format_long_term_context(user_id=user_id, message=message, limit=3)
    try:
        graph_context = learning_graph_store.build_context(user_id=user_id, query=message, limit=4)
    except Exception as exc:
        print(f"Graph context error: {exc}")
    if include_reflection_context:
        try:
            reflection_context = reflection_engine.build_chat_context(user_id=user_id)
        except Exception as exc:
            print(f"Reflection context error: {exc}")

    context_parts: list[str] = []
    if pdf_context:
        context_parts.append("PDF CONTEXT:\n" + "\n\n".join(pdf_context))
    if conv_context:
        context_parts.append("CONVERSATION CONTEXT:\n" + "\n\n".join(conv_context))
    if correction_context:
        context_parts.append("USER CORRECTIONS:\n" + "\n\n".join(correction_context))
    if long_term_context:
        context_parts.append("LONG TERM MEMORY:\n" + "\n\n".join(long_term_context))
    if graph_context:
        context_parts.append("KNOWLEDGE GRAPH:\n" + "\n\n".join(graph_context))
    if reflection_context:
        context_parts.append("REFLECTION CONTEXT:\n" + "\n\n".join(reflection_context))

    context = "\n\n".join(context_parts)

    used_lm = True
    try:
        reply = call_lm_studio(message, context)
    except Exception as exc:
        used_lm = False
        reply = build_local_fallback_reply(
            message=message,
            pdf_context=pdf_context,
            conv_context=conv_context,
            correction_context=correction_context,
            long_term_context=long_term_context,
            graph_context=graph_context,
            reflection_context=reflection_context,
            error=exc,
        )

    memory_store.add_message(user_id, message)

    save_conversation(user_id, "user", message)
    if used_lm:
        save_conversation(user_id, "assistant", reply)
    try:
        learning_pipeline.ingest_conversation(
            user_id=user_id,
            role="user",
            text=message,
            source="chat",
            save_vector_memory=False,
        )
        if used_lm:
            learning_pipeline.ingest_conversation(
                user_id=user_id,
                role="assistant",
                text=reply,
                source="chat",
                save_vector_memory=False,
            )
    except Exception as exc:
        print(f"Learning pipeline conversation ingest error: {exc}")

    if _db_sync_enabled():
        try:
            sync_conversation_message(user_id, "user", message, source="chat")
            if used_lm:
                sync_conversation_message(user_id, "assistant", reply, source="chat")
        except Exception as exc:
            print(f"DB conversation sync error: {exc}")

    if save_to_long_term:
        long_term_memory.add(
            user_id=user_id,
            text=message,
            kind="user_message",
            source="chat",
        )
        if _db_sync_enabled():
            try:
                sync_memory_item(
                    user_external_id=user_id,
                    kind="user_message",
                    text=message,
                    source="chat",
                )
            except Exception as exc:
                print(f"DB memory sync error (user_message): {exc}")
        if used_lm:
            long_term_memory.add(
                user_id=user_id,
                text=reply,
                kind="assistant_reply",
                source="chat",
            )
            if _db_sync_enabled():
                try:
                    sync_memory_item(
                        user_external_id=user_id,
                        kind="assistant_reply",
                        text=reply,
                        source="chat",
                    )
                except Exception as exc:
                    print(f"DB memory sync error (assistant_reply): {exc}")
        if _db_sync_enabled():
            try:
                graph = learning_graph_store.get_graph(user_id=user_id, max_nodes=120, max_edges=150)
                sync_knowledge_edges(user_external_id=user_id, edges=graph["edges"])
            except Exception as exc:
                print(f"DB knowledge sync error: {exc}")

    return {
        "user_id": user_id,
        "reply": reply,
        "memory_size": memory_store.count(user_id),
        "context_hits": len(pdf_context)
        + len(conv_context)
        + len(correction_context)
        + len(long_term_context)
        + len(graph_context)
        + len(reflection_context),
    }
