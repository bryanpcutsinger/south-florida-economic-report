"""
FRED API client for county-level real GDP and unemployment series.

Reads FRED_API_KEY from an environment variable. If missing or any call
fails, returns an empty DataFrame so the secondary KPI row gracefully
degrades to "—".
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import requests

from data.constants import FRED_API_BASE, FRED_GDP_SERIES, FRED_UNRATE_SERIES

CACHE_DIR = Path(__file__).parent / "cache"
GDP_CACHE = CACHE_DIR / "qcew_fred_gdp.parquet"
UNRATE_CACHE = CACHE_DIR / "qcew_fred_unrate.parquet"


def _fred_observations(series_id: str, api_key: str) -> pd.DataFrame:
    """Fetch one FRED series's observations as a (date, value) DataFrame."""
    url = f"{FRED_API_BASE}/series/observations"
    resp = requests.get(
        url,
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
        timeout=15,
    )
    resp.raise_for_status()
    obs = resp.json().get("observations", [])
    if not obs:
        return pd.DataFrame(columns=["date", "value"])
    df = pd.DataFrame(obs)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)


def _fetch_series_set(series_map: dict, api_key: str) -> pd.DataFrame:
    """Fetch all county series in long-format (county_name, date, value).

    Each series is tried up to 2 times to absorb transient network blips.
    Returns empty DataFrame if ANY county fails, so we never persist a
    partial cache that would silently drop counties on subsequent loads.
    """
    frames = []
    for county, sid in series_map.items():
        df = pd.DataFrame()
        for attempt in range(2):
            try:
                df = _fred_observations(sid, api_key)
                if not df.empty:
                    break
            except Exception:
                df = pd.DataFrame()
        if df.empty:
            return pd.DataFrame()  # don't persist a partial set
        df["county_name"] = county
        df["series_id"] = sid
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _fred_api_key() -> str:
    return os.environ.get("FRED_API_KEY", "").strip()


def fetch_real_gdp() -> pd.DataFrame:
    """Cached fetch of annual real GDP for the 3 counties.

    Returns an empty DataFrame if no cache and no API key is set.
    """
    if GDP_CACHE.exists():
        return pd.read_parquet(GDP_CACHE)
    api_key = _fred_api_key()
    if not api_key:
        return pd.DataFrame()
    df = _fetch_series_set(FRED_GDP_SERIES, api_key)
    if not df.empty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(GDP_CACHE, index=False)
    return df


def fetch_unemployment_rate() -> pd.DataFrame:
    """Cached fetch of monthly unemployment rate (NSA) for the 3 counties.

    Returns an empty DataFrame if no cache and no API key is set.
    """
    if UNRATE_CACHE.exists():
        return pd.read_parquet(UNRATE_CACHE)
    api_key = _fred_api_key()
    if not api_key:
        return pd.DataFrame()
    df = _fetch_series_set(FRED_UNRATE_SERIES, api_key)
    if not df.empty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(UNRATE_CACHE, index=False)
    return df
