# Getting Started with SAR Audit Trail System

## Quick Setup Guide

### 1. Install Dependencies

```bash
cd audit-trail-system
pip install -r requirements.txt
```

### 2. Configure Database

Edit `.env` file:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/sar_audit
SECRET_KEY=your-secret-key-change-in-production
ENVIRONMENT=production
```

### 3. Initialize Database

```bash
# Create tables
python scripts/setup_audit_db.py

# With sample data (optional)
python scripts/setup_audit_db.py --seed
```

### 4. Verify Installation

```bash
python scripts/setup_audit_db.py --verify-only
```

## Basic Usage

### In Your Application Code

```python
from fastapi import FastAPI, Request, Depends
from backend.services.audit.case_audit import CaseAuditService
from backend.services.audit.sar_audit import SARAuditService
from backend.db.session import get_db
from sqlalchemy.orm import Session

app = FastAPI()

@app.post("/case/create")
async def create_case(request: Request, db: Session = Depends(get_db)):
    # Create your case
    case_id = "CASE-2024-001"
    
    # Log it in audit trail
    case_service = CaseAuditService(db)
    case_service.log_case_created(
        case_id=case_id,
        case_number="2024-001",
        user_id="analyst123",
        user_email="analyst@bank.com",
        initial_data={"status": "new"},
        request=request,
        session_id=request.headers.get("session-id"),
    )
    
    return {"case_id": case_id}

@app.post("/sar/generate")
async def generate_sar(request: Request, db: Session = Depends(get_db)):
    case_id = "CASE-2024-001"
    alert_ids = ["ALERT-001", "ALERT-002"]
    
    sar_service = SARAuditService(db)
    
    # Log SAR generation start
    sar_service.log_sar_generation_started(
        case_id=case_id,
        alert_ids=alert_ids,
        user_id="analyst123",
        user_email="analyst@bank.com",
        request_data={"case_id": case_id},
        request_obj=request,
    )
    
    # Your AI generation code here...
    reasoning = generate_ai_reasoning(case_id, alert_ids)
    
    # Log reasoning generation
    sar_service.log_sar_reasoning_generated(
        case_id=case_id,
        alert_ids=alert_ids,
        user_id="analyst123",
        user_email="analyst@bank.com",
        reasoning_text=reasoning,
        reasoning_metadata={
            "model_name": "gpt-4",
            "confidence_score": 0.94,
        },
        processing_time_ms=2500,
    )
    
    # Generate report and log it...
    report = generate_sar_report(reasoning)
    
    sar_service.log_sar_report_generated(
        case_id=case_id,
        alert_ids=alert_ids,
        user_id="analyst123",
        user_email="analyst@bank.com",
        report_content=report,
        report_metadata={"format": "FinCEN_SAR_XML"},
        processing_time_ms=5000,
    )
    
    return {"status": "generated"}
```

### Query Audit Trail

```bash
# View case history
python scripts/query_audit_trail.py case CASE-2024-001

# View user activity
python scripts/query_audit_trail.py user analyst123 --days 7

# View SAR trail
python scripts/query_audit_trail.py sar CASE-2024-001

# Get statistics
python scripts/query_audit_trail.py stats --days 30
```

## Key Concepts

### Event Types

**Case Events**: CASE_CREATED, CASE_UPDATED, CASE_VIEWED  
**Alert Events**: ALERT_ADDED, ALERT_REVIEWED  
**SAR Events** (CRITICAL): 
- SAR_GENERATION_STARTED
- SAR_REASONING_GENERATED
- SAR_REPORT_GENERATED
- SAR_REPORT_REVIEWED
- SAR_REPORT_SUBMITTED
- SAR_GENERATION_FAILED

### Severity Levels

- **LOW**: Routine viewing/queries
- **MEDIUM**: Standard operations
- **HIGH**: Important operations (alerts)
- **CRITICAL**: SAR operations, errors

### What Gets Audited?

✅ Every case creation and update  
✅ All alert additions and reviews  
✅ Complete SAR generation process  
✅ AI reasoning with model metadata  
✅ Report generation and modifications  
✅ Review and approval workflow  
✅ Submission to FinCEN  
✅ All errors and failures  
✅ User environment (browser, OS, etc.)  

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_sar_audit.py -v

# Run with coverage
pytest --cov=backend tests/
```

## Common Tasks

### Add New Event Type

1. Add to `AuditEventType` enum in `audit_log.py`
2. Create logging method in appropriate service
3. Add test cases
4. Update documentation

### Query Specific Events

```python
from backend.models.audit_log import AuditLog, AuditEventType
from backend.db.session import get_db

db = next(get_db())

# Get all SAR submissions
sars = db.query(AuditLog).filter(
    AuditLog.event_type == AuditEventType.SAR_REPORT_SUBMITTED
).all()

# Get critical events
critical = db.query(AuditLog).filter(
    AuditLog.severity == AuditSeverity.CRITICAL
).all()
```

### Export Audit Data

```python
import json

logs = db.query(AuditLog).filter(
    AuditLog.case_id == "CASE-2024-001"
).all()

with open("case_audit.json", "w") as f:
    json.dump([log.to_dict() for log in logs], f, indent=2)
```

## Troubleshooting

### Database Connection Issues
- Check `DATABASE_URL` in `.env`
- Verify PostgreSQL is running
- Check network connectivity

### Missing Audit Entries
- Verify service is being called
- Check database commits
- Review error logs

### Performance Issues
- Check database indexes
- Verify query pagination
- Monitor connection pool

## Next Steps

1. ✅ Review `docs/AUDIT_SPECIFICATION.md` for complete details
2. ✅ Customize `config/audit_config.yaml` for your environment
3. ✅ Integrate with your existing systems
4. ✅ Setup monitoring and alerting
5. ✅ Configure backup procedures

## Support

For questions or issues:
- Check documentation in `/docs`
- Review examples in code comments
- Contact: compliance@yourorg.com
