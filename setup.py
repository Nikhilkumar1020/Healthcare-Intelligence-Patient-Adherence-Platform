"""
setup.py
Single-command setup script for the Healthcare Intelligence Platform.

Runs in sequence:
  1. Copy .env.example → .env (if missing)
  2. Test database connection
  3. Initialize database (create schema + indexes)
  4. Generate synthetic data
  5. Run ETL pipeline (load data into DB)
  6. Train ML model
  7. Generate predictions
  8. Ingest RAG documents
  9. Run tests

Usage:
    python setup.py
    python setup.py --skip-ml      (skip ML training, faster)
    python setup.py --skip-rag     (skip RAG ingestion)
    python setup.py --data-only    (only generate + load data)
"""
import sys
import os
import argparse
import shutil
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def step(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def check_env() -> None:
    step("STEP 0: Environment setup")
    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("  Copied .env.example → .env")
        print("  ⚠️  Please edit .env and set DB_PASSWORD and GROQ_API_KEY")
    else:
        print("  .env file exists")
    load_dotenv(env_file)


def test_db_connection() -> bool:
    step("STEP 1: Testing database connection")
    try:
        import duckdb
        conn = duckdb.connect("healthcare.duckdb")
        conn.close()
        print(f"  ✅ Connected to DuckDB locally")
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False


def init_database() -> None:
    step("STEP 2: Initializing database")
    from database.init_db import init_db
    init_db()
    print("  ✅ Database initialized")


def generate_data() -> None:
    step("STEP 3: Generating synthetic data (10K patients, 100K+ refills)")
    import subprocess
    result = subprocess.run(
        [sys.executable, "data/generate_data.py"],
        cwd=ROOT, capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("Data generation failed")
    print("  ✅ Synthetic data generated")


def run_etl() -> None:
    step("STEP 4: Running ETL pipeline")
    from etl.pipeline import run_pipeline
    result = run_pipeline()
    print(f"  ✅ ETL completed in {result['elapsed_seconds']}s")


def train_ml() -> None:
    step("STEP 5: Training ML model")
    import subprocess
    result = subprocess.run(
        [sys.executable, "ml/train.py"],
        cwd=ROOT, capture_output=True, text=True
    )
    print(result.stdout[-2000:])  # Last 2000 chars
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError("ML training failed")
    print("  ✅ ML model trained and saved")


def generate_predictions() -> None:
    step("STEP 6: Generating risk predictions for all patients")
    import subprocess
    result = subprocess.run(
        [sys.executable, "ml/predict.py"],
        cwd=ROOT, capture_output=True, text=True
    )
    print(result.stdout[-1000:])
    if result.returncode != 0:
        print(result.stderr[-500:])
        raise RuntimeError("Prediction generation failed")
    print("  ✅ Risk predictions generated and stored")


def ingest_rag() -> None:
    step("STEP 7: Ingesting RAG knowledge base")
    from rag.ingest import ingest
    ingest()
    print("  ✅ Knowledge base ingested into ChromaDB")


def run_tests() -> None:
    step("STEP 8: Running test suite")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_etl.py",
         "tests/test_agents.py", "tests/test_ml.py", "-v", "--tb=short"],
        cwd=ROOT, capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("  ⚠️  Some tests failed (see above). The application may still work.")
    else:
        print("  ✅ All tests passed")


def print_startup_instructions() -> None:
    print("\n" + "=" * 60)
    print("  🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("""
  Start the application:

  Terminal 1 — API:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
    API Docs: http://localhost:8000/docs

  Terminal 2 — Dashboard:
    streamlit run dashboard/app.py
    Dashboard: http://localhost:8501

  To set GROQ_API_KEY for AI features:
    Edit .env → GROQ_API_KEY=gsk-...

  To run tests:
    python -m pytest tests/ -v

  Architecture Overview:
    data/raw/          ← Synthetic CSV data
    database/          ← PostgreSQL schema + init
    etl/               ← ETL pipeline
    sql/               ← Analytics queries
    ml/                ← Machine Learning
    rag/               ← RAG knowledge base
    agents/            ← AI agents + orchestrator
    api/               ← FastAPI backend
    dashboard/         ← Streamlit frontend
    """)


def main():
    parser = argparse.ArgumentParser(description="Healthcare Intelligence Platform Setup")
    parser.add_argument("--skip-ml",   action="store_true", help="Skip ML training")
    parser.add_argument("--skip-rag",  action="store_true", help="Skip RAG ingestion")
    parser.add_argument("--skip-tests",action="store_true", help="Skip test suite")
    parser.add_argument("--data-only", action="store_true", help="Only generate + load data")
    args = parser.parse_args()

    check_env()

    if not test_db_connection():
        print("\n⚠️  Cannot connect to database. Stopping setup.")
        print("Start PostgreSQL and retry, or use Docker: docker-compose up -d postgres")
        sys.exit(1)

    init_database()
    generate_data()
    run_etl()

    if not args.data_only:
        if not args.skip_ml:
            train_ml()
            generate_predictions()
        else:
            print("\n[Skipped] ML training (--skip-ml)")

        if not args.skip_rag:
            ingest_rag()
        else:
            print("\n[Skipped] RAG ingestion (--skip-rag)")

        if not args.skip_tests:
            run_tests()
        else:
            print("\n[Skipped] Tests (--skip-tests)")

    print_startup_instructions()


if __name__ == "__main__":
    main()
