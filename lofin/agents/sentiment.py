from __future__ import annotations

from sqlalchemy import select

from lofin.agents.base import Agent, next_message
from lofin.agents.messages import AgentMessage
from lofin.db.models import ExtractedSignal, RawPost, SentimentHistory
from lofin.llm.ollama import OllamaClient
from lofin.llm.prompts import SENTIMENT_PROMPT


class SentimentAgent(Agent):
    name = "sentiment"

    def __init__(self, session, llm: OllamaClient | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(session)
        self.llm = llm or OllamaClient()

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        post_ids = message.payload.get("post_ids", [])
        signals = (await self.session.execute(select(ExtractedSignal).where(ExtractedSignal.raw_post_id.in_(post_ids)))).scalars().all()
        for signal in signals:
            post = await self.session.get(RawPost, signal.raw_post_id)
            if not post:
                continue
            content = f"{post.title}\n{post.body}"
            result = await self._classify(signal.symbol, content)
            self.session.add(SentimentHistory(raw_post_id=post.id, symbol=signal.symbol, sentiment=result["sentiment"], score=result["score"], confidence=result["confidence"], model_name="ollama", rationale=result.get("rationale")))
            signal.stance = result["sentiment"] if result["sentiment"] in {"bullish", "bearish", "neutral", "uncertain"} else signal.stance
            signal.confidence = max(signal.confidence, result["confidence"])
        await self.session.commit()
        return [next_message("sentiment", "ranking", "sentiment.updated", {"symbols": message.payload.get("symbols", [])}, message.correlation_id)]

    async def _classify(self, symbol: str, content: str) -> dict[str, object]:
        try:
            data = await self.llm.generate_json(SENTIMENT_PROMPT.format(symbol=symbol, content=content[:5000]))
            return {"sentiment": data.get("sentiment", "uncertain"), "score": float(data.get("score", 0)), "confidence": float(data.get("confidence", 0.4)), "rationale": data.get("rationale")}
        except Exception:
            lower = content.lower()
            score = ("buy" in lower or "bull" in lower) - ("sell" in lower or "bear" in lower)
            return {"sentiment": "bullish" if score > 0 else "bearish" if score < 0 else "uncertain", "score": float(score), "confidence": 0.25, "rationale": "lexical fallback"}
