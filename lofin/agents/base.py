from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from lofin.agents.messages import AgentMessage, AgentName
from lofin.db.models import AgentLog

logger = structlog.get_logger(__name__)


class Agent(ABC):
    name: AgentName

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.log = logger.bind(agent=self.name)

    @abstractmethod
    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        """Process a structured JSON agent message and emit zero or more follow-up messages."""

    async def run(self, message: AgentMessage) -> list[AgentMessage]:
        started = time.perf_counter()
        try:
            responses = await self.handle(message)
            await self._record("ok", message, (time.perf_counter() - started) * 1000)
            return responses
        except Exception as exc:
            await self._record("error", message, (time.perf_counter() - started) * 1000, str(exc))
            self.log.exception("agent_failed", message_type=message.message_type)
            raise

    async def _record(self, status: str, message: AgentMessage, latency_ms: float, error: str | None = None) -> None:
        self.session.add(
            AgentLog(
                agent_name=self.name,
                status=status,
                message_type=message.message_type,
                latency_ms=latency_ms,
                error=error,
                payload=message.model_dump(mode="json"),
            )
        )
        await self.session.commit()


def next_message(sender: AgentName, recipient: AgentName, message_type: str, payload: dict[str, Any], correlation_id: str) -> AgentMessage:
    return AgentMessage(sender=sender, recipient=recipient, message_type=message_type, payload=payload, correlation_id=correlation_id)
