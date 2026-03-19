"""
Analytical computations: HHI concentration index.
"""
from __future__ import annotations
import pandas as pd

from data.clean import get_naics_sectors


def compute_hhi(df: pd.DataFrame, own_code: int) -> pd.DataFrame:
    """Herfindahl-Hirschman Index per county per quarter.

    HHI = sum of squared employment shares across NAICS sectors.
    Values near 0 = diversified, near 1 = concentrated.
    """
    sectors = get_naics_sectors(df, own_code)
    sectors = sectors[
        (~sectors["is_suppressed"]) & (sectors["employment"] > 0)
    ].copy()

    if sectors.empty:
        return pd.DataFrame(columns=["county_name", "date", "year_qtr", "hhi"])

    # Total employment per county-quarter for shares
    county_totals = (
        sectors.groupby(["county_name", "date", "year_qtr"])["employment"]
        .sum()
        .rename("total_empl")
        .reset_index()
    )

    merged = sectors.merge(county_totals, on=["county_name", "date", "year_qtr"])
    merged["share"] = merged["employment"] / merged["total_empl"]
    merged["share_sq"] = merged["share"] ** 2

    hhi = (
        merged.groupby(["county_name", "date", "year_qtr"])["share_sq"]
        .sum()
        .rename("hhi")
        .reset_index()
    )

    return hhi.sort_values(["county_name", "date"]).reset_index(drop=True)
