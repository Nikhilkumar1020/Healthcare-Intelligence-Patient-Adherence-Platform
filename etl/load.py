"""
etl/load.py
Step 4 of ETL: load transformed DataFrames into PostgreSQL.
Uses UPSERT (INSERT ... ON CONFLICT DO NOTHING) for idempotency.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, List
import pandas as pd
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

SCHEMA = "healthcare.healthcare"

# Column lists matching DB schema exactly (insertion order)
TABLE_COLUMNS: Dict[str, List[str]] = {
    "patients": [
        "patient_id","age","gender","city","region",
        "insurance_type","chronic_condition","enrollment_date"
    ],
    "medications": [
        "medication_id","drug_name","drug_category","dosage","manufacturer"
    ],
    "pharmacies": [
        "pharmacy_id","pharmacy_name","city","region"
    ],
    "hcp": [
        "hcp_id","hcp_name","specialization","hospital","city","region"
    ],
    "prescriptions": [
        "prescription_id","patient_id","medication_id","prescription_date",
        "quantity","refill_allowed","days_supply"
    ],
    "refills": [
        "refill_id","patient_id","medication_id","prescription_id",
        "pharmacy_id","refill_date","quantity","was_on_time"
    ],
    "engagements": [
        "engagement_id","patient_id","engagement_type","engagement_date","response"
    ],
    "hcp_patient": [
        "hcp_id","patient_id","first_visit","last_visit","visit_count"
    ],
}

# PK for each table (for ON CONFLICT clause)
TABLE_PK: Dict[str, str] = {
    "patients":      "patient_id",
    "medications":   "medication_id",
    "pharmacies":    "pharmacy_id",
    "hcp":           "hcp_id",
    "prescriptions": "prescription_id",
    "refills":       "refill_id",
    "engagements":   "engagement_id",
    "hcp_patient":   "(hcp_id, patient_id)",
}


def get_connection():
    return duckdb.connect("healthcare.duckdb")


def load_table(conn, table: str, df: pd.DataFrame) -> int:
    """
    Load a DataFrame into the given table using batch upsert.
    Returns count of rows inserted.
    """
    if df.empty:
        logger.warning(f"[load] {table}: empty DataFrame, skipping")
        return 0

    cols = TABLE_COLUMNS.get(table)
    if not cols:
        logger.error(f"[load] Unknown table: {table}")
        return 0

    # Keep only columns that exist in both schema and DataFrame
    available = [c for c in cols if c in df.columns]
    df_subset = df[available].copy()

    # Replace NaN/None with Python None for psycopg2
    df_subset = df_subset.where(pd.notnull(df_subset), None)
    rows = [tuple(r) for r in df_subset.itertuples(index=False, name=None)]

    try:
        # DuckDB can insert a Pandas DataFrame directly using string interpolation
        # Using INSERT OR IGNORE to emulate ON CONFLICT DO NOTHING (DuckDB feature)
        # However, DuckDB's df integration is even simpler: we can just append
        # Let's register df and insert
        conn.register('df_view', df_subset)
        conn.execute(f"INSERT OR IGNORE INTO {SCHEMA}.{table} SELECT * FROM df_view")
        conn.unregister('df_view')
        inserted = len(df_subset)
        logger.info(f"[load] {table}: {inserted:,} rows upserted")
    except Exception as e:
        logger.error(f"[load] {table} INSERT failed: {e}")
        raise

    return inserted


def load_all(transformed_dfs: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    """Load all tables in FK-safe order. Returns {table: rows_loaded}."""
    load_order = [
        "medications", "pharmacies", "hcp", "patients",
        "prescriptions", "refills", "engagements", "hcp_patient"
    ]
    counts = {}
    conn = get_connection()
    try:
        for table in load_order:
            df = transformed_dfs.get(table, pd.DataFrame())
            counts[table] = load_table(conn, table, df)
    finally:
        conn.close()
    return counts


def save_rejected_records(rejected_dfs: Dict[str, pd.DataFrame],
                           output_dir: Path) -> None:
    """Write rejected records to CSV files for audit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for table, df in rejected_dfs.items():
        if not df.empty:
            out = output_dir / f"rejected_{table}_{ts}.csv"
            df.to_csv(out, index=False)
            logger.info(f"[load] Saved {len(df)} rejected {table} records → {out.name}")
