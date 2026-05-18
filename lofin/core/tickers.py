from __future__ import annotations

import re

COMMON_WORDS = {
    "AI", "CEO", "CFO", "USA", "SEC", "ETF", "GDP", "IPO", "ATH", "DD", "YOLO", "ITM", "OTM",
    "IV", "ER", "EPS", "FED", "FOMC", "API", "CPU", "GPU", "EV", "PE", "HODL",
}
KNOWN_ETFS = {
    "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
    "SMH", "SOXX", "ARKK", "VTI", "VOO", "VEA", "VWO", "TLT", "HYG", "LQD", "XRT", "XHB",
}
TICKER_RE = re.compile(r"(?<![A-Z0-9])\$?([A-Z]{1,5})(?![A-Z0-9])")
OPTION_RE = re.compile(
    r"(?P<ticker>\$?[A-Z]{1,5})\s+(?P<strike>\d+(?:\.\d+)?)\s*(?P<kind>[cCpP])\s+(?P<expiry>\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)"
)


def extract_candidate_tickers(text: str) -> set[str]:
    symbols = {m.group(1).upper() for m in TICKER_RE.finditer(text)}
    return {s for s in symbols if s not in COMMON_WORDS}


def classify_symbol(symbol: str) -> str:
    return "etf" if symbol.upper() in KNOWN_ETFS else "stock"


def extract_options(text: str) -> list[dict[str, str | float]]:
    contracts: list[dict[str, str | float]] = []
    for match in OPTION_RE.finditer(text):
        contracts.append(
            {
                "ticker": match.group("ticker").replace("$", "").upper(),
                "strike": float(match.group("strike")),
                "contract_type": "call" if match.group("kind").lower() == "c" else "put",
                "expiry_raw": match.group("expiry"),
            }
        )
    return contracts
