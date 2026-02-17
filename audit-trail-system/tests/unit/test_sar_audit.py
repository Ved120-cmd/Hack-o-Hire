"""
Unit tests for SAR Audit Service - CRITICAL TESTS

These tests ensure the SAR audit trail system works correctly,
which is essential for regulatory compliance.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.audit.sar_audit import SARAuditService
from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.query = Mock()
    return db


@pytest.fixture
def sar_service(mock_db):
    """Create SARAuditService instance with mock db"""
    return SARAuditService(mock_db)


class TestSARAuditService:
    """Test cases for SAR Audit Service"""
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_log_sar_generation_started(self, mock_env_tracker, sar_service, mock_db):
        """Test logging SAR generation start - CRITICAL"""
        mock_env_tracker.capture_environment.return_value = {"env": "data"}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": "Chrome 120",
            "os_info": "Windows 10",
            "device_type": "desktop",
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York",
            "application_version": "1.0.0",
        }
        
        alert_ids = ["ALERT-001", "ALERT-002"]
        request_data = {
            "case_id": "CASE-001",
            "alerts": alert_ids,
            "customer_info": {"name": "John Doe"},
        }
        
        result = sar_service.log_sar_generation_started(
            case_id="CASE-001",
            alert_ids=alert_ids,
            user_id="analyst123",
            user_email="analyst@bank.com",
            request_data=request_data,
            session_id="session-xyz",
        )
        
        # Verify critical fields
        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        
        assert added_log.event_type == AuditEventType.SAR_GENERATION_STARTED
        assert added_log.severity == AuditSeverity.CRITICAL
        assert added_log.case_id == "CASE-001"
        assert added_log.alert_ids == alert_ids
        assert added_log.alert_count == 2
        assert added_log.sar_request_data is not None
        assert "sar" in added_log.tags
        assert "critical" in added_log.tags
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_log_sar_reasoning_generated(self, mock_env_tracker, sar_service, mock_db):
        """Test logging AI-generated reasoning - CRITICAL"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        reasoning_text = """
        Based on analysis of transaction patterns, the following suspicious 
        activities were identified:
        1. Structuring: Multiple transactions just below $10,000 threshold
        2. Velocity: Unusual increase in transaction frequency
        3. Geography: Transactions from high-risk jurisdictions
        """
        
        reasoning_metadata = {
            "model_name": "gpt-4",
            "model_version": "2024-01",
            "prompt_tokens": 1500,
            "completion_tokens": 500,
            "temperature": 0.7,
            "confidence_score": 0.92,
        }
        
        result = sar_service.log_sar_reasoning_generated(
            case_id="CASE-001",
            alert_ids=["ALERT-001", "ALERT-002"],
            user_id="analyst123",
            user_email="analyst@bank.com",
            reasoning_text=reasoning_text,
            reasoning_metadata=reasoning_metadata,
            processing_time_ms=2500,
            generation_audit_id="audit-001",
        )
        
        added_log = mock_db.add.call_args[0][0]
        
        assert added_log.event_type == AuditEventType.SAR_REASONING_GENERATED
        assert added_log.severity == AuditSeverity.CRITICAL
        assert added_log.sar_reasoning == reasoning_text
        assert added_log.sar_reasoning_metadata == reasoning_metadata
        assert added_log.processing_duration_ms == 2500
        assert added_log.compliance_flags["ai_generated"] is True
        assert "audit-001" in added_log.related_audit_ids
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_log_sar_report_generated(self, mock_env_tracker, sar_service, mock_db):
        """Test logging SAR report generation - CRITICAL"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        report_content = """
        SUSPICIOUS ACTIVITY REPORT
        
        Part I: Subject Information
        Name: [REDACTED]
        Account: [REDACTED]
        
        Part II: Suspicious Activity Information
        [Detailed report content...]
        """
        
        report_metadata = {
            "format": "FinCEN_SAR_XML",
            "form_type": "SAR-DI",
            "sections": ["subject_info", "activity_info", "narrative"],
            "generation_method": "AI-assisted",
        }
        
        result = sar_service.log_sar_report_generated(
            case_id="CASE-001",
            alert_ids=["ALERT-001", "ALERT-002"],
            user_id="analyst123",
            user_email="analyst@bank.com",
            report_content=report_content,
            report_metadata=report_metadata,
            processing_time_ms=5000,
            reasoning_audit_id="audit-002",
        )
        
        added_log = mock_db.add.call_args[0][0]
        
        assert added_log.event_type == AuditEventType.SAR_REPORT_GENERATED
        assert added_log.severity == AuditSeverity.CRITICAL
        assert added_log.sar_report_content == report_content
        assert added_log.sar_report_metadata == report_metadata
        assert added_log.compliance_flags["report_generated"] is True
        assert added_log.compliance_flags["ready_for_review"] is True
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_log_sar_report_reviewed_approved(
        self, mock_env_tracker, sar_service, mock_db
    ):
        """Test logging SAR report review - approved"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        result = sar_service.log_sar_report_reviewed(
            case_id="CASE-001",
            user_id="supervisor456",
            user_email="supervisor@bank.com",
            user_role="compliance_officer",
            review_decision="approved",
            review_comments="Report is complete and accurate. Ready for filing.",
            report_audit_id="audit-003",
        )
        
        added_log = mock_db.add.call_args[0][0]
        
        assert added_log.event_type == AuditEventType.SAR_REPORT_REVIEWED
        assert added_log.user_role == "compliance_officer"
        assert added_log.changes_made["review_decision"] == "approved"
        assert added_log.compliance_flags["approved"] is True
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_log_sar_report_reviewed_rejected(
        self, mock_env_tracker, sar_service, mock_db
    ):
        """Test logging SAR report review - rejected"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        changes_requested = [
            "Need more detail on transaction patterns",
            "Include geographic analysis",
            "Clarify timeline of events",
        ]
        
        result = sar_service.log_sar_report_reviewed(
            case_id="CASE-001",
            user_id="supervisor456",
            user_email="supervisor@bank.com",
            user_role="compliance_officer",
            review_decision="rejected",
            review_comments="Insufficient detail. See requested changes.",
            changes_requested=changes_requested,
        )
        
        added_log = mock_db.add.call_args[0][0]
        
        assert added_log.severity == AuditSeverity.CRITICAL
        assert added_log.changes_made["review_decision"] == "rejected"
        assert added_log.changes_made["changes_requested"] == changes_requested
        assert added_log.compliance_flags["approved"] is False
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_log_sar_report_submitted(self, mock_env_tracker, sar_service, mock_db):
        """Test logging SAR submission to FinCEN - CRITICAL"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        filing_number = "SAR-2024-12345678"
        submission_metadata = {
            "submission_date": "2024-02-13T10:30:00Z",
            "submission_method": "electronic",
            "regulatory_body": "FinCEN",
            "confirmation_number": "CONF-98765432",
            "bsa_id": "BSA-2024-001",
        }
        
        result = sar_service.log_sar_report_submitted(
            case_id="CASE-001",
            user_id="supervisor456",
            user_email="supervisor@bank.com",
            filing_number=filing_number,
            submission_metadata=submission_metadata,
            report_audit_id="audit-003",
        )
        
        added_log = mock_db.add.call_args[0][0]
        
        assert added_log.event_type == AuditEventType.SAR_REPORT_SUBMITTED
        assert added_log.severity == AuditSeverity.CRITICAL
        assert added_log.sar_filing_number == filing_number
        assert added_log.compliance_flags["submitted"] is True
        assert added_log.compliance_flags["filing_complete"] is True
        assert added_log.retention_category == "regulatory_filing"
        assert added_log.regulatory_requirements["BSA_filed"] is True
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_log_sar_generation_failed(self, mock_env_tracker, sar_service, mock_db):
        """Test logging SAR generation failure - CRITICAL"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        error_message = "AI model timeout during reasoning generation"
        error_details = {
            "error_type": "TimeoutError",
            "attempted_retries": 3,
            "model": "gpt-4",
        }
        stack_trace = "Traceback (most recent call last):\n  File..."
        
        result = sar_service.log_sar_generation_failed(
            case_id="CASE-001",
            alert_ids=["ALERT-001", "ALERT-002"],
            user_id="analyst123",
            user_email="analyst@bank.com",
            error_message=error_message,
            error_details=error_details,
            stack_trace=stack_trace,
            generation_audit_id="audit-001",
        )
        
        added_log = mock_db.add.call_args[0][0]
        
        assert added_log.event_type == AuditEventType.SAR_GENERATION_FAILED
        assert added_log.severity == AuditSeverity.CRITICAL
        assert added_log.error_occurred is True
        assert added_log.error_message == error_message
        assert added_log.error_stack_trace == stack_trace
        assert added_log.compliance_flags["generation_failed"] is True
        assert added_log.compliance_flags["requires_investigation"] is True
    
    def test_get_sar_audit_trail(self, sar_service, mock_db):
        """Test retrieving complete SAR audit trail"""
        # Setup mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = [
            Mock(spec=AuditLog, event_type=AuditEventType.SAR_GENERATION_STARTED),
            Mock(spec=AuditLog, event_type=AuditEventType.SAR_REASONING_GENERATED),
            Mock(spec=AuditLog, event_type=AuditEventType.SAR_REPORT_GENERATED),
        ]
        
        result = sar_service.get_sar_audit_trail("CASE-001")
        
        assert len(result) == 3
        mock_db.query.assert_called_once_with(AuditLog)
    
    def test_get_sar_by_filing_number(self, sar_service, mock_db):
        """Test retrieving SAR by filing number"""
        filing_number = "SAR-2024-12345678"
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_sar = Mock(spec=AuditLog)
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_sar
        
        result = sar_service.get_sar_by_filing_number(filing_number)
        
        assert result == mock_sar
    
    def test_sanitize_sar_request(self, sar_service):
        """Test sanitization of SAR request data"""
        request_data = {
            "case_id": "CASE-001",
            "customer_name": "John Doe",
            "ssn": "123-45-6789",
            "account_number": "9876543210",
            "credit_card": "4111111111111111",
        }
        
        sanitized = sar_service._sanitize_sar_request(request_data)
        
        assert sanitized["case_id"] == "CASE-001"
        assert sanitized["customer_name"] == "John Doe"
        assert sanitized["ssn"] == "[REDACTED]"
        assert sanitized["account_number"] == "[REDACTED]"
        assert sanitized["credit_card"] == "[REDACTED]"


class TestSARComplianceRequirements:
    """Tests to ensure compliance requirements are met"""
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_all_sar_events_have_critical_severity(
        self, mock_env_tracker, sar_service, mock_db
    ):
        """Ensure all SAR events are marked as CRITICAL severity"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        # Test each SAR event type
        sar_service.log_sar_generation_started(
            "CASE-1", ["A-1"], "u1", "u@e.com", {}
        )
        assert mock_db.add.call_args[0][0].severity == AuditSeverity.CRITICAL
        
        mock_db.reset_mock()
        
        sar_service.log_sar_reasoning_generated(
            "CASE-1", ["A-1"], "u1", "u@e.com", "reasoning", {}, 100
        )
        assert mock_db.add.call_args[0][0].severity == AuditSeverity.CRITICAL
        
        mock_db.reset_mock()
        
        sar_service.log_sar_report_generated(
            "CASE-1", ["A-1"], "u1", "u@e.com", "report", {}, 100
        )
        assert mock_db.add.call_args[0][0].severity == AuditSeverity.CRITICAL
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_sar_submission_includes_regulatory_data(
        self, mock_env_tracker, sar_service, mock_db
    ):
        """Ensure SAR submission captures all regulatory requirements"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        filing_number = "SAR-2024-12345678"
        submission_metadata = {
            "submission_date": "2024-02-13T10:30:00Z",
            "regulatory_body": "FinCEN",
        }
        
        sar_service.log_sar_report_submitted(
            case_id="CASE-001",
            user_id="u1",
            user_email="u@e.com",
            filing_number=filing_number,
            submission_metadata=submission_metadata,
        )
        
        added_log = mock_db.add.call_args[0][0]
        
        # Verify regulatory compliance fields
        assert added_log.sar_filing_number == filing_number
        assert added_log.retention_category == "regulatory_filing"
        assert added_log.regulatory_requirements is not None
        assert "BSA_filed" in added_log.regulatory_requirements
        assert "FinCEN_filing_number" in added_log.regulatory_requirements


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
