"""
Case Routes – ingest, list, detail.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User
from backend.models.case import Case
from backend.models.rule_evaluation import RuleEvaluation
from backend.models.narrative import Narrative
from backend.models.alert import Alert
from backend.schemas.input_schema import CaseInput
from backend.schemas.response_schema import (
    CaseResponse, CaseDetailResponse, PipelineResultResponse,
    RuleEvaluationResponse, NarrativeResponse, AlertResponse,
)
from backend.services.case_orchestrator import CaseOrchestrator

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.post("/ingest", response_model=PipelineResultResponse)
def ingest_case(
    payload: CaseInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ingest a case and run the full SAR pipeline."""
    orchestrator = CaseOrchestrator(db)
    try:
        result = orchestrator.process_case(payload, user.username)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Pipeline failed: {str(e)}")
    return PipelineResultResponse(**result)


@router.get("", response_model=List[CaseResponse])
def list_cases(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all cases, newest first."""
    cases = db.query(Case).order_by(Case.created_at.desc()).all()
    return [CaseResponse.model_validate(c) for c in cases]


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full case detail including rules, narrative, alerts."""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    # Gather related data
    rules = db.query(RuleEvaluation).filter(RuleEvaluation.case_id == case_id).all()
    narr = (
        db.query(Narrative)
        .filter(Narrative.case_id == case_id)
        .order_by(Narrative.version.desc())
        .first()
    )
    alerts = db.query(Alert).filter(Alert.case_id == case_id).all()

    rule_responses = [
        RuleEvaluationResponse(
            rule_name=r.rule_name,
            triggered=r.triggered,
            confidence=r.confidence or 0,
            typology=r.typology,
            reasoning=r.reasoning,
            evidence=r.evidence,
        )
        for r in rules
    ]

    narr_response = NarrativeResponse.model_validate(narr) if narr else None
    alert_responses = [AlertResponse.model_validate(a) for a in alerts]

    return CaseDetailResponse(
        id=case.id,
        case_id=case.case_id,
        status=case.status,
        risk_score=case.risk_score or 0,
        risk_category=case.risk_category or "Low",
        ml_confidence=case.ml_confidence or 0,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
        raw_input=case.raw_input,
        normalized_data=case.normalized_data,
        rule_evaluations=rule_responses,
        narrative=narr_response,
        alerts=alert_responses,
    )
