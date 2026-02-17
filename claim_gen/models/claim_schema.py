"""
Pydantic models for SAR Claim Object Schema Validation
Enterprise-grade data models with comprehensive validation
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class StatusEnum(str, Enum):
    """Claim status enumeration"""

    DRAFT = "draft"
    ANALYST_REVIEW = "analyst_review"
    APPROVED = "approved"
    FILED = "filed"
    REJECTED = "rejected"


class EnvironmentEnum(str, Enum):
    """Deployment environment enumeration"""

    ON_PREM = "on-prem"
    AWS = "aws"
    MULTI_CLOUD = "multi-cloud"


class SeverityBandEnum(str, Enum):
    """Risk severity band enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CustomerIdentifiers(BaseModel):
    """Customer identification details"""

    pan: str = Field(..., description="Permanent Account Number")
    account_nums: List[str] = Field(default_factory=list, description="Account numbers")


class KYCDetails(BaseModel):
    """KYC (Know Your Customer) details"""

    risk_rating: float = Field(..., ge=0, le=100, description="Risk rating score")
    risk_segment: str = Field(..., description="Risk segment classification")
    onboarding_date: datetime = Field(..., description="Customer onboarding date")
    pep_status: bool = Field(..., description="Politically Exposed Person status")
    sanctions_screen: str = Field(..., description="Sanctions screening status")
    adverse_media: List[str] = Field(
        default_factory=list, description="Adverse media findings"
    )


class Customer(BaseModel):
    """Customer information"""

    customer_id: str = Field(..., description="Unique customer identifier")
    identifiers: CustomerIdentifiers
    kyc: KYCDetails
    behavioral_segment: str = Field(..., description="Behavioral segment classification")


class Account(BaseModel):
    """Account information"""

    account_id: str = Field(..., description="Account identifier")
    type: str = Field(..., description="Account type")
    balance_at_alert: float = Field(..., description="Balance at alert time")
    opening_date: datetime = Field(..., description="Account opening date")


class Counterparties(BaseModel):
    """Counterparty information"""

    unique_count: int = Field(..., ge=0, description="Count of unique counterparties")
    high_risk_count: int = Field(..., ge=0, description="High risk counterparties count")
    geo_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Geographic distribution by country code"
    )
    repeat_counterparties: int = Field(
        ..., ge=0, description="Count of repeat counterparties"
    )


class Subject(BaseModel):
    """Subject of investigation"""

    customer: Customer
    accounts: List[Account] = Field(default_factory=list)
    counterparties: Counterparties


class PipelineTransform(BaseModel):
    """Pipeline transformation stage details"""

    stage: str = Field(..., description="Stage name")
    input: str = Field(..., description="Input description")
    output: str = Field(..., description="Output description")
    transform_rules_applied: List[str] = Field(
        default_factory=list, description="Applied transformation rules"
    )
    input_size_bytes: int = Field(..., ge=0, description="Input size in bytes")
    output_size_bytes: int = Field(..., ge=0, description="Output size in bytes")
    timestamp: datetime = Field(..., description="Transformation timestamp")
    hash: str = Field(..., min_length=64, max_length=64, description="SHA256 hash")


class ChronologyEvent(BaseModel):
    """Chronological event in pattern"""

    event: str = Field(..., description="Event description")
    period: str = Field(..., description="Time period")
    total: float = Field(..., description="Total amount or count")


class VelocityMetrics(BaseModel):
    """Transaction velocity metrics"""

    inflow_velocity: float = Field(..., description="Inflow velocity (amount/time)")
    outflow_velocity: float = Field(..., description="Outflow velocity (amount/time)")
    turnaround_time_hours: float = Field(
        ..., ge=0, description="Turnaround time in hours"
    )


class SuspiciousPattern(BaseModel):
    """Suspicious activity pattern"""

    summary: str = Field(..., description="Pattern summary")
    pattern_type: str = Field(..., description="Type of pattern detected")
    chronology: List[ChronologyEvent] = Field(
        default_factory=list, description="Chronological events"
    )
    velocity_metrics: VelocityMetrics


