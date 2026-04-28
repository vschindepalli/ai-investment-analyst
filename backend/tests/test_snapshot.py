from __future__ import annotations

from backend.ingest import snapshot


def test_merge_upserts_stocks_and_features_by_ticker() -> None:
    existing = {
        "stocks": [{"ticker": "NVDA", "name": "NVIDIA Old"}],
        "stock_features": [{"ticker": "NVDA", "growth": 0.4}],
        "news": [],
        "embeddings": [],
    }
    fresh = {
        "stocks": [
            {"ticker": "NVDA", "name": "NVIDIA Corporation"},
            {"ticker": "AMD", "name": "Advanced Micro Devices"},
        ],
        "stock_features": [
            {"ticker": "NVDA", "growth": 0.9},
            {"ticker": "AMD", "growth": 0.7},
        ],
    }

    out = snapshot.merge(existing, fresh)

    assert out["stocks"] == [
        {"ticker": "NVDA", "name": "NVIDIA Corporation"},
        {"ticker": "AMD", "name": "Advanced Micro Devices"},
    ]
    assert out["stock_features"] == [
        {"ticker": "NVDA", "growth": 0.9},
        {"ticker": "AMD", "growth": 0.7},
    ]


def test_merge_appends_and_dedups_news_and_embeddings() -> None:
    existing = {
        "news": [{"ticker": "NVDA", "headline": "AI demand strong"}],
        "embeddings": [{"ticker": "NVDA", "text": "AI demand strong"}],
    }
    fresh = {
        "news": [
            {"ticker": "NVDA", "headline": "AI demand strong"},
            {"ticker": "NVDA", "headline": "Margins expanded"},
        ],
        "embeddings": [
            {"ticker": "NVDA", "text": "AI demand strong"},
            {"ticker": "NVDA", "text": "Datacenter outlook raised"},
        ],
    }

    out = snapshot.merge(existing, fresh)

    assert out["news"] == [
        {"ticker": "NVDA", "headline": "AI demand strong"},
        {"ticker": "NVDA", "headline": "Margins expanded"},
    ]
    assert out["embeddings"] == [
        {"ticker": "NVDA", "text": "AI demand strong"},
        {"ticker": "NVDA", "text": "Datacenter outlook raised"},
    ]


def test_load_save_roundtrip_uses_snapshot_path(tmp_path, monkeypatch) -> None:
    test_path = tmp_path / "snapshot.json"
    monkeypatch.setattr(snapshot, "SNAPSHOT_PATH", test_path)

    before = snapshot.load()
    assert before["stocks"] == []
    assert before["news"] == []

    data = {
        "stocks": [{"ticker": "AAPL", "name": "Apple Inc."}],
        "stock_features": [{"ticker": "AAPL", "growth": 0.6}],
        "news": [{"ticker": "AAPL", "headline": "Product launch"}],
        "embeddings": [{"ticker": "AAPL", "text": "Product launch"}],
    }
    saved_path = snapshot.save(data)
    loaded = snapshot.load()

    assert saved_path == test_path
    assert loaded["stocks"][0]["ticker"] == "AAPL"
    assert loaded["generated_at"] is not None
