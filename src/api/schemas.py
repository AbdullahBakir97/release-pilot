"""Pydantic request and response models for the API layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "PreviewRequest",
    "PreviewResponse",
    "HealthResponse",
    "WebhookResponse",
]


class PreviewRequest(BaseModel):
    """Request body for the ``/api/v1/preview`` endpoint."""

    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    from_ref: str = Field(..., min_length=1, description="Base ref / previous tag")
    to_ref: str = Field(..., min_length=1, description="Head ref / target tag")
    installation_id: int = Field(default=0, description="Optional installation ID")


class PreviewResponse(BaseModel):
    """Response body for the ``/api/v1/preview`` endpoint."""

    name: str
    body: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    contributors: list[str] = Field(default_factory=list)
    bump_kind: str


class HealthResponse(BaseModel):
    """Response body for the ``/health`` endpoint."""

    status: str = "ok"
    uptime: float = 0.0
    version: str = "1.0.0"


class WebhookResponse(BaseModel):
    """Response body for the ``/webhook`` endpoint."""

    received: bool = True
