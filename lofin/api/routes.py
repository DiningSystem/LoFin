from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lofin.agents.messages import AgentMessage
from lofin.api.schemas import AnalyzeRequest, CleanupRequest
from lofin.db.models import DailySummary
from lofin.db.session import get_session
from lofin.services.analytics import narrative_timelines, ticker_profile, top_symbols
from lofin.workers.orchestrator import AgentOrchestrator

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/top-tickers")
async def get_top_tickers(session: AsyncSession = Depends(get_session)) -> list[dict[str, object]]:
    return await top_symbols(session, "stock")


@router.get("/top-etfs")
async def get_top_etfs(session: AsyncSession = Depends(get_session)) -> list[dict[str, object]]:
    return await top_symbols(session, "etf")


@router.get("/narratives")
async def get_narratives(session: AsyncSession = Depends(get_session)) -> list[dict[str, object]]:
    return await narrative_timelines(session)


@router.get("/ticker/{ticker}")
async def get_ticker(ticker: str, session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    return await ticker_profile(session, ticker)


@router.get("/etf/{ticker}")
async def get_etf(ticker: str, session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    return await ticker_profile(session, ticker)


@router.get("/summary/daily")
async def get_daily_summary(session: AsyncSession = Depends(get_session)) -> list[dict[str, object]]:
    rows = (await session.execute(select(DailySummary).order_by(DailySummary.created_at.desc()).limit(20))).scalars().all()
    return [
        {"date": row.summary_date, "scope": row.scope, "symbol": row.symbol, "content": row.content, "risks": row.risks, "catalysts": row.catalysts, "confidence": row.confidence}
        for row in rows
    ]


@router.post("/analyze")
async def analyze(request: AnalyzeRequest, session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    orchestrator = AgentOrchestrator(session)
    await orchestrator.publish(AgentMessage(sender="ingestion", recipient="ingestion", message_type="analysis.requested", payload=request.model_dump(exclude_none=True)))
    processed = await orchestrator.drain()
    return {"status": "completed", "messages_processed": len(processed)}


@router.post("/cleanup")
async def cleanup(request: CleanupRequest, session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    orchestrator = AgentOrchestrator(session)
    await orchestrator.publish(AgentMessage(sender="cleanup", recipient="cleanup", message_type="cleanup.requested", payload=request.model_dump(exclude_none=True)))
    processed = await orchestrator.drain()
    return {"status": "completed", "messages_processed": len(processed)}
