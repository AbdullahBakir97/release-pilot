"""Domain-level exceptions for Release Pilot."""

from __future__ import annotations

__all__ = [
    "ReleasePilotError",
    "TagResolutionError",
    "GitHubAPIError",
    "GenerationError",
    "ConfigurationError",
]


class ReleasePilotError(Exception):
    """Base exception for all Release Pilot errors."""


class TagResolutionError(ReleasePilotError):
    """Raised when the previous tag cannot be resolved."""


class GitHubAPIError(ReleasePilotError):
    """Raised when a GitHub API call fails or returns an unexpected payload."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GenerationError(ReleasePilotError):
    """Raised when release notes generation fails."""


class ConfigurationError(ReleasePilotError):
    """Raised when configuration is missing, malformed, or invalid."""
