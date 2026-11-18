from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from enum import IntEnum, StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.shared_kernel.domain import EntityId, InvariantViolation
from src.shared_kernel.identifiers import PatientId, PrescriptionItemId  # re-export

__all__ = [
    "PatientId", "PrescriptionItemId", "PrescriptionId", "Weekday", "DosageForm",
    "PrescriptionStatus", "Medication", "Dosage", "DoseSchedule", "TreatmentPeriod",
]

MAX_UNITS_PER_INTAKE = 10


@dataclass(frozen=True, slots=True)
class PrescriptionId(EntityId): ...


class Weekday(IntEnum):  # ISO-8601
    MON = 1; TUE = 2; WED = 3; THU = 4; FRI = 5; SAT = 6; SUN = 7


class DosageForm(StrEnum):
    TABLET = "TABLET"; CAPSULE = "CAPSULE"; SACHET = "SACHET"


class PrescriptionStatus(StrEnum):
    DRAFT = "DRAFT"; ACTIVE = "ACTIVE"; SUSPENDED = "SUSPENDED"; COMPLETED = "COMPLETED"


@dataclass(frozen=True, slots=True)
class Medication:
    name: str
    active_ingredient: str | None = None
    concentration: str | None = None

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise InvariantViolation("El nombre del medicamento no puede estar vacío")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True, slots=True)
class Dosage:
    units_per_intake: int
    form: DosageForm

    def __post_init__(self) -> None:
        if not 0 < self.units_per_intake <= MAX_UNITS_PER_INTAKE:
            raise InvariantViolation(
                f"units_per_intake debe estar entre 1 y {MAX_UNITS_PER_INTAKE}"
            )


@dataclass(frozen=True, slots=True)
class DoseSchedule:
    times_of_day: tuple[time, ...]
    days_of_week: frozenset[Weekday]
    timezone: str = "America/Guayaquil"

    def __post_init__(self) -> None:
        if not self.times_of_day:
            raise InvariantViolation("Se requiere al menos una hora de toma")
        if len(set(self.times_of_day)) != len(self.times_of_day):
            raise InvariantViolation("Horas de toma duplicadas")
        if not self.days_of_week:
            raise InvariantViolation("Se requiere al menos un día de la semana")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as e:
            raise InvariantViolation(f"Zona horaria inválida: {self.timezone}") from e
        object.__setattr__(self, "times_of_day", tuple(sorted(self.times_of_day)))

    def overlaps(self, other: DoseSchedule) -> bool:
        return bool(self.days_of_week & other.days_of_week) and bool(
            set(self.times_of_day) & set(other.times_of_day)
        )


@dataclass(frozen=True, slots=True)
class TreatmentPeriod:
    start_date: date
    end_date: date | None = None  # None = tratamiento crónico

    def __post_init__(self) -> None:
        if self.end_date is not None and self.end_date < self.start_date:
            raise InvariantViolation("end_date debe ser >= start_date")