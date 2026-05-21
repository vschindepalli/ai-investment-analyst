from __future__ import annotations

from backend.services import llm


def test_chat_text_skips_ollama_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_CHAT_ENABLED", "false")
    from backend.config import get_settings

    get_settings.cache_clear()

    out = llm.chat_text("system", "user")
    assert out == ""

    get_settings.cache_clear()
    monkeypatch.delenv("OLLAMA_CHAT_ENABLED", raising=False)
