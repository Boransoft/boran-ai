from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth.routes import get_current_external_id
from app.config import settings
from app.db.bootstrap import init_database
from app.db.session import check_db_health
from app.db.sync import sync_user_snapshot
from app.ingest.parsers import SUPPORTED_EXTENSIONS
from app.learning.graph import learning_graph_store
from app.learning.clustering import concept_cluster_engine
from app.learning.consolidation import consolidation_engine
from app.learning.corrections import record_correction
from app.learning.pipeline import learning_pipeline
from app.learning.reflection import reflection_engine
from app.learning.scoring import memory_scoring_engine
from app.learning.semantic_linking import semantic_linker
from app.memory.long_term import long_term_memory
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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


def _build_local_chat_reply(message: str) -> str:
    text = message.strip().lower()

    if "havas" in text:
        return (
            "Havas ilmi, gelenekte harfler, sayilar ve dualar arasindaki manevi "
            "iliskileri konu alan bir alandir; bu konularda guvenilir ve ehil "
            "kaynaklardan ilerlemek onemlidir."
        )

    if any(keyword in text for keyword in ("islam", "islami kaynak", "tasavvuf")):
        return (
            "Islami kaynaklarda temel referans Kur'an ve sahih sunnette aranir. "
            "Tasavvuf ise ihlas, nefis terbiyesi ve guzel ahlaka odaklanan bir "
            "manevi egitim yoludur."
        )

    return (
        "Sorunu anladim. Daha net ve kisa bir yanit verebilmem icin konuyu biraz "
        "daha detaylandirirsan adim adim yardimci olabilirim."
    )


@router.post("/chat", response_model=dict[str, str])
def chat(
    req: ChatRequest | None = None,
):
    _ = req
    return {
        "reply": "Boran AI çalışıyor",
        "answer": "Boran AI çalışıyor",
    }


def _save_upload(file: UploadFile) -> Path:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    max_size_bytes = max(1, settings.upload_max_file_size_mb) * 1024 * 1024
    target_dir = Path(settings.ingest_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / file.filename

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
        pipeline_result = learning_pipeline.ingest_document(
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
        pipeline_result = learning_pipeline.ingest_document(
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
        pipeline_result = learning_pipeline.ingest_document(
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
        result = consolidation_engine.run_for_user(req.user_id)
        return {
            "status": str(result.get("status", "ok")),
            "user_id": req.user_id,
            "processed_users": 1,
            "summaries_created": int(result.get("summary_created", 0)),
        }

    result = consolidation_engine.run_for_user(current_user_id)
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
    state = consolidation_engine.get_state()
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
    return long_term_memory.list_user(user_id=user_id, limit=limit)


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
    graph = learning_graph_store.get_graph(user_id=user_id, max_nodes=30, max_edges=50)
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
        result = learning_pipeline.ingest_document(
            user_id=current_user_id,
            file_path=str(target_file),
            category=category,
            tags=tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": result.status,
        "details": result.details,
    }


@router.post("/learning/ingest/conversation", response_model=LearningIngestResponse)
def learning_ingest_conversation(
    req: LearningConversationIngestRequest,
    current_user_id: str = Depends(get_current_external_id),
):
    result = learning_pipeline.ingest_conversation(
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
    return learning_graph_store.get_concepts(user_id=user_id, limit=limit)


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
    graph = learning_graph_store.get_graph(user_id=user_id)
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
        "related": learning_graph_store.related_terms(user_id=user_id, term=term, limit=limit),
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
        "related": semantic_linker.lookup_similar_terms(user_id=user_id, term=term, limit=limit),
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
    clusters = concept_cluster_engine.list_clusters(user_id=user_id, limit=limit)
    if not clusters:
        clusters = concept_cluster_engine.build_clusters(user_id=user_id)[:limit]
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
    return memory_scoring_engine.top_memories(
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
    result = reflection_engine.reflect_user(user_id=user_id, persist=True)
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
    return reflection_engine.list_reflections(user_id=user_id, limit=limit)


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
    return reflection_engine.get_summary(user_id=user_id)

