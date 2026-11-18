from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.prescription.domain.aggregates import Prescription
    from src.prescription.domain.value_objects import PatientId, PrescriptionId


class PrescriptionRepository(ABC):
    @abstractmethod
    async def get(self, prescription_id: PrescriptionId) -> Prescription | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: PatientId) -> list[Prescription]: ...

    @abstractmethod
    async def save(self, prescription: Prescription) -> None: ...  # insert-or-update del agregado