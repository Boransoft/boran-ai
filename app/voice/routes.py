from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.auth.routes import get_current_external_id
from app.voice.schemas import (
    VoiceChatResponse,
    VoiceHealthResponse,
    VoiceSpeakRequest,
    VoiceSpeakResponse,
    VoiceTranscribeResponse,
)
from app.voice.service import VoiceValidationError, voice_service
from app.voice.stt import STTError
from app.voice.tts import TTSError


router = APIRouter(prefix="/voice", tags=["voice"])
DEMO_DIR = Path(__file__).resolve().parent.parent / "voice_demo"


def _media_type(audio_format: str) -> str:
    fmt = audio_format.lower()
    if fmt == "wav":
        return "audio/wav"
    if fmt == "mp3":
        return "audio/mpeg"
    if fmt == "webm":
        return "audio/webm"
    if fmt == "ogg":
        return "audio/ogg"
    return "application/octet-stream"


def _resolve_upload(
    audio: UploadFile | None,
    fallback_file: UploadFile | None,
) -> UploadFile:
    upload = audio or fallback_file
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing upload. Use multipart field 'audio' (preferred) or 'file'.",
        )
    return upload


@router.get("/demo", include_in_schema=False)
def voice_demo_page():
    return FileResponse(DEMO_DIR / "index.html", media_type="text/html")


@router.get("/demo/app.js", include_in_schema=False)
def voice_demo_js():
    return FileResponse(DEMO_DIR / "app.js", media_type="application/javascript")


@router.get("/demo/styles.css", include_in_schema=False)
def voice_demo_css():
    return FileResponse(DEMO_DIR / "styles.css", media_type="text/css")


@router.get("/health", response_model=VoiceHealthResponse)
def voice_health(
    current_user_id: str = Depends(get_current_external_id),
):
    _ = current_user_id
    return voice_service.health()


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
def voice_transcribe(
    audio: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
    current_user_id: str = Depends(get_current_external_id),
):
    upload = _resolve_upload(audio=audio, fallback_file=file)
    try:
        result = voice_service.transcribe_audio(
            user_id=current_user_id,
            upload=upload,
            language=language,
        )
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except STTError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "status": "ok",
        "user_id": current_user_id,
        "text": result.get("text", ""),
        "language": result.get("language", ""),
        "provider": result.get("provider", ""),
        "audio_file": result.get("audio_file", ""),
        "upload_mime_type": result.get("upload_mime_type", ""),
    }


@router.post("/speak", response_model=VoiceSpeakResponse)
def voice_speak(
    req: VoiceSpeakRequest,
    current_user_id: str = Depends(get_current_external_id),
):
    try:
        result = voice_service.synthesize_text(
            user_id=current_user_id,
            text=req.text,
            audio_format=req.audio_format,
        )
    except TTSError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if req.stream_audio:
        path = voice_service.resolve_output_file(
            user_id=current_user_id,
            file_name=result.get("audio_file", ""),
        )
        return FileResponse(path=path, media_type=_media_type(result.get("audio_format", "")))

    return {
        "status": "ok",
        "user_id": current_user_id,
        "text": req.text,
        "provider": result.get("provider", ""),
        "audio_format": result.get("audio_format", ""),
        "audio_file": result.get("audio_file", ""),
        "audio_url": result.get("audio_url", ""),
        "warning": result.get("warning", ""),
        "tts_voice": result.get("tts_voice", ""),
        "tts_rate": result.get("tts_rate", ""),
        "tts_pitch": result.get("tts_pitch", ""),
    }


@router.post("/chat", response_model=VoiceChatResponse)
def voice_chat(
    audio: UploadFile | None = File(default=None),
    file: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
    save_to_long_term: bool = Form(default=True),
    include_reflection_context: bool | None = Form(default=None),
    audio_format: str | None = Form(default=None),
    debug_timing: bool = Query(default=False),
    current_user_id: str = Depends(get_current_external_id),
):
    upload = _resolve_upload(audio=audio, fallback_file=file)
    try:
        result = voice_service.voice_chat(
            user_id=current_user_id,
            upload=upload,
            language=language,
            save_to_long_term=save_to_long_term,
            include_reflection_context=include_reflection_context,
            audio_format=audio_format,
            debug_timing=debug_timing,
        )
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (STTError, TTSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result


@router.get("/audio/{file_name}")
def voice_audio(
    file_name: str,
    current_user_id: str = Depends(get_current_external_id),
):
    try:
        path = voice_service.resolve_output_file(user_id=current_user_id, file_name=file_name)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    suffix = path.suffix.lower().replace(".", "")
    return FileResponse(path=path, media_type=_media_type(suffix), filename=path.name)
