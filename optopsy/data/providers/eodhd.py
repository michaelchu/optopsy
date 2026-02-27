"""EODHD data provider for historical US equity options chains.

Implements the ``DataProvider`` interface to fetch options data from the
EODHD Marketplace API.  Key features:

- **Bulk download** (``download_options_data``) — fetches the complete
  historical options chain for a symbol, split by option type and paginated
  in ~30-day windows to stay within the 10K-offset API cap.  Supports
  resumable downloads: only rows newer than the latest cached date are fetched.
- **Local read** (``fetch_options_data``) — reads previously downloaded data
  from the parquet cache and applies date/type/expiration filters.
- **Rate limiting** — adaptive throttle based on ``X-RateLimit-Remaining``
  header, with exponential backoff on 429 and 5xx errors.
- **Progress callbacks** — ``download_with_progress()`` accepts callbacks for
  Rich live-display integration in the CLI.
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Callable

import pandas as pd
import requests

from .base import DataProvider
from .cache import ParquetCache

_log = logging.getLogger(__name__)

# Redact api_token from urllib3 debug logs to avoid leaking secrets
_TOKEN_RE = re.compile(r"api_token=[^&\s]+")


class _RedactTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = tuple(
                _TOKEN_RE.sub("api_token=***", str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        record.msg = _TOKEN_RE.sub("api_token=***", str(record.msg))
        return True


logging.getLogger("urllib3.connectionpool").addFilter(_RedactTokenFilter())

_BASE_URL = "https://eodhd.com/api/mp/unicornbay"
_PAGE_LIMIT = 1000
_MAX_OFFSET = 10000  # EODHD rejects offsets beyond ~10K
_TIMEOUT = 60
_MAX_RETRIES = 5
_API_CALLS_PER_REQUEST = 10  # EODHD Marketplace/Options endpoints cost 10 calls each
_MIN_REQUEST_INTERVAL = 0.1  # seconds between requests (600/min, under 1000/min cap)
_RATE_LIMIT_SLOW_THRESHOLD = 50  # slow down when fewer than this many requests remain
_FIELDS = (
    "underlying_symbol,type,exp_date,expiration_type,tradetime,strike,"
    "bid,ask,last,open,high,low,"
    "volume,open_interest,"
    "delta,gamma,theta,vega,rho,volatility,"
    "midpoint,moneyness,theoretical,dte"
)

_COLUMN_MAP = {
    "underlying_symbol": "underlying_symbol",
    "type": "option_type",
    "exp_date": "expiration",
    "tradetime": "quote_date",
    "strike": "strike",
    "bid": "bid",
    "ask": "ask",
    "volume": "volume",
    "delta": "delta",
    "gamma": "gamma",
    "theta": "theta",
    "vega": "vega",
    "rho": "rho",
    "volatility": "implied_volatility",
}

_OPTIONS_NUMERIC_COLS = [
    "strike",
    "bid",
    "ask",
    "last",
    "open",
    "high",
    "low",
    "volume",
    "open_interest",
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
    "implied_volatility",
    "midpoint",
    "moneyness",
    "theoretical",
    "dte",
]


def _parse_date(value: str | None):
    """Parse a YYYY-MM-DD string to a date, or return None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Coerce columns to numeric in-place, ignoring missing columns."""
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _check_response(resp: requests.Response) -> str | None:
    """Return an error string for known EODHD error codes, or None if OK."""
    if resp.status_code == 401:
        return "EODHD API key is invalid or expired."
    if resp.status_code == 403:
        return "EODHD API access denied. Check your subscription plan."
    if resp.status_code == 429:
        return "EODHD rate limit exceeded. Try again later."
    if resp.status_code >= 500:
        return f"EODHD server error ({resp.status_code}). The API may be temporarily unavailable — try again later."
    return None


def _safe_raise_for_status(resp: requests.Response) -> None:
    """Like resp.raise_for_status() but strips api_token from the error URL."""
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        sanitized = re.sub(r"api_token=[^&\s]+", "api_token=***", str(exc))
        raise requests.HTTPError(sanitized, response=resp) from None


class EODHDProvider(DataProvider):
    def __init__(self) -> None:
        self._cache = ParquetCache()
        self._session = requests.Session()
        self._last_request_time: float = 0.0
        self._request_count: int = 0

    @property
    def name(self) -> str:
        return "EODHD"

    @property
    def env_key(self) -> str:
        return "EODHD_API_KEY"

    def list_available_symbols(self) -> list[str] | None:
        """Fetch the list of symbols with options data from EODHD."""
        api_key = self._get_api_key()
        if not api_key:
            return None
        try:
            resp = self._throttled_get(
                f"{_BASE_URL}/options/underlying-symbols",
                {"api_token": api_key},
            )
            error = _check_response(resp)
            if error:
                _log.warning("Failed to fetch available symbols: %s", error)
                return None
            _safe_raise_for_status(resp)
            return resp.json().get("data", [])
        except Exception as exc:
            _log.warning("Failed to fetch available symbols: %s", exc)
            return None

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [self._download_schema(), self._options_schema()]

    def get_tool_names(self) -> list[str]:
        return ["download_options_data", "fetch_options_data"]

    def replaces_dataset(self, tool_name: str) -> bool:
        # download stores data to disk; it does not become the active dataset
        if tool_name == "download_options_data":
            return False
        return True

    def download_with_progress(
        self,
        symbol: str,
        on_progress: Callable[[str, str, int, float], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[str, pd.DataFrame | None]:
        """Download options data with optional progress and status callbacks.

        ``on_progress(symbol, option_type, rows_fetched, pct)`` — *pct* is
        0.0–100.0 representing date-range coverage for the current option type.
        ``on_status`` is called with human-readable status messages.
        """
        return self._download_all_options(
            symbol=symbol, on_progress=on_progress, on_status=on_status
        )

    def execute(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[str, pd.DataFrame | None]:
        if tool_name == "download_options_data":
            return self._download_all_options(symbol=arguments["symbol"])
        if tool_name == "fetch_options_data":
            return self._fetch_options(
                symbol=arguments["symbol"],
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                option_type=arguments.get("option_type"),
                expiration_type=arguments.get("expiration_type", "monthly"),
            )
        return f"Unknown tool: {tool_name}", None

    # -- private helpers --

    def _get_api_key(self) -> str | None:
        return os.environ.get(self.env_key)

    def _throttled_get(self, url: str, params: dict) -> requests.Response:
        """Rate-limited GET with retry on transient errors and 429 backoff.

        Enforces a minimum interval between requests to stay under the
        1,000 requests/minute EODHD cap.  Reads ``X-RateLimit-Remaining``
        and slows down when the quota is nearly exhausted.
        """
        for attempt in range(_MAX_RETRIES + 1):
            # Enforce minimum interval between requests
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < _MIN_REQUEST_INTERVAL:
                time.sleep(_MIN_REQUEST_INTERVAL - elapsed)

            try:
                self._last_request_time = time.monotonic()
                resp = self._session.get(url, params=params, timeout=_TIMEOUT)
                self._request_count += 1
            except requests.RequestException:
                if attempt == _MAX_RETRIES:
                    raise
                time.sleep(2**attempt)
                continue

            # Handle 5xx server errors with exponential backoff
            if resp.status_code >= 500:
                if attempt == _MAX_RETRIES:
                    return resp  # let caller handle the error
                wait = 2 ** (attempt + 1)
                _log.warning(
                    "EODHD %d server error, backing off %ds (attempt %d/%d)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                time.sleep(wait)
                continue

            # Handle 429 with exponential backoff
            if resp.status_code == 429:
                if attempt == _MAX_RETRIES:
                    return resp  # let caller handle the error
                wait = 2 ** (attempt + 1)
                _log.warning(
                    "EODHD 429 rate limit hit, backing off %ds (attempt %d/%d)",
                    wait,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                time.sleep(wait)
                continue

            # Adaptive throttle: slow down when approaching the per-minute cap
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                try:
                    remaining_int = int(remaining)
                    if remaining_int < _RATE_LIMIT_SLOW_THRESHOLD:
                        _log.info(
                            "EODHD rate limit remaining: %d, throttling", remaining_int
                        )
                        time.sleep(1.0)
                except ValueError:
                    pass

            return resp
        raise AssertionError("unreachable")

    def _paginate_window(
        self,
        api_key: str,
        base_params: dict[str, Any],
        on_progress: Callable[[int], None] | None = None,
    ) -> tuple[list[dict], bool, str | None]:
        """Paginate through a single date window using compact mode.

        Returns ``(rows, hit_cap, error_or_none)``.  ``hit_cap`` is True when
        the offset limit was reached, signalling that more data likely exists
        beyond this window.
        """
        rows: list[dict] = []
        url = f"{_BASE_URL}/options/eod"
        params = {
            **base_params,
            "api_token": api_key,
            "page[offset]": 0,
            "compact": 1,
        }
        offset = 0
        hit_cap = False

        while True:
            resp = self._throttled_get(url, params)
            error = _check_response(resp)
            if error:
                return [], False, error
            if resp.status_code == 422:
                # API rejects large offsets — treat like hitting the cap
                hit_cap = True
                break
            _safe_raise_for_status(resp)

            data = resp.json()

            # Compact mode: data is a list of arrays, field names in meta.fields
            meta = data.get("meta", {})
            fields = meta.get("fields", [])
            page_rows = data.get("data", [])
            if not page_rows:
                break

            if fields:
                # Compact format — zip field names with each row array
                for row in page_rows:
                    rows.append(dict(zip(fields, row)))
            else:
                # Fallback to standard format if compact somehow not applied
                for row in page_rows:
                    attrs = row.get("attributes", row)
                    rows.append(attrs)

            if on_progress:
                on_progress(len(rows))

            offset += _PAGE_LIMIT
            next_url = data.get("links", {}).get("next")
            if not next_url or offset >= _MAX_OFFSET:
                hit_cap = bool(next_url)
                break

            url = next_url
            params = {"api_token": api_key, "compact": 1}

        return rows, hit_cap, None

    # -- bulk download --

    def _download_all_options(
        self,
        symbol: str,
        on_progress: Callable[[str, str, int, float], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[str, pd.DataFrame | None]:
        """Download ALL historical options data for a symbol from EODHD.

        Splits requests by option type (call/put) to stay within the 10K
        offset pagination cap.  Stores the complete dataset to a local
        parquet file for subsequent reads by ``_fetch_options``.

        Supports resumable downloads: checks the cache for existing data
        and only fetches rows newer than the latest cached ``quote_date``
        per option type.  Each pagination window is saved incrementally
        so progress is never lost on interruption.
        """
        symbol = symbol.upper()
        api_key = self._get_api_key()
        if not api_key:
            return "EODHD_API_KEY not configured. Add it to your .env file.", None

        self._request_count = 0  # reset counter for this download
        _status = on_status or (lambda msg: None)

        # Check for existing cached data to enable resume
        cached_df = self._cache.read("options", symbol)
        cached_rows = len(cached_df) if cached_df is not None else 0
        is_resume = cached_rows > 0

        errors: list[str] = []
        new_rows_total = 0

        for option_type in ("call", "put"):
            # Determine resume point from cache
            resume_from: str | None = None
            if cached_df is not None and not cached_df.empty:
                type_mask = (
                    cached_df["option_type"].str.lower().str.startswith(option_type[0])
                )
                type_cached = cached_df.loc[type_mask]
                if not type_cached.empty:
                    max_date = pd.to_datetime(type_cached["quote_date"]).max()
                    resume_from = str((max_date + timedelta(days=1)).date())
                    _status(
                        f"Resuming {symbol} {option_type} options from {resume_from} "
                        f"({len(type_cached):,} cached rows)"
                    )
                    _log.info(
                        "Resuming %s %s options from %s (%s cached rows)",
                        symbol,
                        option_type,
                        resume_from,
                        f"{len(type_cached):,}",
                    )

            _status(f"Downloading {symbol} {option_type} options…")
            _log.info("Downloading %s %s options from EODHD…", symbol, option_type)
            new_rows, error = self._fetch_all_for_type(
                api_key,
                symbol,
                option_type,
                resume_from=resume_from,
                on_progress=on_progress,
                on_status=on_status,
            )
            if error:
                errors.append(f"{option_type}: {error}")
                _status(
                    f"Error fetching {symbol} {option_type} options "
                    f"(saved {new_rows:,} rows before error): {error}"
                )
                _log.warning(
                    "Error fetching %s %s options (saved %s rows before error): %s",
                    symbol,
                    option_type,
                    f"{new_rows:,}",
                    error,
                )
            else:
                _status(f"Done: {new_rows:,} new {option_type} rows for {symbol}")
                _log.info(
                    "Downloaded %s new %s rows for %s",
                    f"{new_rows:,}",
                    option_type,
                    symbol,
                )
            new_rows_total += new_rows

        # Re-read the cache to build summary (includes both old + new data)
        df = self._cache.read("options", symbol)

        if df is None or df.empty:
            if errors:
                return (
                    f"Download failed for {symbol}: {'; '.join(errors)}. "
                    "No data was saved. Please retry.",
                    None,
                )
            return f"No options data found for {symbol} on EODHD.", None

        # Build summary
        date_min = df["quote_date"].min().date()
        date_max = df["quote_date"].max().date()
        exp_types = "unknown"
        if "expiration_type" in df.columns:
            counts = df["expiration_type"].value_counts()
            exp_types = ", ".join(f"{k}: {v:,}" for k, v in counts.items())
        file_size = self._cache.total_size_bytes()
        size_mb = round(file_size / 1_048_576, 2)
        api_calls = self._request_count * _API_CALLS_PER_REQUEST

        if is_resume and new_rows_total > 0:
            status = (
                f"Resumed download for {symbol}: added {new_rows_total:,} new rows "
                f"to {cached_rows:,} previously cached. "
                f"Total: {len(df):,} records."
            )
        elif is_resume and new_rows_total == 0:
            status = (
                f"Cache for {symbol} is already up to date "
                f"({len(df):,} records, no new data fetched)."
            )
        else:
            status = f"Downloaded {len(df):,} options records for {symbol}."

        summary = (
            f"{status} "
            f"Date range: {date_min} to {date_max}. "
            f"Expiration types: {exp_types}. "
            f"Saved to local storage ({size_mb} MB total cache). "
            f"API usage: {self._request_count} requests ({api_calls:,} API calls)."
        )

        if errors:
            summary += (
                f" WARNING: partial errors occurred: {'; '.join(errors)}. "
                "Run download_options_data again to retry and fetch remaining data."
            )

        _log.info(summary)
        return summary, None

    _DEDUP_COLS = [
        "quote_date",
        "expiration",
        "strike",
        "option_type",
        "expiration_type",
    ]

    def _normalize_and_save_window(self, rows: list[dict], symbol: str) -> pd.DataFrame:
        """Normalize raw API rows and incrementally merge into the cache."""
        df = pd.DataFrame(rows)
        df = df.rename(columns=_COLUMN_MAP)
        if "expiration" in df.columns:
            df["expiration"] = pd.to_datetime(df["expiration"])
        if "quote_date" in df.columns:
            df["quote_date"] = pd.to_datetime(df["quote_date"])
        _coerce_numeric(df, _OPTIONS_NUMERIC_COLS)

        dedup_cols = [c for c in self._DEDUP_COLS if c in df.columns]
        self._cache.merge_and_save("options", symbol, df, dedup_cols or None)
        return df

    @staticmethod
    def _quarter_windows(start: datetime, end: datetime) -> list[tuple[str, str]]:
        """Generate (from_date, to_date) ~30-day windows, newest first."""
        windows: list[tuple[str, str]] = []
        cur = end
        while cur > start:
            q_start = max(cur - timedelta(days=30), start)
            windows.append((str(q_start.date()), str(cur.date())))
            cur = q_start - timedelta(days=1)
        return windows

    _MIN_WINDOW_DAYS = 1  # stop subdividing at single-day windows

    def _fetch_window_recursive(
        self,
        api_key: str,
        symbol: str,
        option_type: str,
        win_from: str,
        win_to: str,
        rows_fetched: int,
        on_progress: Callable[[str, str, int, float], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> tuple[int, str | None]:
        """Fetch a single date window, subdividing if the offset cap is hit."""
        from_dt = _parse_date(win_from)
        to_dt = _parse_date(win_to)
        if not from_dt or not to_dt:
            return 0, None

        _status = on_status or (lambda msg: None)
        span_days = (to_dt - from_dt).days

        def _pct_at(d: str) -> float:
            """Compute date-range percentage for a given date string."""
            if not date_range:
                return 0.0
            total = (date_range[1] - date_range[0]).days
            if total <= 0:
                return 100.0
            parsed = _parse_date(d)
            if not parsed:
                return 0.0
            # Newest-first: percentage = how far back from end we've reached
            remaining = (
                datetime(parsed.year, parsed.month, parsed.day) - date_range[0]
            ).days
            return min(100.0, max(0.0, (1 - remaining / total) * 100))

        _log.info(
            "Fetching %s %s options: %s to %s (%d days) — %s total rows so far",
            symbol,
            option_type,
            win_from,
            win_to,
            span_days,
            f"{rows_fetched:,}",
        )

        base_params: dict[str, Any] = {
            "filter[underlying_symbol]": symbol,
            "filter[type]": option_type,
            "filter[tradetime_from]": win_from,
            "filter[tradetime_to]": win_to,
            "fields[options-eod]": _FIELDS,
            "page[limit]": _PAGE_LIMIT,
            "sort": "exp_date",
        }

        pct = _pct_at(win_from)

        def _page_progress(page_rows: int) -> None:
            if on_progress:
                on_progress(symbol, option_type, rows_fetched + page_rows, pct)

        rows, hit_cap, error = self._paginate_window(
            api_key, base_params, on_progress=_page_progress
        )

        window_rows = len(rows)
        if rows:
            self._normalize_and_save_window(rows, symbol)
            rows_fetched += window_rows
            if on_progress:
                on_progress(symbol, option_type, rows_fetched, pct)

        if error:
            _status(f"  Error {win_from}–{win_to} ({option_type}): {error} — skipping")
            _log.warning(
                "Error fetching %s to %s for %s %s: %s — continuing",
                win_from,
                win_to,
                symbol,
                option_type,
                error,
            )
            return rows_fetched, None  # continue, don't abort

        if hit_cap and span_days > self._MIN_WINDOW_DAYS:
            # Undo the partial count — subdivision will re-fetch this range fully
            rows_fetched -= window_rows
            # Window too large — subdivide into two halves and retry
            _status(f"  Window {win_from}–{win_to} hit 10K cap, subdividing…")
            _log.warning(
                "Offset cap hit for %s %s (%s to %s), subdividing into smaller windows",
                symbol,
                option_type,
                win_from,
                win_to,
            )
            mid = from_dt + timedelta(days=span_days // 2)
            # First half: already fetched partial data, re-fetch with smaller window
            rows_fetched, _ = self._fetch_window_recursive(
                api_key,
                symbol,
                option_type,
                win_from,
                str(mid),
                rows_fetched,
                on_progress,
                on_status,
                date_range,
            )
            # Second half
            rows_fetched, _ = self._fetch_window_recursive(
                api_key,
                symbol,
                option_type,
                str(mid + timedelta(days=1)),
                win_to,
                rows_fetched,
                on_progress,
                on_status,
                date_range,
            )

        return rows_fetched, None

    def _fetch_all_for_type(
        self,
        api_key: str,
        symbol: str,
        option_type: str,
        resume_from: str | None = None,
        on_progress: Callable[[str, str, int, float], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> tuple[int, str | None]:
        """Fetch all rows for a single option type using date windows.

        Returns ``(rows_fetched, error_or_none)``.  Downloads data in ~30-day
        chunks.  If a window hits the 10K offset cap, it automatically
        subdivides into smaller windows to avoid gaps.
        """
        rows_fetched = 0
        _status = on_status or (lambda msg: None)

        # EODHD provides ~2 years of historical options data
        start = datetime.now() - timedelta(days=730)
        if resume_from:
            parsed = _parse_date(resume_from)
            if parsed:
                start = datetime(parsed.year, parsed.month, parsed.day)
        end = datetime.now()
        date_range = (start, end)

        windows = self._quarter_windows(start, end)
        total_windows = len(windows)

        for i, (win_from, win_to) in enumerate(windows, 1):
            _status(
                f"  {option_type} window {i}/{total_windows}: {win_from} to {win_to}"
            )
            rows_fetched, _ = self._fetch_window_recursive(
                api_key,
                symbol,
                option_type,
                win_from,
                win_to,
                rows_fetched,
                on_progress,
                on_status,
                date_range,
            )

        # Final 100% update
        if on_progress:
            on_progress(symbol, option_type, rows_fetched, 100.0)

        return rows_fetched, None

    # -- local read + filter --

    def _fetch_options(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        option_type: str | None = None,
        expiration_type: str = "monthly",
    ) -> tuple[str, pd.DataFrame | None]:
        """Read locally stored options data, filter, and prepare for backtesting."""
        symbol = symbol.upper()

        df = self._cache.read("options", symbol)
        if df is None or df.empty:
            return (
                f"No local options data for {symbol}. "
                f"Use download_options_data to download it first."
            ), None

        _log.info("Loaded %s local options rows for %s", f"{len(df):,}", symbol)

        # Slice to requested date range
        start_dt = _parse_date(start_date)
        end_dt = _parse_date(end_date)
        if start_dt:
            df = df[df["quote_date"].dt.date >= start_dt]
        if end_dt:
            df = df[df["quote_date"].dt.date <= end_dt]

        if df.empty:
            return (
                f"No options data for {symbol} in the requested date range "
                f"({start_date or 'start'} to {end_date or 'end'}). "
                f"Check the date range against what was downloaded."
            ), None

        return self._apply_options_transforms(df, symbol, option_type, expiration_type)

    def _apply_options_transforms(
        self,
        df: pd.DataFrame,
        symbol: str,
        option_type: str | None,
        expiration_type: str | None,
    ) -> tuple[str, pd.DataFrame | None]:
        """Pipeline: filter → resolve prices → select columns → summarize."""
        df, err = self._filter_options(df, symbol, option_type, expiration_type)
        if err:
            return err, None

        df = self._resolve_underlying_prices(df, symbol)
        df = self._select_options_columns(df)
        df = df.dropna(subset=["underlying_price"])

        if df.empty:
            return (
                f"Fetched options for {symbol} from EODHD but could not "
                "resolve underlying stock prices (yfinance lookup failed). "
                "Try a different date range or check the ticker symbol.",
                None,
            )

        summary = (
            f"Loaded {len(df)} options records for {symbol}. "
            f"Date range: {df['quote_date'].min().date()} to {df['quote_date'].max().date()}, "
            f"expirations: {df['expiration'].nunique()}, "
            f"strikes: {df['strike'].nunique()}"
        )
        return summary, df

    @staticmethod
    def _filter_options(
        df: pd.DataFrame,
        symbol: str,
        option_type: str | None,
        expiration_type: str | None,
    ) -> tuple[pd.DataFrame, str | None]:
        """Filter by expiration type / option type and normalize option_type."""
        df = df.copy()
        if expiration_type and "expiration_type" in df.columns:
            before = len(df)
            df = df[df["expiration_type"].str.lower() == expiration_type.lower()]
            _log.info(
                "Filtered to %s expirations: %s → %s rows",
                expiration_type,
                f"{before:,}",
                f"{len(df):,}",
            )
            if df.empty:
                return df, (
                    f"No {expiration_type} options found for {symbol}. "
                    f"Try a different expiration_type (e.g. 'weekly')."
                )

        if option_type and "option_type" in df.columns:
            ot = option_type.lower()[:1]
            df = df[df["option_type"].str.lower().str[0] == ot]
            if df.empty:
                return df, f"No {option_type} options found for {symbol}."

        df["option_type"] = df["option_type"].str.lower().str[0]
        return df, None

    @staticmethod
    def _resolve_underlying_prices(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Merge underlying close prices from yfinance into the DataFrame."""
        try:
            import yfinance as yf
        except ImportError:
            _log.warning(
                "yfinance is not installed; cannot resolve underlying prices for %s",
                symbol,
            )
            df["underlying_price"] = pd.NA
            return df

        _log.info(
            "Resolving underlying prices via yfinance for %s (%s rows)",
            symbol,
            f"{len(df):,}",
        )
        date_min = df["quote_date"].min().date()
        date_max = df["quote_date"].max().date()
        try:
            stock_df = yf.download(
                symbol,
                start=str(date_min),
                end=str(date_max + timedelta(days=1)),
                progress=False,
            )
            if not stock_df.empty:
                close_col = stock_df["Close"]
                if isinstance(close_col, pd.DataFrame):
                    close_col = close_col.iloc[:, 0]
                price_map = close_col.reset_index()
                price_map.columns = ["quote_date", "underlying_price"]
                price_map["quote_date"] = pd.to_datetime(
                    price_map["quote_date"]
                ).dt.tz_localize(None)
                df = df.merge(price_map, on="quote_date", how="left")
            else:
                _log.warning("yfinance returned no data for %s", symbol)
                df["underlying_price"] = pd.NA
        except Exception as exc:
            _log.warning("yfinance price lookup failed for %s: %s", symbol, exc)
            df["underlying_price"] = pd.NA
        return df

    @staticmethod
    def _select_options_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Keep only the columns needed for optopsy backtesting."""
        keep = [
            "underlying_symbol",
            "underlying_price",
            "option_type",
            "expiration",
            "quote_date",
            "strike",
            "bid",
            "ask",
        ]
        optional = [
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho",
            "implied_volatility",
            "volume",
            "open_interest",
        ]
        keep.extend([c for c in optional if c in df.columns])
        return df[[c for c in keep if c in df.columns]]

    # -- tool schemas --

    def _download_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "download_options_data",
                "description": (
                    "Download ALL historical options data for a US stock "
                    "symbol from EODHD and store locally. This is a one-time "
                    "bulk download that fetches complete history (calls + puts, "
                    "weekly + monthly expirations). Must be run before "
                    "fetch_options_data can load data for the symbol."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "US stock ticker symbol (e.g. SPY, AAPL, TSLA)",
                        },
                    },
                    "required": ["symbol"],
                },
            },
        }

    def _options_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "fetch_options_data",
                "description": (
                    "Load locally stored options data for a US stock symbol "
                    "and prepare it for backtesting. Filters by date range, "
                    "option type, and expiration type. Requires "
                    "download_options_data to have been run first."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "US stock ticker symbol (e.g. AAPL, SPY, TSLA)",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD). Defaults to all available.",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD). Defaults to all available.",
                        },
                        "option_type": {
                            "type": "string",
                            "enum": ["call", "put"],
                            "description": "Filter by option type. Omit for both.",
                        },
                        "expiration_type": {
                            "type": "string",
                            "enum": ["monthly", "weekly"],
                            "description": "Filter by expiration cycle. Defaults to 'monthly'. Use 'weekly' for weekly expirations.",
                        },
                    },
                    "required": ["symbol"],
                },
            },
        }
