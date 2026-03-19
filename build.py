#!/usr/bin/env python3
"""
Build static HTML dashboard from QCEW data for GitHub Pages.

Reuses the existing data pipeline (data/fetch.py, data/clean.py) and
recreates all Plotly charts from the Streamlit app as a self-contained
docs/index.html with embedded JSON figure data rendered by Plotly.js.

Usage:
    python build.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data.fetch import fetch_all_data
from data.clean import clean, get_total_covered, get_naics_sectors, get_latest_quarter
from data.analysis import compute_hhi
from data.constants import (
    FAU_BLUE, FAU_RED, FAU_DARK_GRAY, FAU_GRAY,
    FAU_ELECTRIC_BLUE, FAU_SKY_BLUE, COUNTY_COLORS,
)
from utils.formatting import fmt_number, fmt_currency, fmt_pct
from utils.narratives import narrate_employment_trends, narrate_wage_distribution

DOCS_DIR = Path(__file__).parent / "docs"
MIN_EMPLOYMENT = 100
COUNTY_ORDER = ["Palm Beach", "Broward", "Miami-Dade"]

# ── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background-color: #FFFFFF;
    color: """ + FAU_DARK_GRAY + """;
    line-height: 1.6;
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem 2rem;
}

h1, h2, h3, h4 { color: """ + FAU_BLUE + """; }

/* Header */
.main-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; }
.main-subtitle { font-size: 1.0rem; margin-top: 0.25rem; color: """ + FAU_DARK_GRAY + """; }

.data-badge {
    display: inline-block;
    background-color: """ + FAU_SKY_BLUE + """;
    color: """ + FAU_BLUE + """;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    margin: 1rem 0;
}

/* KPI cards */
.snapshot-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.county-card {
    flex: 1;
    background: linear-gradient(135deg, #F8F9FA 0%, #FFFFFF 100%);
    border-radius: 12px;
    padding: 1.5rem;
    border-left: 5px solid;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.county-card h3 { margin: 0 0 0.8rem 0; font-size: 1.3rem; }
.kpi-row { display: flex; justify-content: space-between; gap: 0.8rem; }
.kpi-item { flex: 1; text-align: center; }
.kpi-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.2rem;
    color: """ + FAU_DARK_GRAY + """;
}
.kpi-value { font-size: 1.4rem; font-weight: 700; color: """ + FAU_BLUE + """; }
.kpi-delta { font-size: 0.8rem; margin-top: 0.1rem; }
.kpi-delta.positive { color: #2E7D32; }
.kpi-delta.negative { color: """ + FAU_RED + """; }

/* Tabs */
.tab-bar { display: flex; border-bottom: 2px solid """ + FAU_GRAY + """; margin: 1.5rem 0 0 0; }
.tab-btn {
    padding: 0.75rem 1.5rem;
    font-weight: 500;
    color: """ + FAU_DARK_GRAY + """;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1rem;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    font-family: inherit;
}
.tab-btn:hover { color: """ + FAU_BLUE + """; }
.tab-btn.active { border-bottom-color: """ + FAU_BLUE + """; color: """ + FAU_BLUE + """; }

.tab-content { display: none; padding-top: 1rem; }
.tab-content.active { display: block; }

/* Chart sections */
.section { margin: 2rem 0; }
.section h2 { font-size: 1.5rem; margin-bottom: 0.5rem; }
.section p { margin-bottom: 0.75rem; }

.chart-row { display: flex; gap: 1rem; }
.chart-col { flex: 1; min-width: 0; }

.divider { border-top: 1px solid #EEEEEE; margin: 2rem 0; }

.source {
    font-size: 0.8rem;
    color: #888;
    margin-top: 0.25rem;
}
.source a { color: """ + FAU_ELECTRIC_BLUE + """; text-decoration: none; }
.source a:hover { text-decoration: underline; }

.footer {
    font-size: 0.8rem;
    color: #888;
    text-align: center;
    margin-top: 2rem;
    padding: 1rem 0;
    border-top: 1px solid #EEE;
}
.footer a { color: """ + FAU_ELECTRIC_BLUE + """; }

@media (max-width: 768px) {
    .snapshot-row, .chart-row { flex-direction: column; }
    body { padding: 0.5rem 1rem; }
    .tab-btn { padding: 0.5rem 1rem; font-size: 0.9rem; }
}
"""

# ── JavaScript ───────────────────────────────────────────────────────────────

JS = """
function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
    document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
    document.getElementById(tabId).classList.add('active');
    document.querySelector('[data-tab="' + tabId + '"]').classList.add('active');
    setTimeout(function() {
        document.querySelectorAll('#' + tabId + ' .plotly-chart').forEach(function(el) {
            if (el.data) Plotly.Plots.resize(el);
        });
    }, 50);
}

Object.keys(figureData).forEach(function(divId) {
    var fig = figureData[divId];
    Plotly.newPlot(divId, fig.data, fig.layout, {responsive: true});
});
"""

# ── Helpers ──────────────────────────────────────────────────────────────────

SOURCE = '<p class="source">Source: <a href="https://www.bls.gov/cew/">BLS QCEW</a> — Quarterly</p>'


