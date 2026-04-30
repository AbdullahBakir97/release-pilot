"""Dependency-injection container -- wires every layer together."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.analyzers.commit_classifier import ConventionalCommitClassifier
from src.analyzers.delta_calculator import GitHubCompareDeltaCalculator
from src.analyzers.version_resolver import SemverTagComparer
from src.application.orchestrator import ReleaseOrchestrator
from src.application.webhook_handler import WebhookHandler
from src.generators.contributor_lister import ContributorLister
from src.generators.grouping_strategy import SectionGrouper
from src.generators.notes_generator import MarkdownNotesGenerator
from src.infrastructure.config.loader import GitHubConfigLoader
from src.infrastructure.github.auth import GitHubAuthenticator
from src.infrastructure.github.client import GitHubClient
from src.infrastructure.github.webhook import WebhookVerifier

if TYPE_CHECKING:
    from src.config.settings import Settings

__all__ = ["Container"]


class Container:
    """Composes the entire dependency graph for Release Pilot.

    Instantiated once at startup and stored on ``app.state.container`` so
    FastAPI dependency-injection helpers can fetch individual components.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # --- Infrastructure ---
        self.github_auth = GitHubAuthenticator(
            settings.app_id,
            settings.get_private_key() or "",
        )
        self.github_client = GitHubClient(self.github_auth)
        self.webhook_verifier: WebhookVerifier | None = (
            WebhookVerifier(settings.webhook_secret) if settings.webhook_secret else None
        )
        self.config_loader = GitHubConfigLoader(self.github_client)

        # --- Analyzers ---
        self.commit_classifier = ConventionalCommitClassifier()
        self.tag_comparer = SemverTagComparer(self.github_client)
        self.delta_calculator = GitHubCompareDeltaCalculator(self.github_client, self.commit_classifier)

        # --- Generators (defaults; orchestrator rebuilds per-config at runtime) ---
        self.grouper = SectionGrouper(sections=[], breaking_section=None)
        self.contributor_lister = ContributorLister()
        self.notes_generator = MarkdownNotesGenerator(self.grouper, self.contributor_lister)

        # --- Application ---
        self.orchestrator = ReleaseOrchestrator(
            self.github_client,
            self.tag_comparer,
            self.delta_calculator,
            self.notes_generator,
            self.config_loader,
        )
        self.webhook_handler = WebhookHandler(self.orchestrator)
