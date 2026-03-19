"""
Industry growth — diverging horizontal bars showing YoY employment and wage change by sector.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.clean import get_naics_sectors, get_latest_quarter
from utils.formatting import fmt_number, fmt_pct
from utils.narratives import source_citation

# Minimum employment to avoid misleading growth rates from tiny industries
MIN_EMPLOYMENT = 100


def render(df: pd.DataFrame):
    """Render diverging bar charts of YoY employment and wage growth by sector."""
    st.header("Industry Growth")

    sectors = get_naics_sectors(df, own_code=5)
    latest = get_latest_quarter(sectors)

    if latest.empty:
        st.info("No industry growth data available.")
        return

    plot_data = latest[
        (~latest["is_suppressed"])
        & (latest["employment"] >= MIN_EMPLOYMENT)
        & (latest["oty_month3_emplvl_pct_chg"].notna())
        & (latest["industry_label"] != "Unclassified")
    ].copy()

    if plot_data.empty:
        st.info("No disclosable growth data for this quarter.")
        return

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Narrative: top growers and biggest decliners (employment)
    sorted_empl = plot_data.sort_values("oty_month3_emplvl_pct_chg", ascending=True)
    growers = sorted_empl[sorted_empl["oty_month3_emplvl_pct_chg"] > 0].nlargest(
        3, "oty_month3_emplvl_pct_chg"
    )
    decliners = sorted_empl[sorted_empl["oty_month3_emplvl_pct_chg"] < 0].nsmallest(
        3, "oty_month3_emplvl_pct_chg"
    )

    parts = [f"In {year} Q{qtr}"]
    if not growers.empty:
        top = growers.iloc[0]
        parts.append(
            f", the fastest-growing industry was {top['industry_label']} "
            f"(+{top['oty_month3_emplvl_pct_chg']:.1f}% YoY)"
        )
    if not decliners.empty:
        bottom = decliners.iloc[0]
        parts.append(
            f", while {bottom['industry_label']} saw the largest decline "
            f"({bottom['oty_month3_emplvl_pct_chg']:.1f}%)"
        )
    parts.append(".")

    n_growing = (plot_data["oty_month3_emplvl_pct_chg"] > 0).sum()
    n_shrinking = (plot_data["oty_month3_emplvl_pct_chg"] < 0).sum()
    parts.append(
        f" Overall, {n_growing} of {len(plot_data)} industries expanded "
        f"while {n_shrinking} contracted."
    )

    # Add wage growth context
    wage_data = plot_data[plot_data["oty_avg_wkly_wage_pct_chg"].notna()]
    if not wage_data.empty:
        top_wage = wage_data.nlargest(1, "oty_avg_wkly_wage_pct_chg").iloc[0]
        bottom_wage = wage_data.nsmallest(1, "oty_avg_wkly_wage_pct_chg").iloc[0]
        parts.append(
            f" The largest wage increase was in {top_wage['industry_label']} "
            f"(+{top_wage['oty_avg_wkly_wage_pct_chg']:.1f}%), "
            f"while {bottom_wage['industry_label']} saw wages "
            f"{'fall' if bottom_wage['oty_avg_wkly_wage_pct_chg'] < 0 else 'grow the least'} "
            f"({bottom_wage['oty_avg_wkly_wage_pct_chg']:+.1f}%)."
        )

    st.markdown("".join(parts))

    # Two charts side by side
    col1, col2 = st.columns(2)
    chart_height = max(450, len(plot_data) * 28)

    # Employment growth bars
    empl_sorted = plot_data.sort_values("oty_month3_emplvl_pct_chg", ascending=True)
    with col1:
        fig_empl = px.bar(
            empl_sorted,
            x="oty_month3_emplvl_pct_chg",
            y="industry_label",
            orientation="h",
            color="oty_month3_emplvl_pct_chg",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            title="Employment Growth (YoY %)",
            labels={
                "oty_month3_emplvl_pct_chg": "YoY %",
                "industry_label": "",
            },
            custom_data=["industry_label", "oty_month3_emplvl_pct_chg", "employment"],
        )

        fig_empl.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "YoY Growth: %{customdata[1]:+.1f}%<br>"
                "Employment: %{customdata[2]:,.0f}<br>"
                "<extra></extra>"
            ),
        )
        fig_empl.add_vline(x=0, line_color="black", line_width=1)
        fig_empl.update_layout(
            xaxis_tickformat="+.1f",
            xaxis_ticksuffix="%",
            height=chart_height,
            showlegend=False,
            coloraxis_showscale=False,
            title_font_size=14,
        )
        st.plotly_chart(fig_empl, use_container_width=True)

    # Wage growth bars
    wage_plot = plot_data[plot_data["oty_avg_wkly_wage_pct_chg"].notna()].copy()
    wage_sorted = wage_plot.sort_values("oty_avg_wkly_wage_pct_chg", ascending=True)
    with col2:
        fig_wage = px.bar(
            wage_sorted,
            x="oty_avg_wkly_wage_pct_chg",
            y="industry_label",
            orientation="h",
            color="oty_avg_wkly_wage_pct_chg",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            title="Wage Growth (YoY %)",
            labels={
                "oty_avg_wkly_wage_pct_chg": "YoY %",
                "industry_label": "",
            },
            custom_data=["industry_label", "oty_avg_wkly_wage_pct_chg", "avg_annual_wage"],
        )

        fig_wage.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "YoY Wage Growth: %{customdata[1]:+.1f}%<br>"
                "Avg Annual Wage: $%{customdata[2]:,.0f}<br>"
                "<extra></extra>"
            ),
        )
        fig_wage.add_vline(x=0, line_color="black", line_width=1)
        fig_wage.update_layout(
            xaxis_tickformat="+.1f",
            xaxis_ticksuffix="%",
            height=chart_height,
            showlegend=False,
            coloraxis_showscale=False,
            title_font_size=14,
        )
        st.plotly_chart(fig_wage, use_container_width=True)

    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
