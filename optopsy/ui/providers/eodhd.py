import logging
import os
import re
import time
from datetime import timedelta
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

        params: dict[str, Any] = {
            "api_token": api_key,
            "filter[underlying_symbol]": symbol.upper(),
            "fields[options-eod]": _FIELDS,
            "page[limit]": _PAGE_LIMIT,
            "page[offset]": 0,
            "sort": "exp_date",
        }

        if option_type:
            params["filter[type]"] = option_type.lower()
        if start_date:
            params["filter[tradetime_from]"] = start_date
        if end_date:
            params["filter[tradetime_to]"] = end_date

        all_rows: list[dict] = []
        url = f"{_BASE_URL}/options/eod"

        offset = 0
        while True:
            resp = self._request_with_retry(url, params)
            if resp.status_code == 401:
                return "EODHD API key is invalid or expired.", None
            if resp.status_code == 403:
                return "EODHD API access denied. Check your subscription plan.", None
            if resp.status_code == 429:
                return "EODHD rate limit exceeded. Try again later.", None
            if resp.status_code == 422:
                # API rejects large offsets — return what we collected so far
                break
            _safe_raise_for_status(resp)

            data = resp.json()
            rows = data.get("data", [])
            if not rows:
                break

            for row in rows:
                attrs = row.get("attributes", row)
                all_rows.append(attrs)

            offset += _PAGE_LIMIT
            next_url = data.get("links", {}).get("next")
            if not next_url or offset >= _MAX_OFFSET:
                break

            url = next_url
            params = {"api_token": api_key}

        if not all_rows:
            return (
                f"No options data found for {symbol.upper()} with the given filters.",
                None,
            )

        df = pd.DataFrame(all_rows)
        df = df.rename(columns=_COLUMN_MAP)

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
