# SAR Audit Trail System - Complete Command Reference
## From Installation to Viewing Logs

This file contains ALL commands you need to set up and use the SAR Audit Trail System.

---

## 📦 PART 1: INITIAL SETUP

### Step 1: Download and Extract Project

```powershell
# Navigate to your projects folder
cd "E:\projects\Hack o hire"

# Extract audit-trail-system.zip (if not already done)
# You should now have: E:\projects\Hack o hire\audit-trail-system
```

---

### Step 2: Install Python Dependencies

```powershell
# Navigate to project directory
cd "E:\projects\Hack o hire\audit-trail-system"

# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list | findstr -i "fastapi sqlalchemy psycopg2"
```

**Expected packages:**
- fastapi
- sqlalchemy
- psycopg2-binary
- pydantic
- pytest

---

## 🐳 PART 2: POSTGRESQL SETUP (DOCKER)

### Step 1: Install Docker Desktop

1. Download from: https://www.docker.com/products/docker-desktop/
2. Install and restart computer
3. Start Docker Desktop
4. Verify: `docker --version`

---

### Step 2: Run PostgreSQL in Docker

```powershell
# Start PostgreSQL container
docker run --name audit-postgres `
  -e POSTGRES_USER=VED `
  -e POSTGRES_PASSWORD=mypassword123 `
  -e POSTGRES_DB=sar_audit `
  -p 5432:5432 `
  -d postgres:15

# Wait 10-15 seconds for PostgreSQL to initialize

# Verify container is running
docker ps

# Should show:
# CONTAINER ID   IMAGE         STATUS         PORTS                    NAMES
# xxxxxxxxxxxx   postgres:15   Up 10 seconds  0.0.0.0:5432->5432/tcp   audit-postgres
```

---

### Step 3: Verify PostgreSQL is Accessible

```powershell
# Connect to PostgreSQL
docker exec -it audit-postgres psql -U VED -d sar_audit

# You should see:
# psql (15.16)
# Type "help" for help.
# sar_audit=#

# Inside psql, run:
\l                          # List databases
\q                          # Quit
```

---

### Step 4: Create .env Configuration File

```powershell
# Create .env file in project root
cd "E:\projects\Hack o hire\audit-trail-system"

# Create .env file with credentials
@"
DATABASE_URL=postgresql://VED:mypassword123@localhost:5432/sar_audit
SECRET_KEY=dev-secret-key-change-in-production
ENVIRONMENT=development
DEBUG=True
"@ | Out-File -FilePath .env -Encoding UTF8

# Verify .env was created
cat .env
```

---

## 🗄️ PART 3: DATABASE INITIALIZATION

### Step 1: Create Database Tables

```powershell
# Navigate to project directory
cd "E:\projects\Hack o hire\audit-trail-system"

# Create tables without sample data
python scripts/setup_audit_db.py

# OR create tables WITH sample data (recommended)
python scripts/setup_audit_db.py --seed
```

**Expected output:**
```
============================================================
Audit Trail System - Database Setup
============================================================
Creating database tables...
✓ Tables created successfully

Verifying tables...
Found 1 table(s):
  - audit_logs
✓ audit_logs table exists

Found 7 index(es) on audit_logs:
  - pk_audit_logs
  - ix_audit_logs_id
  - idx_event_timestamp_desc
  - idx_case_event
  - idx_user_timestamp
  - idx_sar_filing
  - idx_session_timestamp

Seeding sample data...
✓ Seeded 3 sample audit logs

============================================================
Database setup completed successfully!
============================================================
```

---

### Step 2: Verify Tables Were Created

```powershell
# Method 1: Via psql
docker exec -it audit-postgres psql -U VED -d sar_audit -c "\dt"

# Method 2: Via Python
python -c "from sqlalchemy import inspect; from backend.db.session import engine; print('Tables:', inspect(engine).get_table_names())"
```

**Expected output:**
```
Tables: ['audit_logs']
```

---

### Step 3: Verify Database Connection

```powershell
# Test connection
python -c "from backend.db.session import engine; conn = engine.connect(); print('✓ Database connected!'); conn.close()"

