"""
Claim Population Service - Maps upstream pipeline data to claim object fields
Implements enterprise-grade field population logic with validation
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from claim_gen.models.claim_schema import (
    Account,
    Approval,
    AuditTrail,
    BiasCheck,
    ChronologyEvent,
    Counterparties,
    Customer,
    CustomerIdentifiers,
    DetectionLogic,
    EditHistory,
    Evidence,
    GenerationTrace,
    IntegrityHashes,
    KYCDetails,
    ModelScore,
    ModelVersion,
    PipelineTransform,
    RegulatoryHook,
    RetrievalContext,
    RiskAssessment,
    RuleMatch,
    SecurityControls,
    Subject,
    SuspiciousPattern,
    TokenUsage,
    VelocityMetrics,
)
from claim_gen.utils.hash_utils import (
    compute_claim_input_hash,
    compute_data_lineage_hash,
    compute_pipeline_chain_hash,
)

logger = logging.getLogger(__name__)


class ClaimPopulationService:
    """Service for populating claim object fields from upstream data"""

    @staticmethod
    def populate_subject(customer_data: Dict[str, Any]) -> Subject:
        """
        Populate subject information from customer data

        Args:
            customer_data: Customer data from beta stage

        Returns:
            Populated Subject object
        """
        logger.info(f"Populating subject for customer: {customer_data.get('customer_id')}")

        # Extract customer identifiers
        identifiers = CustomerIdentifiers(
            pan=customer_data.get("pan", ""),
            account_nums=customer_data.get("account_numbers", []),
        )

        # Extract KYC details
        kyc_data = customer_data.get("kyc", {})
        kyc = KYCDetails(
            risk_rating=kyc_data.get("risk_rating", 0.0),
            risk_segment=kyc_data.get("risk_segment", "UNKNOWN"),
            onboarding_date=datetime.fromisoformat(
                kyc_data.get("onboarding_date", datetime.utcnow().isoformat())
            ),
            pep_status=kyc_data.get("pep_status", False),
            sanctions_screen=kyc_data.get("sanctions_screen", "CLEAR"),
            adverse_media=kyc_data.get("adverse_media", []),
        )

        # Create customer object
        customer = Customer(
            customer_id=customer_data.get("customer_id", ""),
            identifiers=identifiers,
            kyc=kyc,
            behavioral_segment=customer_data.get("behavioral_segment", "UNKNOWN"),
        )

        # Extract account information
        accounts = []
        for acc_data in customer_data.get("accounts", []):
            account = Account(
                account_id=acc_data.get("account_id", ""),
                type=acc_data.get("type", "UNKNOWN"),
                balance_at_alert=acc_data.get("balance", 0.0),
                opening_date=datetime.fromisoformat(
                    acc_data.get("opening_date", datetime.utcnow().isoformat())
                ),
            )
            accounts.append(account)

        # Extract counterparty infosrmation
        cp_data = customer_data.get("counterparties", {})
        counterparties = Counterparties(
            unique_count=cp_data.get("unique_count", 0),
            high_risk_count=cp_data.get("high_risk_count", 0),
            geo_distribution=cp_data.get("geo_distribution", {}),
            repeat_counterparties=cp_data.get("repeat_counterparties", 0),
        )

        return Subject(customer=customer, accounts=accounts, counterparties=counterparties)

    @staticmethod
    def populate_pipeline_transforms(
        transforms_data: List[Dict[str, Any]]
    ) -> List[PipelineTransform]:
        """
        Populate pipeline transform history

        Args:
            transforms_data: Transform data from alpha→gamma stages

        Returns:
            List of PipelineTransform objects
        """
        logger.info(f"Populating {len(transforms_data)} pipeline transforms")

        transforms = []
        for tf_data in transforms_data:
            transform = PipelineTransform(
                stage=tf_data.get("stage", ""),
                input=tf_data.get("input", ""),
                output=tf_data.get("output", ""),
                transform_rules_applied=tf_data.get("transform_rules_applied", []),
                input_size_bytes=tf_data.get("input_size_bytes", 0),
                output_size_bytes=tf_data.get("output_size_bytes", 0),
                timestamp=datetime.fromisoformat(
                    tf_data.get("timestamp", datetime.utcnow().isoformat())
                ),
                hash=tf_data.get("hash", ""),
            )
            transforms.append(transform)

        return transforms

    @staticmethod
    def populate_suspicious_patterns(
        patterns_data: List[Dict[str, Any]]
    ) -> List[SuspiciousPattern]:
        """
        Populate suspicious activity patterns

        Args:
            patterns_data: Pattern data from rule engine

        Returns:
            List of SuspiciousPattern objects
        """
        logger.info(f"Populating {len(patterns_data)} suspicious patterns")

        patterns = []
        for pattern_data in patterns_data:
            # Extract chronology events
            chronology = []
            for event_data in pattern_data.get("chronology", []):
                event = ChronologyEvent(
                    event=event_data.get("event", ""),
                    period=event_data.get("period", ""),
                    total=event_data.get("total", 0.0),
                )
                chronology.append(event)

            # Extract velocity metrics
            vm_data = pattern_data.get("velocity_metrics", {})
            velocity_metrics = VelocityMetrics(
                inflow_velocity=vm_data.get("inflow_velocity", 0.0),
                outflow_velocity=vm_data.get("outflow_velocity", 0.0),
                turnaround_time_hours=vm_data.get("turnaround_time_hours", 0.0),
            )

            pattern = SuspiciousPattern(
                summary=pattern_data.get("summary", ""),
                pattern_type=pattern_data.get("pattern_type", ""),
                chronology=chronology,
                velocity_metrics=velocity_metrics,
            )
            patterns.append(pattern)

        return patterns

    @staticmethod
    def populate_evidence_set(evidence_data: List[Dict[str, Any]]) -> List[Evidence]:
        """
        Populate normalized evidence set

        Args:
            evidence_data: Evidence references from omega stage

        Returns:
            List of Evidence objects
        """
        logger.info(f"Populating {len(evidence_data)} evidence items")

        evidence_set = []
        for ev_data in evidence_data:
            evidence = Evidence(
                evidence_id=ev_data.get("evidence_id", ""),
                primary_key=ev_data.get("primary_key", ""),
                type=ev_data.get("type", ""),
                timestamp=datetime.fromisoformat(
                    ev_data.get("timestamp", datetime.utcnow().isoformat())
                ),
                features_used=ev_data.get("features_used", {}),
                raw_value=ev_data.get("raw_value"),
                normalized_value=ev_data.get("normalized_value"),
            )
            evidence_set.append(evidence)

        return evidence_set

    @staticmethod
    def populate_detection_logic(
        rule_results: Dict[str, Any], fraud_scores: Dict[str, Any]
    ) -> DetectionLogic:
        """
        Populate detection logic from rule engine and fraud models

        Args:
            rule_results: Rule matching results from gamma stage
            fraud_scores: Fraud model outputs with SHAP values

        Returns:
            DetectionLogic object
        """
        logger.info("Populating detection logic")

        # Populate rules matched
        rules_matched = []
        for rule_data in rule_results.get("rules_matched", []):
            rule = RuleMatch(
                rule_id=rule_data.get("rule_id", ""),
                name=rule_data.get("name", ""),
                thresholds=rule_data.get("thresholds", {}),
                match_strength=rule_data.get("match_strength", 0.0),
                fired_timestamp=datetime.fromisoformat(
                    rule_data.get("fired_timestamp", datetime.utcnow().isoformat())
                ),
            )
            rules_matched.append(rule)

        # Populate model scores
        model_scores = []
        for model_data in fraud_scores.get("model_scores", []):
            score = ModelScore(
                model=model_data.get("model", ""),
                raw_score=model_data.get("raw_score", 0.0),
                shap_contributions=model_data.get("shap_contributions", {}),
            )
            model_scores.append(score)

        # Extract derived metrics
        derived_metrics = fraud_scores.get("derived_metrics", {})

        return DetectionLogic(
            rules_matched=rules_matched,
            model_scores=model_scores,
            derived_metrics=derived_metrics,
        )

    @staticmethod
    def populate_risk_assessment(risk_data: Dict[str, Any]) -> RiskAssessment:
        """
        Populate risk assessment

        Args:
            risk_data: Risk assessment data from fraud models

        Returns:
            RiskAssessment object
        """
        logger.info("Populating risk assessment")

        return RiskAssessment(
            overall_risk_score=risk_data.get("overall_risk_score", 0.0),
            typologies=risk_data.get("typologies", []),
            severity_band=risk_data.get("severity_band", "low"),
            confidence_level=risk_data.get("confidence_level", 0.0),
            predicate_offense=risk_data.get("predicate_offense", "UNKNOWN"),
        )

    @staticmethod
    def populate_regulatory_hooks(rag_results: Dict[str, Any]) -> List[RegulatoryHook]:
        """
        Populate regulatory hooks from RAG results

        Args:
            rag_results: RAG retrieval results with regulatory references

        Returns:
            List of RegulatoryHook objects
        """
        logger.info("Populating regulatory hooks")

        hooks = []
        for hook_data in rag_results.get("regulatory_references", []):
            hook = RegulatoryHook(
                doc_id=hook_data.get("doc_id", ""),
                paragraph=hook_data.get("paragraph", ""),
                similarity_score=hook_data.get("similarity_score", 0.0),
                jurisdiction=hook_data.get("jurisdiction", ""),
                retrieval_timestamp=datetime.fromisoformat(
                    hook_data.get("retrieval_timestamp", datetime.utcnow().isoformat())
                ),
            )
            hooks.append(hook)

        return hooks

    @staticmethod
    def populate_generation_trace(
        llm_data: Dict[str, Any], rag_results: Dict[str, Any]
    ) -> GenerationTrace:
        """
        Populate LLM generation trace for audit

        Args:
            llm_data: LLM generation metadata
            rag_results: RAG retrieval context

        Returns:
            GenerationTrace object
        """
        logger.info("Populating generation trace")

        token_usage = TokenUsage(
            input=llm_data.get("token_usage", {}).get("input", 0),
            output=llm_data.get("token_usage", {}).get("output", 0),
        )

        retrieval_context = RetrievalContext(
            template_ids=rag_results.get("template_ids", []),
            top_k=rag_results.get("top_k", 5),
            avg_similarity=rag_results.get("avg_similarity", 0.0),
        )

        return GenerationTrace(
            llm_prompt=llm_data.get("prompt", ""),
            intermediate_reasoning=llm_data.get("reasoning_steps", []),
            token_usage=token_usage,
            temperature=llm_data.get("temperature", 0.7),
            retrieval_context=retrieval_context,
        )

    @staticmethod
    def populate_security_controls(
        pii_data: Dict[str, Any], rbac_roles: List[str]
    ) -> SecurityControls:
        """
        Populate security and privacy controls

        Args:
            pii_data: PII detection and redaction data
            rbac_roles: RBAC roles with access

        Returns:
            SecurityControls object
        """
        logger.info("Populating security controls")

        bias_check = BiasCheck(
            unbiased=pii_data.get("bias_check", {}).get("unbiased", True),
            flags=pii_data.get("bias_check", {}).get("flags", []),
        )

        return SecurityControls(
            redaction_mask=pii_data.get("redaction_mask", []),
            pii_detected=pii_data.get("pii_detected", 0),
            pii_redacted=pii_data.get("pii_redacted", 0),
            rbac_roles_access=rbac_roles,
            bias_check=bias_check,
        )

    @staticmethod
    def populate_integrity_hashes(
        input_hash: str, output_hash: str, pipeline_hash: str
    ) -> IntegrityHashes:
        """
        Populate integrity verification hashes

        Args:
            input_hash: Input data hash
            output_hash: Output claim hash
            pipeline_hash: Pipeline chain hash

        Returns:
            IntegrityHashes object
        """
        from claim_gen.utils.hash_utils import compute_full_chain_hash

        logger.info("Populating integrity hashes")

        full_chain_hash = compute_full_chain_hash(input_hash, output_hash, pipeline_hash)

        return IntegrityHashes(
            input_hash=input_hash,
            output_hash=output_hash,
            full_chain_hash=full_chain_hash,
        )

    @staticmethod
    def populate_model_version(model_versions: Dict[str, str]) -> ModelVersion:
        """
        Populate model version information

        Args:
            model_versions: Dictionary with llm and rules versions

        Returns:
            ModelVersion object
        """
        return ModelVersion(
            llm=model_versions.get("llm", "unknown"),
            rules=model_versions.get("rules", "unknown"),
        )