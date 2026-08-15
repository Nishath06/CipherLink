"""
CipherLink — Application Configuration

Centralized settings via Pydantic BaseSettings.
All secrets loaded from environment variables.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──────────────────────────────
    APP_NAME: str = "CipherLink"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # ── Database ─────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://cipherlink:cipherlink_secret@localhost:5432/cipherlink"
    DATABASE_ECHO: bool = False

    # ── Redis ────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT / Auth ───────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_ME_TO_A_64_CHAR_RANDOM_HEX_STRING"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Encryption ───────────────────────────────
    ENCRYPTION_MASTER_KEY: str = "CHANGE_ME_TO_A_64_CHAR_HEX_MASTER_KEY"

    # ── AWS S3 ───────────────────────────────────
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "cipherlink-storage"

    # ── Azure Blob ───────────────────────────────
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_STORAGE_CONTAINER: str = "cipherlink"

    # ── Local Storage ────────────────────────────
    LOCAL_STORAGE_PATH: str = "./app_storage"

    # ── CORS ─────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost"]

    # ── Rate Limiting ────────────────────────────
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_API: str = "100/minute"
    RATE_LIMIT_ENCRYPTION: str = "50/minute"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
