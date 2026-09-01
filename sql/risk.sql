-- ============================================================
-- sql/risk.sql
-- Risk analytics queries
-- Demonstrates: CTE, subqueries, CASE, HAVING, window functions
-- ============================================================
SET search_path TO healthcare, public;

-- ── Query 1: High-Risk Patients with Details ──────────────
WITH latest_risk AS (
    SELECT DISTINCT ON (patient_id)
        patient_id, risk_score, risk_level, top_factor, prediction_date
    FROM risk_predictions
    ORDER BY patient_id, prediction_date DESC
),
patient_refill_summary AS (
    SELECT
        patient_id,
        MAX(refill_date)  AS last_refill_date,
        COUNT(*)          AS total_refills,
        SUM(CASE WHEN NOT was_on_time THEN 1 ELSE 0 END) AS missed_refills,
        CURRENT_DATE - MAX(refill_date) AS days_since_last_refill
    FROM refills
    GROUP BY patient_id
)
SELECT
    lr.patient_id,
    p.age,
    p.gender,
    p.region,
    p.chronic_condition,
    p.insurance_type,
    ROUND(lr.risk_score::numeric, 4)  AS risk_score,
    lr.risk_level,
    lr.top_factor,
    prs.last_refill_date,
    prs.days_since_last_refill,
    prs.total_refills,
    prs.missed_refills,
    ROUND(100.0 * prs.missed_refills / NULLIF(prs.total_refills, 0), 2) AS miss_rate_pct
FROM latest_risk lr
JOIN patients p ON lr.patient_id = p.patient_id
LEFT JOIN patient_refill_summary prs ON lr.patient_id = prs.patient_id
WHERE lr.risk_level = 'HIGH'
ORDER BY lr.risk_score DESC;

-- ── Query 2: Risk Distribution by Region ──────────────────
WITH latest_risk AS (
    SELECT DISTINCT ON (patient_id)
        patient_id, risk_level
    FROM risk_predictions
    ORDER BY patient_id, prediction_date DESC
)
SELECT
    p.region,
    COUNT(*) FILTER (WHERE lr.risk_level = 'HIGH')   AS high_risk,
    COUNT(*) FILTER (WHERE lr.risk_level = 'MEDIUM') AS medium_risk,
    COUNT(*) FILTER (WHERE lr.risk_level = 'LOW')    AS low_risk,
    COUNT(*) AS total_scored,
    ROUND(100.0 * COUNT(*) FILTER (WHERE lr.risk_level = 'HIGH') / COUNT(*), 2) AS high_risk_pct,
    RANK() OVER (
        ORDER BY COUNT(*) FILTER (WHERE lr.risk_level = 'HIGH')::float / NULLIF(COUNT(*), 0) DESC
    ) AS risk_rank
FROM latest_risk lr
JOIN patients p ON lr.patient_id = p.patient_id
GROUP BY p.region;

-- ── Query 3: Regional Risk Ranking ────────────────────────
WITH region_stats AS (
    SELECT
        p.region,
        COUNT(DISTINCT p.patient_id) AS total_patients,
        ROUND(AVG(rp.risk_score)::numeric, 4) AS avg_risk_score,
        COUNT(DISTINCT rp.patient_id) FILTER (WHERE rp.risk_level = 'HIGH') AS high_risk_count
    FROM patients p
    LEFT JOIN (
        SELECT DISTINCT ON (patient_id) patient_id, risk_score, risk_level
        FROM risk_predictions
        ORDER BY patient_id, prediction_date DESC
    ) rp ON p.patient_id = rp.patient_id
    GROUP BY p.region
)
SELECT
    region,
    total_patients,
    avg_risk_score,
    high_risk_count,
    ROUND(100.0 * high_risk_count / total_patients, 2) AS high_risk_pct,
    RANK() OVER (ORDER BY avg_risk_score DESC) AS risk_rank
FROM region_stats
ORDER BY risk_rank;

-- ── Query 4: Top Risk Factors Distribution ─────────────────
SELECT
    top_factor,
    COUNT(*) AS patient_count,
    ROUND(AVG(risk_score)::numeric, 4) AS avg_risk_score,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_scored
FROM (
    SELECT DISTINCT ON (patient_id) patient_id, risk_score, top_factor
    FROM risk_predictions
    ORDER BY patient_id, prediction_date DESC
) latest
WHERE top_factor IS NOT NULL
GROUP BY top_factor
ORDER BY patient_count DESC;

-- ── Query 5: Patients at Immediate Risk (high score + long gap) ──
WITH latest_risk AS (
    SELECT DISTINCT ON (patient_id)
        patient_id, risk_score, risk_level, top_factor
    FROM risk_predictions
    ORDER BY patient_id, prediction_date DESC
),
last_refill AS (
    SELECT
        patient_id,
        MAX(refill_date) AS last_refill_date,
        CURRENT_DATE - MAX(refill_date) AS days_since_refill
    FROM refills
    GROUP BY patient_id
)
SELECT
    lr.patient_id,
    p.region,
    ROUND(lr.risk_score::numeric, 4) AS risk_score,
    lr.risk_level,
    lr.top_factor,
    lrf.days_since_refill,
    CASE
        WHEN lrf.days_since_refill > 60 AND lr.risk_level = 'HIGH' THEN 'IMMEDIATE ACTION'
        WHEN lrf.days_since_refill > 45 AND lr.risk_level = 'HIGH' THEN 'URGENT'
        WHEN lr.risk_level = 'HIGH'                                  THEN 'HIGH PRIORITY'
        ELSE 'MONITOR'
    END AS action_priority
FROM latest_risk lr
JOIN patients p ON lr.patient_id = p.patient_id
LEFT JOIN last_refill lrf ON lr.patient_id = lrf.patient_id
WHERE lr.risk_level IN ('HIGH', 'MEDIUM')
ORDER BY lr.risk_score DESC, lrf.days_since_refill DESC
LIMIT 100;
