"""
dashboard/pages/05_🤖_AI_Assistant.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()

import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="AI Healthcare Assistant", page_icon="🤖", layout="wide")
st.markdown("# 🤖 AI Healthcare Assistant")
st.markdown("*GenAI analytics, RAG knowledge base, and Agentic AI orchestration*")

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
if not (GROQ_KEY and GROQ_KEY.startswith("gsk_")):
    st.warning("""
    ⚠️ **Groq API key not configured.**
    Set `GROQ_API_KEY` in your `.env` file to enable AI features.
    The SQL execution and data retrieval will still work; AI explanations will show offline fallback messages.
    """)

st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    "💬 Analytics Assistant (SQL + AI)",
    "📚 Knowledge Base (RAG)",
    "🧠 Agentic AI Orchestrator"
])

# ── TAB 1: SQL Analytics Assistant ─────────────────────────────
with tab1:
    st.markdown("### 💬 Analytics Assistant")
    st.markdown("""
    Ask questions about patient data, adherence trends, pharmacy performance, and risk analytics.
    The assistant generates SQL, executes it against the live database, then uses AI to explain the results.
    **The AI never invents numbers — it only explains actual query results.**
    """)

    example_questions = [
        "How many high-risk patients are there by region?",
        "Which pharmacies have the highest missed refill rate?",
        "What is the average refill gap for patients in the North region?",
        "How has monthly adherence trended over time?",
        "Which medication has the lowest adherence rate?",
        "Compare adherence between North and South regions.",
    ]

    col_ex, col_q = st.columns([1, 2])
    with col_ex:
        st.markdown("**Example Questions:**")
        for q in example_questions:
            if st.button(q, key=f"sql_{q[:20]}", use_container_width=True):
                st.session_state["sql_question"] = q

    with col_q:
        question = st.text_area(
            "Your Question:",
            value=st.session_state.get("sql_question", ""),
            height=100,
            placeholder="Ask anything about patient adherence, risk, pharmacies...",
            key="sql_q_input"
        )
        if st.button("🔍 Analyze", type="primary", use_container_width=True):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Generating SQL and analyzing data..."):
                    from agents.sql_agent import run_sql_agent
                    result = run_sql_agent(question)

                if result.get("error") and "GROQ_API_KEY" in result.get("error", ""):
                    st.error("Groq API key required for SQL generation.")
                elif result.get("sql"):
                    st.markdown("**Generated SQL:**")
                    st.code(result["sql"], language="sql")

                if result.get("data"):
                    st.markdown("**Query Results:**")
                    df = pd.DataFrame(result["data"])
                    st.dataframe(df, use_container_width=True, height=200)
                    st.caption(f"{len(result['data'])} rows returned")

                if result.get("explanation"):
                    st.markdown("**AI Analysis:**")
                    st.markdown(f"""
                    <div style='background:#1e293b;border:1px solid #334155;border-left:4px solid #38bdf8;
                         border-radius:8px;padding:1.2rem;color:#e2e8f0;line-height:1.6;'>
                    {result['explanation']}
                    </div>
                    """, unsafe_allow_html=True)

                if result.get("error"):
                    st.error(f"Error: {result['error']}")

# ── TAB 2: RAG Knowledge Base ───────────────────────────────────
with tab2:
    st.markdown("### 📚 Healthcare Knowledge Base (RAG)")
    st.markdown("""
    Query the approved healthcare knowledge base documents.
    The system retrieves relevant context from:
    - Medication Adherence Guidelines
    - Patient Support SOP
    - Healthcare Analytics Policy
    - Medication Reference Guide
    - Clinical Study Summary
    
    **Sources are always cited. The system explicitly states when information is not found.**
    """)

    rag_examples = [
        "What are common interventions for patients with poor medication adherence?",
        "How should high-risk patients be contacted according to the SOP?",
        "What is the difference between MPR and PDC?",
        "What risk factors are associated with poor adherence?",
        "What are the escalation procedures for missed refills?",
    ]

    col_rex, col_rq = st.columns([1, 2])
    with col_rex:
        st.markdown("**Example Questions:**")
        for q in rag_examples:
            if st.button(q, key=f"rag_{q[:20]}", use_container_width=True):
                st.session_state["rag_question"] = q

    with col_rq:
        rag_q = st.text_area(
            "Your Question:",
            value=st.session_state.get("rag_question", ""),
            height=100,
            placeholder="Ask about adherence guidelines, interventions, SOPs...",
            key="rag_q_input"
        )
        if st.button("📖 Search Knowledge Base", type="primary", use_container_width=True):
            if not rag_q.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Searching knowledge base..."):
                    from agents.rag_agent import run_rag_agent
                    result = run_rag_agent(rag_q)

                st.markdown("**Answer:**")
                st.markdown(f"""
                <div style='background:#1e293b;border:1px solid #334155;border-left:4px solid #818cf8;
                     border-radius:8px;padding:1.2rem;color:#e2e8f0;line-height:1.6;'>
                {result['answer']}
                </div>
                """, unsafe_allow_html=True)

                if result.get("sources"):
                    st.markdown("**📄 Sources:**")
                    for src in result["sources"]:
                        st.markdown(f"- `{src}`")

                if result.get("error"):
                    st.error(f"Error: {result['error']}")

# ── TAB 3: Agentic AI ──────────────────────────────────────────
with tab3:
    st.markdown("### 🧠 Agentic AI Orchestrator")
    st.markdown("""
    The orchestrator automatically routes your question to the right combination of agents:
    - **SQLAgent** → Data analytics questions
    - **RiskAgent** → Patient risk analysis
    - **RAGAgent** → Knowledge base questions
    - **RecommendationAgent** → Business recommendations
    
    *Ask complex questions that span multiple data sources.*
    """)

    agent_examples = [
        "Why has adherence declined in the North region and what should we do?",
        "Which patients are at highest risk and what interventions does the knowledge base recommend?",
        "What is the current data quality status?",
        "Compare adherence between East and West and provide recommendations.",
        "Identify the top risk factors and suggest business priorities.",
    ]

    col_aex, col_aq = st.columns([1, 2])
    with col_aex:
        st.markdown("**Example Questions:**")
        for q in agent_examples:
            if st.button(q, key=f"agent_{q[:20]}", use_container_width=True):
                st.session_state["agent_question"] = q

    with col_aq:
        agent_q = st.text_area(
            "Your Question:",
            value=st.session_state.get("agent_question", ""),
            height=100,
            placeholder="Ask complex business questions...",
            key="agent_q_input"
        )
        if st.button("🚀 Run Agent Workflow", type="primary", use_container_width=True):
            if not agent_q.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("Running multi-agent workflow..."):
                    from agents.orchestrator import run_orchestrator
                    result = run_orchestrator(agent_q)

                st.markdown(f"**Agents Used:** `{' → '.join(result.get('agents_used', ['None']))}`")
                st.markdown(f"**Intent Detected:** `{result.get('intent','general')}`")
                st.markdown("---")

                if result.get("sections"):
                    sections = result["sections"]
                    for section_name, content in sections.items():
                        if content.strip():
                            st.markdown(f"**{section_name}**")
                            st.markdown(f"""
                            <div style='background:#1e293b;border:1px solid #334155;
                                 border-radius:8px;padding:1rem;color:#e2e8f0;
                                 line-height:1.6;margin-bottom:0.8rem;'>
                            {content}
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.markdown("**Response:**")
                    st.markdown(f"""
                    <div style='background:#1e293b;border:1px solid #334155;border-left:4px solid #a78bfa;
                         border-radius:8px;padding:1.2rem;color:#e2e8f0;line-height:1.6;'>
                    {result.get('response', 'No response generated.')}
                    </div>
                    """, unsafe_allow_html=True)

                if result.get("data", {}).get("high_risk_patients"):
                    st.markdown("**High-Risk Patients (from analysis):**")
                    df = pd.DataFrame(result["data"]["high_risk_patients"])
                    st.dataframe(df, use_container_width=True, height=200)

                if result.get("data", {}).get("sources"):
                    st.markdown("**📄 Knowledge Base Sources:**")
                    for src in result["data"]["sources"]:
                        st.markdown(f"- `{src}`")

                if result.get("error"):
                    st.warning(f"Note: {result['error']}")

        st.markdown("---")
        st.markdown("""
        <div style='background:#1c1917;border:1px solid #78350f;border-radius:8px;
             padding:0.8rem 1rem;font-size:0.78rem;color:#fbbf24;'>
        ⚠️ <strong>AI Safety Notice</strong><br>
        All recommendations are business prioritization suggestions based on synthetic data analysis.<br>
        This platform does not provide clinical advice, medical diagnoses, or treatment recommendations.
        </div>
        """, unsafe_allow_html=True)
