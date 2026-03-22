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
        # Migrations: add columns if they don't exist yet
        for stmt in [
            "ALTER TABLE agents ADD COLUMN status VARCHAR NOT NULL DEFAULT 'alive'",
            "ALTER TABLE agents ADD COLUMN last_action VARCHAR",
            "ALTER TABLE agents ADD COLUMN last_action_params JSON DEFAULT '{}'",
            "ALTER TABLE agents ADD COLUMN position_history JSON DEFAULT '[]'",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column already exists
