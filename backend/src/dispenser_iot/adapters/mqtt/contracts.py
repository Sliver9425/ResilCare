from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from src.dispenser_iot.domain.value_objects import DispenseOutcome, PowerSource

P = TypeVar("P", bound=BaseModel)


class Envelope(BaseModel, Generic[P]):
    event_id: UUID                       # clave de idempotencia
    dispenser_id: UUID
    occurred_at: AwareDatetime           # fijado por el DISPOSITIVO
    schema_version: Literal[1] = 1
    payload: P


class ConnectivityPayload(BaseModel):
    status: Literal["online", "offline"]


class PowerPayload(BaseModel):
    source: PowerSource
    battery_pct: int = Field(ge=0, le=100)


class DispensedPayload(BaseModel):
    slot: int = Field(ge=1)
    scheduled_at: AwareDatetime
    outcome: DispenseOutcome


class OutagePayload(BaseModel):
    battery_pct: int = Field(ge=0, le=100)


class OfflineLogEntry(BaseModel):
    event_id: UUID                       # idempotencia por entrada
    slot: int = Field(ge=1)
    scheduled_at: AwareDatetime
    dispensed_at: AwareDatetime | None
    outcome: DispenseOutcome


class OfflineLogPayload(BaseModel):
    entries: list[OfflineLogEntry] = Field(min_length=1, max_length=500)