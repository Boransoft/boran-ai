import logging
from time import perf_counter

import requests

from app.config import settings
from app.db.sync import sync_conversation_message, sync_knowledge_edges, sync_memory_item
from app.learning.clustering import concept_cluster_engine
from app.learning.corrections import search_corrections
from app.learning.graph import learning_graph_store
from app.learning.pipeline import learning_pipeline
from app.learning.reflection import reflection_engine
from app.learning.scoring import memory_scoring_engine
from app.learning.semantic_linking import semantic_linker
from app.memory.long_term import long_term_memory
from app.rag.conversation_memory import save_conversation, search_conversations
from app.rag.search import search_docs_with_metadata
from app.services.memory import memory_store

logger = logging.getLogger("uvicorn.error")


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
                        "Sen boranizm adli yerel calisan asistanisin. "
                        "Kisa, net, dogru ve pratik yanit ver."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.4,
            "max_tokens": 450,
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
    semantic_context: list[str],
    cluster_context: list[str],
    reflection_context: list[str],
    error: Exception,
) -> str:
    context_candidates = (
        pdf_context
        + correction_context
        + conv_context
        + long_term_context
        + graph_context
        + semantic_context
        + cluster_context
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


def _format_long_term_context(user_id: str, message: str, limit: int = 4) -> list[str]:
    memory_items = memory_scoring_engine.top_memories(user_id=user_id, query=message, limit=limit)
    formatted: list[str] = []
    for item in memory_items:
        kind = item.get("kind", "memory")
        text = item.get("text", "")
        score = item.get("importance_score", 0.0)
        formatted.append(f"[LongTerm kind={kind} score={score}]\n{text}")
    return formatted


def _format_cluster_context(user_id: str, message: str, limit: int = 3) -> list[str]:
    return concept_cluster_engine.build_chat_context(user_id=user_id, query=message, limit=limit)


def _format_semantic_context(user_id: str, message: str, limit: int = 4) -> list[str]:
    return semantic_linker.build_query_context(user_id=user_id, query=message, limit=limit)


def _trim_context_items(items: list[str], max_items: int, max_chars: int = 360) -> list[str]:
    trimmed: list[str] = []
    for item in items[:max_items]:
        text = item.strip()
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        if text:
            trimmed.append(text)
    return trimmed


def _build_context_with_budget(
    sections: list[tuple[str, list[str]]],
    max_chars: int,
) -> tuple[str, int]:
    if max_chars <= 0:
        return "", 0

    built: list[str] = []
    total_chars = 0
    for title, items in sections:
        if not items:
            continue
        section_text = title + ":\n" + "\n\n".join(items)
        remaining = max_chars - total_chars
        if remaining <= 0:
            break
        if len(section_text) > remaining:
            if remaining < 40:
                break
            section_text = section_text[: remaining - 3] + "..."
        built.append(section_text)
        total_chars += len(section_text)
    return "\n\n".join(built), total_chars


def build_reply(
    user_id: str,
    message: str,
    save_to_long_term: bool = True,
    include_reflection_context: bool = False,
    debug_timing: bool = False,
    source_ids: list[str] | None = None,
    file_names: list[str] | None = None,
    source_filters: list[str] | None = None,
    recent_documents: list[dict[str, object]] | None = None,
    context_scope: str | None = None,
    doc_top_k: int | None = None,
    doc_similarity_threshold: float | None = None,
) -> dict[str, object]:
    total_start = perf_counter()
    timings: dict[str, float] = {}

    pdf_context: list[str] = []
    conv_context: list[str] = []
    correction_context: list[str] = []
    long_term_context: list[str] = []
    graph_context: list[str] = []
    semantic_context: list[str] = []
    cluster_context: list[str] = []
    reflection_context: list[str] = []
    retrieval_debug: dict[str, object] = {}
    matched_source_ids: list[str] = []
    matched_file_names: list[str] = []
    citations: list[dict[str, object]] = []
    retrieval_fallback_used = False

    retrieval_start = perf_counter()
    step_start = perf_counter()
    try:
        active_source_ids = list(source_ids or [])
        active_file_names = list(file_names or [])

        if source_filters:
            for value in source_filters:
                text = str(value).strip()
                if not text:
                    continue
                if "." in text:
                    if text not in active_file_names:
                        active_file_names.append(text)
                elif text not in active_source_ids:
                    active_source_ids.append(text)

        if not active_source_ids and not active_file_names and recent_documents:
            for item in recent_documents:
                source_id = str(item.get("source_id") or "").strip()
                file_name = str(item.get("file_name") or "").strip()
                if source_id and source_id not in active_source_ids:
                    active_source_ids.append(source_id)
                if file_name and file_name not in active_file_names:
                    active_file_names.append(file_name)

        retrieval = search_docs_with_metadata(
            query=message,
            n_results=max(1, doc_top_k or settings.chat_doc_context_limit),
            user_id=user_id,
            source_ids=active_source_ids,
            file_names=active_file_names,
            recent_documents=recent_documents,
            context_scope=context_scope,
            similarity_threshold=doc_similarity_threshold,
        )
        pdf_context = [hit.prompt_block() for hit in retrieval.hits]
        matched_source_ids = [hit.source_id for hit in retrieval.hits if hit.source_id]
        matched_file_names = [hit.original_file_name for hit in retrieval.hits if hit.original_file_name]
        citation_index: dict[str, dict[str, object]] = {}
        citation_order: list[str] = []
        for hit in retrieval.hits:
            source_key = (hit.source_id or hit.normalized_file_name or hit.original_file_name).strip() or "__unknown__"
            if source_key not in citation_index:
                citation_index[source_key] = {
                    "file_name": hit.original_file_name,
                    "source_id": hit.source_id,
                    "source_type": hit.source_type,
                    "chunk_count_used": 0,
                }
                citation_order.append(source_key)
            citation_index[source_key]["chunk_count_used"] = int(citation_index[source_key]["chunk_count_used"]) + 1
        citations = [citation_index[key] for key in citation_order]
        retrieval_debug = retrieval.debug
        retrieval_fallback_used = bool(retrieval.debug.get("fallback_used", False))
    except Exception as exc:
        print(f"PDF search error: {exc}")
    timings["context.semantic_docs_s"] = round(perf_counter() - step_start, 4)

    step_start = perf_counter()
    try:
        conv_context = search_conversations(
            message,
            user_id=user_id,
            n_results=max(1, settings.chat_conversation_context_limit),
        )
    except Exception as exc:
        print(f"Conversation search error: {exc}")
    timings["context.conversation_s"] = round(perf_counter() - step_start, 4)

    step_start = perf_counter()
    try:
        correction_context = search_corrections(
            user_id=user_id,
            query=message,
            n_results=max(1, settings.chat_correction_context_limit),
        )
    except Exception as exc:
        print(f"Correction search error: {exc}")
    timings["context.corrections_s"] = round(perf_counter() - step_start, 4)

    step_start = perf_counter()
    long_term_context = _format_long_term_context(
        user_id=user_id,
        message=message,
        limit=max(1, settings.chat_long_term_context_limit),
    )
    timings["context.long_term_s"] = round(perf_counter() - step_start, 4)

    step_start = perf_counter()
    cluster_context = _format_cluster_context(
        user_id=user_id,
        message=message,
        limit=max(1, settings.chat_cluster_context_limit),
    )
    timings["context.cluster_s"] = round(perf_counter() - step_start, 4)

    step_start = perf_counter()
    semantic_context = _format_semantic_context(
        user_id=user_id,
        message=message,
        limit=max(1, settings.chat_semantic_context_limit),
    )
    timings["context.semantic_links_s"] = round(perf_counter() - step_start, 4)

    step_start = perf_counter()
    try:
        graph_context = learning_graph_store.build_context(
            user_id=user_id,
            query=message,
            limit=max(1, settings.chat_graph_context_limit),
        )
    except Exception as exc:
        print(f"Graph context error: {exc}")
    timings["context.graph_s"] = round(perf_counter() - step_start, 4)

    step_start = perf_counter()
    if include_reflection_context:
        try:
            reflection_context = reflection_engine.build_chat_context(user_id=user_id)
        except Exception as exc:
            print(f"Reflection context error: {exc}")
    timings["context.reflection_s"] = round(perf_counter() - step_start, 4)

    timings["context_preparation_s"] = round(perf_counter() - retrieval_start, 4)
    timings["memory_retrieval_s"] = round(
        timings["context.semantic_docs_s"]
        + timings["context.conversation_s"]
        + timings["context.corrections_s"]
        + timings["context.long_term_s"],
        4,
    )
    timings["graph_reasoning_context_s"] = round(
        timings["context.cluster_s"]
        + timings["context.semantic_links_s"]
        + timings["context.graph_s"]
        + timings["context.reflection_s"],
        4,
    )

    recent_document_hints = _trim_context_items(
        [
            (
                f"[RecentDoc file={item.get('file_name', '')} source={item.get('source_id', '')} "
                f"chunks={item.get('chunk_count', '')}]"
            ).strip()
            for item in (recent_documents or [])
        ],
        max_items=4,
    )

    if context_scope == "uploaded_documents":
        context_sections = [
            ("RECENT DOCUMENT HINTS", recent_document_hints),
            ("PDF CONTEXT", _trim_context_items(pdf_context, max_items=max(1, settings.chat_doc_context_limit))),
        ]
        if not pdf_context:
            context_sections.extend(
                [
                    (
                        "CONCEPT CLUSTERS",
                        _trim_context_items(
                            cluster_context,
                            max_items=max(1, settings.chat_cluster_context_limit),
                        ),
                    ),
                    (
                        "SEMANTIC LINKING",
                        _trim_context_items(
                            semantic_context,
                            max_items=max(1, settings.chat_semantic_context_limit),
                        ),
                    ),
                ]
            )
    else:
        context_sections = [
            ("RECENT DOCUMENT HINTS", recent_document_hints),
            ("PDF CONTEXT", _trim_context_items(pdf_context, max_items=max(1, settings.chat_doc_context_limit))),
            (
                "CONVERSATION CONTEXT",
                _trim_context_items(
                    conv_context,
                    max_items=max(1, settings.chat_conversation_context_limit),
                ),
            ),
            (
                "USER CORRECTIONS",
                _trim_context_items(
                    correction_context,
                    max_items=max(1, settings.chat_correction_context_limit),
                ),
            ),
            (
                "LONG TERM MEMORY",
                _trim_context_items(
                    long_term_context,
                    max_items=max(1, settings.chat_long_term_context_limit),
                ),
            ),
            (
                "CONCEPT CLUSTERS",
                _trim_context_items(
                    cluster_context,
                    max_items=max(1, settings.chat_cluster_context_limit),
                ),
            ),
            (
                "SEMANTIC LINKING",
                _trim_context_items(
                    semantic_context,
                    max_items=max(1, settings.chat_semantic_context_limit),
                ),
            ),
            (
                "KNOWLEDGE GRAPH",
                _trim_context_items(
                    graph_context,
                    max_items=max(1, settings.chat_graph_context_limit),
                ),
            ),
            ("REFLECTION CONTEXT", _trim_context_items(reflection_context, max_items=2)),
        ]

    context, context_chars = _build_context_with_budget(
        sections=context_sections,
        max_chars=max(400, settings.chat_max_context_chars),
    )
    timings["context_chars"] = float(context_chars)

    used_lm = True
    lm_start = perf_counter()
    try:
        prompt_message = message
        if context_scope == "uploaded_documents":
            focus_sources = ", ".join((file_names or [])[:6]).strip()
            if not focus_sources:
                focus_sources = ", ".join((matched_file_names or matched_source_ids)[:6]).strip()
            if focus_sources:
                prompt_message = f"{message}\n\nBelge odagi: Yanitini oncelikle su kaynaklardan uret: {focus_sources}."
            else:
                prompt_message = (
                    f"{message}\n\nBelge odagi: Yanitini yuklenen belgelerden uret. "
                    "Baglam yetersizse bunu acikca soyle."
                )
        reply = call_lm_studio(prompt_message, context)
    except Exception as exc:
        used_lm = False
        reply = build_local_fallback_reply(
            message=message,
            pdf_context=pdf_context,
            conv_context=conv_context,
            correction_context=correction_context,
            long_term_context=long_term_context,
            graph_context=graph_context,
            semantic_context=semantic_context,
            cluster_context=cluster_context,
            reflection_context=reflection_context,
            error=exc,
        )
    timings["lm_response_s"] = round(perf_counter() - lm_start, 4)

    persist_start = perf_counter()
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
    timings["post_processing_s"] = round(perf_counter() - persist_start, 4)
    timings["total_s"] = round(perf_counter() - total_start, 4)

    logger.info(
        "chat_timing user=%s total=%.3fs context=%.3fs lm=%.3fs post=%.3fs",
        user_id,
        timings["total_s"],
        timings["context_preparation_s"],
        timings["lm_response_s"],
        timings["post_processing_s"],
    )
    logger.info(
        "chat_retrieval user=%s context_scope=%s doc_context_hits=%s matched_source_ids=%s matched_file_names=%s fallback_used=%s",
        user_id,
        context_scope or "",
        len(pdf_context),
        matched_source_ids,
        matched_file_names,
        retrieval_fallback_used,
    )

    response: dict[str, object] = {
        "user_id": user_id,
        "reply": reply,
        "memory_size": memory_store.count(user_id),
        "doc_context_hits": len(pdf_context),
        "doc_sources": list(dict.fromkeys(matched_file_names)),
        "matched_source_ids": list(dict.fromkeys(matched_source_ids)),
        "matched_file_names": list(dict.fromkeys(matched_file_names)),
        "citations": citations,
        "retrieval_fallback_used": retrieval_fallback_used,
        "context_hits": len(pdf_context)
        + len(conv_context)
        + len(correction_context)
        + len(long_term_context)
        + len(cluster_context)
        + len(semantic_context)
        + len(graph_context)
        + len(reflection_context),
    }
    if debug_timing:
        response["debug_timing"] = timings
        response["retrieval_debug"] = retrieval_debug
    return response
