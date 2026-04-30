"""Tests for the section grouper."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities import CommitDelta
from src.domain.enums import ChangeType
from src.generators.grouping_strategy import SectionGrouper


@dataclass
class _S:
    """Minimal SectionConfig stand-in for grouper tests."""

    title: str
    emoji: str
    types: list[str]
    only_if_scope_matches: str | None = None
    excluding_scope: str | None = None


def _delta(
    sha: str,
    type_: ChangeType,
    scope: str | None = None,
    breaking: bool = False,
) -> CommitDelta:
    return CommitDelta(
        sha=sha,
        short_sha=sha[:7],
        message="msg",
        subject="msg",
        author_login="alice",
        author_name="Alice",
        pr_number=None,
        type=type_,
        scope=scope,
        breaking=breaking,
    )


def test_first_match_wins() -> None:
    sections = [
        _S(title="Features", emoji="✨", types=["feat"]),
        _S(title="Anything", emoji="*", types=["feat", "fix"]),
    ]
    grouper = SectionGrouper(sections=sections)
    groups = grouper.group([_delta("aaa", ChangeType.FEAT)])
    assert len(groups) == 1
    assert groups[0].title == "Features"


def test_only_if_scope_matches_filter() -> None:
    sections = [
        _S(
            title="Deps",
            emoji="📦",
            types=["chore"],
            only_if_scope_matches=r"deps|deps-dev",
        ),
        _S(title="Chores", emoji="🔧", types=["chore"]),
    ]
    grouper = SectionGrouper(sections=sections)
    groups = grouper.group(
        [
            _delta("a", ChangeType.CHORE, scope="deps"),
            _delta("b", ChangeType.CHORE, scope="release"),
        ]
    )
    titles = [g.title for g in groups]
    assert "Deps" in titles
    assert "Chores" in titles
    deps = next(g for g in groups if g.title == "Deps")
    chores = next(g for g in groups if g.title == "Chores")
    assert len(deps.commits) == 1 and deps.commits[0].sha == "a"
    assert len(chores.commits) == 1 and chores.commits[0].sha == "b"


def test_excluding_scope_filter() -> None:
    sections = [
        _S(
            title="Chores",
            emoji="🔧",
            types=["chore"],
            excluding_scope=r"deps|deps-dev",
        ),
    ]
    grouper = SectionGrouper(sections=sections)
    groups = grouper.group(
        [
            _delta("a", ChangeType.CHORE, scope="deps"),
            _delta("b", ChangeType.CHORE, scope="release"),
        ]
    )
    assert len(groups) == 1
    assert {c.sha for c in groups[0].commits} == {"b"}


def test_empty_groups_removed() -> None:
    sections = [
        _S(title="Features", emoji="✨", types=["feat"]),
        _S(title="Tests", emoji="🧪", types=["test"]),
    ]
    grouper = SectionGrouper(sections=sections)
    groups = grouper.group([_delta("a", ChangeType.FEAT)])
    titles = [g.title for g in groups]
    assert titles == ["Features"]
