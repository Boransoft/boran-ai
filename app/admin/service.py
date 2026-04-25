from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.config import PROJECT_ROOT, settings
from app.db.session import get_engine
from app.ingest.service import get_documents_collection
from app.learning.pipeline import learning_pipeline


TARGET_PHASE1_TABLES = (
    "users",
    "documents",
    "document_chunks",
    "ingest_jobs",
    "conversations",
    "messages",
    "system_logs",
)


def _safe_iso(value: object) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except Exception:
            return str(value)
    return str(value)


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _to_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _to_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_tags_input(value: object) -> str | list[str] | None:
    if isinstance(value, list):
        tags = [str(item).strip() for item in value if str(item).strip()]
        return tags or None
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        parsed = json.loads(text_value)
    except Exception:
        return text_value
    if isinstance(parsed, list):
        tags = [str(item).strip() for item in parsed if str(item).strip()]
        return tags or None
    return text_value


class AdminDataService:
    def _engine(self) -> Engine | None:
        try:
            return get_engine()
        except Exception:
            return None

    def _table_columns(self, table_name: str) -> set[str]:
        engine = self._engine()
        if engine is None:
            return set()
        try:
            inspector = inspect(engine)
            return {str(column["name"]) for column in inspector.get_columns(table_name)}
        except Exception:
            return set()

    def _table_exists(self, table_name: str) -> bool:
        return len(self._table_columns(table_name)) > 0

    def _load_table_rows(
        self,
        table_name: str,
        limit: int = 500,
        sort_candidates: tuple[str, ...] = ("updated_at", "created_at", "timestamp", "uploaded_at"),
    ) -> list[dict[str, Any]]:
        columns = self._table_columns(table_name)
        if not columns:
            return []

        order_col = next((name for name in sort_candidates if name in columns), None)
        sql = f'SELECT * FROM "{table_name}"'
        if order_col:
            sql += f' ORDER BY "{order_col}" DESC'
        sql += " LIMIT :limit"

        engine = self._engine()
        if engine is None:
            return []

        with engine.connect() as conn:
            rows = conn.execute(text(sql), {"limit": max(1, limit)}).mappings().all()
        return [dict(row) for row in rows]

    def _user_count(self) -> int:
        columns = self._table_columns("users")
        if not columns:
            return 0

        engine = self._engine()
        if engine is None:
            return 0

        with engine.connect() as conn:
            count = conn.execute(text('SELECT COUNT(*) AS total FROM "users"')).scalar()
        return _to_int(count)

    def _load_documents_from_table(self, cap: int = 5000) -> list[dict[str, Any]]:
        rows = self._load_table_rows(
            "documents",
            limit=cap,
            sort_candidates=("uploaded_at", "ingested_at", "updated_at", "created_at"),
        )
        documents: list[dict[str, Any]] = []
        for row in rows:
            file_name = (
                _to_str(row.get("file_name"))
                or _to_str(row.get("original_file_name"))
                or _to_str(row.get("normalized_file_name"))
            )
            source_id = _to_str(row.get("source_id"))
            document_id = _to_str(row.get("document_id")) or _to_str(row.get("id")) or source_id
            documents.append(
                {
                    "id": _to_str(row.get("id")) or document_id,
                    "document_id": document_id,
                    "source_id": source_id,
                    "user_id": _to_str(row.get("user_id")),
                    "file_name": file_name,
                    "source_type": _to_str(row.get("source_type")),
                    "mime_type": _to_str(row.get("mime_type")),
                    "file_size": _to_int(row.get("file_size"), default=0),
                    "chunk_count": _to_int(row.get("chunk_count"), default=0),
                    "status": _to_str(row.get("status")) or "unknown",
                    "uploaded_at": _safe_iso(row.get("uploaded_at") or row.get("created_at")),
                    "category": _to_str(row.get("category")),
                    "tags": row.get("tags") if isinstance(row.get("tags"), list) else _to_str(row.get("tags")),
                }
            )
        return documents

    def _document_registry_path(self) -> Path:
        return Path(settings.ingest_path) / "document_sources.jsonl"

    def _read_registry_rows(self) -> list[dict[str, Any]]:
        path = self._document_registry_path()
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        rows: list[dict[str, Any]] = []
        for line in lines:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                rows.append(item)
        return rows

    def _write_registry_rows(self, rows: list[dict[str, Any]]) -> None:
        path = self._document_registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        if content:
            content += "\n"
        path.write_text(content, encoding="utf-8")

    def _load_documents_from_registry(self, cap: int = 5000) -> list[dict[str, Any]]:
        lines = self._read_registry_rows()
        dedup: dict[str, dict[str, Any]] = {}
        for row in reversed(lines):
            if len(dedup) >= cap:
                break
            source_id = _to_str(row.get("source_id"))
            document_id = _to_str(row.get("document_id")) or source_id
            if not document_id:
                continue
            if document_id in dedup:
                continue
            dedup[document_id] = {
                "id": document_id,
                "document_id": document_id,
                "source_id": source_id,
                "user_id": _to_str(row.get("user_id")),
                "file_name": _to_str(row.get("file_name")) or _to_str(row.get("original_file_name")),
                "source_type": _to_str(row.get("source_type")),
                "mime_type": _to_str(row.get("mime_type")),
                "file_size": _to_int(row.get("file_size"), default=0),
                "chunk_count": _to_int(row.get("chunk_count"), default=0),
                "status": _to_str(row.get("status")) or "ready",
                "uploaded_at": _to_str(row.get("uploaded_at") or row.get("upload_time")),
                "category": _to_str(row.get("category")),
                "tags": row.get("tags") if isinstance(row.get("tags"), list) else _to_str(row.get("tags")),
            }
        return list(dedup.values())

    def list_documents(
        self,
        status: str = "",
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        docs = self._load_documents_from_table(cap=5000)
        if not docs:
            docs = self._load_documents_from_registry(cap=5000)

        status_filter = status.strip().lower()
        query_filter = query.strip().lower()

        if status_filter:
            docs = [item for item in docs if _to_str(item.get("status")).lower() == status_filter]
        if query_filter:
            docs = [
                item
                for item in docs
                if query_filter in _to_str(item.get("file_name")).lower()
                or query_filter in _to_str(item.get("document_id")).lower()
                or query_filter in _to_str(item.get("source_id")).lower()
                or query_filter in _to_str(item.get("user_id")).lower()
            ]

        docs.sort(key=lambda item: _to_str(item.get("uploaded_at")), reverse=True)
        total = len(docs)
        sliced = docs[offset : offset + max(1, limit)]
        return {"items": sliced, "total": total, "limit": limit, "offset": offset}

    def _document_record_from_table(self, document_id: str) -> dict[str, Any] | None:
        target = document_id.strip()
        if not target:
            return None
        columns = self._table_columns("documents")
        if not columns:
            return None
        clauses: list[str] = []
        params: dict[str, Any] = {"target": target}
        if "id" in columns:
            clauses.append('"id"::text = :target')
        if "document_id" in columns:
            clauses.append('"document_id"::text = :target')
        if "source_id" in columns:
            clauses.append('"source_id" = :target')
        if not clauses:
            return None
        order_col = next((name for name in ("uploaded_at", "updated_at", "created_at") if name in columns), None)
        sql = f'SELECT * FROM "documents" WHERE {" OR ".join(clauses)}'
        if order_col:
            sql += f' ORDER BY "{order_col}" DESC'
        sql += " LIMIT 1"
        engine = self._engine()
        if engine is None:
            return None
        with engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

    def _document_record_from_registry(self, document_id: str) -> dict[str, Any] | None:
        target = document_id.strip()
        if not target:
            return None
        for row in reversed(self._read_registry_rows()):
            doc_id = _to_str(row.get("document_id")) or _to_str(row.get("source_id"))
            source_id = _to_str(row.get("source_id"))
            if target in {doc_id, source_id, _to_str(row.get("id"))}:
                return row
        return None

    def _resolve_document_file_path(self, row: dict[str, Any]) -> Path | None:
        candidates: list[Path] = []
        for key in ("file_path", "file", "path", "absolute_path", "local_path"):
            raw = _to_str(row.get(key))
            if raw:
                candidates.append(Path(raw))
        file_name = _to_str(row.get("file_name")) or _to_str(row.get("original_file_name"))
        normalized_file_name = _to_str(row.get("normalized_file_name"))
        for base_path in (Path(settings.ingest_path), Path(settings.pdf_path)):
            if file_name:
                candidates.append(base_path / file_name)
            if normalized_file_name and normalized_file_name != file_name:
                candidates.append(base_path / normalized_file_name)
        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate.resolve()
            except Exception:
                continue
        return None

    def get_document_detail(self, document_id: str) -> dict[str, Any]:
        target = document_id.strip()
        if not target:
            raise ValueError("Belge kimliği gerekli.")

        row = self._document_record_from_table(target)
        source = "table"
        if row is None:
            row = self._document_record_from_registry(target)
            source = "registry"
        if row is None:
            raise ValueError("Belge bulunamadı.")

        file_path = self._resolve_document_file_path(row)
        normalized_document_id = _to_str(row.get("document_id")) or _to_str(row.get("id")) or _to_str(row.get("source_id"))
        return {
            "document": {
                "id": _to_str(row.get("id")) or normalized_document_id,
                "document_id": normalized_document_id,
                "source_id": _to_str(row.get("source_id")),
                "user_id": _to_str(row.get("user_id")),
                "file_name": _to_str(row.get("file_name")) or _to_str(row.get("original_file_name")),
                "source_type": _to_str(row.get("source_type")),
                "mime_type": _to_str(row.get("mime_type")),
                "file_size": _to_int(row.get("file_size"), default=0),
                "chunk_count": _to_int(row.get("chunk_count"), default=0),
                "status": _to_str(row.get("status")) or "unknown",
                "uploaded_at": _safe_iso(row.get("uploaded_at") or row.get("upload_time") or row.get("created_at")),
                "category": _to_str(row.get("category")),
                "tags": row.get("tags") if isinstance(row.get("tags"), list) else _to_str(row.get("tags")),
            },
            "source": source,
            "file_path": str(file_path) if file_path else "",
        }

    def _create_ingest_job(self, document_id: str, status_value: str = "running", stage: str = "ingest") -> str:
        columns = self._table_columns("ingest_jobs")
        if not columns:
            return ""
        values: dict[str, Any] = {}
        if "id" in columns:
            values["id"] = str(uuid4())
        if "status" in columns:
            values["status"] = status_value
        if "stage" in columns:
            values["stage"] = stage
        if "document_id" in columns:
            values["document_id"] = document_id
        if "started_at" in columns:
            values["started_at"] = datetime.now(timezone.utc)
        if "retry_count" in columns:
            values["retry_count"] = 0
        if not values:
            return ""
        quoted_columns = ", ".join(f'"{name}"' for name in values)
        placeholders = ", ".join(f":{name}" for name in values)
        sql = f'INSERT INTO "ingest_jobs" ({quoted_columns}) VALUES ({placeholders})'
        engine = self._engine()
        if engine is None:
            return ""
        try:
            with engine.begin() as conn:
                conn.execute(text(sql), values)
            return _to_str(values.get("id"))
        except Exception:
            return ""

    def _set_ingest_job_result(
        self,
        job_id: str,
        status_value: str,
        error_message: str = "",
    ) -> None:
        if not job_id:
            return
        columns = self._table_columns("ingest_jobs")
        if "id" not in columns:
            return
        assignments: list[str] = []
        params: dict[str, Any] = {"job_id": job_id}
        if "status" in columns:
            assignments.append('"status" = :status')
            params["status"] = status_value
        if "completed_at" in columns:
            assignments.append('"completed_at" = :completed_at')
            params["completed_at"] = datetime.now(timezone.utc)
        if "error_message" in columns:
            assignments.append('"error_message" = :error_message')
            params["error_message"] = error_message
        if not assignments:
            return
        sql = f'UPDATE "ingest_jobs" SET {", ".join(assignments)} WHERE "id"::text = :job_id'
        engine = self._engine()
        if engine is None:
            return
        with engine.begin() as conn:
            conn.execute(text(sql), params)

    def reprocess_document(self, document_id: str) -> dict[str, Any]:
        detail = self.get_document_detail(document_id)
        document = _to_dict(detail.get("document"))
        file_path_text = _to_str(detail.get("file_path"))
        file_path = Path(file_path_text) if file_path_text else None
        if file_path is None or not file_path.exists():
            raise ValueError("Belge dosyasi bulunamadi, yeniden isleme yapilamadi.")

        normalized_document_id = _to_str(document.get("document_id")) or _to_str(document.get("id"))
        job_id = self._create_ingest_job(document_id=normalized_document_id, status_value="running")
        try:
            result = learning_pipeline.ingest_document(
                user_id=_to_str(document.get("user_id")) or "admin_internal",
                file_path=str(file_path),
                category=_to_str(document.get("category")) or "general",
                tags=_normalize_tags_input(document.get("tags")),
            )
            if result.status != "ok":
                message = _to_str(result.details.get("message")) or "Yeniden isleme basarisiz."
                self._set_ingest_job_result(job_id=job_id, status_value="failed", error_message=message)
                raise ValueError(message)
            self._set_ingest_job_result(job_id=job_id, status_value="completed")
            return {
                "status": "ok",
                "message": "Belge yeniden islendi.",
                "document_id": normalized_document_id,
                "job_id": job_id,
                "details": result.details,
            }
        except Exception as exc:
            self._set_ingest_job_result(job_id=job_id, status_value="failed", error_message=str(exc))
            raise

    def _delete_from_documents_table(self, document_id: str, source_id: str) -> int:
        columns = self._table_columns("documents")
        if not columns:
            return 0
        clauses: list[str] = []
        params: dict[str, Any] = {"document_id": document_id, "source_id": source_id}
        if "id" in columns:
            clauses.append('"id"::text = :document_id')
        if "document_id" in columns:
            clauses.append('"document_id"::text = :document_id')
        if source_id and "source_id" in columns:
            clauses.append('"source_id" = :source_id')
        if not clauses:
            return 0
        engine = self._engine()
        if engine is None:
            return 0
        sql = f'DELETE FROM "documents" WHERE {" OR ".join(clauses)}'
        with engine.begin() as conn:
            result = conn.execute(text(sql), params)
        return int(result.rowcount or 0)

    def _delete_from_document_chunks(self, document_id: str, source_id: str) -> int:
        columns = self._table_columns("document_chunks")
        if not columns:
            return 0
        clauses: list[str] = []
        params: dict[str, Any] = {"document_id": document_id, "source_id": source_id}
        if "document_id" in columns:
            clauses.append('"document_id"::text = :document_id')
        if source_id and "source_id" in columns:
            clauses.append('"source_id" = :source_id')
        if not clauses:
            return 0
        engine = self._engine()
        if engine is None:
            return 0
        sql = f'DELETE FROM "document_chunks" WHERE {" OR ".join(clauses)}'
        with engine.begin() as conn:
            result = conn.execute(text(sql), params)
        return int(result.rowcount or 0)

    def _delete_from_ingest_jobs(self, document_id: str) -> int:
        columns = self._table_columns("ingest_jobs")
        if "document_id" not in columns:
            return 0
        engine = self._engine()
        if engine is None:
            return 0
        with engine.begin() as conn:
            result = conn.execute(
                text('DELETE FROM "ingest_jobs" WHERE "document_id"::text = :document_id'),
                {"document_id": document_id},
            )
        return int(result.rowcount or 0)

    def _delete_from_chroma(self, document_id: str, source_id: str) -> int:
        deleted = 0
        collection = get_documents_collection()
        try:
            items = collection.get(where={"document_id": document_id}, include=[])
            deleted += len(items.get("ids") or [])
            collection.delete(where={"document_id": document_id})
        except Exception:
            pass
        if source_id:
            try:
                items = collection.get(where={"source_id": source_id}, include=[])
                deleted += len(items.get("ids") or [])
                collection.delete(where={"source_id": source_id})
            except Exception:
                pass
        return deleted

    def _delete_from_registry(self, document_id: str, source_id: str) -> int:
        rows = self._read_registry_rows()
        kept: list[dict[str, Any]] = []
        removed = 0
        for row in rows:
            row_doc_id = _to_str(row.get("document_id")) or _to_str(row.get("source_id"))
            row_source_id = _to_str(row.get("source_id"))
            if row_doc_id == document_id or (source_id and row_source_id == source_id):
                removed += 1
                continue
            kept.append(row)
        if removed > 0:
            self._write_registry_rows(kept)
        return removed

    def delete_document(self, document_id: str) -> dict[str, Any]:
        detail = self.get_document_detail(document_id)
        document = _to_dict(detail.get("document"))
        normalized_document_id = _to_str(document.get("document_id")) or _to_str(document.get("id"))
        source_id = _to_str(document.get("source_id"))

        deleted_documents = self._delete_from_documents_table(normalized_document_id, source_id)
        deleted_chunks = self._delete_from_document_chunks(normalized_document_id, source_id)
        deleted_jobs = self._delete_from_ingest_jobs(normalized_document_id)
        deleted_registry = self._delete_from_registry(normalized_document_id, source_id)
        deleted_chroma = self._delete_from_chroma(normalized_document_id, source_id)

        return {
            "status": "ok",
            "message": "Belge silindi.",
            "document_id": normalized_document_id,
            "deleted": {
                "documents": deleted_documents,
                "chunks": deleted_chunks,
                "ingest_jobs": deleted_jobs,
                "registry": deleted_registry,
                "chroma_chunks": deleted_chroma,
            },
        }

    def bulk_delete_documents(self, document_ids: list[str]) -> dict[str, Any]:
        targets = [_to_str(item) for item in document_ids if _to_str(item)]
        if not targets:
            raise ValueError("Belge kimlikleri gerekli.")
        deleted = 0
        failures: list[dict[str, str]] = []
        for target in targets:
            try:
                self.delete_document(target)
                deleted += 1
            except Exception as exc:
                failures.append({"document_id": target, "error": str(exc)})
        return {
            "status": "ok",
            "message": "Toplu belge silme tamamlandi.",
            "requested": len(targets),
            "deleted": deleted,
            "failures": failures,
        }

    def bulk_reprocess_documents(self, document_ids: list[str]) -> dict[str, Any]:
        targets = [_to_str(item) for item in document_ids if _to_str(item)]
        if not targets:
            raise ValueError("Belge kimlikleri gerekli.")
        started = 0
        failures: list[dict[str, str]] = []
        for target in targets:
            try:
                self.reprocess_document(target)
                started += 1
            except Exception as exc:
                failures.append({"document_id": target, "error": str(exc)})
        return {
            "status": "ok",
            "message": "Toplu yeniden isleme tamamlandi.",
            "requested": len(targets),
            "started": started,
            "failures": failures,
        }

    def list_chunk_summary(self, limit: int = 50) -> dict[str, Any]:
        if self._table_exists("document_chunks"):
            engine = self._engine()
            if engine is None:
                return {"items": [], "total_chunks": 0}
            sql = """
                SELECT document_id::text AS document_id, COUNT(*) AS chunk_count
                FROM document_chunks
                GROUP BY document_id
                ORDER BY chunk_count DESC
                LIMIT :limit
            """
            with engine.connect() as conn:
                rows = conn.execute(text(sql), {"limit": max(1, limit)}).mappings().all()
                total_chunks = conn.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar()

            documents = self.list_documents(limit=2000)["items"]
            by_document = {str(item.get("document_id")): item for item in documents}
            items: list[dict[str, Any]] = []
            for row in rows:
                document_id = _to_str(row.get("document_id"))
                source = by_document.get(document_id, {})
                items.append(
                    {
                        "document_id": document_id,
                        "file_name": _to_str(source.get("file_name")),
                        "source_id": _to_str(source.get("source_id")),
                        "chunk_count": _to_int(row.get("chunk_count")),
                    }
                )
            return {
                "items": items,
                "total_chunks": _to_int(total_chunks),
            }

        docs = self.list_documents(limit=5000)["items"]
        items = sorted(
            [
                {
                    "document_id": _to_str(item.get("document_id")),
                    "file_name": _to_str(item.get("file_name")),
                    "source_id": _to_str(item.get("source_id")),
                    "chunk_count": _to_int(item.get("chunk_count")),
                }
                for item in docs
            ],
            key=lambda item: item["chunk_count"],
            reverse=True,
        )
        total_chunks = sum(_to_int(item.get("chunk_count")) for item in docs)
        return {
            "items": items[: max(1, limit)],
            "total_chunks": total_chunks,
        }

    def list_ingest_jobs(self, status: str = "", limit: int = 50, offset: int = 0) -> dict[str, Any]:
        rows = self._load_table_rows(
            "ingest_jobs",
            limit=5000,
            sort_candidates=("created_at", "started_at", "updated_at"),
        )
        jobs: list[dict[str, Any]] = []
        for row in rows:
            jobs.append(
                {
                    "id": _to_str(row.get("id")),
                    "status": _to_str(row.get("status")),
                    "stage": _to_str(row.get("stage")),
                    "document_id": _to_str(row.get("document_id")),
                    "file_name": _to_str(row.get("file_name")),
                    "started_at": _safe_iso(row.get("started_at") or row.get("created_at")),
                    "completed_at": _safe_iso(row.get("completed_at")),
                    "retry_count": _to_int(row.get("retry_count")),
                    "error_message": _to_str(row.get("error_message")),
                }
            )

        if not jobs:
            docs = self.list_documents(limit=5000)["items"]
            for item in docs:
                status_value = _to_str(item.get("status")).lower() or "unknown"
                completed_status = {"ready", "completed", "success", "ok"}
                jobs.append(
                    {
                        "id": _to_str(item.get("document_id")),
                        "status": status_value,
                        "stage": "ingest",
                        "document_id": _to_str(item.get("document_id")),
                        "file_name": _to_str(item.get("file_name")),
                        "started_at": _to_str(item.get("uploaded_at")),
                        "completed_at": _to_str(item.get("uploaded_at")) if status_value in completed_status else "",
                        "retry_count": 0,
                        "error_message": "",
                    }
                )
        else:
            docs = self.list_documents(limit=5000)["items"]
            by_document = {str(item.get("document_id")): item for item in docs}
            for item in jobs:
                source = by_document.get(_to_str(item.get("document_id")), {})
                item["file_name"] = _to_str(source.get("file_name"))

        if status.strip():
            filter_status = status.strip().lower()
            jobs = [item for item in jobs if _to_str(item.get("status")).lower() == filter_status]

        jobs.sort(key=lambda item: _to_str(item.get("started_at")), reverse=True)
        total = len(jobs)
        return {
            "items": jobs[offset : offset + max(1, limit)],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _find_ingest_job(self, job_id: str) -> dict[str, Any] | None:
        target = job_id.strip()
        if not target:
            return None
        columns = self._table_columns("ingest_jobs")
        if "id" not in columns:
            return None
        engine = self._engine()
        if engine is None:
            return None
        with engine.connect() as conn:
            row = conn.execute(
                text('SELECT * FROM "ingest_jobs" WHERE "id"::text = :job_id LIMIT 1'),
                {"job_id": target},
            ).mappings().first()
        return dict(row) if row else None

    def _increment_ingest_retry_count(self, job_id: str) -> None:
        columns = self._table_columns("ingest_jobs")
        if "id" not in columns:
            return
        assignments: list[str] = []
        params: dict[str, Any] = {"job_id": job_id}
        if "retry_count" in columns:
            assignments.append('"retry_count" = COALESCE("retry_count", 0) + 1')
        if "status" in columns:
            assignments.append('"status" = :status')
            params["status"] = "retried"
        if not assignments:
            return
        engine = self._engine()
        if engine is None:
            return
        with engine.begin() as conn:
            conn.execute(
                text(f'UPDATE "ingest_jobs" SET {", ".join(assignments)} WHERE "id"::text = :job_id'),
                params,
            )

    def retry_ingest_job(self, job_id: str) -> dict[str, Any]:
        row = self._find_ingest_job(job_id)
        if row is None:
            if self._table_exists("ingest_jobs"):
                raise ValueError("Ingest job bulunamadi.")
            return self.reprocess_document(job_id)

        status_value = _to_str(row.get("status")).lower()
        if status_value not in {"failed", "error"}:
            raise ValueError("Sadece hatali durumdaki isler tekrar denenebilir.")

        document_id = _to_str(row.get("document_id"))
        if not document_id:
            raise ValueError("Islem icin belge kimligi bulunamadi.")

        self._increment_ingest_retry_count(job_id)
        result = self.reprocess_document(document_id)
        result["retried_job_id"] = job_id
        return result

    def retry_failed_ingest_jobs(self, limit: int = 10) -> dict[str, Any]:
        max_limit = max(1, min(100, limit))
        jobs = self.list_ingest_jobs(limit=5000, offset=0)["items"]
        failed_jobs = [
            item for item in jobs if _to_str(item.get("status")).lower() in {"failed", "error"}
        ][:max_limit]

        retried = 0
        failures: list[dict[str, str]] = []
        for item in failed_jobs:
            job_id = _to_str(item.get("id"))
            if not job_id:
                continue
            try:
                self.retry_ingest_job(job_id)
                retried += 1
            except Exception as exc:
                failures.append({"job_id": job_id, "error": str(exc)})

        return {
            "status": "ok",
            "message": "Hatali isler icin tekrar deneme tamamlandi.",
            "retried": retried,
            "attempted": len(failed_jobs),
            "failures": failures,
        }

    def _list_conversations_from_messages_table(self, limit: int = 1000) -> list[dict[str, Any]]:
        columns = self._table_columns("messages")
        if "conversation_id" not in columns:
            return []
        rows = self._load_table_rows(
            "messages",
            limit=limit,
            sort_candidates=("created_at", "updated_at"),
        )
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            conversation_id = _to_str(row.get("conversation_id"))
            if not conversation_id:
                continue
            created_at = _safe_iso(row.get("created_at"))
            item = grouped.get(conversation_id)
            if item is None:
                grouped[conversation_id] = {
                    "conversation_id": conversation_id,
                    "user_id": _to_str(row.get("user_id")),
                    "title": f"Konuşma {conversation_id[:8]}",
                    "last_message_at": created_at,
                    "created_at": created_at,
                }
                continue
            if created_at > _to_str(item.get("last_message_at")):
                item["last_message_at"] = created_at
            if created_at < _to_str(item.get("created_at")):
                item["created_at"] = created_at
        output = list(grouped.values())
        output.sort(key=lambda item: _to_str(item.get("last_message_at")), reverse=True)
        return output

    def list_conversations(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        rows = self._load_table_rows(
            "conversations",
            limit=5000,
            sort_candidates=("last_message_at", "created_at", "updated_at"),
        )
        conversations: list[dict[str, Any]] = []

        if rows:
            columns = set(rows[0].keys())
            is_message_style = "message_text" in columns and "role" in columns
            if is_message_style:
                grouped: dict[str, dict[str, Any]] = {}
                for row in rows:
                    metadata = _to_dict(row.get("metadata_json"))
                    conversation_id = _to_str(metadata.get("conversation_id")) or _to_str(row.get("id"))
                    created_at = _safe_iso(row.get("created_at"))
                    content = _to_str(row.get("message_text"))
                    role = _to_str(row.get("role"))

                    item = grouped.get(conversation_id)
                    if item is None:
                        grouped[conversation_id] = {
                            "conversation_id": conversation_id,
                            "user_id": _to_str(row.get("user_id")),
                            "title": (content[:52] + "...") if len(content) > 55 else (content or f"{role} message"),
                            "last_message_at": created_at,
                            "created_at": created_at,
                        }
                        continue

                    if created_at > _to_str(item.get("last_message_at")):
                        item["last_message_at"] = created_at
                    if created_at < _to_str(item.get("created_at")):
                        item["created_at"] = created_at
                conversations = list(grouped.values())
            else:
                for row in rows:
                    conv_id = _to_str(row.get("id") or row.get("conversation_id"))
                    created_at = _safe_iso(row.get("created_at"))
                    last_message_at = _safe_iso(row.get("last_message_at") or row.get("updated_at") or created_at)
                    conversations.append(
                        {
                            "conversation_id": conv_id,
                            "user_id": _to_str(row.get("user_id")),
                            "title": _to_str(row.get("title")) or f"Konuşma {conv_id[:8]}",
                            "last_message_at": last_message_at,
                            "created_at": created_at,
                        }
                    )

        if not conversations:
            conversations = self._list_conversations_from_messages_table(limit=5000)

        conversations.sort(key=lambda item: _to_str(item.get("last_message_at")), reverse=True)
        total = len(conversations)
        return {
            "items": conversations[offset : offset + max(1, limit)],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def list_conversation_messages(self, conversation_id: str, limit: int = 10) -> dict[str, Any]:
        target = conversation_id.strip()
        if not target:
            return {"items": [], "total": 0}

        output: list[dict[str, Any]] = []
        message_columns = self._table_columns("messages")
        if message_columns and "conversation_id" in message_columns:
            rows = self._load_table_rows(
                "messages",
                limit=5000,
                sort_candidates=("created_at", "updated_at"),
            )
            for row in rows:
                if _to_str(row.get("conversation_id")) != target:
                    continue
                output.append(
                    {
                        "id": _to_str(row.get("id")),
                        "role": _to_str(row.get("role")) or _to_str(row.get("message_type")) or "message",
                        "content": _to_str(row.get("content") or row.get("transcript")),
                        "created_at": _safe_iso(row.get("created_at")),
                    }
                )
        elif self._table_exists("conversations"):
            rows = self._load_table_rows(
                "conversations",
                limit=5000,
                sort_candidates=("created_at", "updated_at"),
            )
            for row in rows:
                row_id = _to_str(row.get("id"))
                metadata = _to_dict(row.get("metadata_json"))
                meta_conversation_id = _to_str(metadata.get("conversation_id"))
                if row_id != target and meta_conversation_id != target:
                    continue
                output.append(
                    {
                        "id": row_id,
                        "role": _to_str(row.get("role")) or "message",
                        "content": _to_str(row.get("message_text") or row.get("content")),
                        "created_at": _safe_iso(row.get("created_at")),
                    }
                )

        output.sort(key=lambda item: _to_str(item.get("created_at")), reverse=True)
        total = len(output)
        return {
            "items": output[: max(1, limit)],
            "total": total,
        }

    def delete_conversation(self, conversation_id: str) -> dict[str, Any]:
        target = conversation_id.strip()
        if not target:
            raise ValueError("Konuşma kimliği gerekli.")

        deleted_messages = 0
        deleted_conversations = 0
        engine = self._engine()
        if engine is None:
            return {
                "status": "ok",
                "message": "Silinecek kayit bulunamadi.",
                "conversation_id": target,
                "deleted": {"messages": 0, "conversations": 0},
            }

        message_columns = self._table_columns("messages")
        conversation_columns = self._table_columns("conversations")

        with engine.begin() as conn:
            if "conversation_id" in message_columns:
                result = conn.execute(
                    text('DELETE FROM "messages" WHERE "conversation_id"::text = :conversation_id'),
                    {"conversation_id": target},
                )
                deleted_messages += int(result.rowcount or 0)

            if conversation_columns:
                clauses: list[str] = []
                params: dict[str, Any] = {"conversation_id": target}
                if "id" in conversation_columns:
                    clauses.append('"id"::text = :conversation_id')
                if "conversation_id" in conversation_columns:
                    clauses.append('"conversation_id"::text = :conversation_id')
                if "metadata_json" in conversation_columns:
                    clauses.append('"metadata_json"->>\'conversation_id\' = :conversation_id')
                if clauses:
                    result = conn.execute(
                        text(f'DELETE FROM "conversations" WHERE {" OR ".join(clauses)}'),
                        params,
                    )
                    deleted_conversations += int(result.rowcount or 0)

        return {
            "status": "ok",
            "message": "Konusma silindi.",
            "conversation_id": target,
            "deleted": {
                "messages": deleted_messages,
                "conversations": deleted_conversations,
            },
        }

    def _fallback_logs_from_files(self, cap: int = 400) -> list[dict[str, Any]]:
        paths = [
            PROJECT_ROOT / "backend-dev.err.log",
            PROJECT_ROOT / "backend-dev.out.log",
        ]
        items: list[dict[str, Any]] = []
        level_pattern = re.compile(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b", re.IGNORECASE)
        timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")

        for path in paths:
            if not path.exists():
                continue
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for raw_line in reversed(lines[-cap:]):
                line = raw_line.strip()
                if not line:
                    continue
                level_match = level_pattern.search(line)
                level = (level_match.group(1) if level_match else ("ERROR" if path.name.endswith(".err.log") else "INFO")).upper()
                timestamp = ""
                ts_match = timestamp_pattern.search(line)
                if ts_match:
                    timestamp = ts_match.group(0)
                items.append(
                    {
                        "id": f"{path.name}:{len(items)}",
                        "level": level,
                        "component": "backend",
                        "message": line,
                        "timestamp": timestamp,
                    }
                )
                if len(items) >= cap:
                    break
            if len(items) >= cap:
                break
        return items

    def _extract_related_refs(self, message: str) -> dict[str, str]:
        text_value = message or ""
        refs: dict[str, str] = {}

        document_match = re.search(r"\b(doc_[a-zA-Z0-9]{8,})\b", text_value)
        if document_match:
            refs["document_id"] = document_match.group(1)

        source_match = re.search(r"\b(src_[a-zA-Z0-9]{8,})\b", text_value)
        if source_match:
            refs["source_id"] = source_match.group(1)

        conversation_match = re.search(
            r"(?:conversation_id|conversation)[=: ]([0-9a-fA-F-]{8,})",
            text_value,
            flags=re.IGNORECASE,
        )
        if conversation_match:
            refs["conversation_id"] = conversation_match.group(1)

        job_match = re.search(r"(?:job_id|ingest_job)[=: ]([0-9a-fA-F-]{8,})", text_value, flags=re.IGNORECASE)
        if job_match:
            refs["job_id"] = job_match.group(1)

        return refs

    def get_log_detail(self, log_id: str) -> dict[str, Any]:
        target = log_id.strip()
        if not target:
            raise ValueError("Kayıt kimliği gerekli.")

        columns = self._table_columns("system_logs")
        if "id" in columns:
            engine = self._engine()
            if engine is not None:
                with engine.connect() as conn:
                    row = conn.execute(
                        text('SELECT * FROM "system_logs" WHERE "id"::text = :log_id LIMIT 1'),
                        {"log_id": target},
                    ).mappings().first()
                if row:
                    message = _to_str(row.get("message"))
                    return {
                        "id": _to_str(row.get("id")),
                        "level": _to_str(row.get("level")).upper() or "INFO",
                        "component": _to_str(row.get("component")) or "system",
                        "message": message,
                        "timestamp": _safe_iso(row.get("timestamp") or row.get("created_at")),
                        "related": self._extract_related_refs(message),
                        "raw": dict(row),
                    }

        for item in self._fallback_logs_from_files(cap=2000):
            if _to_str(item.get("id")) == target:
                message = _to_str(item.get("message"))
                return {
                    "id": _to_str(item.get("id")),
                    "level": _to_str(item.get("level")).upper() or "INFO",
                    "component": _to_str(item.get("component")) or "system",
                    "message": message,
                    "timestamp": _to_str(item.get("timestamp")),
                    "related": self._extract_related_refs(message),
                    "raw": item,
                }

        raise ValueError("Log kaydi bulunamadi.")

    def list_logs(
        self,
        level: str = "",
        component: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        rows = self._load_table_rows(
            "system_logs",
            limit=5000,
            sort_candidates=("timestamp", "created_at", "updated_at"),
        )
        logs: list[dict[str, Any]] = []
        for row in rows:
            message = _to_str(row.get("message"))
            logs.append(
                {
                    "id": _to_str(row.get("id")),
                    "level": _to_str(row.get("level")).upper() or "INFO",
                    "component": _to_str(row.get("component")) or "system",
                    "message": message,
                    "timestamp": _safe_iso(row.get("timestamp") or row.get("created_at")),
                    "related": self._extract_related_refs(message),
                }
            )

        if not logs:
            logs = self._fallback_logs_from_files(cap=600)
            for item in logs:
                item["related"] = self._extract_related_refs(_to_str(item.get("message")))

        level_filter = level.strip().upper()
        component_filter = component.strip().lower()
        if level_filter:
            logs = [item for item in logs if _to_str(item.get("level")).upper() == level_filter]
        if component_filter:
            logs = [item for item in logs if component_filter in _to_str(item.get("component")).lower()]

        logs.sort(key=lambda item: _to_str(item.get("timestamp")), reverse=True)
        total = len(logs)
        return {
            "items": logs[offset : offset + max(1, limit)],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def clear_logs(self, level: str = "", component: str = "") -> dict[str, Any]:
        level_filter = level.strip().upper()
        component_filter = component.strip().lower()

        cleared = 0
        columns = self._table_columns("system_logs")
        if "id" in columns:
            engine = self._engine()
            if engine is not None:
                clauses: list[str] = []
                params: dict[str, Any] = {}
                if level_filter and "level" in columns:
                    clauses.append('UPPER("level") = :level')
                    params["level"] = level_filter
                if component_filter and "component" in columns:
                    clauses.append('LOWER("component") LIKE :component')
                    params["component"] = f"%{component_filter}%"

                sql = 'DELETE FROM "system_logs"'
                if clauses:
                    sql += f' WHERE {" AND ".join(clauses)}'
                with engine.begin() as conn:
                    result = conn.execute(text(sql), params)
                    cleared = int(result.rowcount or 0)

        cleared_files = 0
        if not level_filter and not component_filter:
            for path in (PROJECT_ROOT / "backend-dev.err.log", PROJECT_ROOT / "backend-dev.out.log"):
                try:
                    if path.exists():
                        path.write_text("", encoding="utf-8")
                        cleared_files += 1
                except Exception:
                    continue

        return {
            "status": "ok",
            "message": f"{cleared} kayıt temizlendi.",
            "cleared": cleared,
            "cleared_files": cleared_files,
            "filters": {
                "level": level_filter,
                "component": component_filter,
            },
        }

    def list_chunk_samples(self, document_id: str, limit: int = 6) -> dict[str, Any]:
        target = document_id.strip()
        if not target:
            raise ValueError("Belge kimliği gerekli.")
        capped_limit = max(1, min(50, limit))

        columns = self._table_columns("document_chunks")
        if "document_id" in columns:
            text_column = next(
                (name for name in ("chunk_text", "content", "text") if name in columns),
                "",
            )
            index_column = next((name for name in ("chunk_index", "idx", "position") if name in columns), "")
            if text_column:
                order_clause = f' ORDER BY "{index_column}" ASC' if index_column else ""
                sql = (
                    f'SELECT "{text_column}" AS chunk_text'
                    + (f', "{index_column}" AS chunk_index' if index_column else "")
                    + ' FROM "document_chunks" WHERE "document_id"::text = :document_id'
                    + order_clause
                    + " LIMIT :limit"
                )
                engine = self._engine()
                if engine is not None:
                    with engine.connect() as conn:
                        rows = conn.execute(
                            text(sql),
                            {"document_id": target, "limit": capped_limit},
                        ).mappings().all()
                    items = [
                        {
                            "chunk_index": _to_int(row.get("chunk_index"), default=index),
                            "content": _to_str(row.get("chunk_text")),
                        }
                        for index, row in enumerate(rows)
                    ]
                    return {"document_id": target, "items": items, "total": len(items)}

        detail = self.get_document_detail(target)
        source_id = _to_str(_to_dict(detail.get("document")).get("source_id"))
        collection = get_documents_collection()
        items: list[dict[str, Any]] = []
        try:
            result = collection.get(
                where={"document_id": target},
                include=["documents", "metadatas"],
                limit=capped_limit,
            )
            documents = result.get("documents") or []
            metadata = result.get("metadatas") or []
            for index, content in enumerate(documents):
                meta = metadata[index] if index < len(metadata) and isinstance(metadata[index], dict) else {}
                items.append(
                    {
                        "chunk_index": _to_int(meta.get("chunk_index"), default=index),
                        "content": _to_str(content),
                    }
                )
        except Exception:
            items = []

        if not items and source_id:
            try:
                result = collection.get(
                    where={"source_id": source_id},
                    include=["documents", "metadatas"],
                    limit=capped_limit,
                )
                documents = result.get("documents") or []
                metadata = result.get("metadatas") or []
                for index, content in enumerate(documents):
                    meta = metadata[index] if index < len(metadata) and isinstance(metadata[index], dict) else {}
                    items.append(
                        {
                            "chunk_index": _to_int(meta.get("chunk_index"), default=index),
                            "content": _to_str(content),
                        }
                    )
            except Exception:
                items = []

        return {"document_id": target, "items": items, "total": len(items)}

    def table_status(self) -> dict[str, bool]:
        return {name: self._table_exists(name) for name in TARGET_PHASE1_TABLES}

    def dashboard(self) -> dict[str, Any]:
        documents = self.list_documents(limit=6, offset=0)
        chunk_summary = self.list_chunk_summary(limit=20)
        jobs = self.list_ingest_jobs(limit=5000, offset=0)
        logs = self.list_logs(limit=5000, offset=0)
        conversations = self.list_conversations(limit=6, offset=0)

        table_status = self.table_status()
        missing_tables = [name for name, exists in table_status.items() if not exists]

        active_statuses = {"running", "active", "processing"}
        pending_statuses = {"queued", "pending", "waiting"}

        active_jobs = 0
        pending_jobs = 0
        failed_jobs = 0
        for item in jobs["items"]:
            status_value = _to_str(item.get("status")).lower()
            if status_value in active_statuses:
                active_jobs += 1
            if status_value in pending_statuses:
                pending_jobs += 1
            if status_value in {"failed", "error"}:
                failed_jobs += 1

        recent_errors = [
            item for item in logs["items"] if _to_str(item.get("level")).upper() in {"ERROR", "CRITICAL"}
        ][:6]

        return {
            "counts": {
                "users": self._user_count(),
                "documents": _to_int(documents.get("total")),
                "chunks": _to_int(chunk_summary.get("total_chunks")),
                "ingest_active": active_jobs,
                "ingest_pending": pending_jobs,
                "ingest_failed": failed_jobs,
            },
            "recent_errors": recent_errors,
            "recent_conversations": conversations["items"],
            "recent_documents": documents["items"],
            "tables": table_status,
            "missing_tables": missing_tables,
        }


admin_data_service = AdminDataService()
