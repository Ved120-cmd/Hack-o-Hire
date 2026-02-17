"""
SAR Final Filing Model

Stores the final regulatory-ready SAR bundle after Omega validation.
"""
from sqlalchemy import Column, String, Text, JSONB, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from backend.db.base import Base


class SARFinalFiling(Base):
    """
    Final SAR Filing Bundle
    
    Stores the complete, validated SAR bundle ready for regulatory submission.
    """
    __tablename__ = "sar_final_filings"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Case Information
    case_id = Column(String(100), nullable=False, index=True, comment="Case identifier")
    claim_id = Column(String(100), index=True, comment="Claim identifier")
    alert_ids = Column(JSONB, comment="Associated alert IDs")
    
    # Filing Information
    filing_number = Column(String(100), unique=True, index=True, comment="Official SAR filing number")
    jurisdiction = Column(JSONB, comment="Applicable jurisdictions")
    
    # SAR Bundle (Complete)
    claim_object = Column(JSONB, nullable=False, comment="Complete ClaimObject")
    narrative = Column(Text, nullable=False, comment="SAR narrative from Theta/RAG stage")
    
    # Regulatory Validation
    regulatory_ready = Column(Boolean, nullable=False, default=False, comment="Passed 10-point validation")
    validation_results = Column(JSONB, comment="10-point validation check results")
    validation_timestamp = Column(DateTime, comment="When validation was performed")
    
    # Validation Details
    validation_checks = Column(
        JSONB,
        comment="Detailed results of each of the 10 validation checks"
    )
    validation_errors = Column(
        JSONB,
        comment="Any validation errors or warnings"
    )
    
    # Metadata
    created_by = Column(String(100), comment="User who created the filing")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Status
    status = Column(String(50), default="pending", comment="Filing status")
    submitted_at = Column(DateTime, comment="When filing was submitted to regulator")
    
    # Indexes
    __table_args__ = (
        Index('idx_case_id', case_id),
        Index('idx_filing_number', filing_number),
        Index('idx_regulatory_ready', regulatory_ready),
        Index('idx_status', status),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "case_id": self.case_id,
            "claim_id": self.claim_id,
            "filing_number": self.filing_number,
            "regulatory_ready": self.regulatory_ready,
            "validation_results": self.validation_results,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
