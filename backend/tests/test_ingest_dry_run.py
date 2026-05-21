"""Contract tests for offline ingestion (--dry-run)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.ingest import run as ingest_run
from backend.ingest import snapshot


REQUIRED_STOCK_KEYS = {"ticker", "name", "sector"}
REQUIRED_FEATURE_KEYS = {
    "ticker",
    "revenue_growth",
    "eps_growth",
    "operating_margin",
    "pe_ratio",
    "peg_ratio",
    "rsi",
    "return_3m",
    "sentiment_score",
}


def _assert_snapshot_contract(data: dict, *, expected_tickers: set[str]) -> None:
    assert isinstance(data.get("generated_at"), str) and data["generated_at"]
    for key in ("stocks", "stock_features", "news", "embeddings"):
        assert isinstance(data[key], list)

    tickers = {s["ticker"] for s in data["stocks"]}
    assert tickers == expected_tickers
    assert len(data["stock_features"]) == len(expected_tickers)
    assert {f["ticker"] for f in data["stock_features"]} == expected_tickers

    for row in data["stocks"]:
        assert REQUIRED_STOCK_KEYS <= row.keys()
        assert isinstance(row["ticker"], str) and row["ticker"]

    for row in data["stock_features"]:
        assert REQUIRED_FEATURE_KEYS <= row.keys()
        for metric in (
            "revenue_growth",
            "eps_growth",
            "operating_margin",
            "pe_ratio",
            "peg_ratio",
            "rsi",
            "return_3m",
            "sentiment_score",
        ):
            val = row[metric]
            assert isinstance(val, (int, float))


def test_dry_run_payload_contract() -> None:
    payload = ingest_run._dry_run_payload(["NVDA", "AMD"])

    assert set(payload.keys()) >= {"stocks", "stock_features", "news", "embeddings"}
    _assert_snapshot_contract(
        {**payload, "generated_at": "stub"},
        expected_tickers={"NVDA", "AMD"},
    )
    assert payload["news"] == []
    assert payload["embeddings"] == []


def test_main_dry_run_writes_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    snap_file = tmp_path / "snapshot.json"
    monkeypatch.setattr(snapshot, "SNAPSHOT_PATH", snap_file)
    monkeypatch.setattr("backend.ingest.writer.write_supabase", lambda _payload: False)

    code = ingest_run.main(
        [
            "--dry-run",
            "--refresh",
            "all",
            "--tickers",
            "NVDA,AMD",
            "--no-supabase",
        ]
    )

    assert code == 0
    assert snap_file.exists()
    data = json.loads(snap_file.read_text())
    _assert_snapshot_contract(data, expected_tickers={"NVDA", "AMD"})
