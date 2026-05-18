from sqlalchemy.ext.asyncio import AsyncEngine

from lofin.db.models import Base
from lofin.db.session import engine


async def init_db(db_engine: AsyncEngine | None = None) -> None:
    db_engine = db_engine or engine
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
