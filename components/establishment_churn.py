"""
Establishment churn — net change in establishments by sector.
Proxy for business formation and closure dynamics.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.clean import get_naics_sectors, get_latest_quarter
from utils.formatting import fmt_number
from utils.narratives import source_citation


def render(df: pd.DataFrame):
    """Render diverging bar chart of net establishment change by sector."""
    st.header("Establishment Dynamics")

    sectors = get_naics_sectors(df, own_code=5)
    latest = get_latest_quarter(sectors)

    if latest.empty:
        st.info("No establishment data available.")
        return

    plot_data = latest[
        (~latest["is_suppressed"])
        & (latest["qtrly_estabs"] > 0)
        & (latest["oty_qtrly_estabs_chg"].notna())
        & (latest["industry_label"] != "Unclassified")
    ].copy()

    if plot_data.empty:
        st.info("No disclosable establishment data for this quarter.")
        return

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Narrative
    total_net = plot_data["oty_qtrly_estabs_chg"].sum()
    gainers = plot_data[plot_data["oty_qtrly_estabs_chg"] > 0]
    losers = plot_data[plot_data["oty_qtrly_estabs_chg"] < 0]

    direction = "a net gain" if total_net >= 0 else "a net loss"
    parts = [
        f"In {year} Q{qtr}, Palm Beach County's private sector saw {direction} "
        f"of {fmt_number(abs(total_net))} establishments year-over-year. "
        f"{len(gainers)} industries added firms while {len(losers)} lost them."
    ]

    if not gainers.empty:
        top = gainers.nlargest(1, "oty_qtrly_estabs_chg").iloc[0]
        parts.append(
            f" {top['industry_label']} led with +{fmt_number(top['oty_qtrly_estabs_chg'])} "
            f"new establishments."
        )
    if not losers.empty:
        bottom = losers.nsmallest(1, "oty_qtrly_estabs_chg").iloc[0]
        parts.append(
            f" {bottom['industry_label']} saw the largest decline "
            f"({fmt_number(int(bottom['oty_qtrly_estabs_chg']))})."
        )

    st.markdown("".join(parts))

    # Two side-by-side charts: absolute change and % change
    col1, col2 = st.columns(2)
    chart_height = max(450, len(plot_data) * 28)

    # Absolute change
    abs_sorted = plot_data.sort_values("oty_qtrly_estabs_chg", ascending=True)
    with col1:
        fig_abs = px.bar(
            abs_sorted,
            x="oty_qtrly_estabs_chg",
            y="industry_label",
            orientation="h",
            color="oty_qtrly_estabs_chg",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            title="Net Change in Establishments (YoY)",
            labels={
                "oty_qtrly_estabs_chg": "Net Change",
                "industry_label": "",
            },
            custom_data=["industry_label", "oty_qtrly_estabs_chg", "qtrly_estabs"],
        )
        fig_abs.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Net Change: %{customdata[1]:+,.0f}<br>"
                "Total Establishments: %{customdata[2]:,.0f}<br>"
                "<extra></extra>"
            ),
        )
        fig_abs.add_vline(x=0, line_color="black", line_width=1)
        fig_abs.update_layout(
            xaxis_tickformat="+,.0f",
            height=chart_height,
            showlegend=False,
            coloraxis_showscale=False,
            title_font_size=14,
        )
        st.plotly_chart(fig_abs, use_container_width=True)

    # Percent change
    pct_data = plot_data[plot_data["oty_qtrly_estabs_pct_chg"].notna()].copy()
    pct_sorted = pct_data.sort_values("oty_qtrly_estabs_pct_chg", ascending=True)
    with col2:
        fig_pct = px.bar(
            pct_sorted,
            x="oty_qtrly_estabs_pct_chg",
            y="industry_label",
            orientation="h",
            color="oty_qtrly_estabs_pct_chg",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            title="Establishment Growth Rate (YoY %)",
            labels={
                "oty_qtrly_estabs_pct_chg": "YoY %",
                "industry_label": "",
            },
            custom_data=["industry_label", "oty_qtrly_estabs_pct_chg", "qtrly_estabs"],
        )
        fig_pct.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Growth Rate: %{customdata[1]:+.1f}%<br>"
                "Total Establishments: %{customdata[2]:,.0f}<br>"
                "<extra></extra>"
            ),
        )
        fig_pct.add_vline(x=0, line_color="black", line_width=1)
        fig_pct.update_layout(
            xaxis_tickformat="+.1f",
            xaxis_ticksuffix="%",
            height=chart_height,
            showlegend=False,
            coloraxis_showscale=False,
            title_font_size=14,
        )
        st.plotly_chart(fig_pct, use_container_width=True)

    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
