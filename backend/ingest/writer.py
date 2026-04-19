"""Persist ingestion output to Supabase and/or the local snapshot."""
from __future__ import annotations

import logging
from typing import Any

from backend.db.client import get_client
from backend.ingest.snapshot import load, merge, save

log = logging.getLogger(__name__)


def write_local(payload: dict[str, Any]) -> None:
    existing = load()
    merged = merge(existing, payload)
    path = save(merged)
    log.info("snapshot written to %s", path)


def _chunks(rows: list[dict[str, Any]], size: int = 100):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def write_supabase(payload: dict[str, Any]) -> bool:
    """Upsert to Supabase if configured. Returns True on success, False otherwise."""
    client = get_client()
    if client is None:
        return False
    try:
        if payload.get("stocks"):
            for batch in _chunks(payload["stocks"]):
                client.table("stocks").upsert(batch, on_conflict="ticker").execute()
        if payload.get("stock_features"):
            for batch in _chunks(payload["stock_features"]):
                client.table("stock_features").upsert(batch, on_conflict="ticker").execute()
        if payload.get("news"):
            for batch in _chunks(payload["news"]):
                client.table("news").insert(batch).execute()
        if payload.get("embeddings"):
            for batch in _chunks(payload["embeddings"], size=50):
                client.table("embeddings").insert(batch).execute()
        return True
    except Exception as e:  # noqa: BLE001
        log.error("supabase write failed: %s", e)
        return False
