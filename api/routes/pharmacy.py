"""api/routes/pharmacy.py"""
from fastapi import APIRouter, Query
from typing import Optional
from sql.analytics_queries import get_pharmacy_performance

router = APIRouter()

@router.get("", summary="Pharmacy performance")
def pharmacies(
    region: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    df = get_pharmacy_performance(region=region, limit=limit)
    return {"total": len(df), "pharmacies": df.to_dict(orient="records")}
