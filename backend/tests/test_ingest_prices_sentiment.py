from __future__ import annotations

from backend.ingest import prices, sentiment


def test_rsi_returns_none_when_insufficient_history() -> None:
    closes = [100.0] * 10
    assert prices._rsi(closes, period=14) is None


def test_rsi_high_on_sustained_uptrend() -> None:
    #enough points for wilder rsi(14); steady gains -> rsi near 100.
    closes = [100.0 + i for i in range(30)]
    rsi = prices._rsi(closes, period=14)
    assert rsi is not None
    assert rsi > 90.0


def test_return_window_computes_pct_change() -> None:
    closes = [100.0, 110.0]
    ret = prices._return_window(closes, n_days=1)
    assert ret is not None
    assert abs(ret - 0.10) < 1e-9


def test_return_window_returns_none_for_short_series() -> None:
    assert prices._return_window([100.0], n_days=63) is None


def test_score_text_empty_is_neutral() -> None:
    assert sentiment.score_text("") == 0.5
    assert sentiment.score_text("   ") == 0.5


def test_score_text_maps_positive_and_negative_to_unit_interval() -> None:
    positive = sentiment.score_text("Record earnings beat and strong growth outlook")
    negative = sentiment.score_text("Massive loss, layoffs, and bankruptcy risk")
    assert 0.0 <= positive <= 1.0
    assert 0.0 <= negative <= 1.0
    assert positive > 0.5
    assert negative < 0.5


def test_aggregate_ticker_sentiment_empty_returns_none() -> None:
    assert sentiment.aggregate_ticker_sentiment([]) is None


def test_aggregate_ticker_sentiment_averages_headlines() -> None:
    rows = [
        {"headline": "Record earnings beat and strong growth outlook"},
        {"headline": "Massive loss, layoffs, and bankruptcy risk"},
    ]
    avg = sentiment.aggregate_ticker_sentiment(rows)
    assert avg is not None
    assert 0.0 <= avg <= 1.0
    assert abs(avg - 0.5) < 0.35
