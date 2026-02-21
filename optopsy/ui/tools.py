import logging
import os
from datetime import date, timedelta
from typing import Any

import pandas as pd

import optopsy as op
import optopsy.signals as _signals
from optopsy.signals import apply_signal

from .providers import get_all_provider_tool_schemas, get_provider_for_tool
from .providers.cache import ParquetCache, compute_date_gaps

_log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.expanduser("~"), ".optopsy", "data")

# Cache for yfinance OHLCV data (category="yf_stocks", one file per symbol).
# Deliberately distinct from EODHD's "stocks" category to avoid schema collisions.
_yf_cache = ParquetCache()
_YF_CACHE_CATEGORY = "yf_stocks"
_YF_DEDUP_COLS = ["date"]

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


CALENDAR_STRATEGIES = {name for name, (_, _, is_cal) in STRATEGIES.items() if is_cal}

STRATEGY_NAMES = sorted(STRATEGIES.keys())

# ---------------------------------------------------------------------------
# Signal registry
# ---------------------------------------------------------------------------
# Maps a flat string identifier -> factory lambda that returns a SignalFunc.
# Defaults are baked in so the LLM only needs to pick a name.
# Factories are called at execution time to avoid shared state between runs.


def _normalize_days_param(days):
    """
    Convert days parameter to list format.

    Args:
        days (int or list[int]): Day index or list of day indices (0=Monday, 6=Sunday).

    Returns:
        list[int]: Days parameter as a list.

    Raises:
        TypeError: If days is neither an int nor a list, or if list contains non-integers.
        ValueError: If days is an empty list or contains out-of-range values (not 0-6).
    """
    if isinstance(days, list):
        if not days:
            raise ValueError("days parameter cannot be an empty list")
        if not all(isinstance(day, int) for day in days):
            raise TypeError("all elements in days list must be integers")
        invalid_days = [d for d in days if d < 0 or d > 6]
        if invalid_days:
            raise ValueError(
                f"day values must be 0-6 (Monday-Sunday), got invalid values: {invalid_days}"
            )
        return days
    elif isinstance(days, int):
        if days < 0 or days > 6:
            raise ValueError(f"day value must be 0-6 (Monday-Sunday), got {days}")
        return [days]
    else:
        raise TypeError(
            f"days parameter must be an int or list[int], got {type(days).__name__}"
        )


SIGNAL_REGISTRY: dict[str, Any] = {
    # RSI — defaults: period=14, threshold=30 (below) / 70 (above)
    "rsi_below": lambda **kw: _signals.rsi_below(
        kw.get("period", 14), kw.get("threshold", 30)
    ),
    "rsi_above": lambda **kw: _signals.rsi_above(
        kw.get("period", 14), kw.get("threshold", 70)
    ),
    # SMA — default: period=50
    "sma_below": lambda **kw: _signals.sma_below(kw.get("period", 50)),
    "sma_above": lambda **kw: _signals.sma_above(kw.get("period", 50)),
    # MACD — defaults: fast=12, slow=26, signal_period=9
    "macd_cross_above": lambda **kw: _signals.macd_cross_above(
        kw.get("fast", 12), kw.get("slow", 26), kw.get("signal_period", 9)
    ),
    "macd_cross_below": lambda **kw: _signals.macd_cross_below(
        kw.get("fast", 12), kw.get("slow", 26), kw.get("signal_period", 9)
    ),
    # Bollinger Bands — defaults: length=20, std=2.0
    "bb_above_upper": lambda **kw: _signals.bb_above_upper(
        kw.get("length", 20), kw.get("std", 2.0)
    ),
    "bb_below_lower": lambda **kw: _signals.bb_below_lower(
        kw.get("length", 20), kw.get("std", 2.0)
    ),
    # EMA crossover — defaults: fast=10, slow=50
    "ema_cross_above": lambda **kw: _signals.ema_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "ema_cross_below": lambda **kw: _signals.ema_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # ATR volatility regime — defaults: period=14, multiplier=1.5 (above) / 0.75 (below)
    "atr_above": lambda **kw: _signals.atr_above(
        kw.get("period", 14), kw.get("multiplier", 1.5)
    ),
    "atr_below": lambda **kw: _signals.atr_below(
        kw.get("period", 14), kw.get("multiplier", 0.75)
    ),
    # Day-of-week — default: days=[4] (Friday); pass days=[0,1,2,3,4] for any weekday
    "day_of_week": lambda **kw: _signals.day_of_week(
        *_normalize_days_param(kw.get("days", [4]))
    ),
}

SIGNAL_NAMES = sorted(SIGNAL_REGISTRY.keys())

# Signals that only need quote_date (no OHLCV data / yfinance fetch).
_DATE_ONLY_SIGNALS = frozenset({"day_of_week"})

# Maps strategy name -> required option_type for data fetching.
# "call"/"put" means only that type is needed; None means both are needed.
STRATEGY_OPTION_TYPE: dict[str, str | None] = {
    "long_calls": "call",
    "short_calls": "call",
    "long_call_spread": "call",
    "short_call_spread": "call",
    "long_call_butterfly": "call",
    "short_call_butterfly": "call",
    "long_call_calendar": "call",
    "short_call_calendar": "call",
    "long_call_diagonal": "call",
    "short_call_diagonal": "call",
    "covered_call": "call",
    "long_puts": "put",
    "short_puts": "put",
    "long_put_spread": "put",
    "short_put_spread": "put",
    "long_put_butterfly": "put",
    "short_put_butterfly": "put",
    "long_put_calendar": "put",
    "short_put_calendar": "put",
    "long_put_diagonal": "put",
    "short_put_diagonal": "put",
    "long_straddles": None,
    "short_straddles": None,
    "long_strangles": None,
    "short_strangles": None,
    "iron_condor": None,
    "reverse_iron_condor": None,
    "iron_butterfly": None,
    "reverse_iron_butterfly": None,
    "protective_put": None,
}


def get_required_option_type(strategy_name: str) -> str | None:
    """Return 'call', 'put', or None (both) for a given strategy name."""
    return STRATEGY_OPTION_TYPE.get(strategy_name)


