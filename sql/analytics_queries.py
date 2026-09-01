"""
sql/analytics_queries.py
Python wrapper that executes SQL analytics queries and returns DataFrames.
Used by dashboard, API, and agents.
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)
SCHEMA = "healthcare.healthcare"


def _run(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute SQL and return result as DataFrame. Returns empty DF on error."""
    try:
        conn = duckdb.connect("healthcare.duckdb")
        conn.execute("SET schema = 'healthcare'")
        # DuckDB handles params differently depending on the query, but we can just use execute
        df = conn.execute(sql, params).df()
        conn.close()
        return df
    except Exception as e:
        logger.error(f"[analytics] Query failed: {e}")
        return pd.DataFrame()


# ── KPIs ─────────────────────────────────────────────────────

def get_overview_kpis() -> Dict[str, Any]:
    sql = f"""
    WITH refill_stats AS (
        SELECT
            COUNT(*) AS total_refills,
            SUM(CASE WHEN was_on_time THEN 1 ELSE 0 END) AS on_time_refills,
            SUM(CASE WHEN NOT was_on_time THEN 1 ELSE 0 END) AS missed_refills
        FROM {SCHEMA}.refills
    ),
    risk_stats AS (
        SELECT
            COUNT(*) FILTER (WHERE risk_level = 'HIGH') AS high_risk_count
        FROM (
            SELECT DISTINCT ON (patient_id) patient_id, risk_level
            FROM {SCHEMA}.risk_predictions
            ORDER BY patient_id, prediction_date DESC
        ) lr
    ),
    active_patients AS (
        SELECT COUNT(DISTINCT patient_id) AS active
        FROM {SCHEMA}.refills
        WHERE refill_date >= CURRENT_DATE - INTERVAL '180 days'
    ),
    gap_stats AS (
        SELECT ROUND(AVG(gap_days)::numeric, 1) AS avg_gap
        FROM (
            SELECT refill_date - LAG(refill_date) OVER (
                PARTITION BY patient_id ORDER BY refill_date
            ) AS gap_days
            FROM {SCHEMA}.refills
        ) g
        WHERE gap_days IS NOT NULL AND gap_days > 0
    )
    SELECT
        (SELECT COUNT(*) FROM {SCHEMA}.patients) AS total_patients,
        ap.active AS active_patients,
        rs.total_refills,
        rs.on_time_refills,
        rs.missed_refills,
        ROUND(100.0 * rs.on_time_refills / NULLIF(rs.total_refills, 0), 2) AS adherence_pct,
        ROUND(100.0 * rs.missed_refills / NULLIF(rs.total_refills, 0), 2) AS missed_refill_pct,
        rk.high_risk_count,
        gs.avg_gap AS avg_refill_gap_days
    FROM refill_stats rs, risk_stats rk, active_patients ap, gap_stats gs
    """
    df = _run(sql)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def get_monthly_adherence_trend() -> pd.DataFrame:
    sql = f"""
    SELECT
        DATE_TRUNC('month', refill_date)::date AS month,
        COUNT(*) AS total_refills,
        ROUND(100.0 * SUM(CASE WHEN was_on_time THEN 1 ELSE 0 END) / COUNT(*), 2) AS adherence_pct
    FROM {SCHEMA}.refills
    GROUP BY 1 ORDER BY 1
    """
    return _run(sql)


def get_adherence_by_region() -> pd.DataFrame:
    sql = f"""
    SELECT
        p.region,
        COUNT(DISTINCT r.patient_id) AS patients,
        COUNT(r.refill_id) AS total_refills,
        ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
              / NULLIF(COUNT(r.refill_id), 0), 2) AS adherence_pct
    FROM {SCHEMA}.refills r
    JOIN {SCHEMA}.patients p ON r.patient_id = p.patient_id
    GROUP BY p.region ORDER BY adherence_pct DESC
    """
    return _run(sql)


def get_risk_distribution() -> pd.DataFrame:
    sql = f"""
    SELECT risk_level, COUNT(*) AS count
    FROM (
        SELECT DISTINCT ON (patient_id) patient_id, risk_level
        FROM {SCHEMA}.risk_predictions
        ORDER BY patient_id, prediction_date DESC
    ) lr
    GROUP BY risk_level
    """
    return _run(sql)


