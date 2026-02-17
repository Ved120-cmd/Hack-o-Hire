"""
SAR Claim Generator - Delta Stage (Production Version)
=====================================================

This module generates complete, auditable claim objects from upstream pipeline data.
The claim object serves as the structured input to the RAG pipeline and LLM for
SAR narrative generation.

Pipeline Position:
    Ingestion & Normalization → KYC Enrichment → Rules-Based Engine
    → Claim Generation (YOU ARE HERE) → Narrative Generation (RAG + LLM → SAR Narrative)

Main Purpose:
    Transform scattered detection signals (rules, ML scores, evidence) into a single,
    comprehensive claim object with:
    - Complete audit trail (who, what, when, why)
    - Cryptographic integrity (SHA-256 hashes)
    - All context needed for narrative generation
    - Regulatory compliance metadata
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from claim_gen.models.claim_schema import (
    AuditTrail,
    ClaimObject,
    EnvironmentEnum,
    StatusEnum,
)
from claim_gen.services.claim_population import ClaimPopulationService
from claim_gen.utils.hash_utils import (
    compute_claim_input_hash,
    compute_claim_output_hash,
    compute_data_lineage_hash,
    compute_pipeline_chain_hash,
)

# Configure structured logging for production monitoring
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ClaimGenerationError(Exception):
    """
    Custom exception for claim generation failures.
    
    Raised when claim generation fails due to:
    - Invalid input data
    - Missing required fields
    - Validation errors
    - Database errors
    """

    pass


class ClaimGenerator:
    """
    Main claim generation orchestrator.
    
    Responsibilities:
    1. Validate inputs from upstream stages (Beta, Gamma)
    2. Orchestrate field population via ClaimPopulationService
    3. Compute cryptographic hashes for integrity
    4. Assemble complete claim object
    5. Validate final output with Pydantic
    
    The generated claim object is then passed to:
    - Database for persistence (claim_storage.py)
    - RAG pipeline for context retrieval
    - LLM for SAR narrative expansion
    """

    def __init__(self):
        """Initialize claim generator with population service."""
        self.population_service = ClaimPopulationService()
        logger.info("ClaimGenerator initialized successfully")

    def generate_claim(
        self,
        case_id: str,
        alert_ids: List[str],
        customer_data: Dict[str, Any],
        pipeline_transforms: List[Dict[str, Any]],
        rule_results: Dict[str, Any],
        fraud_scores: Dict[str, Any],
        rag_results: Dict[str, Any],
        environment: str = "on-prem",
        jurisdiction: Optional[List[str]] = None,
        user_id: str = "system",
        model_versions: Optional[Dict[str, str]] = None,
        llm_metadata: Optional[Dict[str, Any]] = None,
        pii_controls: Optional[Dict[str, Any]] = None,
        rbac_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete SAR claim object from upstream pipeline data.
        
        This is the main entry point for claim generation. It takes outputs from
        all upstream stages and assembles them into a comprehensive claim object
        that contains everything needed for SAR narrative generation.
        
        Args:
            case_id: Unique case identifier from case management system
            alert_ids: List of alert IDs that triggered this case (from Alpha stage)
            customer_data: Customer profile from Beta stage containing:
                - customer_id, PAN, account numbers
                - KYC details (risk rating, PEP status, sanctions)
                - Accounts and counterparty information
            pipeline_transforms: Transform history from Alpha→Gamma stages showing
                data flow and transformations applied
            rule_results: Results from Gamma (rule engine) containing:
                - rules_matched: Which rules fired and with what strength
                - suspicious_patterns: Detected patterns (structuring, layering, etc.)
                - evidence_refs: Evidence items supporting the suspicion
            fraud_scores: ML model outputs containing:
                - model_scores: Raw scores from fraud detection models
                - shap_contributions: Feature importance via SHAP
                - risk_assessment: Overall risk score and typologies
            rag_results: RAG system outputs containing:
                - regulatory_references: Relevant regulation citations
                - template_ids: SAR templates to use
                - similarity_scores: How well regulations match
            environment: Deployment environment (on-prem, aws, multi-cloud)
            jurisdiction: Applicable jurisdictions (e.g., ["IN", "US"])
            user_id: ID of analyst/system generating claim
            model_versions: LLM and rules engine versions used
            llm_metadata: LLM generation metadata (prompts, tokens, temperature)
            pii_controls: PII detection/redaction status
            rbac_roles: Roles with access to this claim
            
        Returns:
            Complete claim object as dictionary containing:
            - All 12 schema sections (core IDs, subject, patterns, evidence, etc.)
            - Cryptographic hashes for integrity verification
            - Complete audit trail
            - Ready for RAG pipeline and LLM narrative generation
            
        Raises:
            ClaimGenerationError: If generation fails due to invalid/missing data
            
        Integration Points:
            INPUT from:  backend/rule_based_engine/services/rule_engine.py
            OUTPUT to:   backend/db/ (storage) + Omega stage (RAG + LLM)
        """
        try:
            logger.info(f"Starting claim generation for case_id: {case_id}")

            # ============================================================
            # STEP 1: SET DEFAULTS FOR OPTIONAL PARAMETERS
            # ============================================================
            # These provide sensible defaults if not provided by caller
            jurisdiction = jurisdiction or ["UK"]  # Default to UK
            model_versions = model_versions or {
                "llm": "llama-3.1-8b-instant",  # TODO: Get from config
                "rules": "v1.0",  # TODO: Get from rule_based_engine version
            }
            llm_metadata = llm_metadata or self._get_default_llm_metadata()
            pii_controls = pii_controls or self._get_default_pii_controls()
            rbac_roles = rbac_roles or ["compliance_analyst", "compliance_manager"]

            # ============================================================
            # STEP 2: VALIDATE INPUTS
            # ============================================================
            # Ensure all required data is present before proceeding
            # Prevents cryptic errors later in processing
            self._validate_inputs(case_id, alert_ids, customer_data)

            # ============================================================
            # STEP 3: COMPUTE CRYPTOGRAPHIC HASHES FOR AUDIT TRAIL
            # ============================================================
            # These hashes provide tamper-evident audit trail
            # Regulators can verify data integrity by recomputing hashes
            
            # Input hash: Proves what data went into claim generation
            input_hash = compute_claim_input_hash(
                case_id, alert_ids, customer_data, rule_results, fraud_scores
            )

            # Data lineage hash: Traces data provenance from source
            data_lineage_hash = compute_data_lineage_hash(
                case_id, alert_ids, customer_data
            )

            # Pipeline hash: Verifies all transforms were applied correctly
            pipeline_hash = compute_pipeline_chain_hash(pipeline_transforms)

            # ============================================================
            # STEP 4: POPULATE ALL CLAIM SECTIONS
            # ============================================================
            # Use ClaimPopulationService to map upstream data into claim structure
            # Each populate_* method handles one section of the claim schema
            logger.info("Populating claim components from upstream data")

            # Section 2: Subject & Context (customer, accounts, counterparties)
            subject = self.population_service.populate_subject(customer_data)

            # Section 3: Pipeline Traceability (alpha→beta→gamma transforms)
            transforms = self.population_service.populate_pipeline_transforms(
                pipeline_transforms
            )

            # Section 4: Suspicious Patterns (from Gamma rule engine)
            suspicious_patterns = self.population_service.populate_suspicious_patterns(
                rule_results.get("suspicious_patterns", [])
            )

            # Section 5: Evidence Set (transactions, events supporting suspicion)
            evidence_set = self.population_service.populate_evidence_set(
                rule_results.get("evidence_refs", [])
            )

            # Section 6: Detection Logic (which rules fired, which models scored)
            detection_logic = self.population_service.populate_detection_logic(
                rule_results, fraud_scores
            )

            # Section 7: Risk Assessment (overall score, typologies, severity)
            risk_assessment = self.population_service.populate_risk_assessment(
                fraud_scores.get("risk_assessment", {})
            )

            # Section 8: Regulatory Hooks (relevant regulations from RAG)
            regulatory_hooks = self.population_service.populate_regulatory_hooks(
                rag_results
            )

            # Section 9: LLM Generation Trace (for transparency and audit)
            generation_trace = self.population_service.populate_generation_trace(
                llm_metadata, rag_results
            )

            # Section 11: Security Controls (PII, RBAC, bias checking)
            security_controls = self.population_service.populate_security_controls(
                pii_controls, rbac_roles
            )

            # Section 1: Model Versions
            model_version = self.population_service.populate_model_version(model_versions)

            # ============================================================
            # STEP 5: ASSEMBLE CLAIM DICTIONARY
            # ============================================================
            # Create complete claim dict (without integrity hashes first)
            # We compute output hash after assembly to avoid circular dependency
            logger.info("Assembling complete claim object")

            claim_dict = {
                # Section 1: Core Identifiers & Metadata
                "case_id": case_id,
                "alert_ids": alert_ids,
                "environment": environment,
                "jurisdiction": jurisdiction,
                "model_version": model_version.model_dump(),
                "user_id": user_id,
                "data_lineage_hash": data_lineage_hash,
                
                # Section 2: Subject & Context
                "subject": subject.model_dump(),
                
                # Section 3: Pipeline Traceability
                "pipeline_transforms": [t.model_dump() for t in transforms],
                
                # Section 4: Suspicious Patterns
                "suspicious_patterns": [p.model_dump() for p in suspicious_patterns],
                
                # Section 5: Evidence Set
                "evidence_set": [e.model_dump() for e in evidence_set],
                
                # Section 6: Detection Logic
                "detection_logic": detection_logic.model_dump(),
                
                # Section 7: Risk Assessment
                "risk_assessment": risk_assessment.model_dump(),
                
                # Section 8: Regulatory Hooks
                "regulatory_hooks": [h.model_dump() for h in regulatory_hooks],
                
                # Section 9: LLM Generation Trace
                "generation_trace": generation_trace.model_dump(),
                
                # Section 10: Audit Trail (initially empty)
                "audit_trail": {"edits_history": [], "approvals": []},
                
                # Section 11: Security Controls
                "security_controls": security_controls.model_dump(),
                
                # Section 12: Integrity Hashes (computed below)
                "integrity_hashes": {
                    "input_hash": input_hash,
                    "output_hash": "",  # Computed next
                    "full_chain_hash": "",  # Computed after output hash
                },
            }

            # ============================================================
            # STEP 6: COMPUTE OUTPUT HASH
            # ============================================================
            # Hash the complete claim object (excluding integrity_hashes field
            # to avoid circular dependency)
            output_hash = compute_claim_output_hash(claim_dict)

            # Now populate complete integrity hashes section
            integrity_hashes = self.population_service.populate_integrity_hashes(
                input_hash, output_hash, pipeline_hash
            )
            claim_dict["integrity_hashes"] = integrity_hashes.model_dump()

            # ============================================================
            # STEP 7: VALIDATE WITH PYDANTIC
            # ============================================================
            # Final validation ensures all fields meet schema requirements
            # This catches any missing/invalid data before returning
            logger.info("Validating claim object with Pydantic schema")
            claim_object = ClaimObject(**claim_dict)

            logger.info(
                f"✅ Claim generation successful - claim_id: {claim_object.claim_id}"
            )
            logger.info(
                f"   Risk Score: {claim_object.risk_assessment.overall_risk_score}"
            )
            logger.info(
                f"   Severity: {claim_object.risk_assessment.severity_band}"
            )

            # Return as dictionary for JSON serialization
            # This format is ready for:
            # 1. Database storage (claim_storage.py)
            # 2. RAG pipeline input
            # 3. LLM context for narrative generation
            return claim_object.model_dump(mode="json")

        except Exception as e:
            # Log detailed error for debugging
            logger.error(f"❌ Claim generation failed: {str(e)}", exc_info=True)
            raise ClaimGenerationError(f"Failed to generate claim: {str(e)}") from e

    def _validate_inputs(
        self, case_id: str, alert_ids: List[str], customer_data: Dict[str, Any]
    ) -> None:
        """
        Validate required input parameters before processing.
        
        Checks:
        - case_id is not empty
        - At least one alert_id provided
        - customer_data contains required fields
        
        Args:
            case_id: Case identifier
            alert_ids: Alert identifiers
            customer_data: Customer data from Beta stage
            
        Raises:
            ClaimGenerationError: If validation fails
        """
        if not case_id:
            raise ClaimGenerationError("case_id is required and cannot be empty")

        if not alert_ids or len(alert_ids) == 0:
            raise ClaimGenerationError("At least one alert_id is required")

        if not customer_data:
            raise ClaimGenerationError("customer_data is required and cannot be empty")

        # Verify required customer fields are present
        required_customer_fields = ["customer_id", "kyc", "accounts"]
        for field in required_customer_fields:
            if field not in customer_data:
                raise ClaimGenerationError(
                    f"customer_data missing required field: {field}"
                )

    def _get_default_llm_metadata(self) -> Dict[str, Any]:
        """
        Get default LLM metadata structure.
        
        TODO: In production, this should come from actual LLM calls
        For now, provides structure for downstream systems
        
        Returns:
            Default LLM metadata dictionary
        """
        return {
            "prompt": "",  # TODO: Will be populated by Omega stage
            "reasoning_steps": [],  # TODO: Will be populated by Omega stage
            "token_usage": {"input": 0, "output": 0},
            "temperature": 0.7,
        }

    def _get_default_pii_controls(self) -> Dict[str, Any]:
        """
        Get default PII controls structure.
        
        TODO: In production, integrate with PII detection service
        
        Returns:
            Default PII controls dictionary
        """
        return {
            "redaction_mask": [],
            "pii_detected": 0,
            "pii_redacted": 0,
            "bias_check": {"unbiased": True, "flags": []},
        }


