"""
Industry composition treemap — 2-digit NAICS sectors,
sized by employment, colored by average annual wage.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.clean import get_naics_sectors, get_latest_quarter
from utils.formatting import fmt_number, fmt_currency, fmt_pct
from utils.narratives import source_citation


def render(df: pd.DataFrame):
    """Render industry composition treemap for Palm Beach County."""
    st.header("Industry Composition")

    sectors = get_naics_sectors(df, own_code=5)
    latest = get_latest_quarter(sectors)

    if latest.empty:
        st.info("No industry data available.")
        return

    plot_data = latest[
        (~latest["is_suppressed"]) & (latest["employment"] > 0)
    ].copy()

    if plot_data.empty:
        st.info("No disclosable industry data for this quarter.")
        return

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Narrative
    total_empl = plot_data["employment"].sum()
    top3 = plot_data.nlargest(3, "employment")
    top_shares = [
        (row["industry_label"], row["employment"] / total_empl * 100)
        for _, row in top3.iterrows()
    ]
    formatted = [f"{name} ({fmt_pct(share)})" for name, share in top_shares]
    listing = ", ".join(formatted[:-1]) + f", and {formatted[-1]}"

    st.markdown(
        f"In {year} Q{qtr}, Palm Beach County's private sector employed "
        f"{fmt_number(total_empl)} workers across {len(plot_data)} industries. "
        f"The largest by employment share were {listing}."
    )

    fig = px.treemap(
        plot_data,
        path=["industry_label"],
        values="employment",
        color="avg_annual_wage",
        color_continuous_scale="Plasma",
        labels={"avg_annual_wage": "Avg Annual Wage"},
        custom_data=["industry_label", "employment", "avg_annual_wage"],
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Employment: %{customdata[1]:,.0f}<br>"
            "Avg Annual Wage: $%{customdata[2]:,.0f}<br>"
            "<extra></extra>"
        ),
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>%{value:,.0f}",
    )

    fig.update_layout(
        height=600,
        coloraxis_colorbar=dict(
            title="Avg Annual<br>Wage ($)",
            tickformat="$,.0f",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
