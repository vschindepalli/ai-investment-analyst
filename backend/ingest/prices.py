"""Price-derived metrics: 14-day RSI + 3-month trailing return."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    # Wilder's smoothing
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _return_window(closes: list[float], n_days: int) -> float | None:
    if len(closes) <= n_days:
        return None
    start = closes[-n_days - 1]
    end = closes[-1]
    if start <= 0:
        return None
    return end / start - 1.0


def fetch_price_metrics(ticker: str) -> dict[str, Any]:
    """Return ``{ticker, rsi, return_3m}`` using 6 months of daily closes."""
    import yfinance as yf

    try:
        hist = yf.Ticker(ticker).history(period="6mo", auto_adjust=True)
    except Exception as e:  # noqa: BLE001
        log.warning("price fetch failed for %s: %s", ticker, e)
        hist = None

    if hist is None or hist.empty or "Close" not in hist.columns:
        return {"ticker": ticker.upper(), "rsi": None, "return_3m": None}

    closes = [float(x) for x in hist["Close"].dropna().tolist()]
    return {
        "ticker": ticker.upper(),
        "rsi": _rsi(closes),
        "return_3m": _return_window(closes, 63),  # ~63 trading days = 3 months
    }
