import json
import os
from typing import Any

import pandas as pd

import optopsy as op

from .providers import eodhd_available, fetch_eodhd_options, get_eodhd_tool_schema

DATA_DIR = os.path.join(os.getcwd(), "optopsy_data")

STRATEGY_PARAMS_SCHEMA = {
    "max_entry_dte": {
        "type": "integer",
        "description": "Maximum days to expiration for entry (default: 90)",
    },
    "exit_dte": {
        "type": "integer",
        "description": "Days to expiration for exit (default: 0)",
    },
    "dte_interval": {
        "type": "integer",
        "description": "Interval size for DTE grouping in stats (default: 7)",
    },
    "max_otm_pct": {
        "type": "number",
        "description": "Maximum out-of-the-money percentage (default: 0.5)",
    },
    "otm_pct_interval": {
        "type": "number",
        "description": "Interval size for OTM grouping in stats (default: 0.05)",
    },
    "min_bid_ask": {
        "type": "number",
        "description": "Minimum bid/ask price threshold (default: 0.05)",
    },
    "raw": {
        "type": "boolean",
        "description": "If true, return raw trades instead of aggregated stats (default: false)",
    },
    "drop_nan": {
        "type": "boolean",
        "description": "If true, remove NaN rows from output (default: true)",
    },
    "slippage": {
        "type": "string",
        "enum": ["mid", "spread", "liquidity"],
        "description": "Slippage model: 'mid' (midpoint), 'spread' (full spread), or 'liquidity' (volume-based). Default: 'mid'",
    },
}

CALENDAR_EXTRA_PARAMS = {
    "front_dte_min": {
        "type": "integer",
        "description": "Minimum DTE for front (near-term) leg (default: 20)",
    },
    "front_dte_max": {
        "type": "integer",
        "description": "Maximum DTE for front (near-term) leg (default: 40)",
    },
    "back_dte_min": {
        "type": "integer",
        "description": "Minimum DTE for back (longer-term) leg (default: 50)",
    },
    "back_dte_max": {
        "type": "integer",
        "description": "Maximum DTE for back (longer-term) leg (default: 90)",
    },
}

# Maps strategy name -> (function, description, is_calendar)
STRATEGIES = {
    "long_calls": (op.long_calls, "Buy calls — bullish directional bet", False),
    "long_puts": (op.long_puts, "Buy puts — bearish directional bet", False),
    "short_calls": (op.short_calls, "Sell calls — bearish/neutral income", False),
    "short_puts": (op.short_puts, "Sell puts — bullish/neutral income", False),
    "long_straddles": (
        op.long_straddles,
        "Buy call + put at same strike — bet on large move in either direction",
        False,
    ),
    "short_straddles": (
        op.short_straddles,
        "Sell call + put at same strike — bet on low volatility",
        False,
    ),
    "long_strangles": (
        op.long_strangles,
        "Buy call + put at different strikes — cheaper volatility bet",
        False,
    ),
    "short_strangles": (
        op.short_strangles,
        "Sell call + put at different strikes — wider neutral income",
        False,
    ),
    "long_call_spread": (
        op.long_call_spread,
        "Bull call spread — capped-risk bullish trade",
        False,
    ),
    "short_call_spread": (
        op.short_call_spread,
        "Bear call spread — bearish credit spread",
        False,
    ),
    "long_put_spread": (
        op.long_put_spread,
        "Bear put spread — capped-risk bearish trade",
        False,
    ),
    "short_put_spread": (
        op.short_put_spread,
        "Bull put spread — bullish credit spread",
        False,
    ),
    "long_call_butterfly": (
        op.long_call_butterfly,
        "Long call butterfly — neutral, profits near middle strike",
        False,
    ),
    "short_call_butterfly": (
        op.short_call_butterfly,
        "Short call butterfly — profits from large move",
        False,
    ),
    "long_put_butterfly": (
        op.long_put_butterfly,
        "Long put butterfly — neutral, profits near middle strike",
        False,
    ),
    "short_put_butterfly": (
        op.short_put_butterfly,
        "Short put butterfly — profits from large move",
        False,
    ),
    "iron_condor": (
        op.iron_condor,
        "Iron condor — neutral income, profits when underlying stays in range",
        False,
    ),
    "reverse_iron_condor": (
        op.reverse_iron_condor,
        "Reverse iron condor — profits from large move in either direction",
        False,
    ),
    "iron_butterfly": (
        op.iron_butterfly,
        "Iron butterfly — neutral income, narrower range than iron condor",
        False,
    ),
    "reverse_iron_butterfly": (
        op.reverse_iron_butterfly,
        "Reverse iron butterfly — profits from large move",
        False,
    ),
    "covered_call": (
        op.covered_call,
        "Covered call — long stock + short call for income",
        False,
    ),
    "protective_put": (
        op.protective_put,
        "Protective put — long stock + long put for downside protection",
        False,
    ),
    "long_call_calendar": (
        op.long_call_calendar,
        "Long call calendar — short front-month, long back-month call at same strike",
        True,
    ),
    "short_call_calendar": (
        op.short_call_calendar,
        "Short call calendar — long front-month, short back-month call at same strike",
        True,
    ),
    "long_put_calendar": (
        op.long_put_calendar,
        "Long put calendar — short front-month, long back-month put at same strike",
        True,
    ),
    "short_put_calendar": (
        op.short_put_calendar,
        "Short put calendar — long front-month, short back-month put at same strike",
        True,
    ),
    "long_call_diagonal": (
        op.long_call_diagonal,
        "Long call diagonal — short front-month, long back-month call at different strikes",
        True,
    ),
    "short_call_diagonal": (
        op.short_call_diagonal,
        "Short call diagonal — long front-month, short back-month call at different strikes",
        True,
    ),
    "long_put_diagonal": (
        op.long_put_diagonal,
        "Long put diagonal — short front-month, long back-month put at different strikes",
        True,
    ),
    "short_put_diagonal": (
        op.short_put_diagonal,
        "Short put diagonal — long front-month, short back-month put at different strikes",
        True,
    ),
}


