# SAR Audit Trail System - File Documentation

## 📁 Complete File Guide

This document explains what each file does and how they work together.

---

## 🎯 Core Backend Files

### `backend/models/audit_log.py` ⭐ MOST IMPORTANT
**What it does:**
- Defines the database model for audit logs
- Creates the `audit_logs` table structure
- Stores EVERYTHING: cases, alerts, SAR reasoning, reports, submissions

**Key Components:**
- `AuditLog` class: Main database model with 40+ fields
- `AuditEventType` enum: All possible event types (CASE_CREATED, SAR_GENERATED, etc.)
- `AuditSeverity` enum: LOW, MEDIUM, HIGH, CRITICAL
- Database indexes for fast queries
- JSON fields for flexible metadata storage

**Critical Fields:**
- `case_id`: Links audit to a case
- `user_id`: Who did the action
- `sar_reasoning`: AI-generated suspicious activity reasoning
- `sar_report_content`: Complete SAR report
- `sar_filing_number`: Official FinCEN filing number
- `environment_data`: User's browser, OS, device info

**Why it matters:** This is the foundation - everything else reads/writes to this table.

---

### `backend/services/audit/environment_tracker.py`
**What it does:**
- Captures complete environment context when any action happens
- Records browser, OS, device, IP address, timezone
- Critical for regulatory compliance and investigations

**Key Functions:**
- `capture_environment()`: Gets all environment info from HTTP request
- `_parse_user_agent()`: Extracts browser and OS from user agent string
- `extract_key_environment_fields()`: Pulls key fields for database columns
- `sanitize_environment_data()`: Removes sensitive headers (passwords, tokens)

**Example Output:**
```json
{
  "captured_at": "2024-02-13T10:30:00",
  "system": {
    "platform": "Windows-10",
    "python_version": "3.11.5"
  },
  "client": {
    "browser": "Chrome",
    "browser_version": "120.0",
    "os": "Windows",
    "device_type": "desktop",
    "ip_address": "192.168.1.100"
  }
}
```

**Why it matters:** Proves WHO did WHAT, WHEN, WHERE for regulatory audits.

---

### `backend/services/audit/case_audit.py`
**What it does:**
- Tracks all case-related activities
- Logs case creation, updates, viewing
- Tracks alert additions and reviews

**Key Functions:**
- `log_case_created()`: Records new case creation
- `log_case_updated()`: Tracks changes with before/after values
- `log_alert_added()`: Records suspicious alerts added to case
- `log_alert_reviewed()`: Logs analyst review decisions
- `log_case_viewed()`: Tracks who viewed the case (access audit)
- `get_case_audit_history()`: Retrieves complete case timeline

**Example Usage:**
```python
case_service = CaseAuditService(db)

# Log case creation
case_service.log_case_created(
    case_id="CASE-2024-001",
    case_number="2024-001",
    user_id="analyst123",
    user_email="analyst@bank.com",
    initial_data={"status": "new", "priority": "high"},
    request=request,
)
```

**Why it matters:** Provides complete audit trail of case lifecycle.

---

### `backend/services/audit/sar_audit.py` ⭐ MOST CRITICAL
**What it does:**
- Tracks ENTIRE SAR generation process (most regulated part)
- Captures AI reasoning, report generation, reviews, submissions
- Ensures regulatory compliance with FinCEN requirements

**Key Functions:**

1. **`log_sar_generation_started()`**
   - Records when SAR generation begins
   - Captures request data, alerts, user info
   - Severity: CRITICAL

2. **`log_sar_reasoning_generated()`** ⭐
   - Stores AI-generated reasoning for suspicious activity
   - Records model name, version, tokens, confidence score
   - This is what regulators review to understand AI decisions
   - Severity: CRITICAL

3. **`log_sar_report_generated()`** ⭐
   - Stores complete SAR report content
   - Records format, sections, generation metadata
   - Severity: CRITICAL

4. **`log_sar_report_reviewed()`**
   - Tracks compliance officer review
   - Records approval/rejection decision
   - Captures requested changes
   - Severity: CRITICAL

5. **`log_sar_report_submitted()`** ⭐
   - Records submission to FinCEN
   - Stores official filing number
   - Captures confirmation number
   - Retention: 10 years (regulatory filing)
   - Severity: CRITICAL

