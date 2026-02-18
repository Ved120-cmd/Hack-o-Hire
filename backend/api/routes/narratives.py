"""
Narrative Routes – view, edit, approve, reject.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User
from backend.models.case import Case
from backend.models.narrative import Narrative
from backend.schemas.response_schema import NarrativeResponse
from backend.services.audit_service import AuditService, EventType

router = APIRouter(prefix="/api/v1/cases/{case_id}/narrative", tags=["narratives"])


class NarrativeEditRequest(BaseModel):
    content: str


@router.get("", response_model=NarrativeResponse)
def get_narrative(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the latest narrative version for a case."""
    narr = (
        db.query(Narrative)
        .filter(Narrative.case_id == case_id)
        .order_by(Narrative.version.desc())
        .first()
    )
    if not narr:
        raise HTTPException(404, "Narrative not found")
    return NarrativeResponse.model_validate(narr)


@router.put("", response_model=NarrativeResponse)
def edit_narrative(
    case_id: str,
    payload: NarrativeEditRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Edit narrative – creates a new version (immutable history)."""
    latest = (
        db.query(Narrative)
        .filter(Narrative.case_id == case_id)
        .order_by(Narrative.version.desc())
        .first()
    )
    new_version = (latest.version + 1) if latest else 1

    narr = Narrative(
        case_id=case_id,
        version=new_version,
        content=payload.content,
        llm_prompt=latest.llm_prompt if latest else None,
        rag_context=latest.rag_context if latest else None,
        status="draft",
        created_by=user.username,
    )
    db.add(narr)

    audit = AuditService(db)
    audit.log(case_id, EventType.NARRATIVE_EDITED, {
        "version": new_version,
        "edited_by": user.username,
        "content_preview": payload.content[:300],
        "previous_version": latest.version if latest else None,
    }, user.username)

    db.commit()
    db.refresh(narr)
    return NarrativeResponse.model_validate(narr)


@router.post("/approve", response_model=NarrativeResponse)
def approve_narrative(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Approve the latest narrative version."""
    narr = (
        db.query(Narrative)
        .filter(Narrative.case_id == case_id)
        .order_by(Narrative.version.desc())
        .first()
    )
    if not narr:
        raise HTTPException(404, "Narrative not found")

    narr.status = "approved"

    # Also update case status
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if case:
        case.status = "approved"

    audit = AuditService(db)
    audit.log(case_id, EventType.NARRATIVE_APPROVED, {
        "version": narr.version,
        "approved_by": user.username,
    }, user.username)

    db.commit()
    db.refresh(narr)
    return NarrativeResponse.model_validate(narr)


@router.post("/reject", response_model=NarrativeResponse)
def reject_narrative(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject the latest narrative version."""
    narr = (
        db.query(Narrative)
        .filter(Narrative.case_id == case_id)
        .order_by(Narrative.version.desc())
        .first()
    )
    if not narr:
        raise HTTPException(404, "Narrative not found")

    narr.status = "rejected"

    case = db.query(Case).filter(Case.case_id == case_id).first()
    if case:
        case.status = "rejected"

    audit = AuditService(db)
    audit.log(case_id, EventType.NARRATIVE_REJECTED, {
        "version": narr.version,
        "rejected_by": user.username,
    }, user.username)

    db.commit()
    db.refresh(narr)
    return NarrativeResponse.model_validate(narr)
