"""
ml/features.py
Feature engineering pipeline for patient refill drop-off prediction.

Target definition:
  future_refill_dropoff = 1 if the patient does NOT refill within
  (expected_refill_date + 30 days) for any active prescription.

Features computed:
  - patient demographics (age, insurance, region, chronic_condition)
  - refill behavior (total refills, missed refills, avg gap, max gap)
  - temporal features (days since last refill, refill frequency)
  - adherence percentage
  - engagement features (total, recent 30/90 day)
  - prescription features (# prescriptions, refill_allowed)
  - trend features (early vs recent gap comparison)

No data leakage: features are computed from historical data only,
target is computed from future refill events.
"""

import sys
import logging
from pathlib import Path
from datetime import date, timedelta
from typing import Optional
import pandas as pd
import numpy as np
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)
SCHEMA = "healthcare.healthcare"

# Cutoff date: features computed up to this date, target is after this date
FEATURE_CUTOFF = date(2024, 1, 1)
TARGET_WINDOW  = 30  # days after expected refill date


def _load(sql: str) -> pd.DataFrame:
    try:
        conn = duckdb.connect("healthcare.duckdb")
        conn.execute("SET schema = 'healthcare'")
        df = conn.execute(sql).df()
        conn.close()
        return df
    except Exception as e:
        logger.error(f"[features] SQL failed: {e}")
        raise


