"""Comparison tool — combines scoring + RAG for two or more tickers."""
from __future__ import annotations

from typing import Any

from backend.tools.rag import retrieve
from backend.tools.screener import rank_stocks


def compare(tickers: list[str], query: str, top_k_ctx: int = 4) -> dict[str, Any]:
    ranked = rank_stocks(tickers=tickers, top_k=len(tickers))
    context = retrieve(query, top_k=top_k_ctx, tickers=tickers)
    return {"ranked": ranked, "context": context}
