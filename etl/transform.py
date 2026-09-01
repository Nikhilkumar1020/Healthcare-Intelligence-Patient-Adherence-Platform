"""
etl/transform.py
Step 3 of ETL: clean and transform validated DataFrames into DB-ready form.
"""
import logging
from typing import Dict
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def transform_patients(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["age"] = df["age"].astype(int)
    df["enrollment_date"] = pd.to_datetime(df["enrollment_date"]).dt.date.astype(str)
    df["chronic_condition"] = df["chronic_condition"].fillna("None").str.strip()
    df["gender"]            = df["gender"].str.strip()
    df["region"]            = df["region"].str.strip()
    df["insurance_type"]    = df["insurance_type"].str.strip()
    df["city"]              = df["city"].str.strip().str.title()
    return df[["patient_id","age","gender","city","region",
               "insurance_type","chronic_condition","enrollment_date"]]


def transform_medications(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["drug_name"]     = df["drug_name"].str.strip().str.title()
    df["drug_category"] = df["drug_category"].str.strip()
    df["dosage"]        = df["dosage"].str.strip()
    df["manufacturer"]  = df["manufacturer"].str.strip()
    return df[["medication_id","drug_name","drug_category","dosage","manufacturer"]]


def transform_pharmacies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pharmacy_name"] = df["pharmacy_name"].str.strip()
    df["city"]          = df["city"].str.strip().str.title()
    df["region"]        = df["region"].str.strip()
    # Drop internal column from generator if present
    if "high_miss" in df.columns:
        df = df.drop(columns=["high_miss"])
    return df[["pharmacy_id","pharmacy_name","city","region"]]


def transform_hcp(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hcp_name"]       = df["hcp_name"].str.strip()
    df["specialization"] = df["specialization"].str.strip()
    df["hospital"]       = df["hospital"].str.strip()
    df["city"]           = df["city"].str.strip().str.title()
    df["region"]         = df["region"].str.strip()
    return df[["hcp_id","hcp_name","specialization","hospital","city","region"]]


def transform_prescriptions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["prescription_date"] = pd.to_datetime(df["prescription_date"]).dt.date.astype(str)
    df["quantity"]          = df["quantity"].astype(int)
    df["refill_allowed"]    = df["refill_allowed"].astype(int)
    df["days_supply"]       = pd.to_numeric(df.get("days_supply", 30), errors="coerce").fillna(30).astype(int)
    return df[["prescription_id","patient_id","medication_id","prescription_date",
               "quantity","refill_allowed","days_supply"]]


def transform_refills(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["refill_date"] = pd.to_datetime(df["refill_date"]).dt.date.astype(str)
    df["quantity"]    = df["quantity"].astype(int)
    df["was_on_time"] = df["was_on_time"].astype(str).str.lower().isin(["true","1","yes","t"])
    df["pharmacy_id"] = df["pharmacy_id"].fillna("").str.strip()
    df["prescription_id"] = df["prescription_id"].fillna("").str.strip()
    return df[["refill_id","patient_id","medication_id","prescription_id",
               "pharmacy_id","refill_date","quantity","was_on_time"]]


def transform_engagements(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["engagement_date"] = pd.to_datetime(df["engagement_date"]).dt.date.astype(str)
    df["engagement_type"] = df["engagement_type"].str.strip()
    df["response"]        = df["response"].str.strip()
    return df[["engagement_id","patient_id","engagement_type","engagement_date","response"]]


def transform_hcp_patient(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["first_visit"]  = pd.to_datetime(df["first_visit"]).dt.date.astype(str)
    df["last_visit"]   = pd.to_datetime(df["last_visit"]).dt.date.astype(str)
    df["visit_count"]  = pd.to_numeric(df.get("visit_count", 1), errors="coerce").fillna(1).astype(int)
    return df[["hcp_id","patient_id","first_visit","last_visit","visit_count"]]


TRANSFORMERS = {
    "patients":      transform_patients,
    "medications":   transform_medications,
    "pharmacies":    transform_pharmacies,
    "hcp":           transform_hcp,
    "prescriptions": transform_prescriptions,
    "refills":       transform_refills,
    "engagements":   transform_engagements,
    "hcp_patient":   transform_hcp_patient,
}


def transform_all(valid_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Apply transformations to all validated DataFrames."""
    transformed = {}
    for table, df in valid_dfs.items():
        fn = TRANSFORMERS.get(table)
        if fn and not df.empty:
            try:
                transformed[table] = fn(df)
                logger.info(f"[transform] {table}: {len(transformed[table]):,} rows ready")
            except Exception as e:
                logger.error(f"[transform] {table} failed: {e}")
                transformed[table] = df
        else:
            transformed[table] = df
    return transformed
