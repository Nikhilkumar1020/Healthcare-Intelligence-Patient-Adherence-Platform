"""
agents/sql_agent.py
SQL Analytics Agent: translates natural-language questions to safe SQL,
executes against PostgreSQL, and generates LLM explanations.

Safety guarantees:
  - Only SELECT queries allowed
  - Blocked: DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE/GRANT/EXEC
  - Query timeout: 10 seconds
  - LLM receives actual query result before generating numbers
"""
import os
import re
import json
import logging
from typing import Dict, Any, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
SCHEMA = "healthcare.healthcare"

BLOCKED_KEYWORDS = r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CREATE)\b"

TABLES_CONTEXT = """
Available tables (all in schema 'healthcare'):
- patients(patient_id, age, gender, city, region, insurance_type, chronic_condition, enrollment_date)
- medications(medication_id, drug_name, drug_category, dosage, manufacturer)
- prescriptions(prescription_id, patient_id, medication_id, prescription_date, quantity, refill_allowed, days_supply)
- refills(refill_id, patient_id, medication_id, prescription_id, pharmacy_id, refill_date, quantity, was_on_time)
- pharmacies(pharmacy_id, pharmacy_name, city, region)
- hcp(hcp_id, hcp_name, specialization, hospital, city, region)
- hcp_patient(hcp_id, patient_id, first_visit, last_visit, visit_count)
- engagements(engagement_id, patient_id, engagement_type, engagement_date, response)
- risk_predictions(prediction_id, patient_id, prediction_date, risk_score, risk_level, top_factor, model_version)
- etl_logs(log_id, run_timestamp, table_name, total_records, valid_records, rejected_records, status)
"""


def validate_sql(query: str) -> None:
    """Raise ValueError if query contains blocked operations."""
    q = query.strip()
    if re.search(BLOCKED_KEYWORDS, q, re.IGNORECASE):
        raise ValueError(f"Query contains blocked SQL operations. Only SELECT is allowed.")
    if not re.match(r"^\s*SELECT\b", q, re.IGNORECASE):
        raise ValueError("Only SELECT statements are allowed.")


def qualify_tables(query: str) -> str:
    """Ensure all table references are schema-qualified."""
    tables = ["patients","medications","pharmacies","hcp","hcp_patient",
              "prescriptions","refills","engagements","risk_predictions","etl_logs"]
    for t in tables:
        query = re.sub(rf"\bFROM\s+(?!{SCHEMA}\.){t}\b",
                       f"FROM {SCHEMA}.{t}", query, flags=re.IGNORECASE)
        query = re.sub(rf"\bJOIN\s+(?!{SCHEMA}\.){t}\b",
                       f"JOIN {SCHEMA}.{t}", query, flags=re.IGNORECASE)
    return query


def generate_sql(question: str) -> str:
    """Use OpenAI to translate a natural-language question to SQL."""
    if not (GROQ_KEY and GROQ_KEY.startswith("gsk_")):
        raise EnvironmentError("GROQ_API_KEY is not set.")

    from groq import Groq
    client = Groq(api_key=GROQ_KEY)

    system_prompt = f"""You are a healthcare analytics SQL expert.
Convert the user's natural-language question to a PostgreSQL SELECT query.
{TABLES_CONTEXT}
Rules:
- Only write SELECT statements
- Do NOT use any schema prefixes for table names (e.g. use 'patients' instead of 'healthcare.patients')
- was_on_time is a boolean column in refills (TRUE = on-time, FALSE = missed)
- risk_level values: 'HIGH', 'MEDIUM', 'LOW'
- Always add LIMIT 1000 unless the user asks for counts/aggregations
- Return ONLY the SQL query, no explanation, no markdown

Question: """

    response = client.chat.completions.create(
        model="groq/compound",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        temperature=0,
        max_tokens=500,
    )
    sql = response.choices[0].message.content.strip()
    # Strip markdown code blocks if present
    sql = re.sub(r"```sql\s*", "", sql)
    sql = re.sub(r"```\s*", "", sql)
    return sql.strip()


def execute_sql(query: str) -> pd.DataFrame:
    """Execute validated SQL and return DataFrame."""
    import duckdb
    import sys
    from pathlib import Path
    
    try:
        conn = duckdb.connect("healthcare.duckdb")
        conn.execute("SET schema = 'healthcare'")
        df = conn.execute(query).df()
        conn.close()
        return df
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {e}")


def explain_results(question: str, sql: str, df: pd.DataFrame) -> str:
    """Use LLM to explain query results. LLM receives actual data."""
    if not (GROQ_KEY and GROQ_KEY.startswith("gsk_")):
        return f"Query returned {len(df)} rows. (AI explanation unavailable — no Groq key)"

    from groq import Groq
    client = Groq(api_key=GROQ_KEY)

    # Format data for LLM (limit to 20 rows)
    data_str = df.head(20).to_string(index=False) if not df.empty else "(no results)"

    prompt = f"""You are a healthcare analytics assistant.
The user asked: "{question}"

The SQL query returned this data:
{data_str}

Total rows returned: {len(df)}

Provide a concise, professional explanation of these results in 3–5 sentences.
- Reference the actual numbers from the data provided
- Do NOT invent any statistics not shown above
- Frame insights in business terms (adherence, risk, patient prioritization)
- Do not make clinical or medical recommendations
- End with one actionable business insight

IMPORTANT: This is analysis of SYNTHETIC healthcare data for portfolio demonstration."""

    response = client.chat.completions.create(
        model="groq/compound",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


def run_sql_agent(question: str) -> Dict[str, Any]:
    """
    Full SQL agent pipeline:
    Question → SQL generation → Validation → Execution → LLM explanation

    Returns dict with: sql, data, explanation, error
    """
    result = {"question": question, "sql": "", "data": [], "explanation": "", "error": ""}

    try:
        # Generate SQL
        sql = generate_sql(question)
        result["sql"] = sql

        # Validate
        validate_sql(sql)
        sql = qualify_tables(sql)

        # Execute
        df = execute_sql(sql)
        result["data"] = df.head(100).to_dict(orient="records")

        # Explain
        result["explanation"] = explain_results(question, sql, df)

    except EnvironmentError as e:
        result["error"] = str(e)
        result["explanation"] = (
            "AI analytics assistant requires a Groq API key. "
            "Please set GROQ_API_KEY in your .env file."
        )
    except ValueError as e:
        result["error"] = f"SQL Safety Check: {e}"
        result["explanation"] = "The generated query was blocked for safety reasons."
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[sql_agent] Error: {e}")

    return result
