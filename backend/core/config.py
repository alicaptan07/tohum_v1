from functools import lru_cache
from typing import List, Optional
import os
from tempfile import gettempdir

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = Field(default="Tohum v1")
    debug: bool = Field(default=False)

    sqlite_path: str = Field(default="data/memory.sqlite")
    sqlite_journal_mode: str = Field(default="WAL")

    chroma_path: str = Field(default="data/embeddings")
    chroma_collection: str = Field(default="tohum_memory")
    chroma_top_k: int = Field(default=5)

    embedding_model: str = Field(default="intfloat/multilingual-e5-small")
    embedding_fallback_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    rank_bm25_k1: float = Field(default=1.5)
    rank_bm25_b: float = Field(default=0.75)

    memory_chunk_size: int = Field(default=800)
    memory_chunk_overlap: int = Field(default=80)

    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    hf_api_token: Optional[str] = Field(default=None, env="HF_API_TOKEN")

    whisper_device: str = Field(default="cpu", env="WHISPER_DEVICE")
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")

    tts_profile: str = Field(default="offline", env="TTS_PROFILE")
    tts_voice: str = Field(default="default", env="TTS_VOICE")
    piper_model_path: Optional[str] = Field(default=None, env="PIPER_MODEL_PATH")
    piper_speaker: Optional[str] = Field(default=None, env="PIPER_SPEAKER")
    gtts_language: str = Field(default="tr", env="GTTS_LANGUAGE")

    # platform-bağımsız temp dizini
    audio_tmp_dir: str = Field(
        default_factory=lambda: os.path.join(gettempdir(), "tohum_audio")
    )
    audio_ttl_hours: int = Field(default=24)

    # ✅ parantez artık tam kapalı
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("tts_profile")
    @classmethod
    def _validate_tts_profile(cls, value: str) -> str:
        allowed = {"offline", "online"}
        if value not in allowed:
            raise ValueError(f"TTS_PROFILE must be one of {', '.join(sorted(allowed))}")
        return value


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
