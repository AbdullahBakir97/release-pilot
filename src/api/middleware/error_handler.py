"""Global exception handler middleware for the FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.domain.exceptions import (
    ConfigurationError,
    GenerationError,
    GitHubAPIError,
    ReleasePilotError,
    TagResolutionError,
)

__all__ = ["register_error_handlers"]

logger = logging.getLogger(__name__)

_STATUS_MAP: dict[type[ReleasePilotError], int] = {
    ConfigurationError: 500,
    GitHubAPIError: 502,
    GenerationError: 422,
    TagResolutionError: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on *app*."""

    @app.exception_handler(ReleasePilotError)
    async def handle_domain_error(request: Request, exc: ReleasePilotError) -> JSONResponse:
        """Map domain exceptions to JSON error responses."""
        status_code = _STATUS_MAP.get(type(exc), 500)
        logger.error("Domain error [%s]: %s", type(exc).__name__, exc)
        return JSONResponse(
            status_code=status_code,
            content={"error": type(exc).__name__, "detail": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        """Convert Pydantic validation errors to a 422 response."""
        logger.warning("Validation error: %s", exc)
        return JSONResponse(
            status_code=422,
            content={"error": "ValidationError", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions (details hidden in production)."""
        logger.exception("Unexpected error: %s", exc)
        is_dev = getattr(request.app.state, "settings_is_dev", False)
        detail = str(exc) if is_dev else "An unexpected error occurred."
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "detail": detail},
        )
