"""
Cleaning pipeline and filtering helpers for QCEW data.
Handles type conversion, derived fields, disclosure suppression, and industry labeling.
"""
from __future__ import annotations
import pandas as pd

from data.constants import (
    NUMERIC_COLS,
    SUPERSECTOR_LABELS,
    SUPERSECTOR_DOMAIN_CODES,
    AGGLVL_TOTAL,
    AGGLVL_TOTAL_BY_OWN,
    AGGLVL_SUPERSECTOR,
    AGGLVL_NAICS_SECTOR,
    AGGLVL_NAICS_4DIGIT,
)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Full cleaning pipeline: types, derived fields, industry labels."""
    if df.empty:
        return df

    df = df.copy()

    # Strip quotes from string columns (BLS CSVs are quote-wrapped)
    for col in ["area_fips", "industry_code", "disclosure_code",
                "lq_disclosure_code", "oty_disclosure_code"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip('" ')

    # Convert numeric columns — coerce errors to NaN (handles suppressed values)
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Mark disclosure-suppressed rows
    df["is_suppressed"] = df["disclosure_code"] == "N"

    # Employment: use third month of each quarter (most complete count)
    df["employment"] = df["month3_emplvl"]

    # Quarter/year label for charts (e.g., "2024 Q2")
    df["year_qtr"] = df["year"].astype(int).astype(str) + " Q" + df["qtr"].astype(int).astype(str)

    # Date column for time series (use middle month of each quarter)
    quarter_to_month = {1: 2, 2: 5, 3: 8, 4: 11}
    df["date"] = pd.to_datetime(
        df["year"].astype(int).astype(str) + "-"
        + df["qtr"].map(quarter_to_month).astype(str) + "-01"
    )

    # Derived: average annual wage (weekly × 52)
    df["avg_annual_wage"] = df["avg_wkly_wage"] * 52

    # Sort for consistent ordering
    df = df.sort_values(["county_name", "date", "industry_code"]).reset_index(drop=True)

    # Industry labels — merge supersector domain codes + NAICS sector labels
    df["industry_label"] = df["industry_code"].map(SUPERSECTOR_DOMAIN_CODES)
    naics_mask = df["industry_label"].isna()
    df.loc[naics_mask, "industry_label"] = df.loc[naics_mask, "industry_code"].map(SUPERSECTOR_LABELS)

    # Fallback: use industry_code itself if no label found
    still_missing = df["industry_label"].isna()
    df.loc[still_missing, "industry_label"] = df.loc[still_missing, "industry_code"]

    # Special label for totals
    df.loc[df["industry_code"] == "10", "industry_label"] = "Total, All Industries"

    return df


# ── Filtering helpers ─────────────────────────────────────────────────────────

def get_total_covered(df: pd.DataFrame) -> pd.DataFrame:
    """Total covered employment (own_code=0, agglvl=70)."""
    return df[(df["own_code"] == 0) & (df["agglvl_code"] == AGGLVL_TOTAL)]


def get_total_by_ownership(df: pd.DataFrame, own_code: int = 5) -> pd.DataFrame:
    """Total by ownership type (agglvl=71)."""
    return df[(df["own_code"] == own_code) & (df["agglvl_code"] == AGGLVL_TOTAL_BY_OWN)]


def get_supersectors(df: pd.DataFrame, own_code: int = 5) -> pd.DataFrame:
    """Supersector-level data (agglvl=72) for a given ownership type."""
    return df[(df["own_code"] == own_code) & (df["agglvl_code"] == AGGLVL_SUPERSECTOR)]


def get_naics_sectors(df: pd.DataFrame, own_code: int = 5) -> pd.DataFrame:
    """NAICS 2-digit sector data (agglvl=74) for a given ownership type."""
    return df[(df["own_code"] == own_code) & (df["agglvl_code"] == AGGLVL_NAICS_SECTOR)]


def get_naics_4digit(df: pd.DataFrame, own_code: int = 5) -> pd.DataFrame:
    """NAICS 4-digit industry data (agglvl=76) for a given ownership type."""
    return df[(df["own_code"] == own_code) & (df["agglvl_code"] == AGGLVL_NAICS_4DIGIT)]


def get_latest_quarter(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to the most recent quarter available in the data."""
    if df.empty:
        return df
    max_date = df["date"].max()
    return df[df["date"] == max_date]


def filter_counties(df: pd.DataFrame, counties: list[str]) -> pd.DataFrame:
    """Filter to selected county names."""
    return df[df["county_name"].isin(counties)]


def filter_years(df: pd.DataFrame, year_range: tuple[int, int]) -> pd.DataFrame:
    """Filter to a year range (inclusive)."""
    return df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]


def get_filtered_totals(df: pd.DataFrame, own_code: int,
                        selected_industry: str | None = None) -> pd.DataFrame:
    """Return total-level rows, or single-industry rows when an industry is selected.

    When selected_industry is None (or "All Industries"), returns totals
    (own_code=0 → agglvl 70, otherwise agglvl 71).
    When an industry is specified, returns NAICS sector rows matching that label.
    """
    if selected_industry and selected_industry != "All Industries":
        sector = get_naics_sectors(df, own_code)
        return sector[sector["industry_label"] == selected_industry]
    # No industry filter — return totals
    if own_code == 0:
        return get_total_covered(df)
    return get_total_by_ownership(df, own_code)


def get_available_industries(df: pd.DataFrame, own_code: int) -> list[str]:
    """Sorted list of unique NAICS sector labels available for the dropdown."""
    sectors = get_naics_sectors(df, own_code)
    labels = sectors["industry_label"].dropna().unique().tolist()
    return sorted(labels)
