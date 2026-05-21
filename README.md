# AI Investment Analyst

Hybrid AI financial intelligence system:

- **Deterministic scoring engine** — ranks stocks using a fixed weighted formula.
- **RAG layer** — retrieves news/filings via `pgvector`, embedded locally with
  Ollama's `embeddinggemma` (768d) by default.
- **LLM layer** — explains results only; never computes numbers.

---

## Architecture

```
User Query
   ↓
Next.js UI (Tailwind + Recharts)
   ↓  /api/query proxy
FastAPI  /api/query
   ↓
Intent Classifier (LLM + heuristics)
   ↓
Router  → SCREENING | RESEARCH | COMPARISON
   ↓
Feature Engine   →   Scoring Engine   →   (RAG)   →   LLM Explanation
   ↓
Structured JSON → Next.js UI
```

### Scoring formula

```
FINAL_SCORE = 0.35 * growth
            + 0.25 * valuation
            + 0.25 * momentum
            + 0.15 * sentiment
```

---

## Frontend layout

```
frontend/
  app/
    layout.tsx             Root layout (dark theme)
    globals.css            Tailwind + background gradients
    page.tsx               Search UI + results orchestration
    api/query/route.ts     Server-side proxy -> FastAPI
  components/
    SearchBar.tsx          Query input + example chips
    IntentBadge.tsx        Intent pill (Screening/Research/Comparison)
    StockCard.tsx          Ticker card: score, feature bars, rationale
    FeatureRadar.tsx       Recharts radar of the 4 features
    ScoreBarChart.tsx      Recharts ranking bar chart
    ExplanationPanel.tsx   LLM explanation + confidence + meta flags
    ContextList.tsx        Retrieved RAG passages
    ConfidenceMeter.tsx    Inline confidence bar
  lib/
    types.ts               Shared TS types (mirrors backend schemas)
    api.ts                 runQuery() helper
  tailwind.config.ts
  next.config.mjs
  tsconfig.json
  package.json
```

## Backend layout

```
backend/
  main.py                 FastAPI entry + CORS + /health
  config.py               Settings (env-driven, all optional)
  api/
    query.py              POST /api/query
  orchestrator/
    classifier.py         Intent + ticker extraction
    router.py             Intent → pipeline dispatch
    pipeline.py           Screening / Research / Comparison pipelines
  tools/
    screener.py           Deterministic scoring + ranking
    rag.py                pgvector retrieval (+ offline fallback)
    comparer.py           Two-ticker hybrid
  features/
    builder.py            Raw metrics → normalized features
  services/
    llm.py                Explanation-only LLM wrapper (Ollama qwen3.5:4b)
    embeddings.py         OpenAI embeddings (+ offline hash fallback)
    supabase.py           Lazy Supabase client
  db/
    client.py             DB facade
  schemas/
    request.py            QueryRequest
    response.py           QueryResponse + StockResult + ContextChunk
  sql/
    schema.sql            Supabase tables + match_embeddings RPC
  ingest/
    universe.py           ~30 large-cap default universe
    fundamentals.py       yfinance -> revenue/EPS/margins/PE/PEG
    prices.py             yfinance -> 14d RSI + 3m return
    news.py               yfinance news -> headline/body/publisher
    sentiment.py          VADER -> [0,1] sentiment score
    embed.py              news -> OpenAI (or hash fallback) embeddings
    snapshot.py           local JSON store (upsert + append-dedup)
    writer.py             Supabase upsert + local snapshot writer
    run.py                CLI orchestrator
  data/
    snapshot.json         ingestion output (gitignored)
```

---

## Run locally

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional; app boots without it
cd ..
uvicorn backend.main:app --reload --port 8000
```

Sanity-check:

```bash
curl http://localhost:8000/health

curl -s -X POST http://localhost:8000/api/query \
  -H 'content-type: application/json' \
  -d '{"query":"top AI growth stocks","top_k":3}' | jq
