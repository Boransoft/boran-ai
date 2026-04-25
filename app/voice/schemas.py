from pydantic import BaseModel, Field


class VoiceTranscribeResponse(BaseModel):
    status: str
    user_id: str
    text: str
    language: str = ""
    provider: str
    audio_file: str
    upload_mime_type: str = ""


class VoiceSpeakRequest(BaseModel):
    text: str
    audio_format: str = "mp3"
    stream_audio: bool = False


class VoiceSpeakResponse(BaseModel):
    status: str
    user_id: str
    text: str
    provider: str
    audio_format: str
    audio_file: str
    audio_url: str
    warning: str = ""
    tts_voice: str = ""
    tts_rate: str = ""
    tts_pitch: str = ""


class VoiceChatResponse(BaseModel):
    status: str
    user_id: str
    transcript: str
    reply: str
    stt_provider: str
    tts_provider: str
    audio_format: str
    audio_file: str
    audio_url: str
    warning: str = ""
    upload_mime_type: str = ""
    tts_voice: str = ""
    tts_rate: str = ""
    tts_pitch: str = ""
    debug_timing: dict[str, object] = Field(default_factory=dict)


class VoiceBackendState(BaseModel):
    provider: str
    ready: bool
    detail: str = ""
    config: dict[str, object] = Field(default_factory=dict)


class VoiceHealthResponse(BaseModel):
    status: str
    stt: VoiceBackendState
    tts: VoiceBackendState
    preferred_upload_field: str = "audio"
    alternative_upload_fields: list[str] = Field(default_factory=lambda: ["file"])
    supported_input_mime_types: list[str] = Field(default_factory=list)


class VoiceTranscribeInternal(BaseModel):
    text: str
    language: str = ""
    provider: str


class VoiceSynthesizeInternal(BaseModel):
    provider: str
    output_path: str
    audio_format: str
    warning: str = ""
