"""
Database Engine & Session Factory
==================================
SQLAlchemy session management with auto table creation.
Supports SQLite (default) and PostgreSQL.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from backend.core.config import settings

Base = declarative_base()

_url = settings.database_url
_is_sqlite = _url.startswith("sqlite")

# SQLite doesn't support pool_size / max_overflow
if _is_sqlite:
    engine = create_engine(
        _url,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False},  # required for SQLite + threads
    )
    # Enable WAL mode for better concurrency
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()
else:
    engine = create_engine(
        _url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency – yields a DB session and closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables from registered models (import models first)."""
    import backend.models  # noqa: F401 – registers models with Base
    Base.metadata.create_all(bind=engine)
