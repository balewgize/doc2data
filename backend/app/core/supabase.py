"""Shared Supabase client (service-role) + per-project schema scoping.

Single Supabase project hosts many isolated portfolio projects, one
Postgres schema per project (e.g. ``jev_triage``, ``example_project``).

Pattern for every future router (do NOT create a client per router)::

    from app.core.supabase import scoped_table

    SCHEMA_NAME = "jev_triage"  # one constant per router file

    @router.get("/tickets")
    def list_tickets():
        resp = scoped_table(SCHEMA_NAME, "tickets").select("*").execute()
        return resp.data

The backend always uses the SERVICE ROLE key (bypasses RLS) and all
reads/writes go through FastAPI — never expose this key to the browser.
Tables therefore stay locked down (RLS enabled, no public grants).
"""

import os

from supabase import Client, create_client

_client: Client | None = None


def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip()


def _service_role_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


def is_supabase_configured() -> bool:
    """True when both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set."""
    return bool(supabase_url() and _service_role_key())


def get_supabase_client() -> Client:
    """Return the single shared service-role Supabase client.

    Raises:
        RuntimeError: if SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are missing.
    """
    global _client
    if _client is not None:
        return _client
    url = supabase_url()
    key = _service_role_key()
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured: set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in the environment (.env)."
        )
    _client = create_client(url, key)
    return _client


def reset_supabase_client() -> None:
    """Drop the cached client (mainly for tests)."""
    global _client
    _client = None


def scoped_table(schema: str, table: str):
    """Return a schema-scoped PostgREST table reference.

    Args:
        schema: Postgres schema for one portfolio project (e.g. "jev_triage").
        table: Table inside that schema (e.g. "tickets").

    Example:
        scoped_table("jev_triage", "tickets").select("*").limit(10).execute()
    """
    if not schema or not table:
        raise ValueError("Both schema and table names are required.")
    return get_supabase_client().schema(schema).table(table)
