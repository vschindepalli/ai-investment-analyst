"""Default ticker universe.

Kept intentionally short (~30 large caps across sectors) so the free-tier
ingest stays fast and polite to Yahoo Finance. Override at runtime via
``--tickers`` on the CLI.
"""
from __future__ import annotations

DEFAULT_UNIVERSE: list[dict[str, str]] = [
    # Tech
    {"ticker": "NVDA", "sector": "Technology"},
    {"ticker": "AAPL", "sector": "Technology"},
    {"ticker": "MSFT", "sector": "Technology"},
    {"ticker": "GOOGL", "sector": "Technology"},
    {"ticker": "META", "sector": "Technology"},
    {"ticker": "AMZN", "sector": "Technology"},
    {"ticker": "TSLA", "sector": "Consumer Discretionary"},
    {"ticker": "AMD", "sector": "Technology"},
    {"ticker": "AVGO", "sector": "Technology"},
    {"ticker": "CRM", "sector": "Technology"},
    {"ticker": "ADBE", "sector": "Technology"},
    {"ticker": "ORCL", "sector": "Technology"},
    {"ticker": "NFLX", "sector": "Communication Services"},
    # Financials
    {"ticker": "JPM", "sector": "Financials"},
    {"ticker": "BAC", "sector": "Financials"},
    {"ticker": "V", "sector": "Financials"},
    {"ticker": "MA", "sector": "Financials"},
    {"ticker": "GS", "sector": "Financials"},
    # Healthcare
    {"ticker": "UNH", "sector": "Healthcare"},
    {"ticker": "JNJ", "sector": "Healthcare"},
    {"ticker": "LLY", "sector": "Healthcare"},
    {"ticker": "ABBV", "sector": "Healthcare"},
    {"ticker": "PFE", "sector": "Healthcare"},
    # Consumer
    {"ticker": "WMT", "sector": "Consumer Staples"},
    {"ticker": "COST", "sector": "Consumer Staples"},
    {"ticker": "KO", "sector": "Consumer Staples"},
    {"ticker": "PEP", "sector": "Consumer Staples"},
    {"ticker": "MCD", "sector": "Consumer Discretionary"},
    {"ticker": "NKE", "sector": "Consumer Discretionary"},
    {"ticker": "DIS", "sector": "Communication Services"},
    # Energy
    {"ticker": "XOM", "sector": "Energy"},
    {"ticker": "CVX", "sector": "Energy"},
]


def default_tickers() -> list[str]:
    return [s["ticker"] for s in DEFAULT_UNIVERSE]


def sector_for(ticker: str) -> str | None:
    for s in DEFAULT_UNIVERSE:
        if s["ticker"] == ticker.upper():
            return s["sector"]
    return None
