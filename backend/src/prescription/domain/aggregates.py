from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.prescription.domain.events import (
    PrescriptionActivated, PrescriptionCompleted, PrescriptionItemChanged, PrescriptionSuspended,
)
from src.prescription.domain.value_objects import (
    Dosage, DoseSchedule, Medication, PatientId, PrescriptionId, PrescriptionItemId,
    PrescriptionStatus as S, TreatmentPeriod,
)
from src.shared_kernel.domain import AggregateRoot, InvalidStateTransition, InvariantViolation

_ALLOWED: dict[S, set[S]] = {
    S.DRAFT: {S.ACTIVE},
    S.ACTIVE: {S.SUSPENDED, S.COMPLETED},
    S.SUSPENDED: {S.ACTIVE, S.COMPLETED},
    S.COMPLETED: set(),
}


@dataclass(slots=True)
class PrescriptionItem:
    id: PrescriptionItemId
    medication: Medication
    dosage: Dosage
    schedule: DoseSchedule
    instructions: str | None = None


class Prescription(AggregateRoot):
    def __init__(
        self, *, id: PrescriptionId, patient_id: PatientId, validity: TreatmentPeriod,
        status: S = S.DRAFT, items: Iterable[PrescriptionItem] = (), version: int = 0,
    ) -> None:
        super().__init__()
        self.id = id
        self.patient_id = patient_id
        self.validity = validity
        self.status = status
        self._items: list[PrescriptionItem] = list(items)
        self.version = version

    # ---- fábrica (nuevo) · el constructor se usa también para rehidratar ----
    @classmethod
    def draft(cls, patient_id: PatientId, validity: TreatmentPeriod) -> Prescription:
        return cls(id=PrescriptionId.new(), patient_id=patient_id, validity=validity)

    @property
    def items(self) -> tuple[PrescriptionItem, ...]:
        return tuple(self._items)

    # ---- ítems ----
    def add_item(
        self, medication: Medication, dosage: Dosage, schedule: DoseSchedule,
        instructions: str | None = None,
    ) -> PrescriptionItemId:
        self._ensure_editable()
        for it in self._items:
            same_drug = it.medication.name.casefold() == medication.name.casefold()
            if same_drug and it.schedule.overlaps(schedule):
                raise InvariantViolation(
                    f"Horarios solapados para el medicamento '{medication.name}'"
                )
        item = PrescriptionItem(PrescriptionItemId.new(), medication, dosage, schedule, instructions)
        self._items.append(item)
        self._notify_item_change(item.id, "ADDED")
        return item.id

    def remove_item(self, item_id: PrescriptionItemId) -> None:
        self._ensure_editable()
        item = next((i for i in self._items if i.id == item_id), None)
        if item is None:
            raise InvariantViolation("El ítem no pertenece a esta receta")
        if self.status is S.ACTIVE and len(self._items) == 1:
            raise InvariantViolation("Una receta activa debe conservar al menos un ítem")
        self._items.remove(item)
        self._notify_item_change(item_id, "REMOVED")

    # ---- ciclo de vida ----
    def activate(self) -> None:
        if not self._items:
            raise InvariantViolation("No se puede activar una receta sin ítems")
        self._transition(S.ACTIVE)
        self._record(PrescriptionActivated(prescription_id=self.id, patient_id=self.patient_id))

    def suspend(self) -> None:
        self._transition(S.SUSPENDED)
        self._record(PrescriptionSuspended(prescription_id=self.id, patient_id=self.patient_id))

    def complete(self) -> None:
        self._transition(S.COMPLETED)
        self._record(PrescriptionCompleted(prescription_id=self.id, patient_id=self.patient_id))

    # ---- internos ----
    def _transition(self, target: S) -> None:
        if target not in _ALLOWED[self.status]:
            raise InvalidStateTransition(f"Transición inválida: {self.status} → {target}")
        self.status = target

    def _ensure_editable(self) -> None:
        if self.status not in (S.DRAFT, S.ACTIVE):
            raise InvalidStateTransition(f"Receta no editable en estado {self.status}")

    def _notify_item_change(self, item_id: PrescriptionItemId, change: str) -> None:
        if self.status is S.ACTIVE:  # solo importa al dispositivo si la receta está activa
            self._record(PrescriptionItemChanged(
                prescription_id=self.id, patient_id=self.patient_id,
                item_id=item_id, change=change,  # type: ignore[arg-type]
            ))