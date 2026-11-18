import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.registry import Base

settings = get_settings()
URL = settings.direct_database_url or settings.database_url


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _main() -> None:
    engine = create_async_engine(URL, connect_args={"statement_cache_size": 0})
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


asyncio.run(_main())