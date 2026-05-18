from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from lofin.core.time import utc_now

AgentName = Literal[
    "ingestion", "extraction", "market_data", "sentiment", "narrative_memory", "ranking", "summarization", "risk", "cleanup"
]


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    sender: AgentName
    recipient: AgentName
    message_type: str
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any]
