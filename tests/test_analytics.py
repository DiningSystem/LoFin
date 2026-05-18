from datetime import UTC, datetime

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from lofin.db.models import Base, ExtractedSignal, RawPost, SentimentHistory
from lofin.services.analytics import ticker_profile, top_symbols


@pytest.mark.asyncio
async def test_top_symbols_and_ticker_profile() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        post = RawPost(source="test", source_id="1", title="SMH inflows", body="SMH bullish", posted_at=datetime.now(tz=UTC), content_hash="hash")
        session.add(post)
        await session.flush()
        session.add(ExtractedSignal(raw_post_id=post.id, symbol="SMH", asset_type="etf", stance="bullish", confidence=0.8, catalysts=["ETF inflows"]))
        session.add(SentimentHistory(raw_post_id=post.id, symbol="SMH", sentiment="bullish", score=0.7, confidence=0.8, model_name="test"))
        await session.commit()
        top = await top_symbols(session, "etf")
        profile = await ticker_profile(session, "SMH")
        assert top[0]["symbol"] == "SMH"
        assert profile["mentions"] == 1
        assert profile["avg_sentiment"] == 0.7
