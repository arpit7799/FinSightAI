# app/engines/financial/ratio_calculator.py
"""
Computes all 18 financial ratios from normalized financial statement data.

Input:  flat dict of financial values (from DataNormalizer)
Output: list of computed ratio dicts ready to save as FinancialRatio records

The normalized_data dict keys come from data_normalizer.py — things like
total_revenue, net_income, total_assets, current_assets, etc.
"""


# Industry benchmarks for IT Services sector (TCS, Infosys, Wipro, HCL)
# These are approximate averages — good enough for a portfolio project
IT_SERVICES_BENCHMARKS = {
    "Current Ratio":          {"value": 2.0,  "source": "IT Services India avg"},
    "Quick Ratio":            {"value": 1.8,  "source": "IT Services India avg"},
    "Cash Ratio":             {"value": 0.5,  "source": "IT Services India avg"},
    "Return on Equity":       {"value": 0.25, "source": "IT Services India avg"},
    "Return on Assets":       {"value": 0.15, "source": "IT Services India avg"},
    "Gross Margin":           {"value": 0.30, "source": "IT Services India avg"},
    "EBITDA Margin":          {"value": 0.22, "source": "IT Services India avg"},
    "Net Profit Margin":      {"value": 0.18, "source": "IT Services India avg"},
    "Debt to Equity":         {"value": 0.1,  "source": "IT Services India avg"},
    "Debt to Assets":         {"value": 0.05, "source": "IT Services India avg"},
    "Interest Coverage":      {"value": 15.0, "source": "IT Services India avg"},
    "Asset Turnover":         {"value": 0.85, "source": "IT Services India avg"},
    "Inventory Turnover":     {"value": 20.0, "source": "IT Services India avg"},
    "Receivable Turnover":    {"value": 5.0,  "source": "IT Services India avg"},
    "Earnings Per Share":     {"value": None, "source": "Company specific"},
    "Price to Earnings":      {"value": 25.0, "source": "IT Services India avg"},
    "Price to Book":          {"value": 5.0,  "source": "IT Services India avg"},
    "Dividend Yield":         {"value": 0.02, "source": "IT Services India avg"},
}


