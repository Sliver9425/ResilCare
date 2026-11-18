from dataclasses import dataclass

from src.shared_kernel.domain import EntityId


@dataclass(frozen=True, slots=True)
class PatientId(EntityId):
    """Propiedad de identity_access; referenciado por ID en otros contextos."""


@dataclass(frozen=True, slots=True)
class PrescriptionItemId(EntityId):
    """Propiedad de prescription; referenciado por ID desde dispenser_iot."""