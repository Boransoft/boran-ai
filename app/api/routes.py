from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.auth.routes import get_current_external_id
from app.config import settings
from app.db.bootstrap import init_database
from app.db.session import check_db_health
from app.db.sync import sync_user_snapshot
from app.ingest.parsers import SUPPORTED_EXTENSIONS
from app.rag.search import search_docs_with_metadata
from app.services.context_router import analyze_question
from app.services.llm_service import check_lm_studio_health, generate_obsidian_answer
from app.services.obsidian_context import build_obsidian_context, debug_obsidian_files
from app.schemas import (
    ChatRequest,
    ConsolidationRunRequest,
    ConsolidationRunResponse,
    CorrectionRequest,
    CorrectionResponse,
    DbHealthResponse,
    IngestResponse,
    LearningConceptItem,
    LearningClusterItem,
    LearningConversationIngestRequest,
    LearningGraphResponse,
    LearningIngestResponse,
    KnowledgeGraphResponse,
    LongTermMemoryItem,
    ReflectionRunResponse,
    ReflectionSummaryResponse,
    ScoredMemoryItem,
)


router = APIRouter(tags=["api"])


def _learning_pipeline():
    from app.learning.pipeline import learning_pipeline

    return learning_pipeline


def _learning_graph_store():
    from app.learning.graph import learning_graph_store

    return learning_graph_store


def _concept_cluster_engine():
    from app.learning.clustering import concept_cluster_engine

    return concept_cluster_engine


def _consolidation_engine():
    from app.learning.consolidation import consolidation_engine

    return consolidation_engine


def _reflection_engine():
    from app.learning.reflection import reflection_engine

    return reflection_engine


def _memory_scoring_engine():
    from app.learning.scoring import memory_scoring_engine

    return memory_scoring_engine


def _semantic_linker():
    from app.learning.semantic_linking import semantic_linker

    return semantic_linker


def _long_term_memory():
    from app.memory.long_term import long_term_memory

    return long_term_memory


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/llm/health")
def llm_health() -> dict[str, object]:
    health_result = check_lm_studio_health()
    return {
        "status": "ok" if health_result.ready else "error",
        "ready": health_result.ready,
        "base_url": health_result.base_url,
        "model": health_result.model,
        "error": health_result.error,
    }


@router.get("/db/health", response_model=DbHealthResponse)
def db_health():
    is_ok, detail = check_db_health()
    return {
        "status": "ok" if is_ok else "error",
        "detail": detail,
    }


@router.post("/db/init", response_model=DbHealthResponse)
def db_init():
    try:
        init_database()
        return {
            "status": "ok",
            "detail": "database schema initialized",
        }
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
        }


@router.post("/db/sync/user/{user_id}")
def db_sync_user(
    user_id: str,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot sync another user.",
        )
    try:
        result = sync_user_snapshot(user_id)
        return {
            "status": "ok",
            "user_id": user_id,
            "synced": result,
        }
    except Exception as exc:
        return {
            "status": "error",
            "user_id": user_id,
            "detail": str(exc),
        }


def _build_light_chat_reply(message: str) -> str:
    normalized = (message or "").strip()
    if not normalized:
        return "Bu konuda veri bulunamadı."
    return "Mesajın alındı. Hafif cevap modu aktif."


def _clean_document_filter_list(values: list[str] | None) -> list[str]:
    bad_values = {"", "string", "null", "undefined"}
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text.lower() in bad_values:
            continue
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def _route_debug(route: object) -> dict[str, object]:
    return {
        "area": getattr(route, "area", ""),
        "topic": getattr(route, "topic", ""),
        "intent": getattr(route, "intent", ""),
        "concepts": getattr(route, "concepts", []),
        "obsidian_keys": getattr(route, "obsidian_keys", []),
        "source_pool": getattr(route, "source_pool", ""),
        "confidence": getattr(route, "confidence", 0.0),
    }


