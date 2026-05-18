from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lofin.core.time import utc_now
from lofin.db.models import ExtractedSignal, NarrativeCluster, SentimentHistory


async def top_symbols(session: AsyncSession, asset_type: str, days: int = 7, limit: int = 25) -> list[dict[str, Any]]:
    since = utc_now() - timedelta(days=days)
    stmt = (
        select(ExtractedSignal.symbol, func.count().label("mentions"), func.avg(ExtractedSignal.confidence).label("confidence"))
        .where(ExtractedSignal.asset_type == asset_type, ExtractedSignal.created_at >= since)
        .group_by(ExtractedSignal.symbol)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [{"symbol": row.symbol, "mentions": row.mentions, "confidence": float(row.confidence or 0)} for row in rows]


async def ticker_profile(session: AsyncSession, symbol: str, days: int = 30) -> dict[str, Any]:
    since = utc_now() - timedelta(days=days)
    signal_rows = (await session.execute(select(ExtractedSignal).where(ExtractedSignal.symbol == symbol.upper(), ExtractedSignal.created_at >= since))).scalars().all()
    sentiment_rows = (await session.execute(select(SentimentHistory).where(SentimentHistory.symbol == symbol.upper(), SentimentHistory.created_at >= since))).scalars().all()
    catalysts: dict[str, int] = defaultdict(int)
    for signal in signal_rows:
        for catalyst in signal.catalysts:
            catalysts[catalyst] += 1
    return {
        "symbol": symbol.upper(),
        "mentions": len(signal_rows),
        "bullish": sum(1 for s in signal_rows if s.stance == "bullish"),
        "bearish": sum(1 for s in signal_rows if s.stance == "bearish"),
        "avg_sentiment": sum(s.score for s in sentiment_rows) / len(sentiment_rows) if sentiment_rows else 0,
        "catalysts": sorted(catalysts.items(), key=lambda item: item[1], reverse=True)[:10],
    }


async def narrative_timelines(session: AsyncSession, limit: int = 50) -> list[dict[str, Any]]:
    rows = (await session.execute(select(NarrativeCluster).order_by(NarrativeCluster.velocity.desc(), NarrativeCluster.last_seen_at.desc()).limit(limit))).scalars().all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "theme": row.theme,
            "symbols": row.symbols,
            "summary": row.summary,
            "first_seen_at": row.first_seen_at.isoformat(),
            "last_seen_at": row.last_seen_at.isoformat(),
            "mention_count": row.mention_count,
            "velocity": row.velocity,
            "persistence_score": row.persistence_score,
            "sentiment_trend": row.sentiment_trend,
        }
        for row in rows
    ]


async def mention_velocity(session: AsyncSession, symbol: str, recent_hours: int = 24, baseline_days: int = 14) -> float:
    now = utc_now()
    recent_count = await _count_signals(session, symbol, select(ExtractedSignal).where(ExtractedSignal.created_at >= now - timedelta(hours=recent_hours)))
    baseline_count = await _count_signals(
        session,
        symbol,
        select(ExtractedSignal).where(ExtractedSignal.created_at >= now - timedelta(days=baseline_days), ExtractedSignal.created_at < now - timedelta(hours=recent_hours)),
    )
    recent_daily = recent_count / max(recent_hours / 24, 1e-6)
    baseline_daily = baseline_count / max(baseline_days - recent_hours / 24, 1e-6)
    return recent_daily / baseline_daily if baseline_daily else float(recent_daily > 0)


async def _count_signals(session: AsyncSession, symbol: str, stmt: Select[tuple[ExtractedSignal]]) -> int:
    count_stmt = select(func.count()).select_from(stmt.where(ExtractedSignal.symbol == symbol.upper()).subquery())
    return int((await session.execute(count_stmt)).scalar_one())