def get_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool schemas for all optopsy functions."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "load_csv_data",
                "description": (
                    "Load option chain data from a CSV file in the data directory."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "CSV filename to load",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date filter (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date filter (YYYY-MM-DD)",
                        },
                    },
                    "required": ["filename"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_data_files",
                "description": "List available CSV files in the data directory.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "preview_data",
                "description": (
                    "Show shape, columns, date range, and sample rows of a dataset. "
                    "Omit dataset_name to inspect the most-recently-loaded dataset."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dataset_name": {
                            "type": "string",
                            "description": (
                                "Name (ticker or filename) of the dataset to preview. "
                                "Omit to use the most-recently-loaded dataset."
                            ),
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "suggest_strategy_params",
                "description": (
                    "Analyze a loaded dataset and suggest good starting parameters "
                    "(max_entry_dte, exit_dte, max_otm_pct) based on the actual DTE "
                    "and OTM% distributions. Call this before running a strategy when "
                    "the user has not specified explicit parameters, to avoid guessing "
                    "values the data can't satisfy. Returns percentile tables and a "
                    "JSON block of recommended parameter values ready to pass to "
                    "run_strategy or scan_strategies."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dataset_name": {
                            "type": "string",
                            "description": (
                                "Dataset to analyze. "
                                "Omit to use the most-recently-loaded dataset."
                            ),
                        },
                        "strategy_name": {
                            "type": "string",
                            "enum": STRATEGY_NAMES,
                            "description": (
                                "Optional: tailor suggestions for a specific strategy. "
                                "Iron condors and multi-leg strategies get tighter DTE/OTM% "
                                "defaults. Calendar strategies receive front/back DTE "
                                "recommendations instead of max_entry_dte."
                            ),
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_strategy",
                "description": (
                    "Run an options strategy backtest on the loaded dataset. "
                    "Strategies: " + ", ".join(STRATEGY_NAMES) + ". "
                    "Calendar/diagonal strategies also accept front_dte_min, "
                    "front_dte_max, back_dte_min, back_dte_max."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "strategy_name": {
                            "type": "string",
                            "enum": STRATEGY_NAMES,
                            "description": "Name of the strategy to run",
                        },
                        "entry_signal": {
                            "type": "string",
                            "enum": SIGNAL_NAMES,
                            "description": (
                                "Optional TA signal that gates entry. Only enters trades on "
                                "dates where the signal is True for the underlying symbol. "
                                "Momentum: macd_cross_above, macd_cross_below, ema_cross_above, ema_cross_below. "
                                "Mean-reversion: rsi_below (default RSI<30), rsi_above (default RSI>70), "
                                "bb_below_lower, bb_above_upper. "
                                "Trend filter: sma_above (default SMA50), sma_below (default SMA50). "
                                "Volatility: atr_above (default ATR > 1.5× median), atr_below (default ATR < 0.75× median). "
                                "Calendar: day_of_week (default Friday). "
                                "Use entry_signal_params to override defaults."
                            ),
                        },
                        "entry_signal_params": {
                            "type": "object",
                            "description": (
                                "Optional parameters for entry_signal. Keys by signal type: "
                                "rsi_below/rsi_above → {period: int, threshold: float}; "
                                "sma_below/sma_above → {period: int}; "
                                "macd_cross_above/macd_cross_below → {fast: int, slow: int, signal_period: int}; "
                                "bb_above_upper/bb_below_lower → {length: int, std: float}; "
                                "ema_cross_above/ema_cross_below → {fast: int, slow: int}; "
                                "atr_above/atr_below → {period: int, multiplier: float}; "
                                "day_of_week → {days: list[int]} where 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri."
                            ),
                        },
                        "entry_signal_days": {
                            "type": "integer",
                            "minimum": 1,
                            "description": (
                                "Optional: require the entry_signal to be True for this many consecutive "
                                "trading days before entering. Works with any signal. "
                                "Omit or set to 1 for single-bar behavior (default)."
                            ),
                        },
                        "exit_signal": {
                            "type": "string",
                            "enum": SIGNAL_NAMES,
                            "description": (
                                "Optional TA signal that gates exit. Only exits trades on "
                                "dates where the signal is True. Same signal names as entry_signal."
                            ),
                        },
                        "exit_signal_params": {
                            "type": "object",
                            "description": (
                                "Optional parameters for exit_signal. Same keys as entry_signal_params."
                            ),
                        },
                        "exit_signal_days": {
                            "type": "integer",
                            "minimum": 1,
                            "description": (
                                "Optional: require the exit_signal condition to hold for this "
                                "many consecutive trading days before exiting. Works the same as "
                                "entry_signal_days but for the exit signal. "
                                "Omit or set to 1 for no sustained requirement (default behavior)."
                            ),
                        },
                        "entry_signal_slot": {
                            "type": "string",
                            "description": (
                                "Name of a pre-built signal slot (from build_signal) to "
                                "use as entry date filter. Use this for composite signals. "
                                "Cannot be combined with entry_signal."
                            ),
                        },
                        "exit_signal_slot": {
                            "type": "string",
                            "description": (
                                "Name of a pre-built signal slot (from build_signal) to "
                                "use as exit date filter. Use this for composite signals. "
                                "Cannot be combined with exit_signal."
                            ),
                        },
                        "dataset_name": {
                            "type": "string",
                            "description": (
                                "Name (ticker or filename) of the dataset to run the "
                                "strategy on. Omit to use the most-recently-loaded dataset. "
                                "Use this to compare the same strategy across multiple "
                                "loaded datasets (e.g. 'SPY' vs 'QQQ')."
                            ),
                        },
                        **STRATEGY_PARAMS_SCHEMA,
                        **CALENDAR_EXTRA_PARAMS,
                    },
                    "required": ["strategy_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scan_strategies",
                "description": (
                    "Run multiple strategy/parameter combinations in one call and "
                    "return a ranked leaderboard. Use this instead of calling "
                    "run_strategy repeatedly when the user wants to compare DTE values, "
                    "OTM% values, or multiple strategies on the same dataset. "
                    "Does NOT support signals or calendar strategies — use run_strategy "
                    "for those."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "strategy_names": {
                            "type": "array",
                            "items": {"type": "string", "enum": STRATEGY_NAMES},
                            "minItems": 1,
                            "description": "One or more strategy names to include in the scan.",
                        },
                        "dataset_name": {
                            "type": "string",
                            "description": (
                                "Dataset to run on. "
                                "Omit to use the most-recently-loaded dataset."
                            ),
                        },
                        "max_entry_dte_values": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": (
                                "List of max_entry_dte values to sweep (e.g. [30, 45, 60]). "
                                "Omit to use the default (90)."
                            ),
                        },
                        "exit_dte_values": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": (
                                "List of exit_dte values to sweep (e.g. [0, 7, 14]). "
                                "Omit to use the default (0)."
                            ),
                        },
                        "max_otm_pct_values": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": (
                                "List of max_otm_pct values to sweep (e.g. [0.1, 0.2, 0.3]). "
                                "Omit to use the default (0.5)."
                            ),
                        },
                        "slippage": {
                            "type": "string",
                            "enum": ["mid", "spread", "liquidity"],
                            "description": (
                                "Slippage model applied to all combinations. Default: 'mid'."
                            ),
                        },
                        "max_combinations": {
                            "type": "integer",
                            "description": (
                                "Safety cap on total combinations to run (default: 50). "
                                "Combinations exceeding this limit are skipped."
                            ),
                        },
                    },
                    "required": ["strategy_names"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_results",
                "description": (
                    "List all strategy runs already executed in this session. "
                    "Call this before running a strategy to check whether the same "
                    "combination has already been run and avoid redundant calls. "
                    "Returns a table sorted by mean_return descending."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "strategy_name": {
                            "type": "string",
                            "enum": STRATEGY_NAMES,
                            "description": (
                                "Optional: filter to only show runs for this strategy."
                            ),
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "build_signal",
                "description": (
                    "Build a TA signal (or compose multiple signals) and store the "
                    "resulting valid dates under a named slot. Use this to create "
                    "composite signals (e.g. RSI < 30 AND price above SMA 200) that "
                    "can then be passed to run_strategy via entry_signal_slot / "
                    "exit_signal_slot. Requires data to be loaded first."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot": {
                            "type": "string",
                            "description": (
                                "Name for this signal (e.g. 'entry', 'exit', "
                                "'oversold_uptrend'). Used to reference the signal "
                                "in run_strategy or combine with other slots."
                            ),
                        },
                        "signals": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "enum": SIGNAL_NAMES,
                                        "description": "Signal type name",
                                    },
                                    "params": {
                                        "type": "object",
                                        "description": (
                                            "Optional parameter overrides for this signal"
                                        ),
                                    },
                                    "days": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "description": (
                                            "Optional: require signal True for N "
                                            "consecutive days (sustained)"
                                        ),
                                    },
                                },
                                "required": ["name"],
                            },
                            "minItems": 1,
                            "description": "One or more signals to combine (default: AND)",
                        },
                        "combine": {
                            "type": "string",
                            "enum": ["and", "or"],
                            "description": (
                                "How to combine multiple signals: 'and' (all must be True, "
                                "default) or 'or' (any must be True)"
                            ),
                        },
                        "dataset_name": {
                            "type": "string",
                            "description": (
                                "Name (ticker or filename) of the dataset to build the "
                                "signal from. Omit to use the most-recently-loaded dataset."
                            ),
                        },
                    },
                    "required": ["slot", "signals"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "preview_signal",
                "description": (
                    "Show the valid dates stored in a named signal slot. "
                    "Use after build_signal to inspect how many dates matched."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot": {
                            "type": "string",
                            "description": "Signal slot name to preview",
                        },
                    },
                    "required": ["slot"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_stock_data",
                "description": (
                    "Fetch historical daily OHLCV (open/high/low/close/volume) stock "
                    "price data for a symbol via yfinance. Results are cached locally. "
                    "Use this to inspect price history, verify signal dates, or prime "
                    "the cache before running strategies with TA signals."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "US stock ticker symbol (e.g. SPY, AAPL, QQQ)",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD). Omit for all available history.",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD). Omit for today.",
                        },
                    },
                    "required": ["symbol"],
                },
            },
        },
    ]

    # Data provider tools (only added when API keys are configured)
    tools.extend(get_all_provider_tool_schemas())

    return tools