def get_pharmacy_performance(region: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
    where = f"AND ph.region = $region" if region else ""
    sql = f"""
    SELECT
        ph.pharmacy_id, ph.pharmacy_name, ph.region,
        COUNT(r.refill_id) AS total_refills,
        COUNT(DISTINCT r.patient_id) AS unique_patients,
        ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
              / NULLIF(COUNT(r.refill_id), 0), 2) AS adherence_pct,
        SUM(CASE WHEN NOT r.was_on_time THEN 1 ELSE 0 END) AS missed_refills
    FROM {SCHEMA}.pharmacies ph
    LEFT JOIN {SCHEMA}.refills r ON ph.pharmacy_id = r.pharmacy_id
    WHERE 1=1 {where}
    GROUP BY ph.pharmacy_id, ph.pharmacy_name, ph.region
    HAVING COUNT(r.refill_id) > 0
    ORDER BY adherence_pct DESC
    LIMIT $limit
    """
    params = {"limit": limit}
    if region:
        params["region"] = region
    
    # DuckDB doesn't natively support %(param)s in all contexts if not strictly mapped, but execute with dict works
    return _run(sql, params)


def get_high_risk_patients(limit: int = 200) -> pd.DataFrame:
    sql = f"""
    WITH latest_risk AS (
        SELECT DISTINCT ON (patient_id)
            patient_id, risk_score, risk_level, top_factor, prediction_date
        FROM {SCHEMA}.risk_predictions
        ORDER BY patient_id, prediction_date DESC
    ),
    refill_summary AS (
        SELECT
            patient_id,
            MAX(refill_date) AS last_refill_date,
            COUNT(*) AS total_refills,
            SUM(CASE WHEN NOT was_on_time THEN 1 ELSE 0 END) AS missed_refills,
            CURRENT_DATE - MAX(refill_date) AS days_since_refill
        FROM {SCHEMA}.refills
        GROUP BY patient_id
    )
    SELECT
        lr.patient_id, p.age, p.gender, p.region, p.chronic_condition,
        p.insurance_type, m.drug_name AS medication,
        ROUND(lr.risk_score::numeric, 4) AS risk_score,
        lr.risk_level, lr.top_factor,
        rs.last_refill_date, rs.days_since_refill,
        rs.total_refills, rs.missed_refills,
        ROUND(100.0 * rs.missed_refills / NULLIF(rs.total_refills, 0), 2) AS miss_rate_pct
    FROM latest_risk lr
    JOIN {SCHEMA}.patients p ON lr.patient_id = p.patient_id
    LEFT JOIN refill_summary rs ON lr.patient_id = rs.patient_id
    LEFT JOIN LATERAL (
        SELECT medication_id FROM {SCHEMA}.prescriptions
        WHERE patient_id = lr.patient_id
        ORDER BY prescription_date DESC LIMIT 1
    ) px ON true
    LEFT JOIN {SCHEMA}.medications m ON px.medication_id = m.medication_id
    WHERE lr.risk_level = 'HIGH'
    ORDER BY lr.risk_score DESC
    LIMIT $limit
    """
    try:
        conn = duckdb.connect("healthcare.duckdb")
        conn.execute("SET schema = 'healthcare'")
        df = conn.execute(sql, {"limit": limit}).df()
        conn.close()
        return df
    except Exception as e:
        logger.error(f"[analytics] get_high_risk_patients failed: {e}")
        return pd.DataFrame()


def get_patient_detail(patient_id: str) -> Dict[str, Any]:
    """Return full patient profile with refill history and engagements."""
    # Patient profile
    patient_sql = f"""
    SELECT p.*, m.drug_name, m.drug_category
    FROM {SCHEMA}.patients p
    LEFT JOIN LATERAL (
        SELECT medication_id FROM {SCHEMA}.prescriptions
        WHERE patient_id = $pid
        ORDER BY prescription_date DESC LIMIT 1
    ) px ON true
    LEFT JOIN {SCHEMA}.medications m ON px.medication_id = m.medication_id
    WHERE p.patient_id = $pid
    """
    patient = _run(patient_sql, {"pid": patient_id})

    # Risk
    risk_sql = f"""
    SELECT risk_score, risk_level, top_factor, prediction_date, features_json
    FROM {SCHEMA}.risk_predictions
    WHERE patient_id = '{patient_id}'
    ORDER BY prediction_date DESC LIMIT 1
    """
    risk = _run(risk_sql)

    # Refill history (last 20)
    refill_sql = f"""
    SELECT r.refill_date, r.quantity, r.was_on_time, m.drug_name, ph.pharmacy_name
    FROM {SCHEMA}.refills r
    JOIN {SCHEMA}.medications m ON r.medication_id = m.medication_id
    LEFT JOIN {SCHEMA}.pharmacies ph ON r.pharmacy_id = ph.pharmacy_id
    WHERE r.patient_id = '{patient_id}'
    ORDER BY r.refill_date DESC LIMIT 20
    """
    refills = _run(refill_sql)

    # Engagements (last 10)
    eng_sql = f"""
    SELECT engagement_type, engagement_date, response
    FROM {SCHEMA}.engagements
    WHERE patient_id = '{patient_id}'
    ORDER BY engagement_date DESC LIMIT 10
    """
    engagements = _run(eng_sql)

    return {
        "patient":     patient.to_dict(orient="records")[0] if not patient.empty else {},
        "risk":        risk.to_dict(orient="records")[0] if not risk.empty else {},
        "refills":     refills.to_dict(orient="records"),
        "engagements": engagements.to_dict(orient="records"),
    }


def get_all_patients(
    region: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 500
) -> pd.DataFrame:
    where_clauses = []
    if region:
        where_clauses.append(f"p.region = '{region}'")
    if risk_level:
        where_clauses.append(f"lr.risk_level = '{risk_level}'")
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    sql = f"""
    WITH latest_risk AS (
        SELECT DISTINCT ON (patient_id)
            patient_id, risk_score, risk_level, top_factor
        FROM {SCHEMA}.risk_predictions
        ORDER BY patient_id, prediction_date DESC
    ),
    refill_summary AS (
        SELECT
            patient_id,
            MAX(refill_date) AS last_refill_date,
            COUNT(*) AS total_refills,
            SUM(CASE WHEN NOT was_on_time THEN 1 ELSE 0 END) AS missed_refills,
            CURRENT_DATE - MAX(refill_date) AS days_since_refill
        FROM {SCHEMA}.refills
        GROUP BY patient_id
    )
    SELECT
        p.patient_id, p.age, p.region, p.chronic_condition,
        ROUND(lr.risk_score::numeric, 4) AS risk_score,
        lr.risk_level, lr.top_factor,
        rs.last_refill_date, rs.days_since_refill,
        ROUND(100.0 * (rs.total_refills - rs.missed_refills)
              / NULLIF(rs.total_refills, 0), 2) AS adherence_pct
    FROM {SCHEMA}.patients p
    LEFT JOIN latest_risk lr ON p.patient_id = lr.patient_id
    LEFT JOIN refill_summary rs ON p.patient_id = rs.patient_id
    {where}
    ORDER BY COALESCE(lr.risk_score, 0) DESC
    LIMIT {limit}
    """
    return _run(sql)


def get_etl_status() -> pd.DataFrame:
    sql = f"""
    SELECT table_name, status, total_records, valid_records, rejected_records,
           duplicate_records, missing_values, validation_errors, run_timestamp, notes
    FROM {SCHEMA}.etl_logs
    ORDER BY run_timestamp DESC
    LIMIT 50
    """
    return _run(sql)


def execute_safe_query(query: str) -> pd.DataFrame:
    """
    Execute a user/AI-provided SQL query with safety checks.
    Only SELECT statements allowed; dangerous keywords blocked.
    """
    import re
    q = query.strip()

    # Block dangerous operations
    blocked = r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CREATE)\b"
    if re.search(blocked, q, re.IGNORECASE):
        raise ValueError("Query contains blocked SQL operations. Only SELECT is allowed.")

    if not re.match(r"^\s*SELECT\b", q, re.IGNORECASE):
        raise ValueError("Only SELECT queries are permitted.")

    # Auto-qualify bare table names with schema prefix
    tables = ["patients","medications","pharmacies","hcp","hcp_patient",
              "prescriptions","refills","engagements","risk_predictions","etl_logs"]
    for t in tables:
        q = re.sub(rf"\bFROM\s+{t}\b", f"FROM {SCHEMA}.{t}", q, flags=re.IGNORECASE)
        q = re.sub(rf"\bJOIN\s+{t}\b", f"JOIN {SCHEMA}.{t}", q, flags=re.IGNORECASE)

    return _run(q)
