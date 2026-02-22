import logging
import os
import re
from datetime import date, timedelta
from typing import Any

import pandas as pd

import optopsy.signals as _signals
from optopsy.signals import apply_signal

from ..providers.cache import ParquetCache, compute_date_gaps
from ._models import StrategyResultSummary
from ._schemas import SIGNAL_REGISTRY, STRATEGIES

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
    ):
        self.llm_summary = llm_summary
        self.user_display = user_display or llm_summary
        self.dataset = dataset
        self.signals = signals
        self.datasets = datasets
        self.active_dataset_name = active_dataset_name
        self.results = results
        self.chart_figure = chart_figure


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

    Uses :class:`StrategyResultSummary` to validate and type the output.
    """
    base = {
        "strategy": strategy_name,
        "max_entry_dte": arguments.get("max_entry_dte", 90),
        "exit_dte": arguments.get("exit_dte", 0),
        "max_otm_pct": arguments.get("max_otm_pct", 0.5),
        "slippage": arguments.get("slippage", "mid"),
        "dataset": arguments.get("dataset_name", "default"),
    }
    if "pct_change" in result_df.columns:
        pct = result_df["pct_change"]
        base.update(
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
        base.update(
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
        base.update(
            {
                "count": len(result_df),
                "mean_return": None,
                "std": None,
                "win_rate": None,
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
    ]
    cols = [c for c in keep if c in dataset.columns]
    if len(cols) < len(keep):
        return None
    return dataset[cols].copy()


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
