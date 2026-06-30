# app/engines/fraud/beneish_calculator.py
"""
Beneish M-Score Calculator.

The Beneish M-Score is an 8-variable statistical model that detects
earnings manipulation in financial statements.

Developed by Professor Messod Beneish (1999).
Used by forensic accountants and auditors worldwide.

Score interpretation:
    M > -2.22  → Likely MANIPULATOR (earnings manipulation probable)
    M < -2.22  → Likely SAFE (non-manipulator)
    M < -2.99  → Very likely SAFE

The 8 variables (indices):
    DSRI  - Days Sales Receivable Index
    GMI   - Gross Margin Index
    AQI   - Asset Quality Index
    SGI   - Sales Growth Index
    DEPI  - Depreciation Index
    SGAI  - SGA Expense Index
    LVGI  - Leverage Index
    TATA  - Total Accruals to Total Assets

All variables compare current year to prior year.
Since we often only have 1 year of data, we use defaults
for the index calculations when prior year is unavailable.

IMPORTANT:
The Beneish M-Score requires two years of financial data.

If prior=None, current-year data is used as the prior period.
This causes all index variables to evaluate to approximately 1.0,
which is only a fallback and should not be interpreted as a
reliable manipulation assessment.

"""

# Beneish M-Score threshold
MANIPULATOR_THRESHOLD = -2.22
SAFE_THRESHOLD = -2.99

# Coefficient weights from Beneish (1999) paper
BENEISH_COEFFICIENTS = {
    "constant": -4.840,
    "dsri":      0.920,
    "gmi":       0.528,
    "aqi":       0.404,
    "sgi":       0.892,
    "depi":      0.115,
    "sgai":     -0.172,
    "lvgi":     -0.327,
    "tata":      4.679,
}

# Red flag thresholds for each variable
# Values beyond these are considered warning signals
RED_FLAG_THRESHOLDS = {
    "dsri":  {"threshold": 1.465, "direction": "above",
              "description": "Receivables growing much faster than revenue — possible revenue inflation"},
    "gmi":   {"threshold": 1.193, "direction": "above",
              "description": "Gross margin deteriorating — possible cost manipulation"},
    "aqi":   {"threshold": 1.254, "direction": "above",
              "description": "Asset quality declining — possible capitalisation of expenses"},
    "sgi":   {"threshold": 1.607, "direction": "above",
              "description": "Unusually high sales growth — may indicate aggressive revenue recognition"},
    "depi":  {"threshold": 1.083, "direction": "above",
              "description": "Depreciation rate slowing — possible asset life manipulation"},
    "sgai":  {"threshold": 1.041, "direction": "above",
              "description": "SG&A expenses growing faster than sales"},
    "lvgi":  {"threshold": 1.037, "direction": "above",
              "description": "Leverage increasing — higher financial risk"},
    "tata":  {"threshold": 0.031, "direction": "above",
              "description": "High total accruals — earnings quality concern"},
}


def _safe_div(a, b, default=1.0):
    """Safe division returning default if b is 0 or None."""
    if a is None or b is None or b == 0:
        return default
    return a / b


