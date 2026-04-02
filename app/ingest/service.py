import os
from dataclasses import dataclass
from pathlib import Path

import chromadb

from app.config import settings
from app.ingest.parsers import SUPPORTED_EXTENSIONS, parse_file_to_text
from app.rag.embeddings import encode_texts
from app.rag.ingest import split_text


def _normalize_tags(tags: str | list[str] | None) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [tag.strip().lower() for tag in tags if tag and tag.strip()]
    return [part.strip().lower() for part in tags.split(",") if part.strip()]


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
    text, method, content_type = parse_file_to_text(file_path)
    if not text.strip():
        return IngestOutput(
            result={
                "status": "error",
                "file": file_path,
                "chunks": 0,
                "message": "No text extracted from file.",
                "method": method,
                "content_type": content_type,
                "category": category,
                "tags": _normalize_tags(tags),
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
                "category": category,
                "tags": _normalize_tags(tags),
            },
            text=text,
        )

    embeddings = encode_texts(chunks)
    collection = get_documents_collection()
    base_name = Path(file_path).name
    normalized_tags = _normalize_tags(tags)

    for index, chunk in enumerate(chunks):
        collection.add(
            ids=[f"{base_name}_{index}"],
            documents=[chunk],
            embeddings=[embeddings[index]],
            metadatas=[
                {
                    "source": base_name,
                    "method": method,
                    "content_type": content_type,
                    "category": category,
                    "tags": ",".join(normalized_tags),
                    "user_id": user_id or "",
                }
            ],
        )

    return IngestOutput(
        result={
            "status": "ok",
            "file": file_path,
            "chunks": len(chunks),
            "method": method,
            "collection": settings.documents_collection,
            "content_type": content_type,
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
