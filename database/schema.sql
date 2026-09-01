-- ============================================================
-- Healthcare Intelligence Platform — Database Schema
-- PostgreSQL 16
-- ============================================================

-- Drop and recreate schema for clean initialization
DROP SCHEMA IF EXISTS healthcare CASCADE;
CREATE SCHEMA healthcare;
SET search_path TO healthcare, public;

-- ============================================================
-- TABLE 1: patients
-- ============================================================
CREATE TABLE patients (
    patient_id      VARCHAR(20) PRIMARY KEY,
    age             SMALLINT NOT NULL CHECK (age BETWEEN 1 AND 120),
    gender          VARCHAR(10) NOT NULL CHECK (gender IN ('Male','Female','Other')),
    city            VARCHAR(100) NOT NULL,
    region          VARCHAR(50) NOT NULL,
    insurance_type  VARCHAR(50) NOT NULL,
    chronic_condition VARCHAR(100),
    enrollment_date DATE NOT NULL
);

-- ============================================================
-- TABLE 2: medications
-- ============================================================
CREATE TABLE medications (
    medication_id   VARCHAR(20) PRIMARY KEY,
    drug_name       VARCHAR(100) NOT NULL,
    drug_category   VARCHAR(100) NOT NULL,
    dosage          VARCHAR(50) NOT NULL,
    manufacturer    VARCHAR(100) NOT NULL
);

-- ============================================================
-- TABLE 3: prescriptions
-- ============================================================
CREATE TABLE prescriptions (
    prescription_id     VARCHAR(20) PRIMARY KEY,
    patient_id          VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    medication_id       VARCHAR(20) NOT NULL REFERENCES medications(medication_id),
    prescription_date   DATE NOT NULL,
    quantity            SMALLINT NOT NULL CHECK (quantity > 0),
    refill_allowed      SMALLINT NOT NULL CHECK (refill_allowed >= 0),
    days_supply         SMALLINT NOT NULL CHECK (days_supply > 0) DEFAULT 30
);

-- ============================================================
-- TABLE 4: pharmacies
-- ============================================================
CREATE TABLE pharmacies (
    pharmacy_id     VARCHAR(20) PRIMARY KEY,
    pharmacy_name   VARCHAR(150) NOT NULL,
    city            VARCHAR(100) NOT NULL,
    region          VARCHAR(50) NOT NULL
);

-- ============================================================
-- TABLE 5: refills
-- ============================================================
CREATE TABLE refills (
    refill_id       VARCHAR(20) PRIMARY KEY,
    patient_id      VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    medication_id   VARCHAR(20) NOT NULL REFERENCES medications(medication_id),
    prescription_id VARCHAR(20) REFERENCES prescriptions(prescription_id),
    pharmacy_id     VARCHAR(20) REFERENCES pharmacies(pharmacy_id),
    refill_date     DATE NOT NULL,
    quantity        SMALLINT NOT NULL CHECK (quantity > 0),
    was_on_time     BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- TABLE 6: hcp (Healthcare Providers)
-- ============================================================
CREATE TABLE hcp (
    hcp_id          VARCHAR(20) PRIMARY KEY,
    hcp_name        VARCHAR(150) NOT NULL,
    specialization  VARCHAR(100) NOT NULL,
    hospital        VARCHAR(150) NOT NULL,
    city            VARCHAR(100) NOT NULL,
    region          VARCHAR(50) NOT NULL
);

-- ============================================================
-- TABLE 7: hcp_patient (Many-to-Many)
-- ============================================================
CREATE TABLE hcp_patient (
    hcp_id      VARCHAR(20) NOT NULL REFERENCES hcp(hcp_id),
    patient_id  VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    first_visit DATE NOT NULL,
    last_visit  DATE NOT NULL,
    visit_count SMALLINT NOT NULL DEFAULT 1 CHECK (visit_count >= 1),
    PRIMARY KEY (hcp_id, patient_id),
    CONSTRAINT last_after_first CHECK (last_visit >= first_visit)
);

-- ============================================================
-- TABLE 8: engagements
-- ============================================================
CREATE TABLE engagements (
    engagement_id   VARCHAR(20) PRIMARY KEY,
    patient_id      VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    engagement_type VARCHAR(50) NOT NULL CHECK (engagement_type IN ('Call','Email','SMS','Portal','Mail')),
    engagement_date DATE NOT NULL,
    response        VARCHAR(50) NOT NULL CHECK (response IN ('Responded','No Response','Opted Out','Pending'))
);

-- ============================================================
-- TABLE 9: risk_predictions
-- ============================================================
CREATE TABLE risk_predictions (
    prediction_id   VARCHAR(20) PRIMARY KEY,
    patient_id      VARCHAR(20) NOT NULL REFERENCES patients(patient_id),
    prediction_date DATE NOT NULL,
    risk_score      NUMERIC(5,4) NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
    risk_level      VARCHAR(10) NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH')),
    top_factor      VARCHAR(200),
    model_version   VARCHAR(20) NOT NULL,
    features_json   JSONB
);

-- ============================================================
-- TABLE 10: etl_logs (ETL audit trail)
-- ============================================================
CREATE TABLE etl_logs (
    log_id              SERIAL PRIMARY KEY,
    run_timestamp       TIMESTAMP NOT NULL DEFAULT NOW(),
    table_name          VARCHAR(50) NOT NULL,
    total_records       INTEGER NOT NULL,
    valid_records       INTEGER NOT NULL,
    rejected_records    INTEGER NOT NULL,
    duplicate_records   INTEGER NOT NULL,
    missing_values      INTEGER NOT NULL,
    validation_errors   INTEGER NOT NULL,
    status              VARCHAR(20) NOT NULL CHECK (status IN ('SUCCESS','PARTIAL','FAILED')),
    notes               TEXT
);
