"""api/routes/hcp.py"""
from fastapi import APIRouter
from sql.analytics_queries import _run

router = APIRouter()

@router.get("", summary="HCP list with patient volume")
def list_hcps(limit: int = 100):
    df = _run(f"""
        SELECT h.hcp_id, h.hcp_name, h.specialization, h.hospital, h.region,
               COUNT(hp.patient_id) AS patient_count
        FROM healthcare.hcp h
        LEFT JOIN healthcare.hcp_patient hp ON h.hcp_id = hp.hcp_id
        GROUP BY h.hcp_id, h.hcp_name, h.specialization, h.hospital, h.region
        ORDER BY patient_count DESC LIMIT {limit}
    """)
    return {"total": len(df), "hcps": df.to_dict(orient="records")}
