from __future__ import annotations

from sqlalchemy import select

from lofin.agents.base import Agent, next_message
from lofin.agents.messages import AgentMessage
from lofin.core.tickers import classify_symbol, extract_candidate_tickers, extract_options
from lofin.db.models import ExtractedSignal, OptionsFlow, RawPost, Ticker
from lofin.llm.ollama import OllamaClient
from lofin.llm.prompts import EXTRACTION_PROMPT


class ExtractionAgent(Agent):
    name = "extraction"

    def __init__(self, session, llm: OllamaClient | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(session)
        self.llm = llm or OllamaClient()

    async def handle(self, message: AgentMessage) -> list[AgentMessage]:
        post_ids = message.payload.get("post_ids", [])
        posts = (await self.session.execute(select(RawPost).where(RawPost.id.in_(post_ids)))).scalars().all() if post_ids else []
        symbols: set[str] = set()
        for post in posts:
            content = f"{post.title}\n{post.body}"
            regex_symbols = extract_candidate_tickers(content)
            llm_payload = await self._safe_llm_extract(content)
            for item in llm_payload.get("tickers", []):
                symbol = str(item.get("symbol", "")).replace("$", "").upper()
                if not symbol:
                    continue
                regex_symbols.add(symbol)
                asset_type = item.get("asset_type") or classify_symbol(symbol)
                await self.session.merge(Ticker(symbol=symbol, asset_type=asset_type))
                self.session.add(
                    ExtractedSignal(
                        raw_post_id=post.id,
                        symbol=symbol,
                        asset_type=asset_type,
                        stance=item.get("stance", "uncertain"),
                        confidence=float(item.get("confidence", 0.5)),
                        catalysts=item.get("catalysts", []),
                        entities=item.get("entities", []),
                        claims=item.get("claims", []),
                        uncertainty=float(item.get("uncertainty", 0.5)),
                    )
                )
                symbols.add(symbol)
            for symbol in regex_symbols - symbols:
                asset_type = classify_symbol(symbol)
                await self.session.merge(Ticker(symbol=symbol, asset_type=asset_type))
                self.session.add(ExtractedSignal(raw_post_id=post.id, symbol=symbol, asset_type=asset_type, confidence=0.35, uncertainty=0.8))
                symbols.add(symbol)
            for contract in [*extract_options(content), *llm_payload.get("options", [])]:
                ticker = str(contract.get("ticker", "")).replace("$", "").upper()
                if ticker:
                    self.session.add(OptionsFlow(raw_post_id=post.id, symbol=ticker, contract_type=contract.get("contract_type", "call"), strike=float(contract.get("strike", 0)), expiry=str(contract.get("expiry_raw", ""))))
                    symbols.add(ticker)
            post.processed = True
        await self.session.commit()
        return [
            next_message("extraction", "sentiment", "signals.extracted", {"post_ids": post_ids, "symbols": sorted(symbols)}, message.correlation_id),
            next_message("extraction", "market_data", "symbols.extracted", {"symbols": sorted(symbols)}, message.correlation_id),
            next_message("extraction", "narrative_memory", "posts.extracted", {"post_ids": post_ids, "symbols": sorted(symbols)}, message.correlation_id),
        ]

    async def _safe_llm_extract(self, content: str) -> dict[str, object]:
        try:
            return await self.llm.generate_json(EXTRACTION_PROMPT.format(content=content[:6000]))
        except Exception:
            return {"tickers": [], "options": []}
