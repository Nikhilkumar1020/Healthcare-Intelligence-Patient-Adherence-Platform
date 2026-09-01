"""
database/config.py
Centralised database connection configuration.
All settings come from environment variables — never hardcoded.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_db_url() -> str:
    """Return the PostgreSQL connection URL from environment."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Fallback: assemble from parts
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "healthcare_platform")
    user = os.getenv("DB_USER", "postgres")
    pwd  = os.getenv("DB_PASSWORD", "postgres")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"


def get_db_params() -> dict:
    """Return psycopg2-compatible connection params."""
    url = os.getenv("DATABASE_URL", "")
    if url:
        # Parse postgresql://user:pwd@host:port/db
        from urllib.parse import urlparse
        p = urlparse(url)
        return {
            "host": p.hostname,
            "port": p.port or 5432,
            "dbname": p.path.lstrip("/"),
            "user": p.username,
            "password": p.password,
        }
    return {
        "host":     os.getenv("DB_HOST", "localhost"),
        "port":     int(os.getenv("DB_PORT", "5432")),
        "dbname":   os.getenv("DB_NAME", "healthcare_platform"),
        "user":     os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres"),
    }
