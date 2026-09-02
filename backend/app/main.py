"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth as auth_routes
from app.api.routes import compounds as compound_routes
from app.api.routes import export as export_routes
from app.api.routes import health as health_routes
from app.api.routes import methods as method_routes
from app.api.routes import ml as ml_routes
from app.api.routes import predictions as prediction_routes
from app.api.routes import runs as run_routes
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing heavy (DB ping is optional; migrations run separately)
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

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"name": "LC-MS Method Prediction Suite", "version": "0.1.0"}

    return app


app = create_app()
