"""LLM layer — explanation only (Ollama chat).

Hard rule: this module NEVER computes scores or rankings. It converts
structured scoring / RAG outputs into human-readable explanations.

This project intentionally keeps chat minimal and local:
  - Provider: Ollama
  - Default model: qwen3.5:4b

If Ollama is unavailable or returns invalid output, callers fall back to
deterministic template text so the app remains demoable.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

import httpx

from backend.config import get_settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _ollama_chat_http() -> httpx.Client:
    s = get_settings()
    return httpx.Client(base_url=s.ollama_url, timeout=120.0)


def _parse_json_object(raw: str) -> dict[str, Any]:
    s = raw.strip()
    if not s:
        return {}
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else {}
    except json.JSONDecodeError:
        pass
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j > i:
        try:
            out = json.loads(s[i : j + 1])
            return out if isinstance(out, dict) else {}
        except json.JSONDecodeError:
            pass
    return {}


def _ollama_chat(
    *,
    messages: list[dict[str, str]],
    temperature: float,
    response_format_json: bool,
) -> str | None:
    s = get_settings()
    payload: dict[str, Any] = {
        "model": s.ollama_chat_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if response_format_json:
        payload["format"] = "json"

    client = _ollama_chat_http()
    try:
        resp = client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        msg = (data.get("message") or {}) if isinstance(data, dict) else {}
        content = msg.get("content")
        return (content or "").strip() if isinstance(content, str) else None
    except Exception as exc:  # noqa: BLE001
        log.warning("ollama chat failed: %s", exc)

    # Retry without structured JSON flag (older servers or strict models).
    if response_format_json:
        try:
            pl2 = dict(payload)
            del pl2["format"]
            resp = client.post("/api/chat", json=pl2)
            resp.raise_for_status()
            data = resp.json()
            msg = (data.get("message") or {}) if isinstance(data, dict) else {}
            content = msg.get("content")
            return (content or "").strip() if isinstance(content, str) else None
        except Exception as exc:  # noqa: BLE001
            log.warning("ollama chat retry failed: %s", exc)

    return None


def chat_json(system: str, user: str, *, temperature: float = 0.0) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    text = _ollama_chat(
        messages=messages,
        temperature=temperature,
        response_format_json=True,
    )
    return _parse_json_object(text or "")


def chat_text(system: str, user: str, *, temperature: float = 0.2) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    text = _ollama_chat(messages=messages, temperature=temperature, response_format_json=False)
    return (text or "").strip()


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
