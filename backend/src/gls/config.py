"""Application configuration with environment variable support."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="GLS_",
    )

    # Application
    app_name: str = "Gospel Language Study"
    debug: bool = False

    # Paths - relative to project root
    data_dir: Path = Path("../data")
    database_url: str = "sqlite:///../data/gls.db"

    # AI Provider
    ai_provider: Literal["openai", "anthropic", "mock"] = "mock"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # AI Model Selection (for different use cases)
    ai_model_expensive: str = "gpt-4o"  # For onboarding, complex analysis
    ai_model_cheap: str = "gpt-4o-mini"  # For daily use

    # CORS - for local development
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def talks_dir(self) -> Path:
        """Directory containing talk data."""
        return self.data_dir / "talks"

    @property
    def db_path(self) -> Path:
        """Path to SQLite database file."""
        return self.data_dir / "gls.db"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
