import shutil
from pathlib import Path

from app.config import settings
from app.voice.tts import TTSError, TTSService


def test_tts_falls_back_to_edge_when_coqui_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "voice_tts_provider", "coqui")
    service = TTSService()
    temp_dir = Path(".tmp") / "test_tts_fallback"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    def fake_coqui_synthesize(*, text: str, output_path: Path, audio_format: str):
        _ = (text, output_path, audio_format)
        raise TTSError("coqui import failed: No module named 'TTS'")

    def fake_edge_synthesize(*, text: str, output_path: Path, audio_format: str):
        _ = (text, audio_format)
        final_path = output_path.with_suffix(".mp3")
        final_path.write_bytes(b"ID3")
        return {
            "provider": "edge",
            "output_path": str(final_path),
            "audio_format": "mp3",
            "warning": "",
        }

    monkeypatch.setattr(service._providers["coqui"], "synthesize", fake_coqui_synthesize)
    monkeypatch.setattr(service._providers["edge"], "synthesize", fake_edge_synthesize)

    try:
        result = service.synthesize(
            text="Merhaba",
            output_path=temp_dir / "reply.wav",
            audio_format="wav",
        )

        assert result["provider"] == "edge"
        assert "tts fallback active" in result.get("warning", "")

        health = service.health()
        assert health["provider"] == "edge"
        config = health.get("config", {})
        assert config.get("preferred_provider") == "coqui"
        assert config.get("active_provider") == "edge"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
