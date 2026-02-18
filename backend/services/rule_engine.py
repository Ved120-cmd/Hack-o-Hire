"""
Rule-Based Detection Engine
=============================
Implements threshold, velocity, jurisdiction, and typology checks.
Produces Claim Objects, evidence linkage, risk/confidence scores,
and reasoning artifacts.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# High-risk jurisdictions (FATF grey/blacklist + common offshore)
# ------------------------------------------------------------------ #
HIGH_RISK_JURISDICTIONS = {
    "AF", "AL", "MM", "PA", "PK", "SY", "YE", "IR", "KP",
    "VG", "KY", "JE", "GG", "IM", "BZ", "SC", "MU",
    "AE", "HK", "SG",  # not blacklisted but common layering destinations
}

# ------------------------------------------------------------------ #
# Configurable thresholds
# ------------------------------------------------------------------ #
THRESHOLDS = {
    "single_txn_amount": 1000000,        # ₹10 lakh
    "total_inflow_7d": 5000000,          # ₹50 lakh
    "velocity_count_7d": 30,             # > 30 txns in 7 days
    "unique_counterparties_7d": 20,      # > 20 senders
    "structuring_band_low": 900000,      # just below ₹10 lakh
    "structuring_band_high": 999999,
    "rapid_outflow_pct": 0.80,           # 80% outflow within 48h of inflow
}


class RuleEngine:
    """Deterministic rule-based fraud detection engine."""

    def evaluate(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all rules against normalised case data.

        Returns
        -------
        dict with keys:
            triggered_rules  – list of rule result dicts
            claim_object     – assembled claim
            risk_score       – 0.0-1.0
            confidence_score – 0.0-1.0
            typologies       – list of detected typology strings
            reasoning_artifact – full technical JSON
        """
        logger.info("Rule engine evaluation started")

        transactions = normalized_data.get("transactions", [])
        customer = normalized_data.get("customer", {})
        kyc = normalized_data.get("kyc", {})
        aggregates = normalized_data.get("aggregates", {})
        evidence_objects = normalized_data.get("evidence_objects", [])

        df = pd.DataFrame(transactions) if transactions else pd.DataFrame()
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # Run each rule
        results: List[Dict[str, Any]] = []
        results.append(self._check_threshold(df, aggregates))
        results.append(self._check_velocity(df, aggregates))
        results.append(self._check_jurisdiction(df, transactions))
        results.append(self._check_structuring(df, transactions))
        results.append(self._check_layering(df, transactions, aggregates))
        results.append(self._check_rapid_international(df, transactions))
        results.append(self._check_professional_facilitation(kyc, customer, aggregates))
        results.append(self._check_predicate_offences(kyc, aggregates))

        triggered = [r for r in results if r["triggered"]]
        typologies = list({r["typology"] for r in triggered if r.get("typology")})

        # Compute composite scores
        risk_score = self._compute_risk_score(triggered, kyc)
        confidence_score = self._compute_confidence(triggered)

        # Build claim object
        claim_object = self._build_claim(
            normalized_data, triggered, typologies,
            risk_score, confidence_score, evidence_objects,
        )

        # Build reasoning artifact
        reasoning_artifact = {
            "engine_version": "1.0.0",
            "evaluated_at": datetime.utcnow().isoformat(),
            "rules_evaluated": len(results),
            "rules_triggered": len(triggered),
            "rule_details": results,
            "composite_risk_score": risk_score,
            "composite_confidence": confidence_score,
            "typologies_detected": typologies,
            "thresholds_used": THRESHOLDS,
        }

        logger.info(
            "Rule engine done – %d/%d rules triggered, risk=%.2f, typologies=%s",
            len(triggered), len(results), risk_score, typologies,
        )

        return {
            "triggered_rules": results,
            "claim_object": claim_object,
            "risk_score": risk_score,
            "confidence_score": confidence_score,
            "typologies": typologies,
            "reasoning_artifact": reasoning_artifact,
        }

    # ------------------------------------------------------------ #
    # Individual rule checks
    # ------------------------------------------------------------ #

    def _check_threshold(self, df: pd.DataFrame, agg: Dict) -> Dict[str, Any]:
        """R1: Single transaction or aggregate exceeds threshold."""
        single_hit = agg.get("max_transaction_amount", 0) > THRESHOLDS["single_txn_amount"]
        total_hit = agg.get("total_credit", 0) > THRESHOLDS["total_inflow_7d"]

        triggered = single_hit or total_hit
        evidence = []
        if single_hit:
            evidence.append(f"Max single txn ₹{agg['max_transaction_amount']:,.0f} exceeds ₹{THRESHOLDS['single_txn_amount']:,}")
        if total_hit:
            evidence.append(f"Total credits ₹{agg['total_credit']:,.0f} exceeds ₹{THRESHOLDS['total_inflow_7d']:,}")

        return {
            "rule_name": "threshold_check",
            "triggered": triggered,
            "confidence": 0.9 if triggered else 0.0,
            "risk_contribution": 0.25 if triggered else 0.0,
            "typology": "high_value_transaction" if triggered else None,
            "evidence": evidence,
            "reasoning": "Transaction amounts exceed regulatory reporting thresholds" if triggered else "Within thresholds",
        }

    def _check_velocity(self, df: pd.DataFrame, agg: Dict) -> Dict[str, Any]:
        """R2: Transaction velocity exceeds normal patterns."""
        count_hit = agg.get("total_transactions", 0) > THRESHOLDS["velocity_count_7d"]
        cp_hit = agg.get("unique_counterparties", 0) > THRESHOLDS["unique_counterparties_7d"]

        triggered = count_hit or cp_hit
        evidence = []
        if count_hit:
            evidence.append(f"{agg['total_transactions']} transactions in observation window (threshold: {THRESHOLDS['velocity_count_7d']})")
        if cp_hit:
            evidence.append(f"{agg['unique_counterparties']} unique counterparties (threshold: {THRESHOLDS['unique_counterparties_7d']})")

        return {
            "rule_name": "velocity_check",
            "triggered": triggered,
            "confidence": 0.85 if triggered else 0.0,
            "risk_contribution": 0.20 if triggered else 0.0,
            "typology": "rapid_movement" if triggered else None,
            "evidence": evidence,
            "reasoning": "Unusually high transaction velocity detected" if triggered else "Normal velocity",
        }

    def _check_jurisdiction(self, df: pd.DataFrame, transactions: List[Dict]) -> Dict[str, Any]:
        """R3: Transactions involving high-risk jurisdictions."""
        risky_countries = set()
        risky_txns = []
        for t in transactions:
            country = (t.get("counterparty_country") or "").upper()
            if country in HIGH_RISK_JURISDICTIONS:
                risky_countries.add(country)
                risky_txns.append(t.get("transaction_id", "unknown"))

        triggered = len(risky_countries) > 0
        return {
            "rule_name": "jurisdiction_check",
            "triggered": triggered,
            "confidence": 0.80 if triggered else 0.0,
            "risk_contribution": 0.20 if triggered else 0.0,
            "typology": "high_risk_jurisdiction" if triggered else None,
            "evidence": [
                f"Transactions to/from high-risk jurisdictions: {', '.join(risky_countries)}",
                f"Affected transactions: {risky_txns[:10]}",
            ] if triggered else [],
            "reasoning": f"Funds flow to/from FATF-listed or high-risk jurisdictions: {risky_countries}" if triggered else "No high-risk jurisdictions",
        }

    def _check_structuring(self, df: pd.DataFrame, transactions: List[Dict]) -> Dict[str, Any]:
        """R4: Structuring – amounts just below reporting threshold."""
        structured = [
            t for t in transactions
            if THRESHOLDS["structuring_band_low"] <= t.get("amount", 0) <= THRESHOLDS["structuring_band_high"]
        ]
        triggered = len(structured) >= 3  # 3+ near-threshold txns = suspicious

        return {
            "rule_name": "structuring_check",
            "triggered": triggered,
            "confidence": 0.90 if triggered else 0.0,
            "risk_contribution": 0.25 if triggered else 0.0,
            "typology": "structuring" if triggered else None,
            "evidence": [
                f"{len(structured)} transactions in ₹{THRESHOLDS['structuring_band_low']:,}-₹{THRESHOLDS['structuring_band_high']:,} band",
            ] if triggered else [],
            "reasoning": "Multiple transactions structured just below reporting threshold – indicative of smurfing" if triggered else "No structuring pattern",
        }

    def _check_layering(self, df: pd.DataFrame, transactions: List[Dict], agg: Dict) -> Dict[str, Any]:
        """R5: Layering – rapid inflows from many sources followed by outflows."""
        many_sources = agg.get("unique_counterparties", 0) > 10
        credits = [t for t in transactions if t.get("type") == "credit"]
        debits = [t for t in transactions if t.get("type") == "debit"]

        total_credit = sum(t.get("amount", 0) for t in credits)
        total_debit = sum(t.get("amount", 0) for t in debits)

        rapid_outflow = total_debit > (total_credit * THRESHOLDS["rapid_outflow_pct"]) if total_credit > 0 else False
        triggered = many_sources and rapid_outflow

        return {
            "rule_name": "layering_check",
            "triggered": triggered,
            "confidence": 0.88 if triggered else 0.0,
            "risk_contribution": 0.30 if triggered else 0.0,
            "typology": "layering" if triggered else None,
            "evidence": [
                f"Received funds from {agg.get('unique_counterparties', 0)} unique sources",
                f"₹{total_credit:,.0f} in → ₹{total_debit:,.0f} out ({total_debit/total_credit*100:.0f}% outflow)" if total_credit > 0 else "No outflow calc",
            ] if triggered else [],
            "reasoning": "Classic layering pattern: funds aggregated from multiple sources then rapidly moved onward" if triggered else "No layering pattern",
        }

    def _check_rapid_international(self, df: pd.DataFrame, transactions: List[Dict]) -> Dict[str, Any]:
        """R6: Rapid international movement – large sums moved cross-border quickly."""
        intl_debits = [
            t for t in transactions
            if t.get("type") == "debit"
            and t.get("counterparty_country", "IN") != "IN"
            and t.get("amount", 0) > 500000
        ]
        triggered = len(intl_debits) >= 1

        return {
            "rule_name": "rapid_international_movement",
            "triggered": triggered,
            "confidence": 0.85 if triggered else 0.0,
            "risk_contribution": 0.20 if triggered else 0.0,
            "typology": "rapid_international_movement" if triggered else None,
            "evidence": [
                f"{len(intl_debits)} large international outflows detected",
                f"Destinations: {list({t.get('counterparty_country') for t in intl_debits})}",
            ] if triggered else [],
            "reasoning": "Significant funds rapidly transferred to foreign jurisdictions" if triggered else "No rapid international movement",
        }

    def _check_professional_facilitation(self, kyc: Dict, customer: Dict, agg: Dict) -> Dict[str, Any]:
        """R7: Professional facilitation – income inconsistent with activity."""
        annual_income = kyc.get("annual_income", 0) or 0
        total_credit = agg.get("total_credit", 0)

        # If turnover > 10x declared income, suspicious
        ratio = total_credit / annual_income if annual_income > 0 else 999
        triggered = ratio > 10 and total_credit > 1000000

        return {
            "rule_name": "professional_facilitation",
            "triggered": triggered,
            "confidence": 0.75 if triggered else 0.0,
            "risk_contribution": 0.15 if triggered else 0.0,
            "typology": "professional_facilitation" if triggered else None,
            "evidence": [
                f"Declared annual income: ₹{annual_income:,.0f}",
                f"Transaction volume: ₹{total_credit:,.0f} ({ratio:.1f}x declared income)",
            ] if triggered else [],
            "reasoning": "Transaction volumes grossly inconsistent with declared income – possible third-party facilitation" if triggered else "Income consistent with activity",
        }

    def _check_predicate_offences(self, kyc: Dict, agg: Dict) -> Dict[str, Any]:
        """R8: Indicators of predicate offences (PEP, sanctions, adverse media)."""
        pep = kyc.get("pep_status", False)
        sanctions = kyc.get("sanctions_match", False)
        high_risk = kyc.get("risk_rating", "").lower() == "high"

        triggered = pep or sanctions or high_risk
        evidence = []
        if pep:
            evidence.append("Customer is a Politically Exposed Person (PEP)")
        if sanctions:
            evidence.append("Customer matches sanctions list")
        if high_risk:
            evidence.append("Customer has HIGH KYC risk rating")

        return {
            "rule_name": "predicate_offence_indicators",
            "triggered": triggered,
            "confidence": 0.95 if sanctions else (0.70 if triggered else 0.0),
            "risk_contribution": 0.30 if sanctions else (0.15 if triggered else 0.0),
            "typology": "predicate_offences" if triggered else None,
            "evidence": evidence,
            "reasoning": "Subject linked to predicate offence indicators under POCA Section 340" if triggered else "No predicate offence indicators",
        }

    # ------------------------------------------------------------ #
    # Score computation
    # ------------------------------------------------------------ #

    def _compute_risk_score(self, triggered: List[Dict], kyc: Dict) -> float:
        """Composite risk score from triggered rules (0.0-1.0)."""
        if not triggered:
            return 0.05  # baseline

        score = sum(r.get("risk_contribution", 0) for r in triggered)
        # Boost for PEP/sanctions
        if kyc.get("sanctions_match"):
            score += 0.15
        if kyc.get("pep_status"):
            score += 0.05

        return min(round(score, 4), 1.0)

    def _compute_confidence(self, triggered: List[Dict]) -> float:
        """Average confidence of triggered rules."""
        if not triggered:
            return 0.0
        avg = sum(r.get("confidence", 0) for r in triggered) / len(triggered)
        return round(avg, 4)

    # ------------------------------------------------------------ #
    # Claim builder
    # ------------------------------------------------------------ #

    def _build_claim(
        self,
        normalized: Dict,
        triggered: List[Dict],
        typologies: List[str],
        risk_score: float,
        confidence: float,
        evidence_objects: List[Dict],
    ) -> Dict[str, Any]:
        """Assemble a Claim Object from rule outputs."""
        return {
            "customer_id": normalized.get("customer", {}).get("customer_id", ""),
            "typologies": typologies,
            "triggered_rules": [r["rule_name"] for r in triggered],
            "risk_score": risk_score,
            "confidence_score": confidence,
            "evidence_summary": [
                {
                    "rule": r["rule_name"],
                    "evidence": r["evidence"],
                    "reasoning": r["reasoning"],
                }
                for r in triggered
            ],
            "evidence_objects": evidence_objects,
            "aggregates": normalized.get("aggregates", {}),
            "kyc_flags": {
                "pep": normalized.get("kyc", {}).get("pep_status", False),
                "sanctions": normalized.get("kyc", {}).get("sanctions_match", False),
                "risk_rating": normalized.get("kyc", {}).get("risk_rating", "unknown"),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