def _fig_json(fig):
    """Convert a Plotly figure to a JSON-serializable dict."""
    return json.loads(fig.to_json())


def _delta_html(pct):
    """Render a YoY percent-change badge."""
    if pd.isna(pct):
        return ""
    css = "positive" if pct >= 0 else "negative"
    arrow = "&#9650;" if pct >= 0 else "&#9660;"
    return f'<div class="kpi-delta {css}">{arrow} {abs(pct):.1f}% YoY</div>'


# ── KPI Card ─────────────────────────────────────────────────────────────────

def build_kpi_card(county_df, county_name, color):
    """Generate HTML for one county KPI card."""
    totals = get_total_covered(county_df)
    latest = get_latest_quarter(totals)

    if latest.empty:
        return (
            f'<div class="county-card" style="border-left-color: {color};">'
            f'<h3 style="color: {color};">{county_name} County</h3>'
            f'<p>No data available.</p></div>'
        )

    row = latest.iloc[0]
    return (
        f'<div class="county-card" style="border-left-color: {color};">'
        f'<h3 style="color: {color};">{county_name} County</h3>'
        f'<div class="kpi-row">'
        f'<div class="kpi-item"><div class="kpi-label">Employment</div>'
        f'<div class="kpi-value">{fmt_number(row["employment"])}</div>'
        f'{_delta_html(row.get("oty_month3_emplvl_pct_chg"))}</div>'
        f'<div class="kpi-item"><div class="kpi-label">Establishments</div>'
        f'<div class="kpi-value">{fmt_number(row["qtrly_estabs"])}</div>'
        f'{_delta_html(row.get("oty_qtrly_estabs_pct_chg"))}</div>'
        f'<div class="kpi-item"><div class="kpi-label">Avg Annual Salary</div>'
        f'<div class="kpi-value">{fmt_currency(row["avg_annual_wage"])}</div>'
        f'{_delta_html(row.get("oty_avg_wkly_wage_pct_chg"))}</div>'
        f'</div></div>'
    )


# ── Section Builders ─────────────────────────────────────────────────────────
# Each function builds Plotly figures, adds them to `figures` dict,
# and returns the HTML for that dashboard section.

def build_trends(county_df, county_name, county_id, figures):
    """Employment & Wage Trends — two side-by-side line charts."""
    totals = get_total_covered(county_df)
    if totals.empty:
        return '<div class="section"><h2>Employment &amp; Wage Trends</h2><p>No trend data available.</p></div>'

    totals = totals.sort_values("date")
    earliest, latest = totals.iloc[0], totals.iloc[-1]
    color = COUNTY_COLORS.get(county_name, FAU_BLUE)

    narrative = narrate_employment_trends(
        county_name=county_name,
        start_year=int(earliest["year"]), end_year=int(latest["year"]),
        start_empl=earliest["employment"], end_empl=latest["employment"],
    )
    sw, ew = earliest["avg_annual_wage"], latest["avg_annual_wage"]
    if pd.notna(sw) and pd.notna(ew) and sw > 0:
        wc = (ew - sw) / sw * 100
        narrative += (
            f" Average annual wages went from {fmt_currency(sw)} to "
            f"{fmt_currency(ew)}, {'rising' if wc >= 0 else 'falling'} "
            f"{abs(wc):.1f}% over the same period."
        )

    fig_e = px.line(totals, x="date", y="employment", markers=True,
                    labels={"date": "", "employment": "Employment"}, title="Total Employment")
    fig_e.update_traces(line_color=color, marker=dict(size=4))
    fig_e.update_layout(hovermode="x unified", yaxis_tickformat=",.0f", height=400, title_font_size=14)

    fig_w = px.line(totals, x="date", y="avg_annual_wage", markers=True,
                    labels={"date": "", "avg_annual_wage": "Avg Annual Wage"}, title="Average Annual Wage")
    fig_w.update_traces(line_color=color, marker=dict(size=4))
    fig_w.update_layout(hovermode="x unified", yaxis_tickformat="$,.0f", height=400, title_font_size=14)

    eid, wid = f"{county_id}-trends-empl", f"{county_id}-trends-wage"
    figures[eid], figures[wid] = _fig_json(fig_e), _fig_json(fig_w)

    return (
        f'<div class="section"><h2>Employment &amp; Wage Trends</h2>'
        f'<p>{narrative}</p>'
        f'<div class="chart-row">'
        f'<div class="chart-col"><div id="{eid}" class="plotly-chart"></div></div>'
        f'<div class="chart-col"><div id="{wid}" class="plotly-chart"></div></div>'
        f'</div>{SOURCE}</div>'
    )


