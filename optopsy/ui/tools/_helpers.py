"""Shared helper functions, data classes, and caches for tool handlers.

Provides:

- ``ToolResult`` — value object carrying LLM summary, user display, and
  updated session state (dataset, signals, results) between tool calls.
- DataFrame formatting utilities (``_df_to_markdown``, ``_df_summary``)
- Signal resolution and stock data fetching for TA signals
- Strategy result summary construction (``_make_result_summary``)
- Simulation trade log persistence via ``ParquetCache``
"""

import logging
import os
import re
from datetime import date, timedelta
from typing import Any

import pandas as pd

import optopsy.signals as _signals
from optopsy.metrics import profit_factor as _profit_factor
from optopsy.metrics import win_rate as _win_rate
from optopsy.signals import apply_signal

from ..providers.cache import ParquetCache
from ._models import StrategyResultSummary
from ._schemas import (
    _DATE_ONLY_SIGNALS,
    _IV_SIGNALS,
    SIGNAL_NAMES,
    SIGNAL_REGISTRY,
    STRATEGIES,
)

_log = logging.getLogger(__name__)

# Cache for yfinance OHLCV data (category="yf_stocks", one file per symbol).
# Deliberately distinct from EODHD's "stocks" category to avoid schema collisions.
_yf_cache = ParquetCache()
_YF_CACHE_CATEGORY = "yf_stocks"
_YF_DEDUP_COLS = ["date"]

# Shared simulation cache instance and helpers.
_sim_cache = ParquetCache(
    cache_dir=os.path.join(os.path.expanduser("~"), ".optopsy", "cache")
)
_SIM_CATEGORY = "simulations"


def _sim_fs_key(sim_key: str) -> str:
    """Sanitize a simulation key for filesystem safety."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", sim_key)


def write_sim_trade_log(sim_key: str, trade_log: pd.DataFrame) -> None:
    """Persist a simulation trade log to the cache."""
    _sim_cache.write(_SIM_CATEGORY, _sim_fs_key(sim_key), trade_log)


def read_sim_trade_log(sim_key: str) -> pd.DataFrame | None:
    """Read a simulation trade log from the cache.

    Returns the DataFrame or None if not found / empty.
    """
    df = _sim_cache.read(_SIM_CATEGORY, _sim_fs_key(sim_key))
    if df is None or df.empty:
        return None
    return df


MAX_ROWS = 50


def _yf_fetch_and_cache(
    symbol: str,
    cached: pd.DataFrame | None,
    end_dt: date,
) -> pd.DataFrame | None:
    """Fetch missing yfinance data and update the cache.

    On cold cache, fetches everything with ``period="max"``.  On warm cache,
    fetches only the tail from ``cache_max + 1`` to *end_dt* (the only gap
    worth considering — yfinance returns all available data on first fetch,
    so interior gaps are just non-trading days).

    Returns the updated cached DataFrame, or None when yfinance returns no
    data on a cold cache.  Exceptions from yfinance (``OSError``,
    ``ValueError``) are **not** caught here — callers are responsible for
    handling them.
    """
    import yfinance as yf

    if cached is None or cached.empty:
        _log.info("Cold cache for %s, fetching full history from yfinance", symbol)
        raw = yf.download(symbol, period="max", progress=False)
    else:
        cache_max = pd.to_datetime(cached["date"]).dt.date.max()
        fetch_start = cache_max + timedelta(days=1)
        if fetch_start > end_dt:
            _log.info("Cache for %s is up to date, skipping yfinance", symbol)
            return cached
        _log.info(
            "Fetching %s stock data from %s to %s",
            symbol,
            fetch_start,
            end_dt,
        )
        raw = yf.download(
            symbol,
            start=str(fetch_start),
            end=str(end_dt + timedelta(days=1)),
            progress=False,
        )

    if not raw.empty:
        new_data = _normalise_yf_df(raw, symbol)
        cached = _yf_cache.merge_and_save(
            _YF_CACHE_CATEGORY, symbol, new_data, dedup_cols=_YF_DEDUP_COLS
        )
    return cached


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

    Results are cached in ``~/.optopsy/cache/yf_stocks/{SYMBOL}.parquet``.
    On cold cache, fetches all history via ``period="max"``.  On warm cache,
    only the tail (cache_max → date_max) is fetched.  Interior gaps are
    ignored — yfinance returns all available data on first fetch, so gaps
    are just non-trading days (weekends/holidays).

    Returns a DataFrame with columns:
        underlying_symbol, quote_date, open, high, low, close, volume
    Or None if yfinance is not available or all fetches fail.
    """
    if dataset.empty:
        return None

    try:
        import yfinance as yf  # noqa: F401 — validates availability
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
            cached = _yf_cache.read(_YF_CACHE_CATEGORY, symbol)
            cached = _yf_fetch_and_cache(symbol, cached, date_max)

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


