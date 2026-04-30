"""Coordinates the full release-drafting workflow."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.domain.entities import ReleaseDraft, ReleaseSpec
from src.domain.exceptions import TagResolutionError
from src.domain.interfaces import (
    IConfigLoader,
    IDeltaCalculator,
    IGitHubClient,
    INotesGenerator,
    ITagComparer,
)
from src.generators.contributor_lister import ContributorLister
from src.generators.grouping_strategy import SectionGrouper
from src.generators.notes_generator import MarkdownNotesGenerator
from src.infrastructure.config.schema import ReleasePilotConfig, SectionConfig

__all__ = ["ReleaseOrchestrator"]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _SectionAdapter:
    """Adapter that adds an ``emoji`` attribute expected by SectionGrouper."""

    title: str
    emoji: str
    types: list[str]
    only_if_scope_matches: str | None
    excluding_scope: str | None


@dataclass(slots=True)
class _BreakingSectionAdapter:
    """Adapter for the breaking-changes section (matches BreakingSectionConfig)."""

    title: str
    emoji: str


_LEADING_EMOJI_RE = re.compile(r"^\s*(\S+)\s+")


def _split_emoji(title: str) -> tuple[str, str]:
    """Split a "EMOJI Title" string into (emoji, remainder).

    Returns ``("", title)`` when no leading emoji is detected.
    """
    match = _LEADING_EMOJI_RE.match(title)
    if not match:
        return "", title
    candidate = match.group(1)
    # Treat the first whitespace-separated token as an emoji when it
    # contains no ASCII alphanumerics.
    if any(ch.isalnum() and ord(ch) < 128 for ch in candidate):
        return "", title
    return candidate, title[match.end() :]


def _adapt_sections(sections: list[SectionConfig]) -> list[_SectionAdapter]:
    """Convert config SectionConfig list into grouper-compatible adapters."""
    adapted: list[_SectionAdapter] = []
    for s in sections:
        emoji, remainder = _split_emoji(s.title)
        adapted.append(
            _SectionAdapter(
                title=remainder,
                emoji=emoji,
                types=list(s.types),
                only_if_scope_matches=s.only_if_scope_matches,
                excluding_scope=s.excluding_scope,
            )
        )
    return adapted


class ReleaseOrchestrator:
    """Drives the end-to-end flow that produces a release draft.

    Steps:
      1. Set the installation ID on the GitHub client.
      2. Load the per-repo configuration (or defaults).
      3. Resolve the previous tag if not supplied.
      4. Calculate the commit delta between the previous tag and the
         current tag/ref.
      5. Generate release notes using the configured grouping rules.
      6. Either create a draft release on GitHub or post a preview
         comment on a pull request.
    """

    def __init__(
        self,
        github_client: IGitHubClient,
        tag_comparer: ITagComparer,
        delta_calculator: IDeltaCalculator,
        notes_generator: INotesGenerator,
        config_loader: IConfigLoader,
    ) -> None:
        self._github = github_client
        self._tag_comparer = tag_comparer
        self._delta_calculator = delta_calculator
        self._notes_generator = notes_generator
        self._config_loader = config_loader

    async def draft_release(self, spec: ReleaseSpec) -> ReleaseDraft:
        """Produce a release draft and (optionally) push it to GitHub."""
        draft, config = await self._build_draft(spec)

        if not config.enabled:
            logger.info("Release Pilot disabled for %s/%s", spec.owner, spec.repo)
            return draft

        if config.release.draft:
            await self._github.create_release(
                owner=spec.owner,
                repo=spec.repo,
                tag_name=draft.tag,
                name=draft.name,
                body=draft.body,
                draft=True,
                prerelease=draft.is_prerelease,
                target_commitish=draft.target_commitish,
            )

        return draft

    async def preview_release(self, spec: ReleaseSpec, pr_number: int) -> ReleaseDraft:
        """Generate notes and post them as a PR comment instead of releasing."""
        draft, config = await self._build_draft(spec)
        if not config.enabled:
            logger.info("Release Pilot disabled for %s/%s", spec.owner, spec.repo)
            return draft

        body = f"### Release Pilot preview for `{draft.tag}`\n\n{draft.body}"
        await self._github.post_pr_comment(spec.owner, spec.repo, pr_number, body)
        return draft

    # ------------------------------------------------------------------ helpers

    async def _build_draft(self, spec: ReleaseSpec) -> tuple[ReleaseDraft, ReleasePilotConfig]:
        """Shared pipeline for both ``draft_release`` and ``preview_release``."""
        if hasattr(self._github, "set_installation_id"):
            self._github.set_installation_id(spec.installation_id)  # type: ignore[attr-defined]

        config = await self._config_loader.load(spec.owner, spec.repo)

        previous_tag = spec.previous_tag
        if previous_tag is None:
            try:
                previous_tag = await self._tag_comparer.resolve_previous_tag(spec.owner, spec.repo, spec.tag)
            except TagResolutionError as exc:
                logger.warning("Tag resolution failed: %s -- falling back to root", exc)
                previous_tag = None

        base_ref = previous_tag or spec.target_commitish or spec.tag
        head_ref = spec.tag

        if previous_tag is None or previous_tag == spec.tag:
            deltas: list[Any] = []
        else:
            deltas = await self._delta_calculator.calculate_delta(spec.owner, spec.repo, base=base_ref, head=head_ref)

        spec_with_prev = ReleaseSpec(
            owner=spec.owner,
            repo=spec.repo,
            tag=spec.tag,
            previous_tag=previous_tag,
            target_commitish=spec.target_commitish,
            is_prerelease=spec.is_prerelease,
            trigger=spec.trigger,
            installation_id=spec.installation_id,
        )

        # Re-bind generator to a config-aware grouper / contributor lister.
        generator = self._build_generator(config)
        draft = generator.generate(spec_with_prev, deltas, config)
        return draft, config

    @staticmethod
    def _build_generator(config: ReleasePilotConfig) -> MarkdownNotesGenerator:
        """Compose a notes generator wired with config-driven helpers."""
        breaking_section = (
            _BreakingSectionAdapter(
                title=config.breaking_changes.title,
                emoji="\U0001f4a5",
            )
            if config.breaking_changes.separate_section
            else None
        )
        grouper = SectionGrouper(
            sections=_adapt_sections(config.sections),
            breaking_section=breaking_section,
        )
        contributor_lister = ContributorLister(
            exclude_bots=config.contributors.exclude_bots,
        )
        return MarkdownNotesGenerator(grouper, contributor_lister)
