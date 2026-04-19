"""Headline fetch via yfinance.

yfinance's ``.news`` response shape has shifted a few times. This module is
defensive: it walks the payload and extracts whichever of ``title`` /
``summary`` / ``publisher`` / ``pubDate`` are present.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


def _dig(obj: Any, *keys: str) -> Any:
    """Grab the first non-empty value at any of ``keys`` nested anywhere."""
    if not isinstance(obj, dict):
        return None
    for k in keys:
        if k in obj and obj[k]:
            return obj[k]
    for v in obj.values():
        if isinstance(v, dict):
            found = _dig(v, *keys)
            if found:
                return found
    return None


def _published_at(item: dict[str, Any]) -> str | None:
    ts = _dig(item, "pubDate", "providerPublishTime", "published_at")
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    return str(ts)


def fetch_news(ticker: str, limit: int = 6) -> list[dict[str, Any]]:
    """Return up to ``limit`` normalized news rows for ``ticker``."""
    import yfinance as yf

    try:
        raw = yf.Ticker(ticker).news or []
    except Exception as e:  # noqa: BLE001
        log.warning("news fetch failed for %s: %s", ticker, e)
        return []

    rows: list[dict[str, Any]] = []
    for item in raw[:limit]:
        title = _dig(item, "title")
        summary = _dig(item, "summary", "description")
        publisher = _dig(item, "publisher", "provider")
        link = _dig(item, "canonicalUrl", "clickThroughUrl", "link", "url")
        if isinstance(publisher, dict):
            publisher = _dig(publisher, "displayName", "name")
        if isinstance(link, dict):
            link = _dig(link, "url")
        if not title:
            continue
        body_parts = [p for p in (title, summary) if p]
        rows.append(
            {
                "ticker": ticker.upper(),
                "source": publisher or "yahoo-finance",
                "headline": str(title),
                "body": " — ".join(str(p) for p in body_parts),
                "link": str(link) if link else None,
                "published_at": _published_at(item),
            }
        )
    return rows