# Count records
python -c "from backend.db.session import SessionLocal; from backend.models.audit_log import AuditLog; db = SessionLocal(); print(f'Total audit records: {db.query(AuditLog).count()}'); db.close()"
```

**Expected output:**
```
✓ Database connected!
Total audit records: 3
```

---

## 🔍 PART 4: QUERYING AUDIT LOGS (COMMAND LINE)

### Basic Queries

```powershell
# View statistics
python scripts/query_audit_trail.py stats

# View specific case
python scripts/query_audit_trail.py case CASE-SAMPLE-001

# View user activity (last 30 days)
python scripts/query_audit_trail.py user analyst_001 --days 30

# View SAR audit trail
python scripts/query_audit_trail.py sar CASE-SAMPLE-001

# Find by filing number
python scripts/query_audit_trail.py filing SAR-2024-SAMPLE-001
```

---

### Advanced Queries (Direct SQL via psql)

```powershell
# Connect to database
docker exec -it audit-postgres psql -U VED -d sar_audit

# Inside psql, run these queries:
```

```sql
-- View all logs (last 10)
SELECT 
    event_timestamp,
    event_type,
    case_id,
    user_id,
    severity
FROM audit_logs 
ORDER BY event_timestamp DESC 
LIMIT 10;

-- Count logs by event type
SELECT 
    event_type,
    COUNT(*) as count
FROM audit_logs 
GROUP BY event_type
ORDER BY count DESC;

-- Count logs by severity
SELECT 
    severity,
    COUNT(*) as count
FROM audit_logs 
GROUP BY severity
ORDER BY 
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END;

-- View all critical events
SELECT 
    event_timestamp,
    event_type,
    case_id,
    user_id,
    notes
FROM audit_logs 
WHERE severity = 'critical'
ORDER BY event_timestamp DESC;

-- View SAR submissions
SELECT 
    event_timestamp,
    case_id,
    user_id,
    sar_filing_number
FROM audit_logs 
WHERE event_type = 'sar_report_submitted'
ORDER BY event_timestamp DESC;

-- View SAR generation workflow for a case
SELECT 
    event_timestamp,
    event_type,
    user_id,
    processing_duration_ms
FROM audit_logs 
WHERE case_id = 'CASE-SAMPLE-001'
ORDER BY event_timestamp ASC;

-- Count total records
SELECT COUNT(*) as total_logs FROM audit_logs;

-- View latest record with all details
SELECT * FROM audit_logs ORDER BY event_timestamp DESC LIMIT 1;

-- Exit psql
\q
```

---

## 🌐 PART 5: VIEWING LOGS IN PGADMIN (WEB INTERFACE)

### Step 1: Install and Run pgAdmin

```powershell
# Remove old pgAdmin container (if exists)
docker rm -f pgadmin

# Run pgAdmin in Docker
docker run -p 5050:80 `
  -e PGADMIN_DEFAULT_EMAIL=admin@admin.com `
  -e PGADMIN_DEFAULT_PASSWORD=admin `
  --name pgadmin `
  -d dpage/pgadmin4

# Wait 10-20 seconds for pgAdmin to start

# Verify it's running
docker ps | findstr pgadmin

# Open pgAdmin in browser
start http://localhost:5050
```

---

### Step 2: Login to pgAdmin

**URL:** http://localhost:5050

**Credentials:**
- Email: `admin@admin.com`
- Password: `admin`

Click **Login**

---

### Step 3: Add Database Server in pgAdmin

1. **Right-click "Servers"** in left sidebar
2. Click **Register** → **Server**

**General Tab:**
- Name: `SAR Audit Trail`

**Connection Tab:**
- Host name/address: `host.docker.internal`
- Port: `5432`
- Maintenance database: `sar_audit`
- Username: `VED`
- Password: `mypassword123`
- ✅ Save password: **checked**

Click **Save**

---

### Step 4: Navigate to Audit Logs Table

**Left Sidebar Navigation:**
```
Servers
  └─ SAR Audit Trail
      └─ Databases
          └─ sar_audit
              └─ Schemas
                  └─ public
                      └─ Tables
                          └─ audit_logs
