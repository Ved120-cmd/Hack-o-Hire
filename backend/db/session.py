"""
Database Session Management

Creates SQLAlchemy session factory using PostgreSQL connection.
Uses DATABASE_URL from config.py or environment variable.

TODO: Configure DATABASE_URL via:
  1. Environment variable: DATABASE_URL
  2. config.py settings (if exists)
  3. Docker Compose environment variables
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Try to import config, fallback to environment variable
try:
    from config import settings
    DATABASE_URL = str(settings.DATABASE_URL)
except ImportError:
    # Use environment variable or construct from Docker Compose env vars
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        # Construct from Docker Compose environment variables
        # TODO: Replace with actual environment variable names if different
        db_user = os.getenv("POSTGRES_USER", "user")
        db_password = os.getenv("POSTGRES_PASSWORD", "password")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "sar_audit")
        
        DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not configured. Set DATABASE_URL environment variable "
        "or configure via config.py or Docker Compose environment variables."
    )

# Create database engine
# TODO: Adjust pool settings based on production requirements
engine = create_engine(
    DATABASE_URL,
    echo=False,  # TODO: Set to True for SQL debugging in development
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # TODO: Adjust based on load
    max_overflow=20,  # TODO: Adjust based on load
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Usage:
        db = next(get_db())
        try:
            # use db
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
