"""
Employment and wage trend lines — quarterly totals over time.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st
import pandas as pd

from data.clean import get_total_covered
from data.constants import COUNTY_COLORS
from utils.formatting import fmt_number, fmt_currency
from utils.narratives import narrate_employment_trends, source_citation


def render(df: pd.DataFrame):
    """Render quarterly employment and wage trend lines for Palm Beach County."""
    st.header("Employment & Wage Trends")

    totals = get_total_covered(df)

    if totals.empty:
        st.info("No trend data available.")
        return

    totals = totals.sort_values("date")

    # Narrative: earliest vs latest employment + wage change
    earliest = totals.iloc[0]
    latest = totals.iloc[-1]

    empl_text = narrate_employment_trends(
        county_name="Palm Beach",
        start_year=int(earliest["year"]),
        end_year=int(latest["year"]),
        start_empl=earliest["employment"],
        end_empl=latest["employment"],
    )

    # Add wage context
    start_wage = earliest["avg_annual_wage"]
    end_wage = latest["avg_annual_wage"]
    if pd.notna(start_wage) and pd.notna(end_wage) and start_wage > 0:
        wage_change = (end_wage - start_wage) / start_wage * 100
        direction = "rising" if wage_change >= 0 else "falling"
        wage_text = (
            f" Average annual wages went from {fmt_currency(start_wage)} to "
            f"{fmt_currency(end_wage)}, {direction} {abs(wage_change):.1f}% "
            f"over the same period."
        )
    else:
        wage_text = ""

    st.markdown(empl_text + wage_text)

    color = COUNTY_COLORS.get("Palm Beach", "#2ca02c")

    # Two charts side by side
    col1, col2 = st.columns(2)

    with col1:
        fig_empl = px.line(
            totals,
            x="date",
            y="employment",
            markers=True,
            labels={"date": "", "employment": "Employment"},
            title="Total Employment",
        )
        fig_empl.update_traces(line_color=color, marker=dict(size=4))
        fig_empl.update_layout(
            hovermode="x unified",
            yaxis_tickformat=",.0f",
            height=400,
            title_font_size=14,
        )
        st.plotly_chart(fig_empl, use_container_width=True)

    with col2:
        fig_wage = px.line(
            totals,
            x="date",
            y="avg_annual_wage",
            markers=True,
            labels={"date": "", "avg_annual_wage": "Avg Annual Wage"},
            title="Average Annual Wage",
        )
        fig_wage.update_traces(line_color=color, marker=dict(size=4))
        fig_wage.update_layout(
            hovermode="x unified",
            yaxis_tickformat="$,.0f",
            height=400,
            title_font_size=14,
        )
        st.plotly_chart(fig_wage, use_container_width=True)

    st.caption(source_citation("BLS QCEW", "https://www.bls.gov/cew/", "Quarterly"))
