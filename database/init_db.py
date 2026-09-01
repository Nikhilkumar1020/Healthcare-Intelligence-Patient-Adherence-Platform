"""
database/init_db.py
Creates the healthcare_platform database and applies schema + indexes.
Run once before seeding data.

Usage:
    python database/init_db.py
"""
import sys
import os
import duckdb
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCHEMA_FILE  = Path(__file__).parent / "schema.sql"
INDEXES_FILE = Path(__file__).parent / "indexes.sql"


# create_database_if_missing removed for duckdb


def apply_sql_file(conn, filepath: Path, label: str) -> None:
    """Execute a SQL file against the given connection."""
    sql = filepath.read_text(encoding="utf-8")
    sql = sql.replace("JSONB", "JSON")
    sql = sql.replace("NUMERIC(5,4)", "REAL")
    sql = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY")
    sql = sql.replace("TIMESTAMP NOT NULL DEFAULT NOW()", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # Remove PostgreSQL schema commands globally for both schema and indexes
    import re
    sql = re.sub(r"DROP SCHEMA.*?;", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"CREATE SCHEMA.*?;", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"SET search_path.*?;", "", sql, flags=re.IGNORECASE)
    
    # DuckDB handles multiple statements in execute
    conn.execute(sql)
    print(f"[init_db] Applied {label}: {filepath.name}")


def init_db() -> None:
    """Full database initialisation sequence."""
    print(f"[init_db] Connecting to DuckDB...")
    
    db_path = Path("healthcare.duckdb")
    if db_path.exists():
        db_path.unlink()

    # Step 2: Apply schema + indexes
    conn = duckdb.connect("healthcare.duckdb")
    try:
        # Create schema equivalent in DuckDB
        conn.execute("CREATE SCHEMA IF NOT EXISTS healthcare")
        # DuckDB needs explicit schema prepending or default schema change
        conn.execute("SET schema = 'healthcare'")
        
        apply_sql_file(conn, SCHEMA_FILE,  "schema")
        apply_sql_file(conn, INDEXES_FILE, "indexes")
        print("[init_db] Database initialisation complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
