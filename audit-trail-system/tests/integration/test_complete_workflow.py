"""
Integration tests for complete SAR generation workflow

These tests validate the entire audit trail from case creation
through SAR generation and submission.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from backend.services.audit.case_audit import CaseAuditService
from backend.services.audit.sar_audit import SARAuditService
from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity


@pytest.fixture
def mock_db():
    """Create mock database session for integration tests"""
    db = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.query = Mock()
    
    # Track all added audit logs
    db.audit_logs = []
    
    def add_to_logs(log):
        db.audit_logs.append(log)
    
    db.add.side_effect = add_to_logs
    
    return db


class TestCompleteSARWorkflow:
    """
    Integration test for complete SAR generation workflow
    
    This simulates a real-world scenario where:
    1. User creates a case
    2. Adds suspicious alerts to the case
    3. Reviews alerts
    4. Initiates SAR generation
    5. AI generates reasoning
    6. AI generates SAR report
    7. Compliance officer reviews report
    8. Report is submitted to FinCEN
    """
    
    @patch('backend.services.audit.case_audit.environment_tracker')
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_complete_sar_generation_workflow(
        self,
        mock_sar_env,
        mock_case_env,
        mock_db
    ):
        """Test complete workflow from case creation to SAR submission"""
        
        # Setup mocks
        mock_case_env.capture_environment.return_value = {}
        mock_case_env.extract_key_environment_fields.return_value = {
            "browser_info": "Chrome 120",
            "os_info": "Windows 10",
            "device_type": "desktop",
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York",
            "application_version": "1.0.0",
        }
        mock_sar_env.capture_environment.return_value = {}
        mock_sar_env.extract_key_environment_fields.return_value = {
            "browser_info": "Chrome 120",
            "os_info": "Windows 10",
            "device_type": "desktop",
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York",
            "application_version": "1.0.0",
        }
        
        # Initialize services
        case_service = CaseAuditService(mock_db)
        sar_service = SARAuditService(mock_db)
        
        # STEP 1: Create case
        case_id = "CASE-2024-001"
        case_number = "2024-001"
        user_id = "analyst_john"
        user_email = "john@bank.com"
        
        case_audit = case_service.log_case_created(
            case_id=case_id,
            case_number=case_number,
            user_id=user_id,
            user_email=user_email,
            initial_data={
                "customer_id": "CUST-12345",
                "customer_name": "Jane Smith",
                "status": "new",
                "priority": "high",
            },
            session_id="session-abc123",
        )
        
        # Verify case creation was logged
        assert len(mock_db.audit_logs) == 1
        assert mock_db.audit_logs[0].event_type == AuditEventType.CASE_CREATED
        assert mock_db.audit_logs[0].case_id == case_id
        
        # STEP 2: Add suspicious alerts
        alert_ids = ["ALERT-001", "ALERT-002", "ALERT-003"]
        
        alert_audit = case_service.log_alert_added(
            case_id=case_id,
            alert_ids=alert_ids,
            user_id=user_id,
            user_email=user_email,
            alert_details={
                "source": "transaction_monitoring",
                "total_amount": 250000,
                "pattern": "structuring",
            },
            session_id="session-abc123",
        )
        
        assert len(mock_db.audit_logs) == 2
        assert mock_db.audit_logs[1].event_type == AuditEventType.ALERT_ADDED
        assert mock_db.audit_logs[1].alert_count == 3
        
        # STEP 3: Review alerts
        for alert_id in alert_ids:
            case_service.log_alert_reviewed(
                case_id=case_id,
                alert_id=alert_id,
                user_id=user_id,
                user_email=user_email,
                review_decision="escalate",
                review_notes=f"Alert {alert_id} requires SAR filing",
                session_id="session-abc123",
            )
        
        assert len(mock_db.audit_logs) == 5  # 1 case + 1 alert add + 3 reviews
        
        # STEP 4: Initiate SAR generation
        sar_start_audit = sar_service.log_sar_generation_started(
            case_id=case_id,
            alert_ids=alert_ids,
            user_id=user_id,
            user_email=user_email,
            request_data={
                "case_id": case_id,
                "alert_ids": alert_ids,
                "generation_type": "AI-assisted",
            },
            session_id="session-abc123",
        )
        
        assert len(mock_db.audit_logs) == 6
        assert mock_db.audit_logs[5].event_type == AuditEventType.SAR_GENERATION_STARTED
        assert mock_db.audit_logs[5].severity == AuditSeverity.CRITICAL
        
        # STEP 5: AI generates reasoning
        reasoning_text = """
        Analysis of transactions reveals the following suspicious patterns:
        
        1. Structuring: Customer made multiple cash deposits of $9,500 over 
           a 10-day period, totaling $47,500. This appears designed to avoid 
           the $10,000 reporting threshold.
        
        2. Unusual Velocity: Customer's transaction frequency increased from 
           2-3 transactions per month to 15+ transactions per week.
        
        3. Geographic Risk: Transactions conducted in multiple states within 
           short time periods, inconsistent with stated business purpose.
        """
        
        reasoning_audit = sar_service.log_sar_reasoning_generated(
            case_id=case_id,
            alert_ids=alert_ids,
            user_id=user_id,
            user_email=user_email,
            reasoning_text=reasoning_text,
            reasoning_metadata={
                "model_name": "gpt-4-turbo",
                "model_version": "2024-01",
                "prompt_tokens": 2000,
                "completion_tokens": 600,
                "temperature": 0.7,
                "confidence_score": 0.94,
            },
            processing_time_ms=3500,
            generation_audit_id=str(mock_db.audit_logs[5].id) if hasattr(mock_db.audit_logs[5], 'id') else None,
            session_id="session-abc123",
        )
        
        assert len(mock_db.audit_logs) == 7
        assert mock_db.audit_logs[6].event_type == AuditEventType.SAR_REASONING_GENERATED
        assert mock_db.audit_logs[6].sar_reasoning is not None
        
        # STEP 6: Generate SAR report
        report_content = """
        FinCEN SAR Report
        BSA Identifier: [Generated]
        
        PART I - SUBJECT INFORMATION
        Name: Jane Smith
        Account Number: [REDACTED]
        
        PART II - SUSPICIOUS ACTIVITY INFORMATION
        Type of Suspicious Activity: Structuring
        Amount: $47,500
        
        PART III - INFORMATION ABOUT FINANCIAL INSTITUTION
        [Institution details]
        
        PART IV - FILING INSTITUTION CONTACT INFORMATION
        [Contact information]
        
        PART V - SUSPICIOUS ACTIVITY INFORMATION - NARRATIVE
        """ + reasoning_text
        
        report_audit = sar_service.log_sar_report_generated(
            case_id=case_id,
            alert_ids=alert_ids,
            user_id=user_id,
            user_email=user_email,
            report_content=report_content,
            report_metadata={
                "format": "FinCEN_SAR_XML",
                "form_type": "SAR-DI",
                "sections": ["subject_info", "activity_info", "institution_info", "narrative"],
                "generation_method": "AI-assisted",
                "word_count": 850,
            },
            processing_time_ms=5000,
            reasoning_audit_id=str(mock_db.audit_logs[6].id) if hasattr(mock_db.audit_logs[6], 'id') else None,
            session_id="session-abc123",
        )
        
        assert len(mock_db.audit_logs) == 8
        assert mock_db.audit_logs[7].event_type == AuditEventType.SAR_REPORT_GENERATED
        assert mock_db.audit_logs[7].sar_report_content is not None
        
        # STEP 7: Compliance officer reviews report
        review_audit = sar_service.log_sar_report_reviewed(
            case_id=case_id,
            user_id="supervisor_mary",
            user_email="mary@bank.com",
            user_role="compliance_officer",
            review_decision="approved",
            review_comments="Report is comprehensive and meets regulatory requirements. Approved for filing.",
            report_audit_id=str(mock_db.audit_logs[7].id) if hasattr(mock_db.audit_logs[7], 'id') else None,
            session_id="session-xyz789",
        )
        
        assert len(mock_db.audit_logs) == 9
        assert mock_db.audit_logs[8].event_type == AuditEventType.SAR_REPORT_REVIEWED
        assert mock_db.audit_logs[8].changes_made["review_decision"] == "approved"
        
        # STEP 8: Submit SAR to FinCEN
        filing_number = "SAR-2024-87654321"
        
        submission_audit = sar_service.log_sar_report_submitted(
            case_id=case_id,
            user_id="supervisor_mary",
            user_email="mary@bank.com",
            filing_number=filing_number,
            submission_metadata={
                "submission_date": datetime.utcnow().isoformat(),
                "submission_method": "electronic",
                "regulatory_body": "FinCEN",
                "confirmation_number": "CONF-12345678",
                "bsa_id": "BSA-2024-001",
            },
            report_audit_id=str(mock_db.audit_logs[7].id) if hasattr(mock_db.audit_logs[7], 'id') else None,
            session_id="session-xyz789",
        )
        
        # FINAL VERIFICATION
        assert len(mock_db.audit_logs) == 10
        assert mock_db.audit_logs[9].event_type == AuditEventType.SAR_REPORT_SUBMITTED
        assert mock_db.audit_logs[9].sar_filing_number == filing_number
        assert mock_db.audit_logs[9].compliance_flags["filing_complete"] is True
        
        # Verify complete audit trail
        case_events = [log for log in mock_db.audit_logs if log.case_id == case_id]
        assert len(case_events) == 10
        
        # Verify critical events have correct severity
        critical_events = [
            log for log in mock_db.audit_logs 
            if log.severity == AuditSeverity.CRITICAL
        ]
        assert len(critical_events) >= 5  # All SAR events + alert reviews
        
        # Verify workflow progression
        event_types = [log.event_type for log in mock_db.audit_logs]
        expected_order = [
            AuditEventType.CASE_CREATED,
            AuditEventType.ALERT_ADDED,
            # Alert reviews...
            AuditEventType.SAR_GENERATION_STARTED,
            AuditEventType.SAR_REASONING_GENERATED,
            AuditEventType.SAR_REPORT_GENERATED,
            AuditEventType.SAR_REPORT_REVIEWED,
            AuditEventType.SAR_REPORT_SUBMITTED,
        ]
        
        # Check that key events are present in order
        assert AuditEventType.CASE_CREATED in event_types
        assert AuditEventType.SAR_GENERATION_STARTED in event_types
        assert AuditEventType.SAR_REASONING_GENERATED in event_types
        assert AuditEventType.SAR_REPORT_GENERATED in event_types
        assert AuditEventType.SAR_REPORT_SUBMITTED in event_types
        
        print("\n=== COMPLETE WORKFLOW TEST PASSED ===")
        print(f"Total audit entries created: {len(mock_db.audit_logs)}")
        print(f"Case ID: {case_id}")
        print(f"SAR Filing Number: {filing_number}")
        print("=====================================\n")
    
    @patch('backend.services.audit.sar_audit.environment_tracker')
    def test_sar_generation_failure_workflow(self, mock_env, mock_db):
        """Test workflow when SAR generation fails"""
        mock_env.capture_environment.return_value = {}
        mock_env.extract_key_environment_fields.return_value = {
            "browser_info": None, "os_info": None, "device_type": None,
            "screen_resolution": None, "timezone": None, "application_version": None,
        }
        
        sar_service = SARAuditService(mock_db)
        
        # Start SAR generation
        sar_service.log_sar_generation_started(
            case_id="CASE-002",
            alert_ids=["ALERT-010"],
            user_id="analyst_bob",
            user_email="bob@bank.com",
            request_data={"test": "data"},
        )
        
        # Log failure
        sar_service.log_sar_generation_failed(
            case_id="CASE-002",
            alert_ids=["ALERT-010"],
            user_id="analyst_bob",
            user_email="bob@bank.com",
            error_message="AI model timeout",
            error_details={"error_type": "TimeoutError", "retries": 3},
            stack_trace="Traceback...",
            generation_audit_id=str(mock_db.audit_logs[0].id) if hasattr(mock_db.audit_logs[0], 'id') else None,
        )
        
        assert len(mock_db.audit_logs) == 2
        assert mock_db.audit_logs[1].error_occurred is True
        assert mock_db.audit_logs[1].compliance_flags["requires_investigation"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