def _requires_source_document(message: str, route: object) -> tuple[bool, str]:
    text = (message or "").lower()
    source_bound_phrases = [
        "belgeye göre",
        "belgeye gore",
        "belgede",
        "belgedeki",
        "dokümanda",
        "dokumanda",
        "dokümandaki",
        "dokumandaki",
        "dosyada",
        "dosyadaki",
        "yüklediğim",
        "yukledigim",
        "yüklenen",
        "yuklenen",
        "kaynaklarda",
        "kaynak belge",
        "sayfa",
        "madde",
        "maddeleri",
    ]
    explicit_document_keywords = [
        "şartname",
        "sartname",
        "sözleşme",
        "sozlesme",
        "pdf",
        "drive",
        "notebooklm",
        "teknik şartname",
        "teknik sartname",
        "doküman",
        "dokuman",
        *source_bound_phrases,
    ]
    retrieval_verbs = ["getir", "çıkar", "cikar", "bul", "listele", "özetle", "ozetle"]
    is_document_nouns = ["şartname", "sartname", "sözleşme", "sozlesme", "ihale", "tutanak", "madde"]

    if getattr(route, "area", "") == "Boran.ai" and not any(phrase in text for phrase in source_bound_phrases):
        return False, ""

    for keyword in explicit_document_keywords:
        if keyword in text:
            return True, f"explicit_document_keyword:{keyword}"

    if getattr(route, "area", "") == "Is":
        has_doc_noun = any(keyword in text for keyword in is_document_nouns)
        has_retrieval_verb = any(keyword in text for keyword in retrieval_verbs)
        if has_doc_noun and has_retrieval_verb:
            return True, "is_document_retrieval_intent"

    return False, ""


def _build_missing_document_reply(route: object) -> str:
    concepts = ", ".join(getattr(route, "concepts", []) or [])
    topic = getattr(route, "topic", "") or "-"
    concept_text = f" / {concepts}" if concepts else ""
    return (
        f"Bu soru {getattr(route, 'area', 'Genel')} / {topic}{concept_text} alanına yönlendirildi. "
        "Ancak gerçek belge/RAG kaynağı taranmadan kesin madde getirilemez."
    )


def _build_document_context(req: ChatRequest, user_id: str | None) -> tuple[str, dict[str, object]]:
    try:
        retrieval = search_docs_with_metadata(
            query=req.message,
            n_results=max(1, req.top_k or settings.chat_doc_context_limit),
            user_id=user_id,
            source_ids=_clean_document_filter_list(req.source_ids),
            file_names=_clean_document_filter_list(req.file_names),
            recent_documents=req.recent_documents,
            context_scope=req.context_scope,
            similarity_threshold=req.similarity_threshold,
        )
    except Exception as exc:
        return "", {
            "doc_context_hits": 0,
            "doc_sources": [],
            "matched_source_ids": [],
            "matched_file_names": [],
            "retrieval_fallback_used": False,
            "retrieval_debug": {
                "error": str(exc),
                "reason": "retrieval_exception",
            },
        }

    document_context = "\n\n".join(hit.prompt_block() for hit in retrieval.hits).strip()
    max_chars = max(400, settings.chat_max_context_chars)
    if len(document_context) > max_chars:
        document_context = document_context[: max_chars - 3].rstrip() + "..."
    debug = {
        "doc_context_hits": len(retrieval.hits),
        "doc_sources": list(dict.fromkeys(hit.original_file_name for hit in retrieval.hits if hit.original_file_name)),
        "matched_source_ids": list(dict.fromkeys(hit.source_id for hit in retrieval.hits if hit.source_id)),
        "matched_file_names": list(
            dict.fromkeys(hit.original_file_name for hit in retrieval.hits if hit.original_file_name)
        ),
        "retrieval_fallback_used": bool(retrieval.debug.get("fallback_used", False)),
        "retrieval_debug": retrieval.debug,
    }
    return document_context, debug


def _should_use_obsidian_context(route: object, requires_document: bool) -> bool:
    if requires_document:
        return False
    return getattr(route, "area", "") == "Boran.ai"


def _used_obsidian_files(debug_files: list[dict[str, object]], context: str) -> list[dict[str, object]]:
    if not context.strip():
        return []
    return [item for item in debug_files if item.get("exists") is True]


