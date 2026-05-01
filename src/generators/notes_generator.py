"""Assemble the markdown body of a release draft.

The generated notes are designed to be publishable as-is: each release opens
with a one-line summary that tells a reader what changed at a glance, then
breaking changes (if any) are surfaced in their own callout, then the
detailed sections, contributors, and full-changelog link.
"""

from __future__ import annotations

import re
from typing import Any

from ..domain.entities import ChangeGroup, CommitDelta, ReleaseDraft, ReleaseSpec
from ..domain.enums import BumpKind, ChangeType
from ..domain.interfaces import INotesGenerator
from .contributor_lister import ContributorLister
from .grouping_strategy import SectionGrouper

__all__ = ["MarkdownNotesGenerator"]


class MarkdownNotesGenerator(INotesGenerator):
    """Compose the markdown release-notes body from grouped commit deltas."""

    def __init__(
        self,
        grouper: SectionGrouper,
        contributor_lister: ContributorLister,
    ) -> None:
        self._grouper = grouper
        self._contributors = contributor_lister

    def generate(
        self,
        spec: ReleaseSpec,
        deltas: list[CommitDelta],
        config: Any,
    ) -> ReleaseDraft:
        """Generate a complete ``ReleaseDraft`` for ``spec``."""
        # 1. Apply exclude filters from the config.
        filtered = self._apply_filters(deltas, config)

        # 2. Group commits into sections (breaking section handled inside grouper).
        groups = self._grouper.group(filtered)

        # 3. Build markdown body.
        full_changelog_url = self._full_changelog_url(spec)
        contributors = self._contributors.list_contributors(filtered)
        bump = self._compute_bump(filtered, is_prerelease=spec.is_prerelease)
        body = self._render_body(spec, groups, filtered, contributors, full_changelog_url, bump)

        return ReleaseDraft(
            name=spec.tag,
            tag=spec.tag,
            body=body,
            is_prerelease=spec.is_prerelease,
            target_commitish=spec.target_commitish,
            groups=groups,
            contributors=contributors,
            bump_kind=bump,
            full_changelog_url=full_changelog_url,
        )

    # ------------------------------------------------------------------ filters

    def _apply_filters(
        self,
        deltas: list[CommitDelta],
        config: Any,
    ) -> list[CommitDelta]:
        excluded_authors = set(_safe_attr(config, "excluded_authors", []) or [])
        exclude_bots = bool(_safe_attr(config, "exclude_bots", False))
        exclude_patterns = _safe_attr(config, "exclude_message_patterns", []) or []
        compiled = [re.compile(p) for p in exclude_patterns]

        out: list[CommitDelta] = []
        for delta in deltas:
            if delta.author_login and delta.author_login in excluded_authors:
                continue
            if exclude_bots and delta.author_login.endswith("[bot]"):
                continue
            if any(rx.search(delta.subject) for rx in compiled):
                continue
            out.append(delta)
        return out

    # ------------------------------------------------------------------ render

    def _render_body(
        self,
        spec: ReleaseSpec,
        groups: list[ChangeGroup],
        deltas: list[CommitDelta],
        contributors: list[str],
        full_changelog_url: str | None,
        bump: BumpKind,
    ) -> str:
        """Assemble the markdown sections of the release body."""
        lines: list[str] = []

        # 1. Summary header — one-liner that's readable in feeds and email.
        summary = self._build_summary(deltas, bump)
        if summary:
            lines.append(summary)
            lines.append("")

        # 2. Breaking-change callout, if any. Placed near the top so it's
        #    impossible to miss when scanning a release.
        breaking = [d for d in deltas if d.breaking]
        if breaking:
            lines.append("> [!WARNING]")
            lines.append("> **This release contains breaking changes.** Review the section below before upgrading.")
            lines.append("")

        # 3. Detailed sections.
        lines.append("## What's Changed")
        lines.append("")

        if not groups:
            # Empty release — say so explicitly rather than rendering a
            # blank section that might suggest tooling failure.
            lines.append("_No notable changes since the previous release._")
            lines.append(
                "_If you expected entries here, check that commits since the "
                "previous tag follow the configured filters._"
            )
            lines.append("")
        else:
            for group in groups:
                heading = f"### {group.emoji} {group.title}".strip() if group.emoji else f"### {group.title}"
                lines.append(heading)
                for commit in group.commits:
                    lines.append(self._render_commit_line(spec, commit))
                lines.append("")

        # 4. Contributors with count.
        if contributors:
            lines.append("---")
            lines.append("")
            count = len(contributors)
            noun = "contributor" if count == 1 else "contributors"
            joined = " ".join(contributors)
            lines.append(f"**{count} {noun}:** {joined}")
            lines.append("")

        # 5. Full changelog link.
        if full_changelog_url:
            lines.append(f"**Full Changelog:** {full_changelog_url}")

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _build_summary(deltas: list[CommitDelta], bump: BumpKind) -> str:
        """Produce a one-line summary describing the release at a glance.

        Examples:
          "**Major release** — 3 breaking changes, 5 features, 12 fixes."
          "**Minor release** — 2 features, 4 fixes, 1 doc update."
          "**Patch release** — 3 fixes, 1 chore."
        """
        if not deltas:
            return ""

        kind_label = {
            BumpKind.MAJOR: "Major release",
            BumpKind.MINOR: "Minor release",
            BumpKind.PATCH: "Patch release",
            BumpKind.PRERELEASE: "Pre-release",
            BumpKind.NONE: "Release",
        }[bump]

        # Count commits by category for the summary line.
        counts: dict[str, int] = {}
        for d in deltas:
            if d.breaking:
                counts["breaking"] = counts.get("breaking", 0) + 1
            if d.type is ChangeType.FEAT:
                counts["feat"] = counts.get("feat", 0) + 1
            elif d.type is ChangeType.FIX:
                counts["fix"] = counts.get("fix", 0) + 1
            elif d.type is ChangeType.DOCS:
                counts["docs"] = counts.get("docs", 0) + 1
            elif d.type is ChangeType.PERF:
                counts["perf"] = counts.get("perf", 0) + 1

        parts: list[str] = []
        if counts.get("breaking"):
            n = counts["breaking"]
            parts.append(f"{n} breaking change{'s' if n != 1 else ''}")
        if counts.get("feat"):
            n = counts["feat"]
            parts.append(f"{n} feature{'s' if n != 1 else ''}")
        if counts.get("fix"):
            n = counts["fix"]
            parts.append(f"{n} fix{'es' if n != 1 else ''}")
        if counts.get("perf"):
            n = counts["perf"]
            parts.append(f"{n} performance improvement{'s' if n != 1 else ''}")
        if counts.get("docs"):
            n = counts["docs"]
            parts.append(f"{n} doc update{'s' if n != 1 else ''}")

        if not parts:
            # Only chore/build/ci — keep the summary honest.
            parts.append(f"{len(deltas)} commit{'s' if len(deltas) != 1 else ''}")

        return f"**{kind_label}** — {', '.join(parts)}."

    def _render_commit_line(self, spec: ReleaseSpec, commit: CommitDelta) -> str:
        # Strip the conventional prefix from the subject for cleaner notes.
        subject = _strip_conventional_prefix(commit.subject)

        refs: list[str] = []
        if commit.pr_number is not None:
            pr_url = f"https://github.com/{spec.owner}/{spec.repo}/pull/{commit.pr_number}"
            refs.append(f"[#{commit.pr_number}]({pr_url})")

        commit_url = f"https://github.com/{spec.owner}/{spec.repo}/commit/{commit.sha}"
        refs.append(f"[`{commit.short_sha}`]({commit_url})")

        attribution = ""
        if commit.author_login:
            attribution = f" by @{commit.author_login}"

        return f"- {subject} ({', '.join(refs)}){attribution}"

    def _full_changelog_url(self, spec: ReleaseSpec) -> str | None:
        if not spec.previous_tag:
            return None
        return f"https://github.com/{spec.owner}/{spec.repo}/compare/{spec.previous_tag}...{spec.tag}"

    # ------------------------------------------------------------------ bump

    @staticmethod
    def _compute_bump(deltas: list[CommitDelta], *, is_prerelease: bool) -> BumpKind:
        if is_prerelease:
            return BumpKind.PRERELEASE
        if not deltas:
            return BumpKind.NONE
        if any(d.breaking for d in deltas):
            return BumpKind.MAJOR
        if any(d.type is ChangeType.FEAT for d in deltas):
            return BumpKind.MINOR
        return BumpKind.PATCH


# ---------------------------------------------------------------------- helpers


_CONVENTIONAL_PREFIX_RE = re.compile(
    r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\([^)]+\))?!?:\s*"
)


def _strip_conventional_prefix(subject: str) -> str:
    """Drop the ``type(scope)!:`` prefix so the rendered line reads naturally."""
    return _CONVENTIONAL_PREFIX_RE.sub("", subject).strip() or subject


def _safe_attr(obj: Any, name: str, default: Any) -> Any:
    """Read ``obj.name`` if present, else fall back to ``default``."""
    return getattr(obj, name, default)
