import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import chromadb

from app.config import settings
from app.rag.document_sources import list_recent_document_sources
from app.rag.embeddings import encode_texts


logger = logging.getLogger("uvicorn.error")

FILE_NAME_PATTERN = re.compile(
    r"([^\s,;:()\"']+\.(?:pdf|doc|docx|txt|md|png|jpg|jpeg|webp))",
    re.IGNORECASE,
)


def _clean_list(values: list[str] | None) -> list[str]:
    output: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output


def _normalize_file_name(value: str) -> str:
    text = value.strip().lower().replace("\\", "/")
    text = text.split("/")[-1]
    mojibake_map = {
        "Ã¼": "u",
        "Ã¶": "o",
        "Ã§": "c",
        "ÄŸ": "g",
        "ÅŸ": "s",
        "Ä±": "i",
        "Ä°": "i",
    }
    for bad, good in mojibake_map.items():
        text = text.replace(bad, good)
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    text = re.sub(r"[^a-z0-9._-]+", "", text)
    text = " ".join(text.split())
    return text


def _extract_file_name_hints(query: str) -> list[str]:
    matches = FILE_NAME_PATTERN.findall(query or "")
    output: list[str] = []
    for match in matches:
        normalized = _normalize_file_name(match)
        if normalized and normalized not in output:
            output.append(normalized)
    return output


def _looks_like_recent_document_question(query: str) -> bool:
    lowered = query.lower()
    return (
        "son yüklediğim" in lowered
        or "son yukledigim" in lowered
        or "son belge" in lowered
        or "az önce yüklediğim" in lowered
        or "az once yukledigim" in lowered
        or "az önceki belge" in lowered
        or "az onceki belge" in lowered
        or "last uploaded" in lowered
    )


def query_collection(
    query: str,
    collection_name: str,
    n_results: int = 3,
    where: dict[str, object] | None = None,
) -> dict[str, object]:
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_or_create_collection(collection_name)
    embedding = encode_texts([query])
    return collection.query(
        query_embeddings=embedding,
        n_results=n_results,
        where=where,
    )


@dataclass
class DocumentHit:
    text: str
    source_id: str
    document_id: str
    original_file_name: str
    normalized_file_name: str
    mime_type: str
    source_type: str
    category: str
    method: str
    upload_time: str
    distance: float | None

    def prompt_block(self) -> str:
        return (
            "[Doc "
            f"source_id={self.source_id} "
            f"file={self.original_file_name} "
            f"type={self.source_type} "
            f"mime={self.mime_type} "
            f"category={self.category}"
            "]\n"
            f"{self.text}"
        )


@dataclass
class SearchDocsResult:
    hits: list[DocumentHit]
    debug: dict[str, object]


def _metadata_to_hit(doc_text: str, metadata: dict[str, object], distance: float | None) -> DocumentHit:
    source_id = str(metadata.get("source_id") or metadata.get("source") or "").strip()
    original_file_name = str(
        metadata.get("original_file_name") or metadata.get("file_name") or metadata.get("source") or source_id
    ).strip()
    normalized_file_name = str(metadata.get("normalized_file_name") or _normalize_file_name(original_file_name)).strip()
    return DocumentHit(
        text=doc_text,
        source_id=source_id,
        document_id=str(metadata.get("document_id") or source_id).strip(),
        original_file_name=original_file_name or source_id,
        normalized_file_name=normalized_file_name,
        mime_type=str(metadata.get("mime_type") or metadata.get("content_type") or "application/octet-stream"),
        source_type=str(metadata.get("source_type") or metadata.get("content_type") or "document"),
        category=str(metadata.get("category") or "general"),
        method=str(metadata.get("method") or "unknown"),
        upload_time=str(metadata.get("upload_time") or metadata.get("uploaded_at") or ""),
        distance=distance,
    )


