"""
Wage-employment scatter — each dot is an industry sector.
X = employment, Y = avg annual wage, size = establishments.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.clean import get_naics_sectors, get_latest_quarter
from utils.formatting import fmt_number, fmt_currency
from utils.narratives import source_citation


def render(df: pd.DataFrame):
    """Render wage vs employment scatter plot by industry."""
    st.header("Wage–Employment Landscape")

    sectors = get_naics_sectors(df, own_code=5)
    latest = get_latest_quarter(sectors)

    if latest.empty:
        st.info("No industry data available.")
        return

    plot_data = latest[
        (~latest["is_suppressed"])
        & (latest["employment"] > 0)
        & (latest["avg_annual_wage"].notna())
        & (latest["industry_label"] != "Unclassified")
    ].copy()

    if plot_data.empty:
        st.info("No disclosable industry data for this quarter.")
        return

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Compute weighted average wage for reference lines
    weighted_avg_wage = (
        (plot_data["avg_annual_wage"] * plot_data["employment"]).sum()
        / plot_data["employment"].sum()
    )
    median_empl = plot_data["employment"].median()

    # Narrative
    anchor = plot_data[
        (plot_data["employment"] > median_empl)
        & (plot_data["avg_annual_wage"] > weighted_avg_wage)
    ]
    volume = plot_data[
        (plot_data["employment"] > median_empl)
        & (plot_data["avg_annual_wage"] <= weighted_avg_wage)
    ]

    parts = [
        f"In {year} Q{qtr}, each dot represents a 2-digit NAICS sector. "
        f"Dot size reflects the number of establishments."
    ]
    if not anchor.empty:
        names = anchor.nlargest(3, "employment")["industry_label"].tolist()
        listing = ", ".join(names[:-1]) + f", and {names[-1]}" if len(names) > 1 else names[0]
        parts.append(
            f" The largest high-wage, high-employment sectors — the county's "
            f"anchor industries — are {listing}."
        )
    if not volume.empty:
        names = volume.nlargest(2, "employment")["industry_label"].tolist()
        listing = " and ".join(names)
        parts.append(
            f" {listing} employ large workforces at below-average wages."
        )

    st.markdown("".join(parts))

    fig = px.scatter(
        plot_data,
        x="employment",
        y="avg_annual_wage",
        size="qtrly_estabs",
        text="industry_label",
        labels={
            "employment": "Employment",
            "avg_annual_wage": "Avg Annual Wage",
            "qtrly_estabs": "Establishments",
        },
        custom_data=["industry_label", "employment", "avg_annual_wage", "qtrly_estabs"],
    )

    fig.update_traces(
        textposition="top center",
        textfont_size=9,
        marker=dict(
            color=plot_data["avg_annual_wage"],
            colorscale="Plasma",
            line=dict(width=1, color="white"),
            sizemin=8,
        ),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Employment: %{customdata[1]:,.0f}<br>"
            "Avg Annual Wage: $%{customdata[2]:,.0f}<br>"
            "Establishments: %{customdata[3]:,.0f}<br>"
            "<extra></extra>"
        ),
    )

    # Reference lines: weighted avg wage (horizontal) and median employment (vertical)
    fig.add_hline(
        y=weighted_avg_wage,
        line_dash="dash",
        line_color="gray",
        line_width=1,
        annotation_text=f"Avg Wage: {fmt_currency(weighted_avg_wage)}",
        annotation_position="top left",
    )
    fig.add_vline(
        x=median_empl,
        line_dash="dash",
        line_color="gray",
        line_width=1,
        annotation_text=f"Median Employment: {fmt_number(median_empl)}",
        annotation_position="top right",
    )

    fig.update_layout(
        xaxis_tickformat=",.0f",
        yaxis_tickformat="$,.0f",
        height=550,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
