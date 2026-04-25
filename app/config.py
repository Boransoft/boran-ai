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
    upload_max_file_size_mb: int = 100

    documents_collection: str = "documents"
    conversation_collection: str = "conversation_memory"
    corrections_collection: str = "user_corrections"

    tesseract_cmd: str | None = Field(default=None)

    dataset_preview_rows: int = 200
    auto_consolidation_enabled: bool = True
    consolidation_interval_seconds: int = 300
    consolidation_min_new_items: int = 8
    semantic_link_threshold: float = 0.82
    graph_co_occurrence_window: int = 4
    cluster_min_size: int = 2
    memory_decay_days: int = 30
    memory_importance_default: float = 1.0

    database_url: str | None = None

    jwt_secret_key: str = "change-this-jwt-secret-key-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    admin_identifiers: str = ""

    voice_stt_provider: str = "faster_whisper"
    voice_tts_provider: str = "edge"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_default_language: str | None = "tr"
    whisper_beam_size: int = 1
    whisper_best_of: int = 1
    whisper_vad_filter: bool = False
    tts_model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"
    voice_output_dir: str = str(DATA_ROOT / "voice" / "output")
    audio_upload_dir: str = str(DATA_ROOT / "voice" / "uploads")
    edge_tts_voice: str = "auto"
    edge_tts_voice_profile: str = "female"
    edge_tts_voice_female: str = "tr-TR-EmelNeural"
    edge_tts_voice_male: str = "tr-TR-AhmetNeural"
    edge_tts_rate: str = "-5%"
    edge_tts_pitch: str = "+0Hz"
    coqui_speaker: str | None = None
    coqui_language: str | None = None
    voice_output_format: str = "mp3"
    voice_include_reflection_default: bool = True
    voice_file_ttl_hours: int = 24
    voice_tts_max_chars: int = 700
    voice_warmup_enabled: bool = True
    chat_doc_context_limit: int = 2
    chat_conversation_context_limit: int = 2
    chat_correction_context_limit: int = 1
    chat_long_term_context_limit: int = 2
    chat_cluster_context_limit: int = 2
    chat_semantic_context_limit: int = 2
    chat_graph_context_limit: int = 3
    chat_max_context_chars: int = 3200
    rag_per_source_cap_min: int = 2
    rag_per_source_cap_max: int = 4
    cors_allow_origins: str = "*"
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"
    cors_allow_credentials: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
