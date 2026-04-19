"""Embedding service — multi-provider.

Providers:
  - ``ollama``  (default): local Ollama server, default model ``embeddinggemma`` (768d)
  - ``openai``: OpenAI API, default model ``text-embedding-3-small`` (1536d)
  - ``hash``:  deterministic offline fallback (no network dep)

Selection is driven by ``EMBEDDING_PROVIDER``. The *active provider's
dimension* is authoritative for the whole snapshot — we never mix dims,
because that silently breaks cosine similarity. If the selected provider
fails at call time we fall back to the hash generator **at the active
provider's dim**, so stored and query vectors stay comparable.
"""
from __future__ import annotations

import hashlib
import logging
import math
from functools import lru_cache
from typing import Iterable

import httpx

from backend.config import get_settings

log = logging.getLogger(__name__)

# Per-provider output dimensions. Keep in sync with Supabase schema.
PROVIDER_DIMS: dict[str, int] = {
    "ollama": 768,   # embeddinggemma default
    "openai": 1536,  # text-embedding-3-small
    "hash": 768,     # match Ollama so mixed dev setups stay comparable
}


def active_provider() -> str:
    p = get_settings().embedding_provider
    if p not in PROVIDER_DIMS:
        log.warning("unknown EMBEDDING_PROVIDER=%s, falling back to 'hash'", p)
        return "hash"
    return p


def embed_dim() -> int:
    return PROVIDER_DIMS[active_provider()]


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _ollama_client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(base_url=s.ollama_url, timeout=30.0)


def _ollama_embed_batch(texts: list[str]) -> list[list[float]] | None:
    """Embed a batch in a single HTTP call. Returns None on failure."""
    s = get_settings()
    try:
        resp = _ollama_client().post(
            "/api/embed",
            json={"model": s.ollama_embed_model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        vectors = data.get("embeddings")
        if not vectors or len(vectors) != len(texts):
            return None
        return [list(map(float, v)) for v in vectors]
    except Exception as e:  # noqa: BLE001
        log.warning("ollama embed failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------
def _openai_embed_batch(texts: list[str]) -> list[list[float]] | None:
    s = get_settings()
    if not s.has_openai:
        return None
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=s.openai_api_key)
        resp = client.embeddings.create(model=s.openai_embed_model, input=texts)
        return [list(map(float, d.embedding)) for d in resp.data]
    except Exception as e:  # noqa: BLE001
        log.warning("openai embed failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Hash fallback (offline-safe)
# ---------------------------------------------------------------------------
def _hash_embed(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for token in text.lower().split():
        h = hashlib.md5(token.encode()).digest()
        for i in range(0, len(h), 2):
            idx = ((h[i] << 8) | h[i + 1]) % dim
            vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def embed(text: str) -> list[float]:
    """Embed a single string with the active provider (or hash fallback)."""
    return embed_many([text])[0]


def embed_many(texts: Iterable[str]) -> list[list[float]]:
    """Batch-embed; preserves input order. Falls back to hash at the
    active provider's dim on any provider failure."""
    items = list(texts)
    if not items:
        return []

    provider = active_provider()
    dim = PROVIDER_DIMS[provider]

    result: list[list[float]] | None = None
    if provider == "ollama":
        result = _ollama_embed_batch(items)
    elif provider == "openai":
        result = _openai_embed_batch(items)

    if result is None:
        result = [_hash_embed(t, dim) for t in items]
    return result


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
