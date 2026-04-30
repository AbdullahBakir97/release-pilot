"""Load per-repository configuration from .github/release-pilot.yml."""

from __future__ import annotations

import logging

import yaml
from pydantic import ValidationError

from src.domain.interfaces import IConfigLoader
from src.infrastructure.github.client import GitHubClient

from .schema import ReleasePilotConfig

__all__ = ["GitHubConfigLoader"]

logger = logging.getLogger(__name__)

_CONFIG_PATH = ".github/release-pilot.yml"


class GitHubConfigLoader(IConfigLoader):
    """Loads and validates per-repo Release Pilot configuration via the GitHub API.

    Falls back to sensible defaults when the file is missing, contains
    invalid YAML, or fails Pydantic validation.
    """

    def __init__(self, github_client: GitHubClient) -> None:
        self._client = github_client

    async def load(self, owner: str, repo: str) -> ReleasePilotConfig:
        """Load configuration for *owner/repo*.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            A validated :class:`ReleasePilotConfig` instance.
        """
        content = await self._client.get_file_content(owner, repo, _CONFIG_PATH)

        if content is None:
            logger.debug("No config for %s/%s -- using defaults", owner, repo)
            return ReleasePilotConfig()

        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                logger.warning("Config for %s/%s is not a mapping -- using defaults", owner, repo)
                return ReleasePilotConfig()
            return ReleasePilotConfig(**data)
        except yaml.YAMLError as exc:
            logger.warning("Invalid YAML in config for %s/%s: %s -- using defaults", owner, repo, exc)
            return ReleasePilotConfig()
        except ValidationError as exc:
            logger.warning("Invalid config for %s/%s: %s -- using defaults", owner, repo, exc)
            return ReleasePilotConfig()
