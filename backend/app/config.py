"""Application configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Settings are loaded in this priority order (highest to lowest):
    1. Environment variables
    2. .env file (for local development)
    3. Default values

    For local development, copy .env.example to .env and fill in your values.
    For production, set environment variables directly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Application
    # =========================================================================
    app_name: str = "CWLB API"
    debug: bool = False

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/cwlb",
        description="PostgreSQL connection URL",
    )

    # =========================================================================
    # CORS
    # =========================================================================
    cors_origins: list[str] = ["http://localhost:3000"]

    # =========================================================================
    # API Settings
    # =========================================================================
    api_v1_prefix: str = "/api/v1"

    # =========================================================================
    # External API Keys
    # =========================================================================
    # GovInfo API (https://api.data.gov/signup/)
    # Required for: Public Law ingestion from GovInfo
    govinfo_api_key: str | None = Field(
        default=None,
        description="GovInfo API key from api.data.gov",
    )

    # Congress.gov API (https://api.congress.gov/sign-up/)
    # Required for: Legislator data, bill metadata, sponsor/cosponsor info
    congress_api_key: str | None = Field(
        default=None,
        description="Congress.gov API key from api.congress.gov",
    )

    # =========================================================================
    # Pipeline Cache
    # =========================================================================
    # GCS bucket for shared pipeline cache (optional).
    # When set, pipeline API fetches are cached in GCS so they persist
    # across Cloud Run instances and local rebuilds.
    gcs_cache_bucket: str | None = Field(
        default=None,
        description="GCS bucket name for pipeline cache (e.g., 'cwlb-pipeline-cache')",
    )


settings = Settings()