```

---

### Step 5: View Data in pgAdmin

**Option 1: View All Rows**
- Right-click `audit_logs`
- Select **View/Edit Data** → **All Rows**

**Option 2: Run Custom Query**
- Right-click `sar_audit` database
- Select **Query Tool**
- Paste any SQL query from Part 4
- Click **Execute** (F5)

---

## 🧪 PART 6: TESTING THE SYSTEM

### Run Unit Tests

```powershell
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_sar_audit.py -v

# Run with coverage
pytest tests/unit/ --cov=backend --cov-report=html
```

---

### Run Integration Tests

```powershell
# Run integration tests
pytest tests/integration/ -v

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/integration/test_complete_workflow.py::TestCompleteSARWorkflow::test_complete_sar_generation_workflow -v
```

---

### Run System Verification

```powershell
# Copy verify_system.py to scripts folder
# Then run:
python scripts/verify_system.py
```

**Expected output:**
```
======================================================================
SAR Audit Trail System - Verification
======================================================================

Test 1: Database Connection
----------------------------------------------------------------------
✓ Database connection successful
  Connected to: postgresql://VED:***@localhost:5432/sar_audit

Test 2: Database Tables
----------------------------------------------------------------------
✓ audit_logs table exists
✓ All critical columns present (47 total)

Test 3: Query Audit Logs
----------------------------------------------------------------------
✓ Successfully queried audit logs
  Total records: 3
  Latest event: case_created

... (more tests)

======================================================================
Verification Complete!
======================================================================

✅ System Status: OPERATIONAL
```

---

## 📝 PART 7: CREATING TEST AUDIT LOGS

### Create Sample Logs

```powershell
# Method 1: Using setup script
python scripts/setup_audit_db.py --seed

# Method 2: Quick test workflow
python -c "
from backend.services.audit.case_audit import CaseAuditService
from backend.services.audit.sar_audit import SARAuditService
from backend.db.session import SessionLocal

db = SessionLocal()
case_svc = CaseAuditService(db)
sar_svc = SARAuditService(db)

# Create case
case_svc.log_case_created('TEST-001', 'T-001', 'user1', 'user1@test.com', {'status': 'new'})
print('✓ Case created')

# Add alerts
case_svc.log_alert_added('TEST-001', ['ALERT-1', 'ALERT-2'], 'user1', 'user1@test.com')
print('✓ Alerts added')

# Start SAR
sar_svc.log_sar_generation_started('TEST-001', ['ALERT-1'], 'user1', 'user1@test.com', {})
print('✓ SAR started')

# Generate reasoning
sar_svc.log_sar_reasoning_generated('TEST-001', ['ALERT-1'], 'user1', 'user1@test.com', 'Suspicious pattern detected', {'model': 'gpt-4'}, 1000)
print('✓ Reasoning generated')

# Generate report
sar_svc.log_sar_report_generated('TEST-001', ['ALERT-1'], 'user1', 'user1@test.com', 'SAR Report Content', {'format': 'PDF'}, 2000)
print('✓ Report generated')

# Submit SAR
sar_svc.log_sar_report_submitted('TEST-001', 'supervisor1', 'sup@test.com', 'SAR-2024-TEST-001', {'date': '2024-02-13'})
print('✓ SAR submitted')

print(f'\n✅ Complete workflow created!')
print('View with: python scripts/query_audit_trail.py case TEST-001')

db.close()
"
```

---

### Create Custom Log

```powershell
# Create case audit
python -c "
from backend.services.audit.case_audit import CaseAuditService
from backend.db.session import SessionLocal

