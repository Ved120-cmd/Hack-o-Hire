# SAR Audit Trail System

A comprehensive audit trail system for Suspicious Activity Report (SAR) generation, ensuring full regulatory compliance with FinCEN, BSA, and other financial regulatory requirements.

## Overview

This system provides complete traceability for SAR report generation, from initial case creation through final submission to regulatory authorities. It captures:

- **Environment Context**: Complete system and user environment at time of each action
- **Case Management**: Full lifecycle of suspicious activity cases
- **Alert Tracking**: All suspicious alerts and their reviews
- **SAR Generation**: AI-assisted reasoning and report generation (MOST CRITICAL)
- **Review Workflow**: Compliance officer review and approval process
- **Submission Tracking**: Official filing numbers and regulatory acknowledgment

## Key Features

✅ **Comprehensive Audit Trail**: Every action is logged with full context  
✅ **Regulatory Compliance**: Meets FinCEN and BSA requirements  
✅ **Environment Tracking**: Captures browser, OS, device, and network context  
✅ **AI Transparency**: Records AI model usage, reasoning, and confidence scores  
✅ **Immutable Records**: Audit logs cannot be modified or deleted  
✅ **Long-term Retention**: 7-year retention for compliance  
✅ **Fast Queries**: Optimized indexes for rapid retrieval  
✅ **Privacy Protection**: Automatic PII sanitization  

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/audit-trail-system.git
cd audit-trail-system

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

### Database Setup

```bash
# Setup database
python scripts/setup_audit_db.py

# With sample data
python scripts/setup_audit_db.py --seed

# Drop and recreate (WARNING: destructive)
python scripts/setup_audit_db.py --drop
```

### Configuration

Create `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/sar_audit
SECRET_KEY=your-secret-key
ENVIRONMENT=production
DEBUG=False
```

## Usage Examples

### Logging Case Creation

```python
from backend.services.audit.case_audit import CaseAuditService
from backend.db.session import get_db

db = next(get_db())
case_service = CaseAuditService(db)

case_service.log_case_created(
    case_id="CASE-2024-001",
    case_number="2024-001",
    user_id="analyst123",
    user_email="analyst@bank.com",
    initial_data={"status": "new", "priority": "high"},
    request=request,  # FastAPI request object
    session_id="session-abc",
)
```

### Logging SAR Generation (CRITICAL)

```python
from backend.services.audit.sar_audit import SARAuditService

sar_service = SARAuditService(db)

# Start SAR generation
start_audit = sar_service.log_sar_generation_started(
    case_id="CASE-2024-001",
    alert_ids=["ALERT-001", "ALERT-002"],
    user_id="analyst123",
    user_email="analyst@bank.com",
    request_data={"case_id": "CASE-2024-001", "alerts": ["ALERT-001"]},
    request_obj=request,
    session_id="session-abc",
)

# Log AI-generated reasoning
reasoning_audit = sar_service.log_sar_reasoning_generated(
    case_id="CASE-2024-001",
    alert_ids=["ALERT-001", "ALERT-002"],
    user_id="analyst123",
    user_email="analyst@bank.com",
    reasoning_text="Based on analysis...",
    reasoning_metadata={
        "model_name": "gpt-4",
        "confidence_score": 0.94,
    },
    processing_time_ms=2500,
)

# Log SAR report generation
report_audit = sar_service.log_sar_report_generated(
    case_id="CASE-2024-001",
    alert_ids=["ALERT-001", "ALERT-002"],
    user_id="analyst123",
    user_email="analyst@bank.com",
    report_content="[Complete SAR report content]",
    report_metadata={"format": "FinCEN_SAR_XML"},
    processing_time_ms=5000,
)

# Log SAR submission
submission_audit = sar_service.log_sar_report_submitted(
    case_id="CASE-2024-001",
    user_id="supervisor456",
    user_email="supervisor@bank.com",
    filing_number="SAR-2024-12345678",
    submission_metadata={
        "submission_date": "2024-02-13T10:30:00Z",
        "regulatory_body": "FinCEN",
        "confirmation_number": "CONF-98765432",
    },
)
```

### Querying Audit Trail

