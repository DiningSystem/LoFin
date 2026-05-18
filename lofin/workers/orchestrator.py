from __future__ import annotations

import asyncio
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from lofin.agents import (
    CleanupAgent,
    ExtractionAgent,
    IngestionAgent,
    MarketDataAgent,
    NarrativeMemoryAgent,
    RankingAgent,
    RiskAgent,
    SentimentAgent,
    SummarizationAgent,
)
from lofin.agents.base import Agent
from lofin.agents.messages import AgentMessage, AgentName

AgentFactory = Callable[[AsyncSession], Agent]


class AgentOrchestrator:
    """Lightweight asyncio message bus for structured agent-to-agent JSON messages."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self.factories: dict[AgentName, AgentFactory] = {
            "ingestion": IngestionAgent,
            "extraction": ExtractionAgent,
            "market_data": MarketDataAgent,
            "sentiment": SentimentAgent,
            "narrative_memory": NarrativeMemoryAgent,
            "ranking": RankingAgent,
            "summarization": SummarizationAgent,
            "risk": RiskAgent,
            "cleanup": CleanupAgent,
        }

    async def publish(self, message: AgentMessage) -> None:
        await self.queue.put(message)

    async def drain(self, max_messages: int = 100) -> list[AgentMessage]:
        processed: list[AgentMessage] = []
        count = 0
        while count < max_messages and not self.queue.empty():
            message = await self.queue.get()
            agent = self.factories[message.recipient](self.session)
            responses = await agent.run(message)
            processed.append(message)
            for response in responses:
                await self.publish(response)
            count += 1
        return processed
