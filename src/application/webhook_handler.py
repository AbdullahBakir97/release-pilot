"""Routes incoming GitHub webhook events to the release orchestrator."""

from __future__ import annotations

import logging
import re
from typing import Any

from src.domain.entities import ReleaseSpec
from src.domain.enums import TriggerSource
from src.infrastructure.config.schema import ReleasePilotConfig

from .orchestrator import ReleaseOrchestrator

__all__ = ["WebhookHandler"]

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Dispatch GitHub events that may trigger a release.

    Handled events:
      * ``create`` (ref_type=tag) -> draft release
      * ``push`` with ``refs/tags/`` ref -> draft release
      * ``pull_request`` with ``action=labeled`` and matching label -> preview
      * ``workflow_dispatch`` with ``tag``/``base`` inputs -> draft release
    """

    def __init__(self, orchestrator: ReleaseOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def handle_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Dispatch *event_type* / *payload* to the right handler."""
        match event_type:
            case "push":
                ref = payload.get("ref", "") or ""
                if ref.startswith("refs/tags/"):
                    await self._handle_tag_push(payload)
                else:
                    logger.debug("Ignoring non-tag push: %s", ref)
            case "create":
                if payload.get("ref_type") == "tag":
                    await self._handle_tag_push(payload)
                else:
                    logger.debug("Ignoring create event: %s", payload.get("ref_type"))
            case "pull_request":
                if payload.get("action") == "labeled":
                    await self._handle_pr_label(payload)
                else:
                    logger.debug("Ignoring pull_request action: %s", payload.get("action"))
            case "workflow_dispatch":
                await self._handle_workflow_dispatch(payload)
            case _:
                logger.debug("Ignoring event type: %s", event_type)

    # ------------------------------------------------------------------ handlers

    async def _handle_tag_push(self, payload: dict[str, Any]) -> None:
        """Handle a tag push or tag-create event."""
        owner, repo, installation_id = self._repo_coords(payload)

        ref = payload.get("ref") or ""
        if ref.startswith("refs/tags/"):
            tag = ref[len("refs/tags/") :]
        else:
            tag = ref or ""

        if not tag:
            logger.warning("Tag push with no resolvable tag name; skipping")
            return

        # Lazy default-config tag pattern match.  Real config is loaded
        # again inside the orchestrator for grouping; here we just
        # short-circuit on obviously non-release tags.
        defaults = ReleasePilotConfig()
        if not re.match(defaults.tag_pattern.pattern, tag):
            logger.info("Tag %s doesn't match release pattern; skipping", tag)
            return

        is_prerelease = bool(re.match(defaults.release.prerelease_pattern, tag))
        target_commitish = self._target_commitish(payload, default="main")

        spec = ReleaseSpec(
            owner=owner,
            repo=repo,
            tag=tag,
            previous_tag=None,
            target_commitish=target_commitish,
            is_prerelease=is_prerelease,
            trigger=TriggerSource.TAG_PUSH,
            installation_id=installation_id,
        )
        logger.info("Drafting release for %s/%s tag=%s", owner, repo, tag)
        await self._orchestrator.draft_release(spec)

    async def _handle_pr_label(self, payload: dict[str, Any]) -> None:
        """Handle a PR labeled event for preview generation."""
        owner, repo, installation_id = self._repo_coords(payload)
        label = (payload.get("label") or {}).get("name", "")

        defaults = ReleasePilotConfig()
        if label != defaults.triggers.on_pr_label:
            logger.debug("Ignoring label %r (expected %r)", label, defaults.triggers.on_pr_label)
            return

        pr = payload.get("pull_request") or {}
        pr_number = pr.get("number")
        if not isinstance(pr_number, int):
            logger.warning("PR label event missing PR number; skipping")
            return

        head = pr.get("head") or {}
        target_commitish = head.get("ref") or self._target_commitish(payload, default="main")
        head_sha = head.get("sha") or target_commitish

        spec = ReleaseSpec(
            owner=owner,
            repo=repo,
            tag=f"preview-{pr_number}",
            previous_tag=(pr.get("base") or {}).get("ref"),
            target_commitish=head_sha,
            is_prerelease=True,
            trigger=TriggerSource.PR_LABEL_PREVIEW,
            installation_id=installation_id,
        )
        logger.info("Generating preview for %s/%s#%d", owner, repo, pr_number)
        await self._orchestrator.preview_release(spec, pr_number=pr_number)

    async def _handle_workflow_dispatch(self, payload: dict[str, Any]) -> None:
        """Handle a workflow_dispatch trigger.

        Reads ``inputs.tag`` and (optionally) ``inputs.base`` from the
        payload and forwards them to the orchestrator.
        """
        owner, repo, installation_id = self._repo_coords(payload)
        inputs = payload.get("inputs") or {}
        tag = inputs.get("tag") or ""
        base = inputs.get("base")

        if not tag:
            logger.warning("workflow_dispatch missing 'tag' input; skipping")
            return

        target_commitish = self._target_commitish(payload, default="main")
        defaults = ReleasePilotConfig()
        is_prerelease = bool(re.match(defaults.release.prerelease_pattern, tag))

        spec = ReleaseSpec(
            owner=owner,
            repo=repo,
            tag=tag,
            previous_tag=base,
            target_commitish=target_commitish,
            is_prerelease=is_prerelease,
            trigger=TriggerSource.WORKFLOW_DISPATCH,
            installation_id=installation_id,
        )
        logger.info("Manual draft requested for %s/%s tag=%s", owner, repo, tag)
        await self._orchestrator.draft_release(spec)

    # ------------------------------------------------------------------ utilities

    @staticmethod
    def _repo_coords(payload: dict[str, Any]) -> tuple[str, str, int]:
        """Extract (owner, repo, installation_id) from a webhook payload."""
        repo_obj = payload.get("repository") or {}
        owner = ((repo_obj.get("owner") or {}).get("login")) or repo_obj.get("owner", "")
        name = repo_obj.get("name", "")
        installation = (payload.get("installation") or {}).get("id") or 0
        return owner, name, int(installation)

    @staticmethod
    def _target_commitish(payload: dict[str, Any], *, default: str) -> str:
        """Pick a sane target commitish from a webhook payload."""
        repo = payload.get("repository") or {}
        return payload.get("master_branch") or repo.get("default_branch") or default
