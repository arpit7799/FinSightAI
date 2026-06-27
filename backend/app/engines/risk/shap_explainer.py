# app/engines/risk/shap_explainer.py
"""
Generates SHAP explanations for risk predictions.

SHAP (SHapley Additive exPlanations) tells us how much each
feature contributed to pushing the risk score up or down.

Positive SHAP value = this feature increases risk
Negative SHAP value = this feature decreases risk

We use the XGBoost model for SHAP because TreeExplainer
is exact and fast for tree-based models.
"""

import numpy as np
import shap
from app.engines.risk.feature_engineer import FEATURE_NAMES

# Human-readable labels for each feature
FEATURE_LABELS = {
    "roe": "Return on Equity",
    "roa": "Return on Assets",
    "debt_to_equity": "Debt to Equity Ratio",
    "current_ratio": "Current Ratio",
    "quick_ratio": "Quick Ratio",
    "revenue_growth": "Revenue Growth",
    "cash_flow_margin": "Cash Flow Margin",
    "interest_coverage": "Interest Coverage",
}


class SHAPExplainer:
    """
    Generates SHAP values using TreeExplainer for the XGBoost model.

    TreeExplainer is exact (not approximate) for tree models —
    it's much faster and more accurate than KernelExplainer.

    Usage:
        explainer = SHAPExplainer(xgb_model)
        explanation = explainer.explain(features_dict)
    """

    def __init__(self, xgb_model):
        self.model = xgb_model
        # TreeExplainer is initialized with the model
        self.explainer = shap.TreeExplainer(xgb_model)

    def explain(self, features: dict) -> dict:
        """
        Generate SHAP explanation for a single prediction.

        Returns:
            {
                "shap_values": {"roe": -0.12, "debt_to_equity": 0.18, ...},
                "base_value": 0.35,
                "top_factors": [
                    {"factor": "Debt to Equity Ratio", "direction": "increases_risk",
                     "impact": 0.18, "feature_key": "debt_to_equity"},
                    ...
                ]
            }
        """
        # Build feature array in correct order
        feature_values = [features.get(name, 0.0) for name in FEATURE_NAMES]
        X = np.array(feature_values).reshape(1, -1)

        # Get SHAP values
        shap_values = self.explainer.shap_values(X)

        # shap_values can be a list (for classifiers) or array
        # For binary classification, we want the values for class 1 (distress)
        if isinstance(shap_values, list):
            values = shap_values[1][0]  # class 1, first sample
        else:
            values = shap_values[0]

        base_value = float(self.explainer.expected_value)
        if isinstance(base_value, (list, np.ndarray)):
            base_value = float(base_value[1])  # class 1

        # Map feature names to SHAP values
        shap_dict = {
            name: round(float(val), 6)
            for name, val in zip(FEATURE_NAMES, values)
        }

        # Build top factors list sorted by absolute impact
        top_factors = self._build_top_factors(shap_dict, features)

        return {
            "shap_values": shap_dict,
            "base_value": round(base_value, 6),
            "top_factors": top_factors,
        }

    def _build_top_factors(self, shap_dict: dict, features: dict) -> list[dict]:
        """
        Build a sorted list of the most impactful features.
        Sorted by absolute SHAP value (highest impact first).
        """
        factors = []

        for feature_key, shap_val in shap_dict.items():
            factors.append({
                "factor": FEATURE_LABELS.get(feature_key, feature_key),
                "feature_key": feature_key,
                "feature_value": round(features.get(feature_key, 0.0), 4),
                "shap_value": shap_val,
                "direction": "increases_risk" if shap_val > 0 else "decreases_risk",
                "impact": abs(shap_val),
            })

        # Sort by impact (highest first)
        factors.sort(key=lambda x: x["impact"], reverse=True)

        return factors[:5]  # top 5 factors