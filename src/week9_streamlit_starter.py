"""
Streamlit Barebone Starter -- Week 9
========================================
Clone this repo, then run:
    uv run streamlit run src/week9_streamlit_starter.py

This is intentionally minimal. In class we will build it up together:
    - add sidebar filters
    - add KPI metrics
    - add a drilldown chart with a dimension/metric picker
    - publish it to Streamlit Community Cloud

Data source: processed_data_cube.csv, produced by running main.py
(the cube is created by create_cubes() in stage_3_aggregate.py).
"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Home Credit Dashboard", layout="wide")

DATA_PATH = Path(__file__).resolve().parent.parent / "data"/  "processed_data_cube.csv"


@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)


def main():
    st.title("Home Credit Dashboard")
    st.caption("Portfolio performance by application period")

    df = load_data().copy()
    df["APPLICATION_PERIOD"] = pd.to_datetime(
        {
            "year": df["YEAR_APPLIED"],
            "month": df["MONTH_APPLIED"],
            "day": 1,
        }
    )

    available_periods = sorted(df["APPLICATION_PERIOD"].dropna().unique())
    if not available_periods:
        st.warning("No application data is available to display.")
        return

    with st.sidebar:
        st.subheader("Filters")
        range_option = st.selectbox(
            "Quick range",
            ["All available", "Last 6 months", "Last 12 months", "Last 24 months"],
            index=0,
            help="Choose a preset time window.",
        )

        if range_option == "Last 6 months":
            start_period = available_periods[max(0, len(available_periods) - 6)]
            end_period = available_periods[-1]
        elif range_option == "Last 12 months":
            start_period = available_periods[max(0, len(available_periods) - 12)]
            end_period = available_periods[-1]
        elif range_option == "Last 24 months":
            start_period = available_periods[max(0, len(available_periods) - 24)]
            end_period = available_periods[-1]
        else:
            start_period = available_periods[0]
            end_period = available_periods[-1]

        start_period = st.selectbox(
            "Start month",
            options=available_periods,
            index=available_periods.index(start_period),
            format_func=lambda period: pd.Timestamp(period).strftime("%b %Y"),
            key="start_period",
        )
        end_period = st.selectbox(
            "End month",
            options=available_periods,
            index=available_periods.index(end_period),
            format_func=lambda period: pd.Timestamp(period).strftime("%b %Y"),
            key="end_period",
        )

    if end_period < start_period:
        start_period, end_period = end_period, start_period

    filtered_df = df.loc[
        df["APPLICATION_PERIOD"].between(start_period, end_period)
    ].drop(columns="APPLICATION_PERIOD")

    total_applications = filtered_df["total_applications"].sum()
    total_defaults = filtered_df["total_defaults"].sum()
    total_credit = filtered_df["total_credit"].sum()
    default_rate = (
        total_defaults / total_applications * 100
        if total_applications
        else 0
    )

    with st.container(horizontal=True):
        st.metric(
            "Total applications",
            f"{total_applications / 1_000:,.1f}K",
            icon=":material/description:",
            border=True,
        )
        st.metric(
            "Default rate",
            f"{default_rate:.2f}%",
            icon=":material/percent:",
            border=True,
        )
        st.metric(
            "Total credit",
            f"{total_credit / 1_000_000:,.1f}M",
            icon=":material/account_balance:",
            border=True,
        )

    st.subheader("Data cube preview")
    st.dataframe(filtered_df.head(20), width="stretch", hide_index=True)

    st.subheader("Applications by contract type")

    chart_df = (filtered_df
                .groupby("NAME_CONTRACT_TYPE")
                .agg({"total_applications": "sum"})
                .reset_index()
                )

    fig = px.bar(chart_df, 
                 x="NAME_CONTRACT_TYPE",
                 y="total_applications")

    st.plotly_chart(fig, width= 'stretch')


if __name__ == "__main__":
    main()
