"""Supabase health-check router.

Proves the backend → Supabase wiring end to end with a trivial query
that needs no project tables: listing one auth user via the service-role
key. Works even when no portfolio schema exists yet.

Template for future project routers — copy this shape::

    from fastapi import APIRouter
    from app.core.supabase import scoped_table

    SCHEMA_NAME = "jev_triage"  # <-- one schema per portfolio project
    router = APIRouter(prefix="/api/jev-triage", tags=["jev-triage"])

    @router.get("/tickets")
    def list_tickets():
        return scoped_table(SCHEMA_NAME, "tickets").select("*").execute().data
"""

from fastapi import APIRouter, HTTPException

from app.core.supabase import get_supabase_client, is_supabase_configured

router = APIRouter(tags=["health"])


def _check_supabase() -> dict[str, object]:
    if not is_supabase_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Supabase is not configured: set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY in the environment."
            ),
        )
    try:
        # Trivial end-to-end query: hits the Supabase Auth admin API with
        # the service-role key. Needs no tables/schemas to exist.
        get_supabase_client().auth.admin.list_users(page=1, per_page=1)
    except HTTPException:
        raise
    except Exception as exc:  # network / invalid key / bad URL, etc.
        raise HTTPException(
            status_code=503,
            detail=f"Supabase reachable check failed: {exc}",
        ) from exc
    return {"status": "ok"}


@router.get("/api/health/supabase")
def supabase_health() -> dict[str, object]:
    """Health check: GET /api/health/supabase (primary route)."""
    return _check_supabase()


@router.get("/health/supabase", include_in_schema=False)
def supabase_health_alias() -> dict[str, object]:
    """Alias without the /api prefix (same check)."""
    return _check_supabase()
