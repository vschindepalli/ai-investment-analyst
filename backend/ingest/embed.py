"""Build embedding rows for news items.

Reuses ``services.embeddings.embed`` so the same OpenAI-or-hash fallback logic
powers both live retrieval and the ingest pipeline.
"""
from __future__ import annotations

from typing import Any

from backend.services.embeddings import embed_many


def build_embedding_rows(news_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[tuple[dict[str, Any], str]] = []
    for n in news_rows:
        text = (n.get("body") or n.get("headline") or "").strip()
        if not text:
            continue
        prepared.append((n, text))
    if not prepared:
        return []
    vectors = embed_many(text for _, text in prepared)
    return [
        {
            "ticker": n.get("ticker"),
            "source": n.get("source") or "news",
            "text": text,
            "embedding": vec,
        }
        for (n, text), vec in zip(prepared, vectors)
    ]
