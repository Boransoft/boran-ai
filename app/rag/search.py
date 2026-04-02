import chromadb

from app.config import settings
from app.rag.embeddings import encode_texts


def query_collection(
    query: str,
    collection_name: str,
    n_results: int = 3,
    where: dict[str, str] | None = None,
) -> dict[str, object]:
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_or_create_collection(collection_name)
    embedding = encode_texts([query])
    return collection.query(
        query_embeddings=embedding,
        n_results=n_results,
        where=where,
    )


def search_docs(query: str, n_results: int = 3) -> list[str]:
    results = query_collection(
        query=query,
        collection_name=settings.documents_collection,
        n_results=n_results,
    )

    documents = results.get("documents", [[]])
    metadata = results.get("metadatas", [[]])
    if not documents or not documents[0]:
        return []

    output: list[str] = []
    for index, doc in enumerate(documents[0]):
        meta = metadata[0][index] if metadata and metadata[0] else {}
        source = meta.get("source", "unknown")
        method = meta.get("method", "unknown")
        content_type = meta.get("content_type", "pdf")
        category = meta.get("category", "general")
        output.append(
            f"[Doc source={source} method={method} type={content_type} category={category}]\n{doc}"
        )

    return output
