from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
import os

from app.rag.ocr_utils import extract_text_with_ocr

CHROMA_PATH = "data/chroma"


def split_text(text: str, chunk_size: int = 500, overlap: int = 50):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    full_text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text += page_text + "\n"

    return full_text.strip()


def ingest_pdf(file_path: str):
    os.makedirs(CHROMA_PATH, exist_ok=True)

    full_text = extract_text_from_pdf(file_path)
    method = "normal"

    if not full_text.strip():
        full_text = extract_text_with_ocr(file_path)
        method = "ocr"

    if not full_text.strip():
        return {
            "status": "error",
            "file": file_path,
            "chunks": 0,
            "message": "PDF'den metin çıkarılamadı."
        }

    texts = split_text(full_text, chunk_size=500, overlap=50)

    if not texts:
        return {
            "status": "error",
            "file": file_path,
            "chunks": 0,
            "message": "Chunk oluşturulamadı."
        }

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts).tolist()

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection("documents")

    base = os.path.basename(file_path)

    for i, text in enumerate(texts):
        collection.add(
            ids=[f"{base}_{i}"],
            documents=[text],
            embeddings=[embeddings[i]],
            metadatas=[{"source": base, "method": method}]
        )

    return {
        "status": "ok",
        "file": file_path,
        "chunks": len(texts),
        "method": method
    }