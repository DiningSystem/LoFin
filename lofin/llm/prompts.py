EXTRACTION_PROMPT = """
You extract financial signals from a single discussion. Return ONLY JSON with keys:
tickers: array of {symbol, asset_type: stock|etf, stance: bullish|bearish|neutral|uncertain, confidence: 0..1,
catalysts: string[], entities: string[], claims: string[], uncertainty: 0..1}.
options: array of {ticker, strike, contract_type: call|put, expiry_raw}.
Rules: do not invent tickers; preserve uncertainty; use empty arrays when absent.
Text:
{content}
"""

SENTIMENT_PROMPT = """
Classify financial sentiment for {symbol}. Return ONLY JSON:
{"sentiment":"bullish|bearish|neutral|uncertain","score":-1..1,"confidence":0..1,"rationale":"short evidence-based rationale"}.
Avoid hallucinations and reduce confidence when evidence is promotional or ambiguous.
Text:
{content}
"""

SUMMARY_PROMPT = """
Create an evidence-weighted market narrative summary from retrieved discussions and market context.
Return ONLY JSON with keys content, risks, catalysts, confidence.
Compare recent claims to historical context and call out shifts or acceleration.
Context:
{context}
"""