def build_features(cutoff: date = FEATURE_CUTOFF) -> pd.DataFrame:
    """
    Build ML feature matrix.
    Returns DataFrame with patient_id, all features, and target label.
    """
    cutoff_str = cutoff.isoformat()
    future_str = (cutoff + timedelta(days=90)).isoformat()

    # ── 1. Patient demographics ────────────────────────────
    patients_sql = f"""
    SELECT patient_id, age, gender, region, insurance_type, chronic_condition,
           CURRENT_DATE - enrollment_date AS days_since_enrollment
    FROM {SCHEMA}.patients
    """
    patients_df = _load(patients_sql)

    # ── 2. Refill features (historical, before cutoff) ─────
    refills_sql = f"""
    SELECT
        r.patient_id,
        COUNT(*) AS total_refills,
        SUM(CASE WHEN NOT r.was_on_time THEN 1 ELSE 0 END) AS missed_refills,
        MAX(r.refill_date) AS last_refill_date,
        MIN(r.refill_date) AS first_refill_date,
        CURRENT_DATE - MAX(r.refill_date) AS days_since_last_refill
    FROM {SCHEMA}.refills r
    WHERE r.refill_date < '{cutoff_str}'
    GROUP BY r.patient_id
    """
    refills_df = _load(refills_sql)

    # ── 3. Refill gap features ─────────────────────────────
    gap_sql = f"""
    WITH ordered AS (
        SELECT patient_id, refill_date,
               refill_date - LAG(refill_date) OVER (
                   PARTITION BY patient_id ORDER BY refill_date
               ) AS gap_days,
               ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY refill_date) AS rn,
               COUNT(*) OVER (PARTITION BY patient_id) AS total_cnt
        FROM {SCHEMA}.refills
        WHERE refill_date < '{cutoff_str}'
    ),
    gap_stats AS (
        SELECT
            patient_id,
            ROUND(AVG(gap_days)::numeric, 1) AS avg_refill_gap,
            MAX(gap_days) AS max_refill_gap,
            MIN(gap_days) AS min_refill_gap,
            STDDEV(gap_days) AS stddev_gap,
            AVG(CASE WHEN rn <= total_cnt / 2 THEN gap_days END) AS early_avg_gap,
            AVG(CASE WHEN rn > total_cnt / 2 THEN gap_days END)  AS recent_avg_gap
        FROM ordered
        WHERE gap_days IS NOT NULL AND gap_days > 0
        GROUP BY patient_id
    )
    SELECT * FROM gap_stats
    """
    gap_df = _load(gap_sql)

    # ── 4. Engagement features ─────────────────────────────
    eng_sql = f"""
    SELECT
        patient_id,
        COUNT(*) AS total_engagements,
        COUNT(*) FILTER (WHERE engagement_date >= DATE '{cutoff_str}' - INTERVAL '30 days') AS engagements_30d,
        COUNT(*) FILTER (WHERE engagement_date >= DATE '{cutoff_str}' - INTERVAL '90 days') AS engagements_90d,
        COUNT(*) FILTER (WHERE response = 'Responded') AS responded_count,
        COUNT(*) FILTER (WHERE response = 'No Response') AS no_response_count
    FROM {SCHEMA}.engagements
    WHERE engagement_date < '{cutoff_str}'
    GROUP BY patient_id
    """
    eng_df = _load(eng_sql)

    # ── 5. Prescription features ───────────────────────────
    rx_sql = f"""
    SELECT
        patient_id,
        COUNT(*) AS total_prescriptions,
        AVG(refill_allowed) AS avg_refills_allowed,
        MAX(prescription_date) AS last_prescription_date
    FROM {SCHEMA}.prescriptions
    WHERE prescription_date < '{cutoff_str}'
    GROUP BY patient_id
    """
    rx_df = _load(rx_sql)

    # ── 6. TARGET: missed next refill after cutoff ─────────
    # A patient is a positive case if their MOST RECENT prescription's
    # expected next refill (based on last refill + days_supply)
    # does not occur within the target window
    target_sql = f"""
    WITH last_refill_per_patient AS (
        SELECT DISTINCT ON (patient_id)
            patient_id,
            refill_date AS last_refill,
            medication_id
        FROM {SCHEMA}.refills
        WHERE refill_date < '{cutoff_str}'
        ORDER BY patient_id, refill_date DESC
    ),
    expected_dates AS (
        SELECT
            lrp.patient_id,
            lrp.last_refill + COALESCE(px.days_supply, 30) AS expected_next_refill
        FROM last_refill_per_patient lrp
        LEFT JOIN LATERAL (
            SELECT days_supply FROM {SCHEMA}.prescriptions
            WHERE patient_id = lrp.patient_id AND medication_id = lrp.medication_id
            ORDER BY prescription_date DESC LIMIT 1
        ) px ON true
    ),
    actual_next AS (
        SELECT
            r.patient_id,
            MIN(r.refill_date) AS actual_next_refill
        FROM {SCHEMA}.refills r
        WHERE r.refill_date >= '{cutoff_str}'
        GROUP BY r.patient_id
    )
    SELECT
        ed.patient_id,
        ed.expected_next_refill,
        an.actual_next_refill,
        CASE
            WHEN an.actual_next_refill IS NULL THEN 1
            WHEN an.actual_next_refill > ed.expected_next_refill + INTERVAL '{TARGET_WINDOW} days' THEN 1
            ELSE 0
        END AS future_refill_dropoff
    FROM expected_dates ed
    LEFT JOIN actual_next an ON ed.patient_id = an.patient_id
    """
    target_df = _load(target_sql)

    # ── Merge everything ───────────────────────────────────
    df = patients_df.copy()
    df = df.merge(refills_df, on="patient_id", how="left")
    df = df.merge(gap_df, on="patient_id", how="left")
    df = df.merge(eng_df, on="patient_id", how="left")
    df = df.merge(rx_df, on="patient_id", how="left")
    df = df.merge(target_df[["patient_id","future_refill_dropoff"]], on="patient_id", how="left")

    # ── Fill NAs ───────────────────────────────────────────
    numeric_defaults = {
        "total_refills": 0, "missed_refills": 0, "days_since_last_refill": 365,
        "avg_refill_gap": 60, "max_refill_gap": 0, "min_refill_gap": 0,
        "stddev_gap": 0, "early_avg_gap": 60, "recent_avg_gap": 60,
        "total_engagements": 0, "engagements_30d": 0, "engagements_90d": 0,
        "responded_count": 0, "no_response_count": 0,
        "total_prescriptions": 0, "avg_refills_allowed": 0,
        "days_since_enrollment": 0,
    }
    for col, val in numeric_defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)

    # ── Engineered features ────────────────────────────────
    df["adherence_pct"] = np.where(
        df["total_refills"] > 0,
        100.0 * (df["total_refills"] - df["missed_refills"]) / df["total_refills"],
        50.0
    )
    df["miss_rate_pct"] = np.where(
        df["total_refills"] > 0,
        100.0 * df["missed_refills"] / df["total_refills"],
        50.0
    )
    df["gap_trend"] = np.where(
        df["recent_avg_gap"] > df["early_avg_gap"] * 1.2, 1,
        np.where(df["recent_avg_gap"] < df["early_avg_gap"] * 0.8, -1, 0)
    )
    df["engagement_response_rate"] = np.where(
        df["total_engagements"] > 0,
        df["responded_count"] / df["total_engagements"],
        0
    )

    # ── Encode categoricals ────────────────────────────────
    df["age_group"] = pd.cut(df["age"],
                              bins=[0, 30, 45, 60, 75, 200],
                              labels=[0, 1, 2, 3, 4]).astype(int)
    df["is_senior"] = (df["age"] >= 65).astype(int)

    region_map = {"North": 0, "South": 1, "East": 2, "West": 3, "Central": 4}
    df["region_encoded"] = df["region"].map(region_map).fillna(0).astype(int)

    insurance_map = {"Private": 0, "Medicare": 1, "Medicaid": 2, "Uninsured": 3, "VA": 4}
    df["insurance_encoded"] = df["insurance_type"].map(insurance_map).fillna(0).astype(int)

    df["has_chronic"] = (df["chronic_condition"] != "None").astype(int)

    # Target: default 0 if never had a refill
    df["future_refill_dropoff"] = df["future_refill_dropoff"].fillna(1).astype(int)

    logger.info(f"[features] Built feature matrix: {len(df)} patients, "
                f"drop-off rate = {df['future_refill_dropoff'].mean():.2%}")
    return df


FEATURE_COLS = [
    "age", "age_group", "is_senior", "region_encoded", "insurance_encoded", "has_chronic",
    "total_refills", "missed_refills", "adherence_pct", "miss_rate_pct",
    "days_since_last_refill", "avg_refill_gap", "max_refill_gap", "stddev_gap",
    "gap_trend", "early_avg_gap", "recent_avg_gap",
    "total_engagements", "engagements_30d", "engagements_90d",
    "responded_count", "engagement_response_rate",
    "total_prescriptions", "avg_refills_allowed", "days_since_enrollment",
]

TARGET_COL = "future_refill_dropoff"