def build_treemap(county_df, county_name, county_id, figures):
    """Industry Composition — treemap sized by employment, colored by wage."""
    sectors = get_naics_sectors(county_df, own_code=5)
    latest = get_latest_quarter(sectors)
    if latest.empty:
        return '<div class="section"><h2>Industry Composition</h2><p>No industry data available.</p></div>'

    plot_data = latest[(~latest["is_suppressed"]) & (latest["employment"] > 0)].copy()
    if plot_data.empty:
        return '<div class="section"><h2>Industry Composition</h2><p>No disclosable industry data.</p></div>'

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])
    total_empl = plot_data["employment"].sum()
    top3 = plot_data.nlargest(3, "employment")
    shares = [f"{r['industry_label']} ({fmt_pct(r['employment'] / total_empl * 100)})" for _, r in top3.iterrows()]
    listing = ", ".join(shares[:-1]) + f", and {shares[-1]}"

    narrative = (
        f"In {year} Q{qtr}, {county_name} County's private sector employed "
        f"{fmt_number(total_empl)} workers across {len(plot_data)} industries. "
        f"The largest by employment share were {listing}."
    )

    fig = px.treemap(plot_data, path=["industry_label"], values="employment",
                     color="avg_annual_wage", color_continuous_scale="Plasma",
                     labels={"avg_annual_wage": "Avg Annual Wage"},
                     custom_data=["industry_label", "employment", "avg_annual_wage"])
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Employment: %{customdata[1]:,.0f}<br>"
                      "Avg Annual Wage: $%{customdata[2]:,.0f}<extra></extra>",
        textinfo="label+value", texttemplate="<b>%{label}</b><br>%{value:,.0f}",
    )
    fig.update_layout(height=600, coloraxis_colorbar=dict(title="Avg Annual<br>Wage ($)", tickformat="$,.0f"))

    div_id = f"{county_id}-treemap"
    figures[div_id] = _fig_json(fig)

    return (
        f'<div class="section"><h2>Industry Composition</h2>'
        f'<p>{narrative}</p>'
        f'<div id="{div_id}" class="plotly-chart"></div>{SOURCE}</div>'
    )


def build_wage_landscape(county_df, county_name, county_id, figures):
    """Wage Landscape — horizontal bars ranked by average annual wage."""
    sectors = get_naics_sectors(county_df, own_code=5)
    latest = get_latest_quarter(sectors)
    if latest.empty:
        return '<div class="section"><h2>Wage Landscape</h2><p>No wage data available.</p></div>'

    plot_data = latest[
        (~latest["is_suppressed"]) & latest["avg_annual_wage"].notna() & (latest["employment"] > 0)
    ].copy().sort_values("avg_annual_wage", ascending=True)
    if plot_data.empty:
        return '<div class="section"><h2>Wage Landscape</h2><p>No disclosable wage data.</p></div>'

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])
    weighted_avg = (plot_data["avg_annual_wage"] * plot_data["employment"]).sum() / plot_data["employment"].sum()

    narrative = narrate_wage_distribution(
        county_name=county_name, year=year, qtr=qtr,
        highest_industry=plot_data.iloc[-1]["industry_label"],
        highest_wage=plot_data.iloc[-1]["avg_annual_wage"],
        lowest_industry=plot_data.iloc[0]["industry_label"],
        lowest_wage=plot_data.iloc[0]["avg_annual_wage"],
        overall_avg=weighted_avg,
    )

    fig = px.bar(plot_data, x="avg_annual_wage", y="industry_label", orientation="h",
                 color="avg_annual_wage", color_continuous_scale="Plasma",
                 labels={"avg_annual_wage": "Avg Annual Wage", "industry_label": ""},
                 custom_data=["industry_label", "avg_annual_wage", "employment"])
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Avg Annual Wage: $%{customdata[1]:,.0f}<br>"
                      "Employment: %{customdata[2]:,.0f}<extra></extra>",
    )
    fig.add_vline(x=weighted_avg, line_dash="dash", line_color="gray",
                  annotation_text=f"Avg: {fmt_currency(weighted_avg)}", annotation_position="top")
    fig.update_layout(xaxis_tickformat="$,.0f", height=max(450, len(plot_data) * 28),
                      showlegend=False, coloraxis_showscale=False)

    div_id = f"{county_id}-wages"
    figures[div_id] = _fig_json(fig)

    return (
        f'<div class="section"><h2>Wage Landscape</h2>'
        f'<p>{narrative}</p>'
        f'<div id="{div_id}" class="plotly-chart"></div>{SOURCE}</div>'
    )