def _df_to_markdown(df: pd.DataFrame, max_rows: int = MAX_ROWS) -> str:
    """Convert a DataFrame to a markdown table, truncating if too large."""
    total = len(df)
    truncated = total > max_rows
    if truncated:
        df = df.head(max_rows)
    # Stringify Interval columns so they render as readable text
    # (e.g. "(0, 30]") instead of "[object Object]" in the browser.
    # pd.cut() produces CategoricalDtype with Interval categories, not IntervalDtype.
    interval_cols = [
        c
        for c in df.columns
        if isinstance(df[c].dtype, pd.IntervalDtype)
        or (
            isinstance(df[c].dtype, pd.CategoricalDtype)
            and isinstance(df[c].dtype.categories.dtype, pd.IntervalDtype)
        )
    ]
    if interval_cols:
        df = df.copy()
        for col in interval_cols:
            df[col] = df[col].astype(str)
    table = df.to_markdown(index=False, floatfmt=".4f")
    if truncated:
        table += f"\n\n*... showing {max_rows} of {total} rows*"
    return table


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
        "chart_figure",
        "_result_df",
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
        chart_figure: Any = None,
        result_df: pd.DataFrame | None = None,
    ):
        self.llm_summary = llm_summary
        self.user_display = user_display or llm_summary
        self.dataset = dataset
        self.signals = signals
        self.datasets = datasets
        self.active_dataset_name = active_dataset_name
        self.results = results
        self.chart_figure = chart_figure
        self._result_df = result_df


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
        "The UI already shows an interactive table with the full results. "
        "Do NOT reproduce the data as a table in your response — just "
        "explain the key takeaways and insights in plain text."
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


