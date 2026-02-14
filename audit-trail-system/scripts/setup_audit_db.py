#!/usr/bin/env python3
"""
Database Setup Script for Audit Trail System

This script creates the database tables and optionally seeds sample data.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.session import engine, init_db
from backend.db.base import Base
from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity
from sqlalchemy import text
from datetime import datetime


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully")
        return True
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        return False


def drop_tables():
    """Drop all database tables (use with caution!)"""
    print("WARNING: This will drop all tables!")
    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return False
    
    try:
        Base.metadata.drop_all(bind=engine)
        print("✓ Tables dropped successfully")
        return True
    except Exception as e:
        print(f"✗ Error dropping tables: {e}")
        return False


def verify_tables():
    """Verify tables were created correctly"""
    print("\nVerifying tables...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            
            print(f"Found {len(tables)} table(s):")
            for table in tables:
                print(f"  - {table}")
            
            if 'audit_logs' in tables:
                print("✓ audit_logs table exists")
                
                # Check indexes
                result = conn.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'audit_logs'
                    ORDER BY indexname;
                """))
                indexes = [row[0] for row in result]
                print(f"\nFound {len(indexes)} index(es) on audit_logs:")
                for idx in indexes:
                    print(f"  - {idx}")
                
                return True
            else:
                print("✗ audit_logs table not found")
                return False
                
    except Exception as e:
        print(f"✗ Error verifying tables: {e}")
        return False


def seed_sample_data():
    """Seed sample audit data for testing"""
    print("\nSeeding sample data...")
    
    from backend.db.session import SessionLocal
    db = SessionLocal()
    
    try:
        # Sample audit logs
        sample_logs = [
            AuditLog(
                event_type=AuditEventType.CASE_CREATED,
                event_timestamp=datetime.utcnow(),
                severity=AuditSeverity.MEDIUM,
                user_id="analyst_001",
                user_email="analyst@bank.com",
                case_id="CASE-SAMPLE-001",
                case_number="2024-SAMPLE-001",
                case_status="new",
                environment_data={"sample": "environment"},
                browser_info="Chrome 120",
                os_info="Windows 10",
                device_type="desktop",
                tags=["sample", "test"],
                notes="Sample case creation for testing",
            ),
            AuditLog(
                event_type=AuditEventType.SAR_GENERATION_STARTED,
                event_timestamp=datetime.utcnow(),
                severity=AuditSeverity.CRITICAL,
                user_id="analyst_001",
                user_email="analyst@bank.com",
                case_id="CASE-SAMPLE-001",
                alert_ids=["ALERT-001", "ALERT-002"],
                alert_count=2,
                environment_data={"sample": "environment"},
                sar_request_data={"sample": "request"},
                compliance_flags={
                    "regulatory_body": "FinCEN",
                    "report_type": "SAR",
                },
                tags=["sample", "sar", "test"],
                notes="Sample SAR generation for testing",
            ),
            AuditLog(
                event_type=AuditEventType.SAR_REPORT_SUBMITTED,
                event_timestamp=datetime.utcnow(),
                severity=AuditSeverity.CRITICAL,
                user_id="supervisor_001",
                user_email="supervisor@bank.com",
                case_id="CASE-SAMPLE-001",
                sar_filing_number="SAR-2024-SAMPLE-001",
                environment_data={"sample": "environment"},
                sar_report_metadata={
                    "submission_date": datetime.utcnow().isoformat(),
                    "regulatory_body": "FinCEN",
                },
                compliance_flags={
                    "submitted": True,
                    "filing_complete": True,
                },
                retention_category="regulatory_filing",
                tags=["sample", "sar", "submitted", "test"],
                notes="Sample SAR submission for testing",
            ),
        ]
        
        for log in sample_logs:
            db.add(log)
        
        db.commit()
        print(f"✓ Seeded {len(sample_logs)} sample audit logs")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error seeding data: {e}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Setup Audit Trail Database"
    )
    parser.add_argument(
        '--drop',
        action='store_true',
        help='Drop existing tables before creating (WARNING: destructive)'
    )
    parser.add_argument(
        '--seed',
        action='store_true',
        help='Seed sample data for testing'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing tables'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Audit Trail System - Database Setup")
    print("=" * 60)
    
    if args.verify_only:
        verify_tables()
        return
    
    if args.drop:
        if not drop_tables():
            sys.exit(1)
    
    if not create_tables():
        sys.exit(1)
    
    if not verify_tables():
        sys.exit(1)
    
    if args.seed:
        if not seed_sample_data():
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Database setup completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
