"""Intent classifier.

Determines ``{intent, tickers}`` from a raw user query. Uses the LLM for the
intent label when available, then layers a regex-based ticker extractor on
top so ticker capture is robust even without an LLM.
"""
from __future__ import annotations

import re
from typing import Any

from backend.services.llm import chat_json

_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")

# Common English uppercase tokens that look like tickers but aren't.
_STOPWORDS = {
    "I", "A", "AN", "THE", "AND", "OR", "VS", "VERSUS", "IS", "IT", "OF",
    "TO", "IN", "ON", "FOR", "WITH", "BETTER", "BEST", "TOP", "VS.", "AI",
    "ETF", "USD", "CEO", "IPO", "PE", "PEG", "RSI",
}

# Light company-name → ticker map to help with natural language queries.
_NAME_TO_TICKER = {
    "NVIDIA": "NVDA", "APPLE": "AAPL", "MICROSOFT": "MSFT",
    "GOOGLE": "GOOGL", "ALPHABET": "GOOGL", "META": "META",
    "FACEBOOK": "META", "TESLA": "TSLA", "AMAZON": "AMZN",
}


def _extract_tickers(query: str) -> list[str]:
    upper = query.upper()
    found: list[str] = []
    for name, tkr in _NAME_TO_TICKER.items():
        if name in upper and tkr not in found:
            found.append(tkr)
    for m in _TICKER_RE.findall(query):
        if m in _STOPWORDS:
            continue
        if m not in found:
            found.append(m)
    return found


def _heuristic_intent(query: str, tickers: list[str]) -> str:
    q = query.lower()
    compare_cues = (" vs ", " versus ", "compare", "or better", "better than")
    if any(c in q for c in compare_cues) or len(tickers) >= 2:
        return "COMPARISON"
    research_cues = (
        "why", "how", "what", "news", "earnings", "filing", "risk", "explain",
        "tell me about",
    )
    if any(c in q for c in research_cues):
        return "RESEARCH"
    return "SCREENING"


_SYSTEM = (
    "You classify investment queries. Return strict JSON with keys 'intent' "
    "(one of SCREENING, RESEARCH, COMPARISON) and 'tickers' (array of "
    "uppercase stock symbols mentioned)."
)


def classify(query: str) -> dict[str, Any]:
    tickers = _extract_tickers(query)

    llm_out = chat_json(_SYSTEM, query)
    intent = (llm_out.get("intent") or "").upper() if llm_out else ""
    if intent not in {"SCREENING", "RESEARCH", "COMPARISON"}:
        intent = _heuristic_intent(query, tickers)

    llm_tickers = llm_out.get("tickers") or []
    if isinstance(llm_tickers, list):
        for t in llm_tickers:
            t = str(t).upper().strip()
            if t and t not in tickers:
                tickers.append(t)

    return {"intent": intent, "tickers": tickers}
