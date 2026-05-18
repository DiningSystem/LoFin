from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select

from lofin.agents.base import Agent, next_message
from lofin.agents.messages import AgentMessage
from lofin.core.time import utc_now
from lofin.db.models import ExtractedSignal, NarrativeCluster, RawPost, SentimentHistory
from lofin.llm.ollama import OllamaClient
from lofin.memory.vector_store import VectorMemory


class NarrativeMemoryAgent(Agent):
    name = "narrative_memory"

    def __init__(self, session, llm: OllamaClient | None = None, memory: VectorMemory | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(session)
        self.llm = llm or OllamaClient()
        self.memory = memory or VectorMemory()

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        post_ids = message.payload.get("post_ids", [])
        posts = (await self.session.execute(select(RawPost).where(RawPost.id.in_(post_ids)))).scalars().all()
        for post in posts:
            signals = (await self.session.execute(select(ExtractedSignal).where(ExtractedSignal.raw_post_id == post.id))).scalars().all()
            symbols = sorted({s.symbol for s in signals})
            text = f"{post.title}\n{post.body}"
            vector = await self._embed(text)
            if vector:
                await self.memory.upsert_discussion(post.id, vector, {"source": post.source, "posted_at": post.posted_at, "symbols": symbols, "engagement_score": post.engagement_score, "text": text[:1500]})
        await self._refresh_clusters()
        return [next_message("narrative_memory", "summarization", "memory.updated", {"symbols": message.payload.get("symbols", [])}, message.correlation_id)]

    async def _embed(self, text: str) -> list[float]:
        try:
            return await self.llm.embed(text[:4000])
        except Exception:
            return []

    async def _refresh_clusters(self) -> None:
        since = utc_now() - timedelta(days=30)
        signals = (await self.session.execute(select(ExtractedSignal).where(ExtractedSignal.created_at >= since))).scalars().all()
        themes: dict[str, list[ExtractedSignal]] = defaultdict(list)
        for signal in signals:
            key = (signal.catalysts[0] if signal.catalysts else signal.symbol).lower()[:128]
            themes[key].append(signal)
        for theme, rows in themes.items():
            symbols = sorted({row.symbol for row in rows})
            title = f"{theme.title()} narrative"
            existing = (await self.session.execute(select(NarrativeCluster).where(NarrativeCluster.theme == theme))).scalars().first()
            sentiment_rows = (await self.session.execute(select(SentimentHistory).where(SentimentHistory.symbol.in_(symbols), SentimentHistory.created_at >= since))).scalars().all() if symbols else []
            avg_sentiment = sum(r.score for r in sentiment_rows) / len(sentiment_rows) if sentiment_rows else 0
            first_seen = min(row.created_at for row in rows)
            last_seen = max(row.created_at for row in rows)
            days = max((last_seen - first_seen).days + 1, 1)
            cluster = existing or NarrativeCluster(title=title, theme=theme, first_seen_at=first_seen, last_seen_at=last_seen)
            cluster.title = title
            cluster.symbols = symbols
            cluster.summary = f"Recurring discussion around {theme} across {', '.join(symbols[:8])}."
            cluster.first_seen_at = min(cluster.first_seen_at, first_seen) if existing else first_seen
            cluster.last_seen_at = last_seen
            cluster.mention_count = len(rows)
            cluster.velocity = len(rows) / days
            cluster.persistence_score = min(days / 30, 1.0) * min(len(rows) / 25, 1.0)
            cluster.sentiment_trend = {"30d_average": avg_sentiment, "sample_size": len(sentiment_rows)}
            self.session.add(cluster)
        await self.session.commit()
