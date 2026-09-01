"""tests/test_etl.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()

import pandas as pd
import pytest
from etl.validate import (
    validate_patients, validate_medications, validate_refills,
    validate_engagements
)


def make_patient(**kwargs):
    base = {
        "patient_id": "P10001", "age": "45", "gender": "Female",
        "city": "Boston", "region": "East", "insurance_type": "Private",
        "chronic_condition": "Hypertension", "enrollment_date": "2022-01-15"
    }
    base.update(kwargs)
    return pd.DataFrame([base])


class TestValidatePatients:
    def test_valid_patient(self):
        df = make_patient()
        valid, rejected, report = validate_patients(df)
        assert len(valid) == 1
        assert len(rejected) == 0

    def test_missing_required_field(self):
        df = make_patient(age="")
        valid, rejected, report = validate_patients(df)
        assert len(rejected) == 1
        assert report["missing_values"] >= 1

    def test_invalid_age(self):
        df = make_patient(age="200")
        valid, rejected, report = validate_patients(df)
        assert len(rejected) == 1

    def test_invalid_gender(self):
        df = make_patient(gender="Unknown")
        valid, rejected, report = validate_patients(df)
        assert len(rejected) == 1

    def test_invalid_region(self):
        df = make_patient(region="Pacific")
        valid, rejected, report = validate_patients(df)
        assert len(rejected) == 1

    def test_future_enrollment_date(self):
        df = make_patient(enrollment_date="2030-01-01")
        valid, rejected, report = validate_patients(df)
        assert len(rejected) == 1

    def test_duplicate_detection(self):
        row = make_patient().iloc[0].to_dict()
        df = pd.DataFrame([row, row])
        valid, rejected, report = validate_patients(df)
        assert report["duplicate_records"] == 1
        assert len(valid) == 1


class TestValidateMedications:
    def test_valid_medication(self):
        df = pd.DataFrame([{
            "medication_id": "MED001", "drug_name": "Metformin",
            "drug_category": "Antidiabetic", "dosage": "500mg",
            "manufacturer": "PharmaCo"
        }])
        valid, rejected, report = validate_medications(df)
        assert len(valid) == 1

    def test_missing_drug_name(self):
        df = pd.DataFrame([{
            "medication_id": "MED001", "drug_name": "",
            "drug_category": "Antidiabetic", "dosage": "500mg",
            "manufacturer": "PharmaCo"
        }])
        valid, rejected, report = validate_medications(df)
        assert len(rejected) == 1


class TestValidateRefills:
    def test_negative_quantity(self):
        df = pd.DataFrame([{
            "refill_id": "RF00000001", "patient_id": "P10001",
            "medication_id": "MED001", "prescription_id": "RX0000001",
            "pharmacy_id": "PHA0001", "refill_date": "2023-01-15",
            "quantity": "-30", "was_on_time": "True"
        }])
        valid, rejected, report = validate_refills(
            df, {"P10001"}, {"MED001"}, {"PHA0001"}
        )
        assert len(rejected) == 1

    def test_future_refill_date(self):
        df = pd.DataFrame([{
            "refill_id": "RF00000001", "patient_id": "P10001",
            "medication_id": "MED001", "prescription_id": "RX0000001",
            "pharmacy_id": "PHA0001", "refill_date": "2030-01-15",
            "quantity": "30", "was_on_time": "True"
        }])
        valid, rejected, report = validate_refills(
            df, {"P10001"}, {"MED001"}, {"PHA0001"}
        )
        assert len(rejected) == 1

    def test_invalid_patient_fk(self):
        df = pd.DataFrame([{
            "refill_id": "RF00000001", "patient_id": "P99999",
            "medication_id": "MED001", "prescription_id": "RX0000001",
            "pharmacy_id": "PHA0001", "refill_date": "2023-01-15",
            "quantity": "30", "was_on_time": "True"
        }])
        valid, rejected, report = validate_refills(
            df, {"P10001"}, {"MED001"}, {"PHA0001"}
        )
        assert len(rejected) == 1
