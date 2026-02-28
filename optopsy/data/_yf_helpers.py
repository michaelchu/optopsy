"""Yahoo Finance fetch-and-cache helpers.

Provides ``_yf_fetch_and_cache`` and ``_normalise_yf_df`` for downloading
stock/index OHLCV data via yfinance and caching it in the parquet cache.
"""

import logging
from datetime import date, timedelta

import pandas as pd

from optopsy.data.providers.cache import get_store

_log = logging.getLogger(__name__)

# Cache for yfinance OHLCV data (category="yf_stocks", one file per symbol).
# Deliberately distinct from EODHD's "stocks" category to avoid schema collisions.
_yf_cache = get_store()
_YF_CACHE_CATEGORY = "yf_stocks"
_YF_DEDUP_COLS = ["date"]


def _snap_to_weekday(dt: date, *, forward: bool = False) -> date:
    """Snap a date to the nearest weekday (Mon–Fri).

    By default snaps backward (Sat→Fri, Sun→Fri).  With *forward=True*,
    snaps forward instead (Sat→Mon, Sun→Mon).
    """
    wd = dt.weekday()  # Mon=0 … Sun=6
    if wd == 5:  # Saturday
        return dt + timedelta(days=2) if forward else dt - timedelta(days=1)
    if wd == 6:  # Sunday
        return dt + timedelta(days=1) if forward else dt - timedelta(days=2)
    return dt


def _yf_fetch_and_cache(
    symbol: str,
    cached: pd.DataFrame | None,
    end_dt: date,
) -> pd.DataFrame | None:
    """Fetch missing yfinance data and update the cache.

    On cold cache, fetches everything with ``period="max"``.  On warm cache,
    fetches only the tail from ``cache_max + 1`` to *end_dt* (the only gap
    worth considering — yfinance returns all available data on first fetch,
    so interior gaps are just non-trading days).

    Returns the updated cached DataFrame, or None when yfinance returns no
    data on a cold cache.  Exceptions from yfinance (``OSError``,
    ``ValueError``) are **not** caught here — callers are responsible for
    handling them.
    """
    import yfinance as yf

    # Snap end_dt back to the last weekday — markets are closed on weekends,
    # so fetching Sat/Sun windows is pointless and returns empty results.
    end_dt = _snap_to_weekday(end_dt)

    if cached is None or cached.empty:
        _log.info("Cold cache for %s, fetching full history from yfinance", symbol)
        raw = yf.download(symbol, period="max", progress=False)
    else:
        cache_max = pd.to_datetime(cached["date"]).dt.date.max()
        fetch_start = _snap_to_weekday(cache_max + timedelta(days=1), forward=True)
        if fetch_start > end_dt:
            _log.info("Cache for %s is up to date, skipping yfinance", symbol)
            return cached
        _log.info(
            "Fetching %s stock data from %s to %s",
            symbol,
            fetch_start,
            end_dt,
        )
        raw = yf.download(
            symbol,
            start=str(fetch_start),
            end=str(end_dt + timedelta(days=1)),
            progress=False,
        )

    if not raw.empty:
        new_data = _normalise_yf_df(raw, symbol)
        cached = _yf_cache.merge_and_save(
            _YF_CACHE_CATEGORY, symbol, new_data, dedup_cols=_YF_DEDUP_COLS
        )
    return cached


def _normalise_yf_df(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalise a raw yfinance download DataFrame for cache storage.

    Flattens MultiIndex columns, lowercases names, strips timezone info, adds
    ``underlying_symbol``, and keeps ``date`` (not ``quote_date``) as the date
    column so rows are compatible with the ``stocks/`` cache schema.
    """
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    # yfinance uses "date" as the index name; ensure it's present
    if "date" not in df.columns and "index" in df.columns:
        df = df.rename(columns={"index": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df["underlying_symbol"] = symbol
    keep = ["underlying_symbol", "date", "open", "high", "low", "close", "volume"]
    return df[[c for c in keep if c in df.columns]]
