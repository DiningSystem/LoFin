from __future__ import annotations

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    source: str = Field(default="all", pattern="^(all|reddit|rss)$")
    subreddits: list[str] | None = None
    limit: int = Field(default=25, ge=1, le=200)


class CleanupRequest(BaseModel):
    retention_days: int | None = Field(default=None, ge=1, le=3650)


class TopSymbol(BaseModel):
    symbol: str
    mentions: int
    confidence: float
