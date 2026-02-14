"""
Audit Trail API Endpoints

Provides REST API for querying and analyzing audit trail data.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from pydantic import BaseModel, Field

from backend.db.session import get_db
from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity
from backend.services.audit.case_audit import CaseAuditService
from backend.services.audit.sar_audit import SARAuditService


router = APIRouter(prefix="/audit", tags=["audit"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AuditLogResponse(BaseModel):
    """Response model for audit log entry"""
    id: str
    event_type: str
    event_timestamp: datetime
    severity: str
    user_id: str
    user_email: Optional[str]
    case_id: Optional[str]
    case_number: Optional[str]
    alert_ids: Optional[List[str]]
    alert_count: Optional[int]
    sar_filing_number: Optional[str]
    processing_duration_ms: Optional[int]
    error_occurred: bool
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class AuditLogDetailResponse(AuditLogResponse):
    """Detailed response with full data"""
    user_role: Optional[str]
    user_ip_address: Optional[str]
    session_id: Optional[str]
    case_status: Optional[str]
    browser_info: Optional[str]
    os_info: Optional[str]
    device_type: Optional[str]
    environment_data: Optional[dict]
    sar_reasoning: Optional[str]
    sar_report_content: Optional[str]
    changes_made: Optional[dict]
    reason_for_change: Optional[str]
    tags: Optional[List[str]]
    notes: Optional[str]
    created_at: datetime


class AuditQueryParams(BaseModel):
    """Parameters for querying audit logs"""
    case_id: Optional[str] = None
    user_id: Optional[str] = None
    event_types: Optional[List[str]] = None
    severity: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_term: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class AuditStatsResponse(BaseModel):
    """Audit statistics response"""
    total_events: int
    events_by_type: dict
    events_by_severity: dict
    cases_audited: int
    sars_generated: int
    sars_submitted: int
    errors_count: int
    date_range: dict


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/logs", response_model=List[AuditLogResponse])
async def query_audit_logs(
    case_id: Optional[str] = None,
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Query audit logs with filters
    
    - **case_id**: Filter by case ID
    - **user_id**: Filter by user ID
    - **event_type**: Filter by event type
    - **severity**: Filter by severity level
    - **start_date**: Filter events after this date
    - **end_date**: Filter events before this date
    - **page**: Page number (1-indexed)
    - **page_size**: Results per page (max 1000)
    """
    query = db.query(AuditLog)
    
    # Apply filters
    filters = []
    if case_id:
        filters.append(AuditLog.case_id == case_id)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if event_type:
        filters.append(AuditLog.event_type == event_type)
    if severity:
        filters.append(AuditLog.severity == severity)
    if start_date:
        filters.append(AuditLog.event_timestamp >= start_date)
    if end_date:
        filters.append(AuditLog.event_timestamp <= end_date)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Pagination
    offset = (page - 1) * page_size
    
    results = (
        query
        .order_by(desc(AuditLog.event_timestamp))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    return results


@router.get("/logs/{audit_id}", response_model=AuditLogDetailResponse)
async def get_audit_log_detail(
    audit_id: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information for a specific audit log entry
    
    - **audit_id**: UUID of the audit log entry
    """
    audit_log = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return audit_log


@router.get("/case/{case_id}/history", response_model=List[AuditLogResponse])
async def get_case_audit_history(
    case_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get complete audit history for a specific case
    
    - **case_id**: Case identifier
    - **limit**: Maximum number of records (max 1000)
    """
    case_service = CaseAuditService(db)
    history = case_service.get_case_audit_history(case_id, limit)
    return history


@router.get("/case/{case_id}/sar-trail", response_model=List[AuditLogDetailResponse])
async def get_sar_audit_trail(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Get complete SAR generation audit trail for a case
    
    Returns all SAR-related events in chronological order.
    
    - **case_id**: Case identifier
    """
    sar_service = SARAuditService(db)
    trail = sar_service.get_sar_audit_trail(case_id)
    return trail


@router.get("/sar/filing/{filing_number}", response_model=AuditLogDetailResponse)
async def get_sar_by_filing_number(
    filing_number: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve SAR audit entry by official filing number
    
    - **filing_number**: Official SAR filing number from FinCEN
    """
    sar_service = SARAuditService(db)
    sar_entry = sar_service.get_sar_by_filing_number(filing_number)
    
    if not sar_entry:
        raise HTTPException(
            status_code=404,
            detail=f"SAR filing not found: {filing_number}"
        )
    
    return sar_entry


@router.get("/user/{user_id}/activity", response_model=List[AuditLogResponse])
async def get_user_activity(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    event_types: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get user activity audit trail
    
    - **user_id**: User identifier
    - **days**: Number of days to look back (max 365)
    - **event_types**: Optional list of event types to filter
    - **page**: Page number
    - **page_size**: Results per page
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(AuditLog).filter(
        AuditLog.user_id == user_id,
        AuditLog.event_timestamp >= start_date,
    )
    
    if event_types:
        query = query.filter(AuditLog.event_type.in_(event_types))
    
    offset = (page - 1) * page_size
    
    results = (
        query
        .order_by(desc(AuditLog.event_timestamp))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    return results


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Get audit trail statistics
    
    - **start_date**: Start of date range (defaults to 30 days ago)
    - **end_date**: End of date range (defaults to now)
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Base query
    base_query = db.query(AuditLog).filter(
        AuditLog.event_timestamp >= start_date,
        AuditLog.event_timestamp <= end_date,
    )
    
    # Total events
    total_events = base_query.count()
    
    # Events by type
    events_by_type = {}
    for event_type in AuditEventType:
        count = base_query.filter(AuditLog.event_type == event_type).count()
        if count > 0:
            events_by_type[event_type.value] = count
    
    # Events by severity
    events_by_severity = {}
    for severity in AuditSeverity:
        count = base_query.filter(AuditLog.severity == severity).count()
        if count > 0:
            events_by_severity[severity.value] = count
    
    # Unique cases
    cases_audited = (
        base_query
        .filter(AuditLog.case_id.isnot(None))
        .distinct(AuditLog.case_id)
        .count()
    )
    
    # SAR statistics
    sars_generated = base_query.filter(
        AuditLog.event_type == AuditEventType.SAR_REPORT_GENERATED
    ).count()
    
    sars_submitted = base_query.filter(
        AuditLog.event_type == AuditEventType.SAR_REPORT_SUBMITTED
    ).count()
    
    # Errors
    errors_count = base_query.filter(AuditLog.error_occurred == True).count()
    
    return AuditStatsResponse(
        total_events=total_events,
        events_by_type=events_by_type,
        events_by_severity=events_by_severity,
        cases_audited=cases_audited,
        sars_generated=sars_generated,
        sars_submitted=sars_submitted,
        errors_count=errors_count,
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        }
    )


@router.get("/search")
async def search_audit_logs(
    q: str = Query(..., min_length=3),
    search_fields: List[str] = Query(
        default=["notes", "error_message", "reason_for_change"]
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Full-text search across audit logs
    
    - **q**: Search query (minimum 3 characters)
    - **search_fields**: Fields to search in
    - **page**: Page number
    - **page_size**: Results per page
    """
    # This is a simple implementation. For production, consider using
    # PostgreSQL full-text search or Elasticsearch
    
    search_term = f"%{q}%"
    filters = []
    
    if "notes" in search_fields:
        filters.append(AuditLog.notes.ilike(search_term))
    if "error_message" in search_fields:
        filters.append(AuditLog.error_message.ilike(search_term))
    if "reason_for_change" in search_fields:
        filters.append(AuditLog.reason_for_change.ilike(search_term))
    
    query = db.query(AuditLog)
    if filters:
        query = query.filter(or_(*filters))
    
    offset = (page - 1) * page_size
    
    results = (
        query
        .order_by(desc(AuditLog.event_timestamp))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    return {
        "query": q,
        "total_results": query.count(),
        "page": page,
        "page_size": page_size,
        "results": [log.to_dict() for log in results],
    }


@router.get("/compliance/report")
async def generate_compliance_report(
    start_date: datetime,
    end_date: datetime,
    case_ids: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Generate compliance report for regulatory purposes
    
    - **start_date**: Report start date
    - **end_date**: Report end date
    - **case_ids**: Optional list of specific cases to include
    """
    query = db.query(AuditLog).filter(
        AuditLog.event_timestamp >= start_date,
        AuditLog.event_timestamp <= end_date,
    )
    
    if case_ids:
        query = query.filter(AuditLog.case_id.in_(case_ids))
    
    # SAR activities
    sar_activities = query.filter(
        AuditLog.event_type.in_([
            AuditEventType.SAR_GENERATION_STARTED,
            AuditEventType.SAR_REASONING_GENERATED,
            AuditEventType.SAR_REPORT_GENERATED,
            AuditEventType.SAR_REPORT_REVIEWED,
            AuditEventType.SAR_REPORT_SUBMITTED,
        ])
    ).all()
    
    # Critical events
    critical_events = query.filter(
        AuditLog.severity == AuditSeverity.CRITICAL
    ).all()
    
    # Errors
    errors = query.filter(AuditLog.error_occurred == True).all()
    
    return {
        "report_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "summary": {
            "total_sar_activities": len(sar_activities),
            "critical_events": len(critical_events),
            "errors": len(errors),
            "cases_processed": query.filter(
                AuditLog.case_id.isnot(None)
            ).distinct(AuditLog.case_id).count(),
        },
        "sar_activities": [log.to_dict() for log in sar_activities],
        "critical_events": [log.to_dict() for log in critical_events],
        "errors": [log.to_dict() for log in errors],
    }
