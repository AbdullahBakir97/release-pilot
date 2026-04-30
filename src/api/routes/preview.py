"""Preview endpoint -- generate release notes without creating a release."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from src.api.dependencies import get_orchestrator
from src.api.schemas import PreviewRequest, PreviewResponse
from src.application.orchestrator import ReleaseOrchestrator
from src.domain.entities import ReleaseSpec
from src.domain.enums import TriggerSource

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["preview"])


@router.post("/preview", response_model=PreviewResponse)
async def preview_release(
    request: PreviewRequest,
    orchestrator: ReleaseOrchestrator = Depends(get_orchestrator),
) -> PreviewResponse:
    """Generate release notes for an arbitrary range, without publishing.

    Body fields:
        owner: Repository owner.
        repo: Repository name.
        from_ref: Base ref (previous tag).
        to_ref: Head ref (target tag).
    """
    spec = ReleaseSpec(
        owner=request.owner,
        repo=request.repo,
        tag=request.to_ref,
        previous_tag=request.from_ref,
        target_commitish=request.to_ref,
        is_prerelease=False,
        trigger=TriggerSource.WORKFLOW_DISPATCH,
        installation_id=request.installation_id,
    )

    # Build the draft locally without writing back to GitHub.  We bypass
    # the high-level ``draft_release`` helper to avoid creating a real
    # release as a side effect.
    draft, _ = await orchestrator._build_draft(spec)

    sections = [
        {
            "title": g.title,
            "emoji": g.emoji,
            "count": len(g.commits),
            "items": [
                {
                    "subject": c.subject,
                    "sha": c.sha,
                    "pr_number": c.pr_number,
                    "scope": c.scope,
                    "breaking": c.breaking,
                }
                for c in g.commits
            ],
        }
        for g in draft.groups
    ]

    return PreviewResponse(
        name=draft.name,
        body=draft.body,
        sections=sections,
        contributors=draft.contributors,
        bump_kind=draft.bump_kind.value,
    )
