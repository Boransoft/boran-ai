import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.auth.utils import create_access_token
from app.main import app


def _auth_header(user_id: str) -> dict[str, str]:
    token, _ = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_learning_ingest_document_accepts_file_within_limit(monkeypatch):
    client = TestClient(app)
    temp_dir = Path(".tmp") / "upload-size-ok"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_routes.settings, "upload_max_file_size_mb", 1)
    monkeypatch.setattr(api_routes.settings, "ingest_path", str(temp_dir))

    captured: dict[str, str] = {}

    def fake_ingest_document(user_id: str, file_path: str, category: str, tags: str | None):
        captured["user_id"] = user_id
        captured["file_path"] = file_path
        captured["category"] = category
        captured["tags"] = tags or ""
        return SimpleNamespace(
            status="ok",
            details={
                "status": "ok",
                "source_id": "src_small",
                "chunk_count": 1,
            },
        )

    monkeypatch.setattr(api_routes.learning_pipeline, "ingest_document", fake_ingest_document)

    try:
        response = client.post(
            "/learning/ingest/document",
            headers=_auth_header("upload-user"),
            files={"file": ("small.pdf", b"a" * (512 * 1024), "application/pdf")},
            data={"category": "general"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert captured["user_id"] == "upload-user"
        assert captured["category"] == "general"
        assert Path(captured["file_path"]).name == "small.pdf"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_learning_ingest_document_rejects_oversized_file(monkeypatch):
    client = TestClient(app)
    temp_dir = Path(".tmp") / "upload-size-too-large"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_routes.settings, "upload_max_file_size_mb", 1)
    monkeypatch.setattr(api_routes.settings, "ingest_path", str(temp_dir))

    called = False

    def fake_ingest_document(user_id: str, file_path: str, category: str, tags: str | None):
        nonlocal called
        called = True
        return SimpleNamespace(status="ok", details={"status": "ok"})

    monkeypatch.setattr(api_routes.learning_pipeline, "ingest_document", fake_ingest_document)

    try:
        response = client.post(
            "/learning/ingest/document",
            headers=_auth_header("upload-user"),
            files={"file": ("too-large.pdf", b"a" * (1024 * 1024 + 1), "application/pdf")},
            data={"category": "general"},
        )

        assert response.status_code == 413
        payload = response.json()
        assert "1 MB" in payload.get("detail", "")
        assert called is False
        assert not (temp_dir / "too-large.pdf").exists()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_learning_ingest_document_returns_400_for_unsupported_extension(monkeypatch):
    client = TestClient(app)
    temp_dir = Path(".tmp") / "upload-unsupported-extension"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_routes.settings, "upload_max_file_size_mb", 100)
    monkeypatch.setattr(api_routes.settings, "ingest_path", str(temp_dir))

    try:
        response = client.post(
            "/learning/ingest/document",
            headers=_auth_header("upload-user"),
            files={"file": ("unsupported.bin", b"abc", "application/octet-stream")},
            data={"category": "general"},
        )

        assert response.status_code == 400
        payload = response.json()
        assert "Unsupported file extension" in payload.get("detail", "")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.parametrize(
    ("size_mb", "expected_status"),
    [
        (10, 200),
        (63.3, 200),
        (95, 200),
        (110, 413),
    ],
)
def test_learning_ingest_document_default_100mb_boundaries(monkeypatch, size_mb: float, expected_status: int):
    client = TestClient(app)
    temp_dir = Path(".tmp") / f"upload-size-{size_mb}mb"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api_routes.settings, "upload_max_file_size_mb", 100)
    monkeypatch.setattr(api_routes.settings, "ingest_path", str(temp_dir))

    called = False

    def fake_ingest_document(user_id: str, file_path: str, category: str, tags: str | None):
        nonlocal called
        called = True
        return SimpleNamespace(
            status="ok",
            details={
                "status": "ok",
                "source_id": "src_limit",
                "chunk_count": 1,
            },
        )

    monkeypatch.setattr(api_routes.learning_pipeline, "ingest_document", fake_ingest_document)

    try:
        response = client.post(
            "/learning/ingest/document",
            headers=_auth_header("upload-user"),
            files={"file": ("limit.pdf", b"a" * int(size_mb * 1024 * 1024), "application/pdf")},
            data={"category": "general"},
        )

        assert response.status_code == expected_status
        if expected_status == 200:
            assert called is True
        else:
            payload = response.json()
            assert "100 MB" in payload.get("detail", "")
            assert called is False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