@router.post("/chat", response_model=dict[str, object])
def chat(
    req: ChatRequest,
    request: Request,
):
    try:
        route = analyze_question(req.message)
        user_id = req.user_id or getattr(request.state, "auth_external_id", None)
        document_context, document_debug = _build_document_context(req=req, user_id=user_id)
        requires_doc, document_reason = _requires_source_document(req.message, route)
        should_use_obsidian = _should_use_obsidian_context(route, requires_doc)
        obsidian_context = build_obsidian_context(route.obsidian_keys) if should_use_obsidian else ""
        obsidian_debug = _used_obsidian_files(
            debug_obsidian_files(route.obsidian_keys) if obsidian_context.strip() else [],
            obsidian_context,
        )
        route_payload = _route_debug(route)
        route_payload["requires_document"] = requires_doc
        used_contexts = {
            "obsidian": bool(obsidian_context.strip()),
            "document": bool(document_context.strip()),
        }
        if requires_doc and not document_context.strip():
            reply = _build_missing_document_reply(route)
            return {
                "user_id": user_id or "",
                "reply": reply,
                "answer": reply,
                "used_llm": False,
                "llm_error": "",
                "route": route_payload,
                "domain": route_payload.get("area", ""),
                "used_contexts": used_contexts,
                "requires_document": True,
                "router_bypass_reason": document_reason or "document_context_missing",
                "obsidian_context_chars": len(obsidian_context),
                "obsidian_files_found": len(obsidian_debug),
                "obsidian_files": obsidian_debug,
                "document_context": "",
                "document_context_chars": 0,
                **document_debug,
            }
        llm_answer = generate_obsidian_answer(
            message=req.message,
            route=route,
            obsidian_context=obsidian_context,
            document_context=document_context,
        )
        reply = llm_answer.reply

        return {
            "user_id": user_id or "",
            "reply": reply,
            "answer": reply,
            "used_llm": llm_answer.used_llm,
            "llm_error": llm_answer.error,
            "route": route_payload,
            "domain": route_payload.get("area", ""),
            "used_contexts": used_contexts,
            "requires_document": requires_doc,
            "router_bypass_reason": "",
            "obsidian_context_chars": len(obsidian_context),
            "obsidian_files_found": len(obsidian_debug),
            "obsidian_files": obsidian_debug,
            "document_context": document_context,
            "document_context_chars": len(document_context),
            **document_debug,
        }

    except Exception as exc:
        fallback = f"Yönlendirme testi sırasında hata oluştu: {exc}"
        return {
            "user_id": "",
            "reply": fallback,
            "answer": fallback,
            "used_llm": False,
            "llm_error": str(exc),
            "route": {},
            "domain": "",
            "used_contexts": {
                "obsidian": False,
                "document": False,
            },
            "requires_document": False,
            "router_bypass_reason": "chat_endpoint_exception",
        }


def _save_upload(file: UploadFile) -> Path:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    safe_file_name = Path(file.filename).name
    if not safe_file_name:
        raise HTTPException(status_code=400, detail="Missing filename.")
    ext = Path(safe_file_name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext or 'none'}")

    max_size_bytes = max(1, settings.upload_max_file_size_mb) * 1024 * 1024
    target_dir = Path(settings.ingest_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / safe_file_name

    written = 0
    try:
        with target_file.open("wb") as fp:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Dosya boyutu {settings.upload_max_file_size_mb} MB sinirini asiyor.",
                    )
                fp.write(chunk)
    except HTTPException:
        if target_file.exists():
            target_file.unlink(missing_ok=True)
        raise

    return target_file


@router.post("/ingest/file", response_model=IngestResponse)
def ingest_single_file(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    tags: str | None = Form(default=None),
    current_user_id: str = Depends(get_current_external_id),
):
    target_file = _save_upload(file)
    try:
        pipeline_result = _learning_pipeline().ingest_document(
            user_id=current_user_id,
            file_path=str(target_file),
            category=category,
            tags=tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = pipeline_result.details
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result.get("message", "ingest failed"))
    return result


@router.post("/documents/upload", response_model=IngestResponse)
def documents_upload(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    tags: str | None = Form(default=None),
    current_user_id: str = Depends(get_current_external_id),
):
    return ingest_single_file(
        file=file,
        category=category,
        tags=tags,
        current_user_id=current_user_id,
    )


