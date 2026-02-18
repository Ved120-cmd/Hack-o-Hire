"""
Response Schemas – Pydantic models for API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RuleEvaluationResponse(BaseModel):
    rule_name: str
    triggered: bool
    confidence: float
    typology: Optional[str] = None
    reasoning: Optional[str] = None
    evidence: Optional[Any] = None


class NarrativeResponse(BaseModel):
    id: int
    case_id: str
    version: int
    content: str
    status: str
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEventResponse(BaseModel):
    id: int
    case_id: str
    event_type: str
    event_data: Dict[str, Any]
    user_id: str
    timestamp: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    case_id: str
    alert_type: str
    risk_score: float
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class CaseResponse(BaseModel):
    id: int
    case_id: str
    status: str
    risk_score: Optional[float] = 0.0
    risk_category: Optional[str] = "Low"
    ml_confidence: Optional[float] = 0.0
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CaseDetailResponse(CaseResponse):
    raw_input: Any = None
    normalized_data: Optional[Any] = None
    rule_evaluations: List[RuleEvaluationResponse] = []
    narrative: Optional[NarrativeResponse] = None
    alerts: List[AlertResponse] = []


class PipelineResultResponse(BaseModel):
    case_id: str
    status: str
    risk_score: float
    risk_category: str
    ml_confidence: float
    triggered_rules: List[str]
    typologies: List[str] = []
    narrative_preview: str
    alerts_generated: int
    is_fallback_narrative: bool = False