def _safe_divide(numerator, denominator):
    """Divide two numbers safely — returns None if denominator is 0 or missing."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _get_signal(ratio_name: str, value: float) -> str:
    """
    Returns GOOD, WARNING, or CRITICAL based on the ratio value.
    Each ratio has different logic — some are better when high, some when low.
    """
    if value is None:
        return "NEUTRAL"

    # Thresholds: (warning_threshold, critical_threshold, higher_is_better)
    thresholds = {
        "Current Ratio":       (1.5, 1.0, True),
        "Quick Ratio":         (1.0, 0.5, True),
        "Cash Ratio":          (0.2, 0.1, True),
        "Return on Equity":    (0.10, 0.05, True),
        "Return on Assets":    (0.05, 0.02, True),
        "Gross Margin":        (0.20, 0.10, True),
        "EBITDA Margin":       (0.10, 0.05, True),
        "Net Profit Margin":   (0.05, 0.02, True),
        "Debt to Equity":      (1.0, 2.0, False),   # lower is better
        "Debt to Assets":      (0.5, 0.7, False),   # lower is better
        "Interest Coverage":   (3.0, 1.5, True),
        "Asset Turnover":      (0.5, 0.3, True),
        "Inventory Turnover":  (4.0, 2.0, True),
        "Receivable Turnover": (4.0, 2.0, True),
    }

    if ratio_name not in thresholds:
        return "NEUTRAL"

    warning, critical, higher_is_better = thresholds[ratio_name]

    if higher_is_better:
        if value >= warning:
            return "GOOD"
        elif value >= critical:
            return "WARNING"
        else:
            return "CRITICAL"
    else:
        # Lower is better (debt ratios)
        if value <= warning:
            return "GOOD"
        elif value <= critical:
            return "WARNING"
        else:
            return "CRITICAL"


def _get_interpretation(ratio_name: str, value: float, signal: str) -> str:
    """Returns a simple human-readable interpretation of the ratio value."""
    if value is None:
        return "Could not be calculated — required data missing from financial statements."

    interpretations = {
        "Current Ratio": {
            "GOOD": f"Current ratio of {value:.2f} indicates strong ability to meet short-term obligations.",
            "WARNING": f"Current ratio of {value:.2f} is below ideal. Short-term liquidity needs monitoring.",
            "CRITICAL": f"Current ratio of {value:.2f} is dangerously low. Company may struggle to pay current liabilities.",
        },
        "Quick Ratio": {
            "GOOD": f"Quick ratio of {value:.2f} shows company can cover short-term liabilities without selling inventory.",
            "WARNING": f"Quick ratio of {value:.2f} suggests limited liquid assets relative to current liabilities.",
            "CRITICAL": f"Quick ratio of {value:.2f} indicates serious liquidity concerns.",
        },
        "Return on Equity": {
            "GOOD": f"ROE of {value:.1%} shows strong returns for shareholders.",
            "WARNING": f"ROE of {value:.1%} is below industry average. Returns could be improved.",
            "CRITICAL": f"ROE of {value:.1%} is very low, indicating poor use of shareholder capital.",
        },
        "Return on Assets": {
            "GOOD": f"ROA of {value:.1%} shows efficient use of company assets.",
            "WARNING": f"ROA of {value:.1%} is below peers. Asset utilization could improve.",
            "CRITICAL": f"ROA of {value:.1%} indicates very poor asset efficiency.",
        },
        "Net Profit Margin": {
            "GOOD": f"Net margin of {value:.1%} is healthy — company retains good profit from revenue.",
            "WARNING": f"Net margin of {value:.1%} is thin. Profitability is under pressure.",
            "CRITICAL": f"Net margin of {value:.1%} is very low or negative — serious profitability concern.",
        },
        "Debt to Equity": {
            "GOOD": f"D/E ratio of {value:.2f} shows low financial leverage — conservative capital structure.",
            "WARNING": f"D/E ratio of {value:.2f} shows moderate leverage. Monitor debt levels.",
            "CRITICAL": f"D/E ratio of {value:.2f} is very high — company is heavily debt-financed.",
        },
        "Interest Coverage": {
            "GOOD": f"Interest coverage of {value:.1f}x means earnings comfortably cover interest payments.",
            "WARNING": f"Interest coverage of {value:.1f}x is low — interest payments are a significant burden.",
            "CRITICAL": f"Interest coverage of {value:.1f}x is dangerously low — risk of debt default.",
        },
    }

    if ratio_name in interpretations and signal in interpretations[ratio_name]:
        return interpretations[ratio_name][signal]

    # Generic fallback
    return f"{ratio_name} is {value:.4f}. Signal: {signal}."


class RatioCalculator:
    """
    Calculates all 18 financial ratios from a normalized data dict.

    Usage:
        data = {"total_revenue": 1250000, "net_income": 198000, ...}
        calculator = RatioCalculator(data)
        ratios = calculator.calculate_all()
    """

    def __init__(self, normalized_data: dict):
        self.d = normalized_data  # short alias for readability

    def _get(self, key: str):
        """Get a value from normalized data, return None if missing."""
        return self.d.get(key)

    def calculate_all(self) -> list[dict]:
        """
        Calculate all 18 ratios and return as a list of dicts.
        Each dict maps directly to a FinancialRatio model row.
        """
        ratios = []
        ratios += self._liquidity_ratios()
        ratios += self._profitability_ratios()
        ratios += self._leverage_ratios()
        ratios += self._efficiency_ratios()
        ratios += self._market_ratios()
        return ratios

    def _make_ratio(self, category: str, name: str, formula: str, value) -> dict:
        """Helper that builds a ratio dict with signal and interpretation."""
        signal = _get_signal(name, value)
        benchmark = IT_SERVICES_BENCHMARKS.get(name, {})

        return {
            "ratio_category": category,
            "ratio_name": name,
            "formula": formula,
            "computed_value": value,
            "benchmark_value": benchmark.get("value"),
            "benchmark_source": benchmark.get("source"),
            "signal": signal,
            "interpretation": _get_interpretation(name, value, signal),
        }

    # ── Liquidity Ratios ──────────────────────────────────────────────────

    def _liquidity_ratios(self) -> list[dict]:
        current_assets = self._get("current_assets")
        current_liabilities = self._get("current_liabilities")
        inventory = self._get("inventory") or 0
        cash = self._get("cash_and_equivalents")

        return [
            self._make_ratio(
                "LIQUIDITY", "Current Ratio",
                "Current Assets / Current Liabilities",
                _safe_divide(current_assets, current_liabilities),
            ),
            self._make_ratio(
                "LIQUIDITY", "Quick Ratio",
                "(Current Assets - Inventory) / Current Liabilities",
                _safe_divide(
                    (current_assets - inventory) if current_assets else None,
                    current_liabilities
                ),
            ),
            self._make_ratio(
                "LIQUIDITY", "Cash Ratio",
                "Cash & Equivalents / Current Liabilities",
                _safe_divide(cash, current_liabilities),
            ),
        ]

    # ── Profitability Ratios ──────────────────────────────────────────────

    def _profitability_ratios(self) -> list[dict]:
        net_income = self._get("net_income")
        total_equity = self._get("total_equity")
        total_assets = self._get("total_assets")
        total_revenue = self._get("total_revenue")
        gross_profit = self._get("gross_profit")
        ebitda = self._get("ebitda")

        return [
            self._make_ratio(
                "PROFITABILITY", "Return on Equity",
                "Net Income / Total Equity",
                _safe_divide(net_income, total_equity),
            ),
            self._make_ratio(
                "PROFITABILITY", "Return on Assets",
                "Net Income / Total Assets",
                _safe_divide(net_income, total_assets),
            ),
            self._make_ratio(
                "PROFITABILITY", "Gross Margin",
                "Gross Profit / Total Revenue",
                _safe_divide(gross_profit, total_revenue),
            ),
            self._make_ratio(
                "PROFITABILITY", "EBITDA Margin",
                "EBITDA / Total Revenue",
                _safe_divide(ebitda, total_revenue),
            ),
            self._make_ratio(
                "PROFITABILITY", "Net Profit Margin",
                "Net Income / Total Revenue",
                _safe_divide(net_income, total_revenue),
            ),
        ]

    # ── Leverage Ratios ───────────────────────────────────────────────────

    def _leverage_ratios(self) -> list[dict]:
        total_debt = self._get("total_debt")
        total_equity = self._get("total_equity")
        total_assets = self._get("total_assets")
        ebit = self._get("ebit") or self._get("ebitda")  # fallback to ebitda
        interest_expense = self._get("interest_expense")

        return [
            self._make_ratio(
                "LEVERAGE", "Debt to Equity",
                "Total Debt / Total Equity",
                _safe_divide(total_debt, total_equity),
            ),
            self._make_ratio(
                "LEVERAGE", "Debt to Assets",
                "Total Debt / Total Assets",
                _safe_divide(total_debt, total_assets),
            ),
            self._make_ratio(
                "LEVERAGE", "Interest Coverage",
                "EBIT / Interest Expense",
                _safe_divide(ebit, interest_expense),
            ),
        ]

    # ── Efficiency Ratios ─────────────────────────────────────────────────

    def _efficiency_ratios(self) -> list[dict]:
        total_revenue = self._get("total_revenue")
        total_assets = self._get("total_assets")
        inventory = self._get("inventory")
        cogs = self._get("cost_of_goods_sold")
        accounts_receivable = self._get("accounts_receivable")

        return [
            self._make_ratio(
                "EFFICIENCY", "Asset Turnover",
                "Total Revenue / Total Assets",
                _safe_divide(total_revenue, total_assets),
            ),
            self._make_ratio(
                "EFFICIENCY", "Inventory Turnover",
                "Cost of Goods Sold / Inventory",
                _safe_divide(cogs, inventory),
            ),
            self._make_ratio(
                "EFFICIENCY", "Receivable Turnover",
                "Total Revenue / Accounts Receivable",
                _safe_divide(total_revenue, accounts_receivable),
            ),
        ]

    # ── Market Ratios ─────────────────────────────────────────────────────

    def _market_ratios(self) -> list[dict]:
        eps = self._get("eps")
        net_income = self._get("net_income")

        # Market ratios need share price which we don't have from the PDF
        # We calculate what we can and mark the rest as NEUTRAL
        return [
            self._make_ratio(
                "MARKET", "Earnings Per Share",
                "Net Income / Shares Outstanding",
                eps,  # Only available if explicitly in the filing
            ),
            self._make_ratio(
                "MARKET", "Price to Earnings",
                "Market Price / EPS",
                None,  # Needs live market price — not in annual report
            ),
            self._make_ratio(
                "MARKET", "Price to Book",
                "Market Price / Book Value Per Share",
                None,  # Needs live market price
            ),
            self._make_ratio(
                "MARKET", "Dividend Yield",
                "Dividend Per Share / Market Price",
                None,  # Needs live market price
            ),
        ]