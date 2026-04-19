"""LLM layer — explanation only.

Hard rule: this module NEVER computes scores or rankings. It converts
structured scoring / RAG outputs into human-readable explanations.

When no ``OPENAI_API_KEY`` is configured we fall back to a deterministic
template so the system remains fully demoable offline.
"""
from __future__ import annotations

import json
from typing import Any

from backend.config import get_settings


def _openai_client():
    settings = get_settings()
    if not settings.has_openai:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def chat_json(system: str, user: str, *, temperature: float = 0.0) -> dict[str, Any]:
    """Ask the LLM for a JSON object. Returns {} on any failure."""
    client = _openai_client()
    if client is None:
        return {}
    settings = get_settings()
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        return {}


def chat_text(system: str, user: str, *, temperature: float = 0.2) -> str:
    client = _openai_client()
    if client is None:
        return ""
    settings = get_settings()
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return ""


SCREENING_SYSTEM = (
    "You are an equity research assistant. You interpret numeric scores that "
    "have already been computed by a deterministic model. Never recompute or "
    "invent numbers — only explain them. Be concise, factual, and flag risks."
)

RESEARCH_SYSTEM = (
    "You are an equity research assistant. Summarize the retrieved context "
    "to answer the user's question. Cite tickers and sources inline. If the "
    "context is insufficient, say so explicitly."
)

COMPARISON_SYSTEM = (
    "You are an equity research assistant. Compare the two tickers using the "
    "provided scores and context. Highlight relative strengths, weaknesses, "
    "and risks. Do not recompute numbers."
)


def explain_screening(query: str, ranked: list[dict[str, Any]]) -> str:
    if not ranked:
        return "No stocks matched the scoring criteria."
    payload = json.dumps({"query": query, "ranked": ranked}, default=float)
    text = chat_text(SCREENING_SYSTEM, payload)
    if text:
        return text
    top = ranked[0]
    feats = top.get("features", {})
    return (
        f"Top pick: {top['ticker']} (score {top['score']:.2f}). "
        f"Growth {feats.get('growth', 0):.2f}, valuation {feats.get('valuation', 0):.2f}, "
        f"momentum {feats.get('momentum', 0):.2f}, sentiment {feats.get('sentiment', 0):.2f}. "
        f"Other candidates: "
        + ", ".join(f"{r['ticker']} ({r['score']:.2f})" for r in ranked[1:4])
        + "."
    )


def explain_research(query: str, chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "No relevant context was retrieved for this query."
    payload = json.dumps({"query": query, "context": chunks}, default=float)
    text = chat_text(RESEARCH_SYSTEM, payload)
    if text:
        return text
    snippets = " ".join(c["text"][:180] for c in chunks[:3])
    return f"Context summary: {snippets}"


def explain_comparison(
    query: str,
    ranked: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> str:
    payload = json.dumps(
        {"query": query, "ranked": ranked, "context": chunks}, default=float
    )
    text = chat_text(COMPARISON_SYSTEM, payload)
    if text:
        return text
    if len(ranked) >= 2:
        a, b = ranked[0], ranked[1]
        return (
            f"{a['ticker']} scores {a['score']:.2f} vs {b['ticker']} at "
            f"{b['score']:.2f}. Leader's edge comes from its feature mix "
            f"(growth/valuation/momentum/sentiment)."
        )
    return "Insufficient data to compare."
