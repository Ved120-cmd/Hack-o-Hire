"""
Case Orchestrator
==================
Orchestrates the full SAR pipeline: ingest → normalise → rules → ML → RAG → narrative → audit.
Central coordination point for all services.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.case import Case
from backend.models.rule_evaluation import RuleEvaluation
from backend.models.claim import Claim
from backend.models.narrative import Narrative
from backend.models.alert import Alert
from backend.services.data_normalizer import DataNormalizer
from backend.services.rule_engine import RuleEngine
from backend.services.ml_classifier import MLClassifier
from backend.services.rag_service import RAGService
from backend.services.narrative_generator import NarrativeGenerator
from backend.services.audit_service import AuditService, EventType
from backend.schemas.input_schema import CaseInput

logger = logging.getLogger(__name__)


class CaseOrchestrator:
    """Full pipeline orchestrator."""

    def __init__(self, db: Session):
        self.db = db
        self.normalizer = DataNormalizer()
        self.rule_engine = RuleEngine()
        self.ml_classifier = MLClassifier()
        self.rag_service = RAGService()
        self.narrative_gen = NarrativeGenerator()
        self.audit = AuditService(db)

    def process_case(self, case_input: CaseInput, user_id: str) -> Dict[str, Any]:
        """
        Run the full SAR pipeline end-to-end.

        Steps:
        1. Create case record
        2. Normalise input
        3. Run rule engine
        4. ML classification
        5. RAG retrieval
        6. Narrative generation
        7. Create alerts if high risk
        8. Return summary
        """
        case_id = f"SAR-{uuid.uuid4().hex[:12].upper()}"
        logger.info("=== Pipeline start: %s ===", case_id)

        # ---- Step 1: Create case ----
        raw_input = case_input.model_dump(mode="json")
        case = Case(
            case_id=case_id,
            status="processing",
            raw_input=raw_input,
            created_by=user_id,
        )
        self.db.add(case)
        self.db.flush()

        self.audit.log(case_id, EventType.CASE_CREATED, {
            "raw_input_keys": list(raw_input.keys()),
            "customer_id": case_input.customer.customer_id,
            "alert_count": len(case_input.alerts),
        }, user_id)

        # ---- Step 2: Normalise ----
        normalized = self.normalizer.normalize(case_input)
        case.normalized_data = normalized

        self.audit.log(case_id, EventType.DATA_NORMALIZED, {
            "transaction_count": len(normalized.get("transactions", [])),
            "evidence_objects": normalized.get("evidence_objects", []),
            "aggregates": normalized.get("aggregates", {}),
        }, user_id)

        # ---- Step 3: Rule engine ----
        rule_result = self.rule_engine.evaluate(normalized)

        # Store rule evaluations
        for r in rule_result["triggered_rules"]:
            re = RuleEvaluation(
                case_id=case_id,
                rule_name=r["rule_name"],
                triggered=r["triggered"],
                evidence=r.get("evidence"),
                confidence=r.get("confidence", 0),
                risk_score=r.get("risk_contribution", 0),
                typology=r.get("typology"),
                reasoning=r.get("reasoning"),
                reasoning_artifact=r,
            )
            self.db.add(re)

        self.audit.log(case_id, EventType.RULES_EVALUATED, {
            "triggered_rules": rule_result["triggered_rules"],
            "risk_score": rule_result["risk_score"],
            "confidence_score": rule_result["confidence_score"],
            "typologies": rule_result["typologies"],
            "reasoning_artifact": rule_result["reasoning_artifact"],
        }, user_id)

        # ---- Step 4: ML classification ----
        ml_result = self.ml_classifier.classify(normalized, rule_result)

        case.risk_score = rule_result["risk_score"]
        case.risk_category = ml_result["risk_category"]
        case.ml_confidence = ml_result["ml_confidence"]

        self.audit.log(case_id, EventType.ML_SCORED, {
            "ml_confidence": ml_result["ml_confidence"],
            "risk_category": ml_result["risk_category"],
            "feature_vector": ml_result["feature_vector"],
            "feature_importances": ml_result["feature_importances"],
        }, user_id)

        # ---- Step 5: RAG retrieval ----
        rag_context = self.rag_service.retrieve_context(rule_result["claim_object"])

        self.audit.log(case_id, EventType.RAG_RETRIEVED, {
            "rag_context": {
                source: [{"content_preview": c["content"][:200], "metadata": c.get("metadata")}
                         for c in chunks]
                for source, chunks in rag_context.items()
                if isinstance(chunks, list)
            },
            "query_text": rag_context.get("query_text", ""),
        }, user_id)

        # ---- Step 6: Store claim ----
        claim = Claim(
            case_id=case_id,
            claim_object=rule_result["claim_object"],
            evidence_objects=normalized.get("evidence_objects"),
            risk_score=rule_result["risk_score"],
            ml_confidence=ml_result["ml_confidence"],
        )
        self.db.add(claim)

        # ---- Step 7: Narrative generation ----
        narr_result = self.narrative_gen.generate(
            claim_object=rule_result["claim_object"],
            rag_context=rag_context,
            rule_result=rule_result,
            ml_result=ml_result,
        )

        narrative = Narrative(
            case_id=case_id,
            version=1,
            content=narr_result["narrative"],
            llm_prompt=narr_result["llm_prompt"],
            rag_context={
                source: [c.get("content", "")[:500] for c in chunks]
                for source, chunks in rag_context.items()
                if isinstance(chunks, list)
            },
            status="draft",
            created_by="system",
        )
        self.db.add(narrative)

        self.audit.log(case_id, EventType.NARRATIVE_GENERATED, {
            "llm_provider": narr_result["llm_provider"],
            "is_fallback": narr_result["is_fallback"],
            "llm_prompt": narr_result["llm_prompt"][:1000],
            "narrative_preview": narr_result["narrative"][:500],
        }, user_id)

        # ---- Step 8: Alerts ----
        alerts_count = 0
        if rule_result["risk_score"] >= settings.RISK_ALERT_THRESHOLD:
            alert = Alert(
                case_id=case_id,
                alert_type="HIGH_RISK_SAR",
                risk_score=rule_result["risk_score"],
                message=(
                    f"High-risk case detected: {', '.join(rule_result['typologies'])}. "
                    f"Risk score: {rule_result['risk_score']:.2f}, "
                    f"ML confidence: {ml_result['ml_confidence']:.2f}"
                ),
            )
            self.db.add(alert)
            alerts_count = 1

            self.audit.log(case_id, EventType.ALERT_CREATED, {
                "alert_type": "HIGH_RISK_SAR",
                "risk_score": rule_result["risk_score"],
                "typologies": rule_result["typologies"],
            }, user_id)

        # ---- Finalise ----
        case.status = "pending_review"
        self.db.commit()

        logger.info("=== Pipeline complete: %s – risk=%s ===", case_id, ml_result["risk_category"])

        triggered_rule_names = [
            r["rule_name"] for r in rule_result["triggered_rules"] if r.get("triggered")
        ]

        return {
            "case_id": case_id,
            "status": "pending_review",
            "risk_score": rule_result["risk_score"],
            "risk_category": ml_result["risk_category"],
            "ml_confidence": ml_result["ml_confidence"],
            "triggered_rules": triggered_rule_names,
            "typologies": rule_result["typologies"],
            "narrative_preview": narr_result["narrative"][:500],
            "alerts_generated": alerts_count,
            "is_fallback_narrative": narr_result["is_fallback"],
        }
