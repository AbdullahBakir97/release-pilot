"""Application-wide settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings

__all__ = ["Settings"]


class Settings(BaseSettings):
    """Global application settings.

    Values are read from environment variables or an ``.env`` file.
    Both naming conventions are supported -- the short form (``app_id``)
    used in this codebase, and the long form (``GITHUB_APP_ID``) used by
    Render and other PaaS environments -- and they are kept in sync via
    :meth:`model_post_init`.
    """

    # --- Short / canonical names (used by the application code) ---
    app_id: str = Field(default="", description="GitHub App ID")
    private_key: str = Field(default="", description="GitHub App private key contents")
    private_key_path: str = Field(default="./private-key.pem", description="Path to the private key file")
    webhook_secret: str = Field(default="", description="Webhook signature secret")

    # --- Aliases (the long ENV names some platforms expect) ---
    github_app_id: str = Field(default="", description="Alias for app_id")
    github_private_key: str = Field(default="", description="Alias for private_key")
    github_webhook_secret: str = Field(default="", description="Alias for webhook_secret")

    # --- Server ---
    port: int = Field(default=8000, description="Server port")
    env: str = Field(default="development", description="Environment name")
    log_level: str = Field(default="INFO", description="Logging level")
    allowed_origins: str = Field(default="*", description="CORS allowed origins (comma separated)")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def model_post_init(self, __context: Any) -> None:
        """Sync alias fields so either env var name works."""
        if self.github_app_id and not self.app_id:
            self.app_id = self.github_app_id
        if self.app_id and not self.github_app_id:
            self.github_app_id = self.app_id

        if self.github_private_key and not self.private_key:
            self.private_key = self.github_private_key
        if self.private_key and not self.github_private_key:
            self.github_private_key = self.private_key

        if self.github_webhook_secret and not self.webhook_secret:
            self.webhook_secret = self.github_webhook_secret
        if self.webhook_secret and not self.github_webhook_secret:
            self.github_webhook_secret = self.webhook_secret

    @property
    def is_development(self) -> bool:
        """Whether the app is running in development mode."""
        return self.env.lower() == "development"

    def get_private_key(self) -> str:
        """Return the private key contents.

        If ``private_key`` is set directly it is returned (with literal
        ``\\n`` sequences replaced by real newlines).  Otherwise the key
        is read from ``private_key_path``.  Returns an empty string when
        neither source is available.
        """
        if self.private_key:
            return self.private_key.replace("\\n", "\n")
        path = Path(self.private_key_path)
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return ""
