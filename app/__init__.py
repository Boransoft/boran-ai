import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_PATH = "data/chroma"


def search_docs(query: str):

    model = SentenceTransformer("all-MiniLM-L6-v2")

    embedding = model.encode([query]).tolist()

    client = chromadb.Client(
        chromadb.config.Settings(
            persist_directory=CHROMA_PATH
        )
    )

    collection = client.get_or_create_collection("documents")

    results = collection.query(
        query_embeddings=embedding,
        n_results=3
    )

    return results["documents"][0]