import os
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import altair as alt

# Load credentials
SERVICE_ACCOUNT_KEY = r"C:\Yellow.ai\Streamlit_Dashboard_Cloud_Cost\ym-region-jakarta-fcce3479d4f1.json"
PROJECT_ID = "ym-region-jakarta"
DATASET = "cost_analysis"
TABLE = "gcp_billing_export_resource_v1_01D002_3ABED8_D58F96"

# Authenticate
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY)
client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

# 🎯 Title and Intro
st.set_page_config(page_title="GCP Cost Dashboard", layout="wide")
st.title("💸 GCP Cost Explorer")
st.markdown("Easily track your **Google Cloud costs** with custom filters, visuals, and exports.")

# 📅 Date Range Picker
with st.container():
    st.markdown("### 📅 Date Range Filter")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", pd.to_datetime("today") - pd.Timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", pd.to_datetime("today"))

# 🧠 Load Data
@st.cache_data(ttl=3600)
def load_cost_data(start_date, end_date):
    query = f"""
    SELECT
      service.description AS service,
      DATE(usage_start_time) AS date,
      ROUND(SUM(cost), 2) AS total_cost
    FROM
      `{PROJECT_ID}.{DATASET}.{TABLE}`
    WHERE
      usage_start_time BETWEEN TIMESTAMP('{start_date}') AND TIMESTAMP('{end_date}')
    GROUP BY
      service, date
    ORDER BY
      date DESC
    """
    return client.query(query).result().to_dataframe()

df = load_cost_data(start_date, end_date)

# 🧰 Filters
with st.expander("🔧 Filter Options", expanded=True):
    all_services = df["service"].unique()
    selected_services = st.multiselect("Choose Services", all_services, default=list(all_services))
    df = df[df["service"].isin(selected_services)]

# 📌 KPIs
with st.container():
    st.markdown("### 📊 Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Spend", f"${df['total_cost'].sum():,.2f}")
    if not df.empty:
        top_service = df.groupby("service")["total_cost"].sum().idxmax()
        peak_day = df.groupby("date")["total_cost"].sum().idxmax()
        col2.metric("🚀 Top Service", top_service)
        col3.metric("📈 Peak Spend Day", peak_day.strftime("%Y-%m-%d"))

# 📊 Visuals
st.markdown("### 📉 Cost Breakdown")

tab1, tab2, tab3 = st.tabs(["By Service", "Daily Trend", "Service Drilldown"])

with tab1:
    cost_by_service = df.groupby("service")["total_cost"].sum().sort_values(ascending=False)
    st.bar_chart(cost_by_service)

with tab2:
    daily_cost = df.groupby("date")["total_cost"].sum().sort_index()
    line = alt.Chart(daily_cost.reset_index()).mark_line().encode(
        x="date:T", y="total_cost:Q", tooltip=["date", "total_cost"]
    ).properties(width=800, height=400)
    st.altair_chart(line, use_container_width=True)

with tab3:
    if not df.empty:
        service_to_inspect = st.selectbox("Select a Service", cost_by_service.index)
        service_trend = df[df["service"] == service_to_inspect].groupby("date")["total_cost"].sum()
        st.line_chart(service_trend)

# 🧾 Detailed Data
with st.expander("🧾 Full Billing Data"):
    st.dataframe(df, use_container_width=True)

# 📤 Export Button
st.download_button("📥 Download as CSV", df.to_csv(index=False), file_name="gcp_costs.csv", use_container_width=True)
