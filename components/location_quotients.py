"""
Location quotients — how Palm Beach's industry mix compares to the national average.
LQ > 1 means the industry is more concentrated locally than nationally.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.clean import get_naics_sectors, get_latest_quarter
from utils.formatting import fmt_number
from utils.narratives import source_citation


def render(df: pd.DataFrame):
    """Render horizontal bar chart of employment location quotients by sector."""
    st.header("Location Quotients")

    sectors = get_naics_sectors(df, own_code=5)
    latest = get_latest_quarter(sectors)

    if latest.empty:
        st.info("No location quotient data available.")
        return

    plot_data = latest[
        (~latest["is_suppressed"])
        & (latest["employment"] > 0)
        & (latest["lq_month3_emplvl"].notna())
        & (latest["industry_label"] != "Unclassified")
    ].copy()

    if plot_data.empty:
        st.info("No disclosable location quotient data for this quarter.")
        return

    plot_data = plot_data.sort_values("lq_month3_emplvl", ascending=True)

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Narrative: identify specializations and underrepresented sectors
    specialized = plot_data[plot_data["lq_month3_emplvl"] > 1.0].nlargest(
        3, "lq_month3_emplvl"
    )
    underrep = plot_data[plot_data["lq_month3_emplvl"] < 1.0].nsmallest(
        3, "lq_month3_emplvl"
    )

    parts = [
        f"A location quotient (LQ) compares an industry's local employment share "
        f"to the national average. An LQ above 1.0 means the industry is more "
        f"concentrated in Palm Beach than in the U.S. overall."
    ]

    if not specialized.empty:
        top_names = [
            f"{row['industry_label']} ({row['lq_month3_emplvl']:.2f})"
            for _, row in specialized.iterrows()
        ]
        if len(top_names) >= 3:
            listing = ", ".join(top_names[:-1]) + f", and {top_names[-1]}"
        elif len(top_names) == 2:
            listing = f"{top_names[0]} and {top_names[1]}"
        else:
            listing = top_names[0]
        parts.append(
            f" In {year} Q{qtr}, Palm Beach's most specialized industries were {listing}."
        )

    if not underrep.empty:
        bottom = underrep.iloc[0]
        parts.append(
            f" {bottom['industry_label']} was the most underrepresented "
            f"({bottom['lq_month3_emplvl']:.2f})."
        )

    st.markdown("".join(parts))

    # Diverging bar chart centered at 1.0
    fig = px.bar(
        plot_data,
        x="lq_month3_emplvl",
        y="industry_label",
        orientation="h",
        color="lq_month3_emplvl",
        color_continuous_scale="RdBu",
        color_continuous_midpoint=1.0,
        labels={
            "lq_month3_emplvl": "Location Quotient",
            "industry_label": "",
        },
        custom_data=["industry_label", "lq_month3_emplvl", "employment"],
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "LQ: %{customdata[1]:.2f}<br>"
            "Employment: %{customdata[2]:,.0f}<br>"
            "<extra></extra>"
        ),
    )

    # Reference line at 1.0 (national average)
    fig.add_vline(
        x=1.0,
        line_color="black",
        line_width=1.5,
        line_dash="dash",
        annotation_text="U.S. Average",
        annotation_position="top",
    )

    fig.update_layout(
        xaxis_title="Location Quotient (1.0 = National Average)",
        height=max(450, len(plot_data) * 28),
        showlegend=False,
        coloraxis_showscale=False,
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
