"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.settings import Settings

__all__ = ["configure_logging"]


def configure_logging(settings: Settings) -> None:
    """Set up application logging based on the environment.

    In production, logs are emitted as JSON lines for structured ingestion.
    In development, a human-readable format is used instead.

    Args:
        settings: Application settings providing log level and environment.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if settings.is_development:
        fmt = "%(asctime)s %(levelname)-8s %(name)s -- %(message)s"
        datefmt = "%H:%M:%S"
    else:
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'
        datefmt = "%Y-%m-%dT%H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
