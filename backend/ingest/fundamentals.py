"""Fundamental metric fetch from Yahoo Finance.

Returns per-ticker dicts that map directly to the ``stock_features`` table.
All fields are optional; missing values fall back to ``None`` and the feature
engine's normalizers apply sensible defaults.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def fetch_fundamentals(ticker: str) -> dict[str, Any]:
    """Return ``{ticker, name, sector, industry, revenue_growth, eps_growth,
    operating_margin, pe_ratio, peg_ratio}`` (partial allowed)."""
    import yfinance as yf  # lazy import; keeps startup light

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:  # noqa: BLE001
        log.warning("fundamentals fetch failed for %s: %s", ticker, e)
        info = {}

    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "revenue_growth": _safe_float(info.get("revenueGrowth")),
        "eps_growth": _safe_float(info.get("earningsGrowth")),
        "operating_margin": _safe_float(info.get("operatingMargins")),
        "pe_ratio": _safe_float(info.get("trailingPE") or info.get("forwardPE")),
        "peg_ratio": _safe_float(info.get("trailingPegRatio") or info.get("pegRatio")),
    }
