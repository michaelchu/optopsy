import os
from typing import Any

import pandas as pd
import requests

EODHD_BASE_URL = "https://eodhd.com/api/mp/unicornbay"
EODHD_PAGE_LIMIT = 1000
EODHD_FIELDS = (
    "underlying_symbol,type,exp_date,tradetime,strike,bid,ask,"
    "last,volume,delta,gamma,theta,vega,open_interest"
)

# Maps EODHD response fields to optopsy's expected column names
EODHD_COLUMN_MAP = {
    "underlying_symbol": "underlying_symbol",
    "type": "option_type",
    "exp_date": "expiration",
    "tradetime": "quote_date",
    "strike": "strike",
    "bid": "bid",
    "ask": "ask",
    "last": "underlying_price",
    "volume": "volume",
    "delta": "delta",
    "gamma": "gamma",
    "theta": "theta",
    "vega": "vega",
}


def _get_eodhd_key() -> str | None:
    return os.environ.get("EODHD_API_TOKEN")


def eodhd_available() -> bool:
    return _get_eodhd_key() is not None


def fetch_eodhd_options(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    option_type: str | None = None,
) -> tuple[str, pd.DataFrame | None]:
    """Fetch historical EOD options data from EODHD marketplace API."""
    api_key = _get_eodhd_key()
    if not api_key:
        return "EODHD_API_TOKEN not configured. Add it to your .env file.", None

    params: dict[str, Any] = {
        "api_token": api_key,
        "filter[underlying_symbol]": symbol.upper(),
        "fields[options-eod]": EODHD_FIELDS,
        "page[limit]": EODHD_PAGE_LIMIT,
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
    url = f"{EODHD_BASE_URL}/options/eod"

    while True:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 401:
            return "EODHD API key is invalid or expired.", None
        if resp.status_code == 403:
            return "EODHD API access denied. Check your subscription plan.", None
        if resp.status_code == 429:
            return "EODHD rate limit exceeded. Try again later.", None
        resp.raise_for_status()

        data = resp.json()
        rows = data.get("data", [])
        if not rows:
            break
        all_rows.extend(rows)

        next_url = data.get("links", {}).get("next")
        if not next_url:
            break
        # Next URL is absolute, switch to it
        url = next_url
        params = {}  # params are embedded in the next URL

    if not all_rows:
        return (
            f"No options data found for {symbol.upper()} with the given filters.",
            None,
        )

    df = pd.DataFrame(all_rows)
    df = df.rename(columns=EODHD_COLUMN_MAP)

    # Normalize option_type to c/p
    df["option_type"] = df["option_type"].str.lower().str[0]

    # Parse dates
    df["expiration"] = pd.to_datetime(df["expiration"])
    df["quote_date"] = pd.to_datetime(df["quote_date"])

    # Ensure numeric columns
    numeric_cols = ["strike", "bid", "ask", "underlying_price", "volume"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    greek_cols = ["delta", "gamma", "theta", "vega"]
    for col in greek_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep only optopsy-compatible columns
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

    summary = (
        f"Fetched {len(df)} options records for {symbol.upper()} from EODHD. "
        f"Date range: {df['quote_date'].min().date()} to {df['quote_date'].max().date()}, "
        f"expirations: {df['expiration'].nunique()}, "
        f"strikes: {df['strike'].nunique()}"
    )
    return summary, df


def get_eodhd_tool_schema() -> dict:
    """Return the tool schema for fetching EODHD options data."""
    return {
        "type": "function",
        "function": {
            "name": "fetch_eodhd_options",
            "description": (
                "Fetch historical end-of-day options chain data from EODHD for a US stock symbol. "
                "Returns data ready for optopsy strategy backtesting. "
                "Covers 6000+ US tickers with ~2 years of history."
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
                        "description": "Start date for data range (YYYY-MM-DD). Defaults to all available.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for data range (YYYY-MM-DD). Defaults to today.",
                    },
                    "option_type": {
                        "type": "string",
                        "enum": ["call", "put"],
                        "description": "Filter by option type. Omit for both calls and puts.",
                    },
                },
                "required": ["symbol"],
            },
        },
    }