def _yf_compute_gaps(
    cached_df: pd.DataFrame | None,
    start_dt: date,
    end_dt: date,
) -> list[tuple[str | None, str | None]]:
    """Compute date gaps for the yfinance stock cache.

    Wraps :func:`compute_date_gaps` using ``date`` as the date column
    (matching how yfinance rows are stored in the cache).
    """
    return compute_date_gaps(cached_df, start_dt, end_dt, date_column="date")


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


def _fetch_stock_data_for_signals(dataset: pd.DataFrame) -> pd.DataFrame | None:
    """Fetch OHLCV stock data via yfinance for signal computation.

    Pads the date range by ~250 trading days (~1 year) so that indicators
    with long warmup periods (EMA-200, MACD) have enough history.

    Results are cached in ``~/.optopsy/cache/stocks/{SYMBOL}.parquet``.
    Only missing date ranges (gaps) are fetched from yfinance; subsequent
    calls for the same symbol and date range are served from cache with no
    network activity.

    Returns a DataFrame with columns:
        underlying_symbol, quote_date, open, high, low, close, volume
    Or None if yfinance is not available or all fetches fail.
    """
    if dataset.empty:
        return None

    try:
        import yfinance as yf
    except ImportError:
        _log.warning("yfinance not installed — cannot fetch stock data for TA signals")
        return None

    symbols = dataset["underlying_symbol"].unique().tolist()
    date_min = pd.to_datetime(dataset["quote_date"].min()).date()
    date_max = pd.to_datetime(dataset["quote_date"].max()).date()
    # Pad start by ~250 trading days for indicator warmup
    padded_start = date_min - timedelta(days=365)

    frames = []
    for symbol in symbols:
        try:
            # Phase 1: read cache, detect missing date ranges
            cached = _yf_cache.read(_YF_CACHE_CATEGORY, symbol)
            gaps = _yf_compute_gaps(cached, padded_start, date_max)

            # Phase 2: fetch only the missing gaps from yfinance
            if gaps:
                _log.info(
                    "Fetching %d gap(s) from yfinance for %s: %s",
                    len(gaps),
                    symbol,
                    gaps,
                )
                new_frames = []
                for gap_start, gap_end in gaps:
                    yf_start = gap_start or str(padded_start)
                    yf_end = str(
                        (pd.Timestamp(gap_end).date() + timedelta(days=1))
                        if gap_end
                        else (date_max + timedelta(days=1))
                    )
                    raw = yf.download(
                        symbol, start=yf_start, end=yf_end, progress=False
                    )
                    if raw.empty:
                        continue
                    new_frames.append(_normalise_yf_df(raw, symbol))

                if new_frames:
                    new_data = pd.concat(new_frames, ignore_index=True)
                    cached = _yf_cache.merge_and_save(
                        _YF_CACHE_CATEGORY, symbol, new_data, dedup_cols=_YF_DEDUP_COLS
                    )
            else:
                _log.info("Full cache hit for %s stock data, skipping yfinance", symbol)

            if cached is None or cached.empty:
                continue

            # Phase 3: slice to [padded_start, date_max], rename date → quote_date
            result = cached[
                (pd.to_datetime(cached["date"]).dt.date >= padded_start)
                & (pd.to_datetime(cached["date"]).dt.date <= date_max)
            ].rename(columns={"date": "quote_date"})
            if not result.empty:
                frames.append(
                    result[
                        [
                            "underlying_symbol",
                            "quote_date",
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                        ]
                    ]
                )
        except (OSError, ValueError, KeyError, pd.errors.ParserError) as exc:
            _log.warning("yfinance fetch failed for %s: %s", symbol, exc)

    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def _intersect_with_options_dates(
    signal_dates: pd.DataFrame, options: pd.DataFrame
) -> pd.DataFrame:
    """Filter signal dates to only those present in the options dataset.

    yfinance data extends ~1 year before the options date range (for indicator
    warmup), so signals may fire on dates that have no options data. This
    intersection ensures entry/exit dates always correspond to actual trading
    days in the options dataset.
    """
    if signal_dates.empty or options.empty:
        return signal_dates
    opt_dates = (
        options[["underlying_symbol", "quote_date"]]
        .drop_duplicates()
        .assign(quote_date=lambda df: pd.to_datetime(df["quote_date"]).dt.normalize())
    )
    sd = signal_dates.assign(
        quote_date=lambda df: pd.to_datetime(df["quote_date"]).dt.normalize()
    )
    merged = sd.merge(opt_dates, on=["underlying_symbol", "quote_date"], how="inner")
    return merged.reset_index(drop=True)


def _empty_signal_suggestion(
    raw_signal_dates: pd.DataFrame,
    opt_min: "date",
    opt_max: "date",
) -> str:
    """Build a human-readable suggestion when a signal produces no overlapping dates.

    raw_signal_dates: result of apply_signal() before intersection — the full set
    of dates where the signal fired in the available price history.
    opt_min / opt_max: the date range of the loaded options dataset.

    Three cases:
    1. Signal fired before the options window → suggest fetching around that date.
    2. Signal fired after the options window → same.
    3. Signal fired only within the options window but no dates matched → data gap.
    4. Signal never fired at all → suggest relaxing parameters.
    """
    if raw_signal_dates.empty:
        return (
            "The signal never fired in the available price history. "
            "Try relaxing the signal parameters (e.g. raise the RSI threshold)."
        )

    fired_dates = pd.to_datetime(raw_signal_dates["quote_date"]).dt.date
    before = fired_dates[fired_dates < opt_min]
    after = fired_dates[fired_dates > opt_max]
    within = fired_dates[(fired_dates >= opt_min) & (fired_dates <= opt_max)]

    # If all fired dates are inside the options window but still no overlap,
    # it's a data-gap issue (e.g. signal fired on a date the options dataset skips).
    if before.empty and after.empty and not within.empty:
        return (
            "The signal fired within your options window but on dates not present "
            "in the dataset (possible market holiday or data gap). "
            "Try a slightly wider date range."
        )

    parts = []
    if not before.empty:
        last_before = before.max()
        suggest_start = last_before - timedelta(days=30)
        suggest_end = last_before + timedelta(days=30)
        parts.append(
            f"It last fired on {last_before} (before your options window). "
            f"Try fetching options from {suggest_start} to {suggest_end}."
        )
    if not after.empty:
        first_after = after.min()
        suggest_start = first_after - timedelta(days=30)
        suggest_end = first_after + timedelta(days=30)
        parts.append(
            f"It next fires on {first_after} (after your options window). "
            f"Try fetching options from {suggest_start} to {suggest_end}."
        )
    return " ".join(parts)


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


