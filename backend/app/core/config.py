# app/core/config.py
"""
Central configuration for FinSight AI.
All values are loaded from the .env file via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    Every attribute maps directly to a key in .env.
    """

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "FinSight AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-in-production-use-256-bit-random-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── PostgreSQL ────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+psycopg://finsight:finsight123@localhost:5432/finsight_db"
    )

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant ────────────────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "finsight_chunks"

    # ── Ollama / Llama 3 ──────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"

    # ── BGE Embeddings ────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
    EMBEDDING_DIMENSION: int = 768

    # ── File Storage ──────────────────────────────────────────────────────
    UPLOAD_DIR: str = "../uploads"
    MAX_UPLOAD_SIZE_MB: int = 100

    # ── Celery ────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Single shared instance — import this everywhere
settings = Settings()
