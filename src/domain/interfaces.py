"""Abstract interfaces for Release Pilot services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from .entities import CommitDelta, ReleaseDraft, ReleaseSpec
from .enums import ChangeType

if TYPE_CHECKING:
    # Forward reference for the config object resolved by IConfigLoader.
    # The concrete ReleasePilotConfig lives in the config package and is not
    # imported here to keep the domain layer free of outward dependencies.
    from ..infrastructure.config.schema import ReleasePilotConfig

__all__ = [
    "IGitHubClient",
    "ITagComparer",
    "IDeltaCalculator",
    "ICommitClassifier",
    "INotesGenerator",
    "IConfigLoader",
]


class IGitHubClient(ABC):
    """Client for interacting with the GitHub REST API."""

    @abstractmethod
    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository metadata."""

    @abstractmethod
    async def list_tags(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List all tags in the repository (paginated under the hood)."""

    @abstractmethod
    async def compare_commits(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> dict[str, Any]:
        """Compare two refs and return the GitHub compare payload."""

    @abstractmethod
    async def search_pull_requests_by_sha(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> list[dict[str, Any]]:
        """Search merged PRs that include the given commit SHA."""

    @abstractmethod
    async def list_pull_request_for_commit(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> list[dict[str, Any]]:
        """List PRs associated with a commit via the dedicated endpoint."""

    @abstractmethod
    async def create_release(
        self,
        owner: str,
        repo: str,
        tag: str,
        name: str,
        body: str,
        target_commitish: str,
        draft: bool = True,
        prerelease: bool = False,
    ) -> dict[str, Any]:
        """Create (or draft) a release on GitHub."""

    @abstractmethod
    async def post_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> None:
        """Post a comment on a pull request."""

    @abstractmethod
    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> str | None:
        """Fetch the raw text content of a file, or None if missing."""


class ITagComparer(ABC):
    """Resolves the previous tag relative to a current tag."""

    @abstractmethod
    async def resolve_previous_tag(
        self,
        owner: str,
        repo: str,
        current_tag: str,
    ) -> str | None:
        """Return the tag immediately preceding ``current_tag`` (or None)."""


class IDeltaCalculator(ABC):
    """Computes the list of commits between two refs."""

    @abstractmethod
    async def calculate_delta(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> list[CommitDelta]:
        """Return a list of CommitDelta entries between base and head."""


class ICommitClassifier(ABC):
    """Classifies commit messages into Conventional Commit categories."""

    @abstractmethod
    def classify(self, message: str) -> tuple[ChangeType, str | None, bool]:
        """Classify a commit message.

        Returns:
            A tuple of (type, scope_or_None, breaking_bool).
        """


class INotesGenerator(ABC):
    """Generates release notes from a spec and a list of commit deltas."""

    @abstractmethod
    def generate(
        self,
        spec: ReleaseSpec,
        deltas: list[CommitDelta],
        config: ReleasePilotConfig,
    ) -> ReleaseDraft:
        """Produce a ReleaseDraft from the spec, deltas, and config."""


class IConfigLoader(ABC):
    """Loads the per-repository Release Pilot configuration."""

    @abstractmethod
    async def load(self, owner: str, repo: str) -> ReleasePilotConfig:
        """Load configuration for a given repository."""
