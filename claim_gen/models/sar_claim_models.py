"""
Claim Database Models - SQLAlchemy ORM
Integrates with existing audit-trail-system backend pattern
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Integer, Float, JSON, Text, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func

from backend.db.base import Base


class ClaimDB(Base):
    """
    Main claims table storing complete claim objects.
    
    Stores all 12 sections of the claim object as JSONB for flexibility,
    with key fields extracted for indexing and querying.
    """
    __tablename__ = "claims"

    # Primary identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String(36), unique=True, nullable=False, index=True)
    case_id = Column(String(50), nullable=False, index=True)
    alert_ids = Column(JSONB, nullable=False)

    # Metadata
    version = Column(String(10), nullable=False, default="1.0")
    timestamp_created = Column(DateTime, nullable=False, default=func.now())
    timestamp_last_updated = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    stage = Column(String(50), nullable=False, default="claim_generation")
    status = Column(String(50), nullable=False, default="draft", index=True)
    environment = Column(String(50), nullable=False, index=True)
    jurisdiction = Column(JSONB, nullable=False)
    user_id = Column(String(50), nullable=False)
    data_lineage_hash = Column(String(64), nullable=False)

    # Complete claim object (all 12 sections stored as JSONB)
    claim_data = Column(JSONB, nullable=False)

    # Extracted fields for efficient querying (denormalized from claim_data)
    risk_score = Column(Float, index=True)  # From risk_assessment.overall_risk_score
    severity_band = Column(String(20), index=True)  # From risk_assessment.severity_band
    typologies = Column(ARRAY(String), index=True)  # From risk_assessment.typologies

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Indexes for common query patterns
    __table_args__ = (
        Index('idx_claims_case_status', 'case_id', 'status'),
        Index('idx_claims_created_env', 'timestamp_created', 'environment'),
        Index('idx_claims_risk_severity', 'risk_score', 'severity_band'),
    )

    def __repr__(self):
        return f"<ClaimDB(claim_id={self.claim_id}, case_id={self.case_id}, status={self.status})>"


class ClaimAuditLog(Base):
    """
    Audit log for claim modifications.
    
    Tracks all changes to claims for regulatory compliance and transparency.
    Separate from main AuditLog table to keep claim-specific audit trail.
    """
    __tablename__ = "claim_audit_log"

    # Primary key
    audit_id = Column(Integer, primary_key=True, autoincrement=True)

    # References
    claim_id = Column(String(36), ForeignKey('claims.claim_id', ondelete='CASCADE'), 
                      nullable=False, index=True)

    # Audit details
    action = Column(String(50), nullable=False, index=True)  # CREATED, UPDATED, STATUS_CHANGED, etc.
    actor_id = Column(String(50), nullable=False)  # User who made the change
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)

    # Change details
    changes = Column(JSONB)  # What changed
    reason = Column(Text)  # Why it changed

    # Indexes
    __table_args__ = (
        Index('idx_audit_claim_timestamp', 'claim_id', 'timestamp'),
    )

    def __repr__(self):
        return f"<ClaimAuditLog(claim_id={self.claim_id}, action={self.action}, actor={self.actor_id})>"


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_claim_tables(engine):
    """
    Initialize claim tables in database.
    
    Usage:
        from backend.db.session import engine
        from backend.claim_gen.models.claim_models import init_claim_tables
        
        init_claim_tables(engine)
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(bind=engine, tables=[
        ClaimDB.__table__,
        ClaimAuditLog.__table__
    ])
    print("✅ Claim tables created successfully")