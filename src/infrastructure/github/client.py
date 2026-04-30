"""GitHub API client for Release Pilot operations."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from src.domain.exceptions import GitHubAPIError
from src.domain.interfaces import IGitHubClient

from .auth import GitHubAuthenticator

__all__ = ["GitHubClient", "PREVIEW_COMMENT_MARKER"]

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.github.com"
PREVIEW_COMMENT_MARKER = "<!-- release-pilot:preview -->"


class GitHubClient(IGitHubClient):
    """Concrete GitHub API client backed by *httpx.AsyncClient*.

    All requests are authenticated using installation access tokens
    obtained from the supplied :class:`GitHubAuthenticator`.  The
    installation ID may be updated dynamically per webhook event via
    :meth:`set_installation_id`.
    """

    def __init__(self, authenticator: GitHubAuthenticator, installation_id: int = 0) -> None:
        self._auth = authenticator
        self._installation_id = installation_id

    def set_installation_id(self, installation_id: int) -> None:
        """Update the installation ID used for subsequent API calls."""
        self._installation_id = installation_id

    async def _headers(self) -> dict[str, str]:
        """Build authentication and accept headers."""
        token = await self._auth.get_installation_token(self._installation_id)
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Execute an authenticated API request.

        Raises:
            GitHubAPIError: On non-2xx responses.
        """
        headers = await self._headers()
        async with httpx.AsyncClient(base_url=_BASE_URL, timeout=30.0) as client:
            resp = await client.request(method, path, headers=headers, json=json, params=params)

        if resp.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API error {resp.status_code} on {method} {path}: {resp.text}",
                status_code=resp.status_code,
            )
        return resp

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository metadata."""
        resp = await self._request("GET", f"/repos/{owner}/{repo}")
        return resp.json()

    async def list_tags(self, owner: str, repo: str, per_page: int = 100) -> list[dict[str, Any]]:
        """List tags in the repository (single page; semver-sorted client-side)."""
        resp = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/tags",
            params={"per_page": per_page},
        )
        return resp.json()

    async def compare_commits(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> dict[str, Any]:
        """Compare two refs and return the raw GitHub compare payload."""
        resp = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/compare/{base}...{head}",
        )
        return resp.json()

    async def list_pull_requests_for_commit(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> list[dict[str, Any]]:
        """List PRs associated with a commit via the dedicated endpoint."""
        resp = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/commits/{sha}/pulls",
        )
        return resp.json()

    # IGitHubClient compatibility (singular spelling)
    async def list_pull_request_for_commit(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> list[dict[str, Any]]:
        """Alias for :meth:`list_pull_requests_for_commit`."""
        return await self.list_pull_requests_for_commit(owner, repo, sha)

    async def search_pull_requests_by_sha(
        self,
        owner: str,
        repo: str,
        sha: str,
    ) -> list[dict[str, Any]]:
        """Fallback search for merged PRs containing the given commit SHA."""
        try:
            resp = await self._request(
                "GET",
                "/search/issues",
                params={"q": f"repo:{owner}/{repo} is:pr is:merged sha:{sha}"},
            )
            data = resp.json()
            return list(data.get("items", []))
        except GitHubAPIError as exc:
            logger.warning("PR search failed for %s: %s", sha[:8], exc)
            return []

    async def create_release(
        self,
        owner: str,
        repo: str,
        tag_name: str,
        name: str,
        body: str,
        draft: bool = True,
        prerelease: bool = False,
        target_commitish: str | None = None,
    ) -> dict[str, Any]:
        """Create (or draft) a release on GitHub."""
        payload: dict[str, Any] = {
            "tag_name": tag_name,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        }
        if target_commitish:
            payload["target_commitish"] = target_commitish

        resp = await self._request("POST", f"/repos/{owner}/{repo}/releases", json=payload)
        logger.info("Created release %s on %s/%s (draft=%s)", tag_name, owner, repo, draft)
        return resp.json()

    async def post_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Post or update a Release Pilot preview comment on a PR.

        If a comment containing the preview marker already exists it will
        be patched in place; otherwise a new comment is created.
        """
        marked_body = f"{PREVIEW_COMMENT_MARKER}\n{body}"

        existing_id = await self._find_preview_comment(owner, repo, pr_number)
        if existing_id is not None:
            resp = await self._request(
                "PATCH",
                f"/repos/{owner}/{repo}/issues/comments/{existing_id}",
                json={"body": marked_body},
            )
            logger.info("Updated preview comment %s on %s/%s#%d", existing_id, owner, repo, pr_number)
            return resp.json()

        resp = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": marked_body},
        )
        logger.info("Created preview comment on %s/%s#%d", owner, repo, pr_number)
        return resp.json()

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> str | None:
        """Retrieve a file from the repository, decoded from base64.

        Returns ``None`` when the file does not exist.
        """
        params: dict[str, Any] | None = {"ref": ref} if ref else None
        try:
            resp = await self._request(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                params=params,
            )
            data = resp.json()
            return base64.b64decode(data["content"]).decode("utf-8")
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                return None
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_preview_comment(self, owner: str, repo: str, pr_number: int) -> int | None:
        """Return the ID of an existing Release Pilot preview comment, if any."""
        try:
            resp = await self._request(
                "GET",
                f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            )
            for comment in resp.json():
                if PREVIEW_COMMENT_MARKER in comment.get("body", ""):
                    return int(comment["id"])
        except GitHubAPIError:
            pass
        return None
