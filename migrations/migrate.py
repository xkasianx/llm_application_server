import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings
from src.database.models import Base

logger = logging.getLogger(__name__)


async def migrate_tables() -> None:
    logger.info("Starting to migrate")
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Done migrating")


asyncio.run(migrate_tables())
