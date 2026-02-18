"""
Audit Service
===============
Immutable, append-only audit log for full SAR pipeline traceability.
Every pipeline step is recorded for regulatory reconstruction.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


# Canonical event types
class EventType:
    CASE_CREATED = "CASE_CREATED"
    DATA_NORMALIZED = "DATA_NORMALIZED"
    RULES_EVALUATED = "RULES_EVALUATED"
    ML_SCORED = "ML_SCORED"
    RAG_RETRIEVED = "RAG_RETRIEVED"
    NARRATIVE_GENERATED = "NARRATIVE_GENERATED"
    NARRATIVE_EDITED = "NARRATIVE_EDITED"
    NARRATIVE_APPROVED = "NARRATIVE_APPROVED"
    NARRATIVE_REJECTED = "NARRATIVE_REJECTED"
    ALERT_CREATED = "ALERT_CREATED"
    CASE_STATUS_CHANGED = "CASE_STATUS_CHANGED"


class AuditService:
    """Append-only audit event logger."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        case_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: str = "system",
    ) -> AuditEvent:
        """
        Record an immutable audit event.

        Parameters
        ----------
        case_id : str
            The case this event belongs to
        event_type : str
            One of the EventType constants
        event_data : dict
            Arbitrary JSON payload – must capture enough data for
            full reconstruction of "why did the system write this?"
        user_id : str
            The user or system component that triggered the event
        """
        event = AuditEvent(
            case_id=case_id,
            event_type=event_type,
            event_data=event_data,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            immutable=True,
        )
        self.db.add(event)
        self.db.flush()  # get ID without committing (caller controls tx)

        logger.info(
            "Audit event recorded: case=%s type=%s id=%d",
            case_id, event_type, event.id,
        )
        return event

    def get_trail(self, case_id: str) -> list[Dict[str, Any]]:
        """Return full audit trail for a case, ordered by timestamp."""
        events = (
            self.db.query(AuditEvent)
            .filter(AuditEvent.case_id == case_id)
            .order_by(AuditEvent.timestamp.asc())
            .all()
        )
        return [
            {
                "id": e.id,
                "case_id": e.case_id,
                "event_type": e.event_type,
                "event_data": e.event_data,
                "user_id": e.user_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "immutable": e.immutable,
            }
            for e in events
        ]

    def reconstruct_sentence_reason(
        self, case_id: str, sentence_fragment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reconstruct WHY the system wrote a particular part of the narrative.

        Walks the audit trail to link:
        sentence → narrative generation event → LLM prompt → RAG context
        → rule evaluations → evidence objects → raw input
        """
        trail = self.get_trail(case_id)

        reconstruction = {
            "case_id": case_id,
            "query": sentence_fragment,
            "chain": [],
        }

        for event in trail:
            step = {
                "step": event["event_type"],
                "timestamp": event["timestamp"],
                "summary": self._summarize_event(event),
            }

            # Include relevant detail based on event type
            if event["event_type"] == EventType.NARRATIVE_GENERATED:
                step["llm_prompt_preview"] = (
                    event["event_data"].get("llm_prompt", "")[:500] + "..."
                )
                step["llm_provider"] = event["event_data"].get("llm_provider")
            elif event["event_type"] == EventType.RAG_RETRIEVED:
                step["retrieved_sources"] = [
                    c.get("metadata", {}).get("source_file", "unknown")
                    for ctx_list in event["event_data"].get("rag_context", {}).values()
                    if isinstance(ctx_list, list)
                    for c in ctx_list
                ]
            elif event["event_type"] == EventType.RULES_EVALUATED:
                step["triggered_rules"] = [
                    r["rule_name"]
                    for r in event["event_data"].get("triggered_rules", [])
                    if r.get("triggered")
                ]
            elif event["event_type"] == EventType.DATA_NORMALIZED:
                step["evidence_count"] = len(
                    event["event_data"].get("evidence_objects", [])
                )

            reconstruction["chain"].append(step)

        return reconstruction

    def _summarize_event(self, event: Dict) -> str:
        """One-line summary for audit chain display."""
        summaries = {
            EventType.CASE_CREATED: "Case ingested with raw input data",
            EventType.DATA_NORMALIZED: "Input normalised and evidence objects created",
            EventType.RULES_EVALUATED: "Deterministic rules evaluated against evidence",
            EventType.ML_SCORED: "ML classification applied for risk scoring",
            EventType.RAG_RETRIEVED: "Regulatory context retrieved from vector store",
            EventType.NARRATIVE_GENERATED: "SAR narrative generated by LLM/template",
            EventType.NARRATIVE_EDITED: "Analyst edited the narrative",
            EventType.NARRATIVE_APPROVED: "Narrative approved for filing",
            EventType.NARRATIVE_REJECTED: "Narrative rejected – needs revision",
            EventType.ALERT_CREATED: "High-risk alert generated",
        }
        return summaries.get(event["event_type"], event["event_type"])
