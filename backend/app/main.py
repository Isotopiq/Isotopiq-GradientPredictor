"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth as auth_routes
from app.api.routes import admin as admin_routes
from app.api.routes import columns as column_routes
from app.api.routes import compounds as compound_routes
from app.api.routes import export as export_routes
from app.api.routes import health as health_routes
from app.api.routes import methods as method_routes
from app.api.routes import ml as ml_routes
from app.api.routes import notifications as notification_routes
from app.api.routes import predictions as prediction_routes
from app.api.routes import runs as run_routes
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed default admin (migrations already run in CMD/Dockerfile)
    import logging

    from app.database import engine as async_engine
    from app.core.seed import seed_admin
    from sqlalchemy.ext.asyncio import AsyncSession

    logger = logging.getLogger("app.startup")
    logging.basicConfig(level=logging.INFO)

    # Seed admin user
    print("[startup] Seeding admin user...", flush=True)
    try:
        async with AsyncSession(async_engine) as db:
            await seed_admin(db)
        print("[startup] Admin seed complete.", flush=True)
    except Exception as exc:
        print(f"[startup] Admin seed FAILED: {exc}", flush=True)
        logger.warning("Admin seed skipped: %s", exc)

    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title="LC-MS Method Prediction Suite",
        version="0.1.0",
        description="Predict LC-MS method parameters from compound structure.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = "/api/v1"
    app.include_router(health_routes.router, prefix=api_prefix)
    app.include_router(auth_routes.router, prefix=api_prefix)
    app.include_router(compound_routes.router, prefix=api_prefix)
    app.include_router(method_routes.router, prefix=api_prefix)
    app.include_router(prediction_routes.router, prefix=api_prefix)
    app.include_router(run_routes.router, prefix=api_prefix)
    app.include_router(ml_routes.router, prefix=api_prefix)
    app.include_router(export_routes.router, prefix=api_prefix)
    app.include_router(column_routes.router, prefix=api_prefix)
    app.include_router(notification_routes.router, prefix=api_prefix)
    app.include_router(admin_routes.router, prefix=api_prefix)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"name": "LC-MS Method Prediction Suite", "version": "0.1.0"}

    return app


app = create_app()
