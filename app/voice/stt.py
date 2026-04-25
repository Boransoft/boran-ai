from __future__ import annotations

import logging
import threading
from pathlib import Path
from time import perf_counter

from app.config import settings

logger = logging.getLogger(__name__)


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
            load_started = perf_counter()
            logger.info(
                "stt_lazy_init_start provider=faster_whisper model=%s device=%s compute_type=%s",
                settings.whisper_model_size,
                settings.whisper_device,
                settings.whisper_compute_type,
            )
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except Exception as exc:
                self._error = f"faster-whisper import failed: {exc}"
                logger.warning(
                    "stt_lazy_init_failed stage=import duration_s=%.3f error=%s",
                    perf_counter() - load_started,
                    self._error,
                )
                raise STTError(self._error) from exc

            try:
                self._model = WhisperModel(
                    model_size_or_path=settings.whisper_model_size,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )
                logger.info("stt_lazy_init_done duration_s=%.3f", perf_counter() - load_started)
                return self._model
            except Exception as exc:
                self._error = f"faster-whisper model load failed: {exc}"
                logger.warning(
                    "stt_lazy_init_failed stage=model_load duration_s=%.3f error=%s",
                    perf_counter() - load_started,
                    self._error,
                )
                raise STTError(self._error) from exc

    def transcribe(self, audio_path: Path, language: str | None = None) -> dict[str, str]:
        model = self._load_model()
        try:
            target_language = language or settings.whisper_default_language or None
            segments, info = model.transcribe(
                str(audio_path),
                language=target_language,
                vad_filter=settings.whisper_vad_filter,
                beam_size=max(1, int(settings.whisper_beam_size)),
                best_of=max(1, int(settings.whisper_best_of)),
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

    def warmup(self) -> dict[str, object]:
        try:
            self._load_model()
            return {"ready": True, "detail": "model loaded"}
        except Exception as exc:
            logger.warning("STT warmup failed: %s", exc)
            return {"ready": False, "detail": str(exc)}

    def health(self) -> dict[str, object]:
        detail = self._error
        ready = self._model is not None
        if not detail and not ready:
            detail = "model not loaded yet"
        return {
            "provider": "faster_whisper",
            "ready": ready,
            "detail": detail,
            "config": {
                "model": settings.whisper_model_size,
                "device": settings.whisper_device,
                "compute_type": settings.whisper_compute_type,
                "language": settings.whisper_default_language or "",
                "beam_size": str(settings.whisper_beam_size),
                "vad_filter": str(settings.whisper_vad_filter).lower(),
            },
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

    def warmup(self) -> dict[str, object]:
        if self.provider is None:
            return {
                "provider": self.provider_name,
                "ready": False,
                "detail": "unsupported provider",
            }
        return self.provider.warmup()

    def health(self) -> dict[str, object]:
        if self.provider is None:
            return {
                "provider": self.provider_name,
                "ready": False,
                "detail": "unsupported provider",
            }
        return self.provider.health()


stt_service = STTService()
