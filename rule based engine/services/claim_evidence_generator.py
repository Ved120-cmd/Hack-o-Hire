"""
Claim and Evidence Generation Service
Generates structured claims and evidence from triggered rules with full audit trail
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import uuid

from backend.models.fraud_models import (
    Case, Claim, Evidence, Transaction, Customer, RuleExecution
)
from backend.services.audit_service import AuditService


class ClaimEvidenceGenerator:
    """
    Generates claims and evidence based on triggered rules.
    Each claim represents a suspicion of a specific typology.
    Each evidence item supports one or more claims.
    """
    
    def __init__(self, db_session: Session, audit_service: AuditService):
        self.db = db_session
        self.audit = audit_service
    
    def generate_claims_and_evidence(
        self,
        case_id: int,
        triggered_rules: List[Dict[str, Any]],
        user: str = "system"
    ) -> Tuple[List[Claim], List[Evidence]]:
        """
        Generate claims and supporting evidence from triggered rules.
        
        Args:
            case_id: The case ID
            triggered_rules: List of triggered rule summaries
            user: User generating claims
            
        Returns:
            Tuple of (List of Claims, List of Evidence)
        """
        # Get case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Group rules by typology
        typology_groups = self._group_rules_by_typology(triggered_rules)
        
        claims = []
        all_evidence = []
        
        # Generate claim for each typology
        for typology, rules in typology_groups.items():
            # Generate evidence for this typology
            evidence_list = self._generate_evidence_for_typology(
                case=case,
                typology=typology,
                rules=rules,
                user=user
            )
            all_evidence.extend(evidence_list)
            
            # Generate claim
            claim = self._generate_claim(
                case=case,
                typology=typology,
                rules=rules,
                evidence_list=evidence_list,
                user=user
            )
            claims.append(claim)
        
        return claims, all_evidence
    
    def _group_rules_by_typology(
        self,
        triggered_rules: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group triggered rules by their typology."""
        groups = {}
        for rule in triggered_rules:
            typology = rule.get('typology', 'Unknown')
            if typology not in groups:
                groups[typology] = []
            groups[typology].append(rule)
        return groups
    
    def _generate_evidence_for_typology(
        self,
        case: Case,
        typology: str,
        rules: List[Dict[str, Any]],
        user: str
    ) -> List[Evidence]:
        """
        Generate evidence items for a specific typology.
        Each piece of evidence represents observable facts supporting the typology.
        """
        evidence_list = []
        
        # Get alert and transactions
        alert = case.alert
        customer = alert.customer
        transaction_ids = alert.transaction_ids or []
        transactions = self.db.query(Transaction).filter(
            Transaction.transaction_id.in_(transaction_ids)
        ).all()
        
        # 1. Transaction Pattern Evidence
        if len(transactions) > 0:
            evidence = self._create_transaction_pattern_evidence(
                case=case,
                transactions=transactions,
                rules=rules,
                typology=typology,
                user=user
            )
            evidence_list.append(evidence)
        
        # 2. Customer Behavior Evidence
        customer_evidence = self._create_customer_behavior_evidence(
            case=case,
            customer=customer,
            rules=rules,
            typology=typology,
            user=user
        )
        evidence_list.append(customer_evidence)
        
        # 3. Rule Match Evidence
        for rule in rules:
            rule_evidence = self._create_rule_match_evidence(
                case=case,
                rule=rule,
                user=user
            )
            evidence_list.append(rule_evidence)
        
        return evidence_list
    
    def _create_transaction_pattern_evidence(
        self,
        case: Case,
        transactions: List[Transaction],
        rules: List[Dict[str, Any]],
        typology: str,
        user: str
    ) -> Evidence:
        """Create evidence from transaction patterns."""
        
        # Analyze transaction patterns
        total_amount = sum(t.amount for t in transactions)
        avg_amount = total_amount / len(transactions) if transactions else 0
        
        transaction_types = list(set(t.transaction_type for t in transactions))
        
        # Time span analysis
        timestamps = [t.timestamp for t in transactions]
        time_span_hours = (max(timestamps) - min(timestamps)).total_seconds() / 3600 if len(timestamps) > 1 else 0
        
        # Geographic analysis
        countries = list(set(t.counterparty_country for t in transactions if t.counterparty_country))
        is_multi_country = len(countries) > 1
        
        # Build evidence
        evidence_id = f"EVID-{uuid.uuid4().hex[:12].upper()}"
        
        source_data = {
            "transaction_count": len(transactions),
            "total_amount": total_amount,
            "average_amount": avg_amount,
            "transaction_types": transaction_types,
            "time_span_hours": time_span_hours,
            "countries_involved": countries,
            "is_multi_country": is_multi_country,
            "transaction_ids": [t.transaction_id for t in transactions]
        }
        
        description = self._generate_pattern_description(
            typology=typology,
            txn_count=len(transactions),
            total_amount=total_amount,
            time_span_hours=time_span_hours
        )
        
        # Calculate quality score based on data completeness
        quality_score = self._calculate_evidence_quality(transactions)
        
        evidence = Evidence(
            evidence_id=evidence_id,
            case_id=case.id,
            evidence_type="transaction_pattern",
            description=description,
            source_system="transaction_db",
            source_data=source_data,
            quality_score=quality_score,
            reliability="high",
            transaction_ids=[t.transaction_id for t in transactions],
            rule_ids=[r['rule_id'] for r in rules],
            evidence_date=max(timestamps) if timestamps else datetime.utcnow(),
            collected_at=datetime.utcnow(),
            meta_data={
                "typology": typology,
                "pattern_type": "temporal_clustering"
            }
        )
        
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        
        # Log to audit
        self.audit.log_evidence_collection(
            evidence_id=evidence_id,
            case_id=case.id,
            evidence_type="transaction_pattern",
            source_system="transaction_db",
            quality_score=quality_score,
            transaction_ids=[t.transaction_id for t in transactions],
            rule_ids=[r['rule_id'] for r in rules],
            user=user
        )
        
        return evidence
    
    def _create_customer_behavior_evidence(
        self,
        case: Case,
        customer: Customer,
        rules: List[Dict[str, Any]],
        typology: str,
        user: str
    ) -> Evidence:
        """Create evidence from customer profile and behavior."""
        
        evidence_id = f"EVID-{uuid.uuid4().hex[:12].upper()}"
        
        source_data = {
            "customer_id": customer.customer_id,
            "is_pep": customer.is_pep,
            "is_high_risk": customer.is_high_risk,
            "risk_rating": customer.risk_rating,
            "country": customer.country,
            "kyc_status": customer.kyc_status,
            "account_age_days": (datetime.utcnow() - customer.date_opened).days if customer.date_opened else None
        }
        
        description = self._generate_customer_description(customer, typology)
        
        quality_score = 0.9 if customer.kyc_status == "completed" else 0.7
        
        evidence = Evidence(
            evidence_id=evidence_id,
            case_id=case.id,
            evidence_type="customer_behavior",
            description=description,
            source_system="customer_db",
            source_data=source_data,
            quality_score=quality_score,
            reliability="high",
            transaction_ids=[],
            rule_ids=[r['rule_id'] for r in rules],
            evidence_date=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            meta_data={
                "typology": typology,
                "customer_flags": {
                    "is_pep": customer.is_pep,
                    "is_high_risk": customer.is_high_risk
                }
            }
        )
        
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        
        # Log to audit
        self.audit.log_evidence_collection(
            evidence_id=evidence_id,
            case_id=case.id,
            evidence_type="customer_behavior",
            source_system="customer_db",
            quality_score=quality_score,
            transaction_ids=[],
            rule_ids=[r['rule_id'] for r in rules],
            user=user
        )
        
        return evidence
    
    def _create_rule_match_evidence(
        self,
        case: Case,
        rule: Dict[str, Any],
        user: str
    ) -> Evidence:
        """Create evidence from a specific rule match."""
        
        evidence_id = f"EVID-{uuid.uuid4().hex[:12].upper()}"
        
        source_data = {
            "rule_id": rule['rule_id'],
            "rule_name": rule['rule_name'],
            "confidence_score": rule['confidence_score'],
            "matched_conditions": rule.get('matched_conditions', [])
        }
        
        description = f"Rule '{rule['rule_name']}' triggered with {rule['confidence_score']*100:.0f}% confidence"
        
        evidence = Evidence(
            evidence_id=evidence_id,
            case_id=case.id,
            evidence_type="rule_match",
            description=description,
            source_system="rule_engine",
            source_data=source_data,
            quality_score=rule['confidence_score'],
            reliability="high",
            transaction_ids=[],
            rule_ids=[rule['rule_id']],
            evidence_date=datetime.fromisoformat(rule['executed_at']),
            collected_at=datetime.utcnow(),
            meta_data={
                "typology": rule['typology']
            }
        )
        
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        
        # Log to audit
        self.audit.log_evidence_collection(
            evidence_id=evidence_id,
            case_id=case.id,
            evidence_type="rule_match",
            source_system="rule_engine",
            quality_score=rule['confidence_score'],
            transaction_ids=[],
            rule_ids=[rule['rule_id']],
            user=user
        )
        
        return evidence
    
    def _generate_claim(
        self,
        case: Case,
        typology: str,
        rules: List[Dict[str, Any]],
        evidence_list: List[Evidence],
        user: str
    ) -> Claim:
        """
        Generate a claim for a specific typology.
        A claim is a structured assertion of suspicious activity.
        """
        
        claim_id = f"CLAIM-{uuid.uuid4().hex[:12].upper()}"
        
        # Calculate aggregate confidence and risk scores
        confidence_score = self._calculate_aggregate_confidence(rules)
        risk_score = self._calculate_risk_score(rules, evidence_list)
        severity = self._determine_severity(risk_score)
        
        # Generate claim statement
        statement = self._generate_claim_statement(
            typology=typology,
            case=case,
            rules=rules,
            evidence_list=evidence_list
        )
        
        claim = Claim(
            claim_id=claim_id,
            case_id=case.id,
            typology=typology,
            statement=statement,
            confidence_score=confidence_score,
            risk_score=risk_score,
            severity=severity,
            rules_triggered=[r['rule_id'] for r in rules],
            evidence_ids=[e.evidence_id for e in evidence_list],
            validated=False,
            meta_data={
                "rule_count": len(rules),
                "evidence_count": len(evidence_list),
                "generation_timestamp": datetime.utcnow().isoformat()
            },
            created_at=datetime.utcnow()
        )
        
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        
        # Log to audit
        self.audit.log_claim_generation(
            claim_id=claim_id,
            case_id=case.id,
            typology=typology,
            statement=statement,
            confidence_score=confidence_score,
            risk_score=risk_score,
            supporting_rule_ids=[r['rule_id'] for r in rules],
            supporting_evidence_ids=[e.evidence_id for e in evidence_list],
            user=user
        )
        
        return claim
    
    def _generate_pattern_description(
        self,
        typology: str,
        txn_count: int,
        total_amount: float,
        time_span_hours: float
    ) -> str:
        """Generate human-readable description of transaction pattern."""
        
        time_desc = f"{time_span_hours:.1f} hours" if time_span_hours < 48 else f"{time_span_hours/24:.1f} days"
        
        patterns = {
            "Structuring": f"Pattern of {txn_count} transactions totaling ${total_amount:,.2f} over {time_desc}, suggesting intentional structuring to avoid reporting thresholds",
            "Smurfing": f"Multiple deposits ({txn_count} transactions, ${total_amount:,.2f}) across different locations within {time_desc}, consistent with smurfing behavior",
            "Layering": f"Rapid movement of ${total_amount:,.2f} through {txn_count} transactions over {time_desc}, indicating potential layering activity",
            "Velocity Abuse": f"Abnormally high transaction velocity: {txn_count} transactions within {time_desc}",
            "High Risk Geography": f"{txn_count} international transactions involving high-risk jurisdictions, totaling ${total_amount:,.2f}"
        }
        
        return patterns.get(typology, f"{txn_count} transactions totaling ${total_amount:,.2f} over {time_desc}")
    
    def _generate_customer_description(self, customer: Customer, typology: str) -> str:
        """Generate customer behavior description."""
        
        flags = []
        if customer.is_pep:
            flags.append("Politically Exposed Person (PEP)")
        if customer.is_high_risk:
            flags.append(f"High-risk customer (rating: {customer.risk_rating})")
        if customer.country:
            flags.append(f"Country: {customer.country}")
        
        flag_text = ", ".join(flags) if flags else "Standard risk profile"
        
        return f"Customer profile: {flag_text}. Activity pattern inconsistent with expected behavior for this customer segment."
    
    def _generate_claim_statement(
        self,
        typology: str,
        case: Case,
        rules: List[Dict[str, Any]],
        evidence_list: List[Evidence]
    ) -> str:
        """Generate formal claim statement."""
        
        customer = case.alert.customer
        
        statements = {
            "Structuring": f"Customer {customer.name} (Account: {customer.account_number}) engaged in apparent structuring activity by conducting multiple transactions designed to evade reporting requirements.",
            
            "Smurfing": f"Customer {customer.name} demonstrated smurfing behavior through multiple deposits across different locations within a short timeframe.",
            
            "Layering": f"Customer {customer.name} engaged in rapid movement of funds consistent with layering, a money laundering technique designed to obscure the origin of funds.",
            
            "Velocity Abuse": f"Customer {customer.name} exhibited abnormal transaction velocity inconsistent with legitimate business activity.",
            
            "High Risk Geography": f"Customer {customer.name} conducted transactions with high-risk jurisdictions without adequate business justification.",
            
            "PEP Risk": f"Politically Exposed Person {customer.name} conducted high-value transactions requiring enhanced due diligence.",
            
            "Wire Transfer Abuse": f"Customer {customer.name} conducted frequent international wire transfers suggesting potential trade-based money laundering.",
            
            "Large Cash Activity": f"Customer {customer.name} engaged in large cash transactions inconsistent with stated business purpose."
        }
        
        return statements.get(typology, f"Customer {customer.name} engaged in suspicious activity consistent with {typology}.")
    
    def _calculate_aggregate_confidence(self, rules: List[Dict[str, Any]]) -> float:
        """Calculate aggregate confidence from multiple rules."""
        if not rules:
            return 0.0
        
        # Weighted average based on individual rule confidences
        total_confidence = sum(r['confidence_score'] for r in rules)
        avg_confidence = total_confidence / len(rules)
        
        # Boost confidence if multiple rules agree
        boost = min(0.1 * (len(rules) - 1), 0.2)
        
        return round(min(avg_confidence + boost, 1.0), 2)
    
    def _calculate_risk_score(
        self,
        rules: List[Dict[str, Any]],
        evidence_list: List[Evidence]
    ) -> float:
        """Calculate overall risk score."""
        
        # Base risk from rules
        rule_risk = sum(r['confidence_score'] for r in rules) / len(rules) if rules else 0
        
        # Evidence quality factor
        evidence_quality = sum(e.quality_score for e in evidence_list) / len(evidence_list) if evidence_list else 0
        
        # Combine with weight
        risk_score = (rule_risk * 0.7) + (evidence_quality * 0.3)
        
        return round(risk_score, 2)
    
    def _determine_severity(self, risk_score: float) -> str:
        """Determine severity level from risk score."""
        if risk_score >= 0.85:
            return "critical"
        elif risk_score >= 0.70:
            return "high"
        elif risk_score >= 0.50:
            return "medium"
        else:
            return "low"
    
    def _calculate_evidence_quality(self, transactions: List[Transaction]) -> float:
        """Calculate evidence quality score based on data completeness."""
        if not transactions:
            return 0.0
        
        # Check data completeness
        completeness_scores = []
        for txn in transactions:
            score = 0.0
            total_fields = 6
            
            if txn.counterparty_name:
                score += 1
            if txn.counterparty_country:
                score += 1
            if txn.location:
                score += 1
            if txn.channel:
                score += 1
            if txn.description:
                score += 1
            score += 1  # Always have amount
            
            completeness_scores.append(score / total_fields)
        
        return round(sum(completeness_scores) / len(completeness_scores), 2)