from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.shared_kernel.domain import EntityId, InvariantViolation
from src.shared_kernel.identifiers import PatientId, PrescriptionItemId

__all__ = [
    "PatientId", "PrescriptionItemId", "DispenserId", "DispenseRecordId", "SerialNumber",
    "SlotNumber", "StockLevel", "ConnectivityStatus", "ConnectivityState", "PowerSource",
    "PowerStatus", "DispenseOutcome", "DispenseOrigin", "MAX_SLOTS",
]

MAX_SLOTS = 28
_SERIAL_RE = re.compile(r"^[A-Z0-9\-]{6,64}$")


@dataclass(frozen=True, slots=True)
class DispenserId(EntityId): ...


@dataclass(frozen=True, slots=True)
class DispenseRecordId(EntityId): ...


class ConnectivityStatus(StrEnum):
    ONLINE = "ONLINE"; OFFLINE = "OFFLINE"


class PowerSource(StrEnum):
    MAINS = "MAINS"; BATTERY = "BATTERY"


class DispenseOutcome(StrEnum):
    DISPENSED = "DISPENSED"; MISSED = "MISSED"; JAMMED = "JAMMED"; REFUSED = "REFUSED"


class DispenseOrigin(StrEnum):
    ONLINE = "ONLINE"; OFFLINE_SYNCED = "OFFLINE_SYNCED"


@dataclass(frozen=True, slots=True)
class SerialNumber:
    value: str

    def __post_init__(self) -> None:
        if not _SERIAL_RE.match(self.value):
            raise InvariantViolation("Número de serie inválido (A-Z, 0-9, '-', 6 a 64 caracteres)")


@dataclass(frozen=True, slots=True)
class SlotNumber:
    value: int

    def __post_init__(self) -> None:
        if not 1 <= self.value <= MAX_SLOTS:
            raise InvariantViolation(f"El slot debe estar entre 1 y {MAX_SLOTS}")


@dataclass(frozen=True, slots=True)
class StockLevel:
    """`remaining` se expresa en DOSIS (una liberación = una dosis)."""
    remaining: int
    low_threshold: int = 3

    def __post_init__(self) -> None:
        if self.remaining < 0 or self.low_threshold < 0:
            raise InvariantViolation("El stock y el umbral no pueden ser negativos")

    @property
    def is_empty(self) -> bool:
        return self.remaining == 0

    @property
    def is_low(self) -> bool:
        return self.remaining <= self.low_threshold

    def consume(self, units: int = 1) -> StockLevel:
        # Tolerante: el dispositivo es la fuente de verdad; nunca se descarta un evento real.
        return StockLevel(max(0, self.remaining - units), self.low_threshold)

    def add(self, units: int) -> StockLevel:
        if units <= 0:
            raise InvariantViolation("La recarga debe ser > 0")
        return StockLevel(self.remaining + units, self.low_threshold)


@dataclass(frozen=True, slots=True)
class ConnectivityState:
    status: ConnectivityStatus
    last_seen: datetime | None = None


@dataclass(frozen=True, slots=True)
class PowerStatus:
    source: PowerSource
    battery_pct: int

    def __post_init__(self) -> None:
        if not 0 <= self.battery_pct <= 100:
            raise InvariantViolation("battery_pct debe estar entre 0 y 100")