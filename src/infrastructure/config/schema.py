"""Pydantic models for per-repository configuration (.github/release-pilot.yml)."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "TriggerConfig",
    "ReleaseSettings",
    "SectionConfig",
    "ExcludeConfig",
    "BreakingChangesConfig",
    "ContributorsConfig",
    "TagPatternConfig",
    "ReleasePilotConfig",
]


class TriggerConfig(BaseModel):
    """How releases are triggered."""

    on_tag: bool = True
    on_main: bool = False
    on_pr_label: str = "release:next"


class ReleaseSettings(BaseModel):
    """Release strategy and naming settings."""

    draft: bool = True
    prerelease_pattern: str = r".*-(?:alpha|beta|rc)\.\d+$"
    generate_release_name: bool = True
    include_full_changelog_link: bool = True


class SectionConfig(BaseModel):
    """A single section of the release notes (e.g. Features)."""

    title: str
    types: list[str] = Field(default_factory=list)
    only_if_scope_matches: str | None = None
    excluding_scope: str | None = None
    sort: str = "by_pr_number"  # by_pr_number | by_sha | by_subject


class ExcludeConfig(BaseModel):
    """Filtering rules for which commits to skip entirely."""

    authors: list[str] = Field(default_factory=list)
    bots: bool = False
    matching: str = r"^Merge branch"
    drafts: bool = True


class BreakingChangesConfig(BaseModel):
    """Where and how to render breaking changes."""

    separate_section: bool = True
    title: str = "\U0001f4a5 BREAKING CHANGES"
    detect_via: list[str] = Field(default_factory=lambda: ["!", "BREAKING CHANGE", "BREAKING-CHANGE"])


class ContributorsConfig(BaseModel):
    """Contributor list rendering options."""

    enabled: bool = True
    exclude_bots: bool = False
    format: str = "**Contributors:** {mentions}"


class TagPatternConfig(BaseModel):
    """Pattern that identifies a release-worthy tag."""

    pattern: str = r"^v?\d+\.\d+\.\d+(?:-.+)?$"


def _default_sections() -> list[SectionConfig]:
    """Default section layout matching the documented release notes format."""
    return [
        SectionConfig(title="✨ Features", types=["feat"]),
        SectionConfig(title="\U0001f41b Bug Fixes", types=["fix"]),
        SectionConfig(title="\U0001f4da Documentation", types=["docs"]),
        SectionConfig(title="♻️ Refactoring", types=["refactor", "perf"]),
        SectionConfig(title="\U0001f9ea Tests", types=["test"]),
        SectionConfig(title="⚙️ CI / Build", types=["ci", "build"]),
        SectionConfig(
            title="\U0001f4e6 Dependencies",
            types=["chore"],
            only_if_scope_matches=r"deps|deps-dev",
        ),
        SectionConfig(
            title="\U0001f527 Chores",
            types=["chore"],
            excluding_scope=r"deps|deps-dev",
        ),
    ]


class ReleasePilotConfig(BaseModel):
    """Per-repository configuration for Release Pilot.

    Loaded from ``.github/release-pilot.yml`` in the target repository.
    All fields have sensible defaults so the config file is optional.
    """

    enabled: bool = True
    triggers: TriggerConfig = Field(default_factory=TriggerConfig)
    release: ReleaseSettings = Field(default_factory=ReleaseSettings)
    sections: list[SectionConfig] = Field(default_factory=_default_sections)
    exclude: ExcludeConfig = Field(default_factory=ExcludeConfig)
    breaking_changes: BreakingChangesConfig = Field(default_factory=BreakingChangesConfig)
    contributors: ContributorsConfig = Field(default_factory=ContributorsConfig)
    tag_pattern: TagPatternConfig = Field(default_factory=TagPatternConfig)
