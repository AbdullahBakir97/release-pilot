"""FastAPI dependency-injection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request

if TYPE_CHECKING:
    from src.application.orchestrator import ReleaseOrchestrator
    from src.application.webhook_handler import WebhookHandler
    from src.container import Container
    from src.infrastructure.github.webhook import WebhookVerifier

__all__ = [
    "get_container",
    "get_orchestrator",
    "get_webhook_handler",
    "get_webhook_verifier",
]


def get_container(request: Request) -> Container:
    """Retrieve the DI container stored on application state."""
    return request.app.state.container


def get_orchestrator(
    container: Container = Depends(get_container),
) -> ReleaseOrchestrator:
    """Provide the configured :class:`ReleaseOrchestrator`."""
    return container.orchestrator


def get_webhook_handler(
    container: Container = Depends(get_container),
) -> WebhookHandler:
    """Provide the configured :class:`WebhookHandler`."""
    return container.webhook_handler


def get_webhook_verifier(
    container: Container = Depends(get_container),
) -> WebhookVerifier | None:
    """Provide the optional :class:`WebhookVerifier`.

    Returns ``None`` when no webhook secret has been configured.
    """
    return container.webhook_verifier
