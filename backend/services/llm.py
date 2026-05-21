"""LLM layer — explanation only (Ollama chat).

Hard rule: this module NEVER computes scores or rankings. It converts
structured scoring / RAG outputs into human-readable explanations.

Provider: local Ollama (`OLLAMA_CHAT_MODEL`). On timeout or failure, callers
use deterministic templates so the API stays responsive.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from backend.config import get_settings

log = logging.getLogger(__name__)

_BRIEF = (
    "Reply in at most 4 short sentences. Output only the final answer — "
    "no reasoning, planning, or chain-of-thought."
)


def strip_reasoning(text: str) -> str:
    """Drop model reasoning traces; keep user-facing answer text only."""
    s = text.strip()
    if not s:
        return ""

    s = re.sub(r"(?is)<think>.*?</think>\s*", "", s).strip()
    s = re.sub(r"(?is)<thinking>.*?</thinking>\s*", "", s).strip()

    #drop common fenced reasoning prefixes.
    s = re.sub(
        r"^```(?:think|thinking|reasoning)?\s*\n[\s\S]*?```\s*",
        "",
        s,
        count=1,
        flags=re.IGNORECASE,
    ).strip()

    if re.match(r"(?i)^thinking\s*:", s):
        parts = re.split(r"\n\s*\n", s, maxsplit=1)
        if len(parts) > 1:
            s = parts[1].strip()

    for marker in (
        r"(?i)\*\*final answer\*\*:?\s*",
        r"(?i)\*\*answer\*\*:?\s*",
        r"(?i)^answer:\s*",
    ):
        m = re.search(marker, s)
        if m:
            s = s[m.end() :].strip()
            break

    return s.strip()

#surfaced in api meta so you can see ollama vs template per request.
_last_explanation_source: str = "none"


def explanation_source() -> str:
    return _last_explanation_source


def _ollama_client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(base_url=s.ollama_url, timeout=s.ollama_chat_timeout)


def _ollama_options(temperature: float) -> dict[str, Any]:
    s = get_settings()
    return {
        "temperature": temperature,
        "num_predict": s.ollama_chat_num_predict,
    }


def _parse_json_object(raw: str) -> dict[str, Any]:
    #some models wrap json in markdown fences; strip that first.
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


def _trim_ranked(ranked: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    slim: list[dict[str, Any]] = []
    for row in ranked[:limit]:
        slim.append(
            {
                "ticker": row.get("ticker"),
                "score": row.get("score"),
                "features": row.get("features"),
                "rationale": row.get("rationale"),
            }
        )
    return slim


def _trim_chunks(chunks: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    slim: list[dict[str, Any]] = []
    for c in chunks[:limit]:
        text = (c.get("text") or "")[:280]
        slim.append(
            {
                "source": c.get("source"),
                "ticker": c.get("ticker"),
                "text": text,
                "similarity": c.get("similarity"),
            }
        )
    return slim


def _extract_message_content(data: dict[str, Any]) -> str | None:
    msg = data.get("message") or {}
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return strip_reasoning(content)
    return None


def _ollama_chat(
    *,
    messages: list[dict[str, str]],
    temperature: float,
    response_format_json: bool,
) -> str | None:
    s = get_settings()
    if not s.ollama_chat_enabled:
        return None

    payload: dict[str, Any] = {
        "model": s.ollama_chat_model,
        "messages": messages,
        "stream": False,
        "think": s.ollama_chat_think,
        "options": _ollama_options(temperature),
    }
    if response_format_json:
        payload["format"] = "json"

    client = _ollama_client()
    try:
        resp = client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            return _extract_message_content(data)
    except Exception as exc:  # noqa: BLE001
        log.warning("ollama chat failed: %s", exc)

    if response_format_json:
        try:
            pl2 = dict(payload)
            del pl2["format"]
            resp = client.post("/api/chat", json=pl2)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return _extract_message_content(data)
        except Exception as exc:  # noqa: BLE001
            log.warning("ollama chat retry failed: %s", exc)

    return None


def chat_json(system: str, user: str, *, temperature: float = 0.0) -> dict[str, Any]:
    messages = [
        {"role": "system", "content": f"{system} {_BRIEF}"},
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
        {"role": "system", "content": f"{system} {_BRIEF}"},
        {"role": "user", "content": user},
    ]
    text = _ollama_chat(messages=messages, temperature=temperature, response_format_json=False)
    if text:
        log.info(
            "ollama chat ok model=%s chars=%d",
            get_settings().ollama_chat_model,
            len(text),
        )
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
    global _last_explanation_source
    if not ranked:
        _last_explanation_source = "none"
        return "No stocks matched the scoring criteria."
    payload = json.dumps(
        {"query": query, "ranked": _trim_ranked(ranked)},
        default=float,
    )
    text = chat_text(SCREENING_SYSTEM, payload)
    if text:
        _last_explanation_source = "ollama"
        return text
    _last_explanation_source = (
        "disabled" if not get_settings().ollama_chat_enabled else "template"
    )
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
    global _last_explanation_source
    if not chunks:
        _last_explanation_source = "none"
        return "No relevant context was retrieved for this query."
    payload = json.dumps(
        {"query": query, "context": _trim_chunks(chunks)},
        default=float,
    )
    text = chat_text(RESEARCH_SYSTEM, payload)
    if text:
        _last_explanation_source = "ollama"
        return text
    _last_explanation_source = (
        "disabled" if not get_settings().ollama_chat_enabled else "template"
    )
    snippets = " ".join(c["text"][:180] for c in chunks[:3])
    return f"Context summary: {snippets}"


def explain_comparison(
    query: str,
    ranked: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> str:
    global _last_explanation_source
    payload = json.dumps(
        {
            "query": query,
            "ranked": _trim_ranked(ranked, limit=2),
            "context": _trim_chunks(chunks, limit=4),
        },
        default=float,
    )
    text = chat_text(COMPARISON_SYSTEM, payload)
    if text:
        _last_explanation_source = "ollama"
        return text
    _last_explanation_source = (
        "disabled" if not get_settings().ollama_chat_enabled else "template"
    )
    if len(ranked) >= 2:
        a, b = ranked[0], ranked[1]
        return (
            f"{a['ticker']} scores {a['score']:.2f} vs {b['ticker']} at "
            f"{b['score']:.2f}. Leader's edge comes from its feature mix "
            f"(growth/valuation/momentum/sentiment)."
        )
    return "Insufficient data to compare."