@router.post("/ingest/pdf", response_model=IngestResponse)
def ingest_single_pdf(
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_external_id),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    target_file = _save_upload(file)
    try:
        pipeline_result = _learning_pipeline().ingest_document(
            user_id=current_user_id,
            file_path=str(target_file),
            category="pdf",
            tags="pdf",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = pipeline_result.details
    if result.get("status") != "ok":
        raise HTTPException(status_code=400, detail=result.get("message", "ingest failed"))
    return result


@router.post("/ingest/folder")
def ingest_folder_endpoint(
    folder_path: str | None = None,
    category: str = "general",
    tags: str | None = None,
    current_user_id: str = Depends(get_current_external_id),
):
    target_folder = folder_path or settings.pdf_path
    results: list[dict[str, object]] = []
    path = Path(target_folder)
    if not path.exists():
        return {
            "results": [
                {
                    "status": "error",
                    "file": target_folder,
                    "message": "Folder not found.",
                }
            ]
        }

    for file_name in path.iterdir():
        if file_name.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        pipeline_result = _learning_pipeline().ingest_document(
            user_id=current_user_id,
            file_path=str(file_name),
            category=category,
            tags=tags,
        )
        details = dict(pipeline_result.details)
        details["status"] = pipeline_result.status
        results.append(details)

    return {
        "results": results
    }


@router.post("/feedback/correction", response_model=CorrectionResponse)
def add_correction(
    req: CorrectionRequest,
    current_user_id: str = Depends(get_current_external_id),
):
    if req.user_id and req.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add correction for another user.",
        )
    try:
        from app.learning.corrections import record_correction

        correction_id = record_correction(
            user_id=current_user_id,
            original_answer=req.original_answer,
            corrected_answer=req.corrected_answer,
            note=req.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "ok",
        "user_id": current_user_id,
        "correction_id": correction_id,
    }


@router.post("/jobs/consolidation/run", response_model=ConsolidationRunResponse)
def run_consolidation(
    req: ConsolidationRunRequest,
    current_user_id: str = Depends(get_current_external_id),
):
    if req.user_id and req.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot run consolidation for another user.",
        )

    if req.user_id:
        result = _consolidation_engine().run_for_user(req.user_id)
        return {
            "status": str(result.get("status", "ok")),
            "user_id": req.user_id,
            "processed_users": 1,
            "summaries_created": int(result.get("summary_created", 0)),
        }

    result = _consolidation_engine().run_for_user(current_user_id)
    return {
        "status": str(result.get("status", "ok")),
        "user_id": current_user_id,
        "processed_users": 1,
        "summaries_created": int(result.get("summary_created", 0)),
    }


@router.get("/jobs/consolidation/state")
def consolidation_state(
    current_user_id: str = Depends(get_current_external_id),
):
    state = _consolidation_engine().get_state()
    return {
        "status": "ok",
        "state": {
            current_user_id: state.get(current_user_id)
        },
    }


@router.get("/memory/long-term/{user_id}", response_model=list[LongTermMemoryItem])
def get_long_term_memory(
    user_id: str,
    limit: int = 30,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access memory of another user.",
        )
    return _long_term_memory().list_user(user_id=user_id, limit=limit)


@router.get("/knowledge/graph/{user_id}", response_model=KnowledgeGraphResponse)
def get_knowledge_graph(
    user_id: str,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access graph of another user.",
        )
    graph = _learning_graph_store().get_graph(user_id=user_id, max_nodes=30, max_edges=50)
    nodes = [
        {"id": str(node["term"]), "weight": int(node["frequency"])}
        for node in graph["nodes"]
    ]
    edges = [
        {
            "source": str(edge["source"]),
            "target": str(edge["target"]),
            "relation": str(edge["relation"]),
            "weight": int(edge["weight"]),
        }
        for edge in graph["edges"]
    ]
    return {
        "user_id": user_id,
        "nodes": nodes,
        "edges": edges,
    }


