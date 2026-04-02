from sentence_transformers import SentenceTransformer
import chromadb
import uuid
import os

CHROMA_PATH = "data/chroma"
COLLECTION_NAME = "conversation_memory"

model = SentenceTransformer("all-MiniLM-L6-v2")


def get_collection():
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(COLLECTION_NAME)


def save_conversation(user_id: str, role: str, text: str):
    if not text or not text.strip():
        return

    collection = get_collection()
    embedding = model.encode([text]).tolist()[0]

    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[text],
        embeddings=[embedding],
        metadatas=[{
            "user_id": user_id,
            "role": role,
            "source": "conversation"
        }]
    )


def search_conversations(query: str, user_id: str | None = None, n_results: int = 3):
    collection = get_collection()
    embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=embedding,
        n_results=n_results
    )

    docs = results.get("documents", [[]])
    metas = results.get("metadatas", [[]])

    if not docs or not docs[0]:
        return []

    output = []
    for i, doc in enumerate(docs[0]):
        meta = metas[0][i] if metas and metas[0] else {}

        if user_id and meta.get("user_id") != user_id:
            continue

        role = meta.get("role", "unknown")
        output.append(f"[Konuşma | Rol: {role}]\n{doc}")

    return output