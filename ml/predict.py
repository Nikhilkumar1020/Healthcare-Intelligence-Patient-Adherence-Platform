"""
ml/predict.py
Generates risk predictions for all patients and writes to risk_predictions table.

Risk score → Risk level mapping:
  >= 0.65 → HIGH
  >= 0.40 → MEDIUM
  <  0.40 → LOW

Top factor explanation:
  Rule-based feature contribution (transparent, not SHAP)
  based on the patient's most anomalous feature values.

Usage:
    python ml/predict.py
"""
import sys
import json
import logging
from pathlib import Path
from datetime import date, datetime
from typing import Dict

import numpy as np
import pandas as pd
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from ml.features import build_features, FEATURE_COLS, TARGET_COL, FEATURE_CUTOFF
from ml.model_utils import load_model, load_model_metadata
from ml.model_utils import load_model, load_model_metadata

SCHEMA = "healthcare.healthcare"
HIGH_THRESHOLD   = 0.65
MEDIUM_THRESHOLD = 0.40


def score_to_level(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    elif score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def explain_risk(row: pd.Series) -> str:
    """
    Generate a transparent, rule-based explanation for a patient's risk score.
    Returns human-readable top factor string.
    """
    reasons = []

    if row.get("missed_refills", 0) >= 3:
        reasons.append(f"missed {int(row['missed_refills'])} previous refills")
    elif row.get("missed_refills", 0) >= 1:
        reasons.append(f"has {int(row['missed_refills'])} previous missed refill(s)")

    if row.get("days_since_last_refill", 0) > 60:
        reasons.append(f"{int(row['days_since_last_refill'])} days since last refill")

    if row.get("avg_refill_gap", 0) > 45:
        reasons.append(f"average refill gap of {int(row['avg_refill_gap'])} days")

    if row.get("gap_trend", 0) > 0:
        reasons.append("increasing refill gap trend")

    if row.get("adherence_pct", 100) < 60:
        reasons.append(f"low adherence ({row['adherence_pct']:.0f}%)")

    if row.get("engagements_90d", 0) < 2:
        reasons.append("low recent engagement (last 90 days)")

    if row.get("is_senior", 0) == 1:
        reasons.append("senior patient (age ≥ 65)")

    if not reasons:
        reasons.append("multiple moderate risk signals")

    # Return top 2 factors
    return "; ".join(reasons[:2])


def generate_predictions(cutoff: date = FEATURE_CUTOFF) -> pd.DataFrame:
    """Generate risk predictions for all patients."""
    logger.info("[predict] Loading model...")
    try:
        model = load_model("champion")
        meta  = load_model_metadata("champion")
    except FileNotFoundError:
        logger.error("[predict] No trained model found. Run `python ml/train.py` first.")
        raise

    model_version = meta.get("version", "v1.0")

    logger.info("[predict] Building features...")
    df = build_features(cutoff)

    X = df[FEATURE_COLS].values

    logger.info("[predict] Generating risk scores...")
    scores = model.predict_proba(X)[:, 1]

    df["risk_score"] = scores
    df["risk_level"] = [score_to_level(s) for s in scores]
    df["top_factor"]  = df.apply(explain_risk, axis=1)
    df["model_version"] = model_version
    df["prediction_date"] = date.today().isoformat()

    # Prediction ID
    df["prediction_id"] = [f"PRED{i+1:08d}" for i in range(len(df))]

    dist = df["risk_level"].value_counts()
    logger.info(f"[predict] Risk distribution: "
                f"HIGH={dist.get('HIGH',0)}, "
                f"MEDIUM={dist.get('MEDIUM',0)}, "
                f"LOW={dist.get('LOW',0)}")
    return df


def write_predictions(df: pd.DataFrame) -> int:
    """Write predictions to risk_predictions table."""
    cols = ["prediction_id","patient_id","prediction_date","risk_score",
            "risk_level","top_factor","model_version"]

    rows = []
    for _, row in df[cols].iterrows():
        rows.append((
            row["prediction_id"],
            row["patient_id"],
            row["prediction_date"],
            float(row["risk_score"]),
            row["risk_level"],
            row["top_factor"],
            row["model_version"],
        ))

    try:
        conn = duckdb.connect("healthcare.duckdb")
        conn.execute("SET schema = 'healthcare'")
        conn.register('df_preds', df[cols])
        conn.execute(f"INSERT OR IGNORE INTO {SCHEMA}.risk_predictions SELECT * FROM df_preds")
        conn.unregister('df_preds')
        conn.close()
        logger.info(f"[predict] Wrote {len(df)} predictions to database")
        return len(df)
    except Exception as e:
        logger.error(f"[predict] DB write failed: {e}")
        return 0


def predict_patient(patient_id: str) -> Dict:
    """Generate a single-patient prediction (for API use)."""
    df = generate_predictions()
    row = df[df["patient_id"] == patient_id]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "patient_id":    patient_id,
        "risk_score":    round(float(r["risk_score"]), 4),
        "risk_level":    r["risk_level"],
        "top_factor":    r["top_factor"],
        "model_version": r["model_version"],
        "prediction_date": r["prediction_date"],
    }


if __name__ == "__main__":
    predictions_df = generate_predictions()
    write_predictions(predictions_df)
    logger.info("[predict] Done.")
