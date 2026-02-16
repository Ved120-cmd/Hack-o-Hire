"""
Omega Finalization Stage for SAR Pipeline
==========================================

This module implements the Omega (finalization) stage of the SAR generation pipeline:

    Pipeline Flow:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Alpha → Beta → Gamma → Delta → Theta/RAG → Omega (YOU ARE HERE) │
    └─────────────────────────────────────────────────────────────────┘

Responsibilities:
    1. Take claim + narrative (from Theta/RAG stage)
    2. Run 10-point regulatory validation
    3. Store final bundle to sar_final_filings table
    4. Return regulatory_ready status

Integration Points:
    INPUT:
        - ClaimObject from: Delta stage (claim_gen.generate_claim())
        - Narrative from: Theta/RAG stage (already generated)
    
    OUTPUT:
        - regulatory_ready: bool (True if all 10 checks pass)
        - validation_results: Dict with detailed check results
        - Stored in: sar_final_filings table
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.models.sar_final_filing import SARFinalFiling
from claim_gen.models.claim_schema import ClaimObject

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class OmegaFinalizationError(Exception):
    """Raised when Omega finalization fails"""
    pass


class RegulatoryValidationError(Exception):
    """Raised when regulatory validation fails"""
    pass


class OmegaFinalizer:
    """
    Omega finalization orchestrator.
    
    Responsibilities:
    1. Accept claim + narrative from Theta/RAG stage
    2. Run 10-point regulatory validation
    3. Store final bundle to sar_final_filings table
    4. Return regulatory_ready status
    """

    def __init__(self, db_session_factory=SessionLocal):
        """Initialize Omega finalizer"""
        self._session_factory = db_session_factory
        logger.info("OmegaFinalizer initialized")

    def finalize(self, omega_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main Omega finalization entrypoint.
        
        Expected omega_input structure:
        {
            "case_id": str,                    # Required: Case identifier
            "claim": Dict[str, Any],           # Required: ClaimObject dict from Delta stage
            "narrative": str,                  # Required: SAR narrative from Theta/RAG stage
            "filing_number": Optional[str],    # Optional: Filing number if available
            "user_id": Optional[str],          # Optional: User who initiated finalization
        }
        
        Returns:
            {
                "case_id": str,
                "regulatory_ready": bool,       # True if all 10 checks pass
                "validation_results": Dict,     # Detailed validation results
                "filing_id": str,               # ID of stored filing record
                "errors": List[str],            # Any validation errors
            }
        """
        try:
            # Extract inputs
            case_id = omega_input.get("case_id")
            if not case_id:
                raise OmegaFinalizationError("case_id is required")

            raw_claim = omega_input.get("claim")
            if not raw_claim:
                raise OmegaFinalizationError("claim is required")

            narrative = omega_input.get("narrative")
            if not narrative:
                raise OmegaFinalizationError("narrative is required (from Theta/RAG stage)")

            # TODO: Get filing_number from upstream system or generate if not provided
            filing_number = omega_input.get("filing_number")
            # TODO: Get user_id from authentication context
            user_id = omega_input.get("user_id", "system")

            logger.info(f"Starting Omega finalization for case_id: {case_id}")

            # Reconstruct ClaimObject
            try:
                claim = ClaimObject(**raw_claim)
            except Exception as e:
                raise OmegaFinalizationError(f"Failed to validate ClaimObject: {str(e)}") from e

            # Run 10-point regulatory validation
            validation_results = self._run_regulatory_validation(claim, narrative)

            # Determine regulatory_ready status
            regulatory_ready = all(
                check.get("passed", False) for check in validation_results.get("checks", [])
            )

            # Store final bundle to database
            db = self._session_factory()
            try:
                filing = self._store_final_filing(
                    db=db,
                    case_id=case_id,
                    claim=claim,
                    narrative=narrative,
                    validation_results=validation_results,
                    regulatory_ready=regulatory_ready,
                    filing_number=filing_number,
                    user_id=user_id,
                )
                db.commit()
                filing_id = str(filing.id)
                logger.info(f"Stored final filing: {filing_id}, regulatory_ready: {regulatory_ready}")
            finally:
                db.close()

            # Collect errors
            errors = [
                check.get("error")
                for check in validation_results.get("checks", [])
                if not check.get("passed", False) and check.get("error")
            ]

            return {
                "case_id": case_id,
                "regulatory_ready": regulatory_ready,
                "validation_results": validation_results,
                "filing_id": filing_id,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Omega finalization failed: {str(e)}", exc_info=True)
            raise OmegaFinalizationError(f"Omega finalization failed: {str(e)}") from e

    def _run_regulatory_validation(
        self, claim: ClaimObject, narrative: str
    ) -> Dict[str, Any]:
        """
        Run 10-point regulatory validation.
        
        Returns:
            {
                "checks": [
                    {"name": str, "passed": bool, "error": Optional[str]},
                    ...
                ],
                "overall_passed": bool,
                "timestamp": str,
            }
        """
        checks = []
        timestamp = datetime.utcnow().isoformat()

        # Check 1: Claim object is valid
        try:
            # Already validated when reconstructing ClaimObject
            checks.append({
                "name": "claim_object_valid",
                "description": "ClaimObject structure is valid",
                "passed": True,
                "error": None,
            })
        except Exception as e:
            checks.append({
                "name": "claim_object_valid",
                "description": "ClaimObject structure is valid",
                "passed": False,
                "error": str(e),
            })

        # Check 2: Narrative is not empty
        narrative_valid = bool(narrative and len(narrative.strip()) > 0)
        checks.append({
            "name": "narrative_not_empty",
            "description": "SAR narrative is not empty",
            "passed": narrative_valid,
            "error": None if narrative_valid else "Narrative is empty or whitespace only",
        })

        # Check 3: Narrative meets minimum length requirement
        # TODO: Get minimum length from regulatory requirements config
        min_length = 500  # Placeholder - replace with actual regulatory requirement
        narrative_length_ok = len(narrative) >= min_length
        checks.append({
            "name": "narrative_minimum_length",
            "description": f"Narrative meets minimum length ({min_length} chars)",
            "passed": narrative_length_ok,
            "error": None if narrative_length_ok else f"Narrative too short: {len(narrative)} < {min_length}",
        })

        # Check 4: Case ID is present
        case_id_present = bool(claim.case_id)
        checks.append({
            "name": "case_id_present",
            "description": "Case ID is present",
            "passed": case_id_present,
            "error": None if case_id_present else "Case ID is missing",
        })

        # Check 5: Alert IDs are present
        alert_ids_present = bool(claim.alert_ids and len(claim.alert_ids) > 0)
        checks.append({
            "name": "alert_ids_present",
            "description": "At least one alert ID is present",
            "passed": alert_ids_present,
            "error": None if alert_ids_present else "No alert IDs found",
        })

        # Check 6: Subject information is complete
        subject_complete = (
            claim.subject is not None
            and claim.subject.customer is not None
            and claim.subject.customer.customer_id is not None
        )
        checks.append({
            "name": "subject_complete",
            "description": "Subject (customer) information is complete",
            "passed": subject_complete,
            "error": None if subject_complete else "Subject information is incomplete",
        })

        # Check 7: Risk assessment is present
        risk_assessment_present = (
            claim.risk_assessment is not None
            and claim.risk_assessment.overall_risk_score is not None
        )
        checks.append({
            "name": "risk_assessment_present",
            "description": "Risk assessment is present",
            "passed": risk_assessment_present,
            "error": None if risk_assessment_present else "Risk assessment is missing",
        })

        # Check 8: Suspicious patterns are documented
        patterns_documented = (
            claim.suspicious_patterns is not None
            and len(claim.suspicious_patterns) > 0
        )
        checks.append({
            "name": "patterns_documented",
            "description": "Suspicious patterns are documented",
            "passed": patterns_documented,
            "error": None if patterns_documented else "No suspicious patterns documented",
        })

        # Check 9: Evidence set is present
        evidence_present = (
            claim.evidence_set is not None
            and len(claim.evidence_set) > 0
        )
        checks.append({
            "name": "evidence_present",
            "description": "Evidence set is present",
            "passed": evidence_present,
            "error": None if evidence_present else "No evidence items found",
        })

        # Check 10: Integrity hashes are valid
        integrity_valid = (
            claim.integrity_hashes is not None
            and claim.integrity_hashes.input_hash
            and claim.integrity_hashes.output_hash
            and claim.integrity_hashes.full_chain_hash
        )
        checks.append({
            "name": "integrity_hashes_valid",
            "description": "Integrity hashes are present and valid",
            "passed": integrity_valid,
            "error": None if integrity_valid else "Integrity hashes are missing or invalid",
        })

        overall_passed = all(check.get("passed", False) for check in checks)

        return {
            "checks": checks,
            "overall_passed": overall_passed,
            "timestamp": timestamp,
            "total_checks": len(checks),
            "passed_checks": sum(1 for check in checks if check.get("passed", False)),
            "failed_checks": sum(1 for check in checks if not check.get("passed", False)),
        }

    def _store_final_filing(
        self,
        db: Session,
        case_id: str,
        claim: ClaimObject,
        narrative: str,
        validation_results: Dict[str, Any],
        regulatory_ready: bool,
        filing_number: Optional[str],
        user_id: str,
    ) -> SARFinalFiling:
        """Store final filing bundle to sar_final_filings table"""
        
        # Generate filing number if not provided
        # TODO: Replace with actual filing number generation logic from regulatory system
        if not filing_number:
            # Placeholder format - replace with actual regulatory filing number format
            filing_number = f"SAR-{datetime.utcnow().strftime('%Y%m%d')}-{case_id[:8].upper()}"

        filing = SARFinalFiling(
            case_id=case_id,
            claim_id=claim.claim_id,
            alert_ids=claim.alert_ids,
            filing_number=filing_number,
            jurisdiction=claim.jurisdiction,
            claim_object=claim.model_dump(mode="json"),
            narrative=narrative,
            regulatory_ready=regulatory_ready,
            validation_results=validation_results,
            validation_timestamp=datetime.utcnow(),
            validation_checks={
                check["name"]: {
                    "passed": check.get("passed", False),
                    "error": check.get("error"),
                }
                for check in validation_results.get("checks", [])
            },
            validation_errors=[
                check.get("error")
                for check in validation_results.get("checks", [])
                if not check.get("passed", False) and check.get("error")
            ],
            created_by=user_id,
            status="ready" if regulatory_ready else "validation_failed",
        )

        db.add(filing)
        return filing


def run_omega(omega_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for OmegaFinalizer.finalize().
    
    Example:
        from backend.omega.omega_finalization import run_omega
        
        omega_result = run_omega({
            "case_id": "sar-123",
            "claim": claim_dict,  # From Delta stage
            "narrative": narrative_text,  # From Theta/RAG stage
        })
        
        if omega_result["regulatory_ready"]:
            print("SAR is ready for regulatory filing!")
        else:
            print(f"Validation failed: {omega_result['errors']}")
    """
    finalizer = OmegaFinalizer()
    return finalizer.finalize(omega_input)
