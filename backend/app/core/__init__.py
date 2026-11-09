"""Shared backend package for per-project core modules."""

from app.core.supabase import (
    get_supabase_client,
    is_supabase_configured,
    scoped_table,
)

__all__ = ["get_supabase_client", "is_supabase_configured", "scoped_table"]
