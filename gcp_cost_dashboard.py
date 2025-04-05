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

# 🎯 Page Config
st.set_page_config(page_title="GCP Cost Dashboard", layout="wide")
st.title("💸 GCP Cost Explorer")
st.markdown("Easily track your **Google Cloud costs** with custom filters, visuals, and business-friendly insights.")

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

# 🧰 Filter Options
with st.expander("🔧 Filter Options", expanded=True):
    all_services = df["service"].unique()
    selected_services = st.multiselect("Choose Services", all_services, default=list(all_services))
    df = df[df["service"].isin(selected_services)]

# 📋 Executive Summary
st.markdown("## 📋 Executive Summary")
df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.to_period("M")
monthly_cost = df.groupby("month")["total_cost"].sum().sort_index()

if len(monthly_cost) >= 2:
    latest_month = monthly_cost.index[-1]
    prev_month = monthly_cost.index[-2]
    latest_cost = monthly_cost.iloc[-1]
    prev_cost = monthly_cost.iloc[-2]
    mom_change = ((latest_cost - prev_cost) / prev_cost) * 100 if prev_cost > 0 else 0
    mom_direction = "🔺" if mom_change > 0 else "🔻"
    mom_summary = f"{mom_direction} {abs(mom_change):.2f}% vs {prev_month}"
else:
    latest_cost = monthly_cost.iloc[-1] if not monthly_cost.empty else 0
    mom_summary = "Not enough data"

top_service = df.groupby("service")["total_cost"].sum().idxmax() if not df.empty else "N/A"
top_service_cost = df.groupby("service")["total_cost"].sum().max() if not df.empty else 0

col1, col2, col3 = st.columns(3)
col1.metric("💰 This Month's Spend", f"${latest_cost:,.2f}")
col2.metric("📊 MoM Change", mom_summary)
col3.metric("🚀 Top Contributor", f"{top_service} (${top_service_cost:,.2f})")

# 📉 Monthly Cost Trend
st.markdown("### 📉 Monthly Cost Trend")
monthly_df = monthly_cost.reset_index()
monthly_df["month"] = monthly_df["month"].astype(str)
bar = alt.Chart(monthly_df).mark_bar().encode(
    x=alt.X("month", title="Month"),
    y=alt.Y("total_cost", title="Total Cost"),
    tooltip=["month", "total_cost"]
).properties(width=800, height=400)
st.altair_chart(bar, use_container_width=True)

# 📌 Key Metrics
st.markdown("### 📊 Key Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("💰 Total Spend (Selected)", f"${df['total_cost'].sum():,.2f}")
if not df.empty:
    top_service = df.groupby("service")["total_cost"].sum().idxmax()
    peak_day = df.groupby("date")["total_cost"].sum().idxmax()
    col2.metric("🚀 Top Service", top_service)
    col3.metric("📈 Peak Spend Day", peak_day.strftime("%Y-%m-%d"))

# 💼 Budget vs Actual Comparison
st.markdown("### 💼 Budget vs Actual Comparison")

services_in_data = df["service"].unique()
st.markdown("#### Set Monthly Budgets ($)")
budget_inputs = {}
cols = st.columns(len(services_in_data) if len(services_in_data) <= 4 else 4)

for idx, service in enumerate(services_in_data):
    col = cols[idx % len(cols)]
    budget_inputs[service] = col.number_input(
        f"{service}",
        min_value=0.0,
        value=0.0,
        step=100.0,
        format="%.2f"
    )

budget_df = pd.DataFrame([
    {
        "Service": service,
        "Budget ($)": budget_inputs[service],
        "Actual ($)": df[df["service"] == service]["total_cost"].sum()
    }
    for service in services_in_data
])

budget_df["Variance ($)"] = budget_df["Actual ($)"] - budget_df["Budget ($)"]
budget_df["% Difference"] = budget_df.apply(
    lambda row: (row["Variance ($)"] / row["Budget ($)"] * 100) if row["Budget ($)"] > 0 else 0,
    axis=1
)
budget_df["Status"] = budget_df["Variance ($)"].apply(
    lambda x: "✅ Under" if x <= 0 else "❌ Over"
)

st.dataframe(budget_df.style
    .applymap(lambda x: "color: red;" if isinstance(x, float) and x > 0 else "color: green;", subset=["Variance ($)", "% Difference"])
    .format({"Budget ($)": "${:,.2f}", "Actual ($)": "${:,.2f}", "Variance ($)": "${:,.2f}", "% Difference": "{:.1f}%"})
)

# 📊 Visual Tabs
st.markdown("### 🔍 Cost Breakdown")

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

# 🧾 Raw Data View
with st.expander("🧾 Full Billing Data"):
    st.dataframe(df, use_container_width=True)
