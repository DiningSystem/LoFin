from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from lofin.agents.base import Agent
from lofin.agents.messages import AgentMessage
from lofin.db.models import DailySummary, NarrativeCluster
from lofin.llm.ollama import OllamaClient
from lofin.llm.prompts import SUMMARY_PROMPT


class SummarizationAgent(Agent):
    name = "summarization"

    def __init__(self, session, llm: OllamaClient | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(session)
        self.llm = llm or OllamaClient()

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        clusters = (await self.session.execute(select(NarrativeCluster).order_by(NarrativeCluster.velocity.desc()).limit(20))).scalars().all()
        context = "\n".join(f"{c.title}: symbols={c.symbols}, velocity={c.velocity:.2f}, trend={c.sentiment_trend}" for c in clusters)
        summary = await self._summarize(context)
        self.session.add(
            DailySummary(
                summary_date=datetime.now(tz=UTC).date().isoformat(),
                scope="market",
                symbol=None,
                content=summary["content"],
                risks=summary["risks"],
                catalysts=summary["catalysts"],
                confidence=summary["confidence"],
            )
        )
        await self.session.commit()
        return []

    async def _summarize(self, context: str) -> dict[str, object]:
        try:
            data = await self.llm.generate_json(SUMMARY_PROMPT.format(context=context[:7000]))
            return {"content": data.get("content", ""), "risks": data.get("risks", []), "catalysts": data.get("catalysts", []), "confidence": float(data.get("confidence", 0.4))}
        except Exception:
            return {"content": context[:1200] or "No narrative data available yet.", "risks": ["LLM unavailable; fallback summary used"], "catalysts": [], "confidence": 0.2}
