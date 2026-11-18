from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from src.dispenser_iot.adapters.persistence.mappers import apply_to_model, to_domain
from src.dispenser_iot.adapters.persistence.models import DispenseRecordModel, DispenserModel
from src.dispenser_iot.application.ports import DispenserRepository
from src.dispenser_iot.domain.aggregates import DispenserIoT
from src.dispenser_iot.domain.value_objects import DispenserId, SerialNumber
from src.shared_kernel.domain import ConcurrencyConflict


class SqlDispenserRepository(DispenserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, dispenser_id: DispenserId) -> DispenserIoT | None:
        model = await self._session.get(DispenserModel, dispenser_id.value)
        return await self._hydrate(model)

    async def get_by_serial(self, serial: SerialNumber) -> DispenserIoT | None:
        stmt = select(DispenserModel).where(DispenserModel.serial_number == serial.value)
        model = (await self._session.scalars(stmt)).one_or_none()
        return await self._hydrate(model)

    async def save(self, dispenser: DispenserIoT) -> None:
        model = await self._session.get(
            DispenserModel, dispenser.id.value,
            populate_existing=True, with_for_update=True,
        )
        if model is None:
            model = DispenserModel(id=dispenser.id.value)
            self._session.add(model)
        elif model.version != dispenser.version:
            raise ConcurrencyConflict(
                f"Dispensador modificado por otro proceso "
                f"(esperada v{dispenser.version}, actual v{model.version})"
            )
        apply_to_model(dispenser, model)
        try:
            await self._session.flush()  # primero el padre (FK de dispense_records)
        except StaleDataError as e:
            raise ConcurrencyConflict("El dispensador fue modificado por otro proceso") from e
        dispenser.version = model.version

        pending = dispenser.pull_new_records()
        if pending:
            stmt = pg_insert(DispenseRecordModel).values([
                dict(
                    id=r.id.value, event_id=r.event_id, dispenser_id=dispenser.id.value,
                    slot=r.slot.value, scheduled_at=r.scheduled_at, dispensed_at=r.dispensed_at,
                    outcome=r.outcome.value, origin=r.origin.value,
                ) for r in pending
            ]).on_conflict_do_nothing(index_elements=["event_id"])  # red de seguridad
            await self._session.execute(stmt)

    async def _hydrate(self, model: DispenserModel | None) -> DispenserIoT | None:
        if model is None:
            return None
        stmt = (
            select(DispenseRecordModel)
            .where(DispenseRecordModel.dispenser_id == model.id)
            .order_by(DispenseRecordModel.scheduled_at.desc())
            .limit(DispenserIoT.LOG_WINDOW)
        )
        records = list((await self._session.scalars(stmt)).all())
        return to_domain(model, records)