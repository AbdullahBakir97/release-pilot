"""Shared pytest fixtures for Release Pilot tests."""

from __future__ import annotations

import pytest

from src.domain.entities import CommitDelta, ReleaseSpec
from src.domain.enums import ChangeType, TriggerSource
from src.infrastructure.config.schema import ReleasePilotConfig


def _delta(
    sha: str,
    subject: str,
    *,
    type_: ChangeType = ChangeType.FEAT,
    scope: str | None = None,
    breaking: bool = False,
    pr_number: int | None = None,
    author_login: str = "alice",
    author_name: str = "Alice",
) -> CommitDelta:
    return CommitDelta(
        sha=sha,
        short_sha=sha[:7],
        message=subject,
        subject=subject,
        author_login=author_login,
        author_name=author_name,
        pr_number=pr_number,
        type=type_,
        scope=scope,
        breaking=breaking,
    )


@pytest.fixture
def sample_commits() -> list[CommitDelta]:
    """A representative mix of commit types including a breaking change."""
    return [
        _delta("a1" * 20, "feat(auth): add OAuth login", type_=ChangeType.FEAT, scope="auth", pr_number=42),
        _delta(
            "b2" * 20,
            "fix(parser): handle null",
            type_=ChangeType.FIX,
            scope="parser",
            pr_number=43,
            author_login="bob",
        ),
        _delta("c3" * 20, "docs(readme): clarify install", type_=ChangeType.DOCS, scope="readme", pr_number=45),
        _delta(
            "d4" * 20,
            "feat(api)!: drop legacy endpoint",
            type_=ChangeType.FEAT,
            scope="api",
            breaking=True,
            pr_number=50,
        ),
        _delta(
            "e5" * 20,
            "chore(deps): bump fastapi",
            type_=ChangeType.CHORE,
            scope="deps",
            pr_number=49,
            author_login="dependabot[bot]",
            author_name="dependabot",
        ),
    ]


@pytest.fixture
def sample_config() -> ReleasePilotConfig:
    """A default-valued :class:`ReleasePilotConfig`."""
    return ReleasePilotConfig()


@pytest.fixture
def sample_release_spec() -> ReleaseSpec:
    """A spec for an upgrade from v1.2.0 to v1.3.0 on main."""
    return ReleaseSpec(
        owner="acme",
        repo="widgets",
        tag="v1.3.0",
        previous_tag="v1.2.0",
        target_commitish="main",
        is_prerelease=False,
        trigger=TriggerSource.TAG_PUSH,
        installation_id=12345,
    )


@pytest.fixture
def pr_data() -> dict:
    """A minimal PR object resembling the GitHub REST API response."""
    return {
        "number": 42,
        "title": "feat(auth): add OAuth login",
        "state": "closed",
        "merged": True,
        "user": {"login": "alice"},
        "head": {"sha": "a1" * 20, "ref": "feature/oauth"},
        "base": {"ref": "main"},
        "labels": [{"name": "release:next"}],
    }
