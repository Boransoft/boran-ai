import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth.utils import create_access_token
from app.main import app
from app.voice.routes import voice_service


def _auth_header(user_id: str) -> dict[str, str]:
    token, _ = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_voice_health_requires_auth():
    client = TestClient(app)
    response = client.get("/voice/health")
    assert response.status_code == 401


def test_voice_demo_page_public():
    client = TestClient(app)
    response = client.get("/voice/demo")
    assert response.status_code == 200
    assert "boran.ai Voice Test" in response.text


def test_voice_transcribe_smoke(monkeypatch):
    client = TestClient(app)

    def fake_transcribe(user_id: str, upload, language: str | None = None):
        assert user_id == "voice-user"
        assert language == "tr"
        return {
            "text": "merhaba boran ai",
            "language": "tr",
            "provider": "faster_whisper",
            "audio_file": "fake.wav",
        }

    monkeypatch.setattr(voice_service, "transcribe_audio", fake_transcribe)

    response = client.post(
        "/voice/transcribe",
        headers=_auth_header("voice-user"),
        files={"audio": ("sample.wav", b"RIFF....", "audio/wav")},
        data={"language": "tr"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "merhaba boran ai"
    assert payload["provider"] == "faster_whisper"


def test_voice_speak_smoke(monkeypatch):
    client = TestClient(app)

    def fake_synthesize(user_id: str, text: str, audio_format: str | None = None):
        assert user_id == "voice-user"
        assert text
        return {
            "provider": "edge",
            "audio_format": "mp3",
            "audio_file": "abc.mp3",
            "audio_url": "/voice/audio/abc.mp3",
            "warning": "",
        }

    monkeypatch.setattr(voice_service, "synthesize_text", fake_synthesize)

    response = client.post(
        "/voice/speak",
        headers=_auth_header("voice-user"),
        json={
            "text": "test reply",
            "audio_format": "mp3",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["audio_url"].startswith("/voice/audio/")
    assert payload["audio_format"] == "mp3"


def test_voice_chat_smoke(monkeypatch):
    client = TestClient(app)

    def fake_voice_chat(
        user_id: str,
        upload,
        language: str | None = None,
        save_to_long_term: bool = True,
        include_reflection_context: bool | None = None,
        audio_format: str | None = None,
    ):
        assert user_id == "voice-user"
        return {
            "status": "ok",
            "user_id": user_id,
            "transcript": "soru",
            "reply": "yanit",
            "stt_provider": "faster_whisper",
            "tts_provider": "coqui",
            "audio_format": "wav",
            "audio_file": "reply.wav",
            "audio_url": "/voice/audio/reply.wav",
            "warning": "",
        }

    monkeypatch.setattr(voice_service, "voice_chat", fake_voice_chat)

    response = client.post(
        "/voice/chat",
        headers=_auth_header("voice-user"),
        files={"audio": ("ask.wav", b"RIFF....", "audio/wav")},
        data={
            "language": "tr",
            "save_to_long_term": "true",
            "include_reflection_context": "true",
            "audio_format": "wav",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == "soru"
    assert payload["reply"] == "yanit"
    assert payload["audio_file"] == "reply.wav"


def test_voice_chat_accepts_file_field(monkeypatch):
    client = TestClient(app)

    def fake_voice_chat(
        user_id: str,
        upload,
        language: str | None = None,
        save_to_long_term: bool = True,
        include_reflection_context: bool | None = None,
        audio_format: str | None = None,
    ):
        assert upload.filename == "ask.webm"
        return {
            "status": "ok",
            "user_id": user_id,
            "transcript": "test transcript",
            "reply": "test reply",
            "stt_provider": "faster_whisper",
            "tts_provider": "coqui",
            "audio_format": "mp3",
            "audio_file": "reply.mp3",
            "audio_url": "/voice/audio/reply.mp3",
            "warning": "",
        }

    monkeypatch.setattr(voice_service, "voice_chat", fake_voice_chat)

    response = client.post(
        "/voice/chat",
        headers=_auth_header("voice-user"),
        files={"file": ("ask.webm", b"WEBM....", "audio/webm")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == "test transcript"
    assert payload["audio_url"].endswith(".mp3")


def test_voice_transcribe_rejects_unsupported_mime():
    client = TestClient(app)
    response = client.post(
        "/voice/transcribe",
        headers=_auth_header("voice-user"),
        files={"audio": ("bad.txt", b"not audio", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported audio mime type" in response.json().get("detail", "")


def test_voice_audio_user_isolation():
    client = TestClient(app)
    temp_dir = Path(".tmp") / "test_voice_audio_user_isolation"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    original_output_dir = voice_service.output_dir
    voice_service.output_dir = temp_dir
    try:
        user1 = "user-one"
        user2 = "user-two"

        user1_prefix = voice_service._user_prefix(user1)
        file_name = f"{user1_prefix}_test.wav"
        file_path = temp_dir / file_name
        file_path.write_bytes(b"fakewav")

        ok_response = client.get(f"/voice/audio/{file_name}", headers=_auth_header(user1))
        assert ok_response.status_code == 200

        forbidden = client.get(f"/voice/audio/{file_name}", headers=_auth_header(user2))
        assert forbidden.status_code == 403
    finally:
        voice_service.output_dir = original_output_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
