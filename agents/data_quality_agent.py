"""
agents/data_quality_agent.py
Data Quality Agent: inspects ETL status and generates quality summaries.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logger = logging.getLogger(__name__)


def run_data_quality_agent(question: str = "") -> Dict[str, Any]:
    """Retrieve and summarize current ETL and data quality status."""
    from sql.analytics_queries import get_etl_status
    import psycopg2
    from database.config import get_db_params

    result = {"summary": "", "etl_logs": [], "quality_issues": [], "error": ""}

    try:
        etl_df = get_etl_status()
        if etl_df.empty:
            result["summary"] = (
                "No ETL runs found. Run `python etl/pipeline.py` to populate the database."
            )
            return result

        result["etl_logs"] = etl_df.head(20).to_dict(orient="records")

        # Latest run stats
        latest = etl_df.iloc[0]
        total_src = etl_df.groupby("run_timestamp")["total_records"].sum().iloc[0]
        total_valid = etl_df.groupby("run_timestamp")["valid_records"].sum().iloc[0]
        total_rej = etl_df.groupby("run_timestamp")["rejected_records"].sum().iloc[0]
        quality_pct = (total_valid / max(total_src, 1)) * 100

        issues = []
        for _, row in etl_df.iterrows():
            if row.get("rejected_records", 0) > 0:
                issues.append(
                    f"  {row['table_name']}: {row['rejected_records']} rejected records — {row['notes']}"
                )

        result["quality_issues"] = issues
        result["summary"] = (
            f"Latest ETL run at {latest['run_timestamp']}.\n"
            f"Overall data quality: {quality_pct:.1f}% valid records "
            f"({total_valid:,}/{total_src:,}).\n"
            f"Rejected records: {total_rej:,}.\n"
            + (f"Quality issues detected:\n" + "\n".join(issues) if issues
               else "No significant quality issues detected.")
        )

    except Exception as e:
        result["error"] = str(e)
        result["summary"] = f"Data quality check failed: {e}"
        logger.error(f"[data_quality_agent] Error: {e}")

    return result
