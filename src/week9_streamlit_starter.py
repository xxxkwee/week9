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

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f4f8ff 0%, #edf3ff 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            color: #163a63;
        }
        div[data-testid="stMetricContainer"] {
            background: linear-gradient(135deg, #ffffff 0%, #eef5ff 100%);
            border: 1px solid #dfeaf9;
            border-radius: 18px;
            box-shadow: 0 8px 20px rgba(17, 59, 104, 0.08);
            padding: 0.8rem 1rem;
        }
        .stSidebar .block-container {
            background: rgba(255, 255, 255, 0.8);
            border-radius: 18px;
            padding-top: 1rem;
        }
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
        }
        .insight-box {
            background: linear-gradient(135deg, #ffffff 0%, #f1f6ff 100%);
            border: 1px solid #dfeafe;
            border-left: 5px solid #3b82f6;
            border-radius: 16px;
            padding: 1rem 1.25rem;
            box-shadow: 0 8px 18px rgba(59, 130, 246, 0.08);
            color: #1b3050;
            margin: 1rem 0 1.5rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "processed_data_cube.csv"


@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)


def classify_risk_tier(row):
    burden_score = {"No Debt": 0, "Low Burden": 1, "High Burden": 2}
    ratio_score = {"<1x": 0, "1x-3x": 1, "3x-5x": 2, ">5x": 3}

    score = (
        burden_score.get(str(row.get("BURDEN_CAT", "Low Burden")), 1)
        + ratio_score.get(str(row.get("CREDIT_INCOME_RATIO_GROUP", "1x-3x")), 1)
    )

    if score >= 4:
        return "High Risk"
    if score >= 2:
        return "Medium Risk"
    return "Low Risk"


def format_period(ts):
    return pd.Timestamp(ts).strftime("%b %Y")


def build_insights(filtered_df, risk_summary):
    if filtered_df.empty:
        return "No data in the current selection. Adjust the filters to inspect a broader period or subgroup."

    total_applications = filtered_df["total_applications"].sum()
    total_defaults = filtered_df["total_defaults"].sum()
    default_rate = (total_defaults / total_applications * 100) if total_applications else 0

    top_risk = risk_summary.sort_values("default_rate", ascending=False).iloc[0]
    top_risk_name = top_risk["RISK_TIER"]
    top_risk_default = top_risk["default_rate"]

    highest_group = (
        filtered_df.groupby("NAME_CONTRACT_TYPE", as_index=False)
        .agg(total_applications=("total_applications", "sum"))
        .sort_values("total_applications", ascending=False)
        .iloc[0]
    )

    return (
        f"Current portfolio shows a {default_rate:.2f}% default rate across {total_applications:,.0f} applications. "
        f"{top_risk_name} carries the highest risk profile at {top_risk_default:.2f}% default rate. "
        f"{highest_group['NAME_CONTRACT_TYPE']} is the largest loan segment, contributing {highest_group['total_applications']:,.0f} applications."
    )


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
    available_contract_types = sorted(df["NAME_CONTRACT_TYPE"].dropna().unique())
    available_age_groups = sorted(df["AGE_GROUP"].dropna().unique())
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

        selected_contract_types = st.multiselect(
            "Contract type",
            options=available_contract_types,
            default=available_contract_types,
            help="Filter the dashboard to one or more loan types.",
        )
        selected_age_groups = st.multiselect(
            "Age group",
            options=available_age_groups,
            default=available_age_groups,
            help="Filter the dashboard to one or more age segments.",
        )

        slider_min = pd.Timestamp(available_periods[0]).to_pydatetime().date()
        slider_max = pd.Timestamp(available_periods[-1]).to_pydatetime().date()
        slider_start = pd.Timestamp(start_period).to_pydatetime().date()
        slider_end = pd.Timestamp(end_period).to_pydatetime().date()

        slider_start, slider_end = st.slider(
            "Application period",
            min_value=slider_min,
            max_value=slider_max,
            value=(slider_start, slider_end),
            format="MMM YYYY",
        )

        start_period = pd.Timestamp(slider_start)
        end_period = pd.Timestamp(slider_end)

    if end_period < start_period:
        start_period, end_period = end_period, start_period

    filtered_df = df.loc[
        df["APPLICATION_PERIOD"].between(start_period, end_period)
        & df["NAME_CONTRACT_TYPE"].isin(selected_contract_types)
        & df["AGE_GROUP"].isin(selected_age_groups)
    ].drop(columns="APPLICATION_PERIOD")
    filtered_df = filtered_df.copy()
    filtered_df["RISK_TIER"] = filtered_df.apply(classify_risk_tier, axis=1)

    total_applications = filtered_df["total_applications"].sum()
    total_defaults = filtered_df["total_defaults"].sum()
    total_credit = filtered_df["total_credit"].sum()
    default_rate = (
        total_defaults / total_applications * 100
        if total_applications
        else 0
    )

    risk_summary = (
        filtered_df.groupby("RISK_TIER", as_index=False)
        .agg(
            total_applications=("total_applications", "sum"),
            total_defaults=("total_defaults", "sum"),
        )
        .assign(default_rate=lambda x: x["total_defaults"] / x["total_applications"] * 100)
    )
    risk_summary["RISK_TIER"] = pd.Categorical(
        risk_summary["RISK_TIER"],
        categories=["Low Risk", "Medium Risk", "High Risk"],
        ordered=True,
    )
    risk_summary = risk_summary.sort_values("RISK_TIER")

    high_risk_share = (
        risk_summary.loc[risk_summary["RISK_TIER"] == "High Risk", "total_applications"].sum()
        / total_applications * 100
        if total_applications
        else 0
    )

    selected_range = f"{format_period(start_period)} → {format_period(end_period)}"
    st.caption(f"Selected range: {selected_range}")

    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "Total applications",
        f"{total_applications / 1_000:,.1f}K",
        delta=f"{default_rate:.1f}% avg risk",
        border=True,
        help="Total loan applications included in the selected date range.",
    )
    metric_cols[1].metric(
        "Default rate",
        f"{default_rate:.2f}%",
        delta="portfolio view",
        border=True,
        help="Share of applications that defaulted in the selected window.",
    )
    metric_cols[2].metric(
        "Total credit",
        f"{total_credit / 1_000_000:,.1f}M",
        delta="loan exposure",
        border=True,
        help="Combined credit granted across the filtered segments.",
    )
    metric_cols[3].metric(
        "High risk share",
        f"{high_risk_share:.1f}%",
        delta="at-risk clients",
        border=True,
        help="Share of applications in the highest risk tier.",
    )

    st.markdown(
        f"<div class='insight-box'><strong>Auto insight:</strong> {build_insights(filtered_df, risk_summary)}</div>",
        unsafe_allow_html=True,
    )

    st.subheader("Monthly trend")
    trend_df = (
        filtered_df.assign(
            APPLICATION_PERIOD=pd.to_datetime({
                "year": filtered_df["YEAR_APPLIED"],
                "month": filtered_df["MONTH_APPLIED"],
                "day": 1,
            })
        )
        .groupby("APPLICATION_PERIOD", as_index=False)
        .agg(
            total_applications=("total_applications", "sum"),
            total_defaults=("total_defaults", "sum"),
            total_credit=("total_credit", "sum"),
        )
        .assign(
            default_rate=lambda x: x["total_defaults"] / x["total_applications"] * 100,
            avg_loan_amount=lambda x: x["total_credit"] / x["total_applications"],
        )
    )

    trend_metric = st.selectbox(
        "Trend metric",
        ["Default rate", "Applications", "Total credit", "Avg loan amount"],
        index=0,
        help="Choose the metric shown in the time trend chart.",
    )
    trend_map = {
        "Default rate": "default_rate",
        "Applications": "total_applications",
        "Total credit": "total_credit",
        "Avg loan amount": "avg_loan_amount",
    }
    trend_fig = px.line(
        trend_df,
        x="APPLICATION_PERIOD",
        y=trend_map[trend_metric],
        title=f"{trend_metric} over time",
        color_discrete_sequence=["#2f7ef7"],
    )
    trend_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(trend_fig, width="stretch")

    st.subheader("Risk tier breakdown")
    risk_fig = px.bar(
        risk_summary,
        x="RISK_TIER",
        y="total_applications",
        color="RISK_TIER",
        title="Applications by risk tier",
        text_auto=True,
        color_discrete_map={
            "Low Risk": "#22c55e",
            "Medium Risk": "#f59e0b",
            "High Risk": "#ef4444",
        },
    )
    st.plotly_chart(risk_fig, width="stretch")

    st.dataframe(
        risk_summary[["RISK_TIER", "total_applications", "total_defaults", "default_rate"]]
        .round({"default_rate": 2}),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Risk by age group")
    age_risk_df = (
        filtered_df.groupby(["AGE_GROUP", "RISK_TIER"], as_index=False)
        .agg(total_applications=("total_applications", "sum"), total_defaults=("total_defaults", "sum"))
        .assign(default_rate=lambda x: x["total_defaults"] / x["total_applications"] * 100)
    )
    age_risk_fig = px.bar(
        age_risk_df,
        x="AGE_GROUP",
        y="total_applications",
        color="RISK_TIER",
        barmode="stack",
        title="Risk distribution by age group",
        color_discrete_map={
            "Low Risk": "#22c55e",
            "Medium Risk": "#f59e0b",
            "High Risk": "#ef4444",
        },
    )
    st.plotly_chart(age_risk_fig, width="stretch")

    st.subheader("Burden category by age group")
    burden_df = (
        filtered_df.groupby(["AGE_GROUP", "BURDEN_CAT"], as_index=False)
        .agg(total_applications=("total_applications", "sum"), total_defaults=("total_defaults", "sum"))
        .assign(default_rate=lambda x: x["total_defaults"] / x["total_applications"] * 100)
    )
    burden_fig = px.bar(
        burden_df,
        x="AGE_GROUP",
        y="total_applications",
        color="BURDEN_CAT",
        barmode="stack",
        title="Burden profile by age group",
    )
    st.plotly_chart(burden_fig, width="stretch")

    st.subheader("Region and age comparison")
    comparison_df = (
        filtered_df.groupby(["AGE_GROUP", "NAME_CONTRACT_TYPE"], as_index=False)
        .agg(total_applications=("total_applications", "sum"), total_defaults=("total_defaults", "sum"))
        .assign(default_rate=lambda x: x["total_defaults"] / x["total_applications"] * 100)
    )

    age_contract_fig = px.bar(
        comparison_df,
        x="AGE_GROUP",
        y="total_applications",
        color="NAME_CONTRACT_TYPE",
        barmode="group",
        title="Applications by age group and contract type",
    )
    st.plotly_chart(age_contract_fig, width="stretch")

    comparison_summary = (
        comparison_df.groupby("AGE_GROUP", as_index=False)
        .agg(total_applications=("total_applications", "sum"), total_defaults=("total_defaults", "sum"))
        .assign(default_rate=lambda x: x["total_defaults"] / x["total_applications"] * 100)
    )
    st.dataframe(
        comparison_summary.sort_values("default_rate", ascending=False).round({"default_rate": 2}),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Applications by contract type")

    chart_df = (
        filtered_df.groupby("NAME_CONTRACT_TYPE", as_index=False)
        .agg({"total_applications": "sum"})
    )

    fig = px.bar(
        chart_df,
        x="NAME_CONTRACT_TYPE",
        y="total_applications",
        color="NAME_CONTRACT_TYPE",
        title="Applications by contract type",
    )

    st.plotly_chart(fig, width="stretch")

    st.subheader("Data cube preview")
    st.dataframe(filtered_df.head(20), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
