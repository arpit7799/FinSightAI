# app/engines/risk/risk_scorer.py
"""
Loads trained XGBoost and LightGBM models and generates risk scores.

Both models output a probability (0–1) of financial distress.
We combine them in a weighted average to get the final score.

Final score = (XGB_score * 0.6 + LGBM_score * 0.4) * 100
→ Converts to 0–100 range for readability.
"""

import os
import pickle
import numpy as np
from app.engines.risk.feature_engineer import FEATURE_NAMES

# Weights for model ensemble
XGB_WEIGHT = 0.6
LGBM_WEIGHT = 0.4

# Risk score thresholds
RISK_THRESHOLDS = {
    "LOW": (0, 30),
    "MEDIUM": (30, 60),
    "HIGH": (60, 80),
    "CRITICAL": (80, 100),
}

# Path to saved model files
MODELS_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../../../ml/models"
)


def _get_risk_class(score: float) -> str:
    """Convert numeric score to risk class label."""
    for risk_class, (low, high) in RISK_THRESHOLDS.items():
        if low <= score < high:
            return risk_class
    return "CRITICAL"  # score == 100


class RiskScorer:
    """
    Loads both models once and reuses them for predictions.

    The models are loaded lazily — only when first needed.
    This avoids slow startup if the risk engine isn't used.

    Usage:
        scorer = RiskScorer()
        result = scorer.predict(feature_vector_dict)
    """

    def __init__(self):
        self._xgb_model = None
        self._lgbm_model = None

    def _load_models(self):
        """Load models from disk if not already loaded."""
        if self._xgb_model is None:
            xgb_path = os.path.join(MODELS_DIR, "risk_xgboost.pkl")
            with open(xgb_path, "rb") as f:
                self._xgb_model = pickle.load(f)

        if self._lgbm_model is None:
            lgbm_path = os.path.join(MODELS_DIR, "risk_lightgbm.pkl")
            with open(lgbm_path, "rb") as f:
                self._lgbm_model = pickle.load(f)

    def predict(self, features: dict) -> dict:
        """
        Generate a risk prediction from the feature dict.

        Returns:
            {
                "risk_score": 67.5,
                "risk_class": "HIGH",
                "xgb_score": 0.68,
                "lgbm_score": 0.67,
                "feature_vector": {...}
            }
        """
        self._load_models()

        # Convert dict to ordered numpy array
        feature_values = [features.get(name, 0.0) for name in FEATURE_NAMES]
        X = np.array(feature_values).reshape(1, -1)

        # Get probabilities from each model
        # predict_proba returns [[prob_class_0, prob_class_1]]
        # We want prob_class_1 (probability of financial distress)
        try:
            xgb_prob = float(self._xgb_model.predict_proba(X)[0][1])
        except Exception:
            # Fallback if model format differs
            xgb_prob = float(self._xgb_model.predict(X)[0])

        try:
            lgbm_prob = float(self._lgbm_model.predict_proba(X)[0][1])
        except Exception:
            lgbm_prob = float(self._lgbm_model.predict(X)[0])

        # Weighted ensemble score → 0 to 100
        combined_prob = (xgb_prob * XGB_WEIGHT) + (lgbm_prob * LGBM_WEIGHT)
        risk_score = round(combined_prob * 100, 2)

        return {
            "risk_score": risk_score,
            "risk_class": _get_risk_class(risk_score),
            "xgb_score": round(xgb_prob, 4),
            "lgbm_score": round(lgbm_prob, 4),
            "feature_vector": features,
        }