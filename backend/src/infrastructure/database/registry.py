# Importar aquí TODOS los modelos para que Alembic vea un único metadata.
from src.infrastructure.database.base import Base
from src.infrastructure.database.inbox import ProcessedEventModel  # noqa: F401
from src.identity_access.adapters.persistence.models import PatientModel  # noqa: F401
from src.prescription.adapters.persistence.models import (  # noqa: F401
    PrescriptionItemModel, PrescriptionModel,
)
from src.dispenser_iot.adapters.persistence.models import (  # noqa: F401
    CompartmentModel, DispenseRecordModel, DispenserModel,
)
from src.clinical_advice.adapters.persistence.models import KnowledgeChunkModel  # noqa: F401

__all__ = ["Base"]