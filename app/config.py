from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Boran AI"
    app_version: str = "0.2.0"

    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"
    model_name: str = "qwen2.5-7b-instruct"
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "EMBEDDING_MODEL_NAME"),
    )
    embedding_cache_path: str = str(DATA_ROOT / "models")
    embedding_allow_download: bool = True
    embedding_download_timeout_seconds: float = 1.5

    chroma_path: str = str(DATA_ROOT / "chroma")
    pdf_path: str = str(DATA_ROOT / "pdf")
    memory_path: str = str(DATA_ROOT / "memory")
    graph_path: str = str(DATA_ROOT / "graph")
    ingest_path: str = str(DATA_ROOT / "ingest")

    documents_collection: str = "documents"
    conversation_collection: str = "conversation_memory"
    corrections_collection: str = "user_corrections"

    tesseract_cmd: str | None = Field(default=None)

    dataset_preview_rows: int = 200
    auto_consolidation_enabled: bool = True
    consolidation_interval_seconds: int = 300
    consolidation_min_new_items: int = 8

    database_url: str | None = None

    jwt_secret_key: str = "change-this-jwt-secret-key-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    voice_stt_provider: str = "faster_whisper"
    voice_tts_provider: str = "coqui"
    whisper_model_size: str = "small"
    whisper_compute_type: str = "int8"
    tts_model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"
    voice_output_dir: str = str(DATA_ROOT / "voice" / "output")
    audio_upload_dir: str = str(DATA_ROOT / "voice" / "uploads")
    edge_tts_voice: str = "en-US-AriaNeural"
    coqui_speaker: str | None = None
    coqui_language: str | None = None
    voice_output_format: str = "mp3"
    voice_include_reflection_default: bool = True
    voice_file_ttl_hours: int = 24
    cors_allow_origins: str = "*"
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"
    cors_allow_credentials: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
