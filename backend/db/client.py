"""DB client facade — thin re-export over the Supabase service."""
from __future__ import annotations

from backend.services.supabase import get_client

__all__ = ["get_client"]
