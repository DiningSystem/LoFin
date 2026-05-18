from __future__ import annotations

from sqlalchemy import select

from lofin.agents.base import Agent, next_message
from lofin.agents.messages import AgentMessage
from lofin.db.models import ExtractedSignal, RawPost
from lofin.services.analytics import mention_velocity


class RankingAgent(Agent):
    name = "ranking"

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        ranked: list[dict[str, float | str]] = []
        for symbol in message.payload.get("symbols", []):
            velocity = await mention_velocity(self.session, symbol)
            count = len((await self.session.execute(select(ExtractedSignal).where(ExtractedSignal.symbol == symbol))).scalars().all())
            score = min(1.0, 0.45 * min(velocity / 3, 1) + 0.35 * min(count / 20, 1) + 0.2)
            ranked.append({"symbol": symbol, "score": score, "velocity": velocity})
            if score >= 0.75:
                posts = (await self.session.execute(select(RawPost).join(ExtractedSignal, ExtractedSignal.raw_post_id == RawPost.id).where(ExtractedSignal.symbol == symbol))).scalars().all()
                for post in posts[-20:]:
                    post.high_signal = True
        await self.session.commit()
        return [next_message("ranking", "risk", "ranking.updated", {"ranked": ranked}, message.correlation_id)]
