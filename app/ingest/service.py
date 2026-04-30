import os
import hashlib
import logging
import mimetypes
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from app.config import settings
from app.ingest.parsers import SUPPORTED_EXTENSIONS, parse_file_to_text
from app.rag.embeddings import encode_texts
from app.rag.document_sources import register_document_source
from app.rag.ingest import split_text
from app.rag.ocr_utils import ocr_unavailable_warning


logger = logging.getLogger("uvicorn.error")


def _normalize_tags(tags: str | list[str] | None) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [tag.strip().lower() for tag in tags if tag and tag.strip()]
    return [part.strip().lower() for part in tags.split(",") if part.strip()]


def _normalize_file_name(file_name: str) -> str:
    normalized = file_name.strip().lower().replace("\\", "/")
    normalized = normalized.split("/")[-1]
    mojibake_map = {
        "Ã¼": "u",
        "Ã¶": "o",
        "Ã§": "c",
        "ÄŸ": "g",
        "ÅŸ": "s",
        "Ä±": "i",
        "Ä°": "i",
    }
    for bad, good in mojibake_map.items():
        normalized = normalized.replace(bad, good)
    normalized = normalized.translate(str.maketrans("çğıöşü", "cgiosu"))
    normalized = re.sub(r"[^a-z0-9._-]+", "", normalized)
    normalized = " ".join(normalized.split())
    return normalized


def _source_type(content_type: str, file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    if content_type == "pdf" or ext == ".pdf":
        return "pdf"
    if content_type == "image" or ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}:
        return "image"
    if content_type in {"doc", "docx"} or ext in {".doc", ".docx"}:
        return "document"
    if content_type in {"text", "dataset"} or ext in {".txt", ".md", ".csv", ".json", ".jsonl"}:
        return "text"
    return "document"