class Evidence(BaseModel):
    """Evidence item"""

    evidence_id: str = Field(..., description="Unique evidence identifier")
    primary_key: str = Field(..., description="Primary key reference")
    type: str = Field(..., description="Evidence type")
    timestamp: datetime = Field(..., description="Evidence timestamp")
    features_used: Dict[str, Any] = Field(
        default_factory=dict, description="Features used in analysis"
    )
    raw_value: Any = Field(..., description="Raw value")
    normalized_value: Any = Field(..., description="Normalized value")


class RuleMatch(BaseModel):
    """Rule matching details"""

    rule_id: str = Field(..., description="Rule identifier")
    name: str = Field(..., description="Rule name")
    thresholds: Dict[str, Any] = Field(
        default_factory=dict, description="Rule thresholds"
    )
    match_strength: float = Field(..., ge=0, le=1, description="Match strength score")
    fired_timestamp: datetime = Field(..., description="Rule firing timestamp")


class ModelScore(BaseModel):
    """Model scoring details"""

    model: str = Field(..., description="Model name")
    raw_score: float = Field(..., ge=0, le=1, description="Raw model score")
    shap_contributions: Dict[str, float] = Field(
        default_factory=dict, description="SHAP feature contributions"
    )


class DetectionLogic(BaseModel):
    """Detection logic details"""

    rules_matched: List[RuleMatch] = Field(default_factory=list)
    model_scores: List[ModelScore] = Field(default_factory=list)
    derived_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Derived metrics"
    )


class RiskAssessment(BaseModel):
    """Risk assessment details"""

    overall_risk_score: float = Field(..., ge=0, le=100, description="Overall risk score")
    typologies: List[str] = Field(
        default_factory=list, description="Identified typologies"
    )
    severity_band: SeverityBandEnum = Field(..., description="Severity band")
    confidence_level: float = Field(
        ..., ge=0, le=1, description="Confidence level in assessment"
    )
    predicate_offense: str = Field(..., description="Predicate offense classification")


class RegulatoryHook(BaseModel):
    """Regulatory document reference"""

    doc_id: str = Field(..., description="Document identifier")
    paragraph: str = Field(..., description="Paragraph reference")
    similarity_score: float = Field(
        ..., ge=0, le=1, description="Similarity score to regulation"
    )
    jurisdiction: str = Field(..., description="Jurisdiction")
    retrieval_timestamp: datetime = Field(..., description="Retrieval timestamp")


class TokenUsage(BaseModel):
    """LLM token usage"""

    input: int = Field(..., ge=0, description="Input tokens")
    output: int = Field(..., ge=0, description="Output tokens")


class RetrievalContext(BaseModel):
    """RAG retrieval context"""

    template_ids: List[str] = Field(default_factory=list, description="Template IDs used")
    top_k: int = Field(..., ge=1, description="Top-k retrieval parameter")
    avg_similarity: float = Field(
        ..., ge=0, le=1, description="Average similarity score"
    )


class GenerationTrace(BaseModel):
    """LLM generation trace for audit"""

    llm_prompt: str = Field(..., description="Full LLM prompt")
    intermediate_reasoning: List[str] = Field(
        default_factory=list, description="Intermediate reasoning steps"
    )
    token_usage: TokenUsage
    temperature: float = Field(..., ge=0, le=2, description="Temperature parameter")
    retrieval_context: RetrievalContext


class EditHistory(BaseModel):
    """Edit history entry"""

    version: str = Field(..., description="Version identifier")
    editor_id: str = Field(..., description="Editor user ID")
    timestamp: datetime = Field(..., description="Edit timestamp")
    diff: str = Field(..., description="Diff summary")
    reason: str = Field(..., description="Edit reason")


class Approval(BaseModel):
    """Approval entry"""

    approver_id: str = Field(..., description="Approver user ID")
    timestamp: datetime = Field(..., description="Approval timestamp")
    status: str = Field(..., description="Approval status")


class AuditTrail(BaseModel):
    """Audit trail information"""

    edits_history: List[EditHistory] = Field(default_factory=list)
    approvals: List[Approval] = Field(default_factory=list)


