from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.dispenser_iot.domain.aggregates import DispenserIoT
    from src.dispenser_iot.domain.value_objects import DispenserId, SerialNumber


class DispenserRepository(ABC):
    @abstractmethod
    async def get(self, dispenser_id: DispenserId) -> DispenserIoT | None: ...

    @abstractmethod
    async def get_by_serial(self, serial: SerialNumber) -> DispenserIoT | None: ...

    @abstractmethod
    async def save(self, dispenser: DispenserIoT) -> None: ...


class EventInbox(ABC):
    """Idempotencia: True si el evento es nuevo (y queda registrado), False si es duplicado."""
    @abstractmethod
    async def register_if_new(self, event_id: UUID, topic: str) -> bool: ...