"""
Configuration module for OpenRecords backend.
Loads environment variables and provides settings.
"""
import os
from pathlib import Path
from pydantic import Field
from pydantic.aliases import AliasChoices
from pydantic_settings import BaseSettings
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    openrecords_secret_key: str = "dev-secret-key-change-in-production"
    openrecords_env: str = "dev"
    openrecords_db_path: str = str(BASE_DIR / "data" / "main.db")
    openrecords_cache_db: str = Field(
        default=str(BASE_DIR / "data" / "cache.db"),
        validation_alias=AliasChoices("OPENRECORDS_CACHE_DB", "OPENRECORDS_CACHE_PATH"),
    )
    vector_db_path: str = str(BASE_DIR / "data" / "vectors")

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expiration_days: int = 30

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Cache settings
    cache_ttl_seconds: int = 86400  # 24 hours

    # Storage
    openrecords_vault_path: str = str(BASE_DIR / "vault" / "encrypted_files")

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def is_dev(self) -> bool:
        """Check if running in development mode."""
        return self.openrecords_env.lower() == "dev"

    @property
    def is_prod(self) -> bool:
        """Check if running in production mode."""
        return self.openrecords_env.lower() == "prod"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def database_path(self) -> Path:
        """Get the database path as a Path object."""
        db_path = Path(self.openrecords_db_path)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
        return db_path

    @property
    def cache_db_path(self) -> Path:
        """Get the cache database path as a Path object."""
        db_path = Path(self.openrecords_cache_db)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
        return db_path

    @property
    def vault_path(self) -> Path:
        """Get the vault path as a Path object."""
        vault_path = Path(self.openrecords_vault_path)
        if not vault_path.is_absolute():
            vault_path = BASE_DIR / vault_path
        return vault_path


# Global settings instance
settings = Settings()
