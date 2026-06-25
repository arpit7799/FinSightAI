# tests/unit/test_ratio_calculator.py
"""
Unit tests for the ratio calculator.
No database or PDF needed — just pass a dict of financial data.
"""

import pytest
from app.engines.financial.ratio_calculator import RatioCalculator, _safe_divide, _get_signal


# Sample financial data based on a typical IT services company
SAMPLE_DATA = {
    "total_revenue": 2_250_000_000,
    "cost_of_goods_sold": 1_350_000_000,
    "gross_profit": 900_000_000,
    "ebitda": 495_000_000,
    "ebit": 450_000_000,
    "net_income": 380_000_000,
    "interest_expense": 30_000_000,
    "total_assets": 3_200_000_000,
    "total_equity": 2_800_000_000,
    "total_debt": 200_000_000,
    "current_assets": 1_800_000_000,
    "current_liabilities": 700_000_000,
    "cash_and_equivalents": 500_000_000,
    "inventory": 50_000_000,
    "accounts_receivable": 600_000_000,
}


class TestSafeDivide:

    def test_normal_division(self):
        assert _safe_divide(100, 4) == 25.0

    def test_returns_none_for_zero_denominator(self):
        assert _safe_divide(100, 0) is None

    def test_returns_none_if_numerator_is_none(self):
        assert _safe_divide(None, 100) is None

    def test_returns_none_if_denominator_is_none(self):
        assert _safe_divide(100, None) is None

    def test_rounds_to_4_decimal_places(self):
        result = _safe_divide(1, 3)
        assert result == 0.3333


class TestGetSignal:

    def test_good_current_ratio(self):
        assert _get_signal("Current Ratio", 2.5) == "GOOD"

    def test_warning_current_ratio(self):
        assert _get_signal("Current Ratio", 1.2) == "WARNING"

    def test_critical_current_ratio(self):
        assert _get_signal("Current Ratio", 0.8) == "CRITICAL"

    def test_good_debt_to_equity(self):
        # Lower is better for debt ratios
        assert _get_signal("Debt to Equity", 0.5) == "GOOD"

    def test_critical_debt_to_equity(self):
        assert _get_signal("Debt to Equity", 3.0) == "CRITICAL"

    def test_unknown_ratio_returns_neutral(self):
        assert _get_signal("Some Unknown Ratio", 100) == "NEUTRAL"

    def test_none_value_returns_neutral(self):
        assert _get_signal("Current Ratio", None) == "NEUTRAL"


class TestRatioCalculator:

    def setup_method(self):
        self.calc = RatioCalculator(SAMPLE_DATA)

    def test_returns_18_ratios(self):
        ratios = self.calc.calculate_all()
        assert len(ratios) == 18

    def test_current_ratio_correct(self):
        ratios = self.calc.calculate_all()
        current_ratio = next(r for r in ratios if r["ratio_name"] == "Current Ratio")
        expected = round(1_800_000_000 / 700_000_000, 4)
        assert current_ratio["computed_value"] == expected
        assert current_ratio["signal"] == "GOOD"

    def test_quick_ratio_subtracts_inventory(self):
        ratios = self.calc.calculate_all()
        quick = next(r for r in ratios if r["ratio_name"] == "Quick Ratio")
        expected = round((1_800_000_000 - 50_000_000) / 700_000_000, 4)
        assert quick["computed_value"] == expected

    def test_roe_correct(self):
        ratios = self.calc.calculate_all()
        roe = next(r for r in ratios if r["ratio_name"] == "Return on Equity")
        expected = round(380_000_000 / 2_800_000_000, 4)
        assert roe["computed_value"] == expected

    def test_net_margin_correct(self):
        ratios = self.calc.calculate_all()
        margin = next(r for r in ratios if r["ratio_name"] == "Net Profit Margin")
        expected = round(380_000_000 / 2_250_000_000, 4)
        assert margin["computed_value"] == expected

    def test_ratios_have_required_fields(self):
        ratios = self.calc.calculate_all()
        required_fields = ["ratio_category", "ratio_name", "formula",
                          "computed_value", "signal", "interpretation"]
        for ratio in ratios:
            for field in required_fields:
                assert field in ratio, f"Missing field {field} in ratio {ratio['ratio_name']}"

    def test_missing_data_returns_none_not_error(self):
        # Should not crash if financial data is missing
        calc = RatioCalculator({"total_revenue": 1000000})
        ratios = calc.calculate_all()
        # Should still return 18 ratios, just with None values
        assert len(ratios) == 18

    def test_all_categories_present(self):
        ratios = self.calc.calculate_all()
        categories = {r["ratio_category"] for r in ratios}
        assert categories == {"LIQUIDITY", "PROFITABILITY", "LEVERAGE", "EFFICIENCY", "MARKET"}

    def test_benchmark_values_populated(self):
        ratios = self.calc.calculate_all()
        # Liquidity ratios should all have benchmarks
        liquidity = [r for r in ratios if r["ratio_category"] == "LIQUIDITY"]
        for r in liquidity:
            assert r["benchmark_value"] is not None
            assert r["benchmark_source"] is not None