"""api/routes/ml.py"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class PredictRequest(BaseModel):
    patient_id: Optional[str] = None  # If None, predict all patients

@router.post("/predict", summary="Run ML risk prediction")
def predict(req: PredictRequest):
    try:
        from ml.predict import predict_patient, generate_predictions, write_predictions
        if req.patient_id:
            result = predict_patient(req.patient_id)
            if not result:
                raise HTTPException(status_code=404, detail="Patient not found")
            return result
        else:
            df = generate_predictions()
            write_predictions(df)
            return {
                "status": "completed",
                "total_predictions": len(df),
                "high_risk": int((df["risk_level"] == "HIGH").sum()),
                "medium_risk": int((df["risk_level"] == "MEDIUM").sum()),
                "low_risk": int((df["risk_level"] == "LOW").sum()),
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
