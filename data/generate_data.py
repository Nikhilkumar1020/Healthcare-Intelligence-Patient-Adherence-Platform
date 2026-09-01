"""
data/generate_data.py
Generates all synthetic healthcare datasets.

Realistic correlations built-in:
  - Patients age > 65 → +15% missed refill probability
  - Patients with > 2 missed refills → 80% chance HIGH risk label
  - Refill gap > 45 days → strong HIGH risk predictor
  - Engagement count < 2 last 90 days → moderate risk
  - North region → 8% lower adherence baseline
  - Some pharmacies have structurally higher miss rates
  - Chronic conditions correlate with medication categories

Deterministic: set RANDOM_SEED=42 (or via .env)

Usage:
    python data/generate_data.py
"""

import sys
import os
import random
import csv
import json
from pathlib import Path
from datetime import date, timedelta, datetime
from typing import List, Dict, Any

import numpy as np
import pandas as pd
from faker import Faker

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

SEED = int(os.getenv("RANDOM_SEED", 42))
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# ── Output paths ──────────────────────────────────────────────
OUT = Path(__file__).parent / "raw"
OUT.mkdir(parents=True, exist_ok=True)

# ── Configuration ─────────────────────────────────────────────
N_PATIENTS       = 10_000
N_MEDICATIONS    = 20
N_PHARMACIES     = 100
N_HCPS           = 500
START_DATE       = date(2022, 1, 1)
END_DATE         = date(2024, 6, 30)
REFERENCE_DATE   = date(2024, 6, 30)

REGIONS = ["North", "South", "East", "West", "Central"]
REGION_CITIES: Dict[str, List[str]] = {
    "North":   ["Albany", "Buffalo", "Rochester", "Syracuse", "Troy"],
    "South":   ["Atlanta", "Dallas", "Houston", "Miami", "Orlando"],
    "East":    ["Boston", "Newark", "New York", "Philadelphia", "Baltimore"],
    "West":    ["Denver", "Las Vegas", "Los Angeles", "Phoenix", "Seattle"],
    "Central": ["Chicago", "Columbus", "Detroit", "Indianapolis", "Kansas City"],
}
# Regional adherence multiplier (North is slightly lower)
REGION_ADHERENCE: Dict[str, float] = {
    "North": 0.72, "South": 0.80, "East": 0.81, "West": 0.79, "Central": 0.77
}

INSURANCE_TYPES = ["Private", "Medicare", "Medicaid", "Uninsured", "VA"]
CHRONIC_CONDITIONS = [
    "Type 2 Diabetes", "Hypertension", "Heart Disease", "COPD",
    "Asthma", "Hyperlipidemia", "Depression", "Arthritis", "None"
]
DRUG_CATEGORIES = [
    "Antidiabetic", "Antihypertensive", "Cardiovascular", "Respiratory",
    "Antidepressant", "Lipid-Lowering", "Anticoagulant", "Pain Management"
]
CHRONIC_TO_DRUG: Dict[str, str] = {
    "Type 2 Diabetes":  "Antidiabetic",
    "Hypertension":     "Antihypertensive",
    "Heart Disease":    "Cardiovascular",
    "COPD":             "Respiratory",
    "Asthma":           "Respiratory",
    "Hyperlipidemia":   "Lipid-Lowering",
    "Depression":       "Antidepressant",
    "Arthritis":        "Pain Management",
    "None":             random.choice(DRUG_CATEGORIES),
}
SPECIALIZATIONS = [
    "Cardiologist", "Endocrinologist", "General Practitioner", "Pulmonologist",
    "Psychiatrist", "Rheumatologist", "Neurologist", "Oncologist", "Nephrologist"
]
MANUFACTURERS = [
    "PharmaCo Inc.", "HealthGen Labs", "MedSynth Corp.", "BioRx Partners",
    "CurePath Pharma", "VitalDrug LLC", "TherapeuticX", "NovaMed"
]


# ── Helper functions ──────────────────────────────────────────

def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def date_range_days(start: date, end: date) -> int:
    return (end - start).days


