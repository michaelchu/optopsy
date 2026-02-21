import logging
import os
from datetime import timedelta
from typing import Any

import pandas as pd

import optopsy as op
import optopsy.signals as _signals
from optopsy.signals import apply_signal

from .providers import get_all_provider_tool_schemas, get_provider_for_tool

_log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.expanduser("~"), ".optopsy", "data")

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
                "description": "Show shape, columns, date range, and sample rows of the loaded dataset.",
                "parameters": {"type": "object", "properties": {}, "required": []},
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
    ]

    # Data provider tools (only added when API keys are configured)
    tools.extend(get_all_provider_tool_schemas())

    return tools


def _fetch_stock_data_for_signals(dataset: pd.DataFrame) -> pd.DataFrame | None:
    """Fetch OHLCV stock data via yfinance for signal computation.

    Pads the date range by 250 trading days (~1 year) so that indicators
    with long warmup periods (EMA-200, MACD) have enough history.

    Returns a DataFrame with columns:
        underlying_symbol, quote_date, open, high, low, close, volume
    Or None if yfinance is not available or the fetch fails.
    """
    if dataset.empty:
        return None

    try:
        import yfinance as yf
    except ImportError:
        _log.warning("yfinance not installed — cannot fetch stock data for TA signals")
        return None

    symbols = dataset["underlying_symbol"].unique().tolist()
    date_min = dataset["quote_date"].min()
    date_max = dataset["quote_date"].max()
    # Pad start by ~250 trading days for indicator warmup
    padded_start = date_min - timedelta(days=365)

    frames = []
    for symbol in symbols:
        try:
            df = yf.download(
                symbol,
                start=str(padded_start.date()),
                end=str((date_max + timedelta(days=1)).date()),
                progress=False,
            )
            if df.empty:
                continue
            # yfinance returns MultiIndex columns for single tickers
            cols = df.columns
            if isinstance(cols, pd.MultiIndex):
                df.columns = [c[0] for c in cols]
            price_df = df.reset_index()
            price_df.columns = [c.lower() for c in price_df.columns]
            price_df = price_df.rename(columns={"date": "quote_date"})
            price_df["quote_date"] = pd.to_datetime(
                price_df["quote_date"]
            ).dt.tz_localize(None)
            price_df["underlying_symbol"] = symbol
            frames.append(
                price_df[
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
        except Exception as exc:
            _log.warning("yfinance fetch failed for %s: %s", symbol, exc)

    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


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
    """

    __slots__ = ("llm_summary", "user_display", "dataset", "signals")

    def __init__(
        self,
        llm_summary: str,
        dataset: pd.DataFrame | None,
        user_display: str | None = None,
        signals: dict[str, pd.DataFrame] | None = None,
    ):
        self.llm_summary = llm_summary
        self.user_display = user_display or llm_summary
        self.dataset = dataset
        self.signals = signals


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


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    dataset: pd.DataFrame | None,
    signals: dict[str, pd.DataFrame] | None = None,
) -> ToolResult:
    """
    Execute a tool call and return a ToolResult.

    The ToolResult contains a concise ``llm_summary`` (sent to the LLM) and a
    richer ``user_display`` (shown in the chat UI).  The ``dataset`` field
    carries the currently-active DataFrame forward.  The ``signals`` dict
    carries named signal date DataFrames across tool calls.
    """
    if signals is None:
        signals = {}

    # Helper to build a ToolResult that always carries signals forward.
    def _result(
        llm_summary: str,
        ds: pd.DataFrame | None = dataset,
        user_display: str | None = None,
        sigs: dict[str, pd.DataFrame] | None = None,
    ) -> ToolResult:
        return ToolResult(
            llm_summary, ds, user_display, sigs if sigs is not None else signals
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
            summary = _df_summary(df, f"Loaded '{filename}'")
            display = f"{summary}\n\nFirst 5 rows:\n{_df_to_markdown(df.head())}"
            return _result(summary, df, display)
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
                display = (
                    f"{summary}\n\nFirst 5 rows:\n" f"{_df_to_markdown(df.head())}"
                )
                return _result(summary, df, display)
            return _result(summary)
        except Exception as e:
            return _result(f"Error running {tool_name}: {e}")

    if tool_name == "preview_data":
        if dataset is None:
            return _result("No dataset loaded. Use load_csv_data first.")
        summary = _df_summary(dataset)
        display = f"{summary}\n\nFirst 5 rows:\n{_df_to_markdown(dataset.head())}"
        return _result(summary, user_display=display)

    # -----------------------------------------------------------------
    # build_signal — create/compose TA signals and store as named slots
    # -----------------------------------------------------------------
    if tool_name == "build_signal":
        slot = arguments.get("slot", "").strip()
        if not slot:
            return _result("Missing required 'slot' name for the signal.")
        if dataset is None:
            return _result("No dataset loaded. Load data first.")

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

        # Compute valid dates
        valid_dates = apply_signal(signal_data, combined)

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
    # run_strategy
    # -----------------------------------------------------------------
    if tool_name == "run_strategy":
        strategy_name = arguments.get("strategy_name")
        if not strategy_name or strategy_name not in STRATEGIES:
            return _result(
                f"Unknown strategy '{strategy_name}'. "
                f"Available: {', '.join(STRATEGY_NAMES)}",
            )
        if dataset is None:
            return _result("No dataset loaded. Load data first.")
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
            strat_kwargs["entry_dates"] = apply_signal(signal_data, sig)

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
            strat_kwargs["exit_dates"] = apply_signal(signal_data, exit_sig)
        try:
            result = func(dataset, **strat_kwargs)
            if result.empty:
                params_used = {
                    k: v for k, v in arguments.items() if k != "strategy_name"
                }
                return _result(
                    f"{strategy_name} returned no results with parameters: "
                    f"{params_used or 'defaults'}.",
                )
            is_raw = arguments.get("raw", False)
            mode = "raw trades" if is_raw else "aggregated stats"
            table = _df_to_markdown(result)
            display = f"**{strategy_name}** — {len(result)} {mode}\n\n{table}"
            # LLM gets a compact summary instead of a full table to save tokens.
            # The user already sees the full table via user_display.
            llm_summary = _strategy_llm_summary(result, strategy_name, mode)
            return _result(llm_summary, user_display=display)
        except Exception as e:
            return _result(f"Error running {strategy_name}: {e}")

    available = [
        "load_csv_data",
        "list_data_files",
        "preview_data",
        "build_signal",
        "preview_signal",
        "run_strategy",
    ]
    return _result(f"Unknown tool: {tool_name}. Available: {', '.join(available)}")
