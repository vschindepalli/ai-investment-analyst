from __future__ import annotations

from backend.tools import screener


def test_compute_score_uses_fixed_weights() -> None:
    features = {
        "growth": 1.0,
        "valuation": 0.4,
        "momentum": 0.2,
        "sentiment": 0.6,
    }

    score = screener.compute_score(features)

    # 0.35*1.0 + 0.25*0.4 + 0.25*0.2 + 0.15*0.6
    assert score == 0.59


def test_rationale_surfaces_best_and_worst_feature() -> None:
    features = {
        "growth": 0.82,
        "valuation": 0.30,
        "momentum": 0.77,
        "sentiment": 0.68,
    }

    text = screener._rationale(features)

    assert "Driven by growth (0.82)" in text
    assert "weakest on valuation (0.30)" in text


def test_rank_stocks_sorts_desc_and_respects_top_k(monkeypatch) -> None:
    def _fake_build_features(_tickers):
        return [
            {
                "ticker": "AAA",
                "name": "AAA Co",
                "features": {
                    "growth": 0.6,
                    "valuation": 0.6,
                    "momentum": 0.6,
                    "sentiment": 0.6,
                },
            },
            {
                "ticker": "BBB",
                "name": "BBB Co",
                "features": {
                    "growth": 0.95,
                    "valuation": 0.8,
                    "momentum": 0.85,
                    "sentiment": 0.7,
                },
            },
            {
                "ticker": "CCC",
                "name": "CCC Co",
                "features": {
                    "growth": 0.2,
                    "valuation": 0.4,
                    "momentum": 0.3,
                    "sentiment": 0.4,
                },
            },
        ]

    monkeypatch.setattr(screener, "build_features", _fake_build_features)

    ranked = screener.rank_stocks(top_k=2)

    assert len(ranked) == 2
    assert ranked[0]["ticker"] == "BBB"
    assert ranked[1]["ticker"] == "AAA"
    assert ranked[0]["score"] >= ranked[1]["score"]
    assert isinstance(ranked[0]["rationale"], str) and ranked[0]["rationale"]
