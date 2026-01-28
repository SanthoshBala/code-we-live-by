"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "CWLB API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/cwlb"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # API
    api_v1_prefix: str = "/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
