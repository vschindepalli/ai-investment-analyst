"""VADER-based sentiment scoring.

VADER produces a ``compound`` score in [-1, 1]. We map it to [0, 1] so it
feeds directly into the feature engine's ``sentiment`` slot.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def _analyzer():
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    return SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    if not text:
        return 0.5
    compound = _analyzer().polarity_scores(text).get("compound", 0.0)
    return max(0.0, min(1.0, (compound + 1.0) / 2.0))


def aggregate_ticker_sentiment(news_rows: list[dict[str, Any]]) -> float | None:
    """Average sentiment across a ticker's recent news. ``None`` if empty."""
    if not news_rows:
        return None
    scores = [score_text(r.get("body") or r.get("headline") or "") for r in news_rows]
    if not scores:
        return None
    return sum(scores) / len(scores)
