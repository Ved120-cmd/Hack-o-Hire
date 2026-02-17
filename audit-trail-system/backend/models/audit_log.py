"""
Audit Log Database Model

This model captures comprehensive audit information for SAR report generation,
including environment, case details, reasoning, and generated reports.
"""
from sqlalchemy import (
    Column, String, Text, JSON, DateTime, Integer, 
    Boolean, Float, Index, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum

from backend.db.base import Base


class AuditEventType(str, enum.Enum):
    """Types of audit events"""
    # Environment Events
    ENVIRONMENT_CAPTURED = "environment_captured"
    ENVIRONMENT_CHANGED = "environment_changed"
    
    # Case Events
    CASE_CREATED = "case_created"
    CASE_UPDATED = "case_updated"
    CASE_VIEWED = "case_viewed"
    CASE_DELETED = "case_deleted"
    
    # Alert Events
    ALERT_ADDED = "alert_added"
    ALERT_REVIEWED = "alert_reviewed"
    ALERT_FLAGGED = "alert_flagged"
    
    # SAR Events (CRITICAL)
    SAR_GENERATION_STARTED = "sar_generation_started"
    SAR_REASONING_GENERATED = "sar_reasoning_generated"
    SAR_REPORT_GENERATED = "sar_report_generated"
    SAR_REPORT_REVIEWED = "sar_report_reviewed"
    SAR_REPORT_SUBMITTED = "sar_report_submitted"
    SAR_GENERATION_FAILED = "sar_generation_failed"
    
    # System Events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SYSTEM_ERROR = "system_error"


class AuditSeverity(str, enum.Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog(Base):
    """
    Comprehensive Audit Log for SAR Report Generation
    
    This table captures ALL actions related to SAR report generation with
    complete traceability including environment, reasoning, and outputs.
    """
    __tablename__ = "audit_logs"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Event Information
    event_type = Column(
        SQLEnum(AuditEventType),
        nullable=False,
        index=True,
        comment="Type of audit event"
    )
    event_timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When the event occurred"
    )
    severity = Column(
        SQLEnum(AuditSeverity),
        nullable=False,
        default=AuditSeverity.MEDIUM,
        comment="Event severity level"
    )
    
    # User Information
    user_id = Column(String(100), nullable=False, index=True, comment="User who performed the action")
    user_email = Column(String(255), index=True, comment="User email address")
    user_role = Column(String(50), comment="User role/permission level")
    user_ip_address = Column(String(45), comment="IP address of the user")
    
    # Session Information
    session_id = Column(
        String(100),
        index=True,
        comment="Session identifier for grouping related events"
    )
    
    # Case Information
    case_id = Column(
        String(100),
        index=True,
        comment="Case ID being worked on"
    )
    case_number = Column(String(50), comment="Human-readable case number")
    case_status = Column(String(50), comment="Current status of the case")
    
    # Alert Information
    alert_ids = Column(
        JSONB,
        comment="List of suspicious alert IDs associated with this event"
    )
    alert_count = Column(Integer, comment="Number of alerts in this case")
    
    # Environment Information (CRITICAL for compliance)
    environment_data = Column(
        JSONB,
        comment="Complete environment context at time of event"
    )
    # Breakdown of common environment fields for easier querying:
    browser_info = Column(String(255), comment="Browser type and version")
    os_info = Column(String(100), comment="Operating system information")
    device_type = Column(String(50), comment="Device type (desktop, mobile, tablet)")
    screen_resolution = Column(String(20), comment="Screen resolution")
    timezone = Column(String(50), comment="User timezone")
    application_version = Column(String(20), comment="Application version")
    
    # SAR Generation Information (MOST CRITICAL)
    sar_request_data = Column(
        JSONB,
        comment="Original request data for SAR generation"
    )
    sar_reasoning = Column(
        Text,
        comment="AI-generated reasoning for suspicious activity"
    )
    sar_reasoning_metadata = Column(
        JSONB,
        comment="Metadata about reasoning generation (model, tokens, etc.)"
    )
    sar_report_content = Column(
        Text,
        comment="Complete generated SAR report content"
    )
    sar_report_metadata = Column(
        JSONB,
        comment="Metadata about report generation"
    )
    sar_filing_number = Column(
        String(100),
        index=True,
        comment="Official SAR filing number if submitted"
    )
    
    # Processing Information
    processing_duration_ms = Column(
        Integer,
        comment="How long the operation took in milliseconds"
    )
    api_endpoint = Column(String(255), comment="API endpoint called")
    http_method = Column(String(10), comment="HTTP method used")
    request_payload = Column(JSONB, comment="Request payload (sanitized)")
    response_status = Column(Integer, comment="HTTP response status code")
    
    # Change Tracking
    changes_made = Column(
        JSONB,
        comment="Specific changes made (before/after values)"
    )
    reason_for_change = Column(Text, comment="User-provided reason for changes")
    
    # Error Information
    error_occurred = Column(Boolean, default=False, comment="Whether an error occurred")
    error_message = Column(Text, comment="Error message if applicable")
    error_stack_trace = Column(Text, comment="Full stack trace for debugging")
    
    # Compliance & Regulatory
    compliance_flags = Column(
        JSONB,
        comment="Compliance-related flags and metadata"
    )
    regulatory_requirements = Column(
        JSONB,
        comment="Applicable regulatory requirements (FinCEN, etc.)"
    )
    retention_category = Column(
        String(50),
        default="standard",
        comment="Data retention category"
    )
    
    # Additional Metadata
    tags = Column(JSONB, comment="Searchable tags for categorization")
    notes = Column(Text, comment="Additional notes or context")
    related_audit_ids = Column(
        JSONB,
        comment="IDs of related audit log entries"
    )
    
    # System Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    is_archived = Column(Boolean, default=False, comment="Whether record is archived")
    archived_at = Column(DateTime, comment="When record was archived")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_event_timestamp_desc', event_timestamp.desc()),
        Index('idx_case_event', case_id, event_type),
        Index('idx_user_timestamp', user_id, event_timestamp.desc()),
        Index('idx_sar_filing', sar_filing_number),
        Index('idx_session_timestamp', session_id, event_timestamp),
        Index('idx_severity_timestamp', severity, event_timestamp.desc()),
        Index('idx_event_case_user', event_type, case_id, user_id),
    )
    
    def to_dict(self) -> dict:
        """Convert audit log to dictionary"""
        return {
            "id": str(self.id),
            "event_type": self.event_type.value if self.event_type else None,
            "event_timestamp": self.event_timestamp.isoformat() if self.event_timestamp else None,
            "severity": self.severity.value if self.severity else None,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "session_id": self.session_id,
            "case_id": self.case_id,
            "case_number": self.case_number,
            "alert_ids": self.alert_ids,
            "alert_count": self.alert_count,
            "environment_data": self.environment_data,
            "sar_reasoning": self.sar_reasoning,
            "sar_report_content": self.sar_report_content,
            "sar_filing_number": self.sar_filing_number,
            "processing_duration_ms": self.processing_duration_ms,
            "error_occurred": self.error_occurred,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, event_type={self.event_type}, "
            f"user={self.user_id}, case={self.case_id}, "
            f"timestamp={self.event_timestamp})>"
        )
