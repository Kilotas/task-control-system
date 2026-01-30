from functools import lru_cache
from typing import Literal, List

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Production Control API"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True


    database_url: PostgresDsn
    database_pool_size: int = 20

    # --- API ---
    api_v1_prefix: str = "/api/v1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False

    cors_origins: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_postgres_dsn(cls, v: PostgresDsn) -> PostgresDsn:
        if v.scheme not in ("postgres", "postgresql", "postgresql+asyncpg"):
            raise ValueError("DATABASE_URL must be a PostgreSQL DSN.")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
