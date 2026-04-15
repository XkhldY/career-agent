"""Application configuration from environment."""

from __future__ import annotations

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load from env / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = ""

    # Chroma
    chroma_host: str = ""
    chroma_port: int = 8000
    chroma_data_path: str = "data/chroma_db"

    # External search APIs
    serpapi_api_key: str = ""
    tavily_api_key: str = ""
    brave_search_api_key: str = ""

    # AWS (Bedrock)
    aws_region: str = "us-east-1"

    # JWT auth
    jwt_secret: str = secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 72

    @property
    def has_database(self) -> bool:
        return bool(self.database_url and self.database_url.strip())


settings = Settings()