# ============================================================
# CONVENIENCE FUNCTION FOR DIRECT USAGE
# ============================================================

def generate_claim(
    case_id: str,
    alert_ids: List[str],
    customer_data: Dict[str, Any],
    pipeline_transforms: List[Dict[str, Any]],
    rule_results: Dict[str, Any],
    fraud_scores: Dict[str, Any],
    rag_results: Dict[str, Any],
    **kwargs,
) -> Dict[str, Any]:
    """
    Convenience function for generating claims without instantiating ClaimGenerator.
    
    This is the recommended way to use the claim generator:
    
    Example:
        from backend.claim_gen import generate_claim
        
        claim_object = generate_claim(
            case_id=case_id,
            alert_ids=alert_ids,
            customer_data=customer_data,  # From Beta stage
            pipeline_transforms=transforms,  # From Alpha→Gamma
            rule_results=rule_results,  # From Gamma
            fraud_scores=fraud_scores,  # From ML models
            rag_results=rag_results  # From RAG system
        )
        
        # claim_object is now ready for:
        # 1. Storage: claim_storage.save_claim(claim_object)
        # 2. RAG pipeline: Pass to context retrieval
        # 3. LLM: Pass to narrative generation
    
    Args:
        case_id: Case identifier
        alert_ids: Alert identifiers
        customer_data: Customer data from Beta stage
        pipeline_transforms: Transform history from Alpha→Gamma
        rule_results: Rule engine results from Gamma
        fraud_scores: Fraud model scores
        rag_results: RAG retrieval results
        **kwargs: Additional optional parameters (environment, jurisdiction, etc.)
        
    Returns:
        Complete claim object ready for downstream processing
    """
    generator = ClaimGenerator()
    return generator.generate_claim(
        case_id=case_id,
        alert_ids=alert_ids,
        customer_data=customer_data,
        pipeline_transforms=pipeline_transforms,
        rule_results=rule_results,
        fraud_scores=fraud_scores,
        rag_results=rag_results,
        **kwargs,
    )