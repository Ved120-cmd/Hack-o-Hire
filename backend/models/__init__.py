"""
Models package – import all models so Base.metadata knows about them.
"""

from backend.models.user import User
from backend.models.case import Case
from backend.models.rule_evaluation import RuleEvaluation
from backend.models.claim import Claim
from backend.models.narrative import Narrative
from backend.models.audit_event import AuditEvent
from backend.models.alert import Alert

__all__ = [
    "User", "Case", "RuleEvaluation", "Claim",
    "Narrative", "AuditEvent", "Alert",
]
