"""
SAR Audit Service - MOST CRITICAL COMPONENT

This service provides comprehensive audit trail for SAR (Suspicious Activity Report)
generation, including AI reasoning, report content, and regulatory compliance tracking.

This is the core compliance component that ensures full traceability of all SAR
generation activities as required by FinCEN and other regulatory bodies.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import time

from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity
from backend.services.audit.environment_tracker import environment_tracker
from fastapi import Request


class SARAuditService:
    """
    Comprehensive audit service for SAR report generation
    
    This service ensures complete traceability of:
    - SAR generation requests
    - AI reasoning generation
    - Final SAR report creation
    - Review and submission processes
    - Any failures or errors
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_sar_generation_started(
        self,
        case_id: str,
        alert_ids: List[str],
        user_id: str,
        user_email: str,
        request_data: Dict[str, Any],
        request_obj: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log the start of SAR generation process
        
        Args:
            case_id: Case identifier
            alert_ids: List of suspicious alert IDs
            user_id: User initiating SAR generation
            user_email: User's email
            request_data: Complete request data for SAR generation
            request_obj: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request_obj)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.SAR_GENERATION_STARTED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request_obj.client.host if request_obj and request_obj.client else None,
            session_id=session_id,
            case_id=case_id,
            alert_ids=alert_ids,
            alert_count=len(alert_ids),
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            screen_resolution=env_fields["screen_resolution"],
            timezone=env_fields["timezone"],
            application_version=env_fields["application_version"],
            sar_request_data=self._sanitize_sar_request(request_data),
            compliance_flags={
                "regulatory_body": "FinCEN",
                "report_type": "SAR",
                "generation_method": "AI-assisted",
            },
            regulatory_requirements={
                "BSA": "Bank Secrecy Act compliance",
                "FinCEN_SAR": "FinCEN SAR filing requirements",
            },
            tags=["sar", "generation", "started", "critical"],
            notes=f"SAR generation initiated for case {case_id} with {len(alert_ids)} alerts",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_sar_reasoning_generated(
        self,
        case_id: str,
        alert_ids: List[str],
        user_id: str,
        user_email: str,
        reasoning_text: str,
        reasoning_metadata: Dict[str, Any],
        processing_time_ms: int,
        generation_audit_id: Optional[str] = None,
        request_obj: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log AI-generated reasoning for suspicious activity
        
        This is CRITICAL for regulatory compliance as it captures the
        reasoning behind flagging activities as suspicious.
        
        Args:
            case_id: Case identifier
            alert_ids: List of alert IDs
            user_id: User ID
            user_email: User's email
            reasoning_text: The complete AI-generated reasoning
            reasoning_metadata: Metadata about reasoning generation
                - model_name: AI model used
                - model_version: Model version
                - prompt_tokens: Number of input tokens
                - completion_tokens: Number of output tokens
                - temperature: Model temperature
                - confidence_score: Confidence in reasoning
            processing_time_ms: Time taken to generate reasoning
            generation_audit_id: ID of the SAR generation start audit entry
            request_obj: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request_obj)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        # Link to the generation start event
        related_ids = []
        if generation_audit_id:
            related_ids.append(generation_audit_id)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.SAR_REASONING_GENERATED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request_obj.client.host if request_obj and request_obj.client else None,
            session_id=session_id,
            case_id=case_id,
            alert_ids=alert_ids,
            alert_count=len(alert_ids),
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            sar_reasoning=reasoning_text,
            sar_reasoning_metadata=reasoning_metadata,
            processing_duration_ms=processing_time_ms,
            compliance_flags={
                "ai_generated": True,
                "human_reviewed": False,
                "regulatory_compliant": True,
            },
            related_audit_ids=related_ids,
            tags=["sar", "reasoning", "ai_generated", "critical"],
            notes=f"AI reasoning generated for case {case_id}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_sar_report_generated(
        self,
        case_id: str,
        alert_ids: List[str],
        user_id: str,
        user_email: str,
        report_content: str,
        report_metadata: Dict[str, Any],
        processing_time_ms: int,
        reasoning_audit_id: Optional[str] = None,
        request_obj: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log complete SAR report generation
        
        This captures the final SAR report that will be filed with regulators.
        CRITICAL for maintaining complete audit trail.
        
        Args:
            case_id: Case identifier
            alert_ids: List of alert IDs
            user_id: User ID
            user_email: User's email
            report_content: Complete SAR report content
            report_metadata: Metadata about report
                - format: Report format (PDF, XML, etc.)
                - sections: List of report sections
                - form_type: SAR form type
                - generation_method: How report was generated
            processing_time_ms: Time taken to generate report
            reasoning_audit_id: ID of reasoning generation audit entry
            request_obj: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request_obj)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        # Link to related audit entries
        related_ids = []
        if reasoning_audit_id:
            related_ids.append(reasoning_audit_id)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.SAR_REPORT_GENERATED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request_obj.client.host if request_obj and request_obj.client else None,
            session_id=session_id,
            case_id=case_id,
            alert_ids=alert_ids,
            alert_count=len(alert_ids),
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            sar_report_content=report_content,
            sar_report_metadata=report_metadata,
            processing_duration_ms=processing_time_ms,
            compliance_flags={
                "report_generated": True,
                "ready_for_review": True,
                "needs_submission": True,
            },
            regulatory_requirements={
                "BSA_compliance": True,
                "FinCEN_format": report_metadata.get("format"),
            },
            related_audit_ids=related_ids,
            tags=["sar", "report", "generated", "critical"],
            notes=f"Complete SAR report generated for case {case_id}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_sar_report_reviewed(
        self,
        case_id: str,
        user_id: str,
        user_email: str,
        user_role: str,
        review_decision: str,
        review_comments: Optional[str] = None,
        changes_requested: Optional[List[str]] = None,
        report_audit_id: Optional[str] = None,
        request_obj: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log SAR report review event
        
        Captures compliance officer or supervisor review of generated SAR.
        
        Args:
            case_id: Case identifier
            user_id: Reviewer user ID
            user_email: Reviewer email
            user_role: Reviewer role (e.g., 'compliance_officer', 'supervisor')
            review_decision: Decision ('approved', 'rejected', 'needs_revision')
            review_comments: Reviewer's comments
            changes_requested: List of requested changes
            report_audit_id: ID of report generation audit entry
            request_obj: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request_obj)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        related_ids = []
        if report_audit_id:
            related_ids.append(report_audit_id)
        
        severity = AuditSeverity.CRITICAL
        if review_decision == "rejected":
            severity = AuditSeverity.CRITICAL
        
        audit_entry = AuditLog(
            event_type=AuditEventType.SAR_REPORT_REVIEWED,
            event_timestamp=datetime.utcnow(),
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            user_ip_address=request_obj.client.host if request_obj and request_obj.client else None,
            session_id=session_id,
            case_id=case_id,
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            changes_made={
                "review_decision": review_decision,
                "review_comments": review_comments,
                "changes_requested": changes_requested,
            },
            compliance_flags={
                "reviewed": True,
                "reviewer_role": user_role,
                "approved": review_decision == "approved",
            },
            related_audit_ids=related_ids,
            tags=["sar", "review", review_decision, "critical"],
            notes=f"SAR report reviewed by {user_role}: {review_decision}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_sar_report_submitted(
        self,
        case_id: str,
        user_id: str,
        user_email: str,
        filing_number: str,
        submission_metadata: Dict[str, Any],
        report_audit_id: Optional[str] = None,
        request_obj: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log SAR report submission to regulatory authority
        
        This is the final step in the SAR lifecycle and MUST be audited.
        
        Args:
            case_id: Case identifier
            user_id: User submitting the report
            user_email: User's email
            filing_number: Official SAR filing number from FinCEN
            submission_metadata: Submission details
                - submission_date: When submitted
                - submission_method: How submitted (electronic, paper)
                - regulatory_body: Where submitted (FinCEN, etc.)
                - confirmation_number: Confirmation from regulatory body
            report_audit_id: ID of report generation audit entry
            request_obj: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request_obj)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        related_ids = []
        if report_audit_id:
            related_ids.append(report_audit_id)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.SAR_REPORT_SUBMITTED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request_obj.client.host if request_obj and request_obj.client else None,
            session_id=session_id,
            case_id=case_id,
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            sar_filing_number=filing_number,
            sar_report_metadata=submission_metadata,
            compliance_flags={
                "submitted": True,
                "filing_complete": True,
                "regulatory_acknowledged": submission_metadata.get("confirmation_number") is not None,
            },
            regulatory_requirements={
                "BSA_filed": True,
                "FinCEN_filing_number": filing_number,
                "submission_date": submission_metadata.get("submission_date"),
            },
            related_audit_ids=related_ids,
            retention_category="regulatory_filing",
            tags=["sar", "submitted", "filed", "critical"],
            notes=f"SAR filed with number: {filing_number}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def log_sar_generation_failed(
        self,
        case_id: str,
        alert_ids: List[str],
        user_id: str,
        user_email: str,
        error_message: str,
        error_details: Dict[str, Any],
        stack_trace: Optional[str] = None,
        generation_audit_id: Optional[str] = None,
        request_obj: Optional[Request] = None,
        session_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Log SAR generation failure
        
        Critical for debugging and compliance - captures why SAR generation failed.
        
        Args:
            case_id: Case identifier
            alert_ids: List of alert IDs
            user_id: User ID
            user_email: User's email
            error_message: Error message
            error_details: Additional error details
            stack_trace: Full stack trace if available
            generation_audit_id: ID of generation start audit entry
            request_obj: HTTP request object
            session_id: Session identifier
            
        Returns:
            Created audit log entry
        """
        env_data = environment_tracker.capture_environment(request_obj)
        env_fields = environment_tracker.extract_key_environment_fields(env_data)
        
        related_ids = []
        if generation_audit_id:
            related_ids.append(generation_audit_id)
        
        audit_entry = AuditLog(
            event_type=AuditEventType.SAR_GENERATION_FAILED,
            event_timestamp=datetime.utcnow(),
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            user_ip_address=request_obj.client.host if request_obj and request_obj.client else None,
            session_id=session_id,
            case_id=case_id,
            alert_ids=alert_ids,
            alert_count=len(alert_ids),
            environment_data=env_data,
            browser_info=env_fields["browser_info"],
            os_info=env_fields["os_info"],
            device_type=env_fields["device_type"],
            error_occurred=True,
            error_message=error_message,
            error_stack_trace=stack_trace,
            sar_report_metadata=error_details,
            compliance_flags={
                "generation_failed": True,
                "requires_investigation": True,
            },
            related_audit_ids=related_ids,
            tags=["sar", "error", "failed", "critical"],
            notes=f"SAR generation failed for case {case_id}: {error_message}",
        )
        
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(audit_entry)
        
        return audit_entry
    
    def get_sar_audit_trail(
        self,
        case_id: str,
        include_related: bool = True,
    ) -> List[AuditLog]:
        """
        Get complete SAR audit trail for a case
        
        Args:
            case_id: Case identifier
            include_related: Whether to include related audit entries
            
        Returns:
            List of SAR-related audit log entries in chronological order
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.case_id == case_id,
            AuditLog.event_type.in_([
                AuditEventType.SAR_GENERATION_STARTED,
                AuditEventType.SAR_REASONING_GENERATED,
                AuditEventType.SAR_REPORT_GENERATED,
                AuditEventType.SAR_REPORT_REVIEWED,
                AuditEventType.SAR_REPORT_SUBMITTED,
                AuditEventType.SAR_GENERATION_FAILED,
            ])
        )
        
        return query.order_by(AuditLog.event_timestamp.asc()).all()
    
    def get_sar_by_filing_number(self, filing_number: str) -> Optional[AuditLog]:
        """
        Retrieve SAR audit entry by filing number
        
        Args:
            filing_number: Official SAR filing number
            
        Returns:
            Audit log entry for the SAR submission
        """
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.sar_filing_number == filing_number,
                AuditLog.event_type == AuditEventType.SAR_REPORT_SUBMITTED,
            )
            .first()
        )
    
    def _sanitize_sar_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize SAR request data while preserving audit trail
        
        Removes PII that's not needed for audit but keeps structure.
        """
        if not request_data:
            return {}
        
        sanitized = request_data.copy()
        
        # Remove highly sensitive PII
        pii_fields = ["ssn", "account_number", "credit_card"]
        for field in pii_fields:
            if field in sanitized:
                sanitized[field] = "[REDACTED]"
        
        return sanitized
