"""Conventional commit classifier."""

from __future__ import annotations

import re
from typing import Final

from ..domain.enums import ChangeType
from ..domain.interfaces import ICommitClassifier

__all__ = [
    "ConventionalCommitClassifier",
    "CONVENTIONAL_HEADER_RE",
    "BREAKING_FOOTER_RE",
]


# Shared parser regex -- exported so webhook handlers and other components
# can reuse the exact same parsing rules without duplicating the pattern.
CONVENTIONAL_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s*(?P<desc>.+)$"
)

# "BREAKING CHANGE:" or "BREAKING-CHANGE:" footer marker, anywhere in the body.
BREAKING_FOOTER_RE: Final[re.Pattern[str]] = re.compile(r"^BREAKING[ -]CHANGE\s*:", re.MULTILINE)


class ConventionalCommitClassifier(ICommitClassifier):
    """Parses commit messages following the Conventional Commits spec.

    Returns ``ChangeType.UNKNOWN`` with no scope and ``breaking=False`` for
    messages that do not match the conventional header pattern.
    """

    def classify(self, message: str) -> tuple[ChangeType, str | None, bool]:
        """Classify a commit message.

        Args:
            message: The full commit message (subject and body).

        Returns:
            (ChangeType, scope_or_None, breaking_bool)
        """
        if not message:
            return ChangeType.UNKNOWN, None, False

        # Subject is the first non-empty line.
        lines = message.splitlines()
        subject = lines[0].strip() if lines else ""
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""

        match = CONVENTIONAL_HEADER_RE.match(subject)
        if match is None:
            # Even non-conventional commits may declare a breaking change in the body.
            breaking = bool(BREAKING_FOOTER_RE.search(body))
            return ChangeType.UNKNOWN, None, breaking

        type_str = match.group("type")
        scope = match.group("scope")
        bang = match.group("breaking") is not None
        body_breaking = bool(BREAKING_FOOTER_RE.search(body))

        try:
            change_type = ChangeType(type_str)
        except ValueError:
            change_type = ChangeType.UNKNOWN

        return change_type, scope, bang or body_breaking
