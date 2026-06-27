# app/engines/risk/feature_engineer.py
"""
Builds the feature vector for the risk prediction model.

The ML models were trained on 8 financial features.
We pull these from the already-computed financial ratios
in the database (computed in Phase 5).

If a ratio isn't available, we use a safe default value
rather than crashing — partial data is better than no prediction.
"""

# These are the exact 8 features the models were trained on.
# Order matters — must match training order.
FEATURE_NAMES = [
    "roe",               # Return on Equity
    "roa",               # Return on Assets
    "debt_to_equity",    # Debt to Equity ratio
    "current_ratio",     # Current Ratio
    "quick_ratio",       # Quick Ratio
    "revenue_growth",    # YoY Revenue Growth %
    "cash_flow_margin",  # Operating Cash Flow / Revenue
    "interest_coverage", # EBIT / Interest Expense
]

# Safe defaults when data is missing
# These are set to "average" values so missing data doesn't skew predictions
FEATURE_DEFAULTS = {
    "roe": 0.10,
    "roa": 0.06,
    "debt_to_equity": 0.5,
    "current_ratio": 1.5,
    "quick_ratio": 1.2,
    "revenue_growth": 0.05,
    "cash_flow_margin": 0.10,
    "interest_coverage": 5.0,
}

# Mapping from ratio names in DB → feature names we use
RATIO_NAME_MAP = {
    "Return on Equity": "roe",
    "Return on Assets": "roa",
    "Debt to Equity": "debt_to_equity",
    "Current Ratio": "current_ratio",
    "Quick Ratio": "quick_ratio",
    "Interest Coverage": "interest_coverage",
}


def build_feature_vector(
    ratios: list,
    normalized_data: dict,
) -> dict:
    """
    Build the 8-feature dict for the risk model.

    Args:
        ratios: list of FinancialRatio objects from Phase 5
        normalized_data: merged financial statement values from Phase 4

    Returns:
        dict with exactly 8 features, in FEATURE_NAMES order
    """
    features = dict(FEATURE_DEFAULTS)  # start with defaults

    # Pull ratio values from computed ratios (Phase 5 output)
    for ratio in ratios:
        feature_key = RATIO_NAME_MAP.get(ratio.ratio_name)
        if feature_key and ratio.computed_value is not None:
            features[feature_key] = float(ratio.computed_value)

    # Revenue growth needs two years of data — compute from normalized_data
    # For now we use 0 if not available (single filing)
    if "revenue_growth" not in features or features["revenue_growth"] == FEATURE_DEFAULTS["revenue_growth"]:
        features["revenue_growth"] = _estimate_revenue_growth(normalized_data)

    # Cash flow margin = operating cash flow / revenue
    if "cash_flow_margin" not in features or features["cash_flow_margin"] == FEATURE_DEFAULTS["cash_flow_margin"]:
        features["cash_flow_margin"] = _compute_cash_flow_margin(normalized_data)

    return features


def features_to_list(features: dict) -> list[float]:
    """
    Convert feature dict to ordered list for model input.
    Order must match FEATURE_NAMES exactly.
    """
    return [features.get(name, FEATURE_DEFAULTS[name]) for name in FEATURE_NAMES]


def _estimate_revenue_growth(normalized_data: dict) -> float:
    """
    If we have revenue, use 0 as growth (unknown without prior year).
    A real implementation would compare across multiple filings.
    """
    return 0.0


def _compute_cash_flow_margin(normalized_data: dict) -> float:
    """Compute cash flow margin from normalized financial data."""
    ocf = normalized_data.get("operating_cash_flow")
    revenue = normalized_data.get("total_revenue")

    if ocf and revenue and revenue != 0:
        return round(ocf / revenue, 4)

    return FEATURE_DEFAULTS["cash_flow_margin"]