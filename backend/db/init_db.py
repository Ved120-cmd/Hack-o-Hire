"""
Initialize Database Tables - Production Ready

Creates all database tables based on SQLAlchemy models.
Run this once to set up the database schema.

Usage:
    python backend/db/init_db.py

Prerequisites:
    - PostgreSQL database running (Docker: docker compose up -d)
    - DATABASE_URL configured (via .env or environment variables)
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def init_db():
    """Create all database tables"""
    logger.info("=" * 80)
    logger.info("DATABASE INITIALIZATION")
    logger.info("=" * 80)
    
    try:
        # Import after path is set
        from backend.db.base import Base
        from backend.db.session import engine, DATABASE_URL
        
        # Import models to register them with Base.metadata
        logger.info("Importing database models...")
        from backend.models.audit_log import AuditLog
        from backend.models.sar_final_filing import SARFinalFiling
        
        logger.info(f"Database URL: {str(engine.url).replace(engine.url.password or '', '***')}")
        
        # Test connection first
        logger.info("Testing database connection...")
        engine.connect()
        logger.info("✅ Database connection successful")
        
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("=" * 80)
        logger.info("✅ DATABASE TABLES CREATED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            logger.info(f"  ✓ {table_name}")
        
        logger.info("\n" + "=" * 80)
        logger.info("NEXT STEPS:")
        logger.info("=" * 80)
        logger.info("1. Test connection: python backend/omega/test_db_connection.py")
        logger.info("2. Run integration test: python backend/omega/test_integration.py")
        logger.info("3. View storage structure: python backend/omega/show_storage.py")
        
        return True
        
    except ImportError as e:
        logger.error("=" * 80)
        logger.error("❌ IMPORT ERROR")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("1. Ensure you're running from project root directory")
        logger.error("2. Check that claim_gen package exists")
        logger.error("3. Verify Python path includes project root")
        logger.error(f"4. Current working directory: {Path.cwd()}")
        logger.error(f"5. Project root: {project_root}")
        return False
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ DATABASE INITIALIZATION FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("1. Ensure PostgreSQL is running:")
        logger.error("   docker compose ps")
        logger.error("   docker compose up -d  # If not running")
        logger.error("\n2. Check DATABASE_URL in .env file:")
        logger.error("   cat .env")
        logger.error("\n3. Verify database credentials:")
        logger.error("   docker compose exec postgres psql -U sar_user -d sar_audit -c 'SELECT 1'")
        logger.error("\n4. Check Docker logs:")
        logger.error("   docker compose logs postgres")
        
        import traceback
        logger.error("\nFull traceback:")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)