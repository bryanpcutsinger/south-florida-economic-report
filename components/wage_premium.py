"""
Wage premium analysis — compares Palm Beach's wages and employment concentration
to national averages using BLS location quotients.
"""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from data.clean import get_naics_sectors, get_latest_quarter
from utils.narratives import source_citation


def render(df: pd.DataFrame):
    """Render scatter plot of employment LQ vs wage LQ by sector."""
    st.header("Wage Premium Analysis")

    sectors = get_naics_sectors(df, own_code=5)
    latest = get_latest_quarter(sectors)

    if latest.empty:
        st.info("No location quotient data available.")
        return

    plot_data = latest[
        (~latest["is_suppressed"])
        & (latest["employment"] > 0)
        & (latest["lq_month3_emplvl"].notna())
        & (latest["lq_avg_wkly_wage"].notna())
        & (latest["industry_label"] != "Unclassified")
    ].copy()

    if plot_data.empty:
        st.info("No disclosable LQ data for this quarter.")
        return

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Classify industries into quadrants
    q1 = plot_data[
        (plot_data["lq_month3_emplvl"] > 1) & (plot_data["lq_avg_wkly_wage"] > 1)
    ]  # More concentrated AND pays more
    q2 = plot_data[
        (plot_data["lq_month3_emplvl"] > 1) & (plot_data["lq_avg_wkly_wage"] <= 1)
    ]  # More concentrated but pays less
    q3 = plot_data[
        (plot_data["lq_month3_emplvl"] <= 1) & (plot_data["lq_avg_wkly_wage"] > 1)
    ]  # Less concentrated but pays more

    # Narrative
    parts = [
        f"This chart compares each industry's local employment concentration (x-axis) "
        f"to its local wage premium (y-axis) relative to U.S. averages. "
        f"Industries in the upper-right quadrant are Palm Beach specializations "
        f"that also pay above the national average for that sector."
    ]

    if not q1.empty:
        names = q1.nlargest(3, "employment")["industry_label"].tolist()
        if len(names) > 2:
            listing = ", ".join(names[:-1]) + f", and {names[-1]}"
        elif len(names) == 2:
            listing = f"{names[0]} and {names[1]}"
        else:
            listing = names[0]
        parts.append(
            f" In {year} Q{qtr}, {listing} stood out as concentrated "
            f"specializations with above-average wages."
        )

    if not q2.empty:
        names = q2.nlargest(2, "employment")["industry_label"].tolist()
        listing = " and ".join(names)
        parts.append(
            f" {listing} {'are' if len(names) > 1 else 'is'} overrepresented "
            f"but {'pay' if len(names) > 1 else 'pays'} below the national average."
        )

    st.markdown("".join(parts))

    fig = px.scatter(
        plot_data,
        x="lq_month3_emplvl",
        y="lq_avg_wkly_wage",
        size="employment",
        text="industry_label",
        labels={
            "lq_month3_emplvl": "Employment LQ (vs. U.S.)",
            "lq_avg_wkly_wage": "Wage LQ (vs. U.S.)",
            "employment": "Employment",
        },
        custom_data=[
            "industry_label", "lq_month3_emplvl", "lq_avg_wkly_wage",
            "employment", "avg_annual_wage",
        ],
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
            "Employment LQ: %{customdata[1]:.2f}<br>"
            "Wage LQ: %{customdata[2]:.2f}<br>"
            "Employment: %{customdata[3]:,.0f}<br>"
            "Avg Annual Wage: $%{customdata[4]:,.0f}<br>"
            "<extra></extra>"
        ),
    )

    # Quadrant reference lines at 1.0
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=1)
    fig.add_vline(x=1.0, line_dash="dash", line_color="gray", line_width=1)

    # Quadrant labels
    x_max = plot_data["lq_month3_emplvl"].max()
    y_max = plot_data["lq_avg_wkly_wage"].max()
    x_min = plot_data["lq_month3_emplvl"].min()
    y_min = plot_data["lq_avg_wkly_wage"].min()

    annotations = [
        dict(
            x=max(1.0 + (x_max - 1.0) * 0.7, 1.3),
            y=max(1.0 + (y_max - 1.0) * 0.9, 1.3),
            text="Specialized &<br>Higher Paying",
            showarrow=False,
            font=dict(size=10, color="green"),
            opacity=0.6,
        ),
        dict(
            x=max(1.0 + (x_max - 1.0) * 0.7, 1.3),
            y=min(1.0 - (1.0 - y_min) * 0.7, 0.8),
            text="Specialized &<br>Lower Paying",
            showarrow=False,
            font=dict(size=10, color="orange"),
            opacity=0.6,
        ),
        dict(
            x=min(1.0 - (1.0 - x_min) * 0.7, 0.7),
            y=max(1.0 + (y_max - 1.0) * 0.9, 1.3),
            text="Underrepresented &<br>Higher Paying",
            showarrow=False,
            font=dict(size=10, color="steelblue"),
            opacity=0.6,
        ),
        dict(
            x=min(1.0 - (1.0 - x_min) * 0.7, 0.7),
            y=min(1.0 - (1.0 - y_min) * 0.7, 0.8),
            text="Underrepresented &<br>Lower Paying",
            showarrow=False,
            font=dict(size=10, color="gray"),
            opacity=0.6,
        ),
    ]

    fig.update_layout(
        annotations=annotations,
        height=600,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
