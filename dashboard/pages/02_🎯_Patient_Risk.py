"""
dashboard/pages/02_🎯_Patient_Risk.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Patient Risk", page_icon="🎯", layout="wide")
st.markdown("# 🎯 Patient Risk Analysis")
st.markdown("*Identify and prioritize high-risk patients with AI-powered risk scores*")
st.markdown("---")

from sql.analytics_queries import get_all_patients, get_patient_detail

# ── Filters ────────────────────────────────────────────────────
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
with col_f1:
    region_filter = st.selectbox("Region", ["All", "North", "South", "East", "West", "Central"])
with col_f2:
    risk_filter = st.selectbox("Risk Level", ["All", "HIGH", "MEDIUM", "LOW"])
with col_f3:
    search = st.text_input("Search Patient ID", placeholder="e.g. P10001")
with col_f4:
    limit = st.slider("Max Patients", 50, 500, 200)

@st.cache_data(ttl=120)
def load_patients(region, risk_level, lim):
    r = region if region != "All" else None
    rl = risk_level if risk_level != "All" else None
    return get_all_patients(region=r, risk_level=rl, limit=lim)

try:
    df = load_patients(
        region_filter if region_filter != "All" else None,
        risk_filter if risk_filter != "All" else None,
        limit
    )
except Exception as e:
    st.error(f"Database connection failed: {e}")
    st.stop()

if search:
    df = df[df["patient_id"].str.contains(search, case=False)]

if df.empty:
    st.warning("No patients match the current filters.")
    st.stop()

# ── Summary Metrics ────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Shown", f"{len(df):,}")
c2.metric("High Risk", f"{(df['risk_level'] == 'HIGH').sum():,}")
c3.metric("Avg Risk Score", f"{df['risk_score'].mean():.2f}" if "risk_score" in df.columns else "N/A")
c4.metric("Avg Adherence", f"{df['adherence_pct'].mean():.1f}%" if "adherence_pct" in df.columns else "N/A")

st.markdown("---")

# ── Risk Distribution Charts ───────────────────────────────────
cc1, cc2 = st.columns(2)

with cc1:
    if "risk_score" in df.columns:
        fig = px.histogram(
            df, x="risk_score", color="risk_level",
            color_discrete_map={"HIGH": "#f87171", "MEDIUM": "#fb923c", "LOW": "#4ade80"},
            nbins=30, title="Risk Score Distribution",
        )
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"), height=250,
            xaxis=dict(title="Risk Score", gridcolor="#1e293b"),
            yaxis=dict(title="Patient Count", gridcolor="#1e293b"),
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

with cc2:
    if "region" in df.columns and "risk_level" in df.columns:
        risk_by_region = df.groupby(["region","risk_level"]).size().reset_index(name="count")
        fig = px.bar(
            risk_by_region, x="region", y="count", color="risk_level",
            color_discrete_map={"HIGH": "#f87171", "MEDIUM": "#fb923c", "LOW": "#4ade80"},
            title="Risk by Region",
        )
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"), height=250,
            xaxis=dict(title="Region", gridcolor="#1e293b"),
            yaxis=dict(title="Patients", gridcolor="#1e293b"),
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Patient Table ──────────────────────────────────────────────
st.markdown("### 📋 Patient Table")

def color_risk(val):
    colors = {"HIGH": "background-color:#7f1d1d;color:#fca5a5",
              "MEDIUM": "background-color:#78350f;color:#fde68a",
              "LOW": "background-color:#14532d;color:#86efac"}
    return colors.get(val, "")

display_cols = ["patient_id","age","region","chronic_condition",
                "adherence_pct","last_refill_date","days_since_refill",
                "risk_score","risk_level","top_factor"]
disp_df = df[[c for c in display_cols if c in df.columns]].copy()

# Make risk_score readable
if "risk_score" in disp_df.columns:
    disp_df["risk_score"] = disp_df["risk_score"].apply(lambda x: f"{float(x):.2%}" if pd.notna(x) else "N/A")

styled = disp_df.style.applymap(color_risk, subset=["risk_level"] if "risk_level" in disp_df.columns else [])
st.dataframe(styled, use_container_width=True, height=350)

# ── Patient Detail ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔍 Patient Detail")
selected_id = st.text_input("Enter Patient ID for detailed view:", placeholder="e.g. P10001")

if selected_id:
    with st.spinner("Loading patient profile..."):
        try:
            detail = get_patient_detail(selected_id.strip())
        except Exception as e:
            st.error(f"Could not load patient: {e}")
            st.stop()

    if not detail.get("patient"):
        st.warning(f"Patient {selected_id} not found.")
    else:
        p = detail["patient"]
        risk = detail.get("risk", {})

        dp1, dp2, dp3 = st.columns(3)
        with dp1:
            st.markdown("**Patient Profile**")
            st.markdown(f"""
            - **ID:** {p.get('patient_id','N/A')}
            - **Age:** {p.get('age','N/A')}
            - **Gender:** {p.get('gender','N/A')}
            - **Region:** {p.get('region','N/A')}
            - **City:** {p.get('city','N/A')}
            - **Insurance:** {p.get('insurance_type','N/A')}
            - **Condition:** {p.get('chronic_condition','N/A')}
            """)
        with dp2:
            st.markdown("**Risk Assessment**")
            if risk:
                level = risk.get('risk_level','N/A')
                score = risk.get('risk_score', 0)
                badge_color = {"HIGH":"#f87171","MEDIUM":"#fb923c","LOW":"#4ade80"}.get(level,"gray")
                st.markdown(f"**Risk Score:** {float(score):.2%}")
                st.markdown(f"**Risk Level:** <span style='color:{badge_color};font-weight:700'>{level}</span>", unsafe_allow_html=True)
                st.markdown(f"**Top Factor:** {risk.get('top_factor','N/A')}")
                st.markdown(f"**Assessed:** {risk.get('prediction_date','N/A')}")
            else:
                st.info("No risk assessment available. Run ML prediction.")
        with dp3:
            st.markdown("**Medication**")
            st.markdown(f"- **Drug:** {p.get('drug_name','N/A')}")
            st.markdown(f"- **Category:** {p.get('drug_category','N/A')}")

        # Refill history
        st.markdown("#### Refill History (Last 20)")
        refills = detail.get("refills", [])
        if refills:
            ref_df = pd.DataFrame(refills)
            if "was_on_time" in ref_df.columns:
                ref_df["status"] = ref_df["was_on_time"].apply(
                    lambda x: "✅ On Time" if x else "❌ Missed"
                )
            st.dataframe(ref_df, use_container_width=True, height=200)
        else:
            st.info("No refill history found.")

        # Engagements
        st.markdown("#### Engagement History (Last 10)")
        engs = detail.get("engagements", [])
        if engs:
            st.dataframe(pd.DataFrame(engs), use_container_width=True, height=180)
        else:
            st.info("No engagement records found.")
