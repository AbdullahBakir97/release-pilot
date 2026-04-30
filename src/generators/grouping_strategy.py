"""Group commit deltas into release-note sections."""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from ..domain.entities import ChangeGroup, CommitDelta
from ..domain.enums import ChangeType

__all__ = [
    "SectionGrouper",
    "SectionConfig",
    "BreakingSectionConfig",
]


@runtime_checkable
class SectionConfig(Protocol):
    """Protocol for a configured section in the release notes config.

    Concrete implementations live in ``src.config.models``; we duck-type here
    so the generator stays decoupled from Pydantic models.
    """

    title: str
    emoji: str
    types: list[str]
    only_if_scope_matches: str | None
    excluding_scope: str | None


@runtime_checkable
class BreakingSectionConfig(Protocol):
    """Protocol for the optional breaking-changes section configuration."""

    title: str
    emoji: str


class SectionGrouper:
    """Bucket commit deltas into ``ChangeGroup`` sections.

    Behaviour:
      * Sections are consumed in declared order.
      * For each section, commits are filtered by ``types`` and optional
        scope regexes (``only_if_scope_matches`` / ``excluding_scope``).
      * A commit lands in only one section (first match wins).
      * Empty groups are dropped from the output.
      * If ``breaking_section`` is provided, breaking-change commits are
        diverted to that section instead of their type-based section.
    """

    def __init__(
        self,
        sections: list[SectionConfig | Any],
        breaking_section: BreakingSectionConfig | Any | None = None,
    ) -> None:
        self._sections = sections
        self._breaking_section = breaking_section

    def group(self, deltas: list[CommitDelta]) -> list[ChangeGroup]:
        """Return groups in declared order, skipping empty groups."""
        consumed: set[str] = set()
        groups: list[ChangeGroup] = []

        # Breaking changes -- diverted to a dedicated section if configured.
        breaking_commits: list[CommitDelta] = []
        if self._breaking_section is not None:
            for delta in deltas:
                if delta.breaking:
                    breaking_commits.append(delta)
                    consumed.add(delta.sha)

        for section in self._sections:
            allowed_types = {self._normalize_type(t) for t in section.types}
            scope_in_re = self._compile(getattr(section, "only_if_scope_matches", None))
            scope_out_re = self._compile(getattr(section, "excluding_scope", None))

            bucket: list[CommitDelta] = []
            for delta in deltas:
                if delta.sha in consumed:
                    continue
                if delta.type not in allowed_types:
                    continue
                if scope_in_re is not None:
                    if delta.scope is None or not scope_in_re.search(delta.scope):
                        continue
                if scope_out_re is not None and delta.scope is not None:
                    if scope_out_re.search(delta.scope):
                        continue
                bucket.append(delta)
                consumed.add(delta.sha)

            if bucket:
                groups.append(ChangeGroup(title=section.title, emoji=getattr(section, "emoji", ""), commits=bucket))

        if breaking_commits and self._breaking_section is not None:
            groups.append(
                ChangeGroup(
                    title=self._breaking_section.title,
                    emoji=getattr(self._breaking_section, "emoji", ""),
                    commits=breaking_commits,
                )
            )

        return groups

    @staticmethod
    def _normalize_type(value: str | ChangeType) -> ChangeType:
        if isinstance(value, ChangeType):
            return value
        try:
            return ChangeType(value)
        except ValueError:
            return ChangeType.UNKNOWN

    @staticmethod
    def _compile(pattern: str | None) -> re.Pattern[str] | None:
        if not pattern:
            return None
        return re.compile(pattern)
