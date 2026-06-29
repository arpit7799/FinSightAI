# app/engines/fraud/isolation_forest_detector.py
"""
Isolation Forest anomaly detection for fraud signals.

Isolation Forest is an unsupervised ML algorithm that detects
outliers by isolating data points that are "different" from the rest.

We train it on the 8 financial ratio features and check if
the current company's ratios are anomalous compared to typical patterns.

Since we don't have a large training set at runtime, we use a
small reference dataset of typical IT services company ratios
to build the forest. This is good enough for a portfolio project.
"""

import numpy as np
from sklearn.ensemble import IsolationForest

# Reference data — typical ratio ranges for healthy IT services companies
# This acts as the "normal" baseline for anomaly detection
# Each row is [roe, roa, debt_equity, current_ratio, quick_ratio,
#              revenue_growth, cash_flow_margin, interest_coverage]
REFERENCE_DATA = [
    [0.25, 0.15, 0.10, 2.50, 2.20, 0.15, 0.20, 25.0],  # TCS-like
    [0.28, 0.18, 0.05, 3.00, 2.80, 0.12, 0.22, 30.0],  # Infosys-like
    [0.20, 0.12, 0.15, 2.20, 2.00, 0.10, 0.18, 18.0],  # Wipro-like
    [0.22, 0.14, 0.08, 2.80, 2.50, 0.18, 0.19, 22.0],  # HCL-like
    [0.18, 0.10, 0.20, 1.80, 1.60, 0.08, 0.15, 12.0],  # Mid-cap IT
    [0.15, 0.08, 0.30, 1.50, 1.30, 0.05, 0.12, 8.0],   # Smaller IT
    [0.30, 0.20, 0.05, 3.50, 3.20, 0.20, 0.25, 40.0],  # Strong performer
    [0.10, 0.06, 0.40, 1.20, 1.00, 0.03, 0.08, 5.0],   # Weak performer
    [0.23, 0.16, 0.12, 2.60, 2.30, 0.14, 0.21, 20.0],
    [0.19, 0.11, 0.18, 2.00, 1.80, 0.09, 0.16, 14.0],
]

from app.engines.risk.feature_engineer import FEATURE_NAMES


class IsolationForestDetector:
    """
    Detects anomalous financial profiles using Isolation Forest.

    The model is trained on reference data (typical IT company ratios)
    and then scores the input company's ratios.

    Anomaly score:
        Positive → normal (inlier)
        Negative → anomalous (outlier) — potential fraud signal

    Usage:
        detector = IsolationForestDetector()
        result = detector.detect(features_dict)
    """

    def __init__(self):
        # Train on reference data
        # contamination=0.1 means we expect ~10% of data to be anomalous
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42,  # reproducible results
        )
        X_ref = np.array(REFERENCE_DATA)
        self.model.fit(X_ref)

    def detect(self, features: dict) -> dict:
        """
        Score the given financial feature vector for anomalies.

        Returns:
            {
                "isolation_score": -0.15,  # negative = anomaly
                "is_anomaly": True,
                "red_flags": [...]
            }
        """
        # Build feature vector in correct order
        feature_values = [features.get(name, 0.0) for name in FEATURE_NAMES]
        X = np.array(feature_values).reshape(1, -1)

        # score_samples returns anomaly score
        # More negative = more anomalous
        raw_score = float(self.model.score_samples(X)[0])

        # predict returns 1 (normal) or -1 (anomaly)
        prediction = int(self.model.predict(X)[0])
        is_anomaly = prediction == -1

        red_flags = []
        if is_anomaly:
            red_flags.append({
                "source": "ISOLATION_FOREST",
                "variable": "ANOMALY_SCORE",
                "value": round(raw_score, 4),
                "threshold": 0.0,
                "severity": "MEDIUM",
                "description": (
                    f"Financial profile is statistically anomalous "
                    f"(score: {raw_score:.3f}). Ratios deviate significantly "
                    f"from typical IT services company patterns."
                ),
            })

        return {
            "isolation_score": round(raw_score, 6),
            "is_anomaly": is_anomaly,
            "red_flags": red_flags,
        }