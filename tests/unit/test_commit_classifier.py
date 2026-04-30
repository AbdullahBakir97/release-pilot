"""Tests for the conventional commit classifier."""

from __future__ import annotations

from src.analyzers.commit_classifier import ConventionalCommitClassifier
from src.domain.enums import ChangeType


def test_feat_with_scope() -> None:
    cls = ConventionalCommitClassifier()
    type_, scope, breaking = cls.classify("feat(auth): add OAuth login")
    assert type_ is ChangeType.FEAT
    assert scope == "auth"
    assert breaking is False


def test_fix_without_scope() -> None:
    cls = ConventionalCommitClassifier()
    type_, scope, breaking = cls.classify("fix: handle null")
    assert type_ is ChangeType.FIX
    assert scope is None
    assert breaking is False


def test_breaking_via_bang() -> None:
    cls = ConventionalCommitClassifier()
    type_, scope, breaking = cls.classify("feat!: drop legacy auth")
    assert type_ is ChangeType.FEAT
    assert scope is None
    assert breaking is True


def test_chore_deps_with_bang() -> None:
    cls = ConventionalCommitClassifier()
    type_, scope, breaking = cls.classify("chore(deps)!: bump fastapi")
    assert type_ is ChangeType.CHORE
    assert scope == "deps"
    assert breaking is True


def test_breaking_via_footer() -> None:
    cls = ConventionalCommitClassifier()
    msg = "feat: tweak api\n\nBREAKING CHANGE: removes /v1"
    type_, scope, breaking = cls.classify(msg)
    assert type_ is ChangeType.FEAT
    assert breaking is True


def test_breaking_change_dash_variant() -> None:
    cls = ConventionalCommitClassifier()
    msg = "fix: oops\n\nBREAKING-CHANGE: actually a breaker"
    type_, scope, breaking = cls.classify(msg)
    assert type_ is ChangeType.FIX
    assert breaking is True


def test_non_conventional_message() -> None:
    cls = ConventionalCommitClassifier()
    type_, scope, breaking = cls.classify("Update README")
    assert type_ is ChangeType.UNKNOWN
    assert scope is None
    assert breaking is False


def test_empty_message() -> None:
    cls = ConventionalCommitClassifier()
    type_, scope, breaking = cls.classify("")
    assert type_ is ChangeType.UNKNOWN
    assert scope is None
    assert breaking is False
