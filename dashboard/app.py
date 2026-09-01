"""
dashboard/app.py
Healthcare Intelligence Platform — Main Streamlit Application

Run: streamlit run dashboard/app.py
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

st.set_page_config(
    page_title="Healthcare Intelligence Platform",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* KPI Cards */
.kpi-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.kpi-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #38bdf8;
    line-height: 1;
}
.kpi-label {
    font-size: 0.78rem;
    font-weight: 500;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.3rem;
}
.kpi-delta {
    font-size: 0.75rem;
    color: #4ade80;
    margin-top: 0.2rem;
}

/* Risk badges */
.badge-HIGH   { background: #7f1d1d; color: #fca5a5; padding: 2px 8px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
.badge-MEDIUM { background: #78350f; color: #fde68a; padding: 2px 8px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }
.badge-LOW    { background: #14532d; color: #86efac; padding: 2px 8px; border-radius: 99px; font-size: 0.75rem; font-weight: 600; }

/* Section headers */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #f1f5f9;
    border-bottom: 2px solid #38bdf8;
    padding-bottom: 0.4rem;
    margin-bottom: 1rem;
}

/* AI response */
.ai-response {
    background: #1e293b;
    border: 1px solid #334155;
    border-left: 4px solid #38bdf8;
    border-radius: 8px;
    padding: 1.2rem;
    font-size: 0.9rem;
    line-height: 1.6;
    color: #e2e8f0;
}

/* Disclaimer */
.disclaimer {
    background: #1c1917;
    border: 1px solid #78350f;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 0.78rem;
    color: #fbbf24;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 Healthcare Intelligence")
    st.markdown("**Patient Adherence Platform**")
    st.markdown("---")
    st.markdown("### Navigation")
    st.markdown("Use the page links below 👇")
    st.markdown("---")
    st.markdown("""
    <div class='disclaimer'>
    ⚠️ <strong>Portfolio Demo</strong><br>
    Uses 100% synthetic patient data.<br>
    Not a clinical system.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Tech Stack**")
    st.markdown("""
    - 🐘 PostgreSQL
    - 🐍 Python / Pandas
    - 🤖 Scikit-learn (ML)
    - 🧠 OpenAI + LangChain
    - 📚 ChromaDB (RAG)
    - ⚡ FastAPI
    - 📊 Plotly
    """)

# ── Landing page ────────────────────────────────────────────────
st.markdown("# 🏥 Healthcare Intelligence & Patient Adherence Platform")
st.markdown("### End-to-end analytics platform for medication refill adherence management")

st.markdown("""
<div class='disclaimer'>
⚠️ <strong>Portfolio Demonstration</strong> — This platform uses 100% synthetic patient data.
It is not a real medical diagnosis system and does not provide clinical advice.
All patients, prescriptions, and healthcare providers are fictitious.
</div>
""", unsafe_allow_html=True)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📊 Executive Overview
    Track KPIs, adherence trends, and risk distribution across your patient population.
    """)

with col2:
    st.markdown("""
    ### 🎯 Patient Risk
    Identify and prioritize high-risk patients with ML-powered risk scores and explanations.
    """)

with col3:
    st.markdown("""
    ### 🏪 Pharmacy & HCP Analytics
    Benchmark pharmacy performance and HCP engagement across regions.
    """)

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("""
    ### 🔄 Data Quality
    Monitor ETL pipeline health and data validation results.
    """)

with col5:
    st.markdown("""
    ### 🤖 AI Healthcare Assistant
    Ask questions in natural language — powered by GenAI, RAG, and Agentic AI.
    """)

with col6:
    st.markdown("""
    ### 📋 Architecture
    - ETL Pipeline → PostgreSQL
    - SQL Analytics (CTE, Window Functions)
    - ML Risk Model (Random Forest)
    - GenAI + RAG + LangGraph Agents
    - FastAPI REST Backend
    """)

st.markdown("---")
st.markdown("**👈 Select a page from the sidebar to get started**")
