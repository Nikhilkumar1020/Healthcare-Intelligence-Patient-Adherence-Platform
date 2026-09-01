"""
etl/extract.py
Step 1 of ETL: extract raw CSV files from data/raw/.
Returns raw DataFrames with minimal transformation.
"""
import sys
import csv
import logging
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

EXPECTED_FILES: Dict[str, list] = {
    "patients.csv": [
        "patient_id","age","gender","city","region",
        "insurance_type","chronic_condition","enrollment_date"
    ],
    "medications.csv": [
        "medication_id","drug_name","drug_category","dosage","manufacturer"
    ],
    "pharmacies.csv": [
        "pharmacy_id","pharmacy_name","city","region"
    ],
    "hcp.csv": [
        "hcp_id","hcp_name","specialization","hospital","city","region"
    ],
    "prescriptions.csv": [
        "prescription_id","patient_id","medication_id","prescription_date",
        "quantity","refill_allowed","days_supply"
    ],
    "refills.csv": [
        "refill_id","patient_id","medication_id","prescription_id",
        "pharmacy_id","refill_date","quantity","was_on_time"
    ],
    "engagements.csv": [
        "engagement_id","patient_id","engagement_type","engagement_date","response"
    ],
    "hcp_patient.csv": [
        "hcp_id","patient_id","first_visit","last_visit","visit_count"
    ],
}


def extract_table(filename: str) -> pd.DataFrame:
    """Read a single CSV from raw dir, returning empty DF on error."""
    path = RAW_DIR / filename
    if not path.exists():
        logger.error(f"[extract] File not found: {path}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        logger.info(f"[extract] {filename}: {len(df):,} rows loaded")
        return df
    except Exception as e:
        logger.error(f"[extract] Failed to read {filename}: {e}")
        return pd.DataFrame()


def extract_all() -> Dict[str, pd.DataFrame]:
    """Extract all expected CSV files. Returns dict of {table_name: DataFrame}."""
    result = {}
    for filename, columns in EXPECTED_FILES.items():
        table = filename.replace(".csv", "")
        df = extract_table(filename)
        if df.empty:
            logger.warning(f"[extract] {table} is EMPTY — downstream steps may fail")
        result[table] = df
    return result
