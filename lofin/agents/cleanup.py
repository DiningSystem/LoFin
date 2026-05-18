from __future__ import annotations

import gzip
import json
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select

from lofin.agents.base import Agent
from lofin.agents.messages import AgentMessage
from lofin.core.config import get_settings
from lofin.core.time import utc_now
from lofin.db.models import RawPost
from lofin.memory.vector_store import VectorMemory


class CleanupAgent(Agent):
    name = "cleanup"

    def __init__(self, session, memory: VectorMemory | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(session)
        self.settings = get_settings()
        self.memory = memory or VectorMemory()

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        retention_days = int(message.payload.get("retention_days", self.settings.retention_days))
        cutoff = utc_now() - timedelta(days=retention_days)
        low_score_cutoff = utc_now() - timedelta(days=self.settings.delete_low_score_after_days)
        await self._archive(cutoff)
        stmt = delete(RawPost).where(RawPost.posted_at < cutoff)
        if self.settings.keep_high_signal_forever:
            stmt = stmt.where(RawPost.high_signal.is_(False))
        await self.session.execute(stmt)
        await self.session.execute(delete(RawPost).where(RawPost.posted_at < low_score_cutoff, RawPost.engagement_score < self.settings.high_signal_score, RawPost.high_signal.is_(False)))
        await self.session.commit()
        try:
            await self.memory.delete_older_than(cutoff)
        except Exception as exc:
            self.log.warning("vector_cleanup_failed", error=str(exc))
        return []

    async def _archive(self, cutoff) -> None:  # type: ignore[no-untyped-def]
        archive_dir = Path("archives")
        archive_dir.mkdir(exist_ok=True)
        rows = (await self.session.execute(select(RawPost).where(RawPost.posted_at < cutoff, RawPost.high_signal.is_(True)))).scalars().all()
        if not rows:
            return
        path = archive_dir / f"high_signal_{cutoff.date().isoformat()}.jsonl.gz"
        with gzip.open(path, "at", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps({"id": row.id, "source": row.source, "title": row.title, "body": row.body, "posted_at": row.posted_at.isoformat(), "metadata": row.metadata_json}) + "\n")
