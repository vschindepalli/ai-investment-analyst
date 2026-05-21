from __future__ import annotations

from backend.orchestrator import classifier


def test_extract_tickers_from_names_and_symbols() -> None:
    tickers = classifier._extract_tickers("compare NVIDIA vs AMD and Apple")

    assert "NVDA" in tickers
    assert "AMD" in tickers
    assert "AAPL" in tickers


def test_extract_tickers_ignores_stopwords() -> None:
    tickers = classifier._extract_tickers("TOP AI ETF VS THE BEST")

    assert tickers == []


def test_heuristic_intent_for_comparison_with_two_tickers() -> None:
    intent = classifier._heuristic_intent("What do you think?", ["NVDA", "AMD"])

    assert intent == "COMPARISON"


def test_heuristic_intent_for_research_cues() -> None:
    intent = classifier._heuristic_intent("news and risk for NVDA", ["NVDA"])

    assert intent == "RESEARCH"


def test_heuristic_intent_for_screening_cues() -> None:
    intent = classifier._heuristic_intent("top AI growth stocks", [])

    assert intent == "SCREENING"


def test_classify_overrides_llm_research_for_screening_query(monkeypatch) -> None:
    monkeypatch.setattr(
        classifier,
        "chat_json",
        lambda *_args, **_kwargs: {"intent": "research", "tickers": []},
    )

    out = classifier.classify("top AI growth stocks")

    assert out["intent"] == "SCREENING"


def test_classify_falls_back_to_heuristics_when_llm_empty(monkeypatch) -> None:
    monkeypatch.setattr(classifier, "chat_json", lambda *_args, **_kwargs: {})

    out = classifier.classify("top growth stocks")

    assert out["intent"] == "SCREENING"
    assert out["tickers"] == []


def test_classify_prefers_valid_llm_intent_and_merges_llm_tickers(monkeypatch) -> None:
    monkeypatch.setattr(
        classifier,
        "chat_json",
        lambda *_args, **_kwargs: {"intent": "research", "tickers": ["msft", "nvda"]},
    )

    out = classifier.classify("Tell me about NVIDIA")

    assert out["intent"] == "RESEARCH"
    assert out["tickers"] == ["NVDA", "MSFT"]
