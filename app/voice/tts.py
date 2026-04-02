from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from app.config import settings


class TTSError(RuntimeError):
    pass


class CoquiTTSProvider:
    def __init__(self):
        self._lock = threading.Lock()
        self._tts = None
        self._error = ""

    def _load_model(self):
        with self._lock:
            if self._tts is not None:
                return self._tts
            try:
                from TTS.api import TTS  # type: ignore
            except Exception as exc:
                self._error = f"coqui import failed: {exc}"
                raise TTSError(self._error) from exc

            try:
                self._tts = TTS(model_name=settings.tts_model_name)
                return self._tts
            except Exception as exc:
                self._error = f"coqui model load failed: {exc}"
                raise TTSError(self._error) from exc

    def synthesize(self, text: str, output_path: Path, audio_format: str) -> dict[str, str]:
        tts = self._load_model()
        effective_format = "wav"
        final_path = output_path.with_suffix(".wav")

        kwargs = {}
        if settings.coqui_speaker:
            kwargs["speaker"] = settings.coqui_speaker
        if settings.coqui_language:
            kwargs["language"] = settings.coqui_language

        try:
            tts.tts_to_file(text=text, file_path=str(final_path), **kwargs)
        except Exception as exc:
            raise TTSError(f"coqui synth failed: {exc}") from exc

        warning = ""
        if audio_format.lower() == "mp3":
            warning = "coqui provider currently returns wav in this MVP"

        return {
            "provider": "coqui",
            "output_path": str(final_path),
            "audio_format": effective_format,
            "warning": warning,
        }

    def health(self) -> dict[str, object]:
        detail = self._error
        ready = self._tts is not None
        if not detail and not ready:
            detail = "model not loaded yet"
        return {
            "provider": "coqui",
            "ready": ready,
            "detail": detail,
        }


class EdgeTTSProvider:
    def __init__(self):
        self._error = ""

    async def _save_audio(self, text: str, output_path: Path) -> None:
        try:
            import edge_tts  # type: ignore
        except Exception as exc:
            self._error = f"edge-tts import failed: {exc}"
            raise TTSError(self._error) from exc

        try:
            communicate = edge_tts.Communicate(text=text, voice=settings.edge_tts_voice)
            await communicate.save(str(output_path))
        except Exception as exc:
            self._error = f"edge-tts synth failed: {exc}"
            raise TTSError(self._error) from exc

    def synthesize(self, text: str, output_path: Path, audio_format: str) -> dict[str, str]:
        final_path = output_path.with_suffix(".mp3")
        try:
            asyncio.run(self._save_audio(text=text, output_path=final_path))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._save_audio(text=text, output_path=final_path))
            finally:
                loop.close()

        warning = ""
        if audio_format.lower() == "wav":
            warning = "edge provider returns mp3 in this MVP"

        return {
            "provider": "edge",
            "output_path": str(final_path),
            "audio_format": "mp3",
            "warning": warning,
        }

    def health(self) -> dict[str, object]:
        detail = self._error or "edge service not preloaded"
        return {
            "provider": "edge",
            "ready": True,
            "detail": detail,
        }


class TTSService:
    def __init__(self):
        self.provider_name = settings.voice_tts_provider.strip().lower()
        if self.provider_name == "coqui":
            self.provider = CoquiTTSProvider()
        elif self.provider_name == "edge":
            self.provider = EdgeTTSProvider()
        else:
            self.provider = None

    def synthesize(self, text: str, output_path: Path, audio_format: str) -> dict[str, str]:
        if not text.strip():
            raise TTSError("empty text")
        if self.provider is None:
            raise TTSError(f"unsupported tts provider: {self.provider_name}")
        return self.provider.synthesize(text=text, output_path=output_path, audio_format=audio_format)

    def health(self) -> dict[str, object]:
        if self.provider is None:
            return {
                "provider": self.provider_name,
                "ready": False,
                "detail": "unsupported provider",
            }
        return self.provider.health()


tts_service = TTSService()