db = SessionLocal()
service = CaseAuditService(db)

entry = service.log_case_created(
    case_id='CUSTOM-CASE-001',
    case_number='CC-001',
    user_id='my_user',
    user_email='me@example.com',
    initial_data={'priority': 'high', 'status': 'investigating'}
)

print(f'Created audit entry: {entry.id}')
print(f'Event: {entry.event_type.value}')
print(f'Timestamp: {entry.event_timestamp}')

db.close()
"
```

---

## 🔧 PART 8: DOCKER MANAGEMENT COMMANDS

### PostgreSQL Container

```powershell
# Start PostgreSQL
docker start audit-postgres

# Stop PostgreSQL
docker stop audit-postgres

# Restart PostgreSQL
docker restart audit-postgres

# View logs
docker logs audit-postgres

# Follow logs (live)
docker logs -f audit-postgres

# Check if running
docker ps | findstr audit-postgres

# Connect to PostgreSQL
docker exec -it audit-postgres psql -U VED -d sar_audit

# Execute SQL command directly
docker exec -it audit-postgres psql -U VED -d sar_audit -c "SELECT COUNT(*) FROM audit_logs;"

# Remove container (WARNING: deletes data!)
docker stop audit-postgres
docker rm audit-postgres
```

---

### pgAdmin Container

```powershell
# Start pgAdmin
docker start pgadmin

# Stop pgAdmin
docker stop pgadmin

# Restart pgAdmin
docker restart pgadmin

# View logs
docker logs pgadmin

# Check if running
docker ps | findstr pgadmin

# Remove container
docker stop pgadmin
docker rm pgadmin

# Access in browser
start http://localhost:5050
```

---

### Both Containers

```powershell
# View all running containers
docker ps

# View all containers (including stopped)
docker ps -a

# Start all stopped containers
docker start audit-postgres pgadmin

# Stop all containers
docker stop audit-postgres pgadmin

# Remove all containers
docker rm -f audit-postgres pgadmin
```

---

## 💾 PART 9: BACKUP AND RESTORE

### Backup Database

```powershell
# Backup to SQL file
docker exec -it audit-postgres pg_dump -U VED sar_audit > sar_audit_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Backup to custom format (compressed)
docker exec -it audit-postgres pg_dump -U VED -Fc sar_audit > sar_audit_backup.dump

# Backup specific table
docker exec -it audit-postgres pg_dump -U VED -t audit_logs sar_audit > audit_logs_backup.sql
```

---

### Restore Database

```powershell
# Restore from SQL file
Get-Content sar_audit_backup.sql | docker exec -i audit-postgres psql -U VED -d sar_audit

# Restore from custom format
docker exec -i audit-postgres pg_restore -U VED -d sar_audit -c < sar_audit_backup.dump

# Create new database and restore
docker exec -it audit-postgres psql -U VED -c "CREATE DATABASE sar_audit_restored;"
Get-Content sar_audit_backup.sql | docker exec -i audit-postgres psql -U VED -d sar_audit_restored
```

---

### Export Data to CSV

```powershell
# Export all audit logs to CSV
docker exec -it audit-postgres psql -U VED -d sar_audit -c "COPY (SELECT * FROM audit_logs) TO STDOUT WITH CSV HEADER" > audit_logs_export.csv

# Export specific fields
docker exec -it audit-postgres psql -U VED -d sar_audit -c "COPY (SELECT event_timestamp, event_type, case_id, user_id FROM audit_logs ORDER BY event_timestamp DESC) TO STDOUT WITH CSV HEADER" > audit_logs_summary.csv
```

---

## 🚨 PART 10: TROUBLESHOOTING COMMANDS

### Check Connection

```powershell
# Test database connection
python -c "from backend.db.session import engine; conn = engine.connect(); print('✓ Connected'); conn.close()"

# Check if PostgreSQL is accepting connections
docker exec -it audit-postgres pg_isready -U VED