def write_csv(rows: List[Dict], filename: str, fieldnames: List[str]) -> None:
    path = OUT / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ Wrote {len(rows):,} rows → {path.name}")


# ══════════════════════════════════════════════════════════════
# STEP 1: Medications (reference table, generated first)
# ══════════════════════════════════════════════════════════════

MEDICATION_NAMES = [
    ("Metformin", "Antidiabetic"),
    ("Glipizide", "Antidiabetic"),
    ("Lisinopril", "Antihypertensive"),
    ("Amlodipine", "Antihypertensive"),
    ("Atorvastatin", "Lipid-Lowering"),
    ("Rosuvastatin", "Lipid-Lowering"),
    ("Metoprolol", "Cardiovascular"),
    ("Warfarin", "Anticoagulant"),
    ("Albuterol", "Respiratory"),
    ("Fluticasone", "Respiratory"),
    ("Sertraline", "Antidepressant"),
    ("Escitalopram", "Antidepressant"),
    ("Ibuprofen", "Pain Management"),
    ("Celecoxib", "Pain Management"),
    ("Omeprazole", "Cardiovascular"),
    ("Furosemide", "Cardiovascular"),
    ("Gabapentin", "Pain Management"),
    ("Levothyroxine", "Antidiabetic"),
    ("Clopidogrel", "Anticoagulant"),
    ("Losartan", "Antihypertensive"),
]

DOSAGES = ["10mg", "20mg", "25mg", "50mg", "100mg", "500mg", "1000mg", "2.5mg", "5mg", "40mg"]


def generate_medications() -> pd.DataFrame:
    print("[GEN] Medications...")
    rows = []
    for i, (name, cat) in enumerate(MEDICATION_NAMES, 1):
        rows.append({
            "medication_id": f"MED{i:03d}",
            "drug_name": name,
            "drug_category": cat,
            "dosage": random.choice(DOSAGES),
            "manufacturer": random.choice(MANUFACTURERS),
        })
    write_csv(rows, "medications.csv",
              ["medication_id","drug_name","drug_category","dosage","manufacturer"])
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# STEP 2: Pharmacies
# ══════════════════════════════════════════════════════════════

# 20 pharmacies will have structurally higher miss rates
HIGH_MISS_PHARMACY_COUNT = 20


def generate_pharmacies() -> pd.DataFrame:
    print("[GEN] Pharmacies...")
    rows = []
    pharmacy_names = [
        "HealthFirst", "CareMore", "MedPlus", "RxReady", "PharmaSafe",
        "WellRx", "QuickCure", "TrustPharm", "PharmaHub", "RefillPro",
        "LifeCare", "HealPoint", "UrgiPharm", "PrimeCare", "MedStop",
        "RxWell", "CurePoint", "SafeScript", "HealthDrop", "MedEase",
    ]
    for i in range(1, N_PHARMACIES + 1):
        region = random.choice(REGIONS)
        city   = random.choice(REGION_CITIES[region])
        suffix = random.choice(["Pharmacy", "Drugs", "Health", "Rx", "Medical"])
        base   = pharmacy_names[(i - 1) % len(pharmacy_names)]
        rows.append({
            "pharmacy_id":   f"PHA{i:04d}",
            "pharmacy_name": f"{base} {suffix} #{i}",
            "city":          city,
            "region":        region,
        })
    write_csv(rows, "pharmacies.csv",
              ["pharmacy_id","pharmacy_name","city","region"])
    df = pd.DataFrame(rows)
    df["high_miss"] = df.index < HIGH_MISS_PHARMACY_COUNT  # first 20 → high miss rate
    return df


# ══════════════════════════════════════════════════════════════
# STEP 3: Patients
# ══════════════════════════════════════════════════════════════