6. **`log_sar_generation_failed()`**
   - Logs errors in SAR generation
   - Captures stack trace for debugging
   - Severity: CRITICAL

7. **`get_sar_audit_trail()`**
   - Retrieves complete SAR workflow for a case
   - Returns all SAR events in chronological order

8. **`get_sar_by_filing_number()`**
   - Finds SAR by official filing number
   - Used for regulatory examinations

**Example Usage:**
```python
sar_service = SARAuditService(db)

# Start SAR generation
sar_service.log_sar_generation_started(
    case_id="CASE-001",
    alert_ids=["ALERT-001", "ALERT-002"],
    user_id="analyst123",
    user_email="analyst@bank.com",
    request_data={"alerts": ["ALERT-001"]},
)

# Log AI reasoning
sar_service.log_sar_reasoning_generated(
    case_id="CASE-001",
    alert_ids=["ALERT-001", "ALERT-002"],
    user_id="analyst123",
    user_email="analyst@bank.com",
    reasoning_text="Customer made multiple $9,500 deposits...",
    reasoning_metadata={
        "model_name": "gpt-4",
        "confidence_score": 0.94,
        "prompt_tokens": 2000,
        "completion_tokens": 600,
    },
    processing_time_ms=2500,
)

# Submit to FinCEN
sar_service.log_sar_report_submitted(
    case_id="CASE-001",
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

**Why it matters:** This is THE MOST CRITICAL component for regulatory compliance. Every SAR must have complete audit trail showing reasoning, generation, review, and submission.

---

### `backend/api/endpoints/audit.py`
**What it does:**
- Provides REST API endpoints to query audit data
- Allows filtering, searching, pagination
- Generates compliance reports

**Key Endpoints:**

1. **`GET /api/v1/audit/logs`**
   - Query audit logs with filters
   - Parameters: case_id, user_id, event_type, date range
   - Returns paginated results

2. **`GET /api/v1/audit/logs/{audit_id}`**
   - Get detailed info for specific audit entry
   - Returns full audit log with all fields

3. **`GET /api/v1/audit/case/{case_id}/history`**
   - Get complete history for a case
   - All events related to case ID

4. **`GET /api/v1/audit/case/{case_id}/sar-trail`**
   - Get SAR-specific audit trail
   - Only SAR generation events

5. **`GET /api/v1/audit/sar/filing/{filing_number}`**
   - Find SAR by official filing number
   - Used by regulators

6. **`GET /api/v1/audit/user/{user_id}/activity`**
   - Get user's activity history
   - For internal audits

7. **`GET /api/v1/audit/stats`**
   - Get statistics (total events, SARs generated, errors)
   - Dashboard metrics

8. **`GET /api/v1/audit/search`**
   - Full-text search across audit logs
   - Search notes, errors, reasons

9. **`GET /api/v1/audit/compliance/report`**
   - Generate compliance report for regulators
   - Filter by date range and cases

**Example Usage:**
```bash
# Get case history
curl http://localhost:8000/api/v1/audit/case/CASE-001/history

# Get SAR trail
curl http://localhost:8000/api/v1/audit/case/CASE-001/sar-trail

# Find by filing number
curl http://localhost:8000/api/v1/audit/sar/filing/SAR-2024-12345678