class BiasCheck(BaseModel):
    """Bias detection check"""

    unbiased: bool = Field(..., description="Unbiased flag")
    flags: List[str] = Field(default_factory=list, description="Bias flags if any")


class SecurityControls(BaseModel):
    """Security and privacy controls"""

    redaction_mask: List[str] = Field(
        default_factory=list, description="Redacted field names"
    )
    pii_detected: int = Field(..., ge=0, description="PII instances detected")
    pii_redacted: int = Field(..., ge=0, description="PII instances redacted")
    rbac_roles_access: List[str] = Field(
        default_factory=list, description="RBAC roles with access"
    )
    bias_check: BiasCheck


class IntegrityHashes(BaseModel):
    """Integrity verification hashes"""

    input_hash: str = Field(..., min_length=64, max_length=64, description="Input SHA256")
    output_hash: str = Field(
        ..., min_length=64, max_length=64, description="Output SHA256"
    )
    full_chain_hash: str = Field(
        ..., min_length=64, max_length=64, description="Full chain SHA256"
    )


class ModelVersion(BaseModel):
    """Model version information"""

    llm: str = Field(..., description="LLM model version")
    rules: str = Field(..., description="Rules engine version")


class ClaimObject(BaseModel):
    """Complete SAR Claim Object - Main Schema"""

    # ===== 1. CORE IDENTIFIERS & METADATA =====
    claim_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique claim ID")
    case_id: str = Field(..., description="Associated case ID")
    alert_ids: List[str] = Field(..., description="Associated alert IDs")
    version: str = Field(default="1.0", description="Claim schema version")
    timestamp_created: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    timestamp_last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    stage: str = Field(default="claim_generation", description="Current pipeline stage")
    status: StatusEnum = Field(default=StatusEnum.DRAFT, description="Claim status")
    environment: EnvironmentEnum = Field(..., description="Deployment environment")
    jurisdiction: List[str] = Field(..., description="Applicable jurisdictions")
    model_version: ModelVersion
    user_id: str = Field(..., description="User ID who created claim")
    data_lineage_hash: str = Field(
        ..., min_length=64, max_length=64, description="Data lineage SHA256 hash"
    )

    # ===== 2. SUBJECT & CONTEXT =====
    subject: Subject

    # ===== 3. PIPELINE TRACEABILITY =====
    pipeline_transforms: List[PipelineTransform] = Field(default_factory=list)

    # ===== 4. SUSPICIOUS PATTERN DESCRIPTION =====
    suspicious_patterns: List[SuspiciousPattern] = Field(default_factory=list)

    # ===== 5. NORMALIZED EVIDENCE SET =====
    evidence_set: List[Evidence] = Field(default_factory=list)

    # ===== 6. DETECTION LOGIC =====
    detection_logic: DetectionLogic

    # ===== 7. RISK ASSESSMENT =====
    risk_assessment: RiskAssessment

    # ===== 8. REGULATORY HOOKS =====
    regulatory_hooks: List[RegulatoryHook] = Field(default_factory=list)

    # ===== 9. LLM GENERATION TRACE =====
    generation_trace: GenerationTrace

    # ===== 10. AUDIT & APPROVAL =====
    audit_trail: AuditTrail = Field(default_factory=AuditTrail)

    # ===== 11. SECURITY & CONTROLS =====
    security_controls: SecurityControls

    # ===== 12. INTEGRITY & HASHES =====
    integrity_hashes: IntegrityHashes

    class Config:
        """Pydantic configuration"""

        json_encoders = {datetime: lambda v: v.isoformat()}
        use_enum_values = True

    @model_validator(mode="after")
    def validate_pii_redaction(self) -> "ClaimObject":
        """Ensure PII detected >= PII redacted"""
        if self.security_controls.pii_redacted > self.security_controls.pii_detected:
            raise ValueError("PII redacted cannot exceed PII detected")
        return self

    @model_validator(mode="after")
    def validate_timestamps(self) -> "ClaimObject":
        """Ensure timestamp consistency"""
        if self.timestamp_last_updated < self.timestamp_created:
            raise ValueError("Last updated timestamp cannot be before creation timestamp")
        return self