import os
import hashlib
import uuid
from datetime import datetime, timezone

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


def _file_checksum_sha256(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def ingest_pdf(
    file_path: str,
    collection_name: str | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    scoped_user_id = str(user_id or "").strip()
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
    source_id = f"src_{uuid.uuid4().hex}"
    document_id = f"doc_{uuid.uuid4().hex}"
    upload_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    checksum = _file_checksum_sha256(file_path)

    for index, chunk in enumerate(chunks):
        collection.add(
            ids=[f"{source_id}:chunk:{index:06d}"],
            documents=[chunk],
            embeddings=[embeddings[index]],
            metadatas=[
                {
                    "source": base_name,
                    "source_id": source_id,
                    "document_id": document_id,
                    "file_name": base_name,
                    "original_file_name": base_name,
                    "normalized_file_name": base_name.lower(),
                    "mime_type": "application/pdf",
                    "source_type": "pdf",
                    "upload_time": upload_time,
                    "uploaded_at": upload_time,
                    "chunk_count": len(chunks),
                    "chunk_index": index,
                    "collection": target_collection,
                    "status": "ready",
                    "checksum": checksum,
                    "method": method,
                    "content_type": "pdf",
                    "category": "pdf",
                    "tags": "pdf",
                    "user_id": scoped_user_id,
                }
            ],
        )

    return {
        "status": "ok",
        "file": file_path,
        "chunks": len(chunks),
        "chunk_count": len(chunks),
        "method": method,
        "collection": target_collection,
        "source_id": source_id,
        "document_id": document_id,
        "file_name": base_name,
        "original_file_name": base_name,
        "normalized_file_name": base_name.lower(),
        "mime_type": "application/pdf",
        "source_type": "pdf",
        "upload_time": upload_time,
        "uploaded_at": upload_time,
        "checksum": checksum,
        "user_id": scoped_user_id,
    }
