from lofin.core.tickers import classify_symbol, extract_candidate_tickers, extract_options


def test_extract_candidate_tickers_filters_common_words() -> None:
    symbols = extract_candidate_tickers("Loaded $NVDA and SMH. CEO says AI GPU demand is strong.")
    assert "NVDA" in symbols
    assert "SMH" in symbols
    assert "CEO" not in symbols
    assert "AI" not in symbols


def test_extract_options_contract() -> None:
    contracts = extract_options("Loaded NVDA 150c 6/21 and bought SPY 520p 07/19")
    assert contracts == [
        {"ticker": "NVDA", "strike": 150.0, "contract_type": "call", "expiry_raw": "6/21"},
        {"ticker": "SPY", "strike": 520.0, "contract_type": "put", "expiry_raw": "07/19"},
    ]


def test_classify_known_etf() -> None:
    assert classify_symbol("QQQ") == "etf"
    assert classify_symbol("MSFT") == "stock"
