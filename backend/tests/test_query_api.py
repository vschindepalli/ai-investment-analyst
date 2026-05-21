"""Contract tests for POST /api/query.

Validates response shape and value ranges without calling a live LLM.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app

VALID_INTENTS = {"SCREENING", "RESEARCH", "COMPARISON"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def stub_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    #keep tests fast and deterministic; heuristics still drive intent.
    noop_json = lambda *_args, **_kwargs: {}
    stub_text = lambda *_args, **_kwargs: "contract test explanation"
    monkeypatch.setattr("backend.services.llm.chat_json", noop_json)
    monkeypatch.setattr("backend.orchestrator.classifier.chat_json", noop_json)
    monkeypatch.setattr("backend.services.llm.chat_text", stub_text)


def _assert_feature_ranges(features: dict) -> None:
    for key in ("growth", "valuation", "momentum", "sentiment"):
        assert key in features
        val = features[key]
        assert isinstance(val, (int, float))
        assert 0.0 <= float(val) <= 1.0


def _assert_query_contract(data: dict, *, expected_intent: str | None = None) -> None:
    assert data["intent"] in VALID_INTENTS
    if expected_intent is not None:
        assert data["intent"] == expected_intent

    assert isinstance(data["tickers"], list)
    assert isinstance(data["results"], list)
    assert isinstance(data["context"], list)
    assert isinstance(data["explanation"], str) and data["explanation"]
    assert isinstance(data["confidence"], (int, float))
    assert 0.0 <= float(data["confidence"]) <= 1.0

    meta = data["meta"]
    assert isinstance(meta, dict)
    assert meta.get("llm", {}).get("provider") == "ollama"
    assert isinstance(meta.get("llm", {}).get("ollama_chat_model"), str)
    assert meta.get("llm", {}).get("explanation_source") == "ollama"

    for row in data["results"]:
        assert isinstance(row["ticker"], str) and row["ticker"]
        assert isinstance(row["score"], (int, float))
        _assert_feature_ranges(row["features"])

    for chunk in data["context"]:
        assert isinstance(chunk["source"], str)
        assert isinstance(chunk["text"], str)
        if chunk.get("similarity") is not None:
            #cosine similarity is in [-1, 1], not always non-negative.
            sim = float(chunk["similarity"])
            assert -1.0 <= sim <= 1.0


def test_query_screening_contract(client: TestClient) -> None:
    resp = client.post(
        "/api/query",
        json={"query": "top AI growth stocks", "top_k": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    _assert_query_contract(data, expected_intent="SCREENING")
    assert len(data["results"]) <= 3
    assert len(data["results"]) > 0


def test_query_research_contract(client: TestClient) -> None:
    resp = client.post(
        "/api/query",
        json={"query": "news and risk for NVDA", "top_k": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    _assert_query_contract(data, expected_intent="RESEARCH")
    assert data["results"] == []
    assert "NVDA" in data["tickers"]


def test_query_comparison_contract(client: TestClient) -> None:
    resp = client.post(
        "/api/query",
        json={"query": "compare NVDA vs AAPL", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    _assert_query_contract(data, expected_intent="COMPARISON")
    assert len(data["tickers"]) >= 2
    assert len(data["results"]) >= 2


def test_query_rejects_empty_body(client: TestClient) -> None:
    resp = client.post("/api/query", json={"query": ""})
    assert resp.status_code == 422
