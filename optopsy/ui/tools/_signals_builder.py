"""Signal tool handlers: build_signal, preview_signal, list_signals, fetch_stock_data."""

import logging
from datetime import date
from typing import Any

import pandas as pd

import optopsy.signals as _signals
from optopsy.signals import signal_dates

from ._executor import _register, _require_dataset
from ._helpers import (
    _YF_CACHE_CATEGORY,
    _date_only_fallback,
    _df_to_markdown,
    _empty_signal_suggestion,
    _fetch_stock_data_for_signals,
    _fetch_stock_data_for_symbol,
    _intersect_with_options_dates,
    _iv_signal_data,
    _signal_slot_summary,
    _yf_cache,
    _yf_fetch_and_cache,
)
from ._schemas import (
    _DATE_ONLY_SIGNALS,
    _IV_SIGNALS,
    _OHLC_SIGNALS,
    _VOLUME_SIGNALS,
    SIGNAL_NAMES,
    SIGNAL_REGISTRY,
)

_log = logging.getLogger(__name__)


def _remap_cross_symbol_dates(
    signal_dates_df: pd.DataFrame,
    dataset: pd.DataFrame,
) -> pd.DataFrame:
    """Replace the signal symbol with the options dataset symbol(s).

    When ``signal_symbol`` is used, the signal fires on a different ticker
    (e.g. VIX) than the options dataset (e.g. SPX).  This function copies
    the signal dates once per options-dataset symbol so that the subsequent
    intersection matches correctly.
    """
    options_symbols = dataset["underlying_symbol"].unique().tolist()
    frames = []
    for opt_sym in options_symbols:
        mapped = signal_dates_df.copy()
        mapped["underlying_symbol"] = opt_sym
        frames.append(mapped)
    return pd.concat(frames, ignore_index=True)


@_register("build_signal")
def _handle_build_signal(arguments, dataset, signals, datasets, results, _result):
    slot = arguments.get("slot", "").strip()
    if not slot:
        return _result("Missing required 'slot' name for the signal.")
    active_ds, _, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None
    dataset = active_ds  # shadow for the rest of the block

    signal_specs = arguments.get("signals")
    if not signal_specs or not isinstance(signal_specs, list):
        return _result("'signals' must be a non-empty array of signal specs.")

    # Determine what data the signals need
    has_iv_signal = any(s.get("name") in _IV_SIGNALS for s in signal_specs)
    needs_stock = any(
        s.get("name") not in _DATE_ONLY_SIGNALS and s.get("name") not in _IV_SIGNALS
        for s in signal_specs
    )

    # IV signals use options data; OHLCV signals (RSI, SMA, etc.) use stock
    # data. Combining them in a single build_signal call is not supported
    # because each type requires a different dataset shape.
    if has_iv_signal and needs_stock:
        iv_names = [
            s.get("name")
            for s in signal_specs
            if s.get("name") and s.get("name") in _IV_SIGNALS
        ]
        stock_names = [
            s.get("name")
            for s in signal_specs
            if s.get("name")
            and s.get("name") not in _DATE_ONLY_SIGNALS
            and s.get("name") not in _IV_SIGNALS
        ]
        return _result(
            f"Cannot combine IV signals ({', '.join(iv_names)}) with "
            f"OHLCV signals ({', '.join(stock_names)}) in one build_signal "
            f"call. IV signals use options data while OHLCV signals use "
            f"stock price data. Build them as separate slots and pass them "
            f"to run_strategy via entry_signal_slot / exit_signal_slot.",
        )

    from ._helpers import _IV_MISSING_MSG

    signal_data = None
    signal_symbol = arguments.get("signal_symbol")
    if signal_symbol:
        signal_symbol = signal_symbol.strip()

    if has_iv_signal:
        iv_data = _iv_signal_data(dataset)
        if iv_data is None:
            return _result(_IV_MISSING_MSG)
        signal_data = iv_data
    elif needs_stock:
        if signal_symbol:
            signal_data = _fetch_stock_data_for_symbol(signal_symbol, dataset)
        else:
            signal_data = _fetch_stock_data_for_signals(dataset)
        if signal_data is None:
            return _result(
                "TA signals require stock price data but yfinance is not "
                "installed or the fetch failed. Install yfinance "
                "(`pip install yfinance`) and try again.",
            )
        # Validate that volume signals have access to a volume column.
        has_volume_signal = any(s.get("name") in _VOLUME_SIGNALS for s in signal_specs)
        if has_volume_signal and "volume" not in signal_data.columns:
            vol_names = [
                s.get("name") for s in signal_specs if s.get("name") in _VOLUME_SIGNALS
            ]
            return _result(
                f"Volume signals ({', '.join(vol_names)}) require a 'volume' "
                f"column in the stock data, but it was not found. "
                f"Ensure the stock data source provides volume information.",
            )
        # Validate that OHLC signals have access to high/low/close columns.
        has_ohlc_signal = any(s.get("name") in _OHLC_SIGNALS for s in signal_specs)
        _ohlc_cols = ("high", "low", "close")
        missing_ohlc = [c for c in _ohlc_cols if c not in signal_data.columns]
        if has_ohlc_signal and missing_ohlc:
            ohlc_names = [
                s.get("name") for s in signal_specs if s.get("name") in _OHLC_SIGNALS
            ]
            return _result(
                f"OHLC signals ({', '.join(ohlc_names)}) require "
                f"'high', 'low', and 'close' columns in the stock data, "
                f"but {', '.join(missing_ohlc)} were not found. "
                f"Ensure the stock data source provides OHLCV information.",
            )

    # Fallback for date-only signals
    if signal_data is None:
        signal_data = _date_only_fallback(dataset)

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
    raw_signal_dates = signal_dates(signal_data, combined)

    # Cross-symbol: remap signal symbol to options dataset symbol(s).
    # Only applies when we actually fetched data for signal_symbol (i.e.
    # needs_stock was true).  IV and date-only signals already use the
    # options dataset's symbols, so remapping would duplicate rows.
    if signal_symbol and needs_stock and not raw_signal_dates.empty:
        raw_signal_dates = _remap_cross_symbol_dates(raw_signal_dates, dataset)

    valid_dates = _intersect_with_options_dates(raw_signal_dates, dataset)

    # Store in signals dict
    updated_signals = dict(signals)
    updated_signals[slot] = valid_dates

    combiner = f" {combine.upper()} " if len(descriptions) > 1 else ""
    desc = combiner.join(descriptions)
    n_dates, symbols, date_min, date_max = _signal_slot_summary(valid_dates)
    summary = f"Signal '{slot}' built: {desc} → {n_dates} valid dates for {symbols}"
    display_lines = [summary]
    if n_dates > 0:
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


