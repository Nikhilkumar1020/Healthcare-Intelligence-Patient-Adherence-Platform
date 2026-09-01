"""
etl/validate.py
Step 2 of ETL: validate raw DataFrames.
Returns (valid_df, rejected_df, quality_report dict) for each table.
"""
import logging
import re
from datetime import date
from typing import Tuple, Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Reference date for impossible future-date checks
REFERENCE_DATE = date(2024, 6, 30)
START_DATE     = date(2020, 1, 1)


# ── Allowed value sets ──────────────────────────────────────

VALID_GENDERS      = {"Male", "Female", "Other"}
VALID_REGIONS      = {"North", "South", "East", "West", "Central"}
VALID_INSURANCE    = {"Private", "Medicare", "Medicaid", "Uninsured", "VA"}
VALID_ENG_TYPES    = {"Call", "Email", "SMS", "Portal", "Mail"}
VALID_RESPONSES    = {"Responded", "No Response", "Opted Out", "Pending"}


def _report_base(table: str, total: int) -> Dict[str, Any]:
    return {
        "table": table,
        "total_records": total,
        "valid_records": 0,
        "rejected_records": 0,
        "duplicate_records": 0,
        "missing_values": 0,
        "invalid_records": 0,
        "validation_errors": [],
    }


def _flag(df: pd.DataFrame, mask: pd.Series, reason: str,
          rejected: List[pd.DataFrame], report: dict) -> pd.DataFrame:
    """Mark rows failing mask as rejected."""
    bad = df[mask].copy()
    if len(bad) > 0:
        bad["reject_reason"] = reason
        rejected.append(bad)
        report["invalid_records"] += len(bad)
        report["validation_errors"].append(f"{reason}: {len(bad)} rows")
        logger.warning(f"  [validate] {reason}: {len(bad)} rows")
    return df[~mask]


