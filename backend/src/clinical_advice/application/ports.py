from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    external_id: str
    source: str
    title: str
    content: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk: KnowledgeChunk
    score: float  # similitud coseno 0..1


class EmbeddingPort(ABC):
    @abstractmethod
    async def embed_query(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class KnowledgeRepository(ABC):
    @abstractmethod
    async def upsert_many(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> int: ...

    @abstractmethod
    async def similarity_search(
        self, embedding: list[float], k: int = 4, min_score: float = 0.0
    ) -> list[ScoredChunk]: ...