def _file_checksum_sha256(file_path: str) -> str:
    sha = hashlib.sha256()
    with Path(file_path).open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def get_documents_collection():
    os.makedirs(settings.chroma_path, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(settings.documents_collection)


@dataclass
class IngestOutput:
    result: dict[str, object]
    text: str


def ingest_file_with_text(
    file_path: str,
    category: str = "general",
    tags: str | list[str] | None = None,
    user_id: str | None = None,
) -> IngestOutput:
    scoped_user_id = str(user_id or "").strip()
    base_name = Path(file_path).name
    source_id = f"src_{uuid.uuid4().hex}"
    document_id = f"doc_{uuid.uuid4().hex}"
    upload_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    normalized_tags = _normalize_tags(tags)

    text, method, content_type = parse_file_to_text(file_path)
    source_type = _source_type(content_type, base_name)
    normalized_file_name = _normalize_file_name(base_name)
    checksum = _file_checksum_sha256(file_path)

    if not text.strip():
        message = (
            ocr_unavailable_warning()
            if method == "ocr_unavailable"
            else "No text extracted from file."
        )
        return IngestOutput(
            result={
                "status": "error",
                "file": file_path,
                "chunks": 0,
                "message": message,
                "method": method,
                "content_type": content_type,
                "mime_type": mime_type,
                "source_type": source_type,
                "file_name": base_name,
                "original_file_name": base_name,
                "normalized_file_name": normalized_file_name,
                "source_id": source_id,
                "document_id": document_id,
                "upload_time": upload_time,
                "uploaded_at": upload_time,
                "checksum": checksum,
                "user_id": scoped_user_id,
                "category": category,
                "tags": normalized_tags,
            },
            text="",
        )

    chunks = split_text(text, chunk_size=500, overlap=50)
    if not chunks:
        return IngestOutput(
            result={
                "status": "error",
                "file": file_path,
                "chunks": 0,
                "message": "No chunks generated.",
                "method": method,
                "content_type": content_type,
                "mime_type": mime_type,
                "source_type": source_type,
                "file_name": base_name,
                "original_file_name": base_name,
                "normalized_file_name": normalized_file_name,
                "source_id": source_id,
                "document_id": document_id,
                "upload_time": upload_time,
                "uploaded_at": upload_time,
                "checksum": checksum,
                "user_id": scoped_user_id,
                "category": category,
                "tags": normalized_tags,
            },
            text=text,
        )

    embeddings = encode_texts(chunks)
    collection = get_documents_collection()

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
                    "normalized_file_name": normalized_file_name,
                    "mime_type": mime_type,
                    "source_type": source_type,
                    "upload_time": upload_time,
                    "uploaded_at": upload_time,
                    "chunk_count": len(chunks),
                    "chunk_index": index,
                    "collection": settings.documents_collection,
                    "status": "ready",
                    "checksum": checksum,
                    "method": method,
                    "content_type": content_type,
                    "category": category,
                    "tags": ",".join(normalized_tags),
                    "user_id": scoped_user_id,
                }
            ],
        )

    source_record: dict[str, object] = {
        "source_id": source_id,
        "document_id": document_id,
        "user_id": scoped_user_id,
        "file_name": base_name,
        "original_file_name": base_name,
        "normalized_file_name": normalized_file_name,
        "mime_type": mime_type,
        "source_type": source_type,
        "content_type": content_type,
        "upload_time": upload_time,
        "uploaded_at": upload_time,
        "chunk_count": len(chunks),
        "collection": settings.documents_collection,
        "category": category,
        "tags": normalized_tags,
        "status": "ready",
        "checksum": checksum,
        "method": method,
    }
    try:
        register_document_source(source_record)
    except Exception as exc:
        logger.warning("document_source_registry_write_failed file=%s error=%s", file_path, exc)

    logger.info(
        "ingest_document_ok user_id=%s source_id=%s file=%s mime=%s source_type=%s chunks=%s",
        scoped_user_id,
        source_id,
        base_name,
        mime_type,
        source_type,
        len(chunks),
    )

    return IngestOutput(
        result={
            "status": "ok",
            "file": file_path,
            "chunks": len(chunks),
            "chunk_count": len(chunks),
            "method": method,
            "collection": settings.documents_collection,
            "content_type": content_type,
            "mime_type": mime_type,
            "source_type": source_type,
            "file_name": base_name,
            "original_file_name": base_name,
            "normalized_file_name": normalized_file_name,
            "source_id": source_id,
            "document_id": document_id,
            "upload_time": upload_time,
            "uploaded_at": upload_time,
            "checksum": checksum,
            "user_id": scoped_user_id,
            "category": category,
            "tags": normalized_tags,
        },
        text=text,
    )


def ingest_file(
    file_path: str,
    category: str = "general",
    tags: str | list[str] | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    return ingest_file_with_text(
        file_path=file_path,
        category=category,
        tags=tags,
        user_id=user_id,
    ).result


def ingest_folder_unified(
    folder_path: str,
    category: str = "general",
    tags: str | list[str] | None = None,
    user_id: str | None = None,
) -> list[dict[str, object]]:
    path = Path(folder_path)
    if not path.exists():
        return [
            {
                "status": "error",
                "file": str(path),
                "chunks": 0,
                "message": "Folder not found.",
                "method": "none",
                "content_type": "unknown",
                "category": category,
                "tags": _normalize_tags(tags),
            }
        ]

    results: list[dict[str, object]] = []
    for file_name in os.listdir(path):
        ext = Path(file_name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        full_path = str(path / file_name)
        try:
            results.append(
                ingest_file(
                    file_path=full_path,
                    category=category,
                    tags=tags,
                    user_id=user_id,
                )
            )
        except Exception as exc:
            results.append(
                {
                    "status": "error",
                    "file": full_path,
                    "chunks": 0,
                    "message": str(exc),
                    "method": "failed",
                    "content_type": "unknown",
                    "category": category,
                    "tags": _normalize_tags(tags),
                }
            )

    return results
