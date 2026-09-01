"""api/routes/analytics.py"""
from fastapi import APIRouter
from sql.analytics_queries import (
    get_overview_kpis, get_monthly_adherence_trend,
    get_adherence_by_region, get_risk_distribution
)

router = APIRouter()

@router.get("/overview", summary="Executive overview KPIs")
def overview():
    return get_overview_kpis()

@router.get("/adherence", summary="Monthly adherence trend")
def adherence():
    df = get_monthly_adherence_trend()
    return df.to_dict(orient="records")

@router.get("/adherence/region", summary="Adherence by region")
def adherence_by_region():
    df = get_adherence_by_region()
    return df.to_dict(orient="records")

@router.get("/risk", summary="Risk distribution")
def risk_distribution():
    df = get_risk_distribution()
    return df.to_dict(orient="records")
