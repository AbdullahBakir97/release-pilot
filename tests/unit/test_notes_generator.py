"""Tests for the markdown release-notes generator.

The generator must produce notes that are publishable as-is. These tests
verify the structural pieces (summary header, breaking-change callout,
empty-release fallback, contributor count) and the voice (no AI prose,
specific summary numbers).
"""

from __future__ import annotations

import pytest

from src.domain.entities import CommitDelta, ReleaseSpec
from src.domain.enums import BumpKind, ChangeType, TriggerSource
from src.generators.contributor_lister import ContributorLister
from src.generators.grouping_strategy import SectionGrouper
from src.generators.notes_generator import MarkdownNotesGenerator
from src.infrastructure.config.schema import ReleasePilotConfig

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


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


def _spec(*, previous_tag: str | None = "v1.2.0") -> ReleaseSpec:
    return ReleaseSpec(
        owner="acme",
        repo="widgets",
        tag="v1.3.0",
        previous_tag=previous_tag,
        target_commitish="main",
        is_prerelease=False,
        trigger=TriggerSource.TAG_PUSH,
        installation_id=12345,
    )


@pytest.fixture
def generator() -> MarkdownNotesGenerator:
    config = ReleasePilotConfig()
    return MarkdownNotesGenerator(
        grouper=SectionGrouper(config.sections, config.breaking_changes),
        contributor_lister=ContributorLister(),
    )


@pytest.fixture
def config() -> ReleasePilotConfig:
    return ReleasePilotConfig()


# ------------------------------------------------------------------ #
# Scenario 1: Summary header
# ------------------------------------------------------------------ #


class TestSummary:
    def test_minor_release_summary_lists_features_and_fixes(self, generator, config):
        deltas = [
            _delta("a" * 40, "feat: new endpoint", type_=ChangeType.FEAT),
            _delta("b" * 40, "feat: another", type_=ChangeType.FEAT),
            _delta("c" * 40, "fix: bug", type_=ChangeType.FIX),
        ]
        draft = generator.generate(_spec(), deltas, config)

        assert "Minor release" in draft.body
        assert "2 features" in draft.body
        assert "1 fix" in draft.body  # singular

    def test_major_release_summary_lists_breaking_count(self, generator, config):
        deltas = [
            _delta("a" * 40, "feat!: drop v1 API", type_=ChangeType.FEAT, breaking=True),
            _delta("b" * 40, "feat: minor", type_=ChangeType.FEAT),
            _delta("c" * 40, "fix: bug", type_=ChangeType.FIX),
        ]
        draft = generator.generate(_spec(), deltas, config)

        assert draft.bump_kind is BumpKind.MAJOR
        assert "Major release" in draft.body
        assert "1 breaking change" in draft.body  # singular

    def test_patch_release_summary_for_fixes_only(self, generator, config):
        deltas = [_delta("a" * 40, "fix: a", type_=ChangeType.FIX)]
        draft = generator.generate(_spec(), deltas, config)

        assert draft.bump_kind is BumpKind.PATCH
        assert "Patch release" in draft.body
        assert "1 fix" in draft.body

    def test_chore_only_release_uses_commit_count(self, generator, config):
        deltas = [
            _delta("a" * 40, "chore: bump deps", type_=ChangeType.CHORE),
            _delta("b" * 40, "ci: tweak workflow", type_=ChangeType.CI),
        ]
        draft = generator.generate(_spec(), deltas, config)

        # No feat/fix/docs/perf — falls back to commit count
        assert "2 commits" in draft.body


# ------------------------------------------------------------------ #
# Scenario 2: Breaking-change callout
# ------------------------------------------------------------------ #


class TestBreakingChangeCallout:
    def test_breaking_change_renders_warning_callout(self, generator, config):
        deltas = [
            _delta("a" * 40, "feat!: drop v1", type_=ChangeType.FEAT, breaking=True),
        ]
        draft = generator.generate(_spec(), deltas, config)

        assert "[!WARNING]" in draft.body
        assert "breaking changes" in draft.body.lower()

    def test_no_breaking_change_no_warning(self, generator, config):
        deltas = [_delta("a" * 40, "feat: new", type_=ChangeType.FEAT)]
        draft = generator.generate(_spec(), deltas, config)

        assert "[!WARNING]" not in draft.body


