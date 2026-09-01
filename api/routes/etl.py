"""api/routes/etl.py"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ETLRequest(BaseModel):
    dry_run: bool = False

@router.post("/run", summary="Execute ETL pipeline")
def run_etl(req: ETLRequest, background_tasks: BackgroundTasks):
    try:
        from etl.pipeline import run_pipeline
        # Run synchronously for API (background for dashboard)
        result = run_pipeline(skip_load=req.dry_run)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", summary="ETL status from database")
def etl_status():
    from sql.analytics_queries import get_etl_status
    df = get_etl_status()
    return {"logs": df.to_dict(orient="records")}
