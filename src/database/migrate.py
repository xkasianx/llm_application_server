import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from database.models import Base


async def migrate_tables() -> None:
    print("Starting to migrate")
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("Done migrating")


asyncio.run(migrate_tables())
