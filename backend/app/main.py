import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.supabase import is_supabase_configured
from app.docpipe.storage import init_db
from app.routers.docpipe import router as docpipe_router
from app.routers.health_supabase import router as supabase_health_router


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="DocuBridge API",
        description="Turn supplier catalogs, invoices and other business documents into validated, structured records.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Shared infra router (Supabase health check).
    app.include_router(supabase_health_router)
    # DocuBridge product router.
    app.include_router(docpipe_router)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "supabase_configured": is_supabase_configured()}

    @app.get("/api/hello")
    def hello(name: str = "world") -> dict[str, str]:
        return {"message": f"Hello, {name}!"}

    return app


app = create_app()
