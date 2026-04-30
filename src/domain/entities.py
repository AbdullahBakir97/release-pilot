"""Domain entities for Release Pilot."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import BumpKind, ChangeType, TriggerSource

__all__ = [
    "CommitDelta",
    "ChangeGroup",
    "ReleaseSpec",
    "ReleaseDraft",
]


@dataclass(slots=True)
class CommitDelta:
    """A single commit between two refs.

    Captures everything Release Pilot needs to know about a commit in order
    to classify, group, and render it in release notes.
    """

    sha: str
    short_sha: str
    message: str
    subject: str
    author_login: str
    author_name: str
    pr_number: int | None
    type: ChangeType
    scope: str | None
    breaking: bool


@dataclass(slots=True)
class ChangeGroup:
    """A section of the release notes (e.g. 'Features')."""

    title: str
    emoji: str
    commits: list[CommitDelta] = field(default_factory=list)


@dataclass(slots=True)
class ReleaseSpec:
    """Inputs needed to draft a release."""

    owner: str
    repo: str
    tag: str
    previous_tag: str | None
    target_commitish: str
    is_prerelease: bool
    trigger: TriggerSource
    installation_id: int


@dataclass(slots=True)
class ReleaseDraft:
    """The output of the generation pipeline."""

    name: str
    tag: str
    body: str
    is_prerelease: bool
    target_commitish: str
    groups: list[ChangeGroup]
    contributors: list[str]
    bump_kind: BumpKind
    full_changelog_url: str | None
