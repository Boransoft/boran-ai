from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.services.llm_service import LLMAnswer


def test_chat_general_message_calls_llm(monkeypatch):
    client = TestClient(app)
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(routes, "build_obsidian_context", lambda keys: "")
    monkeypatch.setattr(routes, "debug_obsidian_files", lambda keys: [])
    monkeypatch.setattr(
        routes,
        "_build_document_context",
        lambda req, user_id: ("", {"doc_context_hits": 0, "retrieval_debug": {"test": True}}),
    )

    def fake_generate_obsidian_answer(message, route, obsidian_context, document_context=""):
        calls.append(
            {
                "message": message,
                "area": route.area,
                "document_context": document_context,
            }
        )
        return LLMAnswer(reply="Merhaba.", used_llm=True, error="")

    monkeypatch.setattr(routes, "generate_obsidian_answer", fake_generate_obsidian_answer)

    response = client.post("/chat", json={"user_id": "u1", "message": "merhaba"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"] == "Merhaba."
    assert payload["used_llm"] is True
    assert payload["llm_error"] == ""
    assert payload["route"]["area"] == "Genel"
    assert payload["requires_document"] is False
    assert calls and calls[0]["message"] == "merhaba"


def test_chat_lm_error_is_exposed(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(routes, "build_obsidian_context", lambda keys: "")
    monkeypatch.setattr(routes, "debug_obsidian_files", lambda keys: [])
    monkeypatch.setattr(
        routes,
        "_build_document_context",
        lambda req, user_id: ("", {"doc_context_hits": 0}),
    )
    monkeypatch.setattr(
        routes,
        "generate_obsidian_answer",
        lambda message, route, obsidian_context, document_context="": LLMAnswer(
            reply="LM Studio su an bagli degil.",
            used_llm=False,
            error="connection refused",
        ),
    )

    response = client.post("/chat", json={"user_id": "u1", "message": "merhaba"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["used_llm"] is False
    assert "connection refused" in payload["llm_error"]
    assert payload["router_bypass_reason"] == ""


def test_chat_document_question_without_context_does_not_call_llm(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(routes, "build_obsidian_context", lambda keys: "")
    monkeypatch.setattr(routes, "debug_obsidian_files", lambda keys: [])
    monkeypatch.setattr(
        routes,
        "_build_document_context",
        lambda req, user_id: ("", {"doc_context_hits": 0}),
    )

    def fail_generate(*args, **kwargs):
        raise AssertionError("LLM should not be called without document context")

    monkeypatch.setattr(routes, "generate_obsidian_answer", fail_generate)

    response = client.post(
        "/chat",
        json={"user_id": "u1", "message": "yüklediğim pdf belgesindeki maddeleri getir"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["used_llm"] is False
    assert payload["requires_document"] is True
    assert payload["router_bypass_reason"].startswith("explicit_document_keyword")
    assert "gerçek belge" in payload["reply"] or "gercek belge" in payload["reply"]


def test_chat_boranai_pdf_architecture_question_calls_llm(monkeypatch):
    client = TestClient(app)
    called = {"value": False}

    monkeypatch.setattr(routes, "build_obsidian_context", lambda keys: "Boran.ai context")
    monkeypatch.setattr(routes, "debug_obsidian_files", lambda keys: [])
    monkeypatch.setattr(
        routes,
        "_build_document_context",
        lambda req, user_id: ("", {"doc_context_hits": 0}),
    )

    def fake_generate_obsidian_answer(message, route, obsidian_context, document_context=""):
        called["value"] = True
        return LLMAnswer(reply="PDF ogrenme mimarisi yaniti.", used_llm=True, error="")

    monkeypatch.setattr(routes, "generate_obsidian_answer", fake_generate_obsidian_answer)

    response = client.post(
        "/chat",
        json={"user_id": "u1", "message": "Boran.ai PDF öğrenme mimarisi nasıl çalışmalı?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert called["value"] is True
    assert payload["used_llm"] is True
    assert payload["requires_document"] is False
    assert payload["route"]["area"] == "Boran.ai"