# ------------------------------------------------------------------ #
# Scenario 3: Empty release
# ------------------------------------------------------------------ #


class TestEmptyRelease:
    def test_empty_release_explains_why_explicitly(self, generator, config):
        draft = generator.generate(_spec(), [], config)

        assert "No notable changes" in draft.body
        assert "previous tag" in draft.body  # the diagnostic hint
        assert draft.bump_kind is BumpKind.NONE

    def test_empty_release_omits_summary(self, generator, config):
        draft = generator.generate(_spec(), [], config)

        # Summary line skipped for empty releases
        assert "Major release" not in draft.body
        assert "Patch release" not in draft.body


# ------------------------------------------------------------------ #
# Scenario 4: Contributors with count
# ------------------------------------------------------------------ #


class TestContributors:
    def test_single_contributor_uses_singular_noun(self, generator, config):
        deltas = [_delta("a" * 40, "feat: x", author_login="alice")]
        draft = generator.generate(_spec(), deltas, config)

        assert "1 contributor:" in draft.body
        assert "@alice" in draft.body

    def test_multiple_contributors_use_plural_noun(self, generator, config):
        deltas = [
            _delta("a" * 40, "feat: x", author_login="alice"),
            _delta("b" * 40, "fix: y", author_login="bob"),
            _delta("c" * 40, "docs: z", author_login="carol", type_=ChangeType.DOCS),
        ]
        draft = generator.generate(_spec(), deltas, config)

        assert "3 contributors:" in draft.body


# ------------------------------------------------------------------ #
# Scenario 5: Full changelog link
# ------------------------------------------------------------------ #


class TestFullChangelog:
    def test_link_present_when_previous_tag_known(self, generator, config):
        deltas = [_delta("a" * 40, "feat: x")]
        draft = generator.generate(_spec(previous_tag="v1.2.0"), deltas, config)

        assert "compare/v1.2.0...v1.3.0" in draft.body

    def test_link_absent_when_no_previous_tag(self, generator, config):
        deltas = [_delta("a" * 40, "feat: x")]
        draft = generator.generate(_spec(previous_tag=None), deltas, config)

        assert "compare/" not in draft.body


# ------------------------------------------------------------------ #
# Scenario 6: Commit lines
# ------------------------------------------------------------------ #


class TestCommitLines:
    def test_commit_line_links_to_pr_and_sha(self, generator, config):
        deltas = [
            _delta("a" * 40, "feat(auth): add OAuth", scope="auth", pr_number=42),
        ]
        draft = generator.generate(_spec(), deltas, config)

        assert "#42" in draft.body
        # The first 7 chars of the SHA (a*40 → aaaaaaa)
        assert "`aaaaaaa`" in draft.body

    def test_commit_line_strips_conventional_prefix(self, generator, config):
        deltas = [
            _delta("a" * 40, "feat(auth): add OAuth login support", pr_number=42),
        ]
        draft = generator.generate(_spec(), deltas, config)

        # The rendered line should NOT include the type prefix
        assert "feat(auth):" not in draft.body
        # But the cleaned subject SHOULD
        assert "add OAuth login support" in draft.body

    def test_commit_attribution_uses_author_login(self, generator, config):
        deltas = [_delta("a" * 40, "feat: x", author_login="alice")]
        draft = generator.generate(_spec(), deltas, config)

        assert "by @alice" in draft.body


# ------------------------------------------------------------------ #
# Scenario 7: Voice quality
# ------------------------------------------------------------------ #


class TestVoiceQuality:
    def test_no_ai_prose(self, generator, config):
        deltas = [
            _delta("a" * 40, "feat: x", type_=ChangeType.FEAT),
            _delta("b" * 40, "fix: y", type_=ChangeType.FIX),
        ]
        draft = generator.generate(_spec(), deltas, config)
        lowered = draft.body.lower()

        for phrase in ["delve", "holistic", "i'd be happy to", "hope this helps"]:
            assert phrase not in lowered, f"Notes contain AI phrase '{phrase}'"