class ToolResult:
    """Holds separate outputs for the LLM context and the user-facing UI.

    ``llm_summary`` is a short string sent to the LLM so it can reason about
    what happened without blowing up the token budget.
    ``user_display`` is the richer version (with full tables) shown in the UI.
    ``signals`` carries named signal date DataFrames across tool calls.
    ``datasets`` carries the full named-dataset registry so multiple datasets
    can be active simultaneously (keyed by label, e.g. ticker or filename).
    ``active_dataset_name`` is the label of the dataset that was just loaded
    or selected; None means no change to the active selection.
    ``results`` is the session-scoped registry of strategy runs (keyed by a
    string like ``"short_puts:dte=45,exit=0,otm=0.20,slip=mid"``), carrying
    lightweight scalar summaries across tool calls so the agent can recall
    what it has already run without re-executing.
    """

    __slots__ = (
        "llm_summary",
        "user_display",
        "dataset",
        "signals",
        "datasets",
        "active_dataset_name",
        "results",
    )

    def __init__(
        self,
        llm_summary: str,
        dataset: pd.DataFrame | None,
        user_display: str | None = None,
        signals: dict[str, pd.DataFrame] | None = None,
        datasets: dict[str, pd.DataFrame] | None = None,
        active_dataset_name: str | None = None,
        results: dict[str, dict] | None = None,
    ):
        self.llm_summary = llm_summary
        self.user_display = user_display or llm_summary
        self.dataset = dataset
        self.signals = signals
        self.datasets = datasets
        self.active_dataset_name = active_dataset_name
        self.results = results


def _df_summary(df: pd.DataFrame, label: str = "Dataset") -> str:
    """Return a compact text summary of a DataFrame for the LLM."""
    lines = [
        f"{label}: {len(df)} rows, {len(df.columns)} columns",
        f"Columns: {list(df.columns)}",
    ]
    if "quote_date" in df.columns:
        unique_dates = df["quote_date"].nunique()
        lines.append(
            f"Date range: {df['quote_date'].min().date()} to {df['quote_date'].max().date()} "
            f"({unique_dates} unique quote dates)"
        )
        if unique_dates < 2:
            lines.append(
                "WARNING: Only 1 unique quote_date — backtesting requires multiple "
                "quote dates to build entry/exit pairs. Strategies will return no results."
            )
    if "expiration" in df.columns:
        lines.append(f"Unique expirations: {df['expiration'].nunique()}")
    if "underlying_symbol" in df.columns:
        lines.append(f"Symbols: {df['underlying_symbol'].unique().tolist()}")
    return "\n".join(lines)


def _strategy_llm_summary(df: pd.DataFrame, strategy_name: str, mode: str) -> str:
    """Build a compact LLM summary for strategy results.

    Instead of sending a 20-row markdown table, send key stats so the LLM
    can interpret results without burning tokens.  The user already sees
    the full table via user_display.
    """
    lines = [f"{strategy_name} — {len(df)} {mode}"]

    if "pct_change" in df.columns:
        pct = df["pct_change"]
        lines.append(
            f"pct_change: mean={pct.mean():.4f}, std={pct.std():.4f}, "
            f"min={pct.min():.4f}, max={pct.max():.4f}"
        )
    if "dte_entry" in df.columns:
        lines.append(f"DTE range: {df['dte_entry'].min()} to {df['dte_entry'].max()}")
    if "strike" in df.columns:
        lines.append(
            f"Strike range: {df['strike'].min():.0f} to {df['strike'].max():.0f}"
        )
    if mode == "aggregated stats" and "count" in df.columns:
        lines.append(f"Buckets with positive mean: {(df['mean'] > 0).sum()}/{len(df)}")

    lines.append(
        "STOP — results are ready. DO NOT call run_strategy again. "
        "Present these results to the user and explain the key takeaways."
    )
    return "\n".join(lines)


def _run_one_strategy(
    strategy_name: str,
    dataset: pd.DataFrame,
    strat_kwargs: dict,
) -> tuple[pd.DataFrame | None, str]:
    """Execute one strategy call.

    Returns ``(result_df, "")`` on success or ``(None, error_msg)`` on failure.
    Used by both ``run_strategy`` and ``scan_strategies`` to avoid duplicating
    the core call site.
    """
    if strategy_name not in STRATEGIES:
        return None, f"Unknown strategy '{strategy_name}'"
    func, _, _ = STRATEGIES[strategy_name]
    try:
        return func(dataset, **strat_kwargs), ""
    except Exception as e:
        return None, str(e)


def _make_result_key(strategy_name: str, arguments: dict) -> str:
    """Stable, human-readable key for a strategy run (used as results dict key).

    Encodes the core parameters that meaningfully distinguish runs. Omits
    signal params and dataset_name to keep keys short and scannable.
    """
    dte = arguments.get("max_entry_dte", 90)
    exit_dte = arguments.get("exit_dte", 0)
    otm = arguments.get("max_otm_pct", 0.5)
    slippage = arguments.get("slippage", "mid")
    return f"{strategy_name}:dte={dte},exit={exit_dte},otm={otm:.2f},slip={slippage}"