# Get statistics
curl http://localhost:8000/api/v1/audit/stats?days=30
```

**Why it matters:** Enables programmatic access to audit data for reporting and compliance.

---

### `backend/core/config.py`
**What it does:**
- Central configuration management
- Environment variables and settings
- Database connection settings

**Key Settings:**
- `DATABASE_URL`: PostgreSQL connection string
- `AUDIT_RETENTION_DAYS`: How long to keep records (default: 7 years)
- `SECRET_KEY`: Encryption key
- `LOG_LEVEL`: Logging verbosity
- `MAX_AUDIT_QUERY_LIMIT`: Maximum records to return

**Why it matters:** Single place to configure the entire system.

---

### `backend/db/base.py`
**What it does:**
- Database base configuration
- SQLAlchemy declarative base
- Naming conventions for constraints

**Why it matters:** Foundation for all database models.

---

### `backend/db/session.py`
**What it does:**
- Database session management
- Connection pooling
- Transaction handling

**Key Functions:**
- `get_db()`: FastAPI dependency for database session
- `get_db_context()`: Context manager for standalone scripts
- `init_db()`: Create all tables

**Why it matters:** Manages database connections efficiently and safely.

---

## 🧪 Test Files

### `tests/unit/test_environment_tracking.py`
**What it does:**
- Tests environment capture functionality
- Tests user agent parsing
- Tests data sanitization

**Tests:**
- Browser detection (Chrome, Firefox, Safari, Edge)
- OS detection (Windows, macOS, Linux, iOS, Android)
- Device type (desktop, mobile, tablet)
- PII sanitization

---

### `tests/unit/test_case_audit.py`
**What it does:**
- Tests case audit service functions
- Tests case creation, updates, alert tracking
- Verifies proper logging of all case events

**Tests:**
- Case creation logging
- Case update with before/after values
- Alert addition
- Alert review
- Severity assignment
- Payload sanitization

---

### `tests/unit/test_sar_audit.py` ⭐ CRITICAL TESTS
**What it does:**
- Tests SAR audit service (most critical component)
- Verifies complete SAR workflow
- Ensures regulatory compliance requirements

**Tests:**
- SAR generation start logging
- AI reasoning capture with metadata
- Report generation with full content
- Review workflow (approval/rejection)
- Submission with filing numbers
- Error handling and failure logging
- Complete end-to-end SAR workflow

**Why it matters:** These tests ensure regulatory compliance. If these fail, SAR auditing is broken.

---

### `tests/integration/test_complete_workflow.py`
**What it does:**
- Tests complete end-to-end workflow
- Simulates real-world SAR generation process
- Verifies all components work together

**Workflow Tested:**
1. Create case
2. Add suspicious alerts
3. Review alerts
4. Start SAR generation
5. AI generates reasoning
6. AI generates report
7. Compliance officer reviews
8. Submit to FinCEN

**Why it matters:** Proves the entire system works together correctly.

---

## 🔧 Scripts

### `scripts/setup_audit_db.py`
**What it does:**
- Initializes database
- Creates all tables
- Optionally seeds sample data

**Commands:**
```bash
# Create tables
python scripts/setup_audit_db.py

# Create tables with sample data
python scripts/setup_audit_db.py --seed

# Drop and recreate (WARNING: deletes all data!)
python scripts/setup_audit_db.py --drop

# Just verify tables exist
python scripts/setup_audit_db.py --verify-only
```

**Why it matters:** First script you run to set up the system.

---

### `scripts/query_audit_trail.py`
**What it does:**
- Command-line tool to query audit data
- View cases, users, SARs, statistics
- No need to write SQL

**Commands:**
```bash
# View case history
python scripts/query_audit_trail.py case CASE-2024-001

# View user activity (last 30 days)
python scripts/query_audit_trail.py user analyst123 --days 30

# View SAR audit trail
python scripts/query_audit_trail.py sar CASE-2024-001

# Find by filing number
python scripts/query_audit_trail.py filing SAR-2024-12345678

