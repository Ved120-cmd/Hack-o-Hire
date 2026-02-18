"""
Data Normalizer Service
========================
Normalizes raw JSON input into a flat, analysis-ready structure.
Creates structured Evidence Objects for downstream use.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from backend.schemas.input_schema import CaseInput

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalize and validate incoming case data."""

    def normalize(self, case_input: CaseInput) -> Dict[str, Any]:
        """
        Transform raw CaseInput into a normalized dictionary with:
        - flattened transactions list
        - computed aggregates
        - evidence objects
        """
        logger.info("Normalizing case input for customer %s", case_input.customer.customer_id)

        # Collect all transactions from accounts
        all_transactions = []
        for account in case_input.accounts:
            for txn in account.transactions:
                txn_dict = txn.model_dump()
                txn_dict["account_id"] = account.account_id
                all_transactions.append(txn_dict)

        # Also include flat transactions if provided
        if case_input.transactions:
            for txn in case_input.transactions:
                all_transactions.append(txn.model_dump())

        # Build DataFrame for aggregation
        df = pd.DataFrame(all_transactions) if all_transactions else pd.DataFrame()

        # Compute aggregates
        aggregates = self._compute_aggregates(df)

        # Build evidence objects
        evidence_objects = self._build_evidence_objects(case_input, all_transactions, aggregates)

        normalized = {
            "customer": case_input.customer.model_dump(),
            "kyc": case_input.kyc.model_dump(),
            "accounts": [a.model_dump() for a in case_input.accounts],
            "transactions": all_transactions,
            "alerts": [a.model_dump() for a in case_input.alerts],
            "aggregates": aggregates,
            "evidence_objects": evidence_objects,
            "normalized_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Normalization complete: %d transactions, %d evidence objects",
            len(all_transactions), len(evidence_objects),
        )
        return normalized

    def _compute_aggregates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute statistical aggregates from transaction DataFrame."""
        if df.empty:
            return {
                "total_transactions": 0,
                "total_credit": 0.0,
                "total_debit": 0.0,
                "unique_counterparties": 0,
                "unique_countries": [],
                "avg_transaction_amount": 0.0,
                "max_transaction_amount": 0.0,
                "date_range_days": 0,
            }

        credits = df[df["type"] == "credit"]["amount"].sum() if "type" in df.columns else 0
        debits = df[df["type"] == "debit"]["amount"].sum() if "type" in df.columns else 0

        unique_counterparties = 0
        if "counterparty_account" in df.columns:
            unique_counterparties = df["counterparty_account"].dropna().nunique()

        unique_countries = []
        if "counterparty_country" in df.columns:
            unique_countries = df["counterparty_country"].dropna().unique().tolist()

        date_range_days = 0
        if "date" in df.columns and len(df) > 1:
            try:
                dates = pd.to_datetime(df["date"])
                date_range_days = (dates.max() - dates.min()).days
            except Exception:
                date_range_days = 0

        return {
            "total_transactions": len(df),
            "total_credit": float(credits),
            "total_debit": float(debits),
            "unique_counterparties": int(unique_counterparties),
            "unique_countries": unique_countries,
            "avg_transaction_amount": float(df["amount"].mean()) if not df.empty else 0.0,
            "max_transaction_amount": float(df["amount"].max()) if not df.empty else 0.0,
            "date_range_days": int(date_range_days),
        }

    def _build_evidence_objects(
        self,
        case_input: CaseInput,
        transactions: List[Dict],
        aggregates: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Create structured evidence objects for rule engine consumption."""
        evidence = []

        # Evidence: Customer profile
        evidence.append({
            "evidence_id": f"EV-CUST-{case_input.customer.customer_id}",
            "type": "customer_profile",
            "description": f"Customer {case_input.customer.name} profile and KYC data",
            "data": {
                "customer": case_input.customer.model_dump(),
                "kyc": case_input.kyc.model_dump(),
            },
        })

        # Evidence: Transaction summary
        evidence.append({
            "evidence_id": f"EV-TXN-SUMMARY-{case_input.customer.customer_id}",
            "type": "transaction_summary",
            "description": (
                f"{aggregates['total_transactions']} transactions, "
                f"₹{aggregates['total_credit']:,.0f} credits, "
                f"₹{aggregates['total_debit']:,.0f} debits"
            ),
            "data": aggregates,
        })

        # Evidence: High-value transactions (> 1,00,000)
        high_value = [t for t in transactions if t.get("amount", 0) > 100000]
        if high_value:
            evidence.append({
                "evidence_id": f"EV-HVT-{case_input.customer.customer_id}",
                "type": "high_value_transactions",
                "description": f"{len(high_value)} transactions exceeding ₹1,00,000",
                "data": {"transactions": high_value, "count": len(high_value)},
            })

        # Evidence: International transactions
        intl = [
            t for t in transactions
            if t.get("counterparty_country") and t["counterparty_country"] != "IN"
        ]
        if intl:
            evidence.append({
                "evidence_id": f"EV-INTL-{case_input.customer.customer_id}",
                "type": "international_transactions",
                "description": f"{len(intl)} international transactions detected",
                "data": {
                    "transactions": intl,
                    "countries": list({t["counterparty_country"] for t in intl}),
                },
            })

        # Evidence: Each alert
        for alert in case_input.alerts:
            evidence.append({
                "evidence_id": f"EV-ALERT-{alert.alert_id}",
                "type": "alert",
                "description": alert.description or f"Alert {alert.alert_id}: {alert.alert_type}",
                "data": alert.model_dump(),
            })

        return evidence