@router.post("/learning/ingest/document", response_model=LearningIngestResponse)
def learning_ingest_document(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    tags: str | None = Form(default=None),
    current_user_id: str = Depends(get_current_external_id),
):
    target_file = _save_upload(file)
    try:
        result = _learning_pipeline().ingest_document(
            user_id=current_user_id,
            file_path=str(target_file),
            category=category,
            tags=tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document ingest failed: {exc}") from exc

    details = dict(result.details)
    if result.status != "ok" or details.get("status") != "ok":
        raise HTTPException(status_code=400, detail=str(details.get("message", "ingest failed")))

    chunk_count = int(details.get("chunk_count") or details.get("chunks") or 0)
    response_file = str(details.get("file") or target_file)
    return {
        "status": "ok",
        "file": response_file,
        "chunks": chunk_count,
        "message": "Belge yuklendi",
        "details": details,
    }


@router.post("/learning/ingest/conversation", response_model=LearningIngestResponse)
def learning_ingest_conversation(
    req: LearningConversationIngestRequest,
    current_user_id: str = Depends(get_current_external_id),
):
    result = _learning_pipeline().ingest_conversation(
        user_id=current_user_id,
        role=req.role,
        text=req.text,
        source=req.source,
        save_vector_memory=req.save_vector_memory,
    )
    return {
        "status": result.status,
        "details": result.details,
    }


@router.get("/learning/concepts/{user_id}", response_model=list[LearningConceptItem])
def learning_concepts(
    user_id: str,
    limit: int = 100,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access concepts of another user.",
        )
    return _learning_graph_store().get_concepts(user_id=user_id, limit=limit)


@router.get("/learning/graph/{user_id}", response_model=LearningGraphResponse)
def learning_graph(
    user_id: str,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access graph of another user.",
        )
    graph = _learning_graph_store().get_graph(user_id=user_id)
    return {
        "user_id": user_id,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
    }


@router.get("/learning/graph/{user_id}/related")
def learning_graph_related(
    user_id: str,
    term: str,
    limit: int = 20,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access graph of another user.",
        )
    return {
        "user_id": user_id,
        "term": term,
        "related": _learning_graph_store().related_terms(user_id=user_id, term=term, limit=limit),
    }


@router.get("/learning/graph/{user_id}/semantic")
def learning_graph_semantic(
    user_id: str,
    term: str,
    limit: int = 12,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access graph of another user.",
        )
    return {
        "user_id": user_id,
        "term": term,
        "related": _semantic_linker().lookup_similar_terms(user_id=user_id, term=term, limit=limit),
    }


@router.get("/learning/clusters/{user_id}", response_model=list[LearningClusterItem])
def learning_clusters(
    user_id: str,
    limit: int = 20,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access clusters of another user.",
        )
    clusters = _concept_cluster_engine().list_clusters(user_id=user_id, limit=limit)
    if not clusters:
        clusters = _concept_cluster_engine().build_clusters(user_id=user_id)[:limit]
    return clusters


@router.get("/learning/memory/top/{user_id}", response_model=list[ScoredMemoryItem])
def learning_memory_top(
    user_id: str,
    query: str = "",
    limit: int = 12,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access memory of another user.",
        )
    return _memory_scoring_engine().top_memories(
        user_id=user_id,
        query=query,
        limit=limit,
    )


@router.post("/learning/reflect/{user_id}", response_model=ReflectionRunResponse)
def learning_reflect(
    user_id: str,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reflect another user.",
        )
    result = _reflection_engine().reflect_user(user_id=user_id, persist=True)
    generated = result.get("generated", {})
    return {
        "status": str(result.get("status", "ok")),
        "user_id": user_id,
        "stored_count": int(result.get("stored_count", 0)),
        "generated_kinds": sorted(generated.keys()),
        "source_counts": result.get("source_counts", {}),
    }


@router.get("/learning/reflections/{user_id}", response_model=list[LongTermMemoryItem])
def learning_reflections(
    user_id: str,
    limit: int = 30,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access reflections of another user.",
        )
    return _reflection_engine().list_reflections(user_id=user_id, limit=limit)


@router.get("/learning/summary/{user_id}", response_model=ReflectionSummaryResponse)
def learning_summary(
    user_id: str,
    current_user_id: str = Depends(get_current_external_id),
):
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access summary of another user.",
        )
    return _reflection_engine().get_summary(user_id=user_id)