def build_growth(county_df, county_name, county_id, figures):
    """Industry Growth — side-by-side diverging bars for employment and wage YoY %."""
    sectors = get_naics_sectors(county_df, own_code=5)
    latest = get_latest_quarter(sectors)
    if latest.empty:
        return '<div class="section"><h2>Industry Growth</h2><p>No growth data available.</p></div>'

    plot_data = latest[
        (~latest["is_suppressed"]) & (latest["employment"] >= MIN_EMPLOYMENT)
        & latest["oty_month3_emplvl_pct_chg"].notna() & (latest["industry_label"] != "Unclassified")
    ].copy()
    if plot_data.empty:
        return '<div class="section"><h2>Industry Growth</h2><p>No disclosable growth data.</p></div>'

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    # Narrative
    sorted_e = plot_data.sort_values("oty_month3_emplvl_pct_chg", ascending=True)
    growers = sorted_e[sorted_e["oty_month3_emplvl_pct_chg"] > 0].nlargest(3, "oty_month3_emplvl_pct_chg")
    decliners = sorted_e[sorted_e["oty_month3_emplvl_pct_chg"] < 0].nsmallest(3, "oty_month3_emplvl_pct_chg")

    parts = [f"In {year} Q{qtr}"]
    if not growers.empty:
        t = growers.iloc[0]
        parts.append(f", the fastest-growing industry was {t['industry_label']} (+{t['oty_month3_emplvl_pct_chg']:.1f}% YoY)")
    if not decliners.empty:
        b = decliners.iloc[0]
        parts.append(f", while {b['industry_label']} saw the largest decline ({b['oty_month3_emplvl_pct_chg']:.1f}%)")
    parts.append(".")

    ng = (plot_data["oty_month3_emplvl_pct_chg"] > 0).sum()
    ns = (plot_data["oty_month3_emplvl_pct_chg"] < 0).sum()
    parts.append(f" Overall, {ng} of {len(plot_data)} industries expanded while {ns} contracted.")

    wd = plot_data[plot_data["oty_avg_wkly_wage_pct_chg"].notna()]
    if not wd.empty:
        tw = wd.nlargest(1, "oty_avg_wkly_wage_pct_chg").iloc[0]
        bw = wd.nsmallest(1, "oty_avg_wkly_wage_pct_chg").iloc[0]
        verb = "fall" if bw["oty_avg_wkly_wage_pct_chg"] < 0 else "grow the least"
        parts.append(
            f" The largest wage increase was in {tw['industry_label']} "
            f"(+{tw['oty_avg_wkly_wage_pct_chg']:.1f}%), "
            f"while {bw['industry_label']} saw wages {verb} "
            f"({bw['oty_avg_wkly_wage_pct_chg']:+.1f}%)."
        )

    narrative = "".join(parts)
    chart_h = max(450, len(plot_data) * 28)

    # Employment growth figure
    es = plot_data.sort_values("oty_month3_emplvl_pct_chg", ascending=True)
    fig_e = px.bar(es, x="oty_month3_emplvl_pct_chg", y="industry_label", orientation="h",
                   color="oty_month3_emplvl_pct_chg", color_continuous_scale="RdYlGn",
                   color_continuous_midpoint=0, title="Employment Growth (YoY %)",
                   labels={"oty_month3_emplvl_pct_chg": "YoY %", "industry_label": ""},
                   custom_data=["industry_label", "oty_month3_emplvl_pct_chg", "employment"])
    fig_e.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>YoY Growth: %{customdata[1]:+.1f}%<br>"
                      "Employment: %{customdata[2]:,.0f}<extra></extra>")
    fig_e.add_vline(x=0, line_color="black", line_width=1)
    fig_e.update_layout(xaxis_tickformat="+.1f", xaxis_ticksuffix="%", height=chart_h,
                        showlegend=False, coloraxis_showscale=False, title_font_size=14)

    # Wage growth figure
    wp = plot_data[plot_data["oty_avg_wkly_wage_pct_chg"].notna()].copy()
    ws = wp.sort_values("oty_avg_wkly_wage_pct_chg", ascending=True)
    fig_w = px.bar(ws, x="oty_avg_wkly_wage_pct_chg", y="industry_label", orientation="h",
                   color="oty_avg_wkly_wage_pct_chg", color_continuous_scale="RdYlGn",
                   color_continuous_midpoint=0, title="Wage Growth (YoY %)",
                   labels={"oty_avg_wkly_wage_pct_chg": "YoY %", "industry_label": ""},
                   custom_data=["industry_label", "oty_avg_wkly_wage_pct_chg", "avg_annual_wage"])
    fig_w.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>YoY Wage Growth: %{customdata[1]:+.1f}%<br>"
                      "Avg Annual Wage: $%{customdata[2]:,.0f}<extra></extra>")
    fig_w.add_vline(x=0, line_color="black", line_width=1)
    fig_w.update_layout(xaxis_tickformat="+.1f", xaxis_ticksuffix="%", height=chart_h,
                        showlegend=False, coloraxis_showscale=False, title_font_size=14)

    eid, wid = f"{county_id}-growth-empl", f"{county_id}-growth-wage"
    figures[eid], figures[wid] = _fig_json(fig_e), _fig_json(fig_w)

    return (
        f'<div class="section"><h2>Industry Growth</h2>'
        f'<p>{narrative}</p>'
        f'<div class="chart-row">'
        f'<div class="chart-col"><div id="{eid}" class="plotly-chart"></div></div>'
        f'<div class="chart-col"><div id="{wid}" class="plotly-chart"></div></div>'
        f'</div>{SOURCE}</div>'
    )


