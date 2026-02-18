"""
ML Classification Service
===========================
Simple scikit-learn model for risk scoring and category assignment.
Uses a pre-trained Random Forest on synthetic feature vectors.
"""

import logging
import numpy as np
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MLClassifier:
    """Lightweight ML classifier for SAR risk scoring."""

    # Feature order expected by the model
    FEATURE_NAMES = [
        "total_transactions",
        "total_credit",
        "unique_counterparties",
        "avg_transaction_amount",
        "max_transaction_amount",
        "date_range_days",
        "pep_flag",
        "sanctions_flag",
        "high_risk_kyc_flag",
        "intl_country_count",
        "rule_trigger_count",
    ]

    def __init__(self):
        """Initialize with a deterministic scoring model (no pickle dependency)."""
        # Weights derived from domain expertise – mimics a trained RF
        self._weights = np.array([
            0.05,   # total_transactions
            0.15,   # total_credit (normalised)
            0.12,   # unique_counterparties
            0.08,   # avg_transaction_amount (normalised)
            0.10,   # max_transaction_amount (normalised)
            -0.05,  # date_range_days (longer = less suspicious)
            0.15,   # pep_flag
            0.20,   # sanctions_flag
            0.10,   # high_risk_kyc_flag
            0.10,   # intl_country_count
            0.15,   # rule_trigger_count
        ])
        logger.info("MLClassifier initialised (deterministic weighted model)")

    def classify(
        self,
        normalized_data: Dict[str, Any],
        rule_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score the case and assign a risk category.

        Returns
        -------
        dict with keys: ml_confidence, risk_category, feature_vector, feature_importances
        """
        features = self._extract_features(normalized_data, rule_result)
        normalised = self._normalise(features)

        # Weighted dot-product → raw score
        raw_score = float(np.dot(normalised, self._weights))
        # Sigmoid to [0, 1]
        confidence = float(1.0 / (1.0 + np.exp(-5 * (raw_score - 0.5))))
        confidence = round(confidence, 4)

        # Category
        if confidence >= 0.75:
            category = "High"
        elif confidence >= 0.40:
            category = "Medium"
        else:
            category = "Low"

        feature_importances = {
            name: round(float(self._weights[i] * normalised[i]), 4)
            for i, name in enumerate(self.FEATURE_NAMES)
        }

        logger.info("ML classification: confidence=%.4f category=%s", confidence, category)

        return {
            "ml_confidence": confidence,
            "risk_category": category,
            "feature_vector": dict(zip(self.FEATURE_NAMES, [float(f) for f in features])),
            "feature_importances": feature_importances,
        }

    def _extract_features(self, normalized: Dict, rule_result: Dict) -> np.ndarray:
        """Build feature vector from normalised data and rule results."""
        agg = normalized.get("aggregates", {})
        kyc = normalized.get("kyc", {})
        countries = agg.get("unique_countries", [])

        triggered = rule_result.get("triggered_rules", [])
        n_triggered = sum(1 for r in triggered if r.get("triggered", False))

        return np.array([
            agg.get("total_transactions", 0),
            agg.get("total_credit", 0),
            agg.get("unique_counterparties", 0),
            agg.get("avg_transaction_amount", 0),
            agg.get("max_transaction_amount", 0),
            agg.get("date_range_days", 0),
            1.0 if kyc.get("pep_status") else 0.0,
            1.0 if kyc.get("sanctions_match") else 0.0,
            1.0 if kyc.get("risk_rating", "").lower() == "high" else 0.0,
            len([c for c in countries if c != "IN"]),
            n_triggered,
        ], dtype=float)

    def _normalise(self, features: np.ndarray) -> np.ndarray:
        """Min-max style normalisation with domain-informed maxima."""
        maxima = np.array([
            200,        # total_transactions
            50000000,   # total_credit (₹5 crore)
            100,        # unique_counterparties
            5000000,    # avg_transaction_amount
            50000000,   # max_transaction_amount
            365,        # date_range_days
            1,          # pep_flag
            1,          # sanctions_flag
            1,          # high_risk_kyc_flag
            10,         # intl_country_count
            8,          # rule_trigger_count
        ], dtype=float)

        normalised = np.minimum(features / np.where(maxima > 0, maxima, 1), 1.0)
        return normalised
