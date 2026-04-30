"""Compute the commit delta between two refs using the GitHub compare API."""

from __future__ import annotations

import logging
from typing import Any

from ..domain.entities import CommitDelta
from ..domain.exceptions import GitHubAPIError
from ..domain.interfaces import ICommitClassifier, IDeltaCalculator, IGitHubClient

__all__ = ["GitHubCompareDeltaCalculator"]

logger = logging.getLogger(__name__)


class GitHubCompareDeltaCalculator(IDeltaCalculator):
    """Computes a list of CommitDelta entries via the GitHub compare API.

    For each commit in the compare response we:
      * Build a base CommitDelta (sha, message, author info).
      * Try to find the merged PR associated with the commit, first via the
        dedicated "list PRs for commit" endpoint, then falling back to the
        search API. Defensive about missing PR linkage.
      * Classify type/scope/breaking via the injected ICommitClassifier.
    """

    def __init__(
        self,
        github_client: IGitHubClient,
        classifier: ICommitClassifier,
    ) -> None:
        self._gh = github_client
        self._classifier = classifier

    async def calculate_delta(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> list[CommitDelta]:
        """Return CommitDelta entries between ``base`` and ``head``."""
        try:
            payload = await self._gh.compare_commits(owner, repo, base=base, head=head)
        except Exception as exc:  # pragma: no cover - thin wrapper
            raise GitHubAPIError(f"compare_commits({owner}/{repo} {base}...{head}) failed: {exc}") from exc

        commits = payload.get("commits") or []
        deltas: list[CommitDelta] = []

        for raw in commits:
            delta = await self._build_delta(owner, repo, raw)
            if delta is not None:
                deltas.append(delta)

        return deltas

    async def _build_delta(
        self,
        owner: str,
        repo: str,
        raw: dict[str, Any],
    ) -> CommitDelta | None:
        sha = raw.get("sha") or ""
        if not sha:
            return None

        commit_obj = raw.get("commit") or {}
        message: str = commit_obj.get("message") or ""
        subject = message.splitlines()[0].strip() if message else ""

        author_obj = commit_obj.get("author") or {}
        author_name: str = author_obj.get("name") or ""

        # The top-level "author" key carries the GitHub user (may be null for
        # commits authored by emails not linked to any GitHub account).
        gh_author = raw.get("author") or {}
        author_login: str = (gh_author or {}).get("login") or ""

        pr_number = await self._find_pr_for_commit(owner, repo, sha)

        change_type, scope, breaking = self._classifier.classify(message)

        return CommitDelta(
            sha=sha,
            short_sha=sha[:7],
            message=message,
            subject=subject,
            author_login=author_login,
            author_name=author_name,
            pr_number=pr_number,
            type=change_type,
            scope=scope,
            breaking=breaking,
        )

    async def _find_pr_for_commit(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> int | None:
        """Best-effort PR lookup. Returns None if no PR can be resolved."""
        # Preferred: dedicated REST endpoint -- usually returns the merging PR.
        try:
            prs = await self._gh.list_pull_request_for_commit(owner, repo, sha)
            for pr in prs:
                num = pr.get("number")
                if isinstance(num, int):
                    return num
        except Exception as exc:
            logger.debug("list_pull_request_for_commit failed for %s: %s", sha, exc)

        # Fallback: search API.
        try:
            results = await self._gh.search_pull_requests_by_sha(owner, repo, sha)
            for pr in results:
                num = pr.get("number")
                if isinstance(num, int):
                    return num
        except Exception as exc:
            logger.debug("search_pull_requests_by_sha failed for %s: %s", sha, exc)

        return None
