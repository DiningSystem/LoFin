from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from lofin.agents.messages import AgentMessage
from lofin.core.config import get_settings
from lofin.core.logging import configure_logging
from lofin.db.init_db import init_db
from lofin.db.session import SessionLocal
from lofin.workers.orchestrator import AgentOrchestrator


async def run_cycle() -> None:
    async with SessionLocal() as session:
        orchestrator = AgentOrchestrator(session)
        await orchestrator.publish(AgentMessage(sender="ingestion", recipient="ingestion", message_type="scheduled.ingestion", payload={"source": "all", "limit": 50}))
        await orchestrator.drain(max_messages=250)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(run_cycle()), "interval", minutes=30, id="ingestion-cycle")
    scheduler.start()
    await run_cycle()
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
