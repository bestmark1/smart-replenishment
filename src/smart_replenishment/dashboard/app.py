import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Title and Premium Theme
st.set_page_config(
    page_title="Smart Replenishment Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 38px;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 5px;
    }
    .subtitle {
        font-size: 16px;
        color: #4B5563;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2563EB;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📦 Smart Replenishment Decision Support</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Demand Forecasting & Inventory Optimization Dashboard for Retail Managers</div>', unsafe_allow_html=True)

# Data paths
FORECAST_PATH = "data/processed/final_test_forecast.parquet"
PRIORITY_PATH = "data/processed/priority_results.parquet"

# Load data helper
@st.cache_data
def load_dashboard_data():
    if not os.path.exists(FORECAST_PATH) or not os.path.exists(PRIORITY_PATH):
        return None, None

    df_forecast = pd.read_parquet(FORECAST_PATH)
    df_forecast["date"] = pd.to_datetime(df_forecast["date"])
    df_forecast["dept_id"] = df_forecast["item_id"].apply(lambda x: "_".join(x.split("_")[:2]))

    df_priorities = pd.read_parquet(PRIORITY_PATH)
    df_priorities["dept_id"] = df_priorities["item_id"].apply(lambda x: "_".join(x.split("_")[:2]))

    return df_forecast, df_priorities

df_forecast, df_priorities = load_dashboard_data()

if df_forecast is None or df_priorities is None:
    st.error("Missing process artifacts! Please run the pipeline `make pipeline && make train && make evaluate && make simulate` first.")
else:
    # Sidebar filters
    st.sidebar.header("Filter Scope")
    stores = sorted(df_priorities["store_id"].unique())
    selected_store = st.sidebar.selectbox("Select Store", stores)

    depts = sorted(df_priorities["dept_id"].unique())
    selected_dept = st.sidebar.selectbox("Select Department", depts)

    # Filter priorities
    df_p_filtered = df_priorities[
        (df_priorities["store_id"] == selected_store) &
        (df_priorities["dept_id"] == selected_dept)
    ]

    # Filter forecasts
    df_f_filtered = df_forecast[
        (df_forecast["store_id"] == selected_store) &
        (df_forecast["dept_id"] == selected_dept)
    ]

    # 1. Key Metrics row
    # Calculate Service Level and total financial metrics in scope
    total_demand = df_p_filtered["total_demand"].sum()
    total_lost = df_p_filtered["total_lost_demand"].sum()
    service_level = (total_demand - total_lost) / total_demand if total_demand > 0 else 1.0

    total_holding = df_p_filtered["total_holding_cost"].sum()
    total_penalties = df_p_filtered["total_penalty"].sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label="Service Level (SL)",
            value=f"{service_level * 100:.2f}%",
            delta="Target: 95.0%",
            delta_color="off"
        )
    with col2:
        st.metric(label="Total Demand (Units)", value=f"{total_demand:,.0f}")
    with col3:
        st.metric(label="Holding Costs Proxy", value=f"${total_holding:,.2f}")
    with col4:
        st.metric(label="Stockout Penalty Proxy", value=f"${total_penalties:,.2f}")

    # 2. Main layout: Priorities vs. Series Plot
    st.write("---")
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("📋 Top Replenishment Priorities")
        st.markdown("SKUs with the highest risk of deficit value (lost sales potential):")

        # Display top 10
        display_df = df_p_filtered.head(10)[
            ["item_id", "service_level", "total_lost_demand", "priority_value"]
        ].copy()

        display_df["service_level"] = display_df["service_level"].apply(lambda x: f"{x*100:.1f}%")
        display_df["total_lost_demand"] = display_df["total_lost_demand"].apply(lambda x: f"{x:,.0f}")
        display_df["priority_value"] = display_df["priority_value"].apply(lambda x: f"${x:,.2f}")

        st.dataframe(display_df, use_container_width=True)

    with right_col:
        st.subheader("📈 Series Forecast Visualization")

        # Dropdown to select item
        items_in_scope = sorted(df_p_filtered["item_id"].unique())
        selected_item = st.selectbox("Select SKU to view forecast", items_in_scope)

        # Filter series forecast
        series_df = df_f_filtered[df_f_filtered["item_id"] == selected_item].sort_values("date")

        # Create Plotly Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=series_df["date"],
            y=series_df["demand"],
            mode='lines+markers',
            name='Actual Demand',
            line=dict(color='black', width=2),
            marker=dict(size=5)
        ))
        fig.add_trace(go.Scatter(
            x=series_df["date"],
            y=series_df["forecast"],
            mode='lines+markers',
            name='LightGBM Forecast',
            line=dict(color='orange', width=2, dash='dash'),
            marker=dict(size=5)
        ))

        fig.update_layout(
            title=f"Demand Forecast for {selected_item} at Store {selected_store}",
            xaxis_title="Date",
            yaxis_title="Units",
            legend=dict(x=0, y=1, orientation='h'),
            margin=dict(l=20, r=20, t=40, b=20),
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)

    # 3. Model limitations and assumptions section
    st.write("---")
    st.info("""
    **⚠️ Educational Simulator Disclaimer & Assumptions:**
    * **Periodic Review:** Orders are simulated once daily at midnight.
    * **Lead Time:** 7 days fixed delivery lag between ordering and receipt.
    * **Holding Cost:** Configured at 5% of item price per day.
    * **Stockout Penalty:** Configured at 1.5x of retail price.
    * **Stock Levels:** Real store inventory positions are not represented; all values are computed by the replenishment policy simulator.
    """)
