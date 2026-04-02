import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "data/chroma"


def search_docs(query: str, n_results: int = 3):
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = model.encode([query]).tolist()

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection("documents")

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
        source = meta.get("source", "bilinmeyen_kaynak")
        method = meta.get("method", "bilinmiyor")
        output.append(f"[Kaynak: {source} | Yöntem: {method}]\n{doc}")

    return output