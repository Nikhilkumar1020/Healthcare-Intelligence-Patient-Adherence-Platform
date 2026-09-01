"""api/routes/patients.py"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from sql.analytics_queries import get_all_patients, get_patient_detail

router = APIRouter()

@router.get("", summary="List patients with risk info")
def list_patients(
    region: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None, regex="^(HIGH|MEDIUM|LOW)$"),
    limit: int = Query(200, ge=1, le=1000),
):
    df = get_all_patients(region=region, risk_level=risk_level, limit=limit)
    return {"total": len(df), "patients": df.to_dict(orient="records")}


@router.get("/{patient_id}", summary="Get detailed patient profile")
def get_patient(patient_id: str):
    detail = get_patient_detail(patient_id)
    if not detail.get("patient"):
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return detail
