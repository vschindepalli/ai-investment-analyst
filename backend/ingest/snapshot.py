"""Local JSON snapshot store.

A single file at ``backend/data/snapshot.json`` that mirrors the four Supabase
tables (stocks / stock_features / news / embeddings). Used as the canonical
artifact of an ingestion run and as a drop-in source for the feature engine
and RAG layer when Supabase is not configured.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "snapshot.json"

EMPTY: dict[str, Any] = {
    "generated_at": None,
    "stocks": [],
    "stock_features": [],
    "news": [],
    "embeddings": [],
}


def load() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        return {**EMPTY}
    try:
        with SNAPSHOT_PATH.open() as f:
            return json.load(f)
    except Exception:
        #corrupt snapshot should not block api boot; fall back to empty.
        return {**EMPTY}


def save(snapshot: dict[str, Any]) -> Path:
    snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    #write temp then replace for atomic-ish updates.
    tmp = SNAPSHOT_PATH.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    tmp.replace(SNAPSHOT_PATH)
    return SNAPSHOT_PATH


def merge(existing: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """Merge ``fresh`` into ``existing`` using ticker-based upsert semantics.

    stocks / stock_features: upsert keyed on ``ticker``.
    news / embeddings: append, de-duplicated on (ticker, text).
    """
    out = {**EMPTY, **existing}

    def upsert(key: str, rows: list[dict[str, Any]], pk: str) -> None:
        index = {r[pk]: i for i, r in enumerate(out.get(key) or [])}
        current = list(out.get(key) or [])
        for r in rows:
            if r.get(pk) is None:
                continue
            if r[pk] in index:
                current[index[r[pk]]] = {**current[index[r[pk]]], **r}
            else:
                index[r[pk]] = len(current)
                current.append(r)
        out[key] = current

    upsert("stocks", fresh.get("stocks", []), "ticker")
    upsert("stock_features", fresh.get("stock_features", []), "ticker")

    def append_dedup(key: str, rows: list[dict[str, Any]]) -> None:
        #news uses headline while embeddings use text, so normalize both here.
        seen = {(r.get("ticker"), r.get("text") or r.get("headline")) for r in out.get(key) or []}
        current = list(out.get(key) or [])
        for r in rows:
            k = (r.get("ticker"), r.get("text") or r.get("headline"))
            if k in seen:
                continue
            seen.add(k)
            current.append(r)
        out[key] = current

    append_dedup("news", fresh.get("news", []))
    append_dedup("embeddings", fresh.get("embeddings", []))
    return out
