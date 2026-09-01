-- ============================================================
-- sql/pharmacy.sql
-- Pharmacy performance analytics
-- Demonstrates: RANK, ROW_NUMBER, GROUP BY, HAVING, multi-table JOIN
-- ============================================================
SET search_path TO healthcare, public;

-- ── Query 1: Pharmacy Refill Performance ──────────────────
SELECT
    ph.pharmacy_id,
    ph.pharmacy_name,
    ph.region,
    COUNT(r.refill_id)                                              AS total_refills,
    COUNT(DISTINCT r.patient_id)                                    AS unique_patients,
    SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)                  AS on_time_refills,
    SUM(CASE WHEN NOT r.was_on_time THEN 1 ELSE 0 END)              AS missed_refills,
    ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
          / NULLIF(COUNT(r.refill_id), 0), 2)                      AS adherence_pct,
    RANK() OVER (
        ORDER BY SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)::float
                 / NULLIF(COUNT(r.refill_id), 0) DESC
    )                                                               AS performance_rank
FROM pharmacies ph
LEFT JOIN refills r ON ph.pharmacy_id = r.pharmacy_id
GROUP BY ph.pharmacy_id, ph.pharmacy_name, ph.region
HAVING COUNT(r.refill_id) > 0
ORDER BY adherence_pct DESC;

-- ── Query 2: Top 10 Performing Pharmacies ─────────────────
WITH pharmacy_stats AS (
    SELECT
        ph.pharmacy_id,
        ph.pharmacy_name,
        ph.region,
        COUNT(r.refill_id) AS total_refills,
        ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
              / NULLIF(COUNT(r.refill_id), 0), 2) AS adherence_pct
    FROM pharmacies ph
    JOIN refills r ON ph.pharmacy_id = r.pharmacy_id
    GROUP BY ph.pharmacy_id, ph.pharmacy_name, ph.region
    HAVING COUNT(r.refill_id) >= 50
)
SELECT * FROM pharmacy_stats
ORDER BY adherence_pct DESC
LIMIT 10;

-- ── Query 3: Bottom 10 Performing Pharmacies ──────────────
WITH pharmacy_stats AS (
    SELECT
        ph.pharmacy_id,
        ph.pharmacy_name,
        ph.region,
        COUNT(r.refill_id) AS total_refills,
        ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
              / NULLIF(COUNT(r.refill_id), 0), 2) AS adherence_pct
    FROM pharmacies ph
    JOIN refills r ON ph.pharmacy_id = r.pharmacy_id
    GROUP BY ph.pharmacy_id, ph.pharmacy_name, ph.region
    HAVING COUNT(r.refill_id) >= 50
)
SELECT * FROM pharmacy_stats
ORDER BY adherence_pct ASC
LIMIT 10;

-- ── Query 4: Pharmacy Performance by Region ───────────────
SELECT
    ph.region,
    COUNT(DISTINCT ph.pharmacy_id)                                  AS pharmacy_count,
    COUNT(r.refill_id)                                              AS total_refills,
    ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
          / NULLIF(COUNT(r.refill_id), 0), 2)                      AS adherence_pct,
    ROUND(MIN(
        100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END) OVER (PARTITION BY ph.pharmacy_id)
        / NULLIF(COUNT(r.refill_id) OVER (PARTITION BY ph.pharmacy_id), 0)
    ), 2)                                                           AS min_pharmacy_adherence
FROM pharmacies ph
JOIN refills r ON ph.pharmacy_id = r.pharmacy_id
GROUP BY ph.region
ORDER BY adherence_pct DESC;

-- ── Query 5: Pharmacy Monthly Trend ──────────────────────
SELECT
    ph.pharmacy_id,
    ph.pharmacy_name,
    DATE_TRUNC('month', r.refill_date) AS month,
    COUNT(*) AS refills,
    ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END) / COUNT(*), 2) AS adherence_pct
FROM pharmacies ph
JOIN refills r ON ph.pharmacy_id = r.pharmacy_id
GROUP BY ph.pharmacy_id, ph.pharmacy_name, DATE_TRUNC('month', r.refill_date)
ORDER BY ph.pharmacy_id, month;
