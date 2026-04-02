from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.services.assistant import build_reply
from app.voice.stt import STTError, stt_service
from app.voice.tts import TTSError, tts_service


SUPPORTED_AUDIO_MIME_TYPES = (
    "audio/webm",
    "video/webm",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/3gpp",
    "audio/3gpp2",
    "application/octet-stream",
)

MIME_TO_EXTENSION = {
    "audio/webm": "webm",
    "video/webm": "webm",
    "audio/ogg": "ogg",
    "audio/opus": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
    "audio/3gpp": "3gp",
    "audio/3gpp2": "3g2",
}

ALLOWED_EXTENSIONS = {
    "webm",
    "ogg",
    "wav",
    "mp3",
    "m4a",
    "aac",
    "3gp",
    "3g2",
    "mp4",
}


class VoiceValidationError(ValueError):
    pass


class VoiceService:
    def __init__(self):
        self.upload_dir = Path(settings.audio_upload_dir)
        self.output_dir = Path(settings.voice_output_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _user_prefix(self, user_id: str) -> str:
        return hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:12]

    def _make_name(self, user_id: str, extension: str) -> str:
        ext = extension.lower().replace(".", "")
        if ext not in ALLOWED_EXTENSIONS:
            ext = "bin"
        return f"{self._user_prefix(user_id)}_{uuid.uuid4().hex}.{ext}"

    def _normalize_content_type(self, upload: UploadFile) -> str:
        raw = (upload.content_type or "").strip().lower()
        if not raw:
            return "application/octet-stream"
        return raw.split(";", 1)[0].strip()

    def _filename_extension(self, upload: UploadFile) -> str:
        if not upload.filename or "." not in upload.filename:
            return ""
        return upload.filename.rsplit(".", 1)[1].strip().lower()

    def _normalize_upload_format(self, upload: UploadFile) -> tuple[str, str]:
        content_type = self._normalize_content_type(upload)
        extension_from_name = self._filename_extension(upload)

        if content_type not in SUPPORTED_AUDIO_MIME_TYPES:
            if extension_from_name in ALLOWED_EXTENSIONS:
                return extension_from_name, "application/octet-stream"
            raise VoiceValidationError(
                "Unsupported audio mime type. "
                f"Received: {content_type or 'unknown'}. "
                "Supported: " + ", ".join(SUPPORTED_AUDIO_MIME_TYPES)
            )

        if content_type == "application/octet-stream":
            if extension_from_name in ALLOWED_EXTENSIONS:
                return extension_from_name, content_type
            raise VoiceValidationError(
                "Unknown audio format. Provide a known audio mime type or filename extension."
            )

        resolved_ext = MIME_TO_EXTENSION.get(content_type, "")
        if resolved_ext in ALLOWED_EXTENSIONS:
            return resolved_ext, content_type

        if extension_from_name in ALLOWED_EXTENSIONS:
            return extension_from_name, content_type

        raise VoiceValidationError(
            f"Could not determine upload extension for content-type: {content_type}"
        )

    def supported_input_mime_types(self) -> list[str]:
        return list(SUPPORTED_AUDIO_MIME_TYPES)

    def cleanup_old_files(self) -> dict[str, int]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=settings.voice_file_ttl_hours)
        removed_uploads = 0
        removed_outputs = 0

        for root, counter_name in ((self.upload_dir, "uploads"), (self.output_dir, "outputs")):
            for item in root.glob("*"):
                if not item.is_file():
                    continue
                modified = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
                if modified < cutoff:
                    try:
                        item.unlink(missing_ok=True)
                    except Exception:
                        continue
                    if counter_name == "uploads":
                        removed_uploads += 1
                    else:
                        removed_outputs += 1

        return {
            "removed_uploads": removed_uploads,
            "removed_outputs": removed_outputs,
        }

    def save_upload(self, user_id: str, upload: UploadFile) -> tuple[Path, str]:
        extension, content_type = self._normalize_upload_format(upload)
        file_name = self._make_name(user_id=user_id, extension=extension)
        target = self.upload_dir / file_name

        with target.open("wb") as handle:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        return target, content_type

    def transcribe_audio(self, user_id: str, upload: UploadFile, language: str | None = None) -> dict[str, str]:
        self.cleanup_old_files()
        source_path, upload_mime_type = self.save_upload(user_id=user_id, upload=upload)
        result = stt_service.transcribe(audio_path=source_path, language=language)
        result["audio_file"] = source_path.name
        result["upload_mime_type"] = upload_mime_type
        return result

    def synthesize_text(
        self,
        user_id: str,
        text: str,
        audio_format: str | None = None,
    ) -> dict[str, str]:
        self.cleanup_old_files()
        target_format = (audio_format or settings.voice_output_format).lower()
        base_name = self._make_name(user_id=user_id, extension=target_format)
        base_path = self.output_dir / base_name
        synth = tts_service.synthesize(text=text, output_path=base_path, audio_format=target_format)

        output_path = Path(synth["output_path"])
        synth["audio_file"] = output_path.name
        synth["audio_url"] = f"/voice/audio/{output_path.name}"
        return synth

    def resolve_output_file(self, user_id: str, file_name: str) -> Path:
        normalized = os.path.basename(file_name)
        if normalized != file_name:
            raise PermissionError("invalid filename")
        if not normalized.startswith(f"{self._user_prefix(user_id)}_"):
            raise PermissionError("file does not belong to user")

        path = self.output_dir / normalized
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(normalized)
        return path

    def voice_chat(
        self,
        user_id: str,
        upload: UploadFile,
        language: str | None = None,
        save_to_long_term: bool = True,
        include_reflection_context: bool | None = None,
        audio_format: str | None = None,
    ) -> dict[str, str]:
        include_reflection = (
            settings.voice_include_reflection_default
            if include_reflection_context is None
            else bool(include_reflection_context)
        )

        transcribed = self.transcribe_audio(user_id=user_id, upload=upload, language=language)
        transcript = transcribed.get("text", "").strip()
        if not transcript:
            raise STTError("transcription returned empty text")

        chat_result = build_reply(
            user_id=user_id,
            message=transcript,
            save_to_long_term=save_to_long_term,
            include_reflection_context=include_reflection,
        )
        reply_text = str(chat_result.get("reply", "")).strip()

        tts_result = self.synthesize_text(
            user_id=user_id,
            text=reply_text,
            audio_format=audio_format,
        )

        return {
            "status": "ok",
            "user_id": user_id,
            "transcript": transcript,
            "reply": reply_text,
            "stt_provider": transcribed.get("provider", ""),
            "tts_provider": tts_result.get("provider", ""),
            "audio_format": tts_result.get("audio_format", ""),
            "audio_file": tts_result.get("audio_file", ""),
            "audio_url": tts_result.get("audio_url", ""),
            "warning": tts_result.get("warning", ""),
            "upload_mime_type": transcribed.get("upload_mime_type", ""),
        }

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "stt": stt_service.health(),
            "tts": tts_service.health(),
            "preferred_upload_field": "audio",
            "alternative_upload_fields": ["file"],
            "supported_input_mime_types": self.supported_input_mime_types(),
        }


voice_service = VoiceService()
