from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.dispenser_iot.domain.value_objects import (
    DispenseOrigin, DispenserId, PatientId, PrescriptionItemId, SlotNumber,
)
from src.shared_kernel.domain import DomainEvent


@dataclass(frozen=True, kw_only=True)
class DispenserEvent(DomainEvent):
    dispenser_id: DispenserId
    owner_id: PatientId


@dataclass(frozen=True, kw_only=True)
class DispenserCameOnline(DispenserEvent): ...


@dataclass(frozen=True, kw_only=True)
class DispenserWentOffline(DispenserEvent): ...


@dataclass(frozen=True, kw_only=True)
class PowerOutageDetected(DispenserEvent):
    battery_pct: int


@dataclass(frozen=True, kw_only=True)
class PowerRestored(DispenserEvent):
    battery_pct: int


@dataclass(frozen=True, kw_only=True)
class DispenseRequested(DispenserEvent):  # nuevo: lo publica el adaptador en commands/dispense
    slot: SlotNumber


@dataclass(frozen=True, kw_only=True)
class DoseDispensed(DispenserEvent):
    slot: SlotNumber
    prescription_item_id: PrescriptionItemId | None
    scheduled_at: datetime
    dispensed_at: datetime | None
    origin: DispenseOrigin


@dataclass(frozen=True, kw_only=True)
class DoseMissed(DispenserEvent):
    slot: SlotNumber
    scheduled_at: datetime


@dataclass(frozen=True, kw_only=True)
class StockLow(DispenserEvent):
    slot: SlotNumber
    remaining: int