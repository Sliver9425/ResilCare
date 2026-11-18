from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConnectivityStatus(StrEnum):
    ONLINE = "ONLINE"; OFFLINE = "OFFLINE"


class PowerSource(StrEnum):
    MAINS = "MAINS"; BATTERY = "BATTERY"


class DispenseOutcome(StrEnum):
    DISPENSED = "DISPENSED"; MISSED = "MISSED"; JAMMED = "JAMMED"; REFUSED = "REFUSED"


class DispenseOrigin(StrEnum):
    ONLINE = "ONLINE"; OFFLINE_SYNCED = "OFFLINE_SYNCED"


class DispenserRegister(BaseModel):
    owner_id: UUID
    serial_number: str = Field(pattern=r"^[A-Z0-9\-]{6,64}$")
    slot_count: int = Field(default=7, ge=1, le=28)


class CompartmentLoad(BaseModel):
    prescription_item_id: UUID
    stock: int = Field(gt=0)
    low_threshold: int = Field(default=3, ge=0)


class CompartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slot: int
    prescription_item_id: UUID | None
    stock_remaining: int
    low_threshold: int


class DispenserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    serial_number: str
    connectivity_status: ConnectivityStatus
    last_seen_at: datetime | None
    power_source: PowerSource
    battery_pct: int
    compartments: list[CompartmentOut]


class DispenseRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slot: int
    scheduled_at: datetime
    dispensed_at: datetime | None
    outcome: DispenseOutcome
    origin: DispenseOrigin