def calculate_beneish(current: dict, prior: dict = None) -> dict:
    """
    Calculate Beneish M-Score from financial data.

    Args:
        current: normalized financial data for current year
        prior: normalized financial data for prior year (optional)
               If None, we use defaults of 1.0 for all indices
               (assumes no change from prior year — conservative)

    Returns dict with all 8 variables, the M-Score, signal, and red flags.
    """
    # Use prior year data if available, else use current as proxy
    # (indices become 1.0 meaning "no change" — conservative assumption)
    p = prior if prior else current

    # ── Compute 8 Beneish variables ───────────────────────────────────────

    # DSRI: Days Sales Receivable Index
    # (Receivables_t / Revenue_t) / (Receivables_t-1 / Revenue_t-1)
    curr_receivable_days = _safe_div(
        current.get("accounts_receivable"), current.get("total_revenue")
    )
    prior_receivable_days = _safe_div(
        p.get("accounts_receivable"), p.get("total_revenue")
    )
    dsri = _safe_div(curr_receivable_days, prior_receivable_days)

    # GMI: Gross Margin Index
    # (GrossProfit_t-1 / Revenue_t-1) / (GrossProfit_t / Revenue_t)
    curr_gm = _safe_div(current.get("gross_profit"), current.get("total_revenue"))
    prior_gm = _safe_div(p.get("gross_profit"), p.get("total_revenue"))
    gmi = _safe_div(prior_gm, curr_gm)

    # AQI: Asset Quality Index
    # (1 - (CurrentAssets_t + PPE_t) / TotalAssets_t) /
    # (1 - (CurrentAssets_t-1 + PPE_t-1) / TotalAssets_t-1)
    curr_aqi_base = 1 - _safe_div(
        (current.get("current_assets", 0) + current.get("fixed_assets", 0)),
        current.get("total_assets", 1)
    )
    prior_aqi_base = 1 - _safe_div(
        (p.get("current_assets", 0) + p.get("fixed_assets", 0)),
        p.get("total_assets", 1)
    )
    aqi = _safe_div(curr_aqi_base, prior_aqi_base)

    # SGI: Sales Growth Index
    # Revenue_t / Revenue_t-1
    sgi = _safe_div(current.get("total_revenue"), p.get("total_revenue"))

    # DEPI: Depreciation Index
    # (Depreciation_t-1 / (Depreciation_t-1 + PPE_t-1)) /
    # (Depreciation_t / (Depreciation_t + PPE_t))
    curr_depi = _safe_div(
        current.get("depreciation_amortization"),
        (current.get("depreciation_amortization", 0) + current.get("fixed_assets", 1))
    )
    prior_depi = _safe_div(
        p.get("depreciation_amortization"),
        (p.get("depreciation_amortization", 0) + p.get("fixed_assets", 1))
    )
    depi = _safe_div(prior_depi, curr_depi)

    # SGAI: SGA Expense Index
    # (SGA_t / Revenue_t) / (SGA_t-1 / Revenue_t-1)
    # We use operating_expenses as proxy for SGA
    curr_sgai = _safe_div(current.get("operating_expenses"), current.get("total_revenue"))
    prior_sgai = _safe_div(p.get("operating_expenses"), p.get("total_revenue"))
    sgai = _safe_div(curr_sgai, prior_sgai)

    # LVGI: Leverage Index
    # ((LTD_t + CurrentLiab_t) / TotalAssets_t) /
    # ((LTD_t-1 + CurrentLiab_t-1) / TotalAssets_t-1)
    curr_lev = _safe_div(
        (current.get("total_debt", 0) + current.get("current_liabilities", 0)),
        current.get("total_assets", 1)
    )
    prior_lev = _safe_div(
        (p.get("total_debt", 0) + p.get("current_liabilities", 0)),
        p.get("total_assets", 1)
    )
    lvgi = _safe_div(curr_lev, prior_lev)

    # TATA: Total Accruals to Total Assets
    # (NetIncome_t - OperatingCashFlow_t) / TotalAssets_t
    net_income = current.get("net_income", 0) or 0
    ocf = current.get("operating_cash_flow", 0) or 0
    total_assets = current.get("total_assets", 1) or 1
    tata = (net_income - ocf) / total_assets

    # ── Compute M-Score ───────────────────────────────────────────────────
    c = BENEISH_COEFFICIENTS
    m_score = (
        c["constant"]
        + c["dsri"]  * dsri
        + c["gmi"]   * gmi
        + c["aqi"]   * aqi
        + c["sgi"]   * sgi
        + c["depi"]  * depi
        + c["sgai"]  * sgai
        + c["lvgi"]  * lvgi
        + c["tata"]  * tata
    )

    # ── Determine signal ──────────────────────────────────────────────────
    if m_score > MANIPULATOR_THRESHOLD:
        signal = "MANIPULATOR"
    elif m_score > SAFE_THRESHOLD:
        signal = "GREY_ZONE"
    else:
        signal = "SAFE"

    # ── Identify red flags ────────────────────────────────────────────────
    variables = {
        "dsri": dsri, "gmi": gmi, "aqi": aqi, "sgi": sgi,
        "depi": depi, "sgai": sgai, "lvgi": lvgi, "tata": tata,
    }
    red_flags = _identify_beneish_red_flags(variables)

    print("\n========== BENEISH DEBUG ==========")
    print("DSRI :", dsri)
    print("GMI  :", gmi)
    print("AQI  :", aqi)
    print("SGI  :", sgi)
    print("DEPI :", depi)
    print("SGAI :", sgai)
    print("LVGI :", lvgi)
    print("TATA :", tata)
    print("M_SCORE :", m_score)
    print("SIGNAL :", signal)
    print("==================================\n")

    return {
        "dsri":  round(dsri, 6),
        "gmi":   round(gmi, 6),
        "aqi":   round(aqi, 6),
        "sgi":   round(sgi, 6),
        "depi":  round(depi, 6),
        "sgai":  round(sgai, 6),
        "lvgi":  round(lvgi, 6),
        "tata":  round(tata, 6),
        "beneish_score":  round(m_score, 6),
        "beneish_signal": signal,
        "red_flags": red_flags,
    }


def _identify_beneish_red_flags(variables: dict) -> list[dict]:
    """
    Check each Beneish variable against its red flag threshold.
    Returns a list of triggered red flags with descriptions.
    """
    flags = []

    for var_name, value in variables.items():
        threshold_info = RED_FLAG_THRESHOLDS.get(var_name)
        if not threshold_info:
            continue

        threshold = threshold_info["threshold"]
        direction = threshold_info["direction"]

        triggered = (
            (direction == "above" and value > threshold) or
            (direction == "below" and value < threshold)
        )

        if triggered:
            severity = "HIGH" if abs(value - threshold) / threshold > 0.2 else "MEDIUM"
            flags.append({
                "source": "BENEISH",
                "variable": var_name.upper(),
                "value": round(value, 4),
                "threshold": threshold,
                "severity": severity,
                "description": threshold_info["description"],
            })

    return flags