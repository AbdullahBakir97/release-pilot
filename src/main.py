"""Entry point for the Release Pilot application."""

from __future__ import annotations

import uvicorn

from src.api.app import create_app
from src.config.settings import Settings

__all__ = ["main"]


def main() -> None:
    """Start the application server."""
    settings = Settings()
    app = create_app(settings)
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
