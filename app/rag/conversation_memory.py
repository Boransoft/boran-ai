import os
import uuid

import chromadb

from app.config import settings
from app.rag.embeddings import encode_texts


def get_collection():
    os.makedirs(settings.chroma_path, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(settings.conversation_collection)


def save_conversation(user_id: str, role: str, text: str) -> None:
    if not text or not text.strip():
        return

    collection = get_collection()
    embedding = encode_texts([text])[0]

    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[text],
        embeddings=[embedding],
        metadatas=[
            {
                "user_id": user_id,
                "role": role,
                "source": "conversation",
            }
        ],
    )


def search_conversations(
    query: str,
    user_id: str | None = None,
    n_results: int = 3,
) -> list[str]:
    collection = get_collection()
    embedding = encode_texts([query])

    where = {"user_id": user_id} if user_id else None
    results = collection.query(
        query_embeddings=embedding,
        n_results=n_results,
        where=where,
    )

    documents = results.get("documents", [[]])
    metadata = results.get("metadatas", [[]])
    if not documents or not documents[0]:
        return []

    output: list[str] = []
    for index, doc in enumerate(documents[0]):
        meta = metadata[0][index] if metadata and metadata[0] else {}
        role = meta.get("role", "unknown")
        output.append(f"[Conversation role={role}]\n{doc}")

    return output
