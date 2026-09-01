"""
dashboard/pages/03_🏪_Pharmacy_HCP.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()

import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Pharmacy & HCP", page_icon="🏪", layout="wide")
st.markdown("# 🏪 Pharmacy & HCP Analytics")
st.markdown("*Benchmark pharmacy performance and HCP engagement*")
st.markdown("---")

from sql.analytics_queries import get_pharmacy_performance, _run

region_filter = st.selectbox("Filter by Region", ["All", "North", "South", "East", "West", "Central"])
region = region_filter if region_filter != "All" else None

tab1, tab2 = st.tabs(["🏪 Pharmacy Performance", "👨‍⚕️ HCP Analytics"])

with tab1:
    @st.cache_data(ttl=300)
    def load_pharmacies(r):
        return get_pharmacy_performance(region=r, limit=100)

    try:
        pha_df = load_pharmacies(region)
    except Exception as e:
        st.error(f"Failed to load pharmacy data: {e}")
        st.stop()

    if pha_df.empty:
        st.info("No pharmacy data available.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Pharmacies", f"{len(pha_df):,}")
        c2.metric("Avg Adherence", f"{pha_df['adherence_pct'].mean():.1f}%")
        c3.metric("Best Pharmacy", f"{pha_df['adherence_pct'].max():.1f}%")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏆 Top 15 Pharmacies")
            top = pha_df.nlargest(15, "adherence_pct")
            fig = px.bar(top, x="adherence_pct", y="pharmacy_name", orientation="h",
                         color="adherence_pct",
                         color_continuous_scale=["#fb923c","#4ade80"])
            fig.update_layout(
                plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font=dict(color="#e2e8f0"), height=380, coloraxis_showscale=False,
                yaxis=dict(title=""), xaxis=dict(title="Adherence %", gridcolor="#1e293b"),
                margin=dict(l=20, r=20, t=10, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### ⚠️ Bottom 15 Pharmacies")
            bot = pha_df.nsmallest(15, "adherence_pct")
            fig = px.bar(bot, x="adherence_pct", y="pharmacy_name", orientation="h",
                         color="adherence_pct",
                         color_continuous_scale=["#f87171","#fb923c"])
            fig.update_layout(
                plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font=dict(color="#e2e8f0"), height=380, coloraxis_showscale=False,
                yaxis=dict(title=""), xaxis=dict(title="Adherence %", gridcolor="#1e293b"),
                margin=dict(l=20, r=20, t=10, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📋 Full Pharmacy Table")
        st.dataframe(pha_df, use_container_width=True, height=300)

with tab2:
    @st.cache_data(ttl=300)
    def load_hcps(r):
        where = f"AND h.region = '{r}'" if r else ""
        return _run(f"""
            SELECT h.hcp_id, h.hcp_name, h.specialization, h.hospital, h.region,
                   COUNT(hp.patient_id) AS patient_count,
                   AVG(hp.visit_count) AS avg_visits,
                   MAX(hp.last_visit) AS last_visit
            FROM healthcare.hcp h
            LEFT JOIN healthcare.hcp_patient hp ON h.hcp_id = hp.hcp_id
            WHERE 1=1 {where}
            GROUP BY h.hcp_id, h.hcp_name, h.specialization, h.hospital, h.region
            ORDER BY patient_count DESC LIMIT 100
        """)

    try:
        hcp_df = load_hcps(region)
    except Exception as e:
        st.error(f"Failed to load HCP data: {e}")
        st.stop()

    if not hcp_df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("HCPs", f"{len(hcp_df):,}")
        c2.metric("Avg Patients / HCP", f"{hcp_df['patient_count'].mean():.0f}")
        c3.metric("Top HCP Patients", f"{hcp_df['patient_count'].max():,}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### HCP by Specialization")
            spec = hcp_df.groupby("specialization")["patient_count"].sum().reset_index()
            fig = px.pie(spec, names="specialization", values="patient_count", hole=0.4)
            fig.update_layout(
                plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font=dict(color="#e2e8f0"), height=300,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### Top 10 HCPs by Patient Volume")
            top_hcps = hcp_df.head(10)
            fig = px.bar(top_hcps, x="patient_count", y="hcp_name", orientation="h",
                         color="patient_count", color_continuous_scale=["#818cf8","#38bdf8"])
            fig.update_layout(
                plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font=dict(color="#e2e8f0"), height=300, coloraxis_showscale=False,
                yaxis=dict(title=""), xaxis=dict(title="Patients", gridcolor="#1e293b"),
                margin=dict(l=20, r=20, t=10, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 📋 HCP Table")
        st.dataframe(hcp_df, use_container_width=True, height=300)
