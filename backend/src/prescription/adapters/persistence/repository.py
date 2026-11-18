from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from src.prescription.adapters.persistence.mappers import apply_to_model, to_domain
from src.prescription.adapters.persistence.models import PrescriptionModel
from src.prescription.application.ports import PrescriptionRepository
from src.prescription.domain.aggregates import Prescription
from src.prescription.domain.value_objects import PatientId, PrescriptionId
from src.shared_kernel.domain import ConcurrencyConflict


class SqlPrescriptionRepository(PrescriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, prescription_id: PrescriptionId) -> Prescription | None:
        model = await self._session.get(PrescriptionModel, prescription_id.value)
        return to_domain(model) if model else None

    async def list_by_patient(self, patient_id: PatientId) -> list[Prescription]:
        stmt = (
            select(PrescriptionModel)
            .where(PrescriptionModel.patient_id == patient_id.value)
            .order_by(PrescriptionModel.created_at.desc())
        )
        return [to_domain(m) for m in (await self._session.scalars(stmt)).all()]

    async def save(self, prescription: Prescription) -> None:
        # Lectura fresca + bloqueo de fila: la comparación de versión es explícita
        # y no depende del rowcount del driver.
        model = await self._session.get(
            PrescriptionModel, prescription.id.value,
            populate_existing=True, with_for_update=True,
        )
        if model is None:
            model = PrescriptionModel(id=prescription.id.value)
            self._session.add(model)
        elif model.version != prescription.version:
            raise ConcurrencyConflict(
                f"Receta modificada por otro proceso "
                f"(esperada v{prescription.version}, actual v{model.version})"
            )
        apply_to_model(prescription, model)
        try:
            await self._session.flush()
        except StaleDataError as e:
            raise ConcurrencyConflict("La receta fue modificada por otro proceso") from e
        prescription.version = model.version