# Restricted builtins for build_custom_signal sandbox.
# Blocks import, open, exec, eval, compile, __import__, globals, locals, etc.
_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}


@_register("build_custom_signal")
def _handle_build_custom_signal(
    arguments, dataset, signals, datasets, results, _result
):
    import numpy as np

    slot = arguments.get("slot", "").strip()
    if not slot:
        return _result("Missing required 'slot' name for the signal.")
    code = arguments.get("code", "").strip()
    if not code:
        return _result(
            "Missing required 'code' — provide Python code that computes a boolean `signal` Series."
        )

    active_ds, _, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None
    dataset = active_ds

    # Fetch OHLCV data for signal computation
    signal_symbol = arguments.get("signal_symbol")
    if signal_symbol:
        signal_symbol = signal_symbol.strip()
    if signal_symbol:
        signal_data = _fetch_stock_data_for_symbol(signal_symbol, dataset)
    else:
        signal_data = _fetch_stock_data_for_signals(dataset)
    if signal_data is None:
        return _result(
            "Custom signals require stock price data but yfinance is not "
            "installed or the fetch failed. Install yfinance "
            "(`pip install yfinance`) and try again.",
        )

    flagged_frames = []
    symbols = signal_data["underlying_symbol"].unique()
    errors = []

    for sym in symbols:
        sym_df = signal_data[signal_data["underlying_symbol"] == sym].copy()
        sym_df = sym_df.sort_values("quote_date").reset_index(drop=True)

        exec_globals = {
            "__builtins__": _SAFE_BUILTINS,
            "pd": pd,
            "np": np,
            "df": sym_df,
        }
        exec_locals: dict = {}

        try:
            exec(code, exec_globals, exec_locals)  # noqa: S102
        except Exception as exc:
            errors.append(f"{sym}: {type(exc).__name__}: {exc}")
            continue

        # Check exec_locals first (simple top-level assignments), then
        # exec_globals (signal assigned inside a function that writes to
        # the global scope).  Use `is None` — not `or` — because a
        # pandas Series raises ValueError on truthiness tests.
        sig = exec_locals.get("signal")
        if sig is None:
            sig = exec_globals.get("signal")
        if sig is None:
            errors.append(
                f"{sym}: Code did not produce a variable named `signal`. "
                "Your code must assign a boolean Series to `signal`."
            )
            continue

        if not isinstance(sig, pd.Series):
            errors.append(
                f"{sym}: `signal` must be a pandas Series, got {type(sig).__name__}."
            )
            continue

        if len(sig) != len(sym_df):
            errors.append(
                f"{sym}: `signal` length ({len(sig)}) does not match "
                f"DataFrame length ({len(sym_df)}). Ensure `signal` is "
                f"derived from `df` without changing its length."
            )
            continue

        # Coerce to bool, filling NaN with False
        sig = sig.fillna(False).astype(bool)

        flagged = sym_df.loc[sig.values, ["underlying_symbol", "quote_date"]].copy()
        if not flagged.empty:
            flagged_frames.append(flagged)

    # If ALL symbols failed, return error so the LLM can retry.
    # If only some failed, proceed with partial results and warn.
    if errors and not flagged_frames:
        error_detail = "\n".join(errors)
        return _result(
            f"Custom signal code failed:\n{error_detail}\n\n"
            "Fix the code and try again. The code must assign a boolean "
            "Series named `signal` from DataFrame `df`."
        )

    if not flagged_frames:
        combined = pd.DataFrame(columns=["underlying_symbol", "quote_date"])
    else:
        combined = pd.concat(flagged_frames, ignore_index=True)

    # Cross-symbol: remap signal symbol to options dataset symbol(s).
    # build_custom_signal always fetches stock data, so signal_symbol
    # always means the data came from a different ticker.
    if signal_symbol and not combined.empty:
        combined = _remap_cross_symbol_dates(combined, dataset)

    # Intersect with options dates
    valid_dates = _intersect_with_options_dates(combined, dataset)

    # Store in signals dict
    updated_signals = dict(signals)
    updated_signals[slot] = valid_dates

    desc = arguments.get("description") or "custom code"
    n_dates, syms, date_min, date_max = _signal_slot_summary(valid_dates)
    summary = f"Signal '{slot}' built: {desc} → {n_dates} valid dates for {syms}"
    display_lines = [summary]
    if errors:
        display_lines.append(
            f"WARNING: Code failed for {len(errors)} symbol(s): " + "; ".join(errors)
        )
    if n_dates > 0:
        display_lines.append(f"Date range: {date_min} to {date_max}")
    else:
        opt_min = dataset["quote_date"].min().date()
        opt_max = dataset["quote_date"].max().date()
        if combined.empty:
            display_lines.append(
                "WARNING: The custom signal never triggered for any symbol. "
                "Check your code logic or try different conditions."
            )
        else:
            suggestion = _empty_signal_suggestion(combined, opt_min, opt_max)
            display_lines.append(
                f"WARNING: No signal dates overlap the options data "
                f"({opt_min} to {opt_max}). {suggestion}"
            )
    display = "\n".join(display_lines)
    return _result(summary, user_display=display, sigs=updated_signals)


