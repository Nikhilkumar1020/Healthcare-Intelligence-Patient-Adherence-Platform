"""tests/test_agents.py — Agent safety and routing tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from agents.orchestrator import classify_intent, QuestionType
from agents.sql_agent import validate_sql


class TestSQLSafety:
    def test_select_allowed(self):
        validate_sql("SELECT * FROM healthcare.patients LIMIT 10")

    def test_drop_blocked(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_sql("DROP TABLE patients")

    def test_delete_blocked(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_sql("DELETE FROM patients WHERE 1=1")

    def test_update_blocked(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_sql("UPDATE patients SET age = 99")

    def test_insert_blocked(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_sql("INSERT INTO patients VALUES (1,2,3)")

    def test_truncate_blocked(self):
        with pytest.raises(ValueError, match="blocked"):
            validate_sql("TRUNCATE TABLE patients")

    def test_non_select_rejected(self):
        with pytest.raises(ValueError):
            validate_sql("SHOW TABLES")


class TestIntentClassification:
    def test_data_quality_intent(self):
        assert classify_intent("What is the ETL data quality status?") == QuestionType.DATA_QUALITY
        assert classify_intent("How many rejected records are there?") == QuestionType.DATA_QUALITY

    def test_risk_intent(self):
        assert classify_intent("Which patients are at high risk?") == QuestionType.RISK_ANALYSIS
        assert classify_intent("Show me the risk distribution") == QuestionType.RISK_ANALYSIS

    def test_rag_intent(self):
        assert classify_intent("What does the guideline say about interventions?") == QuestionType.RAG_KNOWLEDGE
        assert classify_intent("What is the SOP for missed refills?") == QuestionType.RAG_KNOWLEDGE

    def test_recommendation_intent(self):
        q = "Why is adherence declining and what should we recommend?"
        assert classify_intent(q) == QuestionType.RECOMMENDATION

    def test_sql_intent(self):
        assert classify_intent("How many patients are in the North region?") == QuestionType.SQL_ANALYTICS
        assert classify_intent("Compare adherence across regions") == QuestionType.SQL_ANALYTICS
