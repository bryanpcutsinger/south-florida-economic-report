"""
Industry Specialization — top NAICS sectors by employment Location Quotient.
Bars colored by LQ band (≥1.25 / 1.0–1.25 / <1.0) to teach the threshold visually.
"""
from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd

from data.clean import get_specialties_data
from data.constants import (
    FAU_BLUE, FAU_STONE, FAU_GRAY, FAU_DARK_GRAY,
)
from utils.narratives import source_citation, format_industry_list


METHODOLOGY_NOTE = (
    "Location Quotient compares the county's share of jobs in each industry "
    "to the U.S. average — values above 1.0 mean the county is more "
    "concentrated than the country in that industry. Industries below 1,000 "
    "jobs are excluded to avoid noise. LQ describes workforce concentration; "
    "it does not measure exports or growth contribution."
)


def _bar_color(lq: float) -> str:
    if lq >= 1.25:
        return FAU_BLUE
    if lq >= 1.0:
        return FAU_STONE
    return FAU_GRAY


def build_figure(plot_data: pd.DataFrame) -> go.Figure:
    # Sort ascending so highest LQ renders at the top of the horizontal chart.
    df = plot_data.sort_values("lq_month3_emplvl", ascending=True)

    colors = [_bar_color(lq) for lq in df["lq_month3_emplvl"]]
    customdata = df[["industry_label", "lq_month3_emplvl", "employment"]].values

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["lq_month3_emplvl"],
        y=df["industry_label"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        customdata=customdata,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "LQ: %{customdata[1]:.2f} (%{customdata[1]:.1f}× U.S.)<br>"
            "Employment: %{customdata[2]:,.0f}"
            "<extra></extra>"
        ),
    ))

    x_max = max(df["lq_month3_emplvl"].max() * 1.10, 1.4)
    fig.add_vline(
        x=1.0, line_dash="dash", line_color=FAU_DARK_GRAY, line_width=1,
        annotation_text="U.S. average",
        annotation_position="top",
        annotation_font=dict(size=9, color=FAU_DARK_GRAY),
    )
    fig.add_vline(
        x=1.25, line_dash="dash", line_color=FAU_DARK_GRAY, line_width=1,
        annotation_text="Strong specialty",
        annotation_position="top",
        annotation_font=dict(size=9, color=FAU_DARK_GRAY),
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(420, 30 * len(df) + 80),
        margin=dict(t=50, b=70, l=10, r=20),
        showlegend=False,
        xaxis=dict(
            title="Concentration vs. U.S. average (1.0 = same as U.S.)",
            range=[0, x_max],
            showgrid=False,
            showline=True, linecolor="black", linewidth=2, mirror=False,
            ticks="outside", tickcolor="black", ticklen=4,
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            showline=True, linecolor="black", linewidth=2, mirror=False,
            automargin=True,
        ),
    )
    return fig


def render(df: pd.DataFrame):
    """Industry Specialization — top sectors by employment LQ with FAU bands."""
    import streamlit as st

    st.header("Industry Specialization")

    plot_data = get_specialties_data(df)
    if plot_data.empty:
        st.info("No disclosable specialization data for this quarter.")
        return

    year = int(plot_data["year"].iloc[0])
    qtr = int(plot_data["qtr"].iloc[0])

    strong = plot_data[plot_data["lq_month3_emplvl"] >= 1.25].nlargest(3, "lq_month3_emplvl")
    if len(strong) == 0:
        narrative = (
            f"In {year} Q{qtr}, no 2-digit NAICS sector exceeded 1.25× the U.S. "
            "concentration after applying the 1,000-job employment floor."
        )
    else:
        names = strong["industry_label"].tolist()
        narrative = (
            f"In {year} Q{qtr}, the county's strongest specialties — industries with "
            f"workforce concentrations of 1.25× the U.S. average or greater — are "
            f"{format_industry_list(names)}."
        )

    st.markdown(narrative)
    fig = build_figure(plot_data)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
    st.caption(f"_{METHODOLOGY_NOTE}_")
