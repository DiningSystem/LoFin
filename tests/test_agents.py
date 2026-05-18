from datetime import UTC, datetime

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from lofin.agents.extraction import ExtractionAgent
from lofin.agents.messages import AgentMessage
from lofin.db.models import Base, ExtractedSignal, OptionsFlow, RawPost


class FakeLLM:
    async def generate_json(self, prompt: str, model: str | None = None):
        return {
            "tickers": [
                {
                    "symbol": "NVDA",
                    "asset_type": "stock",
                    "stance": "bullish",
                    "confidence": 0.9,
                    "catalysts": ["AI infrastructure demand"],
                    "entities": ["Blackwell"],
                    "claims": ["demand remains strong"],
                    "uncertainty": 0.15,
                }
            ],
            "options": [{"ticker": "NVDA", "strike": 150, "contract_type": "call", "expiry_raw": "6/21"}],
        }


@pytest.mark.asyncio
async def test_extraction_agent_persists_structured_signals() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        post = RawPost(
            source="test",
            source_id="1",
            title="NVDA breakout",
            body="Loaded NVDA 150c 6/21 because AI infrastructure demand is strong",
            posted_at=datetime.now(tz=UTC),
            content_hash="abc",
        )
        session.add(post)
        await session.commit()
        message = AgentMessage(sender="ingestion", recipient="extraction", message_type="posts.ingested", payload={"post_ids": [post.id]})
        responses = await ExtractionAgent(session, llm=FakeLLM()).run(message)  # type: ignore[arg-type]
        signals = (await session.execute(select(ExtractedSignal))).scalars().all()
        options = (await session.execute(select(OptionsFlow))).scalars().all()
        assert [r.recipient for r in responses] == ["sentiment", "market_data", "narrative_memory"]
        assert signals[0].symbol == "NVDA"
        assert signals[0].catalysts == ["AI infrastructure demand"]
        assert options[0].contract_type == "call"
