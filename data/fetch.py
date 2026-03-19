"""
Fetch QCEW data from BLS CSV API and cache locally as parquet.
Since QCEW data updates quarterly (with a 6-9 month lag), there's no reason
to hit the API on every app load. Data is fetched once and saved to disk;
use the "Refresh Data" button in the sidebar to pull new quarters.
"""
from __future__ import annotations
import io
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from data.constants import BLS_BASE_URL, COUNTIES, YEARS, QUARTERS

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "qcew_data.parquet"


def _fetch_from_bls() -> pd.DataFrame:
    """Fetch all county-quarter CSVs from BLS and return a consolidated DataFrame."""
    frames = []
    progress = st.progress(0, text="Fetching data from BLS...")
    total = len(COUNTIES) * len(YEARS) * len(QUARTERS)
    done = 0

    for fips in COUNTIES:
        for year in YEARS:
            for qtr in QUARTERS:
                url = BLS_BASE_URL.format(year=year, quarter=qtr, fips=fips)
                try:
                    resp = requests.get(url, timeout=30)
                    if resp.status_code == 200:
                        df = pd.read_csv(io.StringIO(resp.text))
                        df["county_name"] = COUNTIES[fips]
                        frames.append(df)
                except Exception:
                    pass
                done += 1
                progress.progress(done / total,
                                  text=f"Fetching data from BLS... ({done}/{total})")

    progress.empty()

    if not frames:
        st.error("No data could be fetched from BLS. Please try again later.")
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def _save_cache(df: pd.DataFrame) -> None:
    """Save DataFrame to local parquet cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE_FILE, index=False)


def _load_cache() -> pd.DataFrame | None:
    """Load cached parquet if it exists."""
    if CACHE_FILE.exists():
        return pd.read_parquet(CACHE_FILE)
    return None


def fetch_all_data() -> pd.DataFrame:
    """Load QCEW data from local cache, or fetch from BLS if no cache exists."""
    cached = _load_cache()
    if cached is not None:
        return cached

    # No cache — fetch fresh from BLS
    df = _fetch_from_bls()
    if not df.empty:
        _save_cache(df)
    return df


def refresh_data() -> pd.DataFrame:
    """Force re-fetch from BLS and update the local cache."""
    df = _fetch_from_bls()
    if not df.empty:
        _save_cache(df)
    return df
