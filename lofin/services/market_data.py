from __future__ import annotations

from typing import Any

import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential


class MarketDataService:
    """Yahoo Finance/yfinance backed market data service with conservative fallbacks."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    async def snapshot(self, symbol: str) -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info or {}
        history = ticker.history(period="30d")
        volume = float(info.get("last_volume") or history["Volume"].iloc[-1]) if not history.empty else None
        avg_volume = float(history["Volume"].tail(20).mean()) if not history.empty else None
        return {
            "symbol": symbol.upper(),
            "price": float(info.get("last_price")) if info.get("last_price") is not None else None,
            "volume": volume,
            "relative_volume": (volume / avg_volume) if volume and avg_volume else None,
            "market_cap": float(info.get("market_cap")) if info.get("market_cap") is not None else None,
            "metadata_json": {"currency": info.get("currency"), "exchange": info.get("exchange")},
        }

    async def options_chain(self, symbol: str) -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        expiries = list(ticker.options or [])
        return {"symbol": symbol.upper(), "expiries": expiries[:8]}
