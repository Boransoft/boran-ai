import json
from pathlib import Path
from threading import Lock

from app.config import settings


_STORE_LOCK = Lock()


def _store_path() -> Path:
    root = Path(settings.ingest_path)
    root.mkdir(parents=True, exist_ok=True)
    return root / "document_sources.jsonl"


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_record(record: dict[str, object]) -> dict[str, object]:
    source_id = str(record.get("source_id") or "").strip()
    document_id = str(record.get("document_id") or source_id).strip()
    original_file_name = str(record.get("original_file_name") or record.get("file_name") or "").strip()
    normalized_file_name = str(
        record.get("normalized_file_name") or original_file_name.lower().replace("\\", "/").split("/")[-1]
    ).strip()
    upload_time = str(record.get("upload_time") or record.get("uploaded_at") or "").strip()
    uploaded_at = str(record.get("uploaded_at") or upload_time).strip()

    normalized: dict[str, object] = {
        "user_id": str(record.get("user_id") or "").strip(),
        "source_id": source_id,
        "document_id": document_id,
        "file_name": str(record.get("file_name") or original_file_name).strip(),
        "original_file_name": original_file_name,
        "normalized_file_name": normalized_file_name,
        "mime_type": str(record.get("mime_type") or "application/octet-stream"),
        "source_type": str(record.get("source_type") or "document"),
        "upload_time": upload_time,
        "uploaded_at": uploaded_at,
        "chunk_count": _to_int(record.get("chunk_count"), default=0),
        "checksum": str(record.get("checksum") or "").strip(),
        "status": str(record.get("status") or "ready"),
    }
    for key, value in record.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def register_document_source(record: dict[str, object]) -> None:
    path = _store_path()
    normalized = _normalize_record(record)
    line = json.dumps(normalized, ensure_ascii=False)
    with _STORE_LOCK:
        with path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")


def list_recent_document_sources(user_id: str, limit: int = 8) -> list[dict[str, object]]:
    path = _store_path()
    if not path.exists():
        return []

    with _STORE_LOCK:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    output: list[dict[str, object]] = []
    for line in reversed(lines):
        try:
            item = json.loads(line)
        except Exception:
            continue
        if str(item.get("user_id", "")) != user_id:
            continue
        output.append(item)
        if len(output) >= max(1, limit):
            break
    return output
