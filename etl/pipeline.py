"""
etl/pipeline.py
Master ETL orchestrator.

Executes:
  Extract → Validate → Transform → Load
  Saves rejected records and ETL quality report.
  Writes run log to data/logs/.

Usage:
    python etl/pipeline.py
"""
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

# ── Logging setup ────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from etl.extract   import extract_all
from etl.validate  import validate_all
from etl.transform import transform_all
from etl.load      import load_all, save_rejected_records
from database.config import get_db_params
import psycopg2

REJECTED_DIR = Path(__file__).resolve().parent.parent / "data" / "rejected"
SCHEMA = "healthcare"


def log_etl_run(reports: dict, load_counts: dict) -> None:
    """Write ETL run summary to PostgreSQL etl_logs table."""
    try:
        conn = psycopg2.connect(**get_db_params())
        cur  = conn.cursor()
        for table, rpt in reports.items():
            status = "SUCCESS"
            if rpt.get("rejected_records", 0) > 0:
                status = "PARTIAL"
            if rpt.get("valid_records", 0) == 0:
                status = "FAILED"
            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.etl_logs
                    (table_name, total_records, valid_records, rejected_records,
                     duplicate_records, missing_values, validation_errors, status, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    table,
                    rpt.get("total_records", 0),
                    rpt.get("valid_records", 0),
                    rpt.get("rejected_records", 0),
                    rpt.get("duplicate_records", 0),
                    rpt.get("missing_values", 0),
                    rpt.get("invalid_records", 0),
                    status,
                    "; ".join(rpt.get("validation_errors", [])),
                )
            )
        conn.commit()
        cur.close()
        conn.close()
        logger.info("[pipeline] ETL run logged to database")
    except Exception as e:
        logger.warning(f"[pipeline] Could not write ETL log to DB: {e}")


def print_quality_report(reports: dict) -> None:
    logger.info("\n" + "=" * 65)
    logger.info("DATA QUALITY REPORT")
    logger.info("=" * 65)
    total_src = total_valid = total_rejected = 0
    for table, rpt in reports.items():
        total_src      += rpt.get("total_records", 0)
        total_valid    += rpt.get("valid_records", 0)
        total_rejected += rpt.get("rejected_records", 0)
        pct = (rpt.get("valid_records", 0) / rpt.get("total_records", 1)) * 100
        logger.info(
            f"  {table:<18} total={rpt.get('total_records',0):>8,}  "
            f"valid={rpt.get('valid_records',0):>8,}  "
            f"rejected={rpt.get('rejected_records',0):>6,}  "
            f"dups={rpt.get('duplicate_records',0):>5,}  "
            f"({pct:.1f}% valid)"
        )
    logger.info("-" * 65)
    overall = (total_valid / total_src * 100) if total_src > 0 else 0
    logger.info(f"  TOTAL              total={total_src:>8,}  valid={total_valid:>8,}  "
                f"rejected={total_rejected:>6,}  ({overall:.1f}% valid)")
    logger.info("=" * 65 + "\n")


def run_pipeline(skip_load: bool = False) -> dict:
    """
    Run the complete ETL pipeline.
    Returns summary dict for API/dashboard consumption.
    """
    start = datetime.now()
    logger.info(f"[pipeline] Starting ETL run at {start.isoformat()}")

    # ── STEP 1: Extract ───────────────────────────────────────
    logger.info("[pipeline] STEP 1/4: Extracting raw data...")
    raw_dfs = extract_all()

    # ── STEP 2: Validate ──────────────────────────────────────
    logger.info("[pipeline] STEP 2/4: Validating...")
    valid_dfs, rejected_dfs, quality_reports = validate_all(raw_dfs)

    # ── STEP 3: Transform ─────────────────────────────────────
    logger.info("[pipeline] STEP 3/4: Transforming...")
    transformed_dfs = transform_all(valid_dfs)

    # ── STEP 4: Load ──────────────────────────────────────────
    load_counts = {}
    if not skip_load:
        logger.info("[pipeline] STEP 4/4: Loading into PostgreSQL...")
        try:
            load_counts = load_all(transformed_dfs)
        except Exception as e:
            logger.error(f"[pipeline] Load failed: {e}")
            load_counts = {t: 0 for t in transformed_dfs}

        # Save rejected records
        save_rejected_records(rejected_dfs, REJECTED_DIR)

        # Log to DB
        log_etl_run(quality_reports, load_counts)
    else:
        logger.info("[pipeline] STEP 4/4: Skipped (dry run)")

    elapsed = (datetime.now() - start).total_seconds()
    print_quality_report(quality_reports)
    logger.info(f"[pipeline] ETL completed in {elapsed:.1f}s")

    return {
        "status": "completed",
        "elapsed_seconds": round(elapsed, 1),
        "quality_reports": quality_reports,
        "load_counts": load_counts,
        "log_file": str(log_file),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Healthcare ETL Pipeline")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate without loading to DB")
    args = parser.parse_args()
    run_pipeline(skip_load=args.dry_run)
