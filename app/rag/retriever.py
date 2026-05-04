import logging

import chromadb

from app.config import settings
from app.rag.embeddings import encode_texts


logger = logging.getLogger("uvicorn.error")


def retrieve_context(query: str, top_k: int = 5) -> list[str]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    safe_top_k = max(1, min(int(top_k or 5), 20))

    try:
        client = chromadb.PersistentClient(path=settings.chroma_path)
        collection = client.get_or_create_collection(settings.documents_collection)
        query_embedding = encode_texts([normalized_query])
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=safe_top_k,
        )
    except Exception as exc:
        logger.warning("retrieve_context_failed query=%s error=%s", normalized_query, exc)
        return []

    documents = results.get("documents", [])
    if not documents:
        return []

    return [
        chunk.strip()
        for chunk in documents[0]
        if isinstance(chunk, str) and chunk.strip()
    ]
