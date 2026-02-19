import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from .base import DataProvider

_log = logging.getLogger(__name__)

_BASE_URL = "https://eodhd.com/api/mp/unicornbay"
_PAGE_LIMIT = 1000
_MAX_OFFSET = 10000  # EODHD rejects offsets beyond ~10K
_TIMEOUT = 60
_MAX_RETRIES = 2
_FIELDS = (
    "underlying_symbol,type,exp_date,tradetime,strike,bid,ask,"
    "last,volume,delta,gamma,theta,vega,open_interest,midpoint"
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


def _safe_raise_for_status(resp: requests.Response) -> None:
    """Like resp.raise_for_status() but strips api_token from the error URL."""
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        sanitized = re.sub(r"api_token=[^&\s]+", "api_token=***", str(exc))
        raise requests.HTTPError(sanitized, response=resp) from None


class EODHDProvider(DataProvider):

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
        """Paginate through a single date window.

        Returns ``(rows, hit_cap, error_or_none)``.  ``hit_cap`` is True when
        the offset limit was reached, signalling that more data likely exists
        beyond this window.
        """
        rows: list[dict] = []
        url = f"{_BASE_URL}/options/eod"
        params = {**base_params, "api_token": api_key, "page[offset]": 0}
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
            page_rows = data.get("data", [])
            if not page_rows:
                break

            for row in page_rows:
                attrs = row.get("attributes", row)
                rows.append(attrs)

            offset += _PAGE_LIMIT
            next_url = data.get("links", {}).get("next")
            if not next_url or offset >= _MAX_OFFSET:
                hit_cap = bool(next_url)
                break

            url = next_url
            params = {"api_token": api_key}

        return rows, hit_cap, None

    def _fetch_options(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        option_type: str | None = None,
    ) -> tuple[str, pd.DataFrame | None]:
        api_key = self._get_api_key()
        if not api_key:
            return "EODHD_API_KEY not configured. Add it to your .env file.", None

        base_params: dict[str, Any] = {
            "filter[underlying_symbol]": symbol.upper(),
            "fields[options-eod]": _FIELDS,
            "page[limit]": _PAGE_LIMIT,
            "sort": "exp_date",
        }

        if option_type:
            base_params["filter[type]"] = option_type.lower()

        all_rows: list[dict] = []

        if start_date:
            base_params["filter[tradetime_from]"] = start_date
        if end_date:
            base_params["filter[tradetime_to]"] = end_date

        # Adaptive pagination: fetch up to the offset cap, then advance the
        # start cursor past the last returned tradetime and fetch again.
        # This maximises rows per request and minimises total API calls.
        window = 1
        while True:
            _log.info(
                "Fetching %s options: window %d, from=%s — %s rows so far",
                symbol.upper(),
                window,
                base_params.get("filter[tradetime_from]", "start"),
                f"{len(all_rows):,}",
            )
            rows, hit_cap, error = self._paginate_window(api_key, base_params)
            if error:
                return error, None
            all_rows.extend(rows)

            if not hit_cap or not rows:
                break

            # Find the last tradetime in this batch and advance the cursor
            # past it so the next window picks up where we left off.
            last_tradetime = max(r.get("tradetime", "") for r in rows)
            if not last_tradetime:
                break
            # Move start to the day after the last tradetime we received.
            next_start = datetime.strptime(
                last_tradetime[:10], "%Y-%m-%d"
            ).date() + timedelta(days=1)
            if end_date and next_start > datetime.strptime(end_date, "%Y-%m-%d").date():
                break
            base_params["filter[tradetime_from]"] = str(next_start)
            window += 1

        if not all_rows:
            return (
                f"No options data found for {symbol.upper()} with the given filters.",
                None,
            )

        df = pd.DataFrame(all_rows)
        df = df.rename(columns=_COLUMN_MAP)
        df = df.drop_duplicates()

        df["option_type"] = df["option_type"].str.lower().str[0]

        df["expiration"] = pd.to_datetime(df["expiration"])
        df["quote_date"] = pd.to_datetime(df["quote_date"])

        numeric_cols = ["strike", "bid", "ask", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        greek_cols = ["delta", "gamma", "theta", "vega"]
        for col in greek_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # EODHD doesn't provide underlying_price directly. Use yfinance to
        # fetch stock closing prices for the same date range and merge them in.
        _log.info(
            "Fetched %s rows from EODHD for %s. Resolving underlying prices via yfinance",
            f"{len(df):,}",
            symbol.upper(),
        )
        date_min = df["quote_date"].min().date()
        date_max = df["quote_date"].max().date()
        try:
            stock_df = yf.download(
                symbol.upper(),
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
                _log.warning("yfinance returned no data for %s", symbol.upper())
                df["underlying_price"] = pd.NA
        except Exception as exc:
            _log.warning("yfinance price lookup failed for %s: %s", symbol.upper(), exc)
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
                f"Fetched options for {symbol.upper()} from EODHD but could not "
                "resolve underlying stock prices (yfinance lookup failed). "
                "Try a different date range or check the ticker symbol.",
                None,
            )

        summary = (
            f"Fetched {len(df)} options records for {symbol.upper()} from EODHD. "
            f"Date range: {df['quote_date'].min().date()} to {df['quote_date'].max().date()}, "
            f"expirations: {df['expiration'].nunique()}, "
            f"strikes: {df['strike'].nunique()}"
        )
        return summary, df

    def _fetch_stock_prices(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[str, pd.DataFrame | None]:
        api_key = self._get_api_key()
        if not api_key:
            return "EODHD_API_KEY not configured. Add it to your .env file.", None

        params: dict[str, Any] = {
            "api_token": api_key,
            "fmt": "json",
        }
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date

        url = f"https://eodhd.com/api/eod/{symbol.upper()}.US"
        resp = self._request_with_retry(url, params)

        if resp.status_code == 401:
            return "EODHD API key is invalid or expired.", None
        if resp.status_code == 403:
            return "EODHD API access denied. Check your subscription plan.", None
        if resp.status_code == 429:
            return "EODHD rate limit exceeded. Try again later.", None
        _safe_raise_for_status(resp)

        data = resp.json()
        if not data:
            return f"No stock price data found for {symbol.upper()}.", None

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        numeric_cols = ["open", "high", "low", "close", "adjusted_close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.drop(columns=["warning"], errors="ignore")

        summary = (
            f"Fetched {len(df)} daily price records for {symbol.upper()} from EODHD. "
            f"Date range: {df['date'].min().date()} to {df['date'].max().date()}"
        )
        return summary, df

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
