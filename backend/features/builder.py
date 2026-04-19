"""Feature Engine.

Pulls raw data (from Supabase when configured, otherwise from an in-repo mock
universe) and normalizes it into the four feature categories consumed by the
scoring engine:

    {"growth": [0..1], "valuation": [0..1], "momentum": [0..1], "sentiment": [0..1]}

Normalization keeps the deterministic scoring formula stable regardless of the
underlying units of raw metrics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.db.client import get_client

# ---------------------------------------------------------------------------
# Mock universe — used when Supabase is not configured. Values are roughly
# illustrative; the normalization below only cares about relative ordering.
# ---------------------------------------------------------------------------
_MOCK_UNIVERSE: list[dict[str, Any]] = [
    {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "revenue_growth": 0.78,
        "eps_growth": 0.92,
        "operating_margin": 0.54,
        "pe_ratio": 62.0,
        "peg_ratio": 1.4,
        "rsi": 68.0,
        "return_3m": 0.22,
        "sentiment_score": 0.74,
    },
    {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "revenue_growth": 0.05,
        "eps_growth": 0.08,
        "operating_margin": 0.30,
        "pe_ratio": 30.0,
        "peg_ratio": 2.8,
        "rsi": 55.0,
        "return_3m": 0.06,
        "sentiment_score": 0.58,
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "revenue_growth": 0.16,
        "eps_growth": 0.20,
        "operating_margin": 0.44,
        "pe_ratio": 34.0,
        "peg_ratio": 2.1,
        "rsi": 60.0,
        "return_3m": 0.09,
        "sentiment_score": 0.66,
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet Inc.",
        "revenue_growth": 0.12,
        "eps_growth": 0.18,
        "operating_margin": 0.29,
        "pe_ratio": 24.0,
        "peg_ratio": 1.6,
        "rsi": 58.0,
        "return_3m": 0.08,
        "sentiment_score": 0.61,
    },
    {
        "ticker": "META",
        "name": "Meta Platforms, Inc.",
        "revenue_growth": 0.22,
        "eps_growth": 0.36,
        "operating_margin": 0.38,
        "pe_ratio": 27.0,
        "peg_ratio": 1.2,
        "rsi": 64.0,
        "return_3m": 0.14,
        "sentiment_score": 0.55,
    },
    {
        "ticker": "TSLA",
        "name": "Tesla, Inc.",
        "revenue_growth": 0.03,
        "eps_growth": -0.20,
        "operating_margin": 0.08,
        "pe_ratio": 70.0,
        "peg_ratio": 4.5,
        "rsi": 48.0,
        "return_3m": -0.05,
        "sentiment_score": 0.40,
    },
]


@dataclass
class RawStock:
    ticker: str
    name: str
    raw: dict[str, Any]


def _fetch_from_supabase(tickers: list[str] | None) -> list[RawStock] | None:
    client = get_client()
    if client is None:
        return None
    try:
        q = client.table("stock_features").select("*, stocks(name)")
        if tickers:
            q = q.in_("ticker", tickers)
        rows = q.execute().data or []
    except Exception:
        return None
    if not rows:
        return None
    out: list[RawStock] = []
    for r in rows:
        name = (r.get("stocks") or {}).get("name") or r["ticker"]
        out.append(RawStock(ticker=r["ticker"], name=name, raw=r))
    return out


def _fetch_from_snapshot(tickers: list[str] | None) -> list[RawStock] | None:
    """Load from the local ingestion snapshot if one exists."""
    from backend.ingest.snapshot import load

    snap = load()
    rows = snap.get("stock_features") or []
    if not rows:
        return None
    stocks_by_ticker = {s["ticker"]: s for s in snap.get("stocks") or []}
    if tickers:
        wanted = {t.upper() for t in tickers}
        rows = [r for r in rows if r["ticker"] in wanted]
    if not rows:
        return None
    out: list[RawStock] = []
    for r in rows:
        meta = stocks_by_ticker.get(r["ticker"], {})
        name = meta.get("name") or r["ticker"]
        out.append(RawStock(ticker=r["ticker"], name=name, raw=r))
    return out


def _fetch_mock(tickers: list[str] | None) -> list[RawStock]:
    universe = _MOCK_UNIVERSE
    if tickers:
        wanted = {t.upper() for t in tickers}
        universe = [u for u in universe if u["ticker"] in wanted]
    return [RawStock(ticker=u["ticker"], name=u["name"], raw=u) for u in universe]


def fetch_raw(tickers: list[str] | None = None) -> list[RawStock]:
    """Fetch raw stock rows — Supabase, then local snapshot, then mock."""
    return (
        _fetch_from_supabase(tickers)
        or _fetch_from_snapshot(tickers)
        or _fetch_mock(tickers)
    )


# ---------------------------------------------------------------------------
# Normalization helpers — each maps a raw metric into [0, 1] where 1 is
# "better" for the final score. Inverse relationships (P/E, PEG) are flipped.
# ---------------------------------------------------------------------------
def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _norm_growth(raw: dict[str, Any]) -> float:
    rg = float(raw.get("revenue_growth", 0.0))
    eg = float(raw.get("eps_growth", 0.0))
    om = float(raw.get("operating_margin", 0.0))
    # 0% growth -> 0.5, 50%+ growth -> 1.0, -20% -> 0.0
    g = 0.5 + rg * 1.0
    e = 0.5 + eg * 1.0
    m = om * 2.0  # margin of 0.5 -> 1.0
    return _clip(0.4 * g + 0.4 * e + 0.2 * m)


def _norm_valuation(raw: dict[str, Any]) -> float:
    pe = float(raw.get("pe_ratio", 25.0)) or 25.0
    peg = float(raw.get("peg_ratio", 2.0)) or 2.0
    # Cheaper is better. PE 10 -> ~1.0, PE 50 -> ~0.2
    pe_score = _clip(1.0 - (pe - 10.0) / 50.0)
    peg_score = _clip(1.0 - (peg - 1.0) / 3.0)
    return _clip(0.6 * pe_score + 0.4 * peg_score)


def _norm_momentum(raw: dict[str, Any]) -> float:
    rsi = float(raw.get("rsi", 50.0))
    ret = float(raw.get("return_3m", 0.0))
    # RSI sweet spot around 60; anything >80 is overbought.
    if rsi <= 50:
        rsi_score = rsi / 50.0 * 0.6
    elif rsi <= 70:
        rsi_score = 0.6 + (rsi - 50) / 20.0 * 0.4
    else:
        rsi_score = _clip(1.0 - (rsi - 70) / 30.0)
    ret_score = _clip(0.5 + ret * 2.0)
    return _clip(0.5 * rsi_score + 0.5 * ret_score)


def _norm_sentiment(raw: dict[str, Any]) -> float:
    s = float(raw.get("sentiment_score", 0.5))
    return _clip(s)


def build_features(tickers: list[str] | None = None) -> list[dict[str, Any]]:
    """Return a list of ``{ticker, name, features}`` records ready for scoring."""
    stocks = fetch_raw(tickers)
    out: list[dict[str, Any]] = []
    for s in stocks:
        out.append(
            {
                "ticker": s.ticker,
                "name": s.name,
                "features": {
                    "growth": _norm_growth(s.raw),
                    "valuation": _norm_valuation(s.raw),
                    "momentum": _norm_momentum(s.raw),
                    "sentiment": _norm_sentiment(s.raw),
                },
            }
        )
    return out