# Check database exists
docker exec -it audit-postgres psql -U VED -c "\l" | findstr sar_audit
```

---

### Check Tables

```powershell
# List all tables
docker exec -it audit-postgres psql -U VED -d sar_audit -c "\dt"

# Describe audit_logs table
docker exec -it audit-postgres psql -U VED -d sar_audit -c "\d audit_logs"

# Count records
docker exec -it audit-postgres psql -U VED -d sar_audit -c "SELECT COUNT(*) FROM audit_logs;"
```

---

### Reset Database

```powershell
# Drop and recreate database
docker exec -it audit-postgres psql -U VED -c "DROP DATABASE IF EXISTS sar_audit;"
docker exec -it audit-postgres psql -U VED -c "CREATE DATABASE sar_audit;"

# Recreate tables
python scripts/setup_audit_db.py --seed
```

---

### Check Logs for Errors

```powershell
# PostgreSQL logs
docker logs audit-postgres --tail 50

# pgAdmin logs
docker logs pgadmin --tail 50

# Check for connection errors
docker logs audit-postgres 2>&1 | findstr -i "error"
```

---

### Reset Password

```powershell
# Reset VED password
docker exec -it audit-postgres psql -U postgres -c "ALTER USER VED WITH PASSWORD 'newpassword';"

# Update .env file
@"
DATABASE_URL=postgresql://VED:newpassword@localhost:5432/sar_audit
SECRET_KEY=dev-secret-key
ENVIRONMENT=development
DEBUG=True
"@ | Out-File -FilePath .env -Encoding UTF8 -Force
```

---

## 📊 PART 11: USEFUL SQL QUERIES

### Statistics Queries

```sql
-- Total logs
SELECT COUNT(*) as total FROM audit_logs;

-- Logs by severity
SELECT severity, COUNT(*) as count
FROM audit_logs
GROUP BY severity
ORDER BY count DESC;

-- Logs by event type
SELECT event_type, COUNT(*) as count
FROM audit_logs
GROUP BY event_type
ORDER BY count DESC;

-- Logs per day (last 7 days)
SELECT 
    DATE(event_timestamp) as date,
    COUNT(*) as logs_count
FROM audit_logs
WHERE event_timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(event_timestamp)
ORDER BY date DESC;

-- Most active users
SELECT 
    user_id,
    COUNT(*) as actions
FROM audit_logs
GROUP BY user_id
ORDER BY actions DESC
LIMIT 10;

-- Cases with most activity
SELECT 
    case_id,
    COUNT(*) as events
FROM audit_logs
WHERE case_id IS NOT NULL
GROUP BY case_id
ORDER BY events DESC
LIMIT 10;
```

---

### SAR-Specific Queries

```sql
-- All SAR events for a case
SELECT 
    event_timestamp,
    event_type,
    user_id,
    processing_duration_ms
FROM audit_logs
WHERE case_id = 'CASE-SAMPLE-001'
  AND event_type LIKE 'sar_%'
ORDER BY event_timestamp ASC;

-- SAR generation success rate
SELECT 
    COUNT(CASE WHEN event_type = 'sar_report_submitted' THEN 1 END) as submitted,
    COUNT(CASE WHEN event_type = 'sar_generation_started' THEN 1 END) as started,
    ROUND(
        100.0 * COUNT(CASE WHEN event_type = 'sar_report_submitted' THEN 1 END) / 
        NULLIF(COUNT(CASE WHEN event_type = 'sar_generation_started' THEN 1 END), 0),
        2
    ) as success_rate_percent
FROM audit_logs;

-- Average SAR generation time
SELECT 
    AVG(processing_duration_ms) as avg_ms,
    MIN(processing_duration_ms) as min_ms,
    MAX(processing_duration_ms) as max_ms
FROM audit_logs
WHERE event_type IN ('sar_reasoning_generated', 'sar_report_generated')
  AND processing_duration_ms IS NOT NULL;

-- SAR reports by filing number
SELECT 
    sar_filing_number,
    case_id,
    user_id,
    event_timestamp