```python
# Get case history
history = case_service.get_case_audit_history("CASE-2024-001")

# Get SAR audit trail
sar_trail = sar_service.get_sar_audit_trail("CASE-2024-001")

# Get SAR by filing number
sar_entry = sar_service.get_sar_by_filing_number("SAR-2024-12345678")
```

### Using Command-Line Tools

```bash
# Query by case ID
python scripts/query_audit_trail.py case CASE-2024-001

# Query by user
python scripts/query_audit_trail.py user analyst123 --days 30

# Get SAR trail
python scripts/query_audit_trail.py sar CASE-2024-001

# Query by filing number
python scripts/query_audit_trail.py filing SAR-2024-12345678

# Get statistics
python scripts/query_audit_trail.py stats --days 30
```

## API Endpoints

### Query Audit Logs
```
GET /api/v1/audit/logs
Query Parameters:
  - case_id: Filter by case
  - user_id: Filter by user
  - event_type: Filter by event type
  - severity: Filter by severity
  - start_date: Filter by date range
  - end_date: Filter by date range
  - page: Page number
  - page_size: Results per page
```

### Get Case History
```
GET /api/v1/audit/case/{case_id}/history
```

### Get SAR Audit Trail
```
GET /api/v1/audit/case/{case_id}/sar-trail
```

### Get SAR by Filing Number
```
GET /api/v1/audit/sar/filing/{filing_number}
```

### Get Statistics
```
GET /api/v1/audit/stats
```

## Testing

```bash
# Run all tests
pytest

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=backend --cov-report=html
```

## Directory Structure

```
audit-trail-system/
├── backend/
│   ├── models/
│   │   └── audit_log.py              # Audit log database model
│   ├── services/
│   │   └── audit/
│   │       ├── environment_tracker.py # Environment context capture
│   │       ├── case_audit.py          # Case audit service
│   │       └── sar_audit.py           # SAR audit service (CRITICAL)
│   ├── api/
│   │   └── endpoints/
│   │       └── audit.py               # API endpoints
│   ├── core/
│   │   └── config.py                  # Configuration
│   └── db/
│       ├── base.py                    # Database base
│       └── session.py                 # Session management
├── tests/
│   ├── unit/                          # Unit tests
│   └── integration/                   # Integration tests
├── config/
│   └── audit_config.yaml              # Configuration file
├── docs/
│   ├── AUDIT_SPECIFICATION.md         # Complete specification
│   ├── API_DOCUMENTATION.md           # API documentation
│   └── EXAMPLES.md                    # Usage examples
├── scripts/
│   ├── setup_audit_db.py              # Database setup
│   └── query_audit_trail.py           # Query helper
├── requirements.txt                    # Python dependencies
└── setup.py                           # Package setup
```

## Regulatory Compliance

### Bank Secrecy Act (BSA)
✅ All SAR activities fully audited  
✅ 7-year minimum retention period  
✅ Complete traceability  
✅ Immutable audit records  

### FinCEN Requirements
✅ Document suspicious activity reasoning  
✅ Track all report modifications  
✅ Maintain review/approval workflow  
✅ Store submission records with filing numbers  

## Security

- **Authentication**: Required for all operations
- **Authorization**: Role-based access control
- **Encryption**: AES-256-GCM for sensitive fields
- **PII Protection**: Automatic sanitization
- **Audit Trail**: All access is logged

## Performance

- **Indexes**: Optimized for common queries
- **Pagination**: Efficient large result handling
- **Caching**: Configurable query caching
- **Connection Pooling**: Efficient database connections

## Monitoring

Key metrics monitored:
- Audit log creation rate
- Query response time
- Error rate
- Storage usage
- SAR generation success rate

## Support

For issues, questions, or contributions:
- **Email**: compliance@yourorg.com
- **Documentation**: See `/docs` folder
- **Issues**: GitHub Issues

## License

Proprietary - Internal Use Only

## Authors

Compliance Engineering Team

## Changelog

### Version 1.0.0 (2024-02-13)
- Initial release
- Complete audit trail system
- SAR generation tracking
- API endpoints
- Command-line tools
- Comprehensive documentation
