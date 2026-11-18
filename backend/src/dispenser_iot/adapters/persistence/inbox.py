from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.dispenser_iot.application.ports import EventInbox
from src.infrastructure.database.inbox import ProcessedEventModel


class SqlEventInbox(EventInbox):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register_if_new(self, event_id: UUID, topic: str) -> bool:
        stmt = (
            pg_insert(ProcessedEventModel)
            .values(event_id=event_id, topic=topic)
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(ProcessedEventModel.event_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None