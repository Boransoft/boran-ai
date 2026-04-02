from __future__ import annotations

import threading
from pathlib import Path

from app.config import settings


class STTError(RuntimeError):
    pass


class FasterWhisperProvider:
    def __init__(self):
        self._lock = threading.Lock()
        self._model = None
        self._error = ""

    def _load_model(self):
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except Exception as exc:
                self._error = f"faster-whisper import failed: {exc}"
                raise STTError(self._error) from exc

            try:
                self._model = WhisperModel(
                    model_size_or_path=settings.whisper_model_size,
                    device="auto",
                    compute_type=settings.whisper_compute_type,
                )
                return self._model
            except Exception as exc:
                self._error = f"faster-whisper model load failed: {exc}"
                raise STTError(self._error) from exc

    def transcribe(self, audio_path: Path, language: str | None = None) -> dict[str, str]:
        model = self._load_model()
        try:
            segments, info = model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=True,
            )
            text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
            detected = getattr(info, "language", "") or ""
            return {
                "text": text,
                "language": detected,
                "provider": "faster_whisper",
            }
        except Exception as exc:
            raise STTError(f"transcription failed: {exc}") from exc

    def health(self) -> dict[str, object]:
        detail = self._error
        ready = self._model is not None
        if not detail and not ready:
            detail = "model not loaded yet"
        return {
            "provider": "faster_whisper",
            "ready": ready,
            "detail": detail,
        }


class STTService:
    def __init__(self):
        self.provider_name = settings.voice_stt_provider.strip().lower()
        if self.provider_name == "faster_whisper":
            self.provider = FasterWhisperProvider()
        else:
            self.provider = None

    def transcribe(self, audio_path: Path, language: str | None = None) -> dict[str, str]:
        if self.provider is None:
            raise STTError(f"unsupported stt provider: {self.provider_name}")
        return self.provider.transcribe(audio_path=audio_path, language=language)

    def health(self) -> dict[str, object]:
        if self.provider is None:
            return {
                "provider": self.provider_name,
                "ready": False,
                "detail": "unsupported provider",
            }
        return self.provider.health()


stt_service = STTService()
