"""
dashboard/pages/04_🔄_Data_Quality.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()

import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Data Quality", page_icon="🔄", layout="wide")
st.markdown("# 🔄 Data Quality & ETL Monitoring")
st.markdown("*Monitor ETL pipeline health and data validation results*")
st.markdown("---")

from sql.analytics_queries import get_etl_status

@st.cache_data(ttl=60)
def load_etl():
    return get_etl_status()

try:
    etl_df = load_etl()
except Exception as e:
    st.error(f"Cannot connect to database: {e}")
    st.stop()

col_a, col_b = st.columns([3, 1])

with col_a:
    # Latest run summary
    if not etl_df.empty:
        latest_ts = etl_df["run_timestamp"].max()
        latest_run = etl_df[etl_df["run_timestamp"] == latest_ts]
        total_src   = latest_run["total_records"].sum()
        total_valid = latest_run["valid_records"].sum()
        total_rej   = latest_run["rejected_records"].sum()
        total_dups  = latest_run["duplicate_records"].sum()
        quality_pct = (total_valid / max(total_src, 1)) * 100

        st.markdown(f"**Latest ETL Run:** `{latest_ts}`")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Source Records", f"{total_src:,}")
        c2.metric("Valid Records",  f"{total_valid:,}")
        c3.metric("Rejected",       f"{total_rej:,}")
        c4.metric("Duplicates",     f"{total_dups:,}")
        c5.metric("Quality Score",  f"{quality_pct:.1f}%")

        st.markdown("---")
        st.markdown("#### Per-Table Quality Breakdown")
        fig = px.bar(
            latest_run, x="table_name", y=["valid_records","rejected_records"],
            barmode="stack",
            color_discrete_map={"valid_records":"#4ade80","rejected_records":"#f87171"},
            labels={"value":"Records","variable":"Type"},
        )
        fig.update_layout(
            plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
            font=dict(color="#e2e8f0"), height=300,
            xaxis=dict(title="Table", gridcolor="#1e293b"),
            yaxis=dict(title="Record Count", gridcolor="#1e293b"),
            margin=dict(l=20, r=20, t=10, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### ETL Run Log")
        st.dataframe(etl_df.head(50), use_container_width=True, height=300)
    else:
        st.warning("No ETL runs found in database. Run the ETL pipeline first.")

with col_b:
    st.markdown("#### ▶ Run ETL Pipeline")
    st.markdown("*Executes full Extract → Validate → Transform → Load pipeline*")

    if st.button("🚀 Run ETL Now", type="primary", use_container_width=True):
        with st.spinner("Running ETL pipeline..."):
            try:
                from etl.pipeline import run_pipeline
                result = run_pipeline()
                st.success(f"✅ ETL completed in {result['elapsed_seconds']}s")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"ETL failed: {e}")

    if st.button("🔍 Dry Run (validate only)", use_container_width=True):
        with st.spinner("Validating data..."):
            try:
                from etl.pipeline import run_pipeline
                result = run_pipeline(skip_load=True)
                st.success("✅ Validation complete")
                for table, rpt in result.get("quality_reports", {}).items():
                    pct = rpt.get("valid_records", 0) / max(rpt.get("total_records", 1), 1) * 100
                    st.write(f"**{table}**: {pct:.1f}% valid")
            except Exception as e:
                st.error(f"Validation failed: {e}")

    st.markdown("---")
    st.markdown("#### 📁 Rejected Records")
    rej_dir = Path(__file__).resolve().parent.parent.parent / "data" / "rejected"
    rej_files = sorted(rej_dir.glob("*.csv")) if rej_dir.exists() else []
    if rej_files:
        for f in rej_files[-5:]:  # Show last 5
            st.download_button(
                label=f.name,
                data=f.read_bytes(),
                file_name=f.name,
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.info("No rejected record files found.")
