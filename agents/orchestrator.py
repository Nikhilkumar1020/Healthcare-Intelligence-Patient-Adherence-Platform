"""
agents/orchestrator.py
LangGraph-based Agentic AI Orchestrator.

Routes questions to appropriate specialized agents:
  - data_quality   → DataQualityAgent
  - sql_analytics  → SQLAgent
  - risk_analysis  → RiskAgent
  - rag_knowledge  → RAGAgent
  - recommendation → All agents + RecommendationAgent
  - general        → SQLAgent + RAGAgent

The orchestrator determines which agents to invoke based on the question,
then assembles the final structured response.
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from enum import Enum

logger = logging.getLogger(__name__)

GROQ_KEY = os.getenv("GROQ_API_KEY", "")


class QuestionType(str, Enum):
    DATA_QUALITY   = "data_quality"
    SQL_ANALYTICS  = "sql_analytics"
    RISK_ANALYSIS  = "risk_analysis"
    RAG_KNOWLEDGE  = "rag_knowledge"
    RECOMMENDATION = "recommendation"
    GENERAL        = "general"


# Keyword-based intent routing (fast, no LLM required)
INTENT_PATTERNS = {
    QuestionType.DATA_QUALITY: [
        "etl", "data quality", "validation", "rejected", "missing", "duplicate",
        "data error", "pipeline", "ingestion"
    ],
    QuestionType.RISK_ANALYSIS: [
        "risk", "high risk", "drop-off", "dropout", "dropoff", "risky patient",
        "risk score", "risk level", "at risk"
    ],
    QuestionType.RAG_KNOWLEDGE: [
        "guideline", "intervention", "sop", "policy", "best practice",
        "evidence", "study", "protocol", "clinical", "knowledge base",
        "document", "what does the"
    ],
    QuestionType.RECOMMENDATION: [
        "recommend", "what should", "what action", "prioritize", "improve",
        "strategy", "plan", "next step", "what to do", "how to address",
        "business recommendation"
    ],
    QuestionType.SQL_ANALYTICS: [
        "how many", "count", "average", "trend", "compare", "adherence",
        "refill", "pharmacy", "region", "medication", "hcp", "which", "top",
        "bottom", "highest", "lowest", "rate"
    ],
}


def classify_intent(question: str) -> QuestionType:
    """Rule-based intent classification. No LLM needed."""
    if not (GROQ_KEY and GROQ_KEY.startswith("gsk_")):
        # Offline rule-based fallback
        q = question.lower()
        if "risk" in q: return QuestionType.RISK_ANALYSIS
        if "recommend" in q or "why" in q: return QuestionType.RECOMMENDATION
        if "guideline" in q or "policy" in q: return QuestionType.RAG_KNOWLEDGE
        if "quality" in q or "reject" in q: return QuestionType.DATA_QUALITY
        return QuestionType.SQL_ANALYTICS

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        
        q_lower = question.lower()

        # Check if question asks for recommendations AND analytics → multi-agent
        has_recommendation = any(kw in q_lower for kw in INTENT_PATTERNS[QuestionType.RECOMMENDATION])
        has_analytics = any(kw in q_lower for kw in INTENT_PATTERNS[QuestionType.SQL_ANALYTICS])
        has_rag = any(kw in q_lower for kw in INTENT_PATTERNS[QuestionType.RAG_KNOWLEDGE])

        if has_recommendation and (has_analytics or has_rag):
            return QuestionType.RECOMMENDATION

        for intent, keywords in INTENT_PATTERNS.items():
            if any(kw in q_lower for kw in keywords):
                return intent

        return QuestionType.GENERAL
    except:
        return QuestionType.GENERAL


def run_orchestrator(question: str) -> Dict[str, Any]:
    """
    Main orchestrator entry point.
    Routes to appropriate agents and assembles final response.
    """
    intent = classify_intent(question)
    logger.info(f"[orchestrator] Question: {question[:80]}")
    logger.info(f"[orchestrator] Intent: {intent}")

    result = {
        "question":   question,
        "intent":     intent.value,
        "agents_used": [],
        "response":   "",
        "sections":   {},
        "data":       {},
        "error":      ""
    }

    try:
        # ── DATA QUALITY ────────────────────────────────────
        if intent == QuestionType.DATA_QUALITY:
            from agents.data_quality_agent import run_data_quality_agent
            dq = run_data_quality_agent(question)
            result["agents_used"].append("DataQualityAgent")
            result["response"] = dq["summary"]
            result["data"]["etl_logs"] = dq.get("etl_logs", [])

        # ── RISK ANALYSIS ────────────────────────────────────
        elif intent == QuestionType.RISK_ANALYSIS:
            from agents.risk_agent import run_risk_agent
            risk = run_risk_agent(question)
            result["agents_used"].append("RiskAgent")
            result["response"] = risk["risk_summary"]
            result["data"]["high_risk_patients"] = risk.get("high_risk_patients", [])
            result["data"]["regional_insights"]  = risk.get("regional_insights", [])

        # ── RAG KNOWLEDGE ────────────────────────────────────
        elif intent == QuestionType.RAG_KNOWLEDGE:
            from agents.rag_agent import run_rag_agent
            rag = run_rag_agent(question)
            result["agents_used"].append("RAGAgent")
            result["response"] = rag["answer"]
            result["data"]["sources"] = rag.get("sources", [])

        # ── FULL RECOMMENDATION (multi-agent) ────────────────
        elif intent == QuestionType.RECOMMENDATION:
            from agents.sql_agent import run_sql_agent
            from agents.risk_agent import run_risk_agent
            from agents.rag_agent import run_rag_agent
            from agents.recommendation_agent import run_recommendation_agent

            sql_out  = run_sql_agent(question)
            risk_out = run_risk_agent(question)
            rag_out  = run_rag_agent(question)
            rec_out  = run_recommendation_agent(question, sql_out, risk_out, rag_out)

            result["agents_used"] = [
                "SQLAgent", "RiskAgent", "RAGAgent", "RecommendationAgent"
            ]
            result["response"] = rec_out["response"]
            result["sections"] = rec_out.get("sections", {})
            result["data"] = {
                "sql_data":           sql_out.get("data", [])[:10],
                "high_risk_patients": risk_out.get("high_risk_patients", [])[:10],
                "sources":            rag_out.get("sources", []),
            }

        # ── SQL ANALYTICS ─────────────────────────────────────
        elif intent in (QuestionType.SQL_ANALYTICS, QuestionType.GENERAL):
            from agents.sql_agent import run_sql_agent
            sql_out = run_sql_agent(question)
            result["agents_used"].append("SQLAgent")
            result["response"] = sql_out.get("explanation", "")
            result["data"]["sql"] = sql_out.get("sql", "")
            result["data"]["query_results"] = sql_out.get("data", [])
            if sql_out.get("error"):
                result["error"] = sql_out["error"]

    except Exception as e:
        result["error"] = str(e)
        result["response"] = f"Orchestrator error: {e}"
        logger.error(f"[orchestrator] Error: {e}")

    return result