def build_scatter(county_df, county_name, county_id, figures):
    """Wage-Employment Landscape — scatter plot by sector."""
    sectors = get_naics_sectors(county_df, own_code=5)
    latest = get_latest_quarter(sectors)
    if latest.empty:
        return '<div class="section"><h2>Wage\u2013Employment Landscape</h2><p>No data available.</p></div>'

    plot_data = latest[
        (~latest["is_suppressed"]) & (latest["employment"] > 0)
        & latest["avg_annual_wage"].notna() & (latest["industry_label"] != "Unclassified")
    ].copy()
    if plot_data.empty:
        return '<div class="section"><h2>Wage\u2013Employment Landscape</h2><p>No disclosable data.</p></div>'

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])
    wavg = (plot_data["avg_annual_wage"] * plot_data["employment"]).sum() / plot_data["employment"].sum()
    med_e = plot_data["employment"].median()

    anchor = plot_data[(plot_data["employment"] > med_e) & (plot_data["avg_annual_wage"] > wavg)]
    volume = plot_data[(plot_data["employment"] > med_e) & (plot_data["avg_annual_wage"] <= wavg)]

    parts = [f"In {year} Q{qtr}, each dot represents a 2-digit NAICS sector. Dot size reflects the number of establishments."]
    if not anchor.empty:
        names = anchor.nlargest(3, "employment")["industry_label"].tolist()
        listing = ", ".join(names[:-1]) + f", and {names[-1]}" if len(names) > 1 else names[0]
        parts.append(f" The largest high-wage, high-employment sectors \u2014 the county's anchor industries \u2014 are {listing}.")
    if not volume.empty:
        names = volume.nlargest(2, "employment")["industry_label"].tolist()
        parts.append(f" {' and '.join(names)} employ large workforces at below-average wages.")

    fig = px.scatter(plot_data, x="employment", y="avg_annual_wage", size="qtrly_estabs",
                     text="industry_label",
                     labels={"employment": "Employment", "avg_annual_wage": "Avg Annual Wage",
                             "qtrly_estabs": "Establishments"},
                     custom_data=["industry_label", "employment", "avg_annual_wage", "qtrly_estabs"])
    fig.update_traces(
        textposition="top center", textfont_size=9,
        marker=dict(color=plot_data["avg_annual_wage"].tolist(), colorscale="Plasma",
                    line=dict(width=1, color="white"), sizemin=8),
        hovertemplate="<b>%{customdata[0]}</b><br>Employment: %{customdata[1]:,.0f}<br>"
                      "Avg Annual Wage: $%{customdata[2]:,.0f}<br>"
                      "Establishments: %{customdata[3]:,.0f}<extra></extra>",
    )
    fig.add_hline(y=wavg, line_dash="dash", line_color="gray", line_width=1,
                  annotation_text=f"Avg Wage: {fmt_currency(wavg)}", annotation_position="top left")
    fig.add_vline(x=med_e, line_dash="dash", line_color="gray", line_width=1,
                  annotation_text=f"Median Employment: {fmt_number(med_e)}", annotation_position="top right")
    fig.update_layout(xaxis_tickformat=",.0f", yaxis_tickformat="$,.0f", height=550, showlegend=False)

    div_id = f"{county_id}-scatter"
    figures[div_id] = _fig_json(fig)

    return (
        f'<div class="section"><h2>Wage\u2013Employment Landscape</h2>'
        f'<p>{"".join(parts)}</p>'
        f'<div id="{div_id}" class="plotly-chart"></div>{SOURCE}</div>'
    )


def build_churn(county_df, county_name, county_id, figures):
    """Establishment Dynamics — side-by-side diverging bars (absolute + %)."""
    sectors = get_naics_sectors(county_df, own_code=5)
    latest = get_latest_quarter(sectors)
    if latest.empty:
        return '<div class="section"><h2>Establishment Dynamics</h2><p>No data available.</p></div>'

    plot_data = latest[
        (~latest["is_suppressed"]) & (latest["qtrly_estabs"] > 0)
        & latest["oty_qtrly_estabs_chg"].notna() & (latest["industry_label"] != "Unclassified")
    ].copy()
    if plot_data.empty:
        return '<div class="section"><h2>Establishment Dynamics</h2><p>No disclosable data.</p></div>'

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])
    total_net = plot_data["oty_qtrly_estabs_chg"].sum()
    gainers = plot_data[plot_data["oty_qtrly_estabs_chg"] > 0]
    losers = plot_data[plot_data["oty_qtrly_estabs_chg"] < 0]

    direction = "a net gain" if total_net >= 0 else "a net loss"
    parts = [
        f"In {year} Q{qtr}, {county_name} County's private sector saw {direction} "
        f"of {fmt_number(abs(total_net))} establishments year-over-year. "
        f"{len(gainers)} industries added firms while {len(losers)} lost them."
    ]
    if not gainers.empty:
        t = gainers.nlargest(1, "oty_qtrly_estabs_chg").iloc[0]
        parts.append(f" {t['industry_label']} led with +{fmt_number(t['oty_qtrly_estabs_chg'])} new establishments.")
    if not losers.empty:
        b = losers.nsmallest(1, "oty_qtrly_estabs_chg").iloc[0]
        parts.append(f" {b['industry_label']} saw the largest decline ({fmt_number(int(b['oty_qtrly_estabs_chg']))}).")

    chart_h = max(450, len(plot_data) * 28)

    # Absolute change
    abs_s = plot_data.sort_values("oty_qtrly_estabs_chg", ascending=True)
    fig_a = px.bar(abs_s, x="oty_qtrly_estabs_chg", y="industry_label", orientation="h",
                   color="oty_qtrly_estabs_chg", color_continuous_scale="RdYlGn",
                   color_continuous_midpoint=0, title="Net Change in Establishments (YoY)",
                   labels={"oty_qtrly_estabs_chg": "Net Change", "industry_label": ""},
                   custom_data=["industry_label", "oty_qtrly_estabs_chg", "qtrly_estabs"])
    fig_a.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Net Change: %{customdata[1]:+,.0f}<br>"
                      "Total Establishments: %{customdata[2]:,.0f}<extra></extra>")
    fig_a.add_vline(x=0, line_color="black", line_width=1)
    fig_a.update_layout(xaxis_tickformat="+,.0f", height=chart_h, showlegend=False,
                        coloraxis_showscale=False, title_font_size=14)

    # Percent change
    pct = plot_data[plot_data["oty_qtrly_estabs_pct_chg"].notna()].copy()
    pct_s = pct.sort_values("oty_qtrly_estabs_pct_chg", ascending=True)
    fig_p = px.bar(pct_s, x="oty_qtrly_estabs_pct_chg", y="industry_label", orientation="h",
                   color="oty_qtrly_estabs_pct_chg", color_continuous_scale="RdYlGn",
                   color_continuous_midpoint=0, title="Establishment Growth Rate (YoY %)",
                   labels={"oty_qtrly_estabs_pct_chg": "YoY %", "industry_label": ""},
                   custom_data=["industry_label", "oty_qtrly_estabs_pct_chg", "qtrly_estabs"])
    fig_p.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Growth Rate: %{customdata[1]:+.1f}%<br>"
                      "Total Establishments: %{customdata[2]:,.0f}<extra></extra>")
    fig_p.add_vline(x=0, line_color="black", line_width=1)
    fig_p.update_layout(xaxis_tickformat="+.1f", xaxis_ticksuffix="%", height=chart_h,
                        showlegend=False, coloraxis_showscale=False, title_font_size=14)

    aid, pid = f"{county_id}-churn-abs", f"{county_id}-churn-pct"
    figures[aid], figures[pid] = _fig_json(fig_a), _fig_json(fig_p)

    return (
        f'<div class="section"><h2>Establishment Dynamics</h2>'
        f'<p>{"".join(parts)}</p>'
        f'<div class="chart-row">'
        f'<div class="chart-col"><div id="{aid}" class="plotly-chart"></div></div>'
        f'<div class="chart-col"><div id="{pid}" class="plotly-chart"></div></div>'
        f'</div>{SOURCE}</div>'
    )


