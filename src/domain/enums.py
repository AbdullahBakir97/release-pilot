"""Enumerations used throughout the Release Pilot domain layer."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ChangeType",
    "ReleaseStrategy",
    "BumpKind",
    "TriggerSource",
]


class ChangeType(StrEnum):
    """Conventional commit type classification."""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"
    UNKNOWN = "unknown"


class ReleaseStrategy(StrEnum):
    """How releases should be handled once drafted."""

    DRAFT = "draft"
    AUTO = "auto"
    MANUAL = "manual"


class BumpKind(StrEnum):
    """Semantic version bump implied by a change set."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    NONE = "none"


class TriggerSource(StrEnum):
    """Source event that triggered a release-worthy action."""

    TAG_PUSH = "tag_push"
    WORKFLOW_DISPATCH = "workflow_dispatch"
    MAIN_PUSH = "main_push"
    PR_LABEL_PREVIEW = "pr_label_preview"
