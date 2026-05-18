from __future__ import annotations

from lofin.agents.base import Agent, next_message
from lofin.agents.messages import AgentMessage
from lofin.db.models import MarketSnapshot
from lofin.services.market_data import MarketDataService


class MarketDataAgent(Agent):
    name = "market_data"

    def __init__(self, session, service: MarketDataService | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(session)
        self.service = service or MarketDataService()

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        enriched: list[str] = []
        for symbol in message.payload.get("symbols", []):
            try:
                snap = await self.service.snapshot(symbol)
                self.session.add(MarketSnapshot(**snap))
                enriched.append(symbol)
            except Exception as exc:
                self.log.warning("market_data_failed", symbol=symbol, error=str(exc))
        await self.session.commit()
        return [next_message("market_data", "ranking", "market.updated", {"symbols": enriched}, message.correlation_id)]
