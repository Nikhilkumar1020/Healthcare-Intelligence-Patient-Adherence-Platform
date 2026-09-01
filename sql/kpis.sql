-- ============================================================
-- sql/kpis.sql
-- Core healthcare KPIs
-- Demonstrates: aggregations, CASE, date functions, CTEs
-- ============================================================
SET search_path TO healthcare, public;

-- ── KPI 1: Total Patients ─────────────────────────────────
SELECT COUNT(*) AS total_patients FROM patients;

-- ── KPI 2: Active Patients (had a refill in last 180 days) ─
SELECT COUNT(DISTINCT patient_id) AS active_patients
FROM refills
WHERE refill_date >= CURRENT_DATE - INTERVAL '180 days';

-- ── KPI 3: Total Prescriptions ────────────────────────────
SELECT COUNT(*) AS total_prescriptions FROM prescriptions;

-- ── KPI 4: Total Refills ──────────────────────────────────
SELECT COUNT(*) AS total_refills FROM refills;

-- ── KPI 5: Missed Refill Rate ─────────────────────────────
SELECT
    ROUND(
        100.0 * SUM(CASE WHEN was_on_time = FALSE THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2
    ) AS missed_refill_rate_pct
FROM refills;

-- ── KPI 6: Average Adherence Rate (% on-time refills) ─────
SELECT
    ROUND(
        100.0 * SUM(CASE WHEN was_on_time = TRUE THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2
    ) AS avg_adherence_pct
FROM refills;

-- ── KPI 7: High-Risk Patient Count ────────────────────────
-- Uses the latest prediction per patient
WITH latest_risk AS (
    SELECT DISTINCT ON (patient_id)
        patient_id, risk_level, risk_score
    FROM risk_predictions
    ORDER BY patient_id, prediction_date DESC
)
SELECT
    COUNT(*) FILTER (WHERE risk_level = 'HIGH')   AS high_risk_count,
    COUNT(*) FILTER (WHERE risk_level = 'MEDIUM') AS medium_risk_count,
    COUNT(*) FILTER (WHERE risk_level = 'LOW')    AS low_risk_count,
    COUNT(*)                                       AS total_scored
FROM latest_risk;

-- ── KPI 8: Average Refill Gap (days between consecutive refills per patient) ──
-- Uses LAG window function
WITH refill_gaps AS (
    SELECT
        patient_id,
        refill_date,
        LAG(refill_date) OVER (PARTITION BY patient_id ORDER BY refill_date) AS prev_refill_date,
        refill_date - LAG(refill_date) OVER (PARTITION BY patient_id ORDER BY refill_date) AS gap_days
    FROM refills
)
SELECT
    ROUND(AVG(gap_days), 1) AS avg_refill_gap_days,
    ROUND(MAX(gap_days), 1) AS max_refill_gap_days,
    ROUND(MIN(gap_days), 1) AS min_refill_gap_days
FROM refill_gaps
WHERE gap_days IS NOT NULL AND gap_days > 0;

-- ── KPI 9: Risk Distribution ──────────────────────────────
WITH latest_risk AS (
    SELECT DISTINCT ON (patient_id)
        patient_id, risk_level
    FROM risk_predictions
    ORDER BY patient_id, prediction_date DESC
)
SELECT
    risk_level,
    COUNT(*) AS patient_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM latest_risk
GROUP BY risk_level
ORDER BY
    CASE risk_level WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END;

-- ── KPI 10: Monthly Refill Trend ──────────────────────────
SELECT
    DATE_TRUNC('month', refill_date) AS month,
    COUNT(*) AS total_refills,
    SUM(CASE WHEN was_on_time THEN 1 ELSE 0 END) AS on_time_refills,
    SUM(CASE WHEN NOT was_on_time THEN 1 ELSE 0 END) AS missed_refills,
    ROUND(
        100.0 * SUM(CASE WHEN was_on_time THEN 1 ELSE 0 END) / COUNT(*), 2
    ) AS adherence_pct
FROM refills
GROUP BY 1
ORDER BY 1;
