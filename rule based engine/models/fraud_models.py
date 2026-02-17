"""
Fraud Detection Database Models - FIXED VERSION

Fixed: Renamed 'metadata' columns to 'meta_data' to avoid SQLAlchemy reserved name conflict
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

# Assuming you have a Base class in backend.db.base
try:
    from backend.db.base import Base
except ImportError:
    Base = declarative_base()


# ==================== CORE ENTITIES ====================

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200))
    account_number = Column(String(50))
    account_type = Column(String(50))
    date_opened = Column(DateTime)
    risk_rating = Column(String(20))
    kyc_status = Column(String(20))
    occupation = Column(String(100))
    country = Column(String(50))
    is_pep = Column(Boolean, default=False)
    is_high_risk = Column(Boolean, default=False)
    meta_data = Column(JSON)  # FIXED: renamed from metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="customer")
    alerts = relationship("Alert", back_populates="customer")


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(String(50))
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Party information
    sender_account = Column(String(100))
    receiver_account = Column(String(100))
    counterparty_name = Column(String(200))
    counterparty_country = Column(String(50))
    
    # Location & method
    location = Column(String(200))
    channel = Column(String(50))
    
    # Risk indicators
    is_international = Column(Boolean, default=False)
    is_high_risk_country = Column(Boolean, default=False)
    
    # Metadata
    description = Column(Text)
    meta_data = Column(JSON)  # FIXED: renamed from metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="transactions")


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Alert details
    alert_type = Column(String(100))
    severity = Column(String(20), nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Alert data
    description = Column(Text)
    transaction_ids = Column(JSON)
    alert_data = Column(JSON)
    
    # Status
    status = Column(String(50), default="new")
    assigned_to = Column(String(100))
    resolved_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="alerts")
    case = relationship("Case", back_populates="alert", uselist=False)


# ==================== CASE MANAGEMENT ====================

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True)
    case_id = Column(String(100), unique=True, nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    
    # Case details
    status = Column(String(50), default="open")
    priority = Column(String(20))
    
    # Investigation
    investigator = Column(String(100))
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    # SAR details
    sar_filed = Column(Boolean, default=False)
    sar_filed_at = Column(DateTime)
    sar_number = Column(String(100))
    
    # Summary
    summary = Column(Text)
    meta_data = Column(JSON)  # FIXED: renamed from metadata
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alert = relationship("Alert", back_populates="case")
    claims = relationship("Claim", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")


# ==================== CLAIMS & EVIDENCE ====================

class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True)
    claim_id = Column(String(100), unique=True, nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    
    # Claim details
    typology = Column(String(200), nullable=False)
    statement = Column(Text, nullable=False)
    
    # Confidence & risk
    confidence_score = Column(Float)
    risk_score = Column(Float)
    severity = Column(String(20))
    
    # Supporting info
    rules_triggered = Column(JSON)
    evidence_ids = Column(JSON)
    
    # Validation
    validated = Column(Boolean, default=False)
    validated_by = Column(String(100))
    validated_at = Column(DateTime)
    
    meta_data = Column(JSON)  # FIXED: renamed from metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="claims")


class Evidence(Base):
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True)
    evidence_id = Column(String(100), unique=True, nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    
    # Evidence details
    evidence_type = Column(String(100))
    description = Column(Text)
    
    # Source information
    source_system = Column(String(100))
    source_data = Column(JSON)
    
    # Quality & reliability
    quality_score = Column(Float)
    reliability = Column(String(50))
    
    # References
    transaction_ids = Column(JSON)
    rule_ids = Column(JSON)
    
    # Timeline
    evidence_date = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    meta_data = Column(JSON)  # FIXED: renamed from metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="evidence")


# ==================== RULE ENGINE ====================

class Rule(Base):
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Rule details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    typology = Column(String(200))
    
    # Rule logic
    rule_logic = Column(JSON, nullable=False)
    severity = Column(String(20))
    
    # Configuration
    enabled = Column(Boolean, default=True)
    threshold = Column(Float)
    lookback_days = Column(Integer)
    
    # Metadata
    version = Column(String(20))
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    meta_data = Column(JSON)  # FIXED: renamed from metadata


class RuleExecution(Base):
    __tablename__ = "rule_executions"
    
    id = Column(Integer, primary_key=True)
    execution_id = Column(String(100), unique=True, nullable=False, index=True)
    
    rule_id = Column(String(100), ForeignKey("rules.rule_id"), nullable=False)
    case_id = Column(String(100))
    alert_id = Column(String(100))
    
    # Execution details
    triggered = Column(Boolean, default=False)
    confidence_score = Column(Float)
    
    # Data
    input_data = Column(JSON)
    matched_conditions = Column(JSON)
    output_data = Column(JSON)
    
    # Timing
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    execution_time_ms = Column(Integer)
    
    meta_data = Column(JSON)  # FIXED: renamed from metadata