def _select_results(
    results: dict[str, dict],
    result_keys: list[str] | None,
) -> tuple[dict[str, dict] | None, str | None]:
    """Select and validate results by key.

    Returns ``(selected, error_msg)``.  When ``error_msg`` is not None,
    the caller should surface it to the user.
    """
    if result_keys:
        missing = [k for k in result_keys if k not in results]
        if missing:
            return None, (
                f"Result key(s) not found: {missing}. Available: {list(results.keys())}"
            )
        return {k: results[k] for k in result_keys}, None
    return dict(results), None


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

    Uses :class:`StrategyResultSummary` to validate and type the output.
    """
    base: dict[str, Any] = {
        "strategy": strategy_name,
        "max_entry_dte": arguments.get("max_entry_dte", 90),
        "exit_dte": arguments.get("exit_dte", 0),
        "max_otm_pct": arguments.get("max_otm_pct", 0.5),
        "slippage": arguments.get("slippage", "mid"),
        "dataset": arguments.get("dataset_name", "default"),
    }
    if "pct_change" in result_df.columns:
        pct = result_df["pct_change"].dropna()
        base.update(
            {
                "count": len(pct),
                "mean_return": round(float(pct.mean()), 4),
                "std": round(float(pct.std()), 4),
                "win_rate": round(_win_rate(pct), 4),
                "profit_factor": round(_profit_factor(pct), 4),
            }
        )
    elif "mean" in result_df.columns:
        if "count" in result_df.columns:
            total = int(result_df["count"].sum())
            wt_mean = float((result_df["mean"] * result_df["count"]).sum() / total)
        else:
            total = len(result_df)
            wt_mean = float(result_df["mean"].mean())
        # Compute aggregated profit_factor by combining gross wins and
        # losses across all groups, then dividing.  This avoids the
        # pitfall of weighted-averaging per-group profit factors where
        # inf values (groups with no losses) would dominate or need
        # filtering — which would make the aggregate not equal the true
        # all-trades combined ratio.
        agg_pf = None
        if "mean" in result_df.columns and "count" in result_df.columns:
            group_pnl = result_df["mean"] * result_df["count"]
            total_wins = float(group_pnl[group_pnl > 0].sum())
            total_losses = float(group_pnl[group_pnl < 0].sum())
            if total_losses != 0:
                agg_pf = round(abs(total_wins) / abs(total_losses), 4)
            elif total_wins > 0:
                agg_pf = float("inf")
            else:
                agg_pf = 0.0
        base.update(
            {
                "count": total,
                "mean_return": round(wt_mean, 4),
                "std": (
                    round(float(result_df["std"].mean()), 4)
                    if "std" in result_df.columns
                    else None
                ),
                "win_rate": (
                    round(
                        float(
                            (result_df["win_rate"] * result_df["count"]).sum() / total
                        ),
                        4,
                    )
                    if "win_rate" in result_df.columns and "count" in result_df.columns
                    else round(float((result_df["mean"] > 0).mean()), 4)
                ),
                "profit_factor": agg_pf,
            }
        )
    else:
        base.update(
            {
                "count": len(result_df),
                "mean_return": None,
                "std": None,
                "win_rate": None,
                "profit_factor": None,
            }
        )
    return StrategyResultSummary(**base).model_dump()


def _signal_slot_summary(
    valid_dates: pd.DataFrame,
) -> tuple[int, list[str], "date | None", "date | None"]:
    """Extract common stats from a signal slot DataFrame.

    Returns ``(n_dates, symbols, date_min, date_max)``.  When the slot is
    empty ``symbols`` is ``[]`` and date values are ``None``.
    """
    n_dates = len(valid_dates)
    if n_dates == 0:
        return 0, [], None, None
    symbols = valid_dates["underlying_symbol"].unique().tolist()
    date_min = valid_dates["quote_date"].min().date()
    date_max = valid_dates["quote_date"].max().date()
    return n_dates, symbols, date_min, date_max


def _date_only_fallback(dataset: pd.DataFrame) -> pd.DataFrame:
    """Build a minimal date-indexed DataFrame for date-only signals.

    Used when no OHLCV stock data is needed — extracts unique
    ``(underlying_symbol, quote_date)`` pairs from the options dataset.
    """
    return (
        dataset[["underlying_symbol", "quote_date"]]
        .drop_duplicates()
        .sort_values(["underlying_symbol", "quote_date"])
        .reset_index(drop=True)
    )


def _iv_signal_data(dataset: pd.DataFrame) -> pd.DataFrame | None:
    """Extract columns needed for IV rank signals from the options dataset.

    Returns the dataset subset with required columns for IV rank computation,
    or None if the dataset lacks ``implied_volatility``.
    """
    if "implied_volatility" not in dataset.columns:
        return None
    keep = [
        "underlying_symbol",
        "quote_date",
        "underlying_price",
        "strike",
        "option_type",
        "implied_volatility",
        "expiration",
    ]
    cols = [c for c in keep if c in dataset.columns]
    if len(cols) < len(keep):
        return None
    return dataset[cols].copy()


# ---------------------------------------------------------------------------
# Shared parameter key sets (8.4.1)
# ---------------------------------------------------------------------------

_SIGNAL_PARAM_KEYS = frozenset(
    {
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
)

_SIM_PARAM_KEYS = frozenset(
    {"capital", "quantity", "max_positions", "multiplier", "selector"}
)

# ---------------------------------------------------------------------------
# Shared IV error message (8.2.3)
# ---------------------------------------------------------------------------

_IV_MISSING_MSG = (
    "IV rank signals require options data with an "
    "'implied_volatility' column. Fetch data from a provider "
    "that includes IV (e.g. EODHD), or load a CSV with an "
    "implied_volatility column."
)

_IV_COLUMN_MISSING_MSG = (
    "Dataset does not contain 'implied_volatility'. "
    "Fetch data from a provider that includes IV (e.g. EODHD) "
    "or load a CSV with an implied_volatility column."
)


# ---------------------------------------------------------------------------
# Quote date filtering for vol surface tools (8.2.4)
# ---------------------------------------------------------------------------


def _filter_by_quote_date(
    ds: pd.DataFrame,
    quote_date_str: str | None,
) -> tuple[pd.DataFrame | None, str | None, str | None]:
    """Filter a dataset to a single quote date.

    Returns ``(filtered_df, resolved_date_str, error_msg)``.  When
    ``error_msg`` is not None the caller should return it immediately.
    """
    try:
        quote_dates = pd.to_datetime(ds["quote_date"])
    except (ValueError, TypeError) as e:
        return None, None, f"Cannot parse quote_date column as datetime: {e}"

    if quote_date_str:
        target_date = pd.to_datetime(quote_date_str)
        df = ds[quote_dates.dt.normalize() == target_date.normalize()].copy()
        if df.empty:
            available = sorted(quote_dates.dt.date.unique())
            closest = min(
                available, key=lambda d: abs((pd.Timestamp(d) - target_date).days)
            )
            return (
                None,
                None,
                (
                    f"No data for {quote_date_str}. "
                    f"Closest available date: {closest}. "
                    f"Try quote_date='{closest}'."
                ),
            )
        return df, quote_date_str, None
    else:
        latest_day = quote_dates.dt.normalize().max()
        df = ds[quote_dates.dt.normalize() == latest_day].copy()
        return df, str(latest_day.date()), None


# ---------------------------------------------------------------------------
# Signal resolution for strategy handlers (8.2.2)
# ---------------------------------------------------------------------------


def _resolve_signals_for_strategy(
    arguments: dict[str, Any],
    signals: dict[str, pd.DataFrame],
    dataset: pd.DataFrame,
) -> tuple[dict[str, Any], str | None]:
    """Resolve entry/exit signal slots and inline signals into dates.

    Shared by both ``run_strategy`` and ``simulate`` to avoid duplicating
    ~80 lines of signal resolution logic.

    Returns ``(strat_kwargs_update, error_msg)``.  On success ``error_msg``
    is None and ``strat_kwargs_update`` is a dict with ``entry_dates``
    and/or ``exit_dates`` to merge into the strategy kwargs.
    """
    update: dict[str, Any] = {}

    # --- Resolve entry dates ---
    entry_slot = arguments.get("entry_signal_slot")
    entry_signal_name = arguments.get("entry_signal")

    if entry_slot and entry_signal_name:
        return {}, "Cannot use both entry_signal and entry_signal_slot. Pick one."

    if entry_slot:
        if entry_slot not in signals:
            return {}, (
                f"No signal slot '{entry_slot}'. "
                f"Build it first with build_signal. "
                f"Available: {list(signals.keys()) or 'none'}"
            )
        update["entry_dates"] = signals[entry_slot]

    # --- Resolve exit dates ---
    exit_slot = arguments.get("exit_signal_slot")
    exit_signal_name = arguments.get("exit_signal")

    if exit_slot and exit_signal_name:
        return {}, "Cannot use both exit_signal and exit_signal_slot. Pick one."

    if exit_slot:
        if exit_slot not in signals:
            return {}, (
                f"No signal slot '{exit_slot}'. "
                f"Build it first with build_signal. "
                f"Available: {list(signals.keys()) or 'none'}"
            )
        update["exit_dates"] = signals[exit_slot]

    # --- Inline signal resolution ---
    if entry_signal_name and entry_signal_name not in SIGNAL_REGISTRY:
        return {}, (
            f"Unknown entry_signal '{entry_signal_name}'. "
            f"Available: {', '.join(SIGNAL_NAMES)}"
        )
    if exit_signal_name and exit_signal_name not in SIGNAL_REGISTRY:
        return {}, (
            f"Unknown exit_signal '{exit_signal_name}'. "
            f"Available: {', '.join(SIGNAL_NAMES)}"
        )

    # Determine what data each signal needs
    needs_stock = (
        entry_signal_name
        and entry_signal_name not in _DATE_ONLY_SIGNALS
        and entry_signal_name not in _IV_SIGNALS
    ) or (
        exit_signal_name
        and exit_signal_name not in _DATE_ONLY_SIGNALS
        and exit_signal_name not in _IV_SIGNALS
    )
    needs_iv = (entry_signal_name and entry_signal_name in _IV_SIGNALS) or (
        exit_signal_name and exit_signal_name in _IV_SIGNALS
    )

    signal_data = None
    if needs_stock:
        signal_data = _fetch_stock_data_for_signals(dataset)
        if signal_data is None:
            return {}, (
                "TA signals require stock price data but yfinance is not "
                "installed or the fetch failed. Install yfinance "
                "(`pip install yfinance`) and try again."
            )

    iv_signal_data = None
    if needs_iv:
        iv_signal_data = _iv_signal_data(dataset)
        if iv_signal_data is None:
            return {}, _IV_MISSING_MSG

    # Build date-only fallback for non-IV, non-stock signals even when
    # needs_iv is true, so a date-only signal paired with an IV signal
    # does not receive signal_data=None.
    has_non_iv_signal = (
        entry_signal_name and entry_signal_name not in _IV_SIGNALS
    ) or (exit_signal_name and exit_signal_name not in _IV_SIGNALS)
    if signal_data is None and has_non_iv_signal:
        signal_data = _date_only_fallback(dataset)

    for sig_name, prefix, dates_key in [
        (entry_signal_name, "entry", "entry_dates"),
        (exit_signal_name, "exit", "exit_dates"),
    ]:
        if sig_name:
            sd = iv_signal_data if sig_name in _IV_SIGNALS else signal_data
            assert sd is not None
            dates, err_msg = _resolve_inline_signal(
                sig_name, arguments, sd, dataset, prefix
            )
            if err_msg:
                return {}, err_msg
            update[dates_key] = dates

    return update, None


def _resolve_inline_signal(
    signal_name: str,
    arguments: dict[str, Any],
    signal_data: pd.DataFrame,
    dataset: pd.DataFrame,
    prefix: str,
) -> tuple[pd.DataFrame | None, str | None]:
    """Resolve an inline signal name to a filtered dates DataFrame.

    ``prefix`` is ``"entry"`` or ``"exit"`` — used to look up
    ``{prefix}_signal_params`` and ``{prefix}_signal_days`` in *arguments*.

    Returns ``(dates_df, error_msg)``.  On success ``error_msg`` is None.
    On failure ``dates_df`` is None and ``error_msg`` explains the issue.
    """
    params = arguments.get(f"{prefix}_signal_params") or {}
    sig = SIGNAL_REGISTRY[signal_name](**params)
    try:
        days = int(arguments.get(f"{prefix}_signal_days", 0))
    except (TypeError, ValueError):
        days = 0
    if days > 1:
        sig = _signals.sustained(sig, days)

    raw_dates = apply_signal(signal_data, sig)
    filtered = _intersect_with_options_dates(raw_dates, dataset)
    if filtered.empty:
        opt_min = dataset["quote_date"].min().date()
        opt_max = dataset["quote_date"].max().date()
        suggestion = _empty_signal_suggestion(raw_dates, opt_min, opt_max)
        kind = prefix.capitalize()
        return None, (
            f"{kind} signal '{signal_name}' produced no dates overlapping "
            f"the options data ({opt_min} to {opt_max}). {suggestion}"
        )
    return filtered, None