```

### Tests

From the repo root (with `backend/.venv` activated):

```bash
source backend/.venv/bin/activate
pip install -r backend/requirements.txt   # includes pytest
python -m pytest backend/tests -q
```

No Ollama server is required — API tests stub the LLM layer.

### Embeddings

Embeddings default to **local Ollama** using `embeddinggemma` (768d). Install once:

```bash
ollama pull embeddinggemma
```

Configure in `backend/.env`:

```
EMBEDDING_PROVIDER=ollama          # or "openai" or "hash"
OLLAMA_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=embeddinggemma
```

`/health` reports the active provider, dimension, and model. If you change providers,
re-ingest data because vectors with different dimensions are not comparable.
When using Supabase, keep `vector(N)` in `backend/sql/schema.sql` aligned with
the provider (**768** for `embeddinggemma`, **1536** for `text-embedding-3-small`).

### Chat LLM

Intent classification and explanations use local Ollama through
`backend/services/llm.py`. Scores are always deterministic; the LLM only
writes short explanations. If Ollama is slow or offline, the API falls back to
template text within `OLLAMA_CHAT_TIMEOUT` seconds (default 45).

```env
OLLAMA_CHAT_MODEL=gemini-3-flash-preview:latest
OLLAMA_CHAT_TIMEOUT=45
OLLAMA_CHAT_NUM_PREDICT=256
OLLAMA_CHAT_ENABLED=true
```

Install your model once, e.g. `ollama pull gemini-3-flash-preview:latest`. For
faster responses on modest hardware, try `qwen2.5:3b` instead. Set
`OLLAMA_CHAT_ENABLED=false` to use templates only (no Ollama calls).

### Ingestion (real data, free)

Populate `stocks` / `stock_features` / `news` / `embeddings` from Yahoo
Finance, VADER, and Ollama embeddings (or OpenAI/hash depending on config):

```bash
source backend/.venv/bin/activate

# Full refresh over the built-in ~30-ticker universe:
python -m backend.ingest.run --refresh all

# Just one ticker:
python -m backend.ingest.run --refresh all --tickers NVDA

# Only refresh fundamentals (skip prices + news):
python -m backend.ingest.run --refresh fundamentals

# Offline dry-run (no network; uses the in-repo mock universe to exercise
# the write path — good for CI):
python -m backend.ingest.run --refresh all --dry-run
```

Writes:

- `backend/data/snapshot.json` — always; used automatically by the feature
  engine and RAG layer as a drop-in source whenever Supabase isn't configured.
- Supabase tables `stocks` / `stock_features` / `news` / `embeddings` — when
  creds are present.

Resolution order at query time: **Supabase → local snapshot → built-in mock**.
Re-run ingestion at any time; no restart needed — the API reads the snapshot
fresh on every request.

### Frontend (Next.js)

```bash
cd frontend
cp .env.local.example .env.local    # set BACKEND_URL if not localhost:8000
npm install
npm run dev                          # http://localhost:3000
```

The frontend calls its own `/api/query` route which transparently proxies to
the FastAPI backend, so there are no CORS considerations in dev.

Without Supabase credentials or a full data snapshot, the backend can run on mock
fixtures. Embeddings default to local Ollama (`embeddinggemma`). The chat layer
uses `OLLAMA_CHAT_MODEL=qwen3.5:4b`. If Ollama is unavailable, explanations
fall back to deterministic templates.

---

## API contract

`POST /api/query`

Request:

```json
{ "query": "compare NVDA vs AMD for AI exposure", "top_k": 5 }
```

Response:

```json
{
  "intent": "COMPARISON",
  "tickers": ["NVDA", "AMD"],
  "results": [
    {
      "ticker": "NVDA",
      "name": "NVIDIA Corporation",
      "score": 0.71,
      "features": { "growth": 0.9, "valuation": 0.3, "momentum": 0.8, "sentiment": 0.74 },
      "rationale": "Driven by growth (0.90); weakest on valuation (0.30)."
    }
  ],
  "context": [
    { "source": "news", "ticker": "NVDA", "text": "...", "similarity": 0.82 }
  ],
  "explanation": "...",
  "confidence": 0.75,
  "meta": {
    "llm": {
      "provider": "ollama",
      "ollama_chat_model": "qwen3.5:4b"
    },
    "supabase": true
  }
}
```

---

## Supabase setup (when ready)

1. Create a project, enable the `pgvector` extension.
2. Run `backend/sql/schema.sql` in the SQL editor.
3. Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`.
4. Populate `stocks` + `stock_features` via your ingestion job.
5. Populate `embeddings` (chunk → vector) for RAG.

---

## Roadmap

- ML-learned scoring weights (regression over realized returns)
- Real-time streaming ingestion
- User personalization (adaptive weights)
- Multi-agent orchestration (specialized research agents)
