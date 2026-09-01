-- ============================================================
-- sql/adherence.sql
-- Patient adherence analytics
-- Demonstrates: CTE, LAG, LEAD, ROW_NUMBER, RANK, CASE, dates
-- ============================================================
SET search_path TO healthcare, public;

-- ── Query 1: Adherence by Region ──────────────────────────
SELECT
    p.region,
    COUNT(DISTINCT r.patient_id)                                    AS patients,
    COUNT(r.refill_id)                                              AS total_refills,
    SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)                  AS on_time,
    ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
          / NULLIF(COUNT(r.refill_id), 0), 2)                      AS adherence_pct,
    RANK() OVER (ORDER BY
        SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)::float
        / NULLIF(COUNT(r.refill_id), 0) DESC
    )                                                               AS adherence_rank
FROM refills r
JOIN patients p ON r.patient_id = p.patient_id
GROUP BY p.region
ORDER BY adherence_pct DESC;

-- ── Query 2: Adherence by Medication ──────────────────────
SELECT
    m.drug_name,
    m.drug_category,
    COUNT(r.refill_id)                                              AS total_refills,
    ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END)
          / NULLIF(COUNT(r.refill_id), 0), 2)                      AS adherence_pct
FROM refills r
JOIN medications m ON r.medication_id = m.medication_id
GROUP BY m.drug_name, m.drug_category
ORDER BY adherence_pct ASC;

-- ── Query 3: Refill Gap Trend per Patient (LAG) ───────────
-- Calculates consecutive refill gaps per patient to detect increasing gaps
WITH ordered_refills AS (
    SELECT
        patient_id,
        medication_id,
        refill_date,
        was_on_time,
        ROW_NUMBER() OVER (PARTITION BY patient_id, medication_id ORDER BY refill_date) AS rn,
        LAG(refill_date) OVER (PARTITION BY patient_id, medication_id ORDER BY refill_date)
            AS prev_refill_date,
        LEAD(refill_date) OVER (PARTITION BY patient_id, medication_id ORDER BY refill_date)
            AS next_refill_date
    FROM refills
),
gap_calc AS (
    SELECT
        patient_id,
        medication_id,
        refill_date,
        rn,
        prev_refill_date,
        (refill_date - prev_refill_date) AS gap_days,
        LAG(refill_date - prev_refill_date) OVER (
            PARTITION BY patient_id, medication_id ORDER BY refill_date
        ) AS prev_gap_days
    FROM ordered_refills
    WHERE prev_refill_date IS NOT NULL
)
SELECT
    patient_id,
    medication_id,
    refill_date,
    gap_days,
    prev_gap_days,
    CASE
        WHEN gap_days > prev_gap_days THEN 'INCREASING'
        WHEN gap_days < prev_gap_days THEN 'DECREASING'
        ELSE 'STABLE'
    END AS gap_trend
FROM gap_calc
ORDER BY patient_id, refill_date;

-- ── Query 4: Patients with Increasing Refill Gaps ─────────
-- Identifies patients where average recent gap > average early gap
WITH patient_refills AS (
    SELECT
        patient_id,
        refill_date,
        refill_date - LAG(refill_date) OVER (PARTITION BY patient_id ORDER BY refill_date)
            AS gap_days,
        ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY refill_date)         AS rn,
        COUNT(*) OVER (PARTITION BY patient_id)                                  AS total_refills
    FROM refills
),
split_periods AS (
    SELECT
        patient_id,
        total_refills,
        AVG(CASE WHEN rn <= total_refills / 2 THEN gap_days END) AS early_avg_gap,
        AVG(CASE WHEN rn > total_refills / 2  THEN gap_days END) AS recent_avg_gap
    FROM patient_refills
    WHERE gap_days IS NOT NULL
    GROUP BY patient_id, total_refills
    HAVING total_refills >= 4
)
SELECT
    patient_id,
    ROUND(early_avg_gap, 1)  AS early_avg_gap_days,
    ROUND(recent_avg_gap, 1) AS recent_avg_gap_days,
    ROUND(recent_avg_gap - early_avg_gap, 1) AS gap_change,
    CASE
        WHEN recent_avg_gap > early_avg_gap * 1.20 THEN 'WORSENING'
        WHEN recent_avg_gap < early_avg_gap * 0.80 THEN 'IMPROVING'
        ELSE 'STABLE'
    END AS adherence_trend
FROM split_periods
ORDER BY gap_change DESC;

-- ── Query 5: Patients with Multiple Missed Refills ─────────
SELECT
    r.patient_id,
    p.region,
    p.age,
    p.chronic_condition,
    COUNT(*) FILTER (WHERE NOT r.was_on_time) AS missed_refill_count,
    COUNT(*) AS total_refills,
    ROUND(100.0 * COUNT(*) FILTER (WHERE NOT r.was_on_time) / COUNT(*), 2) AS miss_rate_pct
FROM refills r
JOIN patients p ON r.patient_id = p.patient_id
GROUP BY r.patient_id, p.region, p.age, p.chronic_condition
HAVING COUNT(*) FILTER (WHERE NOT r.was_on_time) >= 2
ORDER BY missed_refill_count DESC;

-- ── Query 6: Monthly Adherence Trend by Region ────────────
SELECT
    DATE_TRUNC('month', r.refill_date) AS month,
    p.region,
    COUNT(*) AS total_refills,
    ROUND(100.0 * SUM(CASE WHEN r.was_on_time THEN 1 ELSE 0 END) / COUNT(*), 2) AS adherence_pct
FROM refills r
JOIN patients p ON r.patient_id = p.patient_id
GROUP BY 1, 2
ORDER BY 1, 2;
