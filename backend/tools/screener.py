"""Deterministic scoring engine (alpha model).

The formula is the single source of truth for ranking. The LLM is never
allowed to modify these numbers.
"""
from __future__ import annotations

from typing import Any

from backend.features.builder import build_features

WEIGHTS = {
    "growth": 0.35,
    "valuation": 0.25,
    "momentum": 0.25,
    "sentiment": 0.15,
}


def compute_score(f: dict[str, float]) -> float:
    #this must stay deterministic so scores are reproducible across runs.
    return (
        WEIGHTS["growth"] * f["growth"]
        + WEIGHTS["valuation"] * f["valuation"]
        + WEIGHTS["momentum"] * f["momentum"]
        + WEIGHTS["sentiment"] * f["sentiment"]
    )


def _rationale(f: dict[str, float]) -> str:
    #surface strongest and weakest dimensions to explain rank placement.
    ordered = sorted(f.items(), key=lambda kv: kv[1], reverse=True)
    top = ordered[0]
    bottom = ordered[-1]
    return f"Driven by {top[0]} ({top[1]:.2f}); weakest on {bottom[0]} ({bottom[1]:.2f})."


def rank_stocks(
    tickers: list[str] | None = None, top_k: int = 5
) -> list[dict[str, Any]]:
    rows = build_features(tickers)
    scored = []
    for r in rows:
        f = r["features"]
        scored.append(
            {
                "ticker": r["ticker"],
                "name": r["name"],
                "features": f,
                "score": round(compute_score(f), 4),
                "rationale": _rationale(f),
            }
        )
    #sort after rounding so what users see matches ordering.
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
