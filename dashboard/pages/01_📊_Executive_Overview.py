"""
dashboard/pages/01_📊_Executive_Overview.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Executive Overview", page_icon="📊", layout="wide")

st.markdown("# 📊 Executive Overview")
st.markdown("*Population-level adherence KPIs and trend analytics*")
st.markdown("---")

from sql.analytics_queries import (
    get_overview_kpis, get_monthly_adherence_trend,
    get_adherence_by_region, get_risk_distribution, get_pharmacy_performance
)


@st.cache_data(ttl=300)
def load_data():
    return {
        "kpis":      get_overview_kpis(),
        "trend":     get_monthly_adherence_trend(),
        "regions":   get_adherence_by_region(),
        "risk_dist": get_risk_distribution(),
        "pharmacies": get_pharmacy_performance(limit=30),
    }


try:
    data = load_data()
except Exception as e:
    st.error(f"⚠️ Database connection failed: {e}")
    st.info("Please ensure PostgreSQL is running and the database is initialized. Run `python setup.py` first.")
    st.stop()

kpis = data["kpis"]
trend_df = data["trend"]
region_df = data["regions"]
risk_df  = data["risk_dist"]
pha_df   = data["pharmacies"]

# ── KPI Cards ─────────────────────────────────────────────────
def kpi_card(label, value, delta=None, color="#38bdf8"):
    delta_html = f"<div style='color:#4ade80;font-size:0.75rem'>{delta}</div>" if delta else ""
    return f"""
    <div style='background:linear-gradient(135deg,#1e293b,#0f172a);border:1px solid #334155;
         border-radius:12px;padding:1.2rem 1.5rem;text-align:center;
         transition:transform 0.2s;'>
      <div style='font-size:2.2rem;font-weight:700;color:{color};'>{value}</div>
      <div style='font-size:0.75rem;color:#94a3b8;text-transform:uppercase;
           letter-spacing:0.05em;margin-top:0.3rem;'>{label}</div>
      {delta_html}
    </div>"""


cols = st.columns(6)
kpi_list = [
    ("Total Patients",     f"{kpis.get('total_patients', 0):,}",   None,     "#38bdf8"),
    ("Active Patients",    f"{kpis.get('active_patients', 0):,}",  None,     "#818cf8"),
    ("Avg Adherence",      f"{kpis.get('adherence_pct', 0):.1f}%", None,     "#4ade80"),
    ("High-Risk Patients", f"{kpis.get('high_risk_count', 0):,}",  None,     "#f87171"),
    ("Missed Refill Rate", f"{kpis.get('missed_refill_pct', 0):.1f}%", None, "#fb923c"),
    ("Avg Refill Gap",     f"{kpis.get('avg_refill_gap_days', 0):.0f}d",None, "#a78bfa"),
]
for col, (label, val, delta, color) in zip(cols, kpi_list):
    with col:
        st.markdown(kpi_card(label, val, delta, color), unsafe_allow_html=True)

st.markdown("---")

# ── Charts Row 1 ───────────────────────────────────────────────
c1, c2 = st.columns([2, 1])

with c1:
    st.markdown("#### 📈 Monthly Adherence Trend")
    if not trend_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_df["month"], y=trend_df["adherence_pct"],
            mode="lines+markers", name="Adherence %",
            line=dict(color="#38bdf8", width=2.5),
            marker=dict(size=6, color="#38bdf8"),
            fill="tozeroy", fillcolor="rgba(56,189,248,0.08)"
        ))
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"), height=280,
            yaxis=dict(range=[50, 100], title="Adherence %", gridcolor="#1e293b"),
            xaxis=dict(title="Month", gridcolor="#1e293b"),
            margin=dict(l=20, r=20, t=10, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available. Run ETL and ML pipeline first.")

with c2:
    st.markdown("#### 🎯 Risk Distribution")
    if not risk_df.empty:
        colors = {"HIGH": "#f87171", "MEDIUM": "#fb923c", "LOW": "#4ade80"}
        fig = go.Figure(go.Pie(
            labels=risk_df["risk_level"],
            values=risk_df["count"],
            hole=0.55,
            marker_colors=[colors.get(l, "#64748b") for l in risk_df["risk_level"]],
        ))
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"), height=280,
            showlegend=True, legend=dict(font=dict(color="#e2e8f0")),
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No risk predictions yet. Run `python ml/predict.py`.")

# ── Charts Row 2 ───────────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown("#### 🗺️ Regional Adherence")
    if not region_df.empty:
        fig = px.bar(
            region_df.sort_values("adherence_pct"),
            x="adherence_pct", y="region", orientation="h",
            color="adherence_pct",
            color_continuous_scale=["#f87171", "#fb923c", "#4ade80"],
            text="adherence_pct",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"), height=280,
            coloraxis_showscale=False,
            xaxis=dict(range=[0, 100], title="Adherence %", gridcolor="#1e293b"),
            yaxis=dict(title=""),
            margin=dict(l=20, r=60, t=10, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

with c4:
    st.markdown("#### 🏪 Top Pharmacy Performance")
    if not pha_df.empty:
        top10 = pha_df.head(10)
        fig = px.bar(
            top10, x="adherence_pct", y="pharmacy_name", orientation="h",
            color="adherence_pct",
            color_continuous_scale=["#f87171", "#4ade80"],
        )
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"), height=280,
            coloraxis_showscale=False,
            xaxis=dict(title="Adherence %", gridcolor="#1e293b"),
            yaxis=dict(title=""),
            margin=dict(l=20, r=20, t=10, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