def _build_where(
    user_id: str | None,
    source_ids: list[str] | None = None,
    normalized_file_names: list[str] | None = None,
    raw_file_names: list[str] | None = None,
) -> dict[str, object] | None:
    clauses: list[dict[str, object]] = []
    if user_id:
        clauses.append({"user_id": user_id})

    hint_clauses: list[dict[str, object]] = []
    if source_ids:
        hint_clauses.append({"source_id": {"$in": source_ids}})
    if normalized_file_names:
        hint_clauses.append({"normalized_file_name": {"$in": normalized_file_names}})
    if raw_file_names:
        hint_clauses.append({"source": {"$in": raw_file_names}})
        hint_clauses.append({"file_name": {"$in": raw_file_names}})
        hint_clauses.append({"original_file_name": {"$in": raw_file_names}})

    if hint_clauses:
        if len(hint_clauses) == 1:
            clauses.append(hint_clauses[0])
        else:
            clauses.append({"$or": hint_clauses})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _run_stage_query(
    query: str,
    n_results: int,
    where: dict[str, object] | None,
) -> tuple[list[DocumentHit], dict[str, object]]:
    try:
        results = query_collection(
            query=query,
            collection_name=settings.documents_collection,
            n_results=n_results,
            where=where,
        )
    except Exception as exc:
        logger.warning("retrieval_query_error where=%s error=%s", where, exc)
        return [], {"error": str(exc)}

    documents = results.get("documents", [[]])
    metadatas = results.get("metadatas", [[]])
    distances = results.get("distances", [[]])
    if not documents or not documents[0]:
        return [], {"raw_hits": 0}

    hits: list[DocumentHit] = []
    for idx, text in enumerate(documents[0]):
        metadata = {}
        if metadatas and metadatas[0] and idx < len(metadatas[0]):
            metadata = metadatas[0][idx] or {}
        distance = None
        if distances and distances[0] and idx < len(distances[0]):
            try:
                distance = float(distances[0][idx])
            except Exception:
                distance = None
        hits.append(_metadata_to_hit(text, metadata, distance))
    return hits, {"raw_hits": len(hits)}


