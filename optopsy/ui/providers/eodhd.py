import logging
import os
import re
import time
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from .base import DataProvider
from .cache import ParquetCache

_log = logging.getLogger(__name__)

_BASE_URL = "https://eodhd.com/api/mp/unicornbay"
_PAGE_LIMIT = 1000
_MAX_OFFSET = 10000  # EODHD rejects offsets beyond ~10K
_TIMEOUT = 60
_MAX_RETRIES = 2
_FIELDS = (
    "underlying_symbol,type,exp_date,tradetime,strike,bid,ask,"
    "last,volume,delta,gamma,theta,vega,open_interest,midpoint,expiration_type"
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
}

_OPTIONS_NUMERIC_COLS = [
    "strike",
    "bid",
    "ask",
    "volume",
    "last",
    "delta",
    "gamma",
    "theta",
    "vega",
    "open_interest",
    "midpoint",
]

_STOCK_NUMERIC_COLS = ["open", "high", "low", "close", "adjusted_close", "volume"]


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

    @property
    def name(self) -> str:
        return "EODHD"

    @property
    def env_key(self) -> str:
        return "EODHD_API_KEY"

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [self._options_schema(), self._stock_schema()]

    def get_tool_names(self) -> list[str]:
        return ["fetch_eodhd_options", "fetch_eodhd_stock_prices"]

    def replaces_dataset(self, tool_name: str) -> bool:
        # Stock price lookups are display-only; options data replaces the dataset.
        return tool_name != "fetch_eodhd_stock_prices"

    def execute(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[str, pd.DataFrame | None]:
        if tool_name == "fetch_eodhd_options":
            return self._fetch_options(
                symbol=arguments["symbol"],
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                option_type=arguments.get("option_type"),
                expiration_type=arguments.get("expiration_type", "monthly"),
            )
        if tool_name == "fetch_eodhd_stock_prices":
            return self._fetch_stock_prices(
                symbol=arguments["symbol"],
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
            )
        return f"Unknown tool: {tool_name}", None

    # -- private helpers --

    def _get_api_key(self) -> str | None:
        return os.environ.get(self.env_key)

    @staticmethod
    def _request_with_retry(url: str, params: dict) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return requests.get(url, params=params, timeout=_TIMEOUT)
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == _MAX_RETRIES:
                    raise
                time.sleep(2**attempt)
        # Unreachable, but keeps mypy happy
        raise last_exc  # type: ignore[misc]

    def _paginate_window(
        self, api_key: str, base_params: dict[str, Any]
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
            resp = self._request_with_retry(url, params)
            if resp.status_code == 401:
                return [], False, "EODHD API key is invalid or expired."
            if resp.status_code == 403:
                return (
                    [],
                    False,
                    "EODHD API access denied. Check your subscription plan.",
                )
            if resp.status_code == 429:
                return [], False, "EODHD rate limit exceeded. Try again later."
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

            offset += _PAGE_LIMIT
            next_url = data.get("links", {}).get("next")
            if not next_url or offset >= _MAX_OFFSET:
                hit_cap = bool(next_url)
                break

            url = next_url
            params = {"api_token": api_key, "compact": 1}

        return rows, hit_cap, None

    # -- gap detection --

    @staticmethod
    def _compute_date_gaps(
        cached_df: pd.DataFrame | None,
        start_dt: date | None,
        end_dt: date | None,
        date_column: str = "quote_date",
    ) -> list[tuple[str | None, str | None]]:
        """Compute date ranges missing from cache that need to be fetched.

        Uses a "bookend" strategy: checks if the requested range extends
        before or after the cached date range, and returns those extensions.
        """
        if cached_df is None or cached_df.empty or date_column not in cached_df.columns:
            return [
                (str(start_dt) if start_dt else None, str(end_dt) if end_dt else None)
            ]

        cached_dates = pd.to_datetime(cached_df[date_column]).dt.date
        cached_min = cached_dates.min()
        cached_max = cached_dates.max()

        gaps: list[tuple[str | None, str | None]] = []

        # Gap before cached range
        if start_dt and start_dt < cached_min:
            gaps.append((str(start_dt), str(cached_min - timedelta(days=1))))

        # Gap after cached range
        if end_dt and end_dt > cached_max:
            gaps.append((str(cached_max + timedelta(days=1)), str(end_dt)))
        elif end_dt is None:
            # No end date — fetch from day after cache max onward
            gaps.append((str(cached_max + timedelta(days=1)), None))

        return gaps

    # -- options: cache-aware orchestrator --

    def _fetch_options(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        option_type: str | None = None,
        expiration_type: str = "monthly",
    ) -> tuple[str, pd.DataFrame | None]:
        api_key = self._get_api_key()
        if not api_key:
            return "EODHD_API_KEY not configured. Add it to your .env file.", None

        symbol = symbol.upper()
        start_dt = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # Phase 1: Read cache and detect gaps
        cached_df = self._cache.read("options", symbol)
        if cached_df is not None and not cached_df.empty:
            _log.info(
                "Cache hit for %s options: %s rows", symbol, f"{len(cached_df):,}"
            )
        gaps = self._compute_date_gaps(cached_df, start_dt, end_dt)

        # Phase 2: Fetch missing data from API
        if gaps:
            _log.info(
                "Fetching %d gap(s) from EODHD for %s: %s",
                len(gaps),
                symbol,
                gaps,
            )
            result = self._fetch_options_from_api(api_key, symbol, gaps)
            if isinstance(result, str):
                # API error — use cache if available, otherwise surface error
                if cached_df is None or cached_df.empty:
                    return result, None
                _log.warning("API fetch failed, using cached data: %s", result)
            elif result is not None and not result.empty:
                cached_df = self._cache.merge_and_save("options", symbol, result)
        else:
            _log.info("Full cache hit for %s options, no API calls needed", symbol)

        if cached_df is None or cached_df.empty:
            return (
                f"No options data found for {symbol} with the given filters.",
                None,
            )

        # Phase 3: Slice to requested date range
        df = cached_df.copy()
        if start_dt:
            df = df[df["quote_date"].dt.date >= start_dt]
        if end_dt:
            df = df[df["quote_date"].dt.date <= end_dt]

        if df.empty:
            return (
                f"No options data found for {symbol} in the requested date range.",
                None,
            )

        # Phase 4: Apply client-side filters and transforms
        return self._apply_options_transforms(df, symbol, option_type, expiration_type)

    def _fetch_options_from_api(
        self,
        api_key: str,
        symbol: str,
        gaps: list[tuple[str | None, str | None]],
    ) -> pd.DataFrame | str | None:
        """Fetch options data from EODHD for the given date gaps.

        Returns a normalized DataFrame, an error string, or None.
        """
        all_rows: list[dict] = []

        for gap_start, gap_end in gaps:
            if gap_start is None and gap_end is None:
                continue

            base_params: dict[str, Any] = {
                "filter[underlying_symbol]": symbol,
                "fields[options-eod]": _FIELDS,
                "page[limit]": _PAGE_LIMIT,
                "sort": "exp_date",
                # No filter[type] — always fetch all option types for caching
            }
            if gap_start:
                base_params["filter[tradetime_from]"] = gap_start
            if gap_end:
                base_params["filter[tradetime_to]"] = gap_end

            _log.info(
                "EODHD API fetch: %s, dates=%s to %s",
                symbol,
                gap_start or "start",
                gap_end or "today",
            )

            # Adaptive windowed pagination
            window = 1
            while True:
                _log.info(
                    "Fetching %s options: window %d, from=%s — %s rows so far",
                    symbol,
                    window,
                    base_params.get("filter[tradetime_from]", "start"),
                    f"{len(all_rows):,}",
                )
                rows, hit_cap, error = self._paginate_window(api_key, base_params)
                if error:
                    return error
                all_rows.extend(rows)

                if not hit_cap or not rows:
                    break

                last_tradetime = max(r.get("tradetime", "") for r in rows)
                if not last_tradetime:
                    break
                next_start = datetime.strptime(
                    last_tradetime[:10], "%Y-%m-%d"
                ).date() + timedelta(days=1)
                if (
                    gap_end
                    and next_start > datetime.strptime(gap_end, "%Y-%m-%d").date()
                ):
                    break
                base_params["filter[tradetime_from]"] = str(next_start)
                window += 1

        if not all_rows:
            return None

        # Normalize for cache storage
        df = pd.DataFrame(all_rows)
        df = df.rename(columns=_COLUMN_MAP)
        df = df.drop_duplicates()
        df["expiration"] = pd.to_datetime(df["expiration"])
        df["quote_date"] = pd.to_datetime(df["quote_date"])
        for col in _OPTIONS_NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def _apply_options_transforms(
        self,
        df: pd.DataFrame,
        symbol: str,
        option_type: str | None,
        expiration_type: str | None,
    ) -> tuple[str, pd.DataFrame | None]:
        """Apply client-side filters and yfinance price merge."""
        # Filter by expiration type
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
                return (
                    f"No {expiration_type} options found for {symbol}. "
                    f"Try a different expiration_type (e.g. 'weekly').",
                    None,
                )

        # Filter by option type (client-side — cache stores both)
        if option_type and "option_type" in df.columns:
            ot = option_type.lower()[0]
            df = df[df["option_type"].str.lower().str[0] == ot]
            if df.empty:
                return f"No {option_type} options found for {symbol}.", None

        # Normalize option_type to single char
        df["option_type"] = df["option_type"].str.lower().str[0]

        # Resolve underlying prices via yfinance
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
        optional = ["delta", "gamma", "theta", "vega", "volume"]
        keep.extend([c for c in optional if c in df.columns])
        df = df[[c for c in keep if c in df.columns]]

        df = df.dropna(subset=["underlying_price"])

        if df.empty:
            return (
                f"Fetched options for {symbol} from EODHD but could not "
                "resolve underlying stock prices (yfinance lookup failed). "
                "Try a different date range or check the ticker symbol.",
                None,
            )

        summary = (
            f"Fetched {len(df)} options records for {symbol} from EODHD. "
            f"Date range: {df['quote_date'].min().date()} to {df['quote_date'].max().date()}, "
            f"expirations: {df['expiration'].nunique()}, "
            f"strikes: {df['strike'].nunique()}"
        )
        return summary, df

    # -- stock prices: cache-aware --

    def _fetch_stock_prices(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[str, pd.DataFrame | None]:
        api_key = self._get_api_key()
        if not api_key:
            return "EODHD_API_KEY not configured. Add it to your .env file.", None

        symbol = symbol.upper()
        start_dt = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # Phase 1: Read cache and detect gaps
        cached_df = self._cache.read("stocks", symbol)
        if cached_df is not None and not cached_df.empty:
            _log.info(
                "Cache hit for %s stock prices: %s rows", symbol, f"{len(cached_df):,}"
            )
        gaps = self._compute_date_gaps(cached_df, start_dt, end_dt, date_column="date")

        # Phase 2: Fetch missing data from API
        if gaps:
            _log.info(
                "Fetching %d gap(s) from EODHD for %s stock prices", len(gaps), symbol
            )
            result = self._fetch_stock_prices_from_api(api_key, symbol, gaps)
            if isinstance(result, str):
                if cached_df is None or cached_df.empty:
                    return result, None
                _log.warning("API failed, using cached stock data: %s", result)
            elif result is not None and not result.empty:
                cached_df = self._cache.merge_and_save("stocks", symbol, result)
        else:
            _log.info("Full cache hit for %s stock prices, no API calls needed", symbol)

        if cached_df is None or cached_df.empty:
            return f"No stock price data found for {symbol}.", None

        # Phase 3: Slice to requested range
        df = cached_df.copy()
        if start_dt:
            df = df[df["date"].dt.date >= start_dt]
        if end_dt:
            df = df[df["date"].dt.date <= end_dt]

        if df.empty:
            return f"No stock price data for {symbol} in the requested range.", None

        df = df.drop(columns=["warning"], errors="ignore")

        summary = (
            f"Fetched {len(df)} daily price records for {symbol} from EODHD. "
            f"Date range: {df['date'].min().date()} to {df['date'].max().date()}"
        )
        return summary, df

    def _fetch_stock_prices_from_api(
        self,
        api_key: str,
        symbol: str,
        gaps: list[tuple[str | None, str | None]],
    ) -> pd.DataFrame | str | None:
        """Fetch stock price data from EODHD for the given date gaps."""
        all_data: list[dict] = []

        for gap_start, gap_end in gaps:
            if gap_start is None and gap_end is None:
                continue

            params: dict[str, Any] = {
                "api_token": api_key,
                "fmt": "json",
            }
            if gap_start:
                params["from"] = gap_start
            if gap_end:
                params["to"] = gap_end

            url = f"https://eodhd.com/api/eod/{symbol}.US"
            resp = self._request_with_retry(url, params)

            if resp.status_code == 401:
                return "EODHD API key is invalid or expired."
            if resp.status_code == 403:
                return "EODHD API access denied. Check your subscription plan."
            if resp.status_code == 429:
                return "EODHD rate limit exceeded. Try again later."
            _safe_raise_for_status(resp)

            data = resp.json()
            if data:
                all_data.extend(data)

        if not all_data:
            return None

        df = pd.DataFrame(all_data)
        df["date"] = pd.to_datetime(df["date"])
        for col in _STOCK_NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.drop_duplicates()

        return df

    # -- tool schemas --

    def _options_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "fetch_eodhd_options",
                "description": (
                    "Fetch historical end-of-day options chain data from EODHD "
                    "for a US stock symbol. Returns data ready for optopsy "
                    "strategy backtesting."
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
                            "description": "End date (YYYY-MM-DD). Defaults to today.",
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

    def _stock_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "fetch_eodhd_stock_prices",
                "description": (
                    "Fetch historical end-of-day stock price data (OHLCV) from "
                    "EODHD for a US stock symbol."
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
                            "description": "End date (YYYY-MM-DD). Defaults to today.",
                        },
                    },
                    "required": ["symbol"],
                },
            },
        }
