"""FastAPI application factory."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.middleware.error_handler import register_error_handlers
from src.api.middleware.logging import RequestLoggingMiddleware
from src.api.routes.health import router as health_router
from src.api.routes.preview import router as preview_router
from src.api.routes.webhook import router as webhook_router
from src.config.logging import configure_logging
from src.container import Container

if TYPE_CHECKING:
    from src.config.settings import Settings

__all__ = ["create_app"]

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional pre-built settings.  When ``None`` a new
            :class:`Settings` instance is loaded from the environment.

    Returns:
        A fully configured :class:`FastAPI` application.
    """
    if settings is None:
        from src.config.settings import Settings

        settings = Settings()

    configure_logging(settings)

    app = FastAPI(
        title="Release Pilot",
        version="1.0.0",
        description="GitHub App that drafts professional Releases from your conventional commits.",
    )

    # Static dashboard
    try:
        app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
    except Exception:
        logger.debug("Dashboard static files not found -- skipping mount")

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_error_handlers(app)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """Redirect root to the dashboard."""
        return RedirectResponse(url="/dashboard")

    app.include_router(webhook_router)
    app.include_router(preview_router)
    app.include_router(health_router)

    container = Container(settings)
    app.state.container = container
    app.state.settings_is_dev = settings.is_development

    logger.info("Application created (env=%s, port=%d)", settings.env, settings.port)

    return app