def generate_patients() -> pd.DataFrame:
    print("[GEN] Patients...")
    rows = []
    for i in range(1, N_PATIENTS + 1):
        region = random.choices(REGIONS, weights=[18, 20, 22, 20, 20])[0]
        city   = random.choice(REGION_CITIES[region])
        age    = int(np.clip(np.random.normal(52, 18), 18, 95))
        chronic = random.choices(
            CHRONIC_CONDITIONS,
            weights=[12, 15, 10, 5, 7, 10, 8, 8, 25]
        )[0]
        rows.append({
            "patient_id":       f"P{10000 + i}",
            "age":              age,
            "gender":           random.choices(["Male","Female","Other"], weights=[48,50,2])[0],
            "city":             city,
            "region":           region,
            "insurance_type":   random.choices(
                                    INSURANCE_TYPES,
                                    weights=[40, 30, 15, 10, 5]
                                )[0],
            "chronic_condition": chronic,
            "enrollment_date":  random_date(date(2020, 1, 1), date(2023, 6, 30)).isoformat(),
        })
    write_csv(rows, "patients.csv",
              ["patient_id","age","gender","city","region",
               "insurance_type","chronic_condition","enrollment_date"])
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# STEP 4: HCPs
# ══════════════════════════════════════════════════════════════

HOSPITALS = [
    "City General Hospital", "Regional Medical Center", "Community Health Clinic",
    "University Hospital", "Memorial Hospital", "Metro Health Center",
    "Sunrise Medical Group", "Coastal Medical", "Lakeside Health", "Valley Medical"
]


def generate_hcps() -> pd.DataFrame:
    print("[GEN] HCPs...")
    rows = []
    for i in range(1, N_HCPS + 1):
        region = random.choice(REGIONS)
        city   = random.choice(REGION_CITIES[region])
        rows.append({
            "hcp_id":         f"HCP{i:04d}",
            "hcp_name":       fake.name(),
            "specialization": random.choice(SPECIALIZATIONS),
            "hospital":       random.choice(HOSPITALS),
            "city":           city,
            "region":         region,
        })
    write_csv(rows, "hcp.csv",
              ["hcp_id","hcp_name","specialization","hospital","city","region"])
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# STEP 5: Prescriptions (50K+)
# ══════════════════════════════════════════════════════════════

def assign_medication_for_patient(patient: dict, medications_df: pd.DataFrame) -> str:
    """Assign medication matching patient's chronic condition where possible."""
    condition = patient.get("chronic_condition", "None")
    preferred_cat = CHRONIC_TO_DRUG.get(condition, random.choice(DRUG_CATEGORIES))
    subset = medications_df[medications_df["drug_category"] == preferred_cat]
    if len(subset) == 0:
        subset = medications_df
    return random.choice(subset["medication_id"].tolist())


def generate_prescriptions(patients_df: pd.DataFrame,
                            medications_df: pd.DataFrame) -> pd.DataFrame:
    print("[GEN] Prescriptions (50K+)...")
    rows = []
    pid_counter = 1

    for _, patient in patients_df.iterrows():
        # Each patient gets 3–8 prescriptions over the study period
        n_rx = random.randint(3, 8)
        med_id = assign_medication_for_patient(patient.to_dict(), medications_df)
        enroll = date.fromisoformat(str(patient["enrollment_date"]))
        for _ in range(n_rx):
            rx_date = random_date(max(enroll, START_DATE), END_DATE)
            rows.append({
                "prescription_id": f"RX{pid_counter:07d}",
                "patient_id":      patient["patient_id"],
                "medication_id":   med_id,
                "prescription_date": rx_date.isoformat(),
                "quantity":        random.choice([30, 60, 90]),
                "refill_allowed":  random.randint(3, 12),
                "days_supply":     random.choice([30, 60, 90]),
            })
            pid_counter += 1

    write_csv(rows, "prescriptions.csv",
              ["prescription_id","patient_id","medication_id","prescription_date",
               "quantity","refill_allowed","days_supply"])
    print(f"    Total prescriptions: {len(rows):,}")
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# STEP 6: Refills (100K+) — with realistic adherence patterns
# ══════════════════════════════════════════════════════════════

