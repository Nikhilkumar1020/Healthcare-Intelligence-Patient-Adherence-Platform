"""
agents/recommendation_agent.py
Recommendation Agent: combines SQL, ML risk, and RAG outputs to produce
structured business-oriented recommendations.

Important: All recommendations are explicitly labeled as
"business prioritization recommendations" and not clinical/medical advice.
"""
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
GROQ_KEY = os.getenv("GROQ_API_KEY", "")


def run_recommendation_agent(
    question: str,
    sql_insights: Dict[str, Any] = None,
    risk_insights: Dict[str, Any] = None,
    rag_insights: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Synthesize SQL analytics, risk analysis, and RAG knowledge into
    structured business recommendations.

    Output format:
    - SUMMARY
    - DATA INSIGHTS
    - KEY DRIVERS
    - RECOMMENDED ACTIONS
    - SOURCES
    """
    result = {
        "question": question,
        "response": "",
        "sections": {},
        "error": ""
    }

    try:
        # Build context from all agents
        context_parts = []

        if sql_insights and not sql_insights.get("error"):
            context_parts.append(
                f"SQL ANALYTICS:\n{sql_insights.get('explanation', '')}\n"
                f"Data sample (first 5 rows): {str(sql_insights.get('data', [])[:5])}"
            )

        if risk_insights and not risk_insights.get("error"):
            hr_count = len(risk_insights.get("high_risk_patients", []))
            context_parts.append(
                f"RISK ANALYSIS:\n{risk_insights.get('risk_summary', '')}\n"
                f"High-risk patients (sample): "
                f"{str(risk_insights.get('high_risk_patients', [])[:3])}"
            )
            if risk_insights.get("regional_insights"):
                regions = risk_insights["regional_insights"]
                context_parts.append(
                    f"REGIONAL ADHERENCE: {str(regions)}"
                )

        if rag_insights and not rag_insights.get("error"):
            context_parts.append(
                f"KNOWLEDGE BASE:\n{rag_insights.get('answer', '')}\n"
                f"Sources: {', '.join(rag_insights.get('sources', []))}"
            )

        if not context_parts:
            result["response"] = (
                "Insufficient data from component agents to generate recommendations."
            )
            return result

        combined_context = "\n\n---\n\n".join(context_parts)

        if not (GROQ_KEY and GROQ_KEY.startswith("gsk_")):
            # Offline: structured fallback
            result["response"] = _build_offline_response(question, sql_insights, risk_insights, rag_insights)
            result["sections"] = _parse_sections(result["response"])
            return result

        from groq import Groq
        client = Groq(api_key=GROQ_KEY)

        prompt = f"""You are a healthcare analytics advisor for a medication adherence platform.
Based on the following analytical inputs, generate a structured business recommendation report.

ANALYTICAL INPUTS:
{combined_context}

Generate a response in EXACTLY this format:

SUMMARY:
[2-3 sentence summary of the key finding]

DATA INSIGHTS:
- [specific insight from SQL/analytics data]
- [specific insight from risk analysis]
- [specific insight from regional/pharmacy data if available]

KEY DRIVERS:
- [primary factor contributing to the issue]
- [secondary factor]
- [additional factor if available]

RECOMMENDED ACTIONS:
- [specific, actionable business recommendation 1]
- [specific, actionable business recommendation 2]
- [specific, actionable business recommendation 3]

SOURCES:
- [data source 1]
- [knowledge base document if used]

IMPORTANT DISCLAIMERS:
- Reference only numbers from the data provided above
- Do NOT invent statistics or patient counts
- Label all recommendations as "business prioritization recommendations"
- Do NOT make clinical or medical recommendations
- This platform uses SYNTHETIC data for portfolio demonstration"""

        response = client.chat.completions.create(
            model="groq/compound",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        result["response"] = response.choices[0].message.content.strip()
        result["sections"] = _parse_sections(result["response"])

    except Exception as e:
        result["error"] = str(e)
        result["response"] = f"Recommendation generation failed: {e}"
        logger.error(f"[recommendation_agent] Error: {e}")

    return result


def _build_offline_response(question, sql_insights, risk_insights, rag_insights) -> str:
    """Structured offline response when OpenAI is unavailable."""
    sql_exp = sql_insights.get("explanation", "SQL analysis completed.") if sql_insights else "N/A"
    risk_sum = risk_insights.get("risk_summary", "Risk analysis completed.") if risk_insights else "N/A"
    rag_ans = rag_insights.get("answer", "Knowledge base queried.") if rag_insights else "N/A"
    sources = (rag_insights.get("sources", []) if rag_insights else []) + ["SQL analytics database"]

    return f"""SUMMARY:
Analysis completed for: "{question}"
    Note: AI explanation unavailable (no Groq key). Raw data summaries shown below.

DATA INSIGHTS:
- SQL: {sql_exp}
- Risk: {risk_sum}

KEY DRIVERS:
- See SQL data and risk analysis above for specific drivers.

RECOMMENDED ACTIONS:
- Review high-risk patients identified in the Patient Risk dashboard
- Investigate low-performing pharmacies and regional adherence gaps
- Prioritize outreach for patients with increasing refill gaps

SOURCES:
- {chr(10) + '- '.join(sources)}

⚠️ These are business prioritization recommendations based on synthetic data.
This platform does not provide clinical or medical advice."""


def _parse_sections(text: str) -> Dict[str, str]:
    """Parse structured response into sections dict."""
    sections = {}
    current = None
    lines = text.split("\n")
    for line in lines:
        if line.strip().endswith(":") and line.strip()[:-1].isupper():
            current = line.strip()[:-1]
            sections[current] = ""
        elif current:
            sections[current] = sections.get(current, "") + line + "\n"
    return {k: v.strip() for k, v in sections.items()}
