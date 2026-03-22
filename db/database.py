from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

# timeout=15: wait up to 15 s for a lock instead of failing immediately
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"timeout": 15},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migration: add status column if it doesn't exist yet
        try:
            await conn.execute(text("ALTER TABLE agents ADD COLUMN status VARCHAR NOT NULL DEFAULT 'alive'"))
        except Exception:
            pass  # Column already exists
        # Migration: relationships table is created by create_all above (new installs).
        # No manual migration needed for existing DBs — create_all is idempotent for new tables.