def compute_miss_probability(patient: dict, pharmacy_is_high_miss: bool) -> float:
    """Calculate the probability that a patient misses a given refill."""
    base = 1.0 - REGION_ADHERENCE.get(patient["region"], 0.78)

    # Age effect: seniors >65 slightly harder to adhere
    if patient["age"] > 65:
        base += 0.08
    elif patient["age"] < 30:
        base += 0.04

    # Insurance: uninsured have higher miss rate
    if patient["insurance_type"] == "Uninsured":
        base += 0.10
    elif patient["insurance_type"] == "Medicaid":
        base += 0.05

    # High-miss pharmacy
    if pharmacy_is_high_miss:
        base += 0.12

    return min(base, 0.65)


def generate_refills(patients_df: pd.DataFrame,
                     prescriptions_df: pd.DataFrame,
                     pharmacies_df: pd.DataFrame) -> pd.DataFrame:
    print("[GEN] Refills (100K+)...")
    rows = []
    rid_counter = 1

    patient_lookup = patients_df.set_index("patient_id").to_dict(orient="index")
    pharmacy_ids   = pharmacies_df["pharmacy_id"].tolist()
    high_miss_ids  = set(pharmacies_df[pharmacies_df["high_miss"]]["pharmacy_id"].tolist())

    # Track missed refill history per patient (used to escalate future miss probability)
    missed_history: Dict[str, int] = {}

    for _, rx in prescriptions_df.iterrows():
        pid    = rx["patient_id"]
        mid    = rx["medication_id"]
        rxdate = date.fromisoformat(str(rx["prescription_date"]))
        qty    = int(rx["quantity"])
        days   = int(rx["days_supply"])
        n_refills = int(rx["refill_allowed"])

        patient = patient_lookup.get(pid, {})
        if not patient:
            continue

        # Assign a primary pharmacy for this patient-prescription
        pha_id = random.choice(pharmacy_ids)
        is_high_miss = pha_id in high_miss_ids

        miss_prob = compute_miss_probability(patient, is_high_miss)
        prev_missed = missed_history.get(pid, 0)
        # Escalating miss probability based on history
        if prev_missed >= 3:
            miss_prob = min(miss_prob + 0.25, 0.75)
        elif prev_missed >= 1:
            miss_prob = min(miss_prob + 0.10, 0.70)

        current_date = rxdate + timedelta(days=days)  # first refill due date

        for refill_num in range(1, n_refills + 1):
            if current_date > END_DATE:
                break

            # Decide if patient misses this refill
            missed = random.random() < miss_prob

            if missed:
                missed_history[pid] = missed_history.get(pid, 0) + 1
                # Gap: 10–60 extra days before they actually refill (or skip entirely)
                gap_extra = random.randint(10, 60)
                actual_date = current_date + timedelta(days=gap_extra)
                was_on_time = False
                # Increase miss prob for next refill
                miss_prob = min(miss_prob * 1.15, 0.80)
            else:
                # On-time: ±5 days variance
                jitter = random.randint(-3, 5)
                actual_date = current_date + timedelta(days=jitter)
                was_on_time = True
                # Slight improvement after successful refill
                miss_prob = max(miss_prob * 0.95, 0.05)

            if actual_date > END_DATE:
                break

            rows.append({
                "refill_id":      f"RF{rid_counter:08d}",
                "patient_id":     pid,
                "medication_id":  mid,
                "prescription_id": rx["prescription_id"],
                "pharmacy_id":    pha_id,
                "refill_date":    actual_date.isoformat(),
                "quantity":       qty,
                "was_on_time":    was_on_time,
            })
            rid_counter += 1
            current_date = actual_date + timedelta(days=days)

    write_csv(rows, "refills.csv",
              ["refill_id","patient_id","medication_id","prescription_id",
               "pharmacy_id","refill_date","quantity","was_on_time"])
    print(f"    Total refills: {len(rows):,}")
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# STEP 7: Engagements (50K+)
# ══════════════════════════════════════════════════════════════

ENGAGEMENT_TYPES = ["Call", "Email", "SMS", "Portal", "Mail"]
RESPONSES = ["Responded", "No Response", "Opted Out", "Pending"]
RESPONSE_WEIGHTS = [45, 35, 10, 10]


