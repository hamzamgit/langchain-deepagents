"""Approval API routes (human-in-the-loop)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalRead,
)
from app.services import approval_service, support_orchestrator

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRead])
async def list_approvals(
    status_filter: str | None = Query(default="pending", alias="status"),
    session: AsyncSession = Depends(get_db_session),
) -> list[ApprovalRead]:
    approvals = await approval_service.list_approvals(session, status=status_filter)
    return [ApprovalRead.model_validate(a) for a in approvals]


@router.post("/{approval_id}/approve", response_model=ApprovalDecisionResponse)
async def approve_action(
    approval_id: str,
    body: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalDecisionResponse:
    try:
        outcome = await support_orchestrator.resume_after_approval(
            session,
            approval_id=approval_id,
            approved=True,
            reviewer_note=body.reviewer_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ApprovalDecisionResponse(
        approval_id=outcome["approval_id"],
        status=outcome["status"],
        conversation_id=outcome["conversation_id"],
        final_response=outcome.get("final_response"),
    )


@router.post("/{approval_id}/reject", response_model=ApprovalDecisionResponse)
async def reject_action(
    approval_id: str,
    body: ApprovalDecisionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalDecisionResponse:
    try:
        outcome = await support_orchestrator.resume_after_approval(
            session,
            approval_id=approval_id,
            approved=False,
            reviewer_note=body.reviewer_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ApprovalDecisionResponse(
        approval_id=outcome["approval_id"],
        status=outcome["status"],
        conversation_id=outcome["conversation_id"],
        final_response=outcome.get("final_response"),
    )
