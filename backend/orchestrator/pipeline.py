"""End-to-end pipelines.

Each pipeline composes the underlying layers (features → scoring → RAG → LLM)
into a single ``QueryResponse``.
"""
from __future__ import annotations

from typing import Any

from backend.config import get_settings
from backend.schemas.response import (
    ContextChunk,
    FeatureBreakdown,
    QueryResponse,
    StockResult,
)
from backend.services import llm as llm_service
from backend.tools.comparer import compare
from backend.tools.rag import retrieve
from backend.tools.screener import rank_stocks


def _to_stock_result(row: dict[str, Any]) -> StockResult:
    f = row["features"]
    return StockResult(
        ticker=row["ticker"],
        name=row.get("name"),
        score=row["score"],
        features=FeatureBreakdown(**f),
        rationale=row.get("rationale"),
    )


def _to_chunk(c: dict[str, Any]) -> ContextChunk:
    return ContextChunk(
        source=c.get("source", "unknown"),
        ticker=c.get("ticker"),
        text=c.get("text", ""),
        similarity=c.get("similarity"),
    )


def _meta() -> dict[str, Any]:
    s = get_settings()
    return {
        "llm": {
            "provider": "ollama",
            "ollama_chat_model": s.ollama_chat_model,
        },
        "supabase": s.has_supabase,
    }


# ---------------------------------------------------------------------------
# SCREENING
# ---------------------------------------------------------------------------
def screening_pipeline(
    query: str, tickers: list[str] | None = None, top_k: int = 5
) -> QueryResponse:
    ranked = rank_stocks(tickers=tickers or None, top_k=top_k)
    explanation = llm_service.explain_screening(query, ranked)
    return QueryResponse(
        intent="SCREENING",
        tickers=tickers or [],
        results=[_to_stock_result(r) for r in ranked],
        context=[],
        explanation=explanation,
        confidence=0.8 if ranked else 0.2,
        meta=_meta(),
    )


# ---------------------------------------------------------------------------
# RESEARCH
# ---------------------------------------------------------------------------
def research_pipeline(
    query: str, tickers: list[str] | None = None, top_k: int = 5
) -> QueryResponse:
    chunks = retrieve(query, top_k=top_k, tickers=tickers or None)
    explanation = llm_service.explain_research(query, chunks)
    top_sim = max((c.get("similarity") or 0.0 for c in chunks), default=0.0)
    return QueryResponse(
        intent="RESEARCH",
        tickers=tickers or [],
        results=[],
        context=[_to_chunk(c) for c in chunks],
        explanation=explanation,
        confidence=min(0.95, 0.4 + top_sim * 0.5),
        meta=_meta(),
    )


# ---------------------------------------------------------------------------
# COMPARISON
# ---------------------------------------------------------------------------
def comparison_pipeline(
    query: str, tickers: list[str] | None = None, top_k: int = 5
) -> QueryResponse:
    tickers = tickers or []
    if len(tickers) < 2:
        # Degenerate case: fall back to screening so we still return something
        # useful instead of an empty comparison.
        return screening_pipeline(query, tickers=tickers, top_k=top_k)

    bundle = compare(tickers, query, top_k_ctx=top_k)
    ranked = bundle["ranked"]
    chunks = bundle["context"]
    explanation = llm_service.explain_comparison(query, ranked, chunks)
    return QueryResponse(
        intent="COMPARISON",
        tickers=tickers,
        results=[_to_stock_result(r) for r in ranked],
        context=[_to_chunk(c) for c in chunks],
        explanation=explanation,
        confidence=0.75,
        meta=_meta(),
    )
