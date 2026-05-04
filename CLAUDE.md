# South Florida Regional Economic Report

## What This Is
A single-page Streamlit + Plotly dashboard analyzing the economies of Palm Beach, Broward, and Miami-Dade counties using BLS Quarterly Census of Employment and Wages (QCEW) data. Features a regional snapshot on the main page with per-county deep-dive tabs. Run with `streamlit run app.py`.

## Project Structure

```
app.py                          # Main Streamlit app — regional snapshot + 3 county tabs
data/
  constants.py                  # FIPS codes (3 counties), NAICS labels, aggregation levels, FAU color palette
  clean.py                      # QCEW cleaning pipeline + filtering helpers
  analysis.py                   # STL trend decomposition + linear 2Q projection (deseasonalize_trend, project_trend)
  fetch.py                      # QCEW data fetch (BLS CSV API) — county + national caches in data/cache/
  fetch_fred.py                 # FRED API client — county real GDP + unemployment rate (powers KPI secondary row)
  fetch_irs_migration.py        # IRS SOI migration fetcher — net domestic migration per county (KPI secondary row)
  cache/                        # Parquet caches — qcew_data.parquet, qcew_national.parquet, qcew_fred_gdp.parquet, qcew_fred_unrate.parquet, qcew_irs_migration.parquet
components/
  employment_trends.py          # Side-by-side line charts — raw + STL trend + 2-quarter linear projection for employment and salary
  growth_quadrant.py            # Industry Landscape — YoY employment × YoY wage growth; bubbles colored by industry domain (not county); 4 tinted quadrants
  firm_formation.py             # Firm Openings & Closings — quarterly establishment churn aggregated from industry-level QoQ deltas
  specialties.py                # Industry Specialization — horizontal LQ bars with FAU-band coloring (≥1.25 blue, 1.0–1.25 stone, <1.0 gray)
  employment_treemap.py         # Workforce Composition — treemap of private employment by NAICS sector, colored by FAU industry domain
utils/
  formatting.py                 # fmt_number, fmt_currency, fmt_pct
  narratives.py                 # source_citation(), narrate_employment_trends(), format_industry_list()
```

## Dashboard Layout

### Main Page — Regional Snapshot
- Title and subtitle with data quarter badge
- 3 styled KPI cards (one per county), each showing two rows:
  - Primary (QCEW): Total Employment, Establishments, Average Salary — all with YoY % change.
  - Secondary: Real GDP ($B + YoY %), Unemployment rate (% + YoY pp delta, sign-inverted so falling = green), Net Migration (signed integer, IRS SOI tax-year flow, no arrow). Each cell labels its data period in small gray text.
- Secondary row reads "—" gracefully if `FRED_API_KEY` env var is missing or any fetch fails; primary row is unaffected.

### County Tabs (Palm Beach | Broward | Miami-Dade)
Each tab renders 5 sections for that county:

| # | Section | Component | Chart Type |
|---|---------|-----------|------------|
| 1 | Employment & Salary Trends | `employment_trends.py` | Side-by-side line charts (raw + STL trend + 2Q linear projection) |
| 2 | Workforce Composition | `employment_treemap.py` | Treemap — sectors sized by private employment, colored by FAU industry domain; hover shows employment, establishments, average salary, share. Year buttons below the chart switch the snapshot to the latest quarter of any year back to 2019. |
| 3 | Industry Landscape | `growth_quadrant.py` | Bubble scatter — YoY employment × YoY wage growth |
| 4 | Firm Openings & Closings | `firm_formation.py` | Stacked-relative bar — QoQ establishment additions (blue) vs. losses (red) per quarter, with net line + dashed U.S. benchmark overlay |
| 5 | Industry Specialization | `specialties.py` | Horizontal LQ bars with FAU band coloring (≥1.25 blue, 1.0–1.25 stone, <1.0 gray); reference lines at LQ=1.0 (U.S. average) and LQ=1.25 (strong specialty) |

## Counties

