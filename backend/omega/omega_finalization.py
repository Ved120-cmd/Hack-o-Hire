"""
Omega Finalization Stage for SAR Pipeline - Production Ready
============================================================

Pipeline Flow:
    Alpha → Beta → Gamma → Delta → Theta/RAG → OMEGA (YOU ARE HERE)

Responsibilities:
    1. Accept claim + narrative (from Theta/RAG stage)
    2. Run 10-point regulatory validation
    3. Store final bundle to sar_final_filings table
    4. Return regulatory_ready status

CRITICAL: This stage does NOT generate narratives - it validates and stores only.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.models.sar_final_filing import SARFinalFiling

# Import ClaimObject for validation
try:
    from claim_gen.models.claim_schema import ClaimObject
except ImportError:
    # Fallback if claim_gen not in path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
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


class RegulatoryConfig:
    """
    Regulatory compliance configuration.
    
    These values should be configured based on actual regulatory requirements.
    Replace placeholders with values from:
    - FinCEN regulations
    - BSA/AML requirements
    - Your jurisdiction's regulatory body
    """
    
    # Narrative minimum length (characters)
    NARRATIVE_MIN_LENGTH = int(os.getenv("SAR_NARRATIVE_MIN_LENGTH", "8000"))
    
    # Filing number format regex
    # TODO: Replace with actual regulatory format
    FILING_NUMBER_FORMAT = os.getenv("SAR_FILING_NUMBER_FORMAT", r"^UKFIU-\d{4}-\d{6}$")

    # Minimum number of validation checks that must pass
    # Default: 10 (all checks must pass)
    MIN_CHECKS_PASS = int(os.getenv("SAR_MIN_CHECKS_PASS", "10"))
    
    # Total number of validation checks
    TOTAL_CHECKS = 10


class OmegaFinalizer:
    """
    Omega finalization orchestrator.
    
    IMPORTANT: This class ONLY validates and stores.
    It does NOT generate narratives - that's done by Theta/RAG stage.
    
    Workflow:
    1. Accept claim (from Delta) + narrative (from Theta/RAG)
    2. Run 10-point regulatory validation
    3. Store final bundle to sar_final_filings table
    4. Return regulatory_ready status
    """

    def __init__(self, db_session_factory=SessionLocal):
        """Initialize Omega finalizer with database session factory"""
        self._session_factory = db_session_factory
        self.config = RegulatoryConfig()
        logger.info("OmegaFinalizer initialized")

    def finalize(self, omega_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main Omega finalization entrypoint.
        
        Expected omega_input structure:
        {
            "case_id": str,                    # Required: Case identifier
            "claim": Dict[str, Any],           # Required: ClaimObject dict from Delta
            "narrative": str,                  # Required: SAR narrative from Theta/RAG
            "filing_number": Optional[str],    # Optional: Pre-assigned filing number
            "user_id": Optional[str],          # Optional: User who initiated (default: "system")
        }
        
        Returns:
        {
            "case_id": str,
            "filing_id": str,                  # UUID of stored filing record
            "regulatory_ready": bool,          # True if 9+/10 checks pass
            "validation_results": {
                "checks": [{"name": str, "passed": bool, "error": str}, ...],
                "passed_checks": int,
                "failed_checks": int,
                "overall_passed": bool
            },
            "errors": List[str],               # List of validation errors (if any)
        }
        
        Raises:
            OmegaFinalizationError: If finalization fails
        """
        try:
            logger.info("=" * 80)
            logger.info("OMEGA FINALIZATION STARTED")
            logger.info("=" * 80)
            
            # ============================================================
            # STEP 1: VALIDATE INPUTS
            # ============================================================
            case_id = omega_input.get("case_id")
            if not case_id:
                raise OmegaFinalizationError("case_id is required")

            raw_claim = omega_input.get("claim")
            if not raw_claim:
                raise OmegaFinalizationError("claim is required (from Delta stage)")

            narrative = omega_input.get("narrative")
            if not narrative:
                raise OmegaFinalizationError(
                    "narrative is required (from Theta/RAG stage). "
                    "Omega does NOT generate narratives - it only validates and stores."
                )

            filing_number = omega_input.get("filing_number")
            user_id = omega_input.get("user_id", "system")

            logger.info(f"Case ID: {case_id}")
            logger.info(f"Narrative Length: {len(narrative)} characters")
            logger.info(f"User: {user_id}")

            # ============================================================
            # STEP 2: RECONSTRUCT & VALIDATE CLAIM OBJECT
            # ============================================================
            logger.info("Validating ClaimObject structure...")
            try:
                claim = ClaimObject(**raw_claim)
                logger.info("✅ ClaimObject validation passed")
            except Exception as e:
                logger.error(f"❌ ClaimObject validation failed: {e}")
                raise OmegaFinalizationError(
                    f"Failed to validate ClaimObject: {str(e)}"
                ) from e

            # ============================================================
            # STEP 3: RUN 10-POINT REGULATORY VALIDATION
            # ============================================================
            logger.info("Running 10-point regulatory validation...")
            validation_results = self._run_regulatory_validation(claim, narrative)
            
            passed = validation_results["passed_checks"]
            total = validation_results["total_checks"]
            logger.info(f"Validation Result: {passed}/{total} checks passed")

            # Determine regulatory_ready status
            # Requirement: 9/10 checks must pass (configurable via MIN_CHECKS_PASS)
            regulatory_ready = passed = self.config.MIN_CHECKS_PASS
            
            if regulatory_ready:
                logger.info("✅ REGULATORY READY: SAR bundle passes compliance checks")
            else:
                logger.warning(f"⚠️  NOT REGULATORY READY: Only {passed}/10 checks passed (need {self.config.MIN_CHECKS_PASS})")

            # ============================================================
            # STEP 4: STORE TO DATABASE (sar_final_filings table)
            # ============================================================
            logger.info("Storing final filing bundle to database...")
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
                logger.info(f"✅ Stored filing: {filing_id}")
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Database storage failed: {e}")
                raise OmegaFinalizationError(f"Failed to store filing: {e}") from e
            finally:
                db.close()

            # ============================================================
            # STEP 5: COLLECT ERRORS
            # ============================================================
            errors = [
                check.get("error")
                for check in validation_results.get("checks", [])
                if not check.get("passed", False) and check.get("error")
            ]

            # ============================================================
            # STEP 6: RETURN RESULT
            # ============================================================
            logger.info("=" * 80)
            logger.info("OMEGA FINALIZATION COMPLETED")
            logger.info("=" * 80)
            logger.info(f"Filing ID: {filing_id}")
            logger.info(f"Regulatory Ready: {regulatory_ready}")
            logger.info(f"Validation: {passed}/{total} checks passed")
            
            return {
                "case_id": case_id,
                "filing_id": filing_id,
                "regulatory_ready": regulatory_ready,
                "validation_results": validation_results,
                "errors": errors,
            }

        except OmegaFinalizationError:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error in Omega finalization: {e}", exc_info=True)
            raise OmegaFinalizationError(
                f"Unexpected error in Omega finalization: {str(e)}"
            ) from e

    def _run_regulatory_validation(
        self, claim: ClaimObject, narrative: str
    ) -> Dict[str, Any]:
        """
        Run 10-point regulatory validation checklist.
        
        Each check validates a critical regulatory requirement.
        
        Returns:
            {
                "checks": [
                    {"name": str, "description": str, "passed": bool, "error": Optional[str]},
                    ...  # 10 checks total
                ],
                "passed_checks": int,
                "failed_checks": int,
                "total_checks": int,
                "overall_passed": bool,
                "timestamp": str,
            }
        """
        checks = []
        timestamp = datetime.utcnow().isoformat()

        # ============================================================
        # CHECK 1: ClaimObject Structure Valid
        # ============================================================
        # Already validated when reconstructing, so this always passes
        checks.append({
            "name": "claim_object_valid",
            "description": "ClaimObject structure is valid (Pydantic validation)",
            "passed": True,
            "error": None,
        })

        # ============================================================
        # CHECK 2: Narrative Not Empty
        # ============================================================
        narrative_not_empty = bool(narrative and len(narrative.strip()) > 0)
        checks.append({
            "name": "narrative_not_empty",
            "description": "SAR narrative is not empty",
            "passed": narrative_not_empty,
            "error": None if narrative_not_empty else "Narrative is empty or whitespace only",
        })

        # ============================================================
        # CHECK 3: Narrative Minimum Length
        # ============================================================
        min_length = self.config.NARRATIVE_MIN_LENGTH
        narrative_length_ok = len(narrative) >= min_length
        checks.append({
            "name": "narrative_minimum_length",
            "description": f"Narrative meets minimum length requirement ({min_length} chars)",
            "passed": narrative_length_ok,
            "error": None if narrative_length_ok else 
                f"Narrative too short: {len(narrative)} chars < {min_length} chars (regulatory minimum)",
        })

        # ============================================================
        # CHECK 4: Case ID Present
        # ============================================================
        case_id_present = bool(claim.case_id)
        checks.append({
            "name": "case_id_present",
            "description": "Case ID is present and not empty",
            "passed": case_id_present,
            "error": None if case_id_present else "Case ID is missing",
        })

        # ============================================================
        # CHECK 5: Alert IDs Present
        # ============================================================
        alert_ids_present = bool(claim.alert_ids and len(claim.alert_ids) > 0)
        checks.append({
            "name": "alert_ids_present",
            "description": "At least one alert ID is present",
            "passed": alert_ids_present,
            "error": None if alert_ids_present else "No alert IDs found - SAR must be triggered by alerts",
        })

        # ============================================================
        # CHECK 6: Subject Information Complete
        # ============================================================
        subject_complete = (
            claim.subject is not None
            and claim.subject.customer is not None
            and claim.subject.customer.customer_id is not None
            and claim.subject.customer.identifiers is not None
        )
        checks.append({
            "name": "subject_complete",
            "description": "Subject (customer) information is complete",
            "passed": subject_complete,
            "error": None if subject_complete else "Subject information incomplete - customer ID and identifiers required",
        })

        # ============================================================
        # CHECK 7: Risk Assessment Present
        # ============================================================
        risk_assessment_present = (
            claim.risk_assessment is not None
            and claim.risk_assessment.overall_risk_score is not None
            and claim.risk_assessment.typologies is not None
            and len(claim.risk_assessment.typologies) > 0
        )
        checks.append({
            "name": "risk_assessment_present",
            "description": "Risk assessment is complete with score and typologies",
            "passed": risk_assessment_present,
            "error": None if risk_assessment_present else "Risk assessment incomplete - score and typologies required",
        })

        # ============================================================
        # CHECK 8: Suspicious Patterns Documented
        # ============================================================
        patterns_documented = (
            claim.suspicious_patterns is not None
            and len(claim.suspicious_patterns) > 0
        )
        checks.append({
            "name": "patterns_documented",
            "description": "Suspicious patterns are documented",
            "passed": patterns_documented,
            "error": None if patterns_documented else "No suspicious patterns documented - must document detected patterns",
        })

        # ============================================================
        # CHECK 9: Evidence Set Present
        # ============================================================
        evidence_present = (
            claim.evidence_set is not None
            and len(claim.evidence_set) > 0
        )
        checks.append({
            "name": "evidence_present",
            "description": "Evidence set is present and not empty",
            "passed": evidence_present,
            "error": None if evidence_present else "No evidence items found - must provide supporting evidence",
        })

        # ============================================================
        # CHECK 10: Integrity Hashes Valid
        # ============================================================
        integrity_valid = (
            claim.integrity_hashes is not None
            and claim.integrity_hashes.input_hash
            and claim.integrity_hashes.output_hash
            and claim.integrity_hashes.full_chain_hash
            and len(claim.integrity_hashes.output_hash) == 64  # SHA-256 = 64 hex chars
        )
        checks.append({
            "name": "integrity_hashes_valid",
            "description": "Integrity hashes are present and valid (SHA-256)",
            "passed": integrity_valid,
            "error": None if integrity_valid else "Integrity hashes missing or invalid - audit trail compromised",
        })

        # ============================================================
        # COMPUTE OVERALL RESULTS
        # ============================================================
        passed_checks = sum(1 for check in checks if check.get("passed", False))
        failed_checks = len(checks) - passed_checks
        overall_passed = passed_checks >= self.config.MIN_CHECKS_PASS

        return {
            "checks": checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "total_checks": self.config.TOTAL_CHECKS,
            "overall_passed": overall_passed,
            "timestamp": timestamp,
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
        """
        Store final filing bundle to sar_final_filings table.
        
        This creates an IMMUTABLE record of the validated SAR bundle.
        Once stored, it should NOT be modified (INSERT-only, no UPDATE).
        """
        
        # Generate filing number if not provided
        if not filing_number:
            # Format: SAR-YYYYMMDD-CASEID (first 8 chars uppercase)
            filing_number = f"UKFIU-{datetime.utcnow().year}-{case_id[:6].zfill(6)}"
            logger.info(f"Generated filing number: {filing_number}")

        # Create filing record
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
    
    This is the recommended entry point for Omega finalization.
    
    Example Usage:
        from backend.omega.omega_finalization import run_omega
        
        # Inputs from upstream stages
        claim_dict = delta_stage.generate_claim(...)  # From Delta
        narrative = theta_rag.generate_narrative(...)  # From Theta/RAG
        
        # Run Omega validation and storage
        result = run_omega({
            "case_id": "sar-123",
            "claim": claim_dict,
            "narrative": narrative,
        })
        
        if result["regulatory_ready"]:
            print("✅ SAR is ready for regulatory filing!")
            print(f"Filing ID: {result['filing_id']}")
        else:
            print("⚠️  Validation failed:")
            for error in result["errors"]:
                print(f"  - {error}")
    
    Args:
        omega_input: Dictionary with case_id, claim, narrative
        
    Returns:
        Dictionary with regulatory_ready status and validation results
    """
    finalizer = OmegaFinalizer()
    return finalizer.finalize(omega_input)