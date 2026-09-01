@echo off
echo ============================================================
echo Healthcare Intelligence Platform - Startup Script
echo ============================================================

REM Start the FastAPI backend in a new window
echo Starting FastAPI backend...
start "FastAPI Backend" cmd /c "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

REM Start the Streamlit dashboard in this window
echo Starting Streamlit dashboard...
python -m streamlit run dashboard/app.py --server.port 8501

echo.
echo Please press Ctrl+C to stop the dashboard.
echo To stop the backend, close its command window.
