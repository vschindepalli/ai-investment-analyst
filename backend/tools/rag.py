"""RAG layer.

Flow: query -> embedding -> similarity search (Supabase pgvector RPC) ->
top-k chunks.

Fallback: when Supabase isn't configured we search a small in-repo corpus
using cosine similarity on deterministic hash embeddings. This keeps the
full pipeline runnable offline.
"""
from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.db.client import get_client
from backend.services.embeddings import cosine, embed

# ---------------------------------------------------------------------------
# Offline corpus (only used when Supabase is unavailable).
# ---------------------------------------------------------------------------
_MOCK_CORPUS: list[dict[str, Any]] = [
    {
        "source": "news",
        "ticker": "NVDA",
        "text": (
            "NVIDIA posted record data-center revenue driven by sustained AI "
            "infrastructure demand, with gross margins expanding quarter over "
            "quarter."
        ),
    },
    {
        "source": "10-K",
        "ticker": "AAPL",
        "text": (
            "Apple's services segment continues to grow double digits, "
            "offsetting softer iPhone unit sales and supporting overall "
            "margin expansion."
        ),
    },
    {
        "source": "news",
        "ticker": "MSFT",
        "text": (
            "Microsoft Azure growth reaccelerated on Copilot and AI workload "
            "adoption, with capex guidance rising to fund data-center buildout."
        ),
    },
    {
        "source": "earnings",
        "ticker": "META",
        "text": (
            "Meta's advertising revenue grew on improved ad targeting from "
            "ML-driven ranking, while Reality Labs losses remained elevated."
        ),
    },
    {
        "source": "news",
        "ticker": "TSLA",
        "text": (
            "Tesla cut prices across key markets to defend share, pressuring "
            "automotive gross margin; bulls point to energy storage growth."
        ),
    },
    {
        "source": "news",
        "ticker": "GOOGL",
        "text": (
            "Alphabet's cloud segment turned profitable and Search grew "
            "despite competitive pressure from generative AI answer engines."
        ),
    },
    {
        "source": "news",
        "ticker": "AMD",
        "text": (
            "AMD gained data-center GPU share in AI inference workloads while "
            "PC client demand remained mixed; investors watch MI300 ramp cadence."
        ),
    },
    {
        "source": "earnings",
        "ticker": "AMZN",
        "text": (
            "Amazon Web Services grew on enterprise cloud adoption; retail "
            "margins improved on logistics efficiency and advertising mix."
        ),
    },
]


def _search_supabase(query_vec: list[float], top_k: int) -> list[dict[str, Any]] | None:
    client = get_client()
    if client is None:
        return None
    try:
        resp = client.rpc(
            "match_embeddings",
            {"query_embedding": query_vec, "match_count": top_k},
        ).execute()
        rows = resp.data or []
    except Exception:
        return None
    if not rows:
        return None
    return [
        {
            "source": r.get("source", "unknown"),
            "ticker": r.get("ticker"),
            "text": r.get("text", ""),
            "similarity": float(r.get("similarity", 0.0)),
        }
        for r in rows
    ]


def _search_snapshot(
    query_vec: list[float], top_k: int, tickers: list[str] | None
) -> list[dict[str, Any]] | None:
    """Score the snapshot's stored embeddings against the query vector."""
    from backend.ingest.snapshot import load

    snap = load()
    rows = snap.get("embeddings") or []
    if not rows:
        return None
    if tickers:
        wanted = {t.upper() for t in tickers}
        filtered = [r for r in rows if (r.get("ticker") or "").upper() in wanted]
        rows = filtered or rows
    scored: list[dict[str, Any]] = []
    for r in rows:
        vec = r.get("embedding") or []
        sim = cosine(query_vec, vec)
        scored.append(
            {
                "source": r.get("source", "news"),
                "ticker": r.get("ticker"),
                "text": r.get("text", ""),
                "similarity": round(sim, 4),
            }
        )
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def _search_mock(
    query_vec: list[float], top_k: int, tickers: list[str] | None
) -> list[dict[str, Any]]:
    candidates = _MOCK_CORPUS
    if tickers:
        wanted = {t.upper() for t in tickers}
        candidates = [c for c in candidates if c["ticker"] in wanted] or _MOCK_CORPUS
    scored = []
    for c in candidates:
        sim = cosine(query_vec, embed(c["text"]))
        scored.append({**c, "similarity": round(sim, 4)})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def retrieve(
    query: str, top_k: int = 5, tickers: list[str] | None = None
) -> list[dict[str, Any]]:
    query_vec = embed(query)
    hits = _search_supabase(query_vec, top_k) or _search_snapshot(
        query_vec, top_k, tickers
    )
    if hits:
        return hits
    if not get_settings().allow_mock_fallback:
        return []
    return _search_mock(query_vec, top_k, tickers)
