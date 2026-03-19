"""
Wage landscape — horizontal bars showing sectors ranked by average annual wage.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.clean import get_naics_sectors, get_latest_quarter
from utils.formatting import fmt_currency
from utils.narratives import narrate_wage_distribution, source_citation


def render(df: pd.DataFrame):
    """Render horizontal bar chart of wages by industry."""
    st.header("Wage Landscape")

    sectors = get_naics_sectors(df, own_code=5)
    latest = get_latest_quarter(sectors)

    if latest.empty:
        st.info("No wage data available.")
        return

    plot_data = latest[
        (~latest["is_suppressed"])
        & (latest["avg_annual_wage"].notna())
        & (latest["employment"] > 0)
    ].copy()

    if plot_data.empty:
        st.info("No disclosable wage data for this quarter.")
        return

    # Sort by wage for the chart
    plot_data = plot_data.sort_values("avg_annual_wage", ascending=True)

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Weighted average wage
    weighted_avg = (
        (plot_data["avg_annual_wage"] * plot_data["employment"]).sum()
        / plot_data["employment"].sum()
    )

    # Narrative
    highest = plot_data.iloc[-1]
    lowest = plot_data.iloc[0]
    st.markdown(narrate_wage_distribution(
        county_name="Palm Beach",
        year=year,
        qtr=qtr,
        highest_industry=highest["industry_label"],
        highest_wage=highest["avg_annual_wage"],
        lowest_industry=lowest["industry_label"],
        lowest_wage=lowest["avg_annual_wage"],
        overall_avg=weighted_avg,
    ))

    fig = px.bar(
        plot_data,
        x="avg_annual_wage",
        y="industry_label",
        orientation="h",
        color="avg_annual_wage",
        color_continuous_scale="Plasma",
        labels={"avg_annual_wage": "Avg Annual Wage", "industry_label": ""},
        custom_data=["industry_label", "avg_annual_wage", "employment"],
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Avg Annual Wage: $%{customdata[1]:,.0f}<br>"
            "Employment: %{customdata[2]:,.0f}<br>"
            "<extra></extra>"
        ),
    )

    # Reference line at weighted average
    fig.add_vline(
        x=weighted_avg,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Avg: {fmt_currency(weighted_avg)}",
        annotation_position="top",
    )

    fig.update_layout(
        xaxis_tickformat="$,.0f",
        height=max(450, len(plot_data) * 28),
        showlegend=False,
        coloraxis_showscale=False,
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
