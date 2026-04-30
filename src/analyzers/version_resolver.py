"""Resolve the previous tag for a given current tag using semver ordering."""

from __future__ import annotations

import re
from typing import Final

from ..domain.exceptions import TagResolutionError
from ..domain.interfaces import IGitHubClient, ITagComparer

__all__ = [
    "SemverTagComparer",
    "DEFAULT_TAG_PATTERN",
]


# Default pattern: optional 'v' prefix + MAJOR.MINOR.PATCH plus optional pre-release/build.
DEFAULT_TAG_PATTERN: Final[str] = r"^v?\d+\.\d+\.\d+"

# Splits a tag into its semver core + optional pre-release suffix.
_SEMVER_SPLIT_RE: Final[re.Pattern[str]] = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[-+](?P<pre>.+))?$"
)


class SemverTagComparer(ITagComparer):
    """Resolves the previous tag using semver sort order.

    Lists all tags via the GitHub API, filters them with a configurable
    regex pattern, sorts them by semver, and returns the tag immediately
    before ``current_tag`` in the sorted order. Returns ``None`` when the
    current tag is the first matching tag (initial release).
    """

    def __init__(
        self,
        github_client: IGitHubClient,
        tag_pattern: str = DEFAULT_TAG_PATTERN,
    ) -> None:
        self._gh = github_client
        self._pattern = re.compile(tag_pattern)

    async def resolve_previous_tag(
        self,
        owner: str,
        repo: str,
        current_tag: str,
    ) -> str | None:
        """Find the tag immediately preceding ``current_tag`` by semver order."""
        tags_payload = await self._gh.list_tags(owner, repo)
        tag_names = [t.get("name", "") for t in tags_payload if t.get("name")]

        # Filter to tags matching the configured pattern.
        candidates = [name for name in tag_names if self._pattern.match(name)]

        # Always include the current tag in the sort, even if it doesn't appear
        # in the listing yet (e.g. brand new push that races API consistency).
        if current_tag not in candidates:
            if not self._pattern.match(current_tag):
                raise TagResolutionError(
                    f"Current tag {current_tag!r} does not match pattern {self._pattern.pattern!r}"
                )
            candidates.append(current_tag)

        # Sort ascending by parsed semver tuple.
        sorted_tags = sorted(candidates, key=self._semver_key)

        try:
            idx = sorted_tags.index(current_tag)
        except ValueError:
            return None

        if idx == 0:
            return None
        return sorted_tags[idx - 1]

    @staticmethod
    def _semver_key(tag: str) -> tuple[int, int, int, int, str]:
        """Build a sortable key from a tag string.

        Pre-release tags sort BEFORE their stable counterpart per semver spec
        (e.g. ``1.0.0-rc1`` < ``1.0.0``). We model this with a 4th element:
        ``0`` for pre-release, ``1`` for stable, then the pre-release string.
        Unparseable tags sort to the bottom.
        """
        m = _SEMVER_SPLIT_RE.match(tag)
        if m is None:
            return (-1, -1, -1, -1, tag)
        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        pre = m.group("pre")
        stable_flag = 0 if pre else 1
        return (major, minor, patch, stable_flag, pre or "")
