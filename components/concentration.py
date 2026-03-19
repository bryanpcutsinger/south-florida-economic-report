"""
Economic concentration — HHI over time with reference bands.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.analysis import compute_hhi
from data.constants import COUNTY_COLORS
from utils.narratives import source_citation


def render(df: pd.DataFrame):
    """Render HHI concentration line chart with reference bands."""
    st.header("Economic Concentration")

    hhi_df = compute_hhi(df, own_code=5)

    if hhi_df.empty:
        st.info("Not enough data to compute concentration index.")
        return

    hhi_df = hhi_df.sort_values("date")

    # Narrative
    latest = hhi_df.iloc[-1]
    earliest = hhi_df.iloc[0]
    latest_hhi = latest["hhi"]

    if latest_hhi < 0.10:
        level = "diversified"
    elif latest_hhi < 0.25:
        level = "moderately concentrated"
    else:
        level = "highly concentrated"

    trend = "stable"
    if len(hhi_df) >= 4:
        recent = hhi_df.tail(4)["hhi"]
        delta = recent.iloc[-1] - recent.iloc[0]
        if delta > 0.005:
            trend = "increasing (becoming more concentrated)"
        elif delta < -0.005:
            trend = "decreasing (becoming more diversified)"

    st.markdown(
        f"The Herfindahl-Hirschman Index (HHI) measures how concentrated "
        f"employment is across industries. Palm Beach County's private sector "
        f"HHI is {latest_hhi:.3f}, indicating a **{level}** economy. "
        f"The trend has been {trend} over the past year."
    )

    fig = px.line(
        hhi_df,
        x="date",
        y="hhi",
        markers=True,
        labels={"date": "", "hhi": "HHI"},
    )

    fig.update_traces(
        line_color=COUNTY_COLORS.get("Palm Beach", "#2ca02c"),
        marker=dict(size=5),
    )

    # Reference bands
    fig.add_hrect(
        y0=0, y1=0.10,
        fillcolor="green", opacity=0.08,
        line_width=0,
        annotation_text="Diversified", annotation_position="top left",
    )
    fig.add_hrect(
        y0=0.10, y1=0.25,
        fillcolor="orange", opacity=0.08,
        line_width=0,
        annotation_text="Moderate", annotation_position="top left",
    )
    fig.add_hrect(
        y0=0.25, y1=max(0.35, hhi_df["hhi"].max() + 0.02),
        fillcolor="red", opacity=0.08,
        line_width=0,
        annotation_text="Concentrated", annotation_position="top left",
    )

    # Threshold lines
    fig.add_hline(y=0.10, line_dash="dot", line_color="gray", line_width=1)
    fig.add_hline(y=0.25, line_dash="dot", line_color="gray", line_width=1)

    fig.update_layout(
        hovermode="x unified",
        yaxis_tickformat=".3f",
        height=450,
    )

    st.plotly_chart(fig, use_container_width=True)
    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
