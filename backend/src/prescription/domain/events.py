from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.prescription.domain.value_objects import PatientId, PrescriptionId, PrescriptionItemId
from src.shared_kernel.domain import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PrescriptionEvent(DomainEvent):
    prescription_id: PrescriptionId
    patient_id: PatientId


@dataclass(frozen=True, kw_only=True)
class PrescriptionActivated(PrescriptionEvent): ...


@dataclass(frozen=True, kw_only=True)
class PrescriptionSuspended(PrescriptionEvent): ...


@dataclass(frozen=True, kw_only=True)
class PrescriptionCompleted(PrescriptionEvent): ...


@dataclass(frozen=True, kw_only=True)
class PrescriptionItemChanged(PrescriptionEvent):
    item_id: PrescriptionItemId
    change: Literal["ADDED", "REMOVED"]