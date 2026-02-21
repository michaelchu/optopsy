import itertools as _itertools
import json as _json
import logging
import os
from datetime import date, timedelta
from typing import Any

import pandas as pd

import optopsy as op
from optopsy.signals import apply_signal

from ..providers import get_provider_for_tool
from ..providers.cache import ParquetCache
from ._helpers import (
    DATA_DIR,
    _DATE_ONLY_SIGNALS,
    _YF_CACHE_CATEGORY,
    _YF_DEDUP_COLS,
    _df_summary,
    _df_to_markdown,
    _empty_signal_suggestion,
    _fetch_stock_data_for_signals,
    _intersect_with_options_dates,
    _make_result_key,
    _make_result_summary,
    _normalise_yf_df,
    _run_one_strategy,
    _strategy_llm_summary,
    _yf_cache,
    _yf_compute_gaps,
    ensure_data_dir,
)
from ._helpers import ToolResult
from ._schemas import (
    CALENDAR_EXTRA_PARAMS,
    CALENDAR_STRATEGIES,
    SIGNAL_NAMES,
    SIGNAL_REGISTRY,
    STRATEGIES,
    STRATEGY_NAMES,
)

import optopsy.signals as _signals

_log = logging.getLogger(__name__)


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
    # inspect_cache — list cached datasets and their date ranges
    # -----------------------------------------------------------------
    if tool_name == "inspect_cache":
        filter_symbol = arguments.get("symbol", "").strip().upper() or None
        cache = ParquetCache()
        cache_files = cache.size()  # {category/SYMBOL.parquet: bytes}

        if not cache_files:
            return _result(
                "No cached data found. Use fetch_options_data or fetch_stock_data to load data."
            )

        rows = []
        for key, size_bytes in sorted(cache_files.items()):
            parts = key.split("/")
            if len(parts) != 2:
                continue
            category, fname = parts
            symbol = fname.replace(".parquet", "")
            if filter_symbol and symbol != filter_symbol:
                continue
            df = cache.read(category, symbol)
            if df is None or df.empty:
                continue
            # Detect date column
            date_col = next(
                (c for c in ("quote_date", "date") if c in df.columns), None
            )
            if date_col:
                dates = pd.to_datetime(df[date_col])
                date_from = str(dates.min().date())
                date_to = str(dates.max().date())
                unique_dates = int(dates.dt.date.nunique())
            else:
                date_from = date_to = "unknown"
                unique_dates = 0
            rows.append(
                {
                    "symbol": symbol,
                    "category": category,
                    "rows": len(df),
                    "date_from": date_from,
                    "date_to": date_to,
                    "trading_days": unique_dates,
                    "size_mb": round(size_bytes / 1_048_576, 2),
                }
            )

        if not rows:
            msg = (
                f"No cached data for {filter_symbol}."
                if filter_symbol
                else "No cached data found."
            )
            return _result(msg)

        result_df = pd.DataFrame(rows)
        total_mb = result_df["size_mb"].sum()
        llm_lines = [
            f"inspect_cache: {len(rows)} cached dataset(s), {total_mb:.1f} MB total"
        ]
        for r in rows:
            llm_lines.append(
                f"{r['symbol']} ({r['category']}): {r['rows']:,} rows, "
                f"{r['date_from']} to {r['date_to']}, {r['trading_days']} trading days"
            )
        llm_summary = "\n".join(llm_lines)
        user_display = (
            f"### Cached Datasets\n\n"
            f"*{len(rows)} dataset(s) — {total_mb:.1f} MB total on disk*\n\n"
            f"{_df_to_markdown(result_df)}"
        )
        return _result(llm_summary, user_display=user_display)

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
        top_n = 5
        top = df.head(top_n)
        top_lines = []
        for _, row in top.iterrows():
            parts = [str(row["strategy"])]
            if "max_entry_dte" in row:
                parts.append(f"dte={int(row['max_entry_dte'])}")
            if "exit_dte" in row:
                parts.append(f"exit={int(row['exit_dte'])}")
            if "max_otm_pct" in row:
                parts.append(f"otm={row['max_otm_pct']:.2f}")
            if "mean_return" in row and pd.notna(row["mean_return"]):
                parts.append(f"mean={row['mean_return']:.4f}")
            if "win_rate" in row and pd.notna(row["win_rate"]):
                parts.append(f"wr={row['win_rate']:.2%}")
            top_lines.append(" | ".join(parts))
        more = f" ({n - top_n} more not shown)" if n > top_n else ""
        llm_summary = (
            f"list_results: {n} run(s) {label} this session. "
            f"Top {min(n, top_n)} by mean_return{more}:\n" + "\n".join(top_lines)
        )
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
        "inspect_cache",
        "run_strategy",
        "scan_strategies",
        "list_results",
    ]
    return _result(f"Unknown tool: {tool_name}. Available: {', '.join(available)}")