def build_premium(county_df, county_name, county_id, figures):
    """Wage Premium Analysis — employment LQ vs wage LQ scatter."""
    sectors = get_naics_sectors(county_df, own_code=5)
    latest = get_latest_quarter(sectors)
    if latest.empty:
        return '<div class="section"><h2>Wage Premium Analysis</h2><p>No LQ data available.</p></div>'

    plot_data = latest[
        (~latest["is_suppressed"]) & (latest["employment"] > 0)
        & latest["lq_month3_emplvl"].notna() & latest["lq_avg_wkly_wage"].notna()
        & (latest["industry_label"] != "Unclassified")
    ].copy()
    if plot_data.empty:
        return '<div class="section"><h2>Wage Premium Analysis</h2><p>No disclosable LQ data.</p></div>'

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    q1 = plot_data[(plot_data["lq_month3_emplvl"] > 1) & (plot_data["lq_avg_wkly_wage"] > 1)]
    q2 = plot_data[(plot_data["lq_month3_emplvl"] > 1) & (plot_data["lq_avg_wkly_wage"] <= 1)]

    parts = [
        f"This chart compares each industry's local employment concentration (x-axis) "
        f"to its local wage premium (y-axis) relative to U.S. averages. "
        f"Industries in the upper-right quadrant are {county_name} specializations "
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
        parts.append(f" In {year} Q{qtr}, {listing} stood out as concentrated specializations with above-average wages.")
    if not q2.empty:
        names = q2.nlargest(2, "employment")["industry_label"].tolist()
        pl = len(names) > 1
        parts.append(
            f" {' and '.join(names)} {'are' if pl else 'is'} overrepresented "
            f"but {'pay' if pl else 'pays'} below the national average."
        )

    fig = px.scatter(plot_data, x="lq_month3_emplvl", y="lq_avg_wkly_wage", size="employment",
                     text="industry_label",
                     labels={"lq_month3_emplvl": "Employment LQ (vs. U.S.)",
                             "lq_avg_wkly_wage": "Wage LQ (vs. U.S.)", "employment": "Employment"},
                     custom_data=["industry_label", "lq_month3_emplvl", "lq_avg_wkly_wage",
                                  "employment", "avg_annual_wage"])
    fig.update_traces(
        textposition="top center", textfont_size=9,
        marker=dict(color=plot_data["avg_annual_wage"].tolist(), colorscale="Plasma",
                    line=dict(width=1, color="white"), sizemin=8),
        hovertemplate="<b>%{customdata[0]}</b><br>Employment LQ: %{customdata[1]:.2f}<br>"
                      "Wage LQ: %{customdata[2]:.2f}<br>Employment: %{customdata[3]:,.0f}<br>"
                      "Avg Annual Wage: $%{customdata[4]:,.0f}<extra></extra>",
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=1)
    fig.add_vline(x=1.0, line_dash="dash", line_color="gray", line_width=1)

    x_max = plot_data["lq_month3_emplvl"].max()
    y_max = plot_data["lq_avg_wkly_wage"].max()
    x_min = plot_data["lq_month3_emplvl"].min()
    y_min = plot_data["lq_avg_wkly_wage"].min()
    annotations = [
        dict(x=max(1+(x_max-1)*0.7, 1.3), y=max(1+(y_max-1)*0.9, 1.3),
             text="Specialized &<br>Higher Paying", showarrow=False, font=dict(size=10, color="green"), opacity=0.6),
        dict(x=max(1+(x_max-1)*0.7, 1.3), y=min(1-(1-y_min)*0.7, 0.8),
             text="Specialized &<br>Lower Paying", showarrow=False, font=dict(size=10, color="orange"), opacity=0.6),
        dict(x=min(1-(1-x_min)*0.7, 0.7), y=max(1+(y_max-1)*0.9, 1.3),
             text="Underrepresented &<br>Higher Paying", showarrow=False, font=dict(size=10, color="steelblue"), opacity=0.6),
        dict(x=min(1-(1-x_min)*0.7, 0.7), y=min(1-(1-y_min)*0.7, 0.8),
             text="Underrepresented &<br>Lower Paying", showarrow=False, font=dict(size=10, color="gray"), opacity=0.6),
    ]
    fig.update_layout(annotations=annotations, height=600, showlegend=False)

    div_id = f"{county_id}-premium"
    figures[div_id] = _fig_json(fig)

    return (
        f'<div class="section"><h2>Wage Premium Analysis</h2>'
        f'<p>{"".join(parts)}</p>'
        f'<div id="{div_id}" class="plotly-chart"></div>{SOURCE}</div>'
    )


def build_lq(county_df, county_name, county_id, figures):
    """Location Quotients — diverging horizontal bars by sector."""
    sectors = get_naics_sectors(county_df, own_code=5)
    latest = get_latest_quarter(sectors)
    if latest.empty:
        return '<div class="section"><h2>Location Quotients</h2><p>No LQ data available.</p></div>'

    plot_data = latest[
        (~latest["is_suppressed"]) & (latest["employment"] > 0)
        & latest["lq_month3_emplvl"].notna() & (latest["industry_label"] != "Unclassified")
    ].copy().sort_values("lq_month3_emplvl", ascending=True)
    if plot_data.empty:
        return '<div class="section"><h2>Location Quotients</h2><p>No disclosable LQ data.</p></div>'

    row0 = plot_data.iloc[0]
    year, qtr = int(row0["year"]), int(row0["qtr"])

    specialized = plot_data[plot_data["lq_month3_emplvl"] > 1.0].nlargest(3, "lq_month3_emplvl")
    underrep = plot_data[plot_data["lq_month3_emplvl"] < 1.0].nsmallest(3, "lq_month3_emplvl")

    parts = [
        f"A location quotient (LQ) compares an industry's local employment share "
        f"to the national average. An LQ above 1.0 means the industry is more "
        f"concentrated in {county_name} than in the U.S. overall."
    ]
    if not specialized.empty:
        top = [f"{r['industry_label']} ({r['lq_month3_emplvl']:.2f})" for _, r in specialized.iterrows()]
        if len(top) >= 3:
            listing = ", ".join(top[:-1]) + f", and {top[-1]}"
        elif len(top) == 2:
            listing = f"{top[0]} and {top[1]}"
        else:
            listing = top[0]
        parts.append(f" In {year} Q{qtr}, {county_name}'s most specialized industries were {listing}.")
    if not underrep.empty:
        b = underrep.iloc[0]
        parts.append(f" {b['industry_label']} was the most underrepresented ({b['lq_month3_emplvl']:.2f}).")

    fig = px.bar(plot_data, x="lq_month3_emplvl", y="industry_label", orientation="h",
                 color="lq_month3_emplvl", color_continuous_scale="RdBu",
                 color_continuous_midpoint=1.0,
                 labels={"lq_month3_emplvl": "Location Quotient", "industry_label": ""},
                 custom_data=["industry_label", "lq_month3_emplvl", "employment"])
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>LQ: %{customdata[1]:.2f}<br>"
                      "Employment: %{customdata[2]:,.0f}<extra></extra>")
    fig.add_vline(x=1.0, line_color="black", line_width=1.5, line_dash="dash",
                  annotation_text="U.S. Average", annotation_position="top")
    fig.update_layout(xaxis_title="Location Quotient (1.0 = National Average)",
                      height=max(450, len(plot_data) * 28), showlegend=False, coloraxis_showscale=False)

    div_id = f"{county_id}-lq"
    figures[div_id] = _fig_json(fig)

    return (
        f'<div class="section"><h2>Location Quotients</h2>'
        f'<p>{"".join(parts)}</p>'
        f'<div id="{div_id}" class="plotly-chart"></div>{SOURCE}</div>'
    )