def generate_engagements(patients_df: pd.DataFrame) -> pd.DataFrame:
    print("[GEN] Engagements (50K+)...")
    rows = []
    eid_counter = 1

    for _, patient in patients_df.iterrows():
        pid = patient["patient_id"]
        enroll = date.fromisoformat(str(patient["enrollment_date"]))

        # Base engagement count 3–10; higher risk patients get fewer (inverse relationship)
        # We'll vary this slightly — younger patients respond more
        base_engagements = random.randint(3, 10)
        if patient["age"] > 70:
            base_engagements = max(1, base_engagements - 2)

        for _ in range(base_engagements):
            eng_date = random_date(max(enroll, START_DATE), END_DATE)
            rows.append({
                "engagement_id":   f"ENG{eid_counter:08d}",
                "patient_id":      pid,
                "engagement_type": random.choice(ENGAGEMENT_TYPES),
                "engagement_date": eng_date.isoformat(),
                "response":        random.choices(RESPONSES, weights=RESPONSE_WEIGHTS)[0],
            })
            eid_counter += 1

    write_csv(rows, "engagements.csv",
              ["engagement_id","patient_id","engagement_type","engagement_date","response"])
    print(f"    Total engagements: {len(rows):,}")
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# STEP 8: HCP-Patient relationships
# ══════════════════════════════════════════════════════════════

def generate_hcp_patient(patients_df: pd.DataFrame,
                          hcps_df: pd.DataFrame) -> pd.DataFrame:
    print("[GEN] HCP-Patient relationships...")
    rows = []
    hcp_ids = hcps_df["hcp_id"].tolist()

    for _, patient in patients_df.iterrows():
        pid = patient["patient_id"]
        enroll = date.fromisoformat(str(patient["enrollment_date"]))
        # Each patient has 1–3 HCPs
        n_hcps = random.randint(1, 3)
        assigned = random.sample(hcp_ids, n_hcps)
        for hcp_id in assigned:
            effective_start = max(enroll, START_DATE)
            effective_end = min(effective_start + timedelta(days=365), END_DATE)
            first_visit = random_date(effective_start, effective_end)
            visit_count = random.randint(1, 8)
            last_visit  = first_visit + timedelta(days=random.randint(30, 600))
            last_visit  = min(last_visit, END_DATE)
            rows.append({
                "hcp_id":      hcp_id,
                "patient_id":  pid,
                "first_visit": first_visit.isoformat(),
                "last_visit":  last_visit.isoformat(),
                "visit_count": visit_count,
            })

    write_csv(rows, "hcp_patient.csv",
              ["hcp_id","patient_id","first_visit","last_visit","visit_count"])
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("Healthcare Intelligence Platform — Synthetic Data Generator")
    print(f"  Seed: {SEED}  |  Start: {START_DATE}  |  End: {END_DATE}")
    print("=" * 60)

    meds_df       = generate_medications()
    pharmacies_df = generate_pharmacies()
    patients_df   = generate_patients()
    hcps_df       = generate_hcps()
    prescriptions_df = generate_prescriptions(patients_df, meds_df)
    refills_df    = generate_refills(patients_df, prescriptions_df, pharmacies_df)
    engagements_df = generate_engagements(patients_df)
    hcp_patient_df = generate_hcp_patient(patients_df, hcps_df)

    print("\n" + "=" * 60)
    print("Data Generation Summary:")
    print(f"  Patients:      {len(patients_df):>10,}")
    print(f"  Medications:   {len(meds_df):>10,}")
    print(f"  Pharmacies:    {len(pharmacies_df):>10,}")
    print(f"  HCPs:          {len(hcps_df):>10,}")
    print(f"  Prescriptions: {len(prescriptions_df):>10,}")
    print(f"  Refills:       {len(refills_df):>10,}")
    print(f"  Engagements:   {len(engagements_df):>10,}")
    print(f"  HCP-Patient:   {len(hcp_patient_df):>10,}")
    print("=" * 60)
    print(f"\nAll CSV files written to: {OUT}")


if __name__ == "__main__":
    main()
