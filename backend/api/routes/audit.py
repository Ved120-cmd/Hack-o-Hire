"""
Audit Routes – view audit trail and reconstruct reasoning.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/cases/{case_id}/audit", tags=["audit"])


@router.get("")
def get_audit_trail(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full audit trail for a case."""
    audit = AuditService(db)
    trail = audit.get_trail(case_id)
    return trail


@router.get("/reconstruct")
def reconstruct_reason(
    case_id: str,
    sentence: Optional[str] = Query(None, description="Sentence fragment to trace"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reconstruct why the system generated a specific part of the narrative."""
    audit = AuditService(db)
    return audit.reconstruct_sentence_reason(case_id, sentence)
