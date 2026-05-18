from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from lofin.core.time import utc_now


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RawPost(Base, TimestampMixin):
    __tablename__ = "raw_posts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_id: Mapped[str] = mapped_column(String(256), index=True)
    url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(256))
    title: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="en")
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    high_signal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Ticker(Base, TimestampMixin):
    __tablename__ = "tickers"
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(256))
    asset_type: Mapped[str] = mapped_column(String(16), index=True)  # stock or etf
    sector: Mapped[str | None] = mapped_column(String(128))
    market_cap: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ExtractedSignal(Base, TimestampMixin):
    __tablename__ = "extracted_signals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    raw_post_id: Mapped[str] = mapped_column(ForeignKey("raw_posts.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    asset_type: Mapped[str] = mapped_column(String(16), index=True)
    stance: Mapped[str] = mapped_column(String(16), default="uncertain")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    catalysts: Mapped[list[str]] = mapped_column(JSON, default=list)
    entities: Mapped[list[str]] = mapped_column(JSON, default=list)
    claims: Mapped[list[str]] = mapped_column(JSON, default=list)
    uncertainty: Mapped[float] = mapped_column(Float, default=1.0)
    raw_post: Mapped[RawPost] = relationship()


class OptionsFlow(Base, TimestampMixin):
    __tablename__ = "options_flow"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    raw_post_id: Mapped[str | None] = mapped_column(ForeignKey("raw_posts.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    contract_type: Mapped[str] = mapped_column(String(8))
    strike: Mapped[float] = mapped_column(Float)
    expiry: Mapped[str] = mapped_column(String(32), index=True)
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    implied_volatility: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[int | None] = mapped_column(Integer)
    open_interest: Mapped[int | None] = mapped_column(Integer)


class SentimentHistory(Base, TimestampMixin):
    __tablename__ = "sentiment_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    raw_post_id: Mapped[str | None] = mapped_column(ForeignKey("raw_posts.id", ondelete="SET NULL"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    sentiment: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(128))
    rationale: Mapped[str | None] = mapped_column(Text)


class NarrativeCluster(Base, TimestampMixin):
    __tablename__ = "narrative_clusters"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(256), index=True)
    symbols: Mapped[list[str]] = mapped_column(JSON, default=list)
    theme: Mapped[str] = mapped_column(String(128), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_trend: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    velocity: Mapped[float] = mapped_column(Float, default=0.0)
    persistence_score: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class DailySummary(Base, TimestampMixin):
    __tablename__ = "daily_summaries"
    __table_args__ = (UniqueConstraint("summary_date", "scope", "symbol", name="uq_daily_summary_scope"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    summary_date: Mapped[str] = mapped_column(String(10), index=True)
    scope: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str | None] = mapped_column(String(16), index=True)
    content: Mapped[str] = mapped_column(Text)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list)
    catalysts: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class MarketSnapshot(Base, TimestampMixin):
    __tablename__ = "market_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    price: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    relative_volume: Mapped[float | None] = mapped_column(Float)
    market_cap: Mapped[float | None] = mapped_column(Float)
    implied_volatility: Mapped[float | None] = mapped_column(Float)
    earnings_date: Mapped[str | None] = mapped_column(String(32))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AgentLog(Base, TimestampMixin):
    __tablename__ = "agent_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    message_type: Mapped[str] = mapped_column(String(64), index=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
