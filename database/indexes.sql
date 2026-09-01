-- ============================================================
-- Healthcare Intelligence Platform — Performance Indexes
-- ============================================================
SET search_path TO healthcare, public;

-- patients
CREATE INDEX IF NOT EXISTS idx_patients_region    ON patients(region);
CREATE INDEX IF NOT EXISTS idx_patients_age       ON patients(age);
CREATE INDEX IF NOT EXISTS idx_patients_insurance ON patients(insurance_type);
CREATE INDEX IF NOT EXISTS idx_patients_enrolled  ON patients(enrollment_date);

-- prescriptions
CREATE INDEX IF NOT EXISTS idx_prescriptions_patient  ON prescriptions(patient_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_med      ON prescriptions(medication_id);
CREATE INDEX IF NOT EXISTS idx_prescriptions_date     ON prescriptions(prescription_date);

-- refills
CREATE INDEX IF NOT EXISTS idx_refills_patient    ON refills(patient_id);
CREATE INDEX IF NOT EXISTS idx_refills_med        ON refills(medication_id);
CREATE INDEX IF NOT EXISTS idx_refills_pharmacy   ON refills(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_refills_date       ON refills(refill_date);
CREATE INDEX IF NOT EXISTS idx_refills_on_time    ON refills(was_on_time);

-- engagements
CREATE INDEX IF NOT EXISTS idx_engagements_patient ON engagements(patient_id);
CREATE INDEX IF NOT EXISTS idx_engagements_date    ON engagements(engagement_date);
CREATE INDEX IF NOT EXISTS idx_engagements_type    ON engagements(engagement_type);
CREATE INDEX IF NOT EXISTS idx_engagements_resp    ON engagements(response);

-- risk_predictions
CREATE INDEX IF NOT EXISTS idx_risk_patient   ON risk_predictions(patient_id);
CREATE INDEX IF NOT EXISTS idx_risk_date      ON risk_predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_risk_level     ON risk_predictions(risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_score     ON risk_predictions(risk_score DESC);

-- hcp
CREATE INDEX IF NOT EXISTS idx_hcp_region ON hcp(region);
CREATE INDEX IF NOT EXISTS idx_hcp_spec   ON hcp(specialization);

-- pharmacies
CREATE INDEX IF NOT EXISTS idx_pharmacies_region ON pharmacies(region);

-- etl_logs
CREATE INDEX IF NOT EXISTS idx_etl_logs_ts ON etl_logs(run_timestamp DESC);
