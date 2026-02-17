"""
Audit Service - Integrated with Existing AuditLog Model

This service provides convenience methods for logging rule evaluations, claims,
and evidence in the SAR fraud detection system using your existing AuditLog model.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import uuid as uuid_module

from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity


class AuditService:
    """
    Audit service for SAR fraud detection system.
    Wraps existing AuditLog model with convenience methods for fraud detection workflows.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def _map_event_type(self, event_name: str) -> str:
        """Map custom event names to AuditEventType or return as-is"""
        event_map = {
            "case_created": "CASE_CREATED",
            "rule_evaluated": "CASE_UPDATED",  # Map to CASE_UPDATED
            "claim_generated": "SAR_REASONING_GENERATED",
            "evidence_collected": "CASE_UPDATED",
        }
        return event_map.get(event_name, "CASE_UPDATED")
    
    def _map_severity(self, severity_str: str) -> AuditSeverity:
        """Map severity string to AuditSeverity enum"""
        severity_map = {
            "low": AuditSeverity.LOW,
            "medium": AuditSeverity.MEDIUM,
            "high": AuditSeverity.HIGH,
            "critical": AuditSeverity.CRITICAL
        }
        return severity_map.get(severity_str.lower(), AuditSeverity.MEDIUM)
    
    def log_action(
        self,
        action: str,
        component: str,
        user: str = "system",
        case_id: Optional[int] = None,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        rule_ids: Optional[List[str]] = None,
        evidence_ids: Optional[List[str]] = None,
        claim_ids: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        environment: str = "on-prem",
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> AuditLog:
        """
        Generic action logging using existing AuditLog model.
        
        Args:
            action: Action performed (e.g., 'rule_evaluated', 'claim_generated')
            component: Component that performed action (e.g., 'rule_engine')
            user: User ID who triggered the action
            case_id: Associated case ID
            description: Human-readable description
            details: Detailed information about the action
            rule_ids: List of rule IDs involved
            evidence_ids: List of evidence IDs involved
            claim_ids: List of claim IDs involved
            input_data: Input data to the operation
            output_data: Output data from the operation
            status: Status of the operation (success, failure, warning)
            error_message: Error message if status is failure
            duration_ms: Duration of the operation in milliseconds
            environment: Execution environment
            metadata: Additional metadata
            session_id: Session identifier
            user_email: User email address
        
        Returns:
            Created AuditLog entry
        """
        # Map action to event type
        event_type_str = self._map_event_type(action)
        try:
            event_type = AuditEventType[event_type_str]
        except KeyError:
            event_type = AuditEventType.CASE_UPDATED  # Default fallback
        
        # Determine severity based on status and action
        if status == "failure":
            severity = AuditSeverity.HIGH
        elif action in ["claim_generated", "sar_report_generated"]:
            severity = AuditSeverity.CRITICAL
        else:
            severity = AuditSeverity.MEDIUM
        
        # Build comprehensive metadata
        comprehensive_metadata = {
            "action": action,
            "component": component,
            "status": status,
            "environment": environment,
            "rule_ids": rule_ids or [],
            "evidence_ids": evidence_ids or [],
            "claim_ids": claim_ids or [],
            **(metadata or {})
        }
        
        # Create audit log entry
        audit_log = AuditLog(
            id=uuid_module.uuid4(),
            event_type=event_type,
            event_timestamp=datetime.utcnow(),
            severity=severity,
            user_id=user,
            user_email=user_email,
            user_role=None,  # Can be populated if available
            session_id=session_id,
            case_id=str(case_id) if case_id else None,
            notes=description,
            environment_data={
                "environment_type": environment,
                "component": component,
                "input_data": input_data,
                "output_data": output_data
            },
            sar_request_data=input_data if action in ["claim_generated", "sar_generation_started"] else None,
            sar_reasoning_metadata=comprehensive_metadata if action == "claim_generated" else None,
            processing_duration_ms=duration_ms,
            error_occurred=(status == "failure"),
            error_message=error_message,
            tags=comprehensive_metadata,
            compliance_flags={
                "component": component,
                "action": action,
                "rules_triggered": len(rule_ids) if rule_ids else 0,
                "evidence_collected": len(evidence_ids) if evidence_ids else 0,
                "claims_generated": len(claim_ids) if claim_ids else 0
            }
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
    
    def log_rule_evaluation(
        self,
        rule_id: str,
        rule_name: str,
        case_id: Optional[int],
        triggered: bool,
        confidence_score: float,
        matched_conditions: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: int,
        user: str = "system",
        session_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log a rule evaluation event.
        
        Maps to existing AuditLog with event_type=CASE_UPDATED
        """
        return self.log_action(
            action="rule_evaluated",
            component="rule_engine",
            user=user,
            case_id=case_id,
            description=f"Rule '{rule_name}' evaluated - {'Triggered' if triggered else 'Not triggered'}",
            details={
                "rule_id": rule_id,
                "rule_name": rule_name,
                "triggered": triggered,
                "confidence_score": confidence_score,
                "matched_conditions": matched_conditions,
                "total_conditions": len(matched_conditions)
            },
            rule_ids=[rule_id],
            input_data=input_data,
            output_data=output_data,
            status="success",
            duration_ms=duration_ms,
            session_id=session_id,
            meta_data={
                "rule_evaluation": {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "triggered": triggered,
                    "confidence_score": confidence_score
                }
            }
        )
    
    def log_claim_generation(
        self,
        claim_id: str,
        case_id: int,
        typology: str,
        statement: str,
        confidence_score: float,
        risk_score: float,
        supporting_rule_ids: List[str],
        supporting_evidence_ids: List[str],
        user: str = "system",
        session_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log a claim generation event.
        
        Maps to existing AuditLog with event_type=SAR_REASONING_GENERATED
        Uses sar_reasoning field to store the claim statement
        """
        return self.log_action(
            action="claim_generated",
            component="claim_generator",
            user=user,
            case_id=case_id,
            description=f"Claim generated for typology: {typology}",
            details={
                "claim_id": claim_id,
                "typology": typology,
                "statement": statement,
                "confidence_score": confidence_score,
                "risk_score": risk_score,
                "supporting_rules_count": len(supporting_rule_ids),
                "supporting_evidence_count": len(supporting_evidence_ids)
            },
            rule_ids=supporting_rule_ids,
            evidence_ids=supporting_evidence_ids,
            claim_ids=[claim_id],
            output_data={
                "claim_id": claim_id,
                "typology": typology,
                "confidence_score": confidence_score,
                "risk_score": risk_score
            },
            status="success",
            session_id=session_id,
            meta_data={
                "claim_generation": {
                    "claim_id": claim_id,
                    "typology": typology,
                    "confidence_score": confidence_score,
                    "risk_score": risk_score
                }
            }
        )
    
    def log_evidence_collection(
        self,
        evidence_id: str,
        case_id: int,
        evidence_type: str,
        source_system: str,
        quality_score: float,
        transaction_ids: List[str],
        rule_ids: List[str],
        user: str = "system",
        session_id: Optional[str] = None
    ) -> AuditLog:
        """
        Log an evidence collection event.
        
        Maps to existing AuditLog with event_type=CASE_UPDATED
        """
        return self.log_action(
            action="evidence_collected",
            component="evidence_collector",
            user=user,
            case_id=case_id,
            description=f"Evidence collected: {evidence_type}",
            details={
                "evidence_id": evidence_id,
                "evidence_type": evidence_type,
                "source_system": source_system,
                "quality_score": quality_score,
                "transaction_count": len(transaction_ids),
                "related_rules_count": len(rule_ids)
            },
            rule_ids=rule_ids,
            evidence_ids=[evidence_id],
            output_data={
                "evidence_id": evidence_id,
                "evidence_type": evidence_type,
                "quality_score": quality_score
            },
            status="success",
            session_id=session_id,
            meta_data={
                "evidence_collection": {
                    "evidence_id": evidence_id,
                    "evidence_type": evidence_type,
                    "quality_score": quality_score,
                    "source_system": source_system
                }
            }
        )
    
    def get_audit_trail(
        self,
        case_id: Optional[int] = None,
        action: Optional[str] = None,
        component: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Retrieve audit trail with filters.
        
        Uses existing AuditLog model and indexes for efficient querying.
        """
        query = self.db.query(AuditLog)
        
        if case_id:
            query = query.filter(AuditLog.case_id == str(case_id))
        
        if start_date:
            query = query.filter(AuditLog.event_timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.event_timestamp <= end_date)
        
        # Filter by component in tags
        if component:
            query = query.filter(AuditLog.tags['component'].astext == component)
        
        # Filter by action in tags
        if action:
            query = query.filter(AuditLog.tags['action'].astext == action)
        
        return query.order_by(AuditLog.event_timestamp.desc()).limit(limit).all()
    
    def get_reasoning_chain(self, case_id: int) -> List[Dict[str, Any]]:
        """
        Get the complete reasoning chain for a case.
        Shows how rules -> evidence -> claims are connected.
        
        Builds reasoning chain from existing audit logs.
        """
        audit_logs = self.get_audit_trail(case_id=case_id, limit=1000)
        
        reasoning_chain = []
        for log in audit_logs:
            # Extract action from tags
            action = log.tags.get('action') if log.tags else 'unknown'
            component = log.tags.get('component') if log.tags else 'unknown'
            
            reasoning_chain.append({
                "timestamp": log.event_timestamp.isoformat(),
                "action": action,
                "component": component,
                "description": log.notes,
                "details": log.tags if log.tags else {},
                "rule_ids": log.tags.get('rule_ids', []) if log.tags else [],
                "evidence_ids": log.tags.get('evidence_ids', []) if log.tags else [],
                "claim_ids": log.tags.get('claim_ids', []) if log.tags else [],
                "status": log.tags.get('status', 'unknown') if log.tags else 'unknown',
                "severity": log.severity.value if log.severity else None
            })
        
        return reasoning_chain
    
    def get_rule_execution_history(self, rule_id: str, limit: int = 50) -> List[AuditLog]:
        """
        Get execution history for a specific rule.
        
        Queries audit logs where rule_id is in tags.rule_ids
        """
        return self.db.query(AuditLog).filter(
            AuditLog.tags['action'].astext == 'rule_evaluated',
            AuditLog.tags['rule_ids'].contains([rule_id])
        ).order_by(AuditLog.event_timestamp.desc()).limit(limit).all()
    
    def get_statistics(self, case_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get audit statistics for monitoring.
        """
        query = self.db.query(AuditLog)
        if case_id:
            query = query.filter(AuditLog.case_id == str(case_id))
        
        total_logs = query.count()
        
        # Count by action using tags
        action_counts = {}
        for action in ["rule_evaluated", "claim_generated", "evidence_collected"]:
            action_counts[action] = query.filter(
                AuditLog.tags['action'].astext == action
            ).count()
        
        # Count by status
        status_counts = {}
        for status in ["success", "failure", "warning"]:
            status_counts[status] = query.filter(
                AuditLog.tags['status'].astext == status
            ).count()
        
        return {
            "total_logs": total_logs,
            "action_counts": action_counts,
            "status_counts": status_counts
        }