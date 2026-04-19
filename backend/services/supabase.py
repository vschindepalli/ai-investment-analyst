"""Supabase client wrapper.

Returns ``None`` when credentials are missing so callers can fall back to
mock data paths without crashing.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> Any | None:
    settings = get_settings()
    if not settings.has_supabase:
        return None
    try:
        from supabase import create_client  # type: ignore
    except ImportError:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)
