"""
Unit tests for Case Audit Service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from backend.services.audit.case_audit import CaseAuditService
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
def case_service(mock_db):
    """Create CaseAuditService instance with mock db"""
    return CaseAuditService(mock_db)


class TestCaseAuditService:
    """Test cases for CaseAuditService"""
    
    @patch('backend.services.audit.case_audit.environment_tracker')
    def test_log_case_created(self, mock_env_tracker, case_service, mock_db):
        """Test logging case creation"""
        # Setup mocks
        mock_env_tracker.capture_environment.return_value = {"test": "data"}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": "Chrome 120",
            "os_info": "Windows",
            "device_type": "desktop",
            "screen_resolution": "1920x1080",
            "timezone": "UTC",
            "application_version": "1.0.0",
        }
        
        # Call method
        result = case_service.log_case_created(
            case_id="CASE-001",
            case_number="2024-001",
            user_id="user123",
            user_email="user@example.com",
            initial_data={"status": "new", "priority": "high"},
            session_id="session-abc",
        )
        
        # Verify audit log was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Get the audit log that was added
        added_log = mock_db.add.call_args[0][0]
        assert isinstance(added_log, AuditLog)
        assert added_log.event_type == AuditEventType.CASE_CREATED
        assert added_log.case_id == "CASE-001"
        assert added_log.case_number == "2024-001"
        assert added_log.user_id == "user123"
        assert added_log.severity == AuditSeverity.MEDIUM
    
    @patch('backend.services.audit.case_audit.environment_tracker')
    def test_log_case_updated(self, mock_env_tracker, case_service, mock_db):
        """Test logging case updates"""
        mock_env_tracker.capture_environment.return_value = {"test": "data"}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None,
            "os_info": None,
            "device_type": None,
            "screen_resolution": None,
            "timezone": None,
            "application_version": None,
        }
        
        changes = {
            "status": {"before": "new", "after": "in_progress"},
            "priority": {"before": "medium", "after": "high"},
        }
        
        result = case_service.log_case_updated(
            case_id="CASE-001",
            user_id="user123",
            user_email="user@example.com",
            changes=changes,
            reason="Escalating due to new evidence",
            session_id="session-abc",
        )
        
        mock_db.add.assert_called_once()
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == AuditEventType.CASE_UPDATED
        assert added_log.changes_made == changes
        assert added_log.reason_for_change == "Escalating due to new evidence"
    
    @patch('backend.services.audit.case_audit.environment_tracker')
    def test_log_case_updated_high_severity_on_status_change(
        self, mock_env_tracker, case_service, mock_db
    ):
        """Test that status changes trigger high severity"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        changes = {"status": {"before": "new", "after": "closed"}}
        
        case_service.log_case_updated(
            case_id="CASE-001",
            user_id="user123",
            user_email="user@example.com",
            changes=changes,
        )
        
        added_log = mock_db.add.call_args[0][0]
        assert added_log.severity == AuditSeverity.HIGH
    
    @patch('backend.services.audit.case_audit.environment_tracker')
    def test_log_alert_added(self, mock_env_tracker, case_service, mock_db):
        """Test logging alert addition"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        alert_ids = ["ALERT-001", "ALERT-002", "ALERT-003"]
        
        result = case_service.log_alert_added(
            case_id="CASE-001",
            alert_ids=alert_ids,
            user_id="user123",
            user_email="user@example.com",
            alert_details={"source": "transaction_monitoring"},
        )
        
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == AuditEventType.ALERT_ADDED
        assert added_log.alert_ids == alert_ids
        assert added_log.alert_count == 3
        assert added_log.severity == AuditSeverity.HIGH
    
    @patch('backend.services.audit.case_audit.environment_tracker')
    def test_log_case_viewed(self, mock_env_tracker, case_service, mock_db):
        """Test logging case viewing"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        result = case_service.log_case_viewed(
            case_id="CASE-001",
            user_id="user123",
            user_email="user@example.com",
        )
        
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == AuditEventType.CASE_VIEWED
        assert added_log.severity == AuditSeverity.LOW
    
    @patch('backend.services.audit.case_audit.environment_tracker')
    def test_log_alert_reviewed(self, mock_env_tracker, case_service, mock_db):
        """Test logging alert review"""
        mock_env_tracker.capture_environment.return_value = {}
        mock_env_tracker.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        result = case_service.log_alert_reviewed(
            case_id="CASE-001",
            alert_id="ALERT-001",
            user_id="user123",
            user_email="user@example.com",
            review_decision="escalate",
            review_notes="Suspicious pattern detected",
        )
        
        added_log = mock_db.add.call_args[0][0]
        assert added_log.event_type == AuditEventType.ALERT_REVIEWED
        assert added_log.alert_ids == ["ALERT-001"]
        assert added_log.severity == AuditSeverity.HIGH
        assert added_log.changes_made["review_decision"] == "escalate"
    
    def test_get_case_audit_history(self, case_service, mock_db):
        """Test retrieving case audit history"""
        # Setup mock query
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_limit = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = [Mock(spec=AuditLog)]
        
        result = case_service.get_case_audit_history("CASE-001", limit=50)
        
        mock_db.query.assert_called_once_with(AuditLog)
        assert isinstance(result, list)
    
    def test_sanitize_payload(self, case_service):
        """Test payload sanitization"""
        payload = {
            "case_name": "Test Case",
            "password": "secret123",
            "ssn": "123-45-6789",
            "token": "bearer-token",
        }
        
        sanitized = case_service._sanitize_payload(payload)
        
        assert sanitized["case_name"] == "Test Case"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["ssn"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