def _build_strategy_tool(name: str, description: str, is_calendar: bool) -> dict:
    params = dict(STRATEGY_PARAMS_SCHEMA)
    if is_calendar:
        params.update(CALENDAR_EXTRA_PARAMS)

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": [],
            },
        },
    }


def get_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool schemas for all optopsy functions."""
    tools = []

    # csv_data tool for loading data
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "load_csv_data",
                "description": (
                    "Load option chain data from a CSV file in the data directory. "
                    "The file must contain columns for: underlying_symbol, "
                    "underlying_price, option_type (c/p), expiration, quote_date, "
                    "strike, bid, ask. Optional: delta, gamma, theta, vega, volume."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the CSV file to load from the data directory",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Optional start date filter (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Optional end date filter (YYYY-MM-DD)",
                        },
                    },
                    "required": ["filename"],
                },
            },
        }
    )

    # list_data_files tool
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "list_data_files",
                "description": "List all CSV files in the data directory that are available for loading.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    )

    # preview_data tool
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "preview_data",
                "description": "Show a preview of the currently loaded dataset — column names, shape, date range, and sample rows.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    )

    # Data provider tools (only added when API keys are configured)
    if eodhd_available():
        tools.append(get_eodhd_tool_schema())

    # Strategy tools
    for name, (_, description, is_calendar) in STRATEGIES.items():
        tools.append(_build_strategy_tool(name, description, is_calendar))

    return tools


MAX_ROWS = 50


def _df_to_markdown(df: pd.DataFrame, max_rows: int = MAX_ROWS) -> str:
    """Convert a DataFrame to a markdown table, truncating if too large."""
    total = len(df)
    truncated = total > max_rows
    if truncated:
        df = df.head(max_rows)
    table = df.to_markdown(index=False, floatfmt=".4f")
    if truncated:
        table += f"\n\n*... showing {max_rows} of {total} rows*"
    return table


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def execute_tool(
    tool_name: str, arguments: dict[str, Any], dataset: pd.DataFrame | None
) -> tuple[str, pd.DataFrame | None]:
    """
    Execute a tool call and return (result_text, updated_dataset).

    The dataset is the currently loaded DataFrame (or None if nothing loaded yet).
    """
    if tool_name == "load_csv_data":
        filename = arguments["filename"]
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            available = os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else []
            return (
                f"File '{filename}' not found. Available files: {available}",
                dataset,
            )
        kwargs: dict[str, Any] = {}
        if arguments.get("start_date"):
            kwargs["start_date"] = arguments["start_date"]
        if arguments.get("end_date"):
            kwargs["end_date"] = arguments["end_date"]
        try:
            df = op.csv_data(filepath, **kwargs)
            summary = (
                f"Loaded '{filename}': {len(df)} rows, "
                f"columns: {list(df.columns)}, "
                f"date range: {df['quote_date'].min()} to {df['quote_date'].max()}, "
                f"symbols: {df['underlying_symbol'].unique().tolist()}"
            )
            return summary, df
        except Exception as e:
            return f"Error loading '{filename}': {e}", dataset

    if tool_name == "list_data_files":
        ensure_data_dir()
        files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
        if not files:
            return "No CSV files found in the data directory.", dataset
        return f"Available files: {files}", dataset

    if tool_name == "fetch_eodhd_options":
        try:
            summary, df = fetch_eodhd_options(
                symbol=arguments["symbol"],
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                option_type=arguments.get("option_type"),
            )
            if df is not None:
                return summary, df
            return summary, dataset
        except Exception as e:
            return f"Error fetching EODHD data: {e}", dataset

    if tool_name == "preview_data":
        if dataset is None:
            return "No dataset loaded. Use load_csv_data first.", dataset
        info = (
            f"Shape: {dataset.shape}\n"
            f"Columns: {list(dataset.columns)}\n"
            f"Date range: {dataset['quote_date'].min()} to {dataset['quote_date'].max()}\n"
            f"Symbols: {dataset['underlying_symbol'].unique().tolist()}\n\n"
            f"First 5 rows:\n{_df_to_markdown(dataset.head())}"
        )
        return info, dataset

    # Strategy execution
    if tool_name in STRATEGIES:
        if dataset is None:
            return (
                "No dataset loaded. Please load a CSV file first with load_csv_data.",
                dataset,
            )
        func, _, _ = STRATEGIES[tool_name]
        try:
            result = func(dataset, **arguments)
            if result.empty:
                return (
                    f"{tool_name} returned no results with the given parameters. "
                    "Try relaxing the filters (e.g. increase max_entry_dte or max_otm_pct).",
                    dataset,
                )
            is_raw = arguments.get("raw", False)
            mode = "raw trades" if is_raw else "aggregated stats"
            summary = (
                f"**{tool_name}** — {len(result)} {mode}\n\n"
                f"{_df_to_markdown(result)}"
            )
            return summary, dataset
        except Exception as e:
            return f"Error running {tool_name}: {e}", dataset

    return f"Unknown tool: {tool_name}", dataset
