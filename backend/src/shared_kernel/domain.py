from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Self
from uuid import UUID, uuid4


class DomainError(Exception): ...
class InvariantViolation(DomainError): ...
class InvalidStateTransition(DomainError): ...
class ConcurrencyConflict(DomainError): ...


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class EntityId:
    value: UUID

    @classmethod
    def new(cls) -> Self:
        return cls(uuid4())

    @classmethod
    def from_str(cls, raw: str) -> Self:
        return cls(UUID(raw))

    def __str__(self) -> str:
        return str(self.value)


class AggregateRoot:
    version: int = 0  # lo asigna el repositorio (bloqueo optimista)

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events