@_register("preview_signal")
def _handle_preview_signal(arguments, dataset, signals, datasets, results, _result):
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
    n_dates, symbols, date_min, date_max = _signal_slot_summary(valid_dates)
    if n_dates == 0:
        return _result(f"Signal '{slot}' has 0 valid dates.")
    summary = (
        f"Signal '{slot}': {n_dates} valid dates, "
        f"symbols={symbols}, range={date_min} to {date_max}"
    )
    # Show a sample of dates in the user display
    display = f"{summary}\n\n{_df_to_markdown(valid_dates, max_rows=30)}"
    return _result(summary, user_display=display)


@_register("list_signals")
def _handle_list_signals(arguments, dataset, signals, datasets, results, _result):
    if not signals:
        return _result("No signals built yet.")

    rows = []
    for slot, valid_dates in signals.items():
        n_dates, symbols, date_min, date_max = _signal_slot_summary(valid_dates)
        rows.append(
            {
                "slot": slot,
                "dates": n_dates,
                "symbols": ", ".join(str(s) for s in symbols),
                "date_from": str(date_min or ""),
                "date_to": str(date_max or ""),
            }
        )

    result_df = pd.DataFrame(rows)
    llm_lines = [f"list_signals: {len(rows)} signal slot(s)"]
    for r in rows:
        if r["dates"] > 0:
            llm_lines.append(
                f"'{r['slot']}': {r['dates']} dates, symbols={r['symbols']}, "
                f"range={r['date_from']} to {r['date_to']}"
            )
        else:
            llm_lines.append(f"'{r['slot']}': 0 dates")
    llm_summary = "\n".join(llm_lines)
    user_display = f"### Signal Slots ({len(rows)})\n\n{_df_to_markdown(result_df)}"
    return _result(llm_summary, user_display=user_display)


@_register("fetch_stock_data")
def _handle_fetch_stock_data(arguments, dataset, signals, datasets, results, _result):
    try:
        import yfinance as yf  # noqa: F401
    except ImportError:
        return _result("yfinance is not installed. Run: pip install yfinance")

    symbol = arguments["symbol"].upper()

    try:
        cached = _yf_cache.read(_YF_CACHE_CATEGORY, symbol)
        cached = _yf_fetch_and_cache(symbol, cached, date.today())
    except (OSError, ValueError) as exc:
        _log.warning("yfinance fetch failed for %s: %s", symbol, exc)
        cached = _yf_cache.read(_YF_CACHE_CATEGORY, symbol)

    if cached is None or cached.empty:
        return _result(f"No stock data found for {symbol}.")

    df = cached.rename(columns={"date": "quote_date"})
    d_min = pd.to_datetime(df["quote_date"]).dt.date.min()
    d_max = pd.to_datetime(df["quote_date"]).dt.date.max()
    summary = (
        f"Fetched {len(df):,} daily price records for {symbol}. "
        f"Date range: {d_min} to {d_max}."
    )
    display = f"{summary}\n\nFirst 10 rows:\n{_df_to_markdown(df.head(10))}"
    return _result(summary, user_display=display)
