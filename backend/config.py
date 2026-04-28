"""Central runtime configuration.

All env vars are optional — the app boots without them and falls back to mock
data / deterministic explanations so the full pipeline is demoable end-to-end.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    # Embedding provider: "ollama" (default, local), "openai", or "hash" (offline fallback).
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "embeddinggemma")
    ollama_chat_model: str = os.getenv(
        "OLLAMA_CHAT_MODEL", "gemini-3-flash-preview:latest"
    )

    supabase_url: str | None = os.getenv("SUPABASE_URL") or None
    supabase_key: str | None = os.getenv("SUPABASE_KEY") or None

    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
