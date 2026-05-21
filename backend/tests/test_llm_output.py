from __future__ import annotations

from backend.services.llm import strip_reasoning


def test_strip_reasoning_removes_think_tags() -> None:
    raw = "<think>Let me check.</think>NVDA leads on growth."
    assert strip_reasoning(raw) == "NVDA leads on growth."


def test_strip_reasoning_removes_thinking_prefix() -> None:
    raw = "Thinking: step one.\n\nNVDA is a GPU leader."
    assert strip_reasoning(raw) == "NVDA is a GPU leader."


def test_strip_reasoning_keeps_plain_answer() -> None:
    raw = "NVDA leads the screen on growth and momentum."
    assert strip_reasoning(raw) == raw
