import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.base import Base, TimestampMixin

EMBEDDING_DIM = get_settings().embedding_dim


class KnowledgeChunkModel(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="source_external"),  # siembra idempotente
        Index(
            "ix_knowledge_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(128))        # p.ej. "seed_medicamentos.json"
    external_id: Mapped[str] = mapped_column(String(128))   # id dentro del JSON semilla
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))