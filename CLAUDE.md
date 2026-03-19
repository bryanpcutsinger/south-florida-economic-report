# South Florida Regional Economic Report

## What This Is
A single-page Streamlit + Plotly dashboard analyzing the economies of Palm Beach, Broward, and Miami-Dade counties using BLS Quarterly Census of Employment and Wages (QCEW) data. Features a regional snapshot on the main page with per-county deep-dive tabs. Run with `streamlit run app.py`.

## Project Structure

```
app.py                          # Main Streamlit app — regional snapshot + 3 county tabs
data/
  constants.py                  # FIPS codes (3 counties), NAICS labels, aggregation levels, FAU color palette
  clean.py                      # QCEW cleaning pipeline + filtering helpers
  analysis.py                   # HHI concentration index computation
  fetch.py                      # QCEW data fetch (BLS CSV API) — parquet cached to data/cache/
  cache/                        # Parquet cache — first load fetches all 3 counties, then reads from disk
components/
  employment_trends.py          # Side-by-side line charts — total employment + avg annual wage over time
  industry_treemap.py           # Treemap — 2-digit NAICS sectors, size=employment, color=avg wage
  wage_landscape.py             # Horizontal bars — sectors ranked by avg annual wage
  industry_growth.py            # Side-by-side diverging bars — YoY employment + wage growth by sector
  wage_employment_scatter.py    # Scatter — x=employment, y=avg wage, size=establishments
  establishment_churn.py        # Side-by-side diverging bars — net establishment change (absolute + %)
  wage_premium.py               # Scatter — employment LQ vs wage LQ with quadrant labels
  location_quotients.py         # Diverging horizontal bars — employment LQ by sector
  concentration.py              # HHI line chart over time with reference bands
utils/
  formatting.py                 # fmt_number, fmt_currency, fmt_pct
  narratives.py                 # source_citation(), narrate_employment_trends(), narrate_wage_distribution()
```

## Dashboard Layout

### Main Page — Regional Snapshot
- Title and subtitle with data quarter badge
- 3 styled KPI cards (one per county) showing:
  - Total Employment with YoY % change
  - Establishments with YoY % change
  - Average Annual Salary with YoY % change

### County Tabs (Palm Beach | Broward | Miami-Dade)
Each tab renders 9 sections for that county:

| # | Section | Component | Chart Type |
|---|---------|-----------|------------|
| 1 | Employment Trends | `employment_trends.py` | Side-by-side line charts |
| 2 | Industry Composition | `industry_treemap.py` | Treemap — 2-digit NAICS |
| 3 | Wage Landscape | `wage_landscape.py` | Horizontal bars by wage |
| 4 | Industry Growth | `industry_growth.py` | Diverging bars (employment + wage YoY %) |
| 5 | Wage–Employment Landscape | `wage_employment_scatter.py` | Scatter with quadrant lines |
| 6 | Establishment Dynamics | `establishment_churn.py` | Diverging bars (absolute + %) |
| 7 | Wage Premium Analysis | `wage_premium.py` | LQ scatter with quadrant labels |
| 8 | Location Quotients | `location_quotients.py` | Diverging horizontal bars |
| 9 | Economic Concentration | `concentration.py` | HHI line with reference bands |

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

1. `fetch.py` → downloads BLS CSV for each year/quarter/county (3 counties × years × quarters), caches to parquet
2. `clean.py` → standardizes types, adds `employment`, `avg_annual_wage`, `is_suppressed`, `industry_label` columns
3. `app.py` → filters `df[df["county_name"] == county]` for each tab, passes to components
4. Filter helpers in `clean.py`: `get_total_covered(df)`, `get_naics_sectors(df)`, `get_latest_quarter(df)`
5. `analysis.py` → `compute_hhi(df, own_code=5)` returns HHI time series

## API Keys

None required. The QCEW CSV API is unauthenticated. Env vars for BEA/BLS/Census keys existed in the old version but have been removed.

## Python Environment
- Python 3.9, venv at `.venv/`
- Key packages: streamlit, plotly, pandas, requests

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