| County | FIPS | Card Color |
|--------|------|------------|
| Palm Beach | 12099 | FAU Blue (#003366) |
| Broward | 12011 | FAU Red (#CC0000) |
| Miami-Dade | 12086 | FAU Electric Blue (#126BD9) |

## FAU Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| FAU Blue | #003366 | Primary — headers, titles, metric values |
| FAU Red | #CC0000 | Broward accent, negative deltas |
| FAU Dark Gray | #4D4C55 | Body text, labels |
| FAU Gray | #CCCCCC | Borders, tab underlines |
| FAU Electric Blue | #126BD9 | Miami-Dade accent, links |
| FAU Stone | #7A97AB | Available for charts |
| FAU Sky Blue | #D9ECFF | Data badge background |
| FAU Sand | #D4B98B | Available for charts |

White background throughout (no dark theme).

## Key Design Decisions

- **Single page, no sidebar** — scroll-through narrative layout with tabs for county drill-downs
- **3 counties**: Palm Beach, Broward, Miami-Dade
- **QCEW data only** — all sections use BLS QCEW CSV API (no API key needed)
- **2-digit NAICS** (agglvl_code=74) for all industry analysis
- **Ownership codes**: Regional snapshot uses own_code=0 (Total Covered); all industry sections use own_code=5 (Private only)
- **"Unclassified" excluded** from all industry charts
- **Employment measure**: `month3_emplvl` (third month of quarter), aliased as `employment` in clean.py
- **Avg annual wage**: `avg_wkly_wage * 52`, derived in clean.py
- **Location quotients**: `lq_month3_emplvl` and `lq_avg_wkly_wage` — pre-computed by BLS in QCEW CSV
- **Component pattern**: Each component exposes `render(df)` — receives a pre-filtered county DataFrame
- **Data caching**: All 3 counties cached to `data/cache/qcew_data.parquet`; first load fetches from BLS (~3 min); subsequent loads read from disk

## Data Pipeline

1. `fetch.py` → downloads BLS CSV for each year/quarter/county (3 counties × years × quarters), caches to `qcew_data.parquet`. Also fetches the U.S. national aggregate (area code `US000`, agglvl=10) once and caches to `qcew_national.parquet` for the firm-formation benchmark line.
2. `clean.py` → standardizes types, adds `employment`, `avg_annual_wage`, `is_suppressed`, `industry_label` columns
3. `app.py` → filters `df[df["county_name"] == county]` for each tab, passes to components
4. Filter helpers in `clean.py`: `get_total_covered(df)`, `get_naics_sectors(df)`, `get_latest_quarter(df)`
5. `analysis.py` → `deseasonalize_trend(series, period=4, log_transform=False)` returns STL trend component

## API Keys

- **QCEW**: unauthenticated; no key needed.
- **FRED** (county GDP + unemployment for the secondary KPI row): set `FRED_API_KEY` in the environment. The user's global `~/.claude/CLAUDE.md` already lists their key. Without the env var, secondary KPI cells render "—" but the rest of the dashboard works.
- **IRS SOI** (net migration): public download, no key.

## Python Environment
- Python 3.9, venv at `.venv/`
- Key packages: streamlit, plotly, pandas, requests, statsmodels

## Cleanup History (2025-03-18)
Removed 27 legacy files from the old multi-tab, multi-county version:
- **21 component files**: building_permits, county_comparison, data_explorer, employment_shares, gdp, growth_analysis, hhi, income_distribution, industry_breakdown, industry_rankings, kpi_cards, location_quotient, personal_income, population, poverty_inequality, property_housing, seasonal_patterns, shift_share, time_series, unemployment, wage_distribution
- **6 data modules**: config (API key manager), fetch_bea, fetch_census, fetch_laus, fetch_permits, fetch_titles
- **Dead code trimmed** from analysis.py (3 unused functions), narratives.py (10 unused functions), formatting.py (3 unused functions), constants.py (INCOME_BRACKET_LABELS, BENCHMARK_GEOS, OWNERSHIP_CODES, naics_code_to_sector_label)

## Status as of 2025-03-18
- **Working dashboard**: Regional snapshot + 3 county tabs, all using QCEW data
- **FAU-themed**: White background, FAU color palette from https://www.fau.edu/styleguide/colors/
- **Goal**: Create a better economic report than the existing FAU South Florida Economic Report
- **Potential next steps**: Add non-QCEW data sources (BEA GDP, Census demographics, LAUS unemployment), add downloadable data tables, add cross-county comparison charts on the main page
