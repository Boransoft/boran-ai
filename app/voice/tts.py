from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from time import perf_counter

from app.config import settings


class TTSError(RuntimeError):
    pass


logger = logging.getLogger(__name__)


class CoquiTTSProvider:
    def __init__(self):
        self._lock = threading.Lock()
        self._tts = None
        self._error = ""

    def _load_model(self):
        with self._lock:
            if self._tts is not None:
                return self._tts
            load_started = perf_counter()
            logger.info("tts_lazy_init_start provider=coqui model=%s", settings.tts_model_name)
            try:
                from TTS.api import TTS  # type: ignore
            except Exception as exc:
                self._error = f"coqui import failed: {exc}"
                logger.warning(
                    "tts_lazy_init_failed provider=coqui stage=import duration_s=%.3f error=%s",
                    perf_counter() - load_started,
                    self._error,
                )
                raise TTSError(self._error) from exc

            try:
                self._tts = TTS(model_name=settings.tts_model_name)
                logger.info(
                    "tts_lazy_init_done provider=coqui duration_s=%.3f",
                    perf_counter() - load_started,
                )
                return self._tts
            except Exception as exc:
                self._error = f"coqui model load failed: {exc}"
                logger.warning(
                    "tts_lazy_init_failed provider=coqui stage=model_load duration_s=%.3f error=%s",
                    perf_counter() - load_started,
                    self._error,
                )
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

    def warmup(self) -> dict[str, object]:
        try:
            self._load_model()
            return {"ready": True, "detail": "model loaded"}
        except Exception as exc:
            return {"ready": False, "detail": str(exc)}


class EdgeTTSProvider:
    def __init__(self):
        self._error = ""

    def _resolve_voice(self) -> str:
        override = settings.edge_tts_voice.strip()
        if override and override.lower() != "auto":
            return override

        profile = settings.edge_tts_voice_profile.strip().lower()
        if profile == "male":
            return settings.edge_tts_voice_male
        return settings.edge_tts_voice_female

    async def _save_audio(self, text: str, output_path: Path, voice: str) -> None:
        try:
            import edge_tts  # type: ignore
        except Exception as exc:
            self._error = f"edge-tts import failed: {exc}"
            raise TTSError(self._error) from exc

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=settings.edge_tts_rate,
                pitch=settings.edge_tts_pitch,
            )
            await communicate.save(str(output_path))
        except Exception as exc:
            self._error = f"edge-tts synth failed: {exc}"
            raise TTSError(self._error) from exc

    def synthesize(self, text: str, output_path: Path, audio_format: str) -> dict[str, str]:
        final_path = output_path.with_suffix(".mp3")
        selected_voice = self._resolve_voice()
        try:
            asyncio.run(
                self._save_audio(
                    text=text,
                    output_path=final_path,
                    voice=selected_voice,
                )
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    self._save_audio(
                        text=text,
                        output_path=final_path,
                        voice=selected_voice,
                    )
                )
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
            "tts_voice": selected_voice,
            "tts_rate": settings.edge_tts_rate,
            "tts_pitch": settings.edge_tts_pitch,
        }

    def health(self) -> dict[str, object]:
        detail = self._error or "edge service not preloaded"
        return {
            "provider": "edge",
            "ready": True,
            "detail": detail,
            "config": {
                "voice": self._resolve_voice(),
                "rate": settings.edge_tts_rate,
                "pitch": settings.edge_tts_pitch,
                "profile": settings.edge_tts_voice_profile,
                "voice_female": settings.edge_tts_voice_female,
                "voice_male": settings.edge_tts_voice_male,
            },
        }

    def warmup(self) -> dict[str, object]:
        try:
            import edge_tts  # type: ignore

            _ = edge_tts.__name__
            return {"ready": True, "detail": "edge-tts imported"}
        except Exception as exc:
            self._error = f"edge-tts import failed: {exc}"
            return {"ready": False, "detail": self._error}


class TTSService:
    def __init__(self):
        configured = settings.voice_tts_provider.strip().lower()
        self.preferred_provider_name = configured or "edge"
        self._providers = {
            "coqui": CoquiTTSProvider(),
            "edge": EdgeTTSProvider(),
        }
        self.active_provider_name = (
            self.preferred_provider_name
            if self.preferred_provider_name in self._providers
            else "edge"
        )
        self._last_error = ""

    def _candidate_provider_names(self) -> list[str]:
        names: list[str] = []
        if self.preferred_provider_name in self._providers:
            names.append(self.preferred_provider_name)
        if "edge" in self._providers and "edge" not in names:
            names.append("edge")
        return names

    def synthesize(self, text: str, output_path: Path, audio_format: str) -> dict[str, str]:
        if not text.strip():
            raise TTSError("empty text")
        candidates = self._candidate_provider_names()
        if not candidates:
            raise TTSError(f"unsupported tts provider: {self.preferred_provider_name}")

        errors: list[str] = []
        for idx, provider_name in enumerate(candidates):
            provider = self._providers[provider_name]
            try:
                result = provider.synthesize(text=text, output_path=output_path, audio_format=audio_format)
                self.active_provider_name = provider_name
                self._last_error = ""

                if idx > 0:
                    fallback_note = (
                        f"tts fallback active: preferred={self.preferred_provider_name}, "
                        f"active={provider_name}."
                    )
                    existing_warning = str(result.get("warning", "")).strip()
                    result["warning"] = (
                        f"{existing_warning} {fallback_note}".strip()
                        if existing_warning
                        else fallback_note
                    )
                return result
            except TTSError as exc:
                errors.append(f"{provider_name}: {exc}")
                self._last_error = str(exc)
                continue

        raise TTSError("all tts providers failed: " + " | ".join(errors))

    def health(self) -> dict[str, object]:
        candidates = self._candidate_provider_names()
        if not candidates:
            return {
                "provider": self.preferred_provider_name,
                "ready": False,
                "detail": "unsupported provider",
            }

        providers_health: dict[str, dict[str, object]] = {}
        for name in ("coqui", "edge"):
            if name in self._providers:
                providers_health[name] = self._providers[name].health()

        active = self.active_provider_name
        if active not in providers_health:
            active = candidates[0]

        active_health = providers_health.get(active, {})
        detail = str(active_health.get("detail", "") or "")
        if self._last_error:
            detail = f"{detail} | last_error={self._last_error}".strip(" |")

        return {
            "provider": active,
            "ready": bool(active_health.get("ready", False)),
            "detail": detail,
            "config": {
                "preferred_provider": self.preferred_provider_name,
                "active_provider": active,
                "fallback_provider": "edge" if self.preferred_provider_name != "edge" else "",
                "providers": providers_health,
            },
        }

    def warmup(self) -> dict[str, object]:
        candidates = self._candidate_provider_names()
        if not candidates:
            return {
                "provider": self.preferred_provider_name,
                "ready": False,
                "detail": "unsupported provider",
            }

        warmup_report: dict[str, dict[str, object]] = {}
        for name in candidates:
            provider = self._providers[name]
            if hasattr(provider, "warmup"):
                info = provider.warmup()
            else:
                info = {"ready": True, "detail": "no warmup required"}
            warmup_report[name] = info
            if bool(info.get("ready", False)):
                self.active_provider_name = name
                self._last_error = ""
                break
            self._last_error = str(info.get("detail", "") or self._last_error)

        health_payload = self.health()
        config_payload = dict(health_payload.get("config", {}))
        config_payload["warmup"] = warmup_report
        health_payload["config"] = config_payload
        return health_payload


tts_service = TTSService()
