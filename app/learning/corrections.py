import os
import uuid
from datetime import datetime, timezone

import chromadb

from app.config import settings
from app.db.sync import sync_correction, sync_knowledge_edges, sync_memory_item
from app.learning.extractor import concept_extractor
from app.learning.graph import learning_graph_store
from app.memory.long_term import long_term_memory
from app.rag.embeddings import encode_texts


def get_collection():
    os.makedirs(settings.chroma_path, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(settings.corrections_collection)


def _build_document(original_answer: str, corrected_answer: str, note: str | None) -> str:
    lines = [
        f"Original answer: {original_answer.strip()}",
        f"Corrected answer: {corrected_answer.strip()}",
    ]
    if note and note.strip():
        lines.append(f"Note: {note.strip()}")
    return "\n".join(lines)


def record_correction(
    user_id: str,
    original_answer: str,
    corrected_answer: str,
    note: str | None = None,
) -> str:
    correction_id = str(uuid.uuid4())
    document = _build_document(original_answer, corrected_answer, note)
    created_at = datetime.now(tz=timezone.utc).isoformat()
    try:
        embedding = encode_texts([document])[0]
        collection = get_collection()
        collection.add(
            ids=[correction_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[
                {
                    "user_id": user_id,
                    "source": "user_correction",
                    "created_at": created_at,
                }
            ],
        )
    except Exception as exc:
        print(f"Correction vector write error: {exc}")

    long_term_memory.add(
        user_id=user_id,
        text=document,
        kind="correction",
        source="feedback",
        metadata={"created_at": created_at},
    )
    extraction = concept_extractor.extract(corrected_answer)
    learning_graph_store.update_from_extraction(user_id=user_id, result=extraction)

    if settings.database_url:
        try:
            sync_correction(
                user_external_id=user_id,
                original_answer=original_answer,
                corrected_answer=corrected_answer,
                note=note,
            )
            sync_memory_item(
                user_external_id=user_id,
                kind="correction",
                text=document,
                source="feedback",
                metadata_json={"created_at": created_at},
            )
            graph = learning_graph_store.get_graph(user_id=user_id, max_nodes=120, max_edges=150)
            sync_knowledge_edges(user_external_id=user_id, edges=graph["edges"])
        except Exception as exc:
            print(f"DB correction sync error: {exc}")

    return correction_id


def search_corrections(user_id: str, query: str, n_results: int = 3) -> list[str]:
    try:
        collection = get_collection()
        embedding = encode_texts([query])
        results = collection.query(
            query_embeddings=embedding,
            n_results=n_results,
            where={"user_id": user_id},
        )
    except Exception as exc:
        print(f"Correction search error: {exc}")
        return []

    documents = results.get("documents", [[]])
    if not documents or not documents[0]:
        return []

    output: list[str] = []
    for doc in documents[0]:
        output.append(f"[Correction memory]\n{doc}")
    return output
