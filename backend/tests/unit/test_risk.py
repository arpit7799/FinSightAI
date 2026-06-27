# tests/unit/test_risk.py
"""
Unit tests for the Risk Prediction Engine.
No real models or database needed.
"""

import pytest
from app.engines.risk.feature_engineer import (
    build_feature_vector,
    features_to_list,
    FEATURE_NAMES,
    FEATURE_DEFAULTS,
)
from app.engines.risk.risk_scorer import _get_risk_class


# ── Fake ratio objects ────────────────────────────────────────────────────────

class FakeRatio:
    """Mimics a FinancialRatio model object."""
    def __init__(self, name, value):
        self.ratio_name = name
        self.computed_value = value


# ── Feature Engineer tests ────────────────────────────────────────────────────

class TestFeatureEngineer:

    def test_returns_all_8_features(self):
        ratios = [
            FakeRatio("Return on Equity", 0.20),
            FakeRatio("Current Ratio", 2.1),
        ]
        features = build_feature_vector(ratios, {})
        assert len(features) == len(FEATURE_NAMES)
        for name in FEATURE_NAMES:
            assert name in features

    def test_maps_roe_correctly(self):
        ratios = [FakeRatio("Return on Equity", 0.25)]
        features = build_feature_vector(ratios, {})
        assert features["roe"] == 0.25

    def test_maps_current_ratio_correctly(self):
        ratios = [FakeRatio("Current Ratio", 1.8)]
        features = build_feature_vector(ratios, {})
        assert features["current_ratio"] == 1.8

    def test_uses_defaults_for_missing_ratios(self):
        features = build_feature_vector([], {})
        assert features["roe"] == FEATURE_DEFAULTS["roe"]
        assert features["debt_to_equity"] == FEATURE_DEFAULTS["debt_to_equity"]

    def test_computes_cash_flow_margin_from_normalized(self):
        normalized = {
            "operating_cash_flow": 200_000,
            "total_revenue": 1_000_000,
        }
        features = build_feature_vector([], normalized)
        assert features["cash_flow_margin"] == 0.2

    def test_features_to_list_correct_order(self):
        features = {name: float(i) for i, name in enumerate(FEATURE_NAMES)}
        result = features_to_list(features)
        assert result == [float(i) for i in range(len(FEATURE_NAMES))]

    def test_features_to_list_length(self):
        features = build_feature_vector([], {})
        result = features_to_list(features)
        assert len(result) == 8

    def test_none_ratio_value_uses_default(self):
        ratios = [FakeRatio("Return on Equity", None)]
        features = build_feature_vector(ratios, {})
        # None value should fall back to default
        assert features["roe"] == FEATURE_DEFAULTS["roe"]


# ── Risk Class tests ──────────────────────────────────────────────────────────

class TestRiskClass:

    def test_score_0_is_low(self):
        assert _get_risk_class(0) == "LOW"

    def test_score_15_is_low(self):
        assert _get_risk_class(15) == "LOW"

    def test_score_30_is_medium(self):
        assert _get_risk_class(30) == "MEDIUM"

    def test_score_45_is_medium(self):
        assert _get_risk_class(45) == "MEDIUM"

    def test_score_60_is_high(self):
        assert _get_risk_class(60) == "HIGH"

    def test_score_75_is_high(self):
        assert _get_risk_class(75) == "HIGH"

    def test_score_80_is_critical(self):
        assert _get_risk_class(80) == "CRITICAL"

    def test_score_95_is_critical(self):
        assert _get_risk_class(95) == "CRITICAL"