def build_concentration(county_df, county_name, county_id, figures):
    """Economic Concentration — HHI line chart with reference bands."""
    hhi_df = compute_hhi(county_df, own_code=5)
    if hhi_df.empty:
        return '<div class="section"><h2>Economic Concentration</h2><p>Not enough data to compute HHI.</p></div>'

    hhi_df = hhi_df.sort_values("date")
    latest_hhi = hhi_df.iloc[-1]["hhi"]

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

    narrative = (
        f"The Herfindahl-Hirschman Index (HHI) measures how concentrated "
        f"employment is across industries. {county_name} County's private sector "
        f"HHI is {latest_hhi:.3f}, indicating a <strong>{level}</strong> economy. "
        f"The trend has been {trend} over the past year."
    )

    color = COUNTY_COLORS.get(county_name, FAU_BLUE)
    fig = px.line(hhi_df, x="date", y="hhi", markers=True, labels={"date": "", "hhi": "HHI"})
    fig.update_traces(line_color=color, marker=dict(size=5))
    fig.add_hrect(y0=0, y1=0.10, fillcolor="green", opacity=0.08, line_width=0,
                  annotation_text="Diversified", annotation_position="top left")
    fig.add_hrect(y0=0.10, y1=0.25, fillcolor="orange", opacity=0.08, line_width=0,
                  annotation_text="Moderate", annotation_position="top left")
    fig.add_hrect(y0=0.25, y1=max(0.35, hhi_df["hhi"].max() + 0.02), fillcolor="red", opacity=0.08,
                  line_width=0, annotation_text="Concentrated", annotation_position="top left")
    fig.add_hline(y=0.10, line_dash="dot", line_color="gray", line_width=1)
    fig.add_hline(y=0.25, line_dash="dot", line_color="gray", line_width=1)
    fig.update_layout(hovermode="x unified", yaxis_tickformat=".3f", height=450)

    div_id = f"{county_id}-hhi"
    figures[div_id] = _fig_json(fig)

    return (
        f'<div class="section"><h2>Economic Concentration</h2>'
        f'<p>{narrative}</p>'
        f'<div id="{div_id}" class="plotly-chart"></div>{SOURCE}</div>'
    )


