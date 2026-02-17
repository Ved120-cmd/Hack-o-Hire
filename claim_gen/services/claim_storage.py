"""
Claim Storage Service - Integrated with SQLAlchemy ORM
Matches the pattern from audit-trail-system backend
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from claim_gen.models.sar_claim_models import ClaimDB, ClaimAuditLog
from backend.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ClaimStorageError(Exception):
    """Custom exception for storage operations"""
    pass


class ClaimStorage:
    """
    PostgreSQL storage service for SAR claim objects using SQLAlchemy ORM.
    Integrates with existing audit-trail-system database pattern.
    """

    def __init__(self, db_session: Session, audit_service: Optional[AuditService] = None):
        """
        Initialize storage service with database session.
        
        Args:
            db_session: SQLAlchemy database session (from get_db())
            audit_service: Optional audit service for logging
        """
        self.db = db_session
        self.audit = audit_service
        logger.info("ClaimStorage initialized with SQLAlchemy session")

    def save_claim(self, claim_object: Dict[str, Any], user: str = "system") -> str:
        """
        Save claim object to database.
        
        Args:
            claim_object: Complete claim object dictionary
            user: User ID saving the claim
            
        Returns:
            claim_id of saved claim
            
        Raises:
            ClaimStorageError: If save operation fails
        """
        try:
            claim_id = claim_object["claim_id"]
            logger.info(f"Saving claim: {claim_id}")

            # Check if claim already exists
            existing_claim = self.db.query(ClaimDB).filter(
                ClaimDB.claim_id == claim_id
            ).first()

            if existing_claim:
                # Update existing claim
                existing_claim.timestamp_last_updated = datetime.utcnow()
                existing_claim.status = claim_object["status"]
                existing_claim.claim_data = claim_object
                existing_claim.updated_at = datetime.utcnow()
                
                action = "UPDATED"
                logger.info(f"Updating existing claim: {claim_id}")
            else:
                # Create new claim
                claim_db = ClaimDB(
                    claim_id=claim_id,
                    case_id=claim_object["case_id"],
                    alert_ids=claim_object["alert_ids"],
                    version=claim_object["version"],
                    timestamp_created=claim_object["timestamp_created"],
                    timestamp_last_updated=claim_object["timestamp_last_updated"],
                    stage=claim_object["stage"],
                    status=claim_object["status"],
                    environment=claim_object["environment"],
                    jurisdiction=claim_object["jurisdiction"],
                    user_id=claim_object["user_id"],
                    data_lineage_hash=claim_object["data_lineage_hash"],
                    
                    # Store complete claim object as JSONB
                    claim_data=claim_object,
                    
                    # Extract key fields for indexing/querying
                    risk_score=claim_object["risk_assessment"]["overall_risk_score"],
                    severity_band=claim_object["risk_assessment"]["severity_band"],
                    typologies=claim_object["risk_assessment"]["typologies"],
                )
                
                self.db.add(claim_db)
                action = "CREATED"
                logger.info(f"Creating new claim: {claim_id}")

            # Commit to database
            self.db.commit()

            # Log to audit trail using existing AuditService
            if self.audit:
                self.audit.log_action(
                    action="claim_saved",
                    component="claim_storage",
                    user=user,
                    case_id=int(claim_object["case_id"]) if claim_object["case_id"].isdigit() else None,
                    description=f"Claim {action.lower()}: {claim_id}",
                    details={
                        "claim_id": claim_id,
                        "action": action,
                        "risk_score": claim_object["risk_assessment"]["overall_risk_score"],
                        "severity": claim_object["risk_assessment"]["severity_band"],
                    },
                    claim_ids=[claim_id],
                    status="success"
                )

            # Create audit log entry in claims audit table
            self._log_audit_entry(
                claim_id=claim_id,
                action=action,
                actor_id=user,
                changes={"action": action, "claim_saved": True},
                reason=f"Claim {action.lower()} in Delta stage"
            )

            logger.info(f"✅ Claim saved successfully: {claim_id}")
            return claim_id

        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Failed to save claim: {str(e)}", exc_info=True)
            raise ClaimStorageError(f"Failed to save claim: {str(e)}") from e

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve claim by ID.
        
        Args:
            claim_id: Claim identifier
            
        Returns:
            Claim object dictionary or None if not found
        """
        try:
            claim_db = self.db.query(ClaimDB).filter(
                ClaimDB.claim_id == claim_id
            ).first()

            if claim_db:
                logger.info(f"Retrieved claim: {claim_id}")
                return claim_db.claim_data
            else:
                logger.warning(f"Claim not found: {claim_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to retrieve claim: {str(e)}")
            raise ClaimStorageError(f"Failed to retrieve claim: {str(e)}") from e

    def get_claims_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all claims for a case.
        
        Args:
            case_id: Case identifier
            
        Returns:
            List of claim objects
        """
        try:
            claims_db = self.db.query(ClaimDB).filter(
                ClaimDB.case_id == case_id
            ).order_by(ClaimDB.timestamp_created.desc()).all()

            logger.info(f"Retrieved {len(claims_db)} claims for case: {case_id}")
            return [claim.claim_data for claim in claims_db]

        except Exception as e:
            logger.error(f"Failed to retrieve claims: {str(e)}")
            raise ClaimStorageError(f"Failed to retrieve claims: {str(e)}") from e

    def update_claim_status(
        self,
        claim_id: str,
        new_status: str,
        user_id: str,
        reason: str = ""
    ) -> bool:
        """
        Update claim status with audit trail.
        
        Args:
            claim_id: Claim identifier
            new_status: New status (draft|analyst_review|approved|filed|rejected)
            user_id: User making the update
            reason: Reason for status change
            
        Returns:
            True if successful
        """
        try:
            claim_db = self.db.query(ClaimDB).filter(
                ClaimDB.claim_id == claim_id
            ).first()

            if not claim_db:
                raise ClaimStorageError(f"Claim not found: {claim_id}")

            old_status = claim_db.status
            claim_db.status = new_status
            claim_db.timestamp_last_updated = datetime.utcnow()
            claim_db.updated_at = datetime.utcnow()
            
            # Update status in claim_data JSONB as well
            claim_data = claim_db.claim_data
            claim_data["status"] = new_status
            claim_data["timestamp_last_updated"] = datetime.utcnow().isoformat()
            claim_db.claim_data = claim_data

            self.db.commit()

            # Log audit entry
            self._log_audit_entry(
                claim_id=claim_id,
                action="STATUS_CHANGED",
                actor_id=user_id,
                changes={"old_status": old_status, "new_status": new_status},
                reason=reason
            )

            # Log to main audit service
            if self.audit:
                self.audit.log_action(
                    action="claim_status_changed",
                    component="claim_storage",
                    user=user_id,
                    case_id=int(claim_db.case_id) if claim_db.case_id.isdigit() else None,
                    description=f"Claim status changed: {old_status} → {new_status}",
                    details={
                        "claim_id": claim_id,
                        "old_status": old_status,
                        "new_status": new_status,
                        "reason": reason
                    },
                    claim_ids=[claim_id],
                    status="success"
                )

            logger.info(f"Claim status updated: {claim_id} -> {new_status}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update claim status: {str(e)}")
            raise ClaimStorageError(f"Failed to update claim status: {str(e)}") from e

    def get_audit_trail(self, claim_id: str) -> List[Dict[str, Any]]:
        """
        Get complete audit trail for a claim.
        
        Args:
            claim_id: Claim identifier
            
        Returns:
            List of audit log entries
        """
        try:
            audit_logs = self.db.query(ClaimAuditLog).filter(
                ClaimAuditLog.claim_id == claim_id
            ).order_by(ClaimAuditLog.timestamp.desc()).all()

            logger.info(f"Retrieved {len(audit_logs)} audit entries for: {claim_id}")
            
            return [
                {
                    "audit_id": log.audit_id,
                    "claim_id": log.claim_id,
                    "action": log.action,
                    "actor_id": log.actor_id,
                    "timestamp": log.timestamp.isoformat(),
                    "changes": log.changes,
                    "reason": log.reason
                }
                for log in audit_logs
            ]

        except Exception as e:
            logger.error(f"Failed to retrieve audit trail: {str(e)}")
            raise ClaimStorageError(f"Failed to retrieve audit trail: {str(e)}") from e

    def search_claims(
        self,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        severity_band: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_risk_score: Optional[float] = None,
        typologies: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search claims with filters.
        
        Args:
            status: Filter by status
            environment: Filter by environment
            severity_band: Filter by severity (low|medium|high|critical)
            start_date: Filter by start date
            end_date: Filter by end date
            min_risk_score: Minimum risk score threshold
            typologies: Filter by typologies
            limit: Maximum results to return
            
        Returns:
            List of matching claims
        """
        try:
            query = self.db.query(ClaimDB)

            # Apply filters
            if status:
                query = query.filter(ClaimDB.status == status)

            if environment:
                query = query.filter(ClaimDB.environment == environment)
            
            if severity_band:
                query = query.filter(ClaimDB.severity_band == severity_band)

            if start_date:
                query = query.filter(ClaimDB.timestamp_created >= start_date)

            if end_date:
                query = query.filter(ClaimDB.timestamp_created <= end_date)
            
            if min_risk_score is not None:
                query = query.filter(ClaimDB.risk_score >= min_risk_score)
            
            if typologies:
                # Filter by typologies (JSONB array overlap)
                query = query.filter(ClaimDB.typologies.overlap(typologies))

            # Order and limit
            results = query.order_by(
                ClaimDB.timestamp_created.desc()
            ).limit(limit).all()

            logger.info(f"Search returned {len(results)} claims")
            return [claim.claim_data for claim in results]

        except Exception as e:
            logger.error(f"Claim search failed: {str(e)}")
            raise ClaimStorageError(f"Claim search failed: {str(e)}") from e

    def _log_audit_entry(
        self,
        claim_id: str,
        action: str,
        actor_id: str,
        changes: Dict[str, Any],
        reason: str
    ) -> None:
        """
        Log audit entry in claim_audit_log table (internal method).
        
        Args:
            claim_id: Claim identifier
            action: Action performed
            actor_id: User performing action
            changes: Changes made
            reason: Reason for action
        """
        try:
            audit_log = ClaimAuditLog(
                claim_id=claim_id,
                action=action,
                actor_id=actor_id,
                changes=changes,
                reason=reason
            )
            
            self.db.add(audit_log)
            # Note: Commit happens in parent transaction
            
        except Exception as e:
            logger.error(f"Failed to create audit log entry: {str(e)}")
            # Don't raise - audit logging failure shouldn't break main operation


# ============================================================
# CONVENIENCE FUNCTIONS (for backward compatibility)
# ============================================================

def get_storage(db_session: Session, audit_service: Optional[AuditService] = None) -> ClaimStorage:
    """
    Get ClaimStorage instance with database session.
    
    Usage:
        from backend.db.session import get_db
        from backend.claim_gen.services.claim_storage import get_storage
        
        db = next(get_db())
        storage = get_storage(db)
        storage.save_claim(claim_object)
    
    Args:
        db_session: SQLAlchemy session
        audit_service: Optional audit service
        
    Returns:
        ClaimStorage instance
    """
    return ClaimStorage(db_session, audit_service)