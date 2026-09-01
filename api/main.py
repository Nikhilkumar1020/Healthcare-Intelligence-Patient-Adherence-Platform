"""
api/main.py
FastAPI application entry point.

Start with:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

Swagger docs: http://localhost:8000/docs
"""
import sys
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from api.routes import patients, analytics, pharmacy, hcp, ml, etl, ai


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logging.info("[API] Healthcare Intelligence Platform API starting...")
    yield
    logging.info("[API] API shutting down.")


app = FastAPI(
    title="Healthcare Intelligence & Patient Adherence Platform",
    description=(
        "AI-powered healthcare analytics API for medication adherence management. "
        "Uses synthetic patient data for portfolio demonstration purposes. "
        "NOT a clinical decision-making system."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(patients.router,   prefix="/patients",   tags=["Patients"])
app.include_router(analytics.router,  prefix="/analytics",  tags=["Analytics"])
app.include_router(pharmacy.router,   prefix="/pharmacies", tags=["Pharmacies"])
app.include_router(hcp.router,        prefix="/hcp",        tags=["HCP"])
app.include_router(ml.router,         prefix="/ml",         tags=["ML Predictions"])
app.include_router(etl.router,        prefix="/etl",        tags=["ETL"])
app.include_router(ai.router,         prefix="/ai",         tags=["AI"])


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Healthcare Intelligence Platform",
        "version": "1.0.0",
        "disclaimer": "This platform uses synthetic patient data for portfolio demonstration only.",
    }
