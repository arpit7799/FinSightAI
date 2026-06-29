# app/engines/fraud/fraud_aggregator.py
"""
Combines Beneish, Altman, and Isolation Forest results
into a single composite fraud score and risk class.

Weighting:
    Beneish M-Score:    40% (most direct manipulation signal)
    Altman Z-Score:     40% (financial health / distress)
    Isolation Forest:   20% (anomaly detection)
"""

# Signal → numeric score mapping for aggregation
BENEISH_SCORE_MAP = {
    "SAFE":         10,
    "GREY_ZONE":    55,
    "MANIPULATOR":  85,
}

ALTMAN_SCORE_MAP = {
    "SAFE":     10,
    "GREY":     50,
    "DISTRESS": 85,
}

# Weights
BENEISH_WEIGHT  = 0.40
ALTMAN_WEIGHT   = 0.40
ISOLATION_WEIGHT = 0.20


def compute_composite_fraud_score(
    beneish_signal: str,
    altman_zone: str,
    is_anomaly: bool,
) -> float:
    """
    Compute a composite fraud risk score from 0 to 100.

    Higher = more fraud risk.
    """
    beneish_component  = BENEISH_SCORE_MAP.get(beneish_signal, 50) * BENEISH_WEIGHT
    altman_component   = ALTMAN_SCORE_MAP.get(altman_zone, 50) * ALTMAN_WEIGHT
    isolation_component = (70 if is_anomaly else 10) * ISOLATION_WEIGHT

    return round(beneish_component + altman_component + isolation_component, 2)


def get_fraud_risk_class(score: float) -> str:
    """Convert composite score to FraudRiskClass."""
    if score < 30:
        return "SAFE"
    elif score < 65:
        return "GREY_ZONE"
    else:
        return "MANIPULATOR"


def merge_red_flags(
    beneish_flags: list,
    altman_flags: list,
    isolation_flags: list,
) -> list:
    """
    Combine red flags from all 3 methods.
    Sort by severity (HIGH first), then by source.
    """
    all_flags = beneish_flags + altman_flags + isolation_flags

    # Sort: HIGH severity first
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_flags.sort(key=lambda f: severity_order.get(f.get("severity", "LOW"), 2))

    return all_flags