def _rerank_hits(
    hits: list[DocumentHit],
    n_results: int,
    requested_source_ids: set[str],
    requested_file_names: set[str],
    recent_source_ids: set[str],
    recent_file_names: set[str],
    query_file_names: set[str],
    prefer_recent: bool,
    similarity_threshold: float | None = None,
) -> tuple[list[DocumentHit], dict[str, object]]:
    scored: list[tuple[float, int, DocumentHit]] = []
    for index, hit in enumerate(hits):
        semantic_score = 0.5
        if hit.distance is not None:
            semantic_score = 1.0 / (1.0 + max(hit.distance, 0.0))
        if similarity_threshold is not None and semantic_score < similarity_threshold:
            continue

        boost = 0.0
        if hit.source_id and hit.source_id in requested_source_ids:
            boost += 0.40
        if hit.source_id and hit.source_id in recent_source_ids:
            boost += 0.25
        if hit.normalized_file_name and hit.normalized_file_name in requested_file_names:
            boost += 0.35
        if hit.normalized_file_name and hit.normalized_file_name in recent_file_names:
            boost += 0.20
        if hit.normalized_file_name and hit.normalized_file_name in query_file_names:
            boost += 0.30
        if prefer_recent and hit.source_id and hit.source_id in recent_source_ids:
            boost += 0.15

        scored.append((semantic_score + boost, index, hit))

    scored.sort(key=lambda item: (-item[0], item[1]))
    deduped_ranked: list[DocumentHit] = []
    seen: set[tuple[str, str]] = set()
    for _, _, hit in scored:
        dedupe_key = (hit.source_id, hit.text[:120])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped_ranked.append(hit)

    target_count = max(1, n_results)
    unique_sources = {
        (hit.source_id or hit.document_id or f"unknown:{index}")
        for index, hit in enumerate(deduped_ranked)
    }
    configured_min_cap = max(1, settings.rag_per_source_cap_min)
    configured_max_cap = max(configured_min_cap, settings.rag_per_source_cap_max)
    if len(unique_sources) <= 1:
        per_source_cap = target_count
    else:
        # For top_k=12, dynamic cap becomes 4 with default settings.
        dynamic_cap = max(configured_min_cap, (target_count + 2) // 3)
        per_source_cap = min(configured_max_cap, dynamic_cap)

    selected: list[DocumentHit] = []
    source_counts: dict[str, int] = {}
    overflow_by_source: dict[str, list[DocumentHit]] = {}
    source_order: list[str] = []
    source_order_index: dict[str, int] = {}

    for hit in deduped_ranked:
        source_key = hit.source_id or hit.document_id or "__unknown__"
        count = source_counts.get(source_key, 0)
        if count >= per_source_cap:
            if source_key not in overflow_by_source:
                overflow_by_source[source_key] = []
                source_order.append(source_key)
                source_order_index[source_key] = len(source_order) - 1
            overflow_by_source[source_key].append(hit)
            continue
        selected.append(hit)
        source_counts[source_key] = count + 1
        if len(selected) >= target_count:
            break

    if len(selected) < target_count:
        while len(selected) < target_count:
            available_sources = [key for key in source_order if overflow_by_source.get(key)]
            if not available_sources:
                break
            available_sources.sort(key=lambda key: (source_counts.get(key, 0), source_order_index.get(key, 10_000)))
            chosen_source = available_sources[0]
            hit = overflow_by_source[chosen_source].pop(0)
            selected.append(hit)
            source_counts[chosen_source] = source_counts.get(chosen_source, 0) + 1

    diversity: dict[str, int] = {}
    for hit in selected:
        source_key = hit.source_id or hit.document_id or "__unknown__"
        diversity[source_key] = diversity.get(source_key, 0) + 1

    return selected, {
        "per_source_cap": per_source_cap,
        "per_source_cap_config": {
            "min": configured_min_cap,
            "max": configured_max_cap,
        },
        "unique_sources_in_pool": len(unique_sources),
        "selected_source_distribution": diversity,
    }


def search_docs_with_metadata(
    query: str,
    n_results: int = 3,
    user_id: str | None = None,
    source_ids: list[str] | None = None,
    file_names: list[str] | None = None,
    recent_documents: list[dict[str, object]] | None = None,
    context_scope: str | None = None,
    similarity_threshold: float | None = None,
) -> SearchDocsResult:
    if not query.strip():
        return SearchDocsResult(
            hits=[],
            debug={"reason": "empty_query", "doc_context_hits": 0},
        )
    scoped_user_id = str(user_id or "").strip()
    if not scoped_user_id:
        logger.warning("retrieval_blocked_missing_user_scope query=%s", query)
        return SearchDocsResult(
            hits=[],
            debug={
                "reason": "missing_user_scope",
                "doc_context_hits": 0,
                "fallback_used": False,
            },
        )

    cleaned_source_ids = _clean_list(source_ids)
    cleaned_file_names = _clean_list(file_names)
    normalized_requested_file_names = [_normalize_file_name(name) for name in cleaned_file_names]

    recent_source_ids: list[str] = []
    recent_file_names: list[str] = []
    recent_pairs: list[tuple[str, str]] = []
    for item in recent_documents or []:
        source_id = str(item.get("source_id") or "").strip()
        file_name = str(item.get("file_name") or "").strip()
        if source_id and source_id not in recent_source_ids:
            recent_source_ids.append(source_id)
        if file_name:
            normalized = _normalize_file_name(file_name)
            if normalized and normalized not in recent_file_names:
                recent_file_names.append(normalized)
            if source_id and normalized:
                recent_pairs.append((source_id, normalized))

    if scoped_user_id and not recent_source_ids:
        for item in list_recent_document_sources(user_id=scoped_user_id, limit=8):
            source_id = str(item.get("source_id") or "").strip()
            file_name = str(item.get("original_file_name") or item.get("file_name") or "").strip()
            if source_id and source_id not in recent_source_ids:
                recent_source_ids.append(source_id)
            if file_name:
                normalized = _normalize_file_name(file_name)
                if normalized and normalized not in recent_file_names:
                    recent_file_names.append(normalized)
                if source_id and normalized:
                    recent_pairs.append((source_id, normalized))

    query_file_names = _extract_file_name_hints(query)
    prefer_recent = _looks_like_recent_document_question(query)

    stage_plan: list[tuple[str, list[str], list[str], list[str], int]] = []
    explicit_file_names = _clean_list(normalized_requested_file_names + query_file_names)
    explicit_source_ids = _clean_list(cleaned_source_ids)
    for source_id, normalized_name in recent_pairs:
        if normalized_name in explicit_file_names and source_id not in explicit_source_ids:
            explicit_source_ids.append(source_id)
    if explicit_file_names:
        for source_id, normalized_name in recent_pairs:
            for explicit_name in explicit_file_names:
                if not explicit_name or not normalized_name:
                    continue
                if explicit_name.split(".")[-1:] != normalized_name.split(".")[-1:]:
                    continue
                if SequenceMatcher(a=explicit_name, b=normalized_name).ratio() >= 0.78:
                    if source_id not in explicit_source_ids:
                        explicit_source_ids.append(source_id)
                    break
    raw_explicit_file_names = _clean_list(cleaned_file_names)

    if explicit_source_ids or explicit_file_names or raw_explicit_file_names:
        stage_plan.append(
            (
                "explicit_scope",
                explicit_source_ids,
                explicit_file_names,
                raw_explicit_file_names,
                max(n_results * 14, 60),
            )
        )
    if prefer_recent and recent_source_ids:
        stage_plan.append(
            (
                "last_recent_scope",
                [recent_source_ids[0]],
                [recent_file_names[0]] if recent_file_names else [],
                [],
                max(n_results * 10, 40),
            )
        )
    if recent_source_ids or recent_file_names:
        stage_plan.append(
            (
                "recent_scope",
                recent_source_ids,
                recent_file_names,
                [],
                max(n_results * 14, 60),
            )
        )
    stage_plan.append(("user_scope", [], [], [], max(n_results * 18, 90)))

    stage_debug: list[dict[str, object]] = []
    selected_stage = ""
    selected_hits: list[DocumentHit] = []
    used_fallback = False
    seen_stages: set[tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = set()

    for stage_name, stage_source_ids, stage_file_names, stage_raw_file_names, stage_limit in stage_plan:
        stage_key = (
            stage_name,
            tuple(stage_source_ids),
            tuple(stage_file_names),
            tuple(stage_raw_file_names),
        )
        if stage_key in seen_stages:
            continue
        seen_stages.add(stage_key)

        where = _build_where(
            user_id=scoped_user_id,
            source_ids=stage_source_ids or None,
            normalized_file_names=stage_file_names or None,
            raw_file_names=stage_raw_file_names or None,
        )
        hits, stage_meta = _run_stage_query(
            query=query,
            n_results=stage_limit,
            where=where,
        )

        reranked, rerank_meta = _rerank_hits(
            hits=hits,
            n_results=n_results,
            requested_source_ids=set(cleaned_source_ids),
            requested_file_names=set(normalized_requested_file_names),
            recent_source_ids=set(recent_source_ids),
            recent_file_names=set(recent_file_names),
            query_file_names=set(query_file_names),
            prefer_recent=prefer_recent,
            similarity_threshold=similarity_threshold,
        )

        stage_entry: dict[str, object] = {
            "stage": stage_name,
            "where": where,
            **stage_meta,
            "selected_hits": len(reranked),
            **rerank_meta,
        }
        if reranked:
            stage_entry["matched_source_ids"] = [hit.source_id for hit in reranked]
        stage_debug.append(stage_entry)

        if reranked:
            selected_stage = stage_name
            selected_hits = reranked
            used_fallback = stage_name != stage_plan[0][0]
            break

    debug: dict[str, object] = {
        "query": query,
        "context_scope": context_scope or "",
        "filters": {
            "user_id": scoped_user_id,
            "source_ids": cleaned_source_ids,
            "file_names": cleaned_file_names,
            "recent_source_ids": recent_source_ids,
            "recent_file_names": recent_file_names,
            "query_file_names": query_file_names,
            "similarity_threshold": similarity_threshold,
        },
        "stages": stage_debug,
        "selected_stage": selected_stage,
        "fallback_used": used_fallback,
        "doc_context_hits": len(selected_hits),
        "matched_source_ids": [hit.source_id for hit in selected_hits],
        "matched_file_names": [hit.original_file_name for hit in selected_hits],
    }

    logger.info(
        "retrieval_debug user_id=%s stage=%s fallback=%s hits=%s source_filters=%s file_filters=%s matched_sources=%s",
        scoped_user_id,
        selected_stage or "none",
        used_fallback,
        len(selected_hits),
        cleaned_source_ids,
        cleaned_file_names,
        [hit.source_id for hit in selected_hits],
    )
    if not selected_hits:
        logger.warning(
            "retrieval_zero_hits user_id=%s query=%s context_scope=%s source_filters=%s file_filters=%s",
            scoped_user_id,
            query,
            context_scope or "",
            cleaned_source_ids,
            cleaned_file_names,
        )

    return SearchDocsResult(hits=selected_hits, debug=debug)


def search_docs(
    query: str,
    n_results: int = 3,
    user_id: str | None = None,
    source_filters: list[str] | None = None,
) -> list[str]:
    result = search_docs_with_metadata(
        query=query,
        n_results=n_results,
        user_id=user_id,
        source_ids=source_filters,
    )
    return [hit.prompt_block() for hit in result.hits]
