"""Per-portfolio-project routers.

Each future portfolio project gets its own module here, e.g.
``app/routers/jev_triage.py``, with a ``SCHEMA_NAME`` constant at the top
and all queries scoped via ``scoped_table(SCHEMA_NAME, ...)``.
"""

from app.routers.health_supabase import router as supabase_health_router

__all__ = ["supabase_health_router"]
