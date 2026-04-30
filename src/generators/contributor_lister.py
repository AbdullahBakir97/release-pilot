"""Extract a stable, de-duplicated list of contributors from commit deltas."""

from __future__ import annotations

from ..domain.entities import CommitDelta

__all__ = ["ContributorLister"]


class ContributorLister:
    """Build the ordered list of ``@login`` mentions for the release notes.

    Behaviour:
      * Reads ``author_login`` from each delta (skipping empty values).
      * Optionally excludes bot accounts whose login ends in ``[bot]``.
      * Returns logins prefixed with ``@`` in first-seen order (stable).
    """

    def __init__(self, exclude_bots: bool = False) -> None:
        self._exclude_bots = exclude_bots

    def list_contributors(self, deltas: list[CommitDelta]) -> list[str]:
        """Return de-duplicated ``@login`` strings in first-seen order."""
        seen: set[str] = set()
        contributors: list[str] = []

        for delta in deltas:
            login = (delta.author_login or "").strip()
            if not login:
                continue
            if self._exclude_bots and login.endswith("[bot]"):
                continue
            if login in seen:
                continue
            seen.add(login)
            contributors.append(f"@{login}")

        return contributors