# Get statistics
python scripts/query_audit_trail.py stats --days 30
```

**Why it matters:** Easy way to inspect audit data without SQL knowledge.

---

## ⚙️ Configuration

### `config/audit_config.yaml`
**What it does:**
- YAML configuration file
- Detailed settings for all components
- Alternative to .env file

**Sections:**
- Database settings
- Audit settings (retention, batch size)
- Compliance settings (regulatory requirements)
- Logging configuration
- API settings
- Security settings
- Alerting configuration
- Backup settings
- Monitoring settings

**Why it matters:** Centralized configuration for production deployments.

---

### `.env` (you create this)
**What it does:**
- Environment-specific settings
- Database credentials
- Secret keys

**Required Contents:**
```env
DATABASE_URL=postgresql://audit_user:audit_password@localhost:5432/sar_audit
SECRET_KEY=your-secret-key
ENVIRONMENT=development
DEBUG=True
```

**Why it matters:** Keeps secrets out of code.

---

## 📦 Package Files

### `requirements.txt`
**What it does:**
- Lists all Python dependencies
- Version specifications

**Key Dependencies:**
- `fastapi`: Web framework
- `sqlalchemy`: Database ORM
- `psycopg2-binary`: PostgreSQL driver
- `pydantic`: Data validation
- `pytest`: Testing framework
- `python-dateutil`: Date handling
- `pyyaml`: YAML config parsing

**Usage:**
```bash
pip install -r requirements.txt
```

---

### `setup.py`
**What it does:**
- Package installation configuration
- Defines package metadata
- Lists dependencies

**Usage:**
```bash
pip install -e .  # Install in development mode
```

---

## 📚 Documentation

### `README.md`
**What it does:**
- Main documentation
- Quick start guide
- Usage examples
- API overview

**Who reads it:** Everyone starting with the system.

---

### `GETTING_STARTED.md`
**What it does:**
- Step-by-step setup guide
- Basic usage examples
- Common tasks
- Troubleshooting

**Who reads it:** New users setting up for first time.

---

### `POSTGRESQL_SETUP.md` / `DOCKER_POSTGRES_GUIDE.md`
**What it does:**
- PostgreSQL installation instructions
- Docker setup guide
- Connection troubleshooting

**Who reads it:** DevOps, first-time installers.

---

### `VERIFICATION_COMMANDS.md`
**What it does:**
- Commands to verify system is working
- Health checks
- Test commands

**Who reads it:** Anyone verifying the installation.

---

## 🔍 How Files Work Together

### Example: Logging a SAR Generation

1. **Your application** calls:
   ```python
   sar_service.log_sar_generation_started(...)
   ```

2. **`sar_audit.py`** processes the request:
   - Calls `environment_tracker.py` to capture environment
   - Creates `AuditLog` object (from `audit_log.py`)
   - Sets event_type = SAR_GENERATION_STARTED
   - Sets severity = CRITICAL

3. **`environment_tracker.py`** captures:
   - Browser: Chrome 120
   - OS: Windows 10
   - IP: 192.168.1.100
   - Timezone: America/New_York

4. **`session.py`** manages database:
   - Opens connection
   - Commits transaction
   - Closes connection

5. **`audit_log.py`** model saves to database:
   - Inserts row into `audit_logs` table
   - Auto-generates UUID
   - Sets timestamp

6. **Later, query it:**
   ```bash
   python scripts/query_audit_trail.py sar CASE-001
   ```

7. **`query_audit_trail.py`** retrieves:
   - Uses `session.py` to connect
   - Queries `AuditLog` model
   - Filters by case_id
   - Displays results

---

## 📊 Data Flow Diagram

```
User Action (Web/API)
    ↓
Case/SAR Audit Service (case_audit.py / sar_audit.py)
    ↓
Environment Tracker (environment_tracker.py) → Captures context
    ↓
Audit Log Model (audit_log.py) → Creates database record
    ↓
Session Manager (session.py) → Commits to database
    ↓
PostgreSQL Database (audit_logs table)
    ↓
Query Scripts / API (query_audit_trail.py / audit.py)
    ↓
Reports / Compliance / Investigation
```

---

## 🎯 Most Important Files (Priority Order)

1. **`audit_log.py`** - Database model, stores everything
2. **`sar_audit.py`** - SAR auditing (regulatory critical)
3. **`case_audit.py`** - Case lifecycle tracking
4. **`environment_tracker.py`** - Context capture
5. **`session.py`** - Database connectivity
6. **`setup_audit_db.py`** - Database initialization
7. **`query_audit_trail.py`** - Query tool
8. **`test_sar_audit.py`** - Critical tests

---

## ❓ Quick Reference

**Want to:**
- **Set up database?** → Run `setup_audit_db.py`
- **Log a case?** → Use `CaseAuditService` from `case_audit.py`
- **Log SAR?** → Use `SARAuditService` from `sar_audit.py`
- **Query data?** → Run `query_audit_trail.py` or use API from `audit.py`
- **Verify system?** → Run `verify_system.py`
- **Test everything?** → Run `pytest tests/`

---

## 🔐 Security & Compliance Files

Files handling sensitive data or regulatory requirements:
- `audit_log.py` - PII sanitization
- `sar_audit.py` - Regulatory compliance
- `environment_tracker.py` - Privacy protection
- `config.py` - Security settings

---

This system has **17 main files** working together to provide complete, regulatory-compliant audit trail for SAR generation!