# ── HTML Assembly ────────────────────────────────────────────────────────────

SECTION_BUILDERS = [
    build_trends, build_treemap, build_wage_landscape, build_growth,
    build_scatter, build_churn, build_premium, build_lq, build_concentration,
]


def build_html(df):
    """Assemble the complete static HTML dashboard."""
    figures = {}

    # Data quarter badge
    sample_totals = get_total_covered(df)
    sample_latest = get_latest_quarter(sample_totals)
    if not sample_latest.empty:
        r = sample_latest.iloc[0]
        badge = f"Data as of {int(r['year'])} Q{int(r['qtr'])}"
    else:
        badge = "Data unavailable"

    # KPI cards
    kpi_cards = ""
    for county_name in COUNTY_ORDER:
        county_df = df[df["county_name"] == county_name]
        color = COUNTY_COLORS.get(county_name, FAU_BLUE)
        kpi_cards += build_kpi_card(county_df, county_name, color)

    # Tab buttons + tab content
    tab_buttons = ""
    tab_content = ""
    for county_name in COUNTY_ORDER:
        county_df = df[df["county_name"] == county_name]
        county_id = county_name.lower().replace(" ", "-")
        active = " active" if county_name == COUNTY_ORDER[0] else ""

        tab_buttons += (
            f'<button class="tab-btn{active}" data-tab="{county_id}" '
            f"onclick=\"showTab('{county_id}')\">{county_name} County</button>\n"
        )

        sections = []
        for i, builder in enumerate(SECTION_BUILDERS):
            if i > 0:
                sections.append('<div class="divider"></div>')
            sections.append(builder(county_df, county_name, county_id, figures))

        tab_content += f'<div id="{county_id}" class="tab-content{active}">\n'
        tab_content += "\n".join(sections)
        tab_content += "\n</div>\n"

    figures_json = json.dumps(figures)
    built = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Assemble HTML — CSS and JS are regular strings (no f-string escaping needed)
    return "\n".join([
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "<title>South Florida Regional Economic Report</title>",
        '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>',
        "<style>",
        CSS,
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        f'<h1 class="main-title">South Florida Regional Economic Report</h1>',
        f'<p class="main-subtitle">Quarterly Census of Employment and Wages (QCEW) &mdash; '
        f'Palm Beach, Broward &amp; Miami-Dade Counties</p>',
        f'<div class="data-badge">{badge}</div>',
        "</header>",
        f'<h3 style="color: {FAU_BLUE};">Regional Snapshot</h3>',
        f'<div class="snapshot-row">{kpi_cards}</div>',
        '<div class="divider"></div>',
        f'<div class="tab-bar">{tab_buttons}</div>',
        tab_content,
        '<footer class="footer">',
        f'Source: <a href="https://www.bls.gov/cew/">BLS QCEW</a> &mdash; Quarterly '
        f'| Last updated: {built}',
        "</footer>",
        "<script>",
        f"var figureData = {figures_json};",
        JS,
        "</script>",
        "</body>",
        "</html>",
    ])


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading QCEW data...")
    raw = fetch_all_data()
    if raw.empty:
        print("ERROR: No data available. Check your internet connection.")
        sys.exit(1)

    df = clean(raw)
    print(f"  {len(df):,} rows for {df['county_name'].nunique()} counties")

    print("Building HTML dashboard...")
    html = build_html(df)

    DOCS_DIR.mkdir(exist_ok=True)
    output = DOCS_DIR / "index.html"
    output.write_text(html, encoding="utf-8")
    print(f"Done! {output} ({output.stat().st_size / 1024:.0f} KB)")
