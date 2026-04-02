import os

import chromadb
from pypdf import PdfReader

from app.config import settings
from app.rag.embeddings import encode_texts
from app.rag.ocr_utils import extract_text_with_ocr


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks: list[str] = []
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
    full_text: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            full_text.append(page_text)

    return "\n".join(full_text).strip()


def get_collection(collection_name: str):
    os.makedirs(settings.chroma_path, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(collection_name)


def ingest_pdf(file_path: str, collection_name: str | None = None) -> dict[str, object]:
    full_text = extract_text_from_pdf(file_path)
    method = "normal"

    if not full_text:
        full_text = extract_text_with_ocr(file_path)
        method = "ocr"

    if not full_text:
        return {
            "status": "error",
            "file": file_path,
            "chunks": 0,
            "message": "Could not extract text from PDF.",
        }

    chunks = split_text(full_text, chunk_size=500, overlap=50)
    if not chunks:
        return {
            "status": "error",
            "file": file_path,
            "chunks": 0,
            "message": "No chunks generated.",
        }

    embeddings = encode_texts(chunks)
    target_collection = collection_name or settings.documents_collection
    collection = get_collection(target_collection)
    base_name = os.path.basename(file_path)

    for index, chunk in enumerate(chunks):
        collection.add(
            ids=[f"{base_name}_{index}"],
            documents=[chunk],
            embeddings=[embeddings[index]],
            metadatas=[{"source": base_name, "method": method}],
        )

    return {
        "status": "ok",
        "file": file_path,
        "chunks": len(chunks),
        "method": method,
        "collection": target_collection,
    }
