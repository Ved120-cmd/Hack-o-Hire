"""
Case Audit Service

Tracks all case-related activities including creation, updates, 
alert additions, and status changes.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import json

from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity
from backend.services.audit.environment_tracker import environment_tracker
from fastapi import Request


class CaseAuditService:
    """
    Service for auditing case-related operations
    
    Tracks:
    - Case creation
    - Case updates
    - Alert additions
    - Status changes
    - Case viewing/access
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_case_created(
        self,
        case_id: str,
        case_number: str,
        user_id: str,
        user_email: str,
        initial_data: Dict[str, Any],
        request: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log case creation event
        
        Args:
            case_id: Unique case identifier
            case_number: Human-readable case number
            user_id: User who created the case
            user_email: User's email
            initial_data: Initial case data
            request: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.CASE_CREATED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request.client.host if request and request.client else None,
            session_id=session_id,
            case_id=case_id,
            case_number=case_number,
            case_status=initial_data.get("status", "new"),
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            screen_resolution=env_fields["screen_resolution"],
            timezone=env_fields["timezone"],
            application_version=env_fields["application_version"],
            request_payload=self._sanitize_payload(initial_data),
            tags=["case", "creation"],
            notes=f"New case created: {case_number}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_case_updated(
        self,
        case_id: str,
        user_id: str,
        user_email: str,
        changes: Dict[str, Any],
        reason: Optional[str] = None,
        request: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log case update event with before/after values
        
        Args:
            case_id: Case identifier
            user_id: User making the update
            user_email: User's email
            changes: Dictionary with before/after values
            reason: Reason for the update
            request: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        # Determine severity based on changes
        severity = AuditSeverity.MEDIUM
        if "status" in changes or "risk_level" in changes:
            severity = AuditSeverity.HIGH
        
        audit_entry = AuditLog(
            event_type=AuditEventType.CASE_UPDATED,
            event_timestamp=datetime.utcnow(),
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request.client.host if request and request.client else None,
            session_id=session_id,
            case_id=case_id,
            case_status=changes.get("status", {}).get("after"),
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            changes_made=changes,
            reason_for_change=reason,
            tags=["case", "update"],
            notes=f"Case {case_id} updated: {len(changes)} field(s) changed",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_alert_added(
        self,
        case_id: str,
        alert_ids: List[str],
        user_id: str,
        user_email: str,
        alert_details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log suspicious alert addition to case
        
        Args:
            case_id: Case identifier
            alert_ids: List of alert IDs being added
            user_id: User adding the alerts
            user_email: User's email
            alert_details: Additional alert information
            request: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.ALERT_ADDED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request.client.host if request and request.client else None,
            session_id=session_id,
            case_id=case_id,
            alert_ids=alert_ids,
            alert_count=len(alert_ids),
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            request_payload=self._sanitize_payload(alert_details) if alert_details else None,
            tags=["case", "alert", "suspicious_activity"],
            notes=f"Added {len(alert_ids)} suspicious alert(s) to case {case_id}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_case_viewed(
        self,
        case_id: str,
        user_id: str,
        user_email: str,
        request: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log case viewing/access event
        
        Args:
            case_id: Case identifier
            user_id: User viewing the case
            user_email: User's email
            request: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.CASE_VIEWED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.LOW,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request.client.host if request and request.client else None,
            session_id=session_id,
            case_id=case_id,
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            tags=["case", "access"],
            notes=f"Case {case_id} accessed by {user_id}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_alert_reviewed(
        self,
        case_id: str,
        alert_id: str,
        user_id: str,
        user_email: str,
        review_decision: str,
        review_notes: Optional[str] = None,
        request: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log alert review event
        
        Args:
            case_id: Case identifier
            alert_id: Alert being reviewed
            user_id: User reviewing the alert
            user_email: User's email
            review_decision: Decision made (e.g., 'escalate', 'dismiss', 'investigate')
            review_notes: Additional review notes
            request: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.ALERT_REVIEWED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request.client.host if request and request.client else None,
            session_id=session_id,
            case_id=case_id,
            alert_ids=[alert_id],
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            changes_made={
                "review_decision": review_decision,
                "review_notes": review_notes,
            },
            tags=["alert", "review", "decision"],
            notes=f"Alert {alert_id} reviewed with decision: {review_decision}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def get_case_audit_history(
        self,
        case_id: str,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get complete audit history for a case
        
        Args:
            case_id: Case identifier
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.case_id == case_id)
            .order_by(AuditLog.event_timestamp.desc())
            .limit(limit)
            .all()
        )
    
    def _sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from payload"""
        if not payload:
            return {}
        
        sanitized = payload.copy()
        
        # List of fields to redact
        sensitive_fields = [
            "password",
            "secret",
            "token",
            "api_key",
            "ssn",
            "credit_card",
        ]
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "[REDACTED]"
        
        return sanitized