def _make_result_summary(
    strategy_name: str,
    result_df: pd.DataFrame,
    arguments: dict,
) -> dict:
    """Build a lightweight scalar summary stored in the results registry.

    Stores only scalar stats — never full DataFrames — so memory usage stays
    proportional to the number of runs rather than data volume.  Handles both
    raw-mode (``pct_change`` column) and aggregated-mode (``mean`` column).
    """
    summary: dict = {
        "strategy": strategy_name,
        "max_entry_dte": arguments.get("max_entry_dte", 90),
        "exit_dte": arguments.get("exit_dte", 0),
        "max_otm_pct": arguments.get("max_otm_pct", 0.5),
        "slippage": arguments.get("slippage", "mid"),
        "dataset": arguments.get("dataset_name", "default"),
    }
    if "pct_change" in result_df.columns:
        pct = result_df["pct_change"]
        summary.update(
            {
                "count": len(pct),
                "mean_return": round(float(pct.mean()), 4),
                "std": round(float(pct.std()), 4),
                "win_rate": round(float((pct > 0).mean()), 4),
            }
        )
    elif "mean" in result_df.columns:
        if "count" in result_df.columns:
            total = int(result_df["count"].sum())
            wt_mean = float((result_df["mean"] * result_df["count"]).sum() / total)
        else:
            total = len(result_df)
            wt_mean = float(result_df["mean"].mean())
        summary.update(
            {
                "count": total,
                "mean_return": round(wt_mean, 4),
                "std": (
                    round(float(result_df["std"].mean()), 4)
                    if "std" in result_df.columns
                    else None
                ),
                "win_rate": round(float((result_df["mean"] > 0).mean()), 4),
            }
        )
    else:
        summary.update(
            {
                "count": len(result_df),
                "mean_return": None,
                "std": None,
                "win_rate": None,
            }
        )
    return summary


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    dataset: pd.DataFrame | None,
    signals: dict[str, pd.DataFrame] | None = None,
    datasets: dict[str, pd.DataFrame] | None = None,
    results: dict[str, dict] | None = None,
) -> ToolResult:
    """
    Execute a tool call and return a ToolResult.

    The ToolResult contains a concise ``llm_summary`` (sent to the LLM) and a
    richer ``user_display`` (shown in the chat UI).  The ``dataset`` field
    carries the currently-active DataFrame forward.  The ``signals`` dict
    carries named signal date DataFrames across tool calls.  The ``datasets``
    dict is the named-dataset registry (ticker/filename -> DataFrame) that
    allows multiple datasets to be active simultaneously.  The ``results`` dict
    is the session-scoped strategy run registry.
    """
    if signals is None:
        signals = {}
    if datasets is None:
        datasets = {}
    if results is None:
        results = {}

    def _resolve_dataset(
        name: str | None,
        active: pd.DataFrame | None,
        dss: dict[str, pd.DataFrame],
    ) -> pd.DataFrame | None:
        """Return the dataset for *name*, falling back to *active*."""
        if name:
            return dss.get(name)
        return active

    # Helper to build a ToolResult that always carries state forward.
    def _result(
        llm_summary: str,
        ds: pd.DataFrame | None = dataset,
        user_display: str | None = None,
        sigs: dict[str, pd.DataFrame] | None = None,
        dss: dict[str, pd.DataFrame] | None = None,
        active_name: str | None = None,
        res: dict[str, dict] | None = None,
    ) -> ToolResult:
        return ToolResult(
            llm_summary,
            ds,
            user_display,
            sigs if sigs is not None else signals,
            dss if dss is not None else datasets,
            active_name,
            res if res is not None else results,
        )

    if tool_name == "load_csv_data":
        filename = arguments["filename"]
        filepath = os.path.realpath(os.path.join(DATA_DIR, filename))
        if not filepath.startswith(os.path.realpath(DATA_DIR)):
            return _result("Access denied: path outside data directory.")
        if not os.path.exists(filepath):
            available = os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else []
            return _result(
                f"File '{filename}' not found. Available files: {available}",
            )
        kwargs: dict[str, Any] = {}
        if arguments.get("start_date"):
            kwargs["start_date"] = arguments["start_date"]
        if arguments.get("end_date"):
            kwargs["end_date"] = arguments["end_date"]
        try:
            df = op.csv_data(filepath, **kwargs)
            label = filename
            updated_datasets = {**datasets, label: df}
            summary = _df_summary(df, f"Loaded '{label}'")
            if len(updated_datasets) > 1:
                summary += f"\nActive datasets: {list(updated_datasets.keys())}"
            display = f"{summary}\n\nFirst 5 rows:\n{_df_to_markdown(df.head())}"
            return _result(
                summary, df, display, dss=updated_datasets, active_name=label
            )
        except Exception as e:
            return _result(f"Error loading '{filename}': {e}")

    if tool_name == "list_data_files":
        ensure_data_dir()
        files = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
        if not files:
            return _result("No CSV files found in the data directory.")
        return _result(f"Available files: {files}")

    # Generic data-provider dispatch
    provider = get_provider_for_tool(tool_name)
    if provider is not None:
        try:
            summary, df = provider.execute(tool_name, arguments)
            if df is not None:
                if not provider.replaces_dataset(tool_name):
                    # Display-only tool (e.g. stock prices) — show but keep
                    # the current active dataset unchanged.
                    display = f"{summary}\n\n{_df_to_markdown(df)}"
                    return _result(summary, user_display=display)
                # Derive a label from the ticker symbol in the data if possible.
                label: str
                if "underlying_symbol" in df.columns:
                    syms = df["underlying_symbol"].unique()
                    label = syms[0] if len(syms) == 1 else str(list(syms))
                else:
                    label = tool_name
                updated_datasets = {**datasets, label: df}
                display = (
                    f"{summary}\n\nFirst 5 rows:\n" f"{_df_to_markdown(df.head())}"
                )
                if len(updated_datasets) > 1:
                    summary += f"\nActive datasets: {list(updated_datasets.keys())}"
                return _result(
                    summary, df, display, dss=updated_datasets, active_name=label
                )
            return _result(summary)
        except Exception as e:
            return _result(f"Error running {tool_name}: {e}")

    if tool_name == "preview_data":
        ds_name = arguments.get("dataset_name")
        active_ds = _resolve_dataset(ds_name, dataset, datasets)
        if active_ds is None:
            if datasets:
                return _result(
                    f"Dataset '{ds_name}' not found. "
                    f"Available: {list(datasets.keys())}"
                )
            return _result("No dataset loaded. Use load_csv_data first.")
        label = ds_name or (list(datasets.keys())[-1] if datasets else "Dataset")
        summary = _df_summary(active_ds, label)
        display = f"{summary}\n\nFirst 5 rows:\n{_df_to_markdown(active_ds.head())}"
        return _result(summary, user_display=display)

    # -----------------------------------------------------------------
    # suggest_strategy_params — analyze DTE/OTM% distributions and
    # return anchored parameter recommendations for strategy runs
    # -----------------------------------------------------------------
    if tool_name == "suggest_strategy_params":
        import json as _json

        ds_name = arguments.get("dataset_name")
        active_ds = _resolve_dataset(ds_name, dataset, datasets)
        if active_ds is None:
            if datasets:
                return _result(
                    f"Dataset '{ds_name}' not found. "
                    f"Available: {list(datasets.keys())}"
                )
            return _result("No dataset loaded. Load data first.")

        strategy_name = arguments.get("strategy_name")
        df = active_ds.copy()

        # DTE distribution
        df["_dte"] = (
            pd.to_datetime(df["expiration"]) - pd.to_datetime(df["quote_date"])
        ).dt.days
        dte_series = df["_dte"].dropna()
        dte_pcts = {
            k: int(dte_series.quantile(q))
            for k, q in [
                ("p10", 0.10),
                ("p25", 0.25),
                ("p50", 0.50),
                ("p75", 0.75),
                ("p90", 0.90),
            ]
        }
        dte_stats = {
            "min": int(dte_series.min()),
            **dte_pcts,
            "max": int(dte_series.max()),
        }

        # OTM% distribution — only rows where underlying_price > 0
        df_otm = df[df["underlying_price"] > 0].copy()
        df_otm["_otm_pct"] = (
            df_otm["strike"] - df_otm["underlying_price"]
        ).abs() / df_otm["underlying_price"]
        otm_series = df_otm["_otm_pct"].dropna()
        otm_pcts = {
            k: round(float(otm_series.quantile(q)), 4)
            for k, q in [
                ("p10", 0.10),
                ("p25", 0.25),
                ("p50", 0.50),
                ("p75", 0.75),
                ("p90", 0.90),
            ]
        }
        otm_stats = {
            "min": round(float(otm_series.min()), 4),
            **otm_pcts,
            "max": round(float(otm_series.max()), 4),
        }

        # Base recommendations
        recommended: dict = {
            "max_entry_dte": dte_stats["p75"],
            "exit_dte": max(0, dte_stats["p10"]),
            "max_otm_pct": otm_stats["p75"],
        }
        strategy_note = ""

        # Strategy-specific overrides
        if strategy_name in CALENDAR_STRATEGIES:
            recommended = {
                "front_dte_min": max(10, dte_stats["p10"]),
                "front_dte_max": min(45, dte_stats["p50"]),
                "back_dte_min": min(50, dte_stats["p75"]),
                "back_dte_max": min(120, dte_stats["p90"]),
            }
            strategy_note = (
                "Calendar strategy — use front/back DTE instead of max_entry_dte."
            )
        elif strategy_name in {
            "iron_condor",
            "reverse_iron_condor",
            "iron_butterfly",
            "reverse_iron_butterfly",
        }:
            recommended["max_entry_dte"] = min(45, dte_stats["p75"])
            recommended["max_otm_pct"] = min(0.3, otm_stats["p75"])
            strategy_note = (
                "Multi-leg strategies typically work best in the 20-45 DTE range."
            )
        elif strategy_name and "spread" in strategy_name:
            recommended["max_otm_pct"] = min(0.2, otm_stats["p75"])
            strategy_note = "Spreads often use tighter OTM% for better liquidity."

        reco_json = _json.dumps(recommended, indent=2)
        label = f" for `{strategy_name}`" if strategy_name else ""

        dte_rows = "\n".join(f"| {k} | {v} |" for k, v in dte_stats.items())
        otm_rows = "\n".join(f"| {k} | {v:.4f} |" for k, v in otm_stats.items())

        llm_summary = (
            f"suggest_strategy_params{label}\n"
            f"DTE distribution: {dte_stats}\n"
            f"OTM% distribution: {otm_stats}\n"
            f"Recommended: {recommended}"
            + (f"\nNote: {strategy_note}" if strategy_note else "")
        )
        user_display = (
            f"### Parameter Suggestions{label}\n\n"
            f"**DTE Distribution** ({len(dte_series):,} options)\n\n"
            f"| Percentile | DTE |\n|---|---|\n{dte_rows}\n\n"
            f"**OTM% Distribution** ({len(otm_series):,} options)\n\n"
            f"| Percentile | OTM% |\n|---|---|\n{otm_rows}\n\n"
            f"**Recommended starting parameters:**\n```json\n{reco_json}\n```"
            + (f"\n\n*{strategy_note}*" if strategy_note else "")
        )
        return _result(llm_summary, user_display=user_display)

    # -----------------------------------------------------------------
    # build_signal — create/compose TA signals and store as named slots
    # -----------------------------------------------------------------
    if tool_name == "build_signal":
        slot = arguments.get("slot", "").strip()
        if not slot:
            return _result("Missing required 'slot' name for the signal.")
        ds_name = arguments.get("dataset_name")
        active_ds = _resolve_dataset(ds_name, dataset, datasets)
        if active_ds is None:
            if datasets:
                return _result(
                    f"Dataset '{ds_name}' not found. "
                    f"Available: {list(datasets.keys())}"
                )
            return _result("No dataset loaded. Load data first.")
        dataset = active_ds  # shadow for the rest of the block

        signal_specs = arguments.get("signals")
        if not signal_specs or not isinstance(signal_specs, list):
            return _result("'signals' must be a non-empty array of signal specs.")

        # Determine if any signal needs OHLCV data
        needs_stock = any(s.get("name") not in _DATE_ONLY_SIGNALS for s in signal_specs)

        signal_data = None
        if needs_stock:
            signal_data = _fetch_stock_data_for_signals(dataset)
            if signal_data is None:
                return _result(
                    "TA signals require stock price data but yfinance is not "
                    "installed or the fetch failed. Install yfinance "
                    "(`pip install yfinance`) and try again.",
                )

        # Fallback for date-only signals
        if signal_data is None:
            signal_data = (
                dataset[["underlying_symbol", "quote_date"]]
                .drop_duplicates()
                .sort_values(["underlying_symbol", "quote_date"])
                .reset_index(drop=True)
            )

        # Build individual signal functions
        built_signals = []
        descriptions = []
        for spec in signal_specs:
            name = spec.get("name")
            if not name or name not in SIGNAL_REGISTRY:
                return _result(
                    f"Unknown signal '{name}'. Available: {', '.join(SIGNAL_NAMES)}"
                )
            params = spec.get("params") or {}
            sig = SIGNAL_REGISTRY[name](**params)
            try:
                sig_days = int(spec.get("days", 0))
            except (TypeError, ValueError):
                sig_days = 0
            if sig_days > 1:
                sig = _signals.sustained(sig, sig_days)
                descriptions.append(f"{name}(sustained {sig_days}d)")
            else:
                param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                descriptions.append(f"{name}({param_str})" if param_str else name)
            built_signals.append(sig)

        # Combine signals
        combine = arguments.get("combine", "and")
        if len(built_signals) == 1:
            combined = built_signals[0]
        elif combine == "or":
            combined = _signals.or_signals(*built_signals)
        else:
            combined = _signals.and_signals(*built_signals)

        # Compute valid dates, intersected with actual options dates.
        # Keep the raw (pre-intersection) result so we can reuse it for
        # the suggestion message without a second apply_signal() call.
        raw_signal_dates = apply_signal(signal_data, combined)
        valid_dates = _intersect_with_options_dates(raw_signal_dates, dataset)

        # Store in signals dict
        updated_signals = dict(signals)
        updated_signals[slot] = valid_dates

        combiner = f" {combine.upper()} " if len(descriptions) > 1 else ""
        desc = combiner.join(descriptions)
        n_dates = len(valid_dates)
        symbols = valid_dates["underlying_symbol"].unique().tolist() if n_dates else []
        summary = (
            f"Signal '{slot}' built: {desc} → {n_dates} valid dates " f"for {symbols}"
        )
        display_lines = [summary]
        if n_dates > 0:
            date_min = valid_dates["quote_date"].min().date()
            date_max = valid_dates["quote_date"].max().date()
            display_lines.append(f"Date range: {date_min} to {date_max}")
        else:
            opt_min = dataset["quote_date"].min().date()
            opt_max = dataset["quote_date"].max().date()
            suggestion = _empty_signal_suggestion(raw_signal_dates, opt_min, opt_max)
            display_lines.append(
                f"WARNING: No signal dates overlap the options data "
                f"({opt_min} to {opt_max}). {suggestion}"
            )
        display = "\n".join(display_lines)
        return _result(summary, user_display=display, sigs=updated_signals)

    # -----------------------------------------------------------------
    # preview_signal — inspect stored signal dates
    # -----------------------------------------------------------------
    if tool_name == "preview_signal":
        slot = arguments.get("slot", "").strip()
        if not slot:
            return _result("Missing required 'slot' name.")
        if slot not in signals:
            available_slots = list(signals.keys()) if signals else []
            return _result(
                f"No signal named '{slot}'. "
                f"Available slots: {available_slots or 'none — use build_signal first'}"
            )
        valid_dates = signals[slot]
        n_dates = len(valid_dates)
        if n_dates == 0:
            return _result(f"Signal '{slot}' has 0 valid dates.")
        symbols = valid_dates["underlying_symbol"].unique().tolist()
        date_min = valid_dates["quote_date"].min().date()
        date_max = valid_dates["quote_date"].max().date()
        summary = (
            f"Signal '{slot}': {n_dates} valid dates, "
            f"symbols={symbols}, range={date_min} to {date_max}"
        )
        # Show a sample of dates in the user display
        display = f"{summary}\n\n{_df_to_markdown(valid_dates, max_rows=30)}"
        return _result(summary, user_display=display)

    # -----------------------------------------------------------------
    # fetch_stock_data — explicit yfinance OHLCV fetch (display-only)
    # -----------------------------------------------------------------
    if tool_name == "fetch_stock_data":
        try:
            import yfinance as yf
        except ImportError:
            return _result("yfinance is not installed. Run: pip install yfinance")

        symbol = arguments["symbol"].upper()
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

        start_dt = pd.Timestamp(start_date).date() if start_date else None
        end_dt = pd.Timestamp(end_date).date() if end_date else date.today()
        # When no start date given, fetch the full available history
        fetch_start = start_dt or date(2000, 1, 1)

        cached = _yf_cache.read(_YF_CACHE_CATEGORY, symbol)
        gaps = _yf_compute_gaps(cached, fetch_start, end_dt)

        if gaps:
            new_frames = []
            for gap_start, gap_end in gaps:
                yf_start = gap_start or str(fetch_start)
                yf_end = str(
                    (pd.Timestamp(gap_end).date() + timedelta(days=1))
                    if gap_end
                    else (end_dt + timedelta(days=1))
                )
                try:
                    raw = yf.download(
                        symbol, start=yf_start, end=yf_end, progress=False
                    )
                    if not raw.empty:
                        new_frames.append(_normalise_yf_df(raw, symbol))
                except (OSError, ValueError) as exc:
                    _log.warning("yfinance fetch failed for %s: %s", symbol, exc)

            if new_frames:
                new_data = pd.concat(new_frames, ignore_index=True)
                cached = _yf_cache.merge_and_save(
                    _YF_CACHE_CATEGORY, symbol, new_data, dedup_cols=_YF_DEDUP_COLS
                )

        if cached is None or cached.empty:
            return _result(f"No stock data found for {symbol}.")

        # Slice to requested range and rename date → quote_date for display
        df = cached.rename(columns={"date": "quote_date"})
        if start_dt:
            df = df[pd.to_datetime(df["quote_date"]).dt.date >= start_dt]
        df = df[pd.to_datetime(df["quote_date"]).dt.date <= end_dt]

        if df.empty:
            return _result(f"No stock data for {symbol} in the requested date range.")

        d_min = pd.to_datetime(df["quote_date"]).dt.date.min()
        d_max = pd.to_datetime(df["quote_date"]).dt.date.max()
        summary = (
            f"Fetched {len(df):,} daily price records for {symbol}. "
            f"Date range: {d_min} to {d_max}."
        )
        display = f"{summary}\n\nFirst 10 rows:\n{_df_to_markdown(df.head(10))}"
        return _result(summary, user_display=display)

    # -----------------------------------------------------------------
    # run_strategy
    # -----------------------------------------------------------------
    if tool_name == "run_strategy":
        strategy_name = arguments.get("strategy_name")
        if not strategy_name or strategy_name not in STRATEGIES:
            return _result(
                f"Unknown strategy '{strategy_name}'. "
                f"Available: {', '.join(STRATEGY_NAMES)}",
            )
        ds_name = arguments.get("dataset_name")
        active_ds = _resolve_dataset(ds_name, dataset, datasets)
        if active_ds is None:
            if datasets:
                return _result(
                    f"Dataset '{ds_name}' not found. "
                    f"Available: {list(datasets.keys())}"
                )
            return _result("No dataset loaded. Load data first.")
        dataset = active_ds  # shadow for the rest of the block
        func, _, _ = STRATEGIES[strategy_name]
        # Build a clean kwargs dict without mutating the original arguments.
        # Strip signal params — handled separately below.
        _signal_keys = {
            "strategy_name",
            "entry_signal",
            "entry_signal_params",
            "entry_signal_days",
            "exit_signal",
            "exit_signal_params",
            "exit_signal_days",
            "entry_signal_slot",
            "exit_signal_slot",
        }
        strat_kwargs = {
            k: v
            for k, v in arguments.items()
            if k not in _signal_keys
            and (strategy_name in CALENDAR_STRATEGIES or k not in CALENDAR_EXTRA_PARAMS)
        }

        # --- Resolve entry dates ---
        entry_slot = arguments.get("entry_signal_slot")
        entry_signal_name = arguments.get("entry_signal")

        if entry_slot and entry_signal_name:
            return _result(
                "Cannot use both entry_signal and entry_signal_slot. Pick one."
            )

        # Use pre-built slot if provided
        if entry_slot:
            if entry_slot not in signals:
                return _result(
                    f"No signal slot '{entry_slot}'. "
                    f"Build it first with build_signal. "
                    f"Available: {list(signals.keys()) or 'none'}"
                )
            strat_kwargs["entry_dates"] = signals[entry_slot]

        # --- Resolve exit dates ---
        exit_slot = arguments.get("exit_signal_slot")
        exit_signal_name = arguments.get("exit_signal")

        if exit_slot and exit_signal_name:
            return _result(
                "Cannot use both exit_signal and exit_signal_slot. Pick one."
            )

        if exit_slot:
            if exit_slot not in signals:
                return _result(
                    f"No signal slot '{exit_slot}'. "
                    f"Build it first with build_signal. "
                    f"Available: {list(signals.keys()) or 'none'}"
                )
            strat_kwargs["exit_dates"] = signals[exit_slot]

        # --- Inline signal resolution (single signal, no slot) ---
        # Validate signal names early, before fetching stock data
        if entry_signal_name and entry_signal_name not in SIGNAL_REGISTRY:
            return _result(
                f"Unknown entry_signal '{entry_signal_name}'. "
                f"Available: {', '.join(SIGNAL_NAMES)}",
            )
        if exit_signal_name and exit_signal_name not in SIGNAL_REGISTRY:
            return _result(
                f"Unknown exit_signal '{exit_signal_name}'. "
                f"Available: {', '.join(SIGNAL_NAMES)}",
            )

        # Determine if we need OHLCV stock data for signal computation
        needs_stock = (
            entry_signal_name and entry_signal_name not in _DATE_ONLY_SIGNALS
        ) or (exit_signal_name and exit_signal_name not in _DATE_ONLY_SIGNALS)

        signal_data = None
        if needs_stock:
            signal_data = _fetch_stock_data_for_signals(dataset)
            if signal_data is None:
                return _result(
                    "TA signals require stock price data but yfinance is not "
                    "installed or the fetch failed. Install yfinance "
                    "(`pip install yfinance`) and try again.",
                )

        # For date-only signals, extract unique dates from the option dataset
        if signal_data is None and (entry_signal_name or exit_signal_name):
            signal_data = (
                dataset[["underlying_symbol", "quote_date"]]
                .drop_duplicates()
                .sort_values(["underlying_symbol", "quote_date"])
                .reset_index(drop=True)
            )

        # Resolve entry_signal string -> SignalFunc -> pre-computed entry_dates
        if entry_signal_name:
            entry_params = arguments.get("entry_signal_params") or {}
            sig = SIGNAL_REGISTRY[entry_signal_name](**entry_params)
            # Wrap with sustained() if entry_signal_days is provided
            try:
                days = int(arguments.get("entry_signal_days", 0))
            except (TypeError, ValueError):
                days = 0
            if days > 1:
                sig = _signals.sustained(sig, days)
            raw_entry_dates = apply_signal(signal_data, sig)
            entry_dates = _intersect_with_options_dates(raw_entry_dates, dataset)
            if entry_dates.empty:
                opt_min = dataset["quote_date"].min().date()
                opt_max = dataset["quote_date"].max().date()
                suggestion = _empty_signal_suggestion(raw_entry_dates, opt_min, opt_max)
                return _result(
                    f"Entry signal '{entry_signal_name}' produced no dates overlapping "
                    f"the options data ({opt_min} to {opt_max}). {suggestion}"
                )
            strat_kwargs["entry_dates"] = entry_dates

        # Resolve exit_signal string -> SignalFunc -> pre-computed exit_dates
        if exit_signal_name:
            exit_params = arguments.get("exit_signal_params") or {}
            exit_sig = SIGNAL_REGISTRY[exit_signal_name](**exit_params)
            try:
                exit_days = int(arguments.get("exit_signal_days", 0))
            except (TypeError, ValueError):
                exit_days = 0
            if exit_days > 1:
                exit_sig = _signals.sustained(exit_sig, exit_days)
            raw_exit_dates = apply_signal(signal_data, exit_sig)
            exit_dates = _intersect_with_options_dates(raw_exit_dates, dataset)
            if exit_dates.empty:
                opt_min = dataset["quote_date"].min().date()
                opt_max = dataset["quote_date"].max().date()
                suggestion = _empty_signal_suggestion(raw_exit_dates, opt_min, opt_max)
                return _result(
                    f"Exit signal '{exit_signal_name}' produced no dates overlapping "
                    f"the options data ({opt_min} to {opt_max}). {suggestion}"
                )
            strat_kwargs["exit_dates"] = exit_dates
        result_df, err = _run_one_strategy(strategy_name, dataset, strat_kwargs)
        if err:
            return _result(f"Error running {strategy_name}: {err}")
        if result_df is None or result_df.empty:
            params_used = {k: v for k, v in arguments.items() if k != "strategy_name"}
            return _result(
                f"{strategy_name} returned no results with parameters: "
                f"{params_used or 'defaults'}.",
            )
        is_raw = arguments.get("raw", False)
        mode = "raw trades" if is_raw else "aggregated stats"
        table = _df_to_markdown(result_df)
        display = f"**{strategy_name}** — {len(result_df)} {mode}\n\n{table}"
        # LLM gets a compact summary instead of a full table to save tokens.
        # The user already sees the full table via user_display.
        llm_summary = _strategy_llm_summary(result_df, strategy_name, mode)
        result_key = _make_result_key(strategy_name, arguments)
        updated_results = {
            **results,
            result_key: _make_result_summary(strategy_name, result_df, arguments),
        }
        return _result(llm_summary, user_display=display, res=updated_results)

    # -----------------------------------------------------------------
    # scan_strategies — run Cartesian product of params in one call
    # -----------------------------------------------------------------
    if tool_name == "scan_strategies":
        import itertools as _itertools

        strategy_names = arguments.get("strategy_names", [])
        if not strategy_names:
            return _result("'strategy_names' must be a non-empty list.")
        invalid = [s for s in strategy_names if s not in STRATEGIES]
        if invalid:
            return _result(
                f"Unknown strategies: {invalid}. "
                f"Available: {', '.join(STRATEGY_NAMES)}"
            )

        active_ds = _resolve_dataset(arguments.get("dataset_name"), dataset, datasets)
        if active_ds is None:
            if datasets:
                return _result(
                    f"Dataset '{arguments.get('dataset_name')}' not found. "
                    f"Available: {list(datasets.keys())}"
                )
            return _result("No dataset loaded. Load data first.")

        max_combos = int(arguments.get("max_combinations", 50))
        slippage = arguments.get("slippage", "mid")
        dte_values = arguments.get("max_entry_dte_values") or [90]
        exit_values = arguments.get("exit_dte_values") or [0]
        otm_values = arguments.get("max_otm_pct_values") or [0.5]

        all_combos = list(
            _itertools.product(strategy_names, dte_values, exit_values, otm_values)
        )
        truncated = len(all_combos) > max_combos
        combos_to_run = all_combos[:max_combos]

        rows = []
        errors = []
        scan_results = dict(results)

        for strat, max_dte, exit_dte, max_otm in combos_to_run:
            if strat in CALENDAR_STRATEGIES:
                errors.append(
                    f"{strat}: skipped (calendar strategy — no front/back DTE sweep; "
                    "use run_strategy directly)"
                )
                continue

            strat_kwargs = {
                "max_entry_dte": max_dte,
                "exit_dte": exit_dte,
                "max_otm_pct": max_otm,
                "slippage": slippage,
            }
            result_df, err = _run_one_strategy(strat, active_ds, strat_kwargs)

            combo_args = {
                "max_entry_dte": max_dte,
                "exit_dte": exit_dte,
                "max_otm_pct": max_otm,
                "slippage": slippage,
            }
            if err:
                errors.append(
                    f"{strat}(dte={max_dte},exit={exit_dte},otm={max_otm:.2f}): {err}"
                )
                continue

            if result_df is None or result_df.empty:
                rows.append(
                    {
                        "strategy": strat,
                        "max_entry_dte": max_dte,
                        "exit_dte": exit_dte,
                        "max_otm_pct": max_otm,
                        "count": 0,
                        "mean_return": float("nan"),
                        "std": float("nan"),
                        "win_rate": float("nan"),
                    }
                )
                continue

            summary = _make_result_summary(strat, result_df, combo_args)
            rows.append(
                {
                    "strategy": strat,
                    "max_entry_dte": max_dte,
                    "exit_dte": exit_dte,
                    "max_otm_pct": max_otm,
                    "count": summary["count"],
                    "mean_return": summary["mean_return"],
                    "std": summary["std"],
                    "win_rate": summary["win_rate"],
                }
            )
            key = _make_result_key(strat, combo_args)
            scan_results[key] = {**summary, "source": "scan_strategies"}

        if not rows and not errors:
            return _result("scan_strategies: no combinations produced results.")

        leaderboard = (
            pd.DataFrame(rows)
            .sort_values("mean_return", ascending=False)
            .reset_index(drop=True)
        )
        n_ok = int(leaderboard["mean_return"].notna().sum())
        n_empty = int((leaderboard["count"] == 0).sum())

        header_parts = [
            f"scan_strategies: {len(combos_to_run)} combination(s) run, "
            f"{n_ok} with results, {n_empty} empty, {len(errors)} error(s)"
        ]
        if truncated:
            header_parts.append(
                f"WARNING: {len(all_combos) - max_combos} combination(s) skipped "
                f"(exceeded max_combinations={max_combos})"
            )
        if errors:
            header_parts.append("Errors/skipped: " + "; ".join(errors))

        best_rows = leaderboard[leaderboard["mean_return"].notna()]
        if not best_rows.empty:
            best = best_rows.iloc[0]
            header_parts.append(
                f"Best: {best['strategy']} "
                f"(dte={best['max_entry_dte']}, exit={best['exit_dte']}, "
                f"otm={best['max_otm_pct']:.2f}) — "
                f"mean={best['mean_return']:.4f}, win_rate={best['win_rate']:.2%}"
            )

        llm_summary = "\n".join(header_parts)
        table = _df_to_markdown(leaderboard)
        user_display = f"### Strategy Scan Results\n\n{llm_summary}\n\n{table}"
        return _result(llm_summary, user_display=user_display, res=scan_results)

    # -----------------------------------------------------------------
    # list_results — recall prior strategy runs from this session
    # -----------------------------------------------------------------
    if tool_name == "list_results":
        filter_name = arguments.get("strategy_name")
        relevant = {
            k: v
            for k, v in results.items()
            if filter_name is None or v.get("strategy") == filter_name
        }

        if not relevant:
            if filter_name:
                return _result(
                    f"No prior runs for '{filter_name}' in this session. "
                    "Use run_strategy or scan_strategies first."
                )
            return _result(
                "No strategy runs in this session yet. "
                "Use run_strategy or scan_strategies first."
            )

        df = (
            pd.DataFrame(list(relevant.values()))
            .sort_values("mean_return", ascending=False, na_position="last")
            .reset_index(drop=True)
        )
        col_order = [
            "strategy",
            "max_entry_dte",
            "exit_dte",
            "max_otm_pct",
            "slippage",
            "count",
            "mean_return",
            "std",
            "win_rate",
            "dataset",
        ]
        df = df[[c for c in col_order if c in df.columns]]

        n = len(df)
        label = f"for '{filter_name}'" if filter_name else "across all strategies"
        llm_summary = f"list_results: {n} run(s) {label} this session.\n" + df[
            [
                c
                for c in [
                    "strategy",
                    "max_entry_dte",
                    "exit_dte",
                    "max_otm_pct",
                    "mean_return",
                    "win_rate",
                ]
                if c in df.columns
            ]
        ].to_string(index=False)
        user_display = (
            f"### Prior Strategy Runs "
            f"({n}{f' — {filter_name}' if filter_name else ''})\n\n"
            "*Session only — not persisted across restarts. "
            "Sorted by mean_return descending.*\n\n"
            f"{_df_to_markdown(df)}"
        )
        return _result(llm_summary, user_display=user_display)

    available = [
        "load_csv_data",
        "list_data_files",
        "preview_data",
        "suggest_strategy_params",
        "build_signal",
        "preview_signal",
        "fetch_stock_data",
        "run_strategy",
        "scan_strategies",
        "list_results",
    ]
    return _result(f"Unknown tool: {tool_name}. Available: {', '.join(available)}")
