"""
agents/risk_agent.py
Risk Analysis Agent: analyzes patient risk patterns, regional comparisons,
and pharmacy performance using the analytics query layer.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logger = logging.getLogger(__name__)


def run_risk_agent(question: str, region: Optional[str] = None) -> Dict[str, Any]:
    """Analyze risk patterns and return structured risk insights."""
    from sql.analytics_queries import (
        get_risk_distribution, get_adherence_by_region,
        get_high_risk_patients, get_pharmacy_performance
    )

    result = {
        "question": question,
        "risk_summary": "",
        "high_risk_patients": [],
        "regional_insights": [],
        "pharmacy_insights": [],
        "error": ""
    }

    try:
        # Risk distribution
        risk_df = get_risk_distribution()
        if not risk_df.empty:
            risk_counts = risk_df.set_index("risk_level")["count"].to_dict()
            total = sum(risk_counts.values())
            high_pct = round(risk_counts.get("HIGH", 0) / max(total, 1) * 100, 1)
            result["risk_summary"] = (
                f"Current risk distribution across {total:,} scored patients: "
                f"HIGH={risk_counts.get('HIGH', 0):,} ({high_pct}%), "
                f"MEDIUM={risk_counts.get('MEDIUM', 0):,}, "
                f"LOW={risk_counts.get('LOW', 0):,}."
            )

        # High-risk patients
        hr_df = get_high_risk_patients(limit=50)
        result["high_risk_patients"] = hr_df.head(20).to_dict(orient="records") if not hr_df.empty else []

        # Regional adherence
        region_df = get_adherence_by_region()
        result["regional_insights"] = region_df.to_dict(orient="records") if not region_df.empty else []

        # Pharmacy performance
        pha_df = get_pharmacy_performance(region=region, limit=20)
        result["pharmacy_insights"] = pha_df.head(10).to_dict(orient="records") if not pha_df.empty else []

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[risk_agent] Error: {e}")

    return result
