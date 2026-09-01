-- ============================================================
-- sql/hcp.sql
-- HCP engagement and patient volume analytics
-- Demonstrates: multi-table JOINs, GROUP BY, HAVING, aggregations
-- ============================================================
SET search_path TO healthcare, public;

-- ── Query 1: HCP Patient Volume and Engagement ────────────
SELECT
    h.hcp_id,
    h.hcp_name,
    h.specialization,
    h.hospital,
    h.region,
    COUNT(hp.patient_id)    AS patient_count,
    AVG(hp.visit_count)     AS avg_visits_per_patient,
    MAX(hp.last_visit)      AS most_recent_visit,
    MIN(hp.first_visit)     AS earliest_visit
FROM hcp h
LEFT JOIN hcp_patient hp ON h.hcp_id = hp.hcp_id
GROUP BY h.hcp_id, h.hcp_name, h.specialization, h.hospital, h.region
ORDER BY patient_count DESC;

-- ── Query 2: HCP-Patient Adherence Correlation ────────────
WITH patient_adherence AS (
    SELECT
        patient_id,
        ROUND(100.0 * SUM(CASE WHEN was_on_time THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 2) AS adherence_pct
    FROM refills
    GROUP BY patient_id
)
SELECT
    h.hcp_id,
    h.hcp_name,
    h.specialization,
    h.region,
    COUNT(hp.patient_id)            AS patient_count,
    ROUND(AVG(pa.adherence_pct), 2) AS avg_patient_adherence
FROM hcp h
JOIN hcp_patient hp ON h.hcp_id = hp.hcp_id
LEFT JOIN patient_adherence pa ON hp.patient_id = pa.patient_id
GROUP BY h.hcp_id, h.hcp_name, h.specialization, h.region
HAVING COUNT(hp.patient_id) >= 5
ORDER BY avg_patient_adherence DESC;

-- ── Query 3: HCP Engagement Activity ──────────────────────
SELECT
    h.hcp_id,
    h.hcp_name,
    h.specialization,
    h.region,
    COUNT(e.engagement_id)  AS total_engagements,
    COUNT(DISTINCT e.patient_id) AS engaged_patients,
    COUNT(e.engagement_id) FILTER (WHERE e.response = 'Responded') AS responded_count,
    ROUND(
        100.0 * COUNT(e.engagement_id) FILTER (WHERE e.response = 'Responded')
        / NULLIF(COUNT(e.engagement_id), 0), 2
    )                       AS response_rate_pct
FROM hcp h
JOIN hcp_patient hp ON h.hcp_id = hp.hcp_id
LEFT JOIN engagements e ON hp.patient_id = e.patient_id
GROUP BY h.hcp_id, h.hcp_name, h.specialization, h.region
HAVING COUNT(e.engagement_id) > 0
ORDER BY total_engagements DESC;

-- ── Query 4: HCP Specialization Summary ───────────────────
SELECT
    h.specialization,
    COUNT(DISTINCT h.hcp_id)        AS hcp_count,
    COUNT(DISTINCT hp.patient_id)   AS total_patients,
    ROUND(AVG(hp.visit_count), 2)   AS avg_visits
FROM hcp h
LEFT JOIN hcp_patient hp ON h.hcp_id = hp.hcp_id
GROUP BY h.specialization
ORDER BY total_patients DESC;

-- ── Query 5: High-Risk Patients by HCP ────────────────────
WITH latest_risk AS (
    SELECT DISTINCT ON (patient_id)
        patient_id, risk_level, risk_score
    FROM risk_predictions
    ORDER BY patient_id, prediction_date DESC
)
SELECT
    h.hcp_id,
    h.hcp_name,
    h.specialization,
    COUNT(hp.patient_id)                                            AS total_patients,
    COUNT(lr.patient_id) FILTER (WHERE lr.risk_level = 'HIGH')     AS high_risk_patients,
    ROUND(
        100.0 * COUNT(lr.patient_id) FILTER (WHERE lr.risk_level = 'HIGH')
        / NULLIF(COUNT(hp.patient_id), 0), 2
    )                                                               AS high_risk_pct,
    ROUND(AVG(lr.risk_score)::numeric, 4)                          AS avg_risk_score
FROM hcp h
JOIN hcp_patient hp ON h.hcp_id = hp.hcp_id
LEFT JOIN latest_risk lr ON hp.patient_id = lr.patient_id
GROUP BY h.hcp_id, h.hcp_name, h.specialization
HAVING COUNT(hp.patient_id) >= 5
ORDER BY high_risk_pct DESC;