FROM audit_logs
WHERE sar_filing_number IS NOT NULL
ORDER BY event_timestamp DESC;
```

---

### Search Queries

```sql
-- Search by case ID
SELECT * FROM audit_logs WHERE case_id = 'CASE-001';

-- Search by user
SELECT * FROM audit_logs WHERE user_id = 'analyst123';

-- Search by date range
SELECT * FROM audit_logs 
WHERE event_timestamp BETWEEN '2024-02-01' AND '2024-02-14';

-- Search in notes
SELECT * FROM audit_logs 
WHERE notes LIKE '%suspicious%'
ORDER BY event_timestamp DESC;

-- Search for errors
SELECT * FROM audit_logs 
WHERE error_occurred = true
ORDER BY event_timestamp DESC;

-- Search critical events
SELECT * FROM audit_logs 
WHERE severity = 'critical'
ORDER BY event_timestamp DESC;
```

---

## 🎯 PART 12: QUICK REFERENCE COMMANDS

### Start Everything

```powershell
# Start PostgreSQL
docker start audit-postgres

# Start pgAdmin
docker start pgadmin

# Verify both running
docker ps

# Open pgAdmin
start http://localhost:5050
```

---

### Stop Everything

```powershell
# Stop PostgreSQL
docker stop audit-postgres

# Stop pgAdmin
docker stop pgadmin

# Verify stopped
docker ps -a
```

---

### Daily Commands

```powershell
# View stats
python scripts/query_audit_trail.py stats

# View recent logs
python scripts/query_audit_trail.py case CASE-001

# Check system health
python -c "from backend.db.session import SessionLocal; from backend.models.audit_log import AuditLog; db = SessionLocal(); print(f'System OK - {db.query(AuditLog).count()} records'); db.close()"

# Create test log
python -c "from backend.services.audit.case_audit import CaseAuditService; from backend.db.session import SessionLocal; db = SessionLocal(); s = CaseAuditService(db); s.log_case_created('TEST', 'T1', 'u1', 'u@e.com', {}); print('✓ Test log created'); db.close()"
```

---

## 📞 PART 13: SUPPORT COMMANDS

### Get Version Info

```powershell
# Python version
python --version

# Docker version
docker --version

# PostgreSQL version
docker exec -it audit-postgres psql -U VED -c "SELECT version();"

# Package versions
pip list | findstr -i "fastapi sqlalchemy psycopg2 pydantic pytest"
```

---

### System Information

```powershell
# Database info
docker exec -it audit-postgres psql -U VED -d sar_audit -c "
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'sar_audit';
"

# Table size
docker exec -it audit-postgres psql -U VED -d sar_audit -c "
SELECT 
    pg_size_pretty(pg_total_relation_size('audit_logs')) AS total_size,
    pg_size_pretty(pg_relation_size('audit_logs')) AS table_size,
    pg_size_pretty(pg_indexes_size('audit_logs')) AS indexes_size;
"

# Connection info
docker exec -it audit-postgres psql -U VED -d sar_audit -c "
SELECT 
    datname,
    usename,
    application_name,
    client_addr,
    state
FROM pg_stat_activity
WHERE datname = 'sar_audit';
"
```

---

## 🎓 END OF COMMAND REFERENCE

This file contains every command you need to:
- ✅ Install and setup the system
- ✅ Create and manage database
- ✅ Query audit logs
- ✅ View logs in pgAdmin
- ✅ Run tests
- ✅ Backup and restore
- ✅ Troubleshoot issues
- ✅ Monitor system health

**Save this file for future reference!**

---

## 📝 Notes

- Replace `mypassword123` with your actual password
- All commands assume PostgreSQL user is `VED`
- pgAdmin runs on port 5050, PostgreSQL on port 5432
- Docker containers persist data unless explicitly removed with `-v` flag
- Always backup before major changes

**Last Updated:** February 2024
**System Version:** 1.0.0