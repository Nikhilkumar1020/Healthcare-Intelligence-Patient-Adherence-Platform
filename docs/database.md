# Database Documentation

## Schema Overview

The platform uses PostgreSQL 16 with a `healthcare` schema containing 10 tables.

## ER Diagram

```
patients (PK: patient_id)
    │
    ├── prescriptions (FK: patient_id, medication_id)
    │       └── medications (PK: medication_id)
    │
    ├── refills (FK: patient_id, medication_id, pharmacy_id, prescription_id)
    │       └── pharmacies (PK: pharmacy_id)
    │
    ├── engagements (FK: patient_id)
    │
    ├── hcp_patient (PK: hcp_id + patient_id, FK: hcp_id, patient_id)
    │       └── hcp (PK: hcp_id)
    │
    └── risk_predictions (FK: patient_id)

etl_logs (audit trail, no FK)
```

## Table Descriptions

### patients
Core patient registry. 10,000 synthetic records.
- `patient_id` VARCHAR PK — format: P10001 - P20000
- `age` SMALLINT, CHECK (1-120)
- `gender` VARCHAR, CHECK ('Male','Female','Other')
- `region` VARCHAR — North/South/East/West/Central
- `insurance_type` — Private/Medicare/Medicaid/Uninsured/VA
- `chronic_condition` — most common: Hypertension, Type 2 Diabetes

### refills
Primary analytics table. 100K+ records.
- `was_on_time` BOOLEAN — critical field for adherence computation
- Adherence % = COUNT(was_on_time=TRUE) / COUNT(*) × 100
- Refill gap = refill_date - LAG(refill_date) OVER (PARTITION BY patient_id ORDER BY refill_date)

### risk_predictions
ML model output table.
- `risk_score` NUMERIC(5,4) — 0.0000 to 1.0000
- `risk_level` — HIGH (≥0.65) / MEDIUM (0.40-0.64) / LOW (<0.40)
- `top_factor` — Human-readable explanation
- `features_json` JSONB — raw feature values for audit

## Key SQL Patterns

### Adherence Rate
```sql
SELECT ROUND(100.0 * SUM(CASE WHEN was_on_time THEN 1 ELSE 0 END) / COUNT(*), 2)
FROM healthcare.refills;
```

### Refill Gap with LAG
```sql
SELECT patient_id, refill_date,
       refill_date - LAG(refill_date) OVER (PARTITION BY patient_id ORDER BY refill_date) AS gap_days
FROM healthcare.refills;
```

### Latest Risk per Patient (DISTINCT ON)
```sql
SELECT DISTINCT ON (patient_id) patient_id, risk_level, risk_score
FROM healthcare.risk_predictions
ORDER BY patient_id, prediction_date DESC;
```

## Indexes

All FK columns, date columns, and commonly-filtered columns are indexed.
See `database/indexes.sql` for the complete list.