def validate_patients(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "patients"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    # Duplicates
    dup = df.duplicated(subset=["patient_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    # Missing required fields
    required = ["patient_id","age","gender","city","region","insurance_type","enrollment_date"]
    missing_mask = df[required].isin(["", None, "nan"]).any(axis=1)
    report["missing_values"] = int(missing_mask.sum())
    df = _flag(df, missing_mask, "Missing required fields", rejected, report)

    # Age range
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df = _flag(df, df["age"].isna() | (df["age"] < 1) | (df["age"] > 120),
               "Invalid age", rejected, report)

    # Gender
    df = _flag(df, ~df["gender"].isin(VALID_GENDERS), "Invalid gender", rejected, report)

    # Region
    df = _flag(df, ~df["region"].isin(VALID_REGIONS), "Invalid region", rejected, report)

    # Insurance
    df = _flag(df, ~df["insurance_type"].isin(VALID_INSURANCE),
               "Invalid insurance_type", rejected, report)

    # Enrollment date
    df["enrollment_date"] = pd.to_datetime(df["enrollment_date"], errors="coerce")
    df = _flag(df, df["enrollment_date"].isna(), "Invalid enrollment_date", rejected, report)
    df = _flag(df, df["enrollment_date"].dt.date > REFERENCE_DATE,
               "Future enrollment_date", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_medications(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "medications"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    dup = df.duplicated(subset=["medication_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    required = ["medication_id","drug_name","drug_category","dosage","manufacturer"]
    missing_mask = df[required].isin(["", None, "nan"]).any(axis=1)
    report["missing_values"] = int(missing_mask.sum())
    df = _flag(df, missing_mask, "Missing required fields", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_pharmacies(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "pharmacies"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    dup = df.duplicated(subset=["pharmacy_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    missing_mask = df[["pharmacy_id","pharmacy_name","city","region"]].isin(["",None,"nan"]).any(axis=1)
    report["missing_values"] = int(missing_mask.sum())
    df = _flag(df, missing_mask, "Missing required fields", rejected, report)
    df = _flag(df, ~df["region"].isin(VALID_REGIONS), "Invalid region", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_hcp(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "hcp"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    dup = df.duplicated(subset=["hcp_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    required = ["hcp_id","hcp_name","specialization","hospital","city","region"]
    missing_mask = df[required].isin(["",None,"nan"]).any(axis=1)
    report["missing_values"] = int(missing_mask.sum())
    df = _flag(df, missing_mask, "Missing required fields", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_prescriptions(df: pd.DataFrame,
                             valid_patients: set,
                             valid_medications: set) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "prescriptions"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    dup = df.duplicated(subset=["prescription_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    required = ["prescription_id","patient_id","medication_id","prescription_date","quantity","refill_allowed"]
    missing_mask = df[required].isin(["",None,"nan"]).any(axis=1)
    report["missing_values"] = int(missing_mask.sum())
    df = _flag(df, missing_mask, "Missing required fields", rejected, report)

    # FK checks
    df = _flag(df, ~df["patient_id"].isin(valid_patients), "Invalid patient_id FK", rejected, report)
    df = _flag(df, ~df["medication_id"].isin(valid_medications), "Invalid medication_id FK", rejected, report)

    # Dates
    df["prescription_date"] = pd.to_datetime(df["prescription_date"], errors="coerce")
    df = _flag(df, df["prescription_date"].isna(), "Invalid prescription_date", rejected, report)
    df = _flag(df, df["prescription_date"].dt.date > REFERENCE_DATE,
               "Future prescription_date", rejected, report)

    # Quantity / refill
    df["quantity"]       = pd.to_numeric(df["quantity"], errors="coerce")
    df["refill_allowed"] = pd.to_numeric(df["refill_allowed"], errors="coerce")
    df = _flag(df, df["quantity"].isna() | (df["quantity"] <= 0), "Non-positive quantity", rejected, report)
    df = _flag(df, df["refill_allowed"].isna() | (df["refill_allowed"] < 0),
               "Negative refill_allowed", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_refills(df: pd.DataFrame,
                      valid_patients: set,
                      valid_medications: set,
                      valid_pharmacies: set) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "refills"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    dup = df.duplicated(subset=["refill_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    required = ["refill_id","patient_id","medication_id","refill_date","quantity"]
    missing_mask = df[required].isin(["",None,"nan"]).any(axis=1)
    report["missing_values"] = int(missing_mask.sum())
    df = _flag(df, missing_mask, "Missing required fields", rejected, report)

    df = _flag(df, ~df["patient_id"].isin(valid_patients), "Invalid patient_id FK", rejected, report)
    df = _flag(df, ~df["medication_id"].isin(valid_medications), "Invalid medication_id FK", rejected, report)

    # pharmacy_id can be null but if present must be valid
    has_pha = df["pharmacy_id"].notna() & (df["pharmacy_id"] != "")
    bad_pha = has_pha & ~df["pharmacy_id"].isin(valid_pharmacies)
    df = _flag(df, bad_pha, "Invalid pharmacy_id FK", rejected, report)

    df["refill_date"] = pd.to_datetime(df["refill_date"], errors="coerce")
    df = _flag(df, df["refill_date"].isna(), "Invalid refill_date", rejected, report)
    df = _flag(df, df["refill_date"].dt.date < START_DATE, "Impossible early refill_date", rejected, report)
    df = _flag(df, df["refill_date"].dt.date > REFERENCE_DATE, "Future refill_date", rejected, report)

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df = _flag(df, df["quantity"].isna() | (df["quantity"] <= 0), "Non-positive quantity", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_engagements(df: pd.DataFrame, valid_patients: set) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "engagements"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    dup = df.duplicated(subset=["engagement_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    required = ["engagement_id","patient_id","engagement_type","engagement_date","response"]
    missing_mask = df[required].isin(["",None,"nan"]).any(axis=1)
    report["missing_values"] = int(missing_mask.sum())
    df = _flag(df, missing_mask, "Missing required fields", rejected, report)

    df = _flag(df, ~df["patient_id"].isin(valid_patients), "Invalid patient_id FK", rejected, report)
    df = _flag(df, ~df["engagement_type"].isin(VALID_ENG_TYPES), "Invalid engagement_type", rejected, report)
    df = _flag(df, ~df["response"].isin(VALID_RESPONSES), "Invalid response", rejected, report)

    df["engagement_date"] = pd.to_datetime(df["engagement_date"], errors="coerce")
    df = _flag(df, df["engagement_date"].isna(), "Invalid engagement_date", rejected, report)
    df = _flag(df, df["engagement_date"].dt.date > REFERENCE_DATE, "Future engagement_date", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_hcp_patient(df: pd.DataFrame,
                           valid_patients: set,
                           valid_hcps: set) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    table = "hcp_patient"
    report = _report_base(table, len(df))
    rejected: List[pd.DataFrame] = []

    dup = df.duplicated(subset=["hcp_id","patient_id"])
    report["duplicate_records"] = int(dup.sum())
    df = df[~dup].copy()

    df = _flag(df, ~df["patient_id"].isin(valid_patients), "Invalid patient_id FK", rejected, report)
    df = _flag(df, ~df["hcp_id"].isin(valid_hcps), "Invalid hcp_id FK", rejected, report)

    df["first_visit"] = pd.to_datetime(df["first_visit"], errors="coerce")
    df["last_visit"]  = pd.to_datetime(df["last_visit"],  errors="coerce")
    df = _flag(df, df["first_visit"].isna() | df["last_visit"].isna(), "Invalid visit dates", rejected, report)
    df = _flag(df, df["last_visit"] < df["first_visit"], "last_visit before first_visit", rejected, report)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
    report["valid_records"]    = len(df)
    report["rejected_records"] = len(rejected_df)
    return df, rejected_df, report


def validate_all(raw: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame],
                                                         Dict[str, pd.DataFrame],
                                                         Dict[str, dict]]:
    """
    Validate all tables in dependency order.
    Returns (valid_dfs, rejected_dfs, quality_reports).
    """
    valid, rejected, reports = {}, {}, {}

    # Reference tables first
    for table, fn in [
        ("medications", validate_medications),
        ("pharmacies",  validate_pharmacies),
        ("hcp",         validate_hcp),
    ]:
        v, r, rpt = fn(raw.get(table, pd.DataFrame()))
        valid[table] = v
        rejected[table] = r
        reports[table] = rpt

    # Patients
    v, r, rpt = validate_patients(raw.get("patients", pd.DataFrame()))
    valid["patients"] = v
    rejected["patients"] = r
    reports["patients"] = rpt

    # FK sets
    patient_ids  = set(valid["patients"]["patient_id"].tolist())
    med_ids      = set(valid["medications"]["medication_id"].tolist())
    pharmacy_ids = set(valid["pharmacies"]["pharmacy_id"].tolist())
    hcp_ids      = set(valid["hcp"]["hcp_id"].tolist())

    # Dependent tables
    v, r, rpt = validate_prescriptions(raw.get("prescriptions", pd.DataFrame()),
                                        patient_ids, med_ids)
    valid["prescriptions"] = v
    rejected["prescriptions"] = r
    reports["prescriptions"] = rpt

    v, r, rpt = validate_refills(raw.get("refills", pd.DataFrame()),
                                  patient_ids, med_ids, pharmacy_ids)
    valid["refills"] = v
    rejected["refills"] = r
    reports["refills"] = rpt

    v, r, rpt = validate_engagements(raw.get("engagements", pd.DataFrame()), patient_ids)
    valid["engagements"] = v
    rejected["engagements"] = r
    reports["engagements"] = rpt

    v, r, rpt = validate_hcp_patient(raw.get("hcp_patient", pd.DataFrame()),
                                      patient_ids, hcp_ids)
    valid["hcp_patient"] = v
    rejected["hcp_patient"] = r
    reports["hcp_patient"] = rpt

    return valid, rejected, reports
