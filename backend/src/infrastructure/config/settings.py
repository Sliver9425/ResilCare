from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["dev", "test", "prod"] = "dev"

    # Supabase (usar el pooler: puerto 6543, modo transaction)
    database_url: str  # postgresql+asyncpg://user:pass@host:6543/postgres
    direct_database_url: str | None = None   # migraciones (Alembic)
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_echo: bool = False

    # Debe coincidir con el modelo de embeddings elegido (ver decisión D3)
    embedding_dim: int = 384

    @field_validator("database_url")
    @classmethod
    def _require_asyncpg(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL debe usar el driver postgresql+asyncpg://")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()