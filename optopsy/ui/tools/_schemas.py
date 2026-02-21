import logging
from typing import Any

import optopsy as op
import optopsy.signals as _signals

from ..providers import get_all_provider_tool_schemas

_log = logging.getLogger(__name__)

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
                "name": "inspect_cache",
                "description": (
                    "List all locally cached datasets and their date ranges without "
                    "making any network requests. Use this to discover what data is "
                    "already available before deciding whether to fetch more. "
                    "Optionally filter by symbol."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": (
                                "Optional ticker symbol to filter results (e.g. 'SPY'). "
                                "Omit to list all cached symbols."
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
