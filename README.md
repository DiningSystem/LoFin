# LoFin

LoFin is a local-first, production-style multi-agent financial intelligence platform for stocks and ETFs. It continuously ingests public financial discussions and news, extracts structured market signals, stores longitudinal memory, and ranks narratives with local Ollama-hosted LLMs.

## Architecture

```text
Connectors -> Ingestion Agent -> Extraction Agent -> Sentiment Agent
                                  |-> Market Data Agent -> Ranking Agent -> Risk Agent
                                  |-> Narrative Memory Agent -> Summarization Agent
                                  |-> Cleanup Agent for retention/archive policies
```

Core components:

- **FastAPI backend** exposes analysis, cleanup, ticker, ETF, narrative, and summary APIs.
- **PostgreSQL** stores raw posts, extracted signals, tickers, ETF records, options mentions, sentiment history, narrative clusters, daily summaries, market snapshots, and agent logs.
- **Qdrant** stores vector memory for semantic retrieval with source, timestamp, sentiment, and ticker payload filters.
- **Ollama** provides local inference for `llama3.1`, `qwen3`, and `deepseek-r1` compatible JSON extraction/summarization prompts.
- **Streamlit dashboard** visualizes top stocks, ETFs, narrative clusters, ticker pages, options activity, risk scores, and AI summaries.
- **Async orchestrator** provides lightweight structured JSON message passing without requiring Kafka/Celery on day one.

## Implemented Agents

1. **Ingestion Agent** pulls Reddit and RSS, timestamps content, deduplicates by content hash, and stores raw discussions.
2. **Extraction Agent** combines regex and Ollama JSON extraction for stock tickers, ETF tickers, option contracts, catalysts, claims, stance, and uncertainty.
3. **Market Data Agent** retrieves price, volume, relative volume, market cap, expiries, and market metadata through Yahoo Finance/yfinance.
4. **Sentiment Agent** performs confidence-scored bullish/bearish/neutral/uncertain classification through Ollama with lexical fallback.
5. **Narrative Memory Agent** embeds discussions in Qdrant, tracks rolling narrative clusters, sentiment trend, velocity, and persistence.
6. **Ranking Agent** scores opportunities from mention velocity, repeated mentions, and high-signal thresholds.
7. **Summarization Agent** generates daily market summaries with catalysts, risks, confidence, and historical context.
8. **Risk Agent** flags coordinated hype, low-signal items, and suspicious momentum bursts.
9. **Cleanup Agent** applies rolling retention, archives high-signal discussions, deletes low-score stale content, and cleans vector memory.

## API

- `GET /top-tickers`
- `GET /top-etfs`
- `GET /narratives`
- `GET /ticker/{ticker}`
- `GET /etf/{ticker}`
- `GET /summary/daily`
- `POST /analyze`
- `POST /cleanup`
- `GET /metrics`

## Local setup

```bash
cp .env.example .env
./scripts/dev_bootstrap.sh
docker compose up --build
```

Open:

- API: <http://localhost:8000/docs>
- Dashboard: <http://localhost:8501>
- Qdrant: <http://localhost:6333/dashboard>
- Ollama: <http://localhost:11434>

Pull alternate local models:

```bash
docker compose exec ollama ollama pull qwen3
docker compose exec ollama ollama pull deepseek-r1
```

Then set `OLLAMA_MODEL=qwen3` or `OLLAMA_MODEL=deepseek-r1` in `.env`.

## Retention policy

Environment variables:

```env
RETENTION_DAYS=30
DELETE_LOW_SCORE_AFTER_DAYS=7
KEEP_HIGH_SIGNAL_FOREVER=true
HIGH_SIGNAL_SCORE=0.75
```

`POST /cleanup` deletes stale discussions, preserves high-signal records when configured, archives historical high-signal snapshots to `archives/*.jsonl.gz`, and attempts to remove old Qdrant vectors.

## Longitudinal memory model

LoFin is designed to avoid single-post analysis. Each discussion is stored in durable tables and, when embeddings are available, in vector memory. Narrative clusters maintain:

- first/last seen timestamps,
- mention count and velocity,
- recurring symbols,
- sentiment trend samples,
- persistence score,
- theme summary.

This enables week-over-week and month-over-month reasoning about recurring themes such as AI infrastructure demand, semiconductor shortages, nuclear energy revival, or sector ETF inflow narratives.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,dashboard]"
pytest
ruff check .
mypy lofin
uvicorn lofin.api.app:app --reload
```

For quick local tests without PostgreSQL, the default `DATABASE_URL` falls back to SQLite. Production and Docker use PostgreSQL.

## Example output

`GET /top-tickers`

```json
[
  {"symbol": "NVDA", "mentions": 42, "confidence": 0.81},
  {"symbol": "TSLA", "mentions": 29, "confidence": 0.68}
]
```

`GET /narratives`

```json
[
  {
    "title": "AI Infrastructure Demand narrative",
    "theme": "ai infrastructure demand",
    "symbols": ["NVDA", "SMH", "AMD"],
    "mention_count": 88,
    "velocity": 4.2,
    "persistence_score": 0.74
  }
]
```

## Scaling roadmap

The current queue is intentionally lightweight and local-first. The `AgentMessage` schema and agent boundaries are designed for future migration to Redis Streams, Celery, Kafka, WebSocket streaming, or multi-worker Kubernetes deployments without changing agent business logic.
