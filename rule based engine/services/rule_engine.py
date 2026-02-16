"""
Rule-Based Fraud Detection Engine
Evaluates transactions against configurable rules and logs all executions to audit trail
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import yaml
import uuid
import time

from backend.models.fraud_models import (
    Transaction, Customer, Alert, Case, Rule, RuleExecution
)
from backend.services.audit_service import AuditService


class RuleEngine:
    """
    Rule-based fraud detection engine with full audit integration.
    Evaluates transactions against defined rules and creates alerts.
    """
    
    def __init__(self, db_session: Session, audit_service: AuditService):
        self.db = db_session
        self.audit = audit_service
        self.rules: List[Dict[str, Any]] = []
        self.load_rules()
    
    def load_rules(self, rule_file: str = "rule_definitions.yaml"):
        """Load rule definitions from YAML file."""
        try:
            with open(rule_file, 'r') as f:
                config = yaml.safe_load(f)
                self.rules = config.get('rules', [])
            print(f"Loaded {len(self.rules)} rules")
        except Exception as e:
            print(f"Error loading rules: {e}")
            self.rules = []
    
    def evaluate_alert(
        self, 
        alert_id: str, 
        user: str = "system"
    ) -> Tuple[Case, List[str]]:
        """
        Evaluate all rules for a given alert.
        Creates a case and logs all rule evaluations to audit trail.
        
        Args:
            alert_id: The alert to evaluate
            user: User performing the evaluation
            
        Returns:
            Tuple of (Case, List of triggered rule IDs)
        """
        start_time = time.time()
        
        # Get alert
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        # Create case
        case = Case(
            case_id=f"CASE-{uuid.uuid4().hex[:12].upper()}",
            alert_id=alert.id,
            status="open",
            priority=alert.severity,
            investigator=user,
            opened_at=datetime.utcnow()
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        
        # Log case creation
        self.audit.log_action(
            action="case_created",
            component="rule_engine",
            user=user,
            case_id=case.id,
            description=f"Case created from alert {alert_id}",
            details={
                "alert_id": alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity
            },
            status="success"
        )
        
        # Get customer and transactions
        customer = alert.customer
        transaction_ids = alert.transaction_ids or []
        transactions = self.db.query(Transaction).filter(
            Transaction.transaction_id.in_(transaction_ids)
        ).all()
        
        # Prepare data for rule evaluation
        evaluation_data = {
            "customer": self._customer_to_dict(customer),
            "transactions": [self._transaction_to_dict(t) for t in transactions],
            "alert": {
                "alert_id": alert_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "triggered_at": alert.triggered_at.isoformat()
            }
        }
        
        # Evaluate each rule
        triggered_rules = []
        for rule_def in self.rules:
            if not rule_def.get('enabled', True):
                continue
            
            result = self._evaluate_rule(
                rule_def=rule_def,
                data=evaluation_data,
                case_id=case.id,
                user=user
            )
            
            if result['triggered']:
                triggered_rules.append(result['rule_id'])
        
        # Update case with summary
        case.summary = f"Evaluated {len(self.rules)} rules, {len(triggered_rules)} triggered"
        case.meta_data = {
            "total_rules_evaluated": len(self.rules),
            "rules_triggered": len(triggered_rules),
            "evaluation_time_ms": int((time.time() - start_time) * 1000)
        }
        self.db.commit()
        
        return case, triggered_rules
    
    def _evaluate_rule(
        self,
        rule_def: Dict[str, Any],
        data: Dict[str, Any],
        case_id: int,
        user: str
    ) -> Dict[str, Any]:
        """
        Evaluate a single rule against the data.
        Logs the evaluation to audit trail.
        """
        start_time = time.time()
        
        rule_id = rule_def['rule_id']
        rule_name = rule_def['name']
        conditions = rule_def['conditions']
        
        # Perform rule evaluation
        matched_conditions = []
        triggered = False
        confidence_score = 0.0
        
        try:
            # Extract relevant transactions based on rule
            relevant_txns = self._filter_transactions_for_rule(
                transactions=data['transactions'],
                conditions=conditions
            )
            
            # Check if conditions are met
            if self._check_conditions(
                conditions=conditions,
                transactions=relevant_txns,
                customer=data['customer']
            ):
                triggered = True
                matched_conditions = self._get_matched_conditions(
                    conditions, relevant_txns, data['customer']
                )
                confidence_score = self._calculate_confidence(
                    matched_conditions, rule_def
                )
        
        except Exception as e:
            print(f"Error evaluating rule {rule_id}: {e}")
            triggered = False
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Create rule execution record
        execution = RuleExecution(
            execution_id=f"EXEC-{uuid.uuid4().hex[:12].upper()}",
            rule_id=rule_id,
            case_id=f"CASE-{case_id}",
            triggered=triggered,
            confidence_score=confidence_score,
            input_data=data,
            matched_conditions=matched_conditions,
            output_data={
                "triggered": triggered,
                "confidence_score": confidence_score,
                "matched_count": len(matched_conditions)
            },
            executed_at=datetime.utcnow(),
            execution_time_ms=duration_ms
        )
        self.db.add(execution)
        self.db.commit()
        
        # Log to audit trail
        self.audit.log_rule_evaluation(
            rule_id=rule_id,
            rule_name=rule_name,
            case_id=case_id,
            triggered=triggered,
            confidence_score=confidence_score,
            matched_conditions=matched_conditions,
            input_data={
                "transaction_count": len(data['transactions']),
                "customer_id": data['customer']['customer_id']
            },
            output_data={
                "triggered": triggered,
                "confidence_score": confidence_score,
                "typology": rule_def.get('typology'),
                "severity": rule_def.get('severity')
            },
            duration_ms=duration_ms,
            user=user
        )
        
        return {
            "rule_id": rule_id,
            "triggered": triggered,
            "confidence_score": confidence_score,
            "matched_conditions": matched_conditions
        }
    
    def _filter_transactions_for_rule(
        self,
        transactions: List[Dict[str, Any]],
        conditions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter transactions relevant to the rule conditions."""
        filtered = transactions
        
        # Filter by transaction type
        if 'transaction_type' in conditions:
            txn_type = conditions['transaction_type']
            filtered = [t for t in filtered if t['transaction_type'] == txn_type]
        
        # Filter by transaction types (multiple)
        if 'transaction_types' in conditions:
            txn_types = conditions['transaction_types']
            filtered = [t for t in filtered if t['transaction_type'] in txn_types]
        
        # Filter by amount range
        if 'amount_range' in conditions:
            min_amt = conditions['amount_range'].get('min', 0)
            max_amt = conditions['amount_range'].get('max', float('inf'))
            filtered = [t for t in filtered if min_amt <= t['amount'] <= max_amt]
        
        # Filter by amount threshold
        if 'amount_threshold' in conditions:
            threshold = conditions['amount_threshold']
            filtered = [t for t in filtered if t['amount'] >= threshold]
        
        # Filter by time window
        if 'time_window_days' in conditions:
            days = conditions['time_window_days']
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = [t for t in filtered 
                       if datetime.fromisoformat(t['timestamp']) >= cutoff]
        
        if 'time_window_hours' in conditions:
            hours = conditions['time_window_hours']
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            filtered = [t for t in filtered 
                       if datetime.fromisoformat(t['timestamp']) >= cutoff]
        
        # Filter by international
        if 'is_international' in conditions:
            filtered = [t for t in filtered 
                       if t.get('is_international') == conditions['is_international']]
        
        # Filter by high risk country
        if 'is_high_risk_country' in conditions:
            filtered = [t for t in filtered 
                       if t.get('is_high_risk_country') == conditions['is_high_risk_country']]
        
        # Filter by channel
        if 'channel' in conditions:
            channel = conditions['channel']
            filtered = [t for t in filtered if t.get('channel') == channel]
        
        return filtered
    
    def _check_conditions(
        self,
        conditions: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        customer: Dict[str, Any]
    ) -> bool:
        """Check if rule conditions are satisfied."""
        
        # Check minimum transaction count
        if 'min_transaction_count' in conditions:
            min_count = conditions['min_transaction_count']
            if len(transactions) < min_count:
                return False
        
        # Check customer is PEP
        if 'customer_is_pep' in conditions:
            if customer.get('is_pep') != conditions['customer_is_pep']:
                return False
        
        # Check round amounts
        if conditions.get('round_amounts_only', False):
            if not all(t['amount'] % 1000 == 0 for t in transactions):
                return False
        
        # Check different locations (smurfing)
        if conditions.get('different_locations', False):
            locations = set(t.get('location') for t in transactions if t.get('location'))
            if len(locations) < 2:
                return False
        
        # Check same counterparty
        if conditions.get('same_counterparty', False):
            counterparties = set(t.get('counterparty_name') for t in transactions 
                               if t.get('counterparty_name'))
            if len(counterparties) != 1:
                return False
        
        return True
    
    def _get_matched_conditions(
        self,
        conditions: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        customer: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get list of conditions that were matched."""
        matched = []
        
        if 'min_transaction_count' in conditions:
            matched.append({
                "condition": "min_transaction_count",
                "expected": conditions['min_transaction_count'],
                "actual": len(transactions),
                "matched": True
            })
        
        if 'amount_range' in conditions:
            amounts = [t['amount'] for t in transactions]
            matched.append({
                "condition": "amount_range",
                "range": conditions['amount_range'],
                "actual_amounts": amounts,
                "matched": True
            })
        
        if 'time_window_days' in conditions:
            matched.append({
                "condition": "time_window_days",
                "window": conditions['time_window_days'],
                "transaction_count": len(transactions),
                "matched": True
            })
        
        if 'customer_is_pep' in conditions:
            matched.append({
                "condition": "customer_is_pep",
                "expected": conditions['customer_is_pep'],
                "actual": customer.get('is_pep'),
                "matched": True
            })
        
        return matched
    
    def _calculate_confidence(
        self,
        matched_conditions: List[Dict[str, Any]],
        rule_def: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on matched conditions."""
        if not matched_conditions:
            return 0.0
        
        # Base confidence from rule threshold
        base_confidence = rule_def.get('thresholds', {}).get('confidence_threshold', 0.7)
        
        # Adjust based on number of conditions matched
        total_conditions = len(rule_def.get('conditions', {}))
        matched_count = len(matched_conditions)
        
        if total_conditions > 0:
            match_ratio = matched_count / total_conditions
            confidence = base_confidence * match_ratio
        else:
            confidence = base_confidence
        
        return round(min(confidence, 1.0), 2)
    
    def _customer_to_dict(self, customer: Customer) -> Dict[str, Any]:
        """Convert Customer model to dictionary."""
        return {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "account_number": customer.account_number,
            "is_pep": customer.is_pep,
            "is_high_risk": customer.is_high_risk,
            "risk_rating": customer.risk_rating,
            "country": customer.country
        }
    
    def _transaction_to_dict(self, txn: Transaction) -> Dict[str, Any]:
        """Convert Transaction model to dictionary."""
        return {
            "transaction_id": txn.transaction_id,
            "transaction_type": txn.transaction_type,
            "amount": txn.amount,
            "currency": txn.currency,
            "timestamp": txn.timestamp.isoformat(),
            "is_international": txn.is_international,
            "is_high_risk_country": txn.is_high_risk_country,
            "location": txn.location,
            "channel": txn.channel,
            "counterparty_name": txn.counterparty_name,
            "counterparty_country": txn.counterparty_country
        }
    
    def get_triggered_rules_summary(self, case_id: int) -> List[Dict[str, Any]]:
        """Get summary of all triggered rules for a case."""
        executions = self.db.query(RuleExecution).filter(
            RuleExecution.case_id == f"CASE-{case_id}",
            RuleExecution.triggered == True
        ).all()
        
        summary = []
        for exec in executions:
            # Get rule definition
            rule_def = next((r for r in self.rules if r['rule_id'] == exec.rule_id), None)
            
            summary.append({
                "rule_id": exec.rule_id,
                "rule_name": rule_def['name'] if rule_def else "Unknown",
                "typology": rule_def['typology'] if rule_def else "Unknown",
                "confidence_score": exec.confidence_score,
                "matched_conditions": exec.matched_conditions,
                "executed_at": exec.executed_at.isoformat()
            })
        
        return summary