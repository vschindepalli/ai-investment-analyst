"""Ingestion CLI.

Usage:

    # Full run over the default universe:
    python -m backend.ingest.run --refresh all

    # Only fundamentals for a specific ticker:
    python -m backend.ingest.run --refresh fundamentals --tickers NVDA

    # Dry-run (no network, writes a deterministic snapshot from the in-repo
    # mock universe — useful for CI / offline demos):
    python -m backend.ingest.run --refresh all --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any

from backend.ingest.universe import DEFAULT_UNIVERSE, default_tickers, sector_for
from backend.ingest.writer import write_local, write_supabase

log = logging.getLogger("ingest")

REFRESH_CHOICES = ["all", "fundamentals", "prices", "news"]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Populate stock features / news / embeddings.")
    p.add_argument(
        "--refresh",
        choices=REFRESH_CHOICES,
        default="all",
        help="which pipeline stages to run (default: all)",
    )
    p.add_argument(
        "--tickers",
        default=None,
        help="comma-separated ticker list (default: built-in universe)",
    )
    p.add_argument(
        "--limit-news",
        type=int,
        default=6,
        help="max news items per ticker (default: 6)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="skip all network calls; use the in-repo mock universe",
    )
    p.add_argument(
        "--no-supabase",
        action="store_true",
        help="only write the local snapshot (default: also upsert to Supabase if configured)",
    )
    p.add_argument("--verbose", "-v", action="count", default=0)
    return p.parse_args(argv)


def _dry_run_payload(tickers: list[str]) -> dict[str, Any]:
    """Produce a deterministic snapshot from the existing mock universe.

    Exercises the write path end-to-end without hitting Yahoo Finance.
    """
    from backend.features.builder import _MOCK_UNIVERSE

    wanted = {t.upper() for t in tickers}
    universe = [u for u in _MOCK_UNIVERSE if u["ticker"] in wanted] or _MOCK_UNIVERSE

    stocks = [
        {
            "ticker": u["ticker"],
            "name": u["name"],
            "sector": sector_for(u["ticker"]),
            "industry": None,
        }
        for u in universe
    ]
    stock_features = [
        {
            "ticker": u["ticker"],
            "revenue_growth": u["revenue_growth"],
            "eps_growth": u["eps_growth"],
            "operating_margin": u["operating_margin"],
            "pe_ratio": u["pe_ratio"],
            "peg_ratio": u["peg_ratio"],
            "rsi": u["rsi"],
            "return_3m": u["return_3m"],
            "sentiment_score": u["sentiment_score"],
        }
        for u in universe
    ]
    return {
        "stocks": stocks,
        "stock_features": stock_features,
        "news": [],
        "embeddings": [],
    }


def _run_for_ticker(
    ticker: str, do_fundamentals: bool, do_prices: bool, do_news: bool, limit_news: int
) -> dict[str, Any]:
    from backend.ingest.embed import build_embedding_rows
    from backend.ingest.fundamentals import fetch_fundamentals
    from backend.ingest.news import fetch_news
    from backend.ingest.prices import fetch_price_metrics
    from backend.ingest.sentiment import aggregate_ticker_sentiment

    stock: dict[str, Any] = {"ticker": ticker}
    feature: dict[str, Any] = {"ticker": ticker}
    news_rows: list[dict[str, Any]] = []
    embedding_rows: list[dict[str, Any]] = []

    if do_fundamentals:
        f = fetch_fundamentals(ticker)
        stock.update(
            {
                "name": f.get("name"),
                "sector": f.get("sector") or sector_for(ticker),
                "industry": f.get("industry"),
            }
        )
        for k in ("revenue_growth", "eps_growth", "operating_margin", "pe_ratio", "peg_ratio"):
            feature[k] = f.get(k)
    else:
        stock["sector"] = sector_for(ticker)

    if do_prices:
        p = fetch_price_metrics(ticker)
        feature["rsi"] = p.get("rsi")
        feature["return_3m"] = p.get("return_3m")

    if do_news:
        news_rows = fetch_news(ticker, limit=limit_news)
        s = aggregate_ticker_sentiment(news_rows)
        if s is not None:
            feature["sentiment_score"] = s
        embedding_rows = build_embedding_rows(news_rows)

    return {
        "stocks": [stock],
        "stock_features": [feature],
        "news": news_rows,
        "embeddings": embedding_rows,
    }


def _merge_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, list[dict[str, Any]]] = {
        "stocks": [],
        "stock_features": [],
        "news": [],
        "embeddings": [],
    }
    for p in payloads:
        for k in out:
            out[k].extend(p.get(k, []))
    return out


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = default_tickers()
    log.info("ingesting %d tickers (refresh=%s, dry_run=%s)", len(tickers), args.refresh, args.dry_run)

    if args.dry_run:
        payload = _dry_run_payload(tickers)
    else:
        do_fund = args.refresh in ("all", "fundamentals")
        do_px = args.refresh in ("all", "prices")
        do_news = args.refresh in ("all", "news")

        payloads: list[dict[str, Any]] = []
        for i, t in enumerate(tickers, start=1):
            try:
                log.info("[%d/%d] %s", i, len(tickers), t)
                payloads.append(_run_for_ticker(t, do_fund, do_px, do_news, args.limit_news))
            except Exception as e:  # noqa: BLE001
                log.error("ticker %s failed: %s", t, e)
        payload = _merge_payloads(payloads)

    log.info(
        "built payload: %d stocks, %d features, %d news, %d embeddings",
        len(payload["stocks"]),
        len(payload["stock_features"]),
        len(payload["news"]),
        len(payload["embeddings"]),
    )

    write_local(payload)
    if not args.no_supabase:
        ok = write_supabase(payload)
        log.info("supabase write: %s", "ok" if ok else "skipped (not configured or failed)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
