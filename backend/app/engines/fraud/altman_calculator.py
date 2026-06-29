# app/engines/fraud/altman_calculator.py
"""
Altman Z-Score Calculator.

The Altman Z-Score predicts the probability of bankruptcy
within 2 years. Developed by Edward Altman (1968).

Widely used by banks, credit analysts, and investors.

Score interpretation:
    Z > 2.99   → SAFE zone (unlikely to go bankrupt)
    1.81-2.99  → GREY zone (uncertain)
    Z < 1.81   → DISTRESS zone (high bankruptcy risk)

Formula (original Altman 1968 for public companies):
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5

Variables:
    X1 = Working Capital / Total Assets
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Market Value of Equity / Total Liabilities
    X5 = Revenue / Total Assets
"""

# Zone thresholds
SAFE_THRESHOLD = 2.99
GREY_LOW_THRESHOLD = 1.81

# Altman Z-Score coefficients (original 1968 model)
COEFFICIENTS = {
    "x1": 1.2,
    "x2": 1.4,
    "x3": 3.3,
    "x4": 0.6,
    "x5": 1.0,
}


def _safe_div(a, b, default=0.0):
    if a is None or b is None or b == 0:
        return default
    return a / b


def calculate_altman(normalized_data: dict) -> dict:
    """
    Calculate Altman Z-Score from normalized financial data.

    Note on X4 (Market Value of Equity / Total Liabilities):
    We don't have market cap from annual reports.
    We substitute Book Value of Equity as a conservative proxy.
    This is the 'private company' variant of the Z-Score.

    Returns dict with all 5 variables, Z-Score, zone, and red flags.
    """
    total_assets = normalized_data.get("total_assets") or 1  # avoid div by zero

    # X1: Working Capital / Total Assets
    working_capital = (
        (normalized_data.get("current_assets") or 0) -
        (normalized_data.get("current_liabilities") or 0)
    )
    x1 = _safe_div(working_capital, total_assets)

    # X2: Retained Earnings / Total Assets
    x2 = _safe_div(
        normalized_data.get("retained_earnings"),
        total_assets
    )

    # X3: EBIT / Total Assets
    ebit = normalized_data.get("ebit") or normalized_data.get("ebitda") or 0
    x3 = _safe_div(ebit, total_assets)

    # X4: Book Value of Equity / Total Liabilities (proxy for market value)
    x4 = _safe_div(
        normalized_data.get("total_equity"),
        normalized_data.get("total_liabilities")
    )

    # X5: Revenue / Total Assets
    x5 = _safe_div(
        normalized_data.get("total_revenue"),
        total_assets
    )

    # ── Calculate Z-Score ─────────────────────────────────────────────────
    z_score = (
        COEFFICIENTS["x1"] * x1 +
        COEFFICIENTS["x2"] * x2 +
        COEFFICIENTS["x3"] * x3 +
        COEFFICIENTS["x4"] * x4 +
        COEFFICIENTS["x5"] * x5
    )

    # ── Determine zone ────────────────────────────────────────────────────
    if z_score > SAFE_THRESHOLD:
        zone = "SAFE"
    elif z_score > GREY_LOW_THRESHOLD:
        zone = "GREY"
    else:
        zone = "DISTRESS"

    # ── Red flags ─────────────────────────────────────────────────────────
    red_flags = _identify_altman_red_flags(z_score, x1, x3, x4)

    return {
        "altman_x1": round(x1, 6),
        "altman_x2": round(x2, 6),
        "altman_x3": round(x3, 6),
        "altman_x4": round(x4, 6),
        "altman_x5": round(x5, 6),
        "altman_score": round(z_score, 6),
        "altman_zone": zone,
        "red_flags": red_flags,
    }


def _identify_altman_red_flags(
    z_score: float, x1: float, x3: float, x4: float
) -> list[dict]:
    """Identify specific red flags from Z-Score variables."""
    flags = []

    if z_score < GREY_LOW_THRESHOLD:
        flags.append({
            "source": "ALTMAN",
            "variable": "Z_SCORE",
            "value": round(z_score, 4),
            "threshold": GREY_LOW_THRESHOLD,
            "severity": "HIGH" if z_score < 1.0 else "MEDIUM",
            "description": f"Z-Score of {z_score:.2f} indicates financial distress zone (threshold: {GREY_LOW_THRESHOLD})",
        })

    if x1 < 0:
        flags.append({
            "source": "ALTMAN",
            "variable": "X1_WORKING_CAPITAL",
            "value": round(x1, 4),
            "threshold": 0,
            "severity": "HIGH",
            "description": "Negative working capital — current liabilities exceed current assets",
        })

    if x3 < 0:
        flags.append({
            "source": "ALTMAN",
            "variable": "X3_EBIT",
            "value": round(x3, 4),
            "threshold": 0,
            "severity": "HIGH",
            "description": "Negative EBIT — company is operating at a loss",
        })

    if x4 < 0.5:
        flags.append({
            "source": "ALTMAN",
            "variable": "X4_EQUITY_RATIO",
            "value": round(x4, 4),
            "threshold": 0.5,
            "severity": "MEDIUM",
            "description": "Low equity to liabilities ratio — heavily debt-financed",
        })

    return flags