from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from lofin.agents.base import Agent, next_message
from lofin.agents.messages import AgentMessage
from lofin.connectors.reddit import RedditConnector
from lofin.connectors.rss import RSSConnector
from lofin.db.models import RawPost


class IngestionAgent(Agent):
    name = "ingestion"

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        source = message.payload.get("source", "all")
        posts: list[dict[str, object]] = []
        if source in {"all", "reddit"}:
            posts.extend(await RedditConnector().fetch(message.payload.get("subreddits"), int(message.payload.get("limit", 50))))
        if source in {"all", "rss"}:
            posts.extend(await RSSConnector().fetch())
        inserted: list[str] = []
        for post in posts:
            model = RawPost(**post)  # type: ignore[arg-type]
            self.session.add(model)
            try:
                await self.session.flush()
                inserted.append(model.id)
            except IntegrityError:
                await self.session.rollback()
        await self.session.commit()
        return [next_message("ingestion", "extraction", "posts.ingested", {"post_ids": inserted}, message.correlation_id)]
