import logging
from typing import Any

import optopsy as op
import optopsy.signals as _signals

from ..providers import get_all_provider_tool_schemas

_log = logging.getLogger(__name__)

# Legacy dicts kept for backward compatibility with code that imports them.
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

# Signal-related properties shared by run_strategy and simulate tool schemas.
SIGNAL_PARAMS_SCHEMA = {
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
}

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


_TOOL_DESCRIPTIONS: dict[str, str] = {
    "preview_data": (
        "Show shape, columns, date range, and sample rows of a dataset. "
        "Omit dataset_name to inspect the most-recently-loaded dataset."
    ),
    "describe_data": (
        "Show summary statistics, data types, missing values, and "
        "distributions for a dataset. Use for data quality checks "
        "and debugging."
    ),
    "suggest_strategy_params": (
        "Analyze a loaded dataset and suggest good starting parameters "
        "(max_entry_dte, exit_dte, max_otm_pct) based on the actual DTE "
        "and OTM% distributions. Call this before running a strategy when "
        "the user has not specified explicit parameters, to avoid guessing "
        "values the data can't satisfy. Returns percentile tables and a "
        "JSON block of recommended parameter values ready to pass to "
        "run_strategy or scan_strategies."
    ),
    "run_strategy": (
        "Run an options strategy backtest on the loaded dataset. "
        "Strategies: "
        + ", ".join(sorted(op.__dict__.get("__all__", [])) or ["long_calls"])
        + ". "
        "Calendar/diagonal strategies also accept front_dte_min, "
        "front_dte_max, back_dte_min, back_dte_max."
    ),
    "scan_strategies": (
        "Run multiple strategy/parameter combinations in one call and "
        "return a ranked leaderboard. Use this instead of calling "
        "run_strategy repeatedly when the user wants to compare DTE values, "
        "OTM% values, or multiple strategies on the same dataset. "
        "Does NOT support signals or calendar strategies — use run_strategy "
        "for those."
    ),
    "list_results": (
        "List all strategy runs already executed in this session. "
        "Call this before running a strategy to check whether the same "
        "combination has already been run and avoid redundant calls. "
        "Returns a table sorted by mean_return descending."
    ),
    "build_signal": (
        "Build a TA signal (or compose multiple signals) and store the "
        "resulting valid dates under a named slot. Use this to create "
        "composite signals (e.g. RSI < 30 AND price above SMA 200) that "
        "can then be passed to run_strategy via entry_signal_slot / "
        "exit_signal_slot. Requires data to be loaded first."
    ),
    "preview_signal": (
        "Show the valid dates stored in a named signal slot. "
        "Use after build_signal to inspect how many dates matched."
    ),
    "list_signals": (
        "List all named signal slots built in this session. "
        "Shows slot names, date counts, and date ranges."
    ),
    "inspect_cache": (
        "List all locally cached datasets and their date ranges without "
        "making any network requests. Use this to discover what data is "
        "already available before deciding whether to fetch more. "
        "Optionally filter by symbol."
    ),
    "clear_cache": (
        "Delete cached datasets (options chains, stock prices). "
        "Optionally filter by symbol."
    ),
    "fetch_stock_data": (
        "Fetch all available daily OHLCV (open/high/low/close/volume) "
        "stock price data for a symbol via yfinance. Always fetches the "
        "full history and caches it locally. Use this to inspect price "
        "history, verify signal dates, or prime the cache before running "
        "strategies with TA signals."
    ),
    "simulate": (
        "Run a chronological simulation of an options strategy. "
        "Walks through trades sequentially with capital tracking, "
        "position limits, and equity curve generation. Returns "
        "trade log, equity curve, and summary stats (win rate, "
        "max drawdown, profit factor, etc.)."
    ),
    "get_simulation_trades": (
        "Show the full trade log from a previous simulation. "
        "Use after 'simulate' when the user asks to see "
        "detailed trades."
    ),
    "create_chart": (
        "Create an interactive Plotly chart from strategy results, "
        "simulation trade logs, datasets, or signals. Use this to "
        "visualize equity curves, return distributions, strategy "
        "comparisons, and heatmaps."
    ),
}


def get_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool schemas for all optopsy functions.

    Generates parameter schemas from Pydantic models in ``_models.py``
    and pairs them with prompt-engineered descriptions from
    ``_TOOL_DESCRIPTIONS``.
    """
    from ._models import TOOL_ARG_MODELS, pydantic_to_openai_params

    # Core tools (exclude provider-specific tools like fetch_options_data)
    _PROVIDER_TOOLS = {"fetch_options_data"}
    tools = []
    for tool_name, model_cls in TOOL_ARG_MODELS.items():
        if tool_name in _PROVIDER_TOOLS:
            continue
        description = _TOOL_DESCRIPTIONS.get(tool_name, f"Execute {tool_name}")
        # Use run_strategy description with dynamic strategy list
        if tool_name == "run_strategy":
            description = (
                "Run an options strategy backtest on the loaded dataset. "
                "Strategies: " + ", ".join(STRATEGY_NAMES) + ". "
                "Calendar/diagonal strategies also accept front_dte_min, "
                "front_dte_max, back_dte_min, back_dte_max."
            )
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": pydantic_to_openai_params(model_cls),
                },
            }
        )

    # Data provider tools (only added when API keys are configured)
    tools.extend(get_all_provider_tool_schemas())

    return tools
