"""tests/test_ml.py — ML feature engineering and prediction tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest
import pandas as pd
import numpy as np
from ml.predict import score_to_level, explain_risk


class TestRiskScoring:
    def test_high_risk_threshold(self):
        assert score_to_level(0.80) == "HIGH"
        assert score_to_level(0.65) == "HIGH"

    def test_medium_risk_threshold(self):
        assert score_to_level(0.55) == "MEDIUM"
        assert score_to_level(0.40) == "MEDIUM"

    def test_low_risk_threshold(self):
        assert score_to_level(0.39) == "LOW"
        assert score_to_level(0.10) == "LOW"
        assert score_to_level(0.0) == "LOW"

    def test_boundary_conditions(self):
        assert score_to_level(0.65) == "HIGH"
        assert score_to_level(0.64) == "MEDIUM"
        assert score_to_level(0.40) == "MEDIUM"
        assert score_to_level(0.399) == "LOW"


class TestExplainRisk:
    def test_missed_refills_explanation(self):
        row = pd.Series({"missed_refills": 3, "days_since_last_refill": 20,
                         "avg_refill_gap": 30, "gap_trend": 0,
                         "adherence_pct": 80, "engagements_90d": 5, "is_senior": 0})
        explanation = explain_risk(row)
        assert "missed" in explanation.lower()

    def test_long_gap_explanation(self):
        row = pd.Series({"missed_refills": 0, "days_since_last_refill": 90,
                         "avg_refill_gap": 30, "gap_trend": 0,
                         "adherence_pct": 80, "engagements_90d": 5, "is_senior": 0})
        explanation = explain_risk(row)
        assert "days" in explanation.lower() or "refill" in explanation.lower()

    def test_no_crash_on_empty_row(self):
        row = pd.Series({})
        # Should not crash, returns default message
        result = explain_risk(row)
        assert isinstance(result, str)
        assert len(result) > 0


class TestFeatureCols:
    def test_feature_cols_exist(self):
        from ml.features import FEATURE_COLS, TARGET_COL
        assert len(FEATURE_COLS) >= 20
        assert TARGET_COL == "future_refill_dropoff"
        assert "total_refills" in FEATURE_COLS
        assert "adherence_pct" in FEATURE_COLS
        assert "avg_refill_gap" in FEATURE_COLS
