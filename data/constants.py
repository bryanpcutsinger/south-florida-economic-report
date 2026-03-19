"""
Constants for the South Florida Regional Economic Dashboard.
FIPS codes, NAICS labels, ownership codes, color palettes, and API config.
"""
from datetime import date

# ── BLS QCEW API ──────────────────────────────────────────────────────────────
BLS_BASE_URL = "https://data.bls.gov/cew/data/api/{year}/{quarter}/area/{fips}.csv"

# Year range: 2019 through current year (API returns 404 for unpublished quarters)
START_YEAR = 2019
END_YEAR = date.today().year
YEARS = list(range(START_YEAR, END_YEAR + 1))
QUARTERS = [1, 2, 3, 4]

# ── Counties ──────────────────────────────────────────────────────────────────
COUNTIES = {
    "12099": "Palm Beach",
    "12011": "Broward",
    "12086": "Miami-Dade",
}

# ── FAU Color Palette ────────────────────────────────────────────────────────
FAU_BLUE = "#003366"
FAU_RED = "#CC0000"
FAU_DARK_GRAY = "#4D4C55"
FAU_GRAY = "#CCCCCC"
FAU_ELECTRIC_BLUE = "#126BD9"
FAU_STONE = "#7A97AB"
FAU_SKY_BLUE = "#D9ECFF"
FAU_SAND = "#D4B98B"

COUNTY_COLORS = {
    "Palm Beach": FAU_BLUE,
    "Broward": FAU_RED,
    "Miami-Dade": FAU_ELECTRIC_BLUE,
}

# ── Aggregation levels ────────────────────────────────────────────────────────
# 70 = Total, all industries (own_code 0 only)
# 71 = Total, all industries by ownership
# 72 = Supersector (NAICS domain)
# 73 = Supersector subdivision
# 74 = NAICS Sector (2-digit)
# 75 = NAICS 3-digit
# 76 = NAICS 4-digit
# 77 = NAICS 5-digit
# 78 = NAICS 6-digit
AGGLVL_TOTAL = 70          # Total covered, own_code=0
AGGLVL_TOTAL_BY_OWN = 71   # Total by ownership
AGGLVL_SUPERSECTOR = 72    # Supersector by ownership
AGGLVL_NAICS_SECTOR = 74   # 2-digit NAICS sector by ownership
AGGLVL_NAICS_4DIGIT = 76   # 4-digit NAICS industry by ownership

# ── Supersector labels (own_code 5 = private) ────────────────────────────────
SUPERSECTOR_LABELS = {
    "11":    "Agriculture",
    "21":    "Mining",
    "22":    "Utilities",
    "23":    "Construction",
    "31-33": "Manufacturing",
    "42":    "Wholesale Trade",
    "44-45": "Retail Trade",
    "48-49": "Transportation & Warehousing",
    "51":    "Information",
    "52":    "Finance & Insurance",
    "53":    "Real Estate",
    "54":    "Professional & Technical Services",
    "55":    "Management of Companies",
    "56":    "Admin & Waste Services",
    "61":    "Educational Services",
    "62":    "Health Care & Social Assistance",
    "71":    "Arts & Entertainment",
    "72":    "Accommodation & Food Services",
    "81":    "Other Services",
    "92":    "Public Administration",
    "99":    "Unclassified",
}

# Supersector codes used by each ownership type at agglvl 72
# (subset varies by ownership; own_code 5 has the broadest private set)
SUPERSECTOR_DOMAIN_CODES = {
    "101": "Goods-producing",
    "102": "Service-providing",
    "1011": "Natural Resources & Mining",
    "1012": "Construction",
    "1013": "Manufacturing",
    "1021": "Trade, Transportation & Utilities",
    "1022": "Information",
    "1023": "Financial Activities",
    "1024": "Professional & Business Services",
    "1025": "Education & Health Services",
    "1026": "Leisure & Hospitality",
    "1027": "Other Services",
    "1028": "Public Administration",
    "1029": "Unclassified",
}

# ── Numeric columns that need type conversion ─────────────────────────────────
NUMERIC_COLS = [
    "own_code", "agglvl_code", "size_code", "year", "qtr",
    "qtrly_estabs",
    "month1_emplvl", "month2_emplvl", "month3_emplvl",
    "total_qtrly_wages", "taxable_qtrly_wages", "qtrly_contributions",
    "avg_wkly_wage",
    "lq_qtrly_estabs",
    "lq_month1_emplvl", "lq_month2_emplvl", "lq_month3_emplvl",
    "lq_total_qtrly_wages", "lq_taxable_qtrly_wages",
    "lq_qtrly_contributions", "lq_avg_wkly_wage",
    "oty_qtrly_estabs_chg", "oty_qtrly_estabs_pct_chg",
    "oty_month1_emplvl_chg", "oty_month1_emplvl_pct_chg",
    "oty_month2_emplvl_chg", "oty_month2_emplvl_pct_chg",
    "oty_month3_emplvl_chg", "oty_month3_emplvl_pct_chg",
    "oty_total_qtrly_wages_chg", "oty_total_qtrly_wages_pct_chg",
    "oty_taxable_qtrly_wages_chg", "oty_taxable_qtrly_wages_pct_chg",
    "oty_qtrly_contributions_chg", "oty_qtrly_contributions_pct_chg",
    "oty_avg_wkly_wage_chg", "oty_avg_wkly_wage_pct_chg",
]

