"""
Initialize Database Tables

Creates all database tables based on SQLAlchemy models.
Run this once to set up the database schema.

Usage:
    python backend/db/init_db.py

Prerequisites:
    - PostgreSQL database running (via Docker Compose or standalone)
    - DATABASE_URL environment variable set or configured in config.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db.base import Base
from backend.db.session import engine
# Import models to register them with Base.metadata
from backend.models.audit_log import AuditLog
from backend.models.sar_final_filing import SARFinalFiling

def init_db():
    """Create all database tables"""
    print("Initializing database tables...")
    print(f"Database URL: {engine.url}")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables created successfully!")
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Error creating tables: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running: docker-compose up -d")
        print("2. Check DATABASE_URL environment variable")
        print("3. Verify database credentials")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
