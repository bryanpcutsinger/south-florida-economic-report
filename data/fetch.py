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

try:
    import streamlit as st
except ImportError:
    st = None

from data.constants import BLS_BASE_URL, COUNTIES, YEARS, QUARTERS, AGGLVL_US_TOTAL

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "qcew_data.parquet"
NATIONAL_CACHE_FILE = CACHE_DIR / "qcew_national.parquet"


def _fetch_from_bls() -> pd.DataFrame:
    """Fetch all county-quarter CSVs from BLS and return a consolidated DataFrame."""
    frames = []
    total = len(COUNTIES) * len(YEARS) * len(QUARTERS)
    done = 0

    # Use Streamlit progress bar if available, otherwise print to console
    use_st = False
    if st is not None:
        try:
            progress = st.progress(0, text="Fetching data from BLS...")
            use_st = True
        except Exception:
            pass
    if not use_st:
        print("Fetching data from BLS...", flush=True)

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
                if use_st:
                    progress.progress(done / total,
                                      text=f"Fetching data from BLS... ({done}/{total})")
                else:
                    print(f"\r  {done}/{total}", end="", flush=True)

    if use_st:
        progress.empty()
    else:
        print()

    if not frames:
        msg = "No data could be fetched from BLS. Please try again later."
        if use_st:
            st.error(msg)
        else:
            print(f"ERROR: {msg}")
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
    """Force re-fetch from BLS and update the local cache.

    NOTE: this only refreshes the per-county cache. The national cache
    (qcew_national.parquet) is left untouched because no UI currently
    invokes refresh_data(). When a Refresh button is added to app.py,
    extend this function to also call _fetch_national_from_bls().
    """
    df = _fetch_from_bls()
    if not df.empty:
        _save_cache(df)
    return df


# ── National (US000) fetch ───────────────────────────────────────────────────


def _fetch_national_from_bls() -> pd.DataFrame:
    """Fetch US000 (national totals) for each year/quarter.

    Returns RAW BLS columns filtered to (own_code=0, agglvl_code=AGGLVL_US_TOTAL),
    which yields exactly one row per quarter (empirically verified for 2024 Q1).

    Do NOT pass this through clean() — clean() requires the `county_name`
    column added by the per-county fetcher.
    """
    frames = []
    total = len(YEARS) * len(QUARTERS)
    done = 0

    use_st = False
    if st is not None:
        try:
            progress = st.progress(0, text="Fetching U.S. national QCEW from BLS...")
            use_st = True
        except Exception:
            pass
    if not use_st:
        print("Fetching U.S. national QCEW from BLS...", flush=True)

    for year in YEARS:
        for qtr in QUARTERS:
            url = BLS_BASE_URL.format(year=year, quarter=qtr, fips="US000")
            try:
                resp = requests.get(url, timeout=60)  # larger timeout — file is bigger
                if resp.status_code == 200:
                    df = pd.read_csv(io.StringIO(resp.text))
                    df = df[(df["own_code"] == 0) & (df["agglvl_code"] == AGGLVL_US_TOTAL)]
                    frames.append(df)
            except Exception:
                pass
            done += 1
            if use_st:
                progress.progress(done / total,
                                  text=f"Fetching U.S. national QCEW... ({done}/{total})")
            else:
                print(f"\r  {done}/{total}", end="", flush=True)

    if use_st:
        progress.empty()
    else:
        print()

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fetch_national_data() -> pd.DataFrame:
    """Load national QCEW totals from cache, or fetch from BLS if no cache exists.

    Returns raw BLS columns (NOT cleaned). Use data.clean.get_national_qoq_pct
    to derive the QoQ percent change series.
    """
    if NATIONAL_CACHE_FILE.exists():
        return pd.read_parquet(NATIONAL_CACHE_FILE)
    df = _fetch_national_from_bls()
    if not df.empty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(NATIONAL_CACHE_FILE, index=False)
    return df
