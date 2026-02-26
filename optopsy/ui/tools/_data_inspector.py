"""Data inspection tool handlers: preview_data, describe_data, suggest_strategy_params."""

import json as _json

import pandas as pd

from optopsy.strategies._helpers import (
    _DEFAULT_ATM_DELTA,
    _DEFAULT_DEEP_ITM_DELTA,
    _DEFAULT_DELTA,
    _DEFAULT_ITM_WING_DELTA,
    _DEFAULT_OTM_DELTA,
    _DEFAULT_OTM_WING_DELTA,
)

from ._executor import _register, _require_dataset
from ._helpers import _df_summary, _df_to_markdown
from ._schemas import CALENDAR_STRATEGIES


@_register("preview_data")
def _handle_preview_data(arguments, dataset, signals, datasets, results, _result):
    active_ds, label, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None
    summary = _df_summary(active_ds, label)

    try:
        rows = max(int(arguments.get("rows", 5) or 5), 1)
    except (TypeError, ValueError):
        return _result("Invalid 'rows' parameter; it must be a positive integer.")
    raw_sample = arguments.get("sample", False)
    sample = raw_sample is True or (
        isinstance(raw_sample, str) and raw_sample.strip().lower() == "true"
    )
    position = arguments.get("position", "head")
    if position not in ("head", "tail"):
        return _result(
            f"Invalid position '{position}'. Allowed values are 'head' or 'tail'."
        )

    if sample:
        preview = active_ds.sample(min(rows, len(active_ds)))
        pos_label = f"Random sample of {len(preview)} rows"
    elif position == "tail":
        preview = active_ds.tail(rows)
        pos_label = f"Last {len(preview)} rows"
    else:
        preview = active_ds.head(rows)
        pos_label = f"First {len(preview)} rows"

    display = f"{summary}\n\n{pos_label}:\n{_df_to_markdown(preview)}"
    return _result(summary, user_display=display)


@_register("describe_data")
def _handle_describe_data(arguments, dataset, signals, datasets, results, _result):
    active_ds, label, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None

    columns = arguments.get("columns")
    if isinstance(columns, str):
        columns = [columns]
    elif columns is not None and not isinstance(columns, (list, tuple)):
        return _result("`columns` must be a string or a list of strings.")
    if columns:
        if not all(isinstance(c, str) for c in columns):
            return _result("All entries in `columns` must be strings.")
        missing = [c for c in columns if c not in active_ds.columns]
        if missing:
            return _result(
                f"Columns not found: {missing}. Available: {list(active_ds.columns)}"
            )
        df = active_ds[columns]
    else:
        df = active_ds

    # Shape
    shape = f"{len(df):,} rows x {len(df.columns)} columns"

    # Dtypes
    dtype_lines = [f"| {c} | {df[c].dtype} |" for c in df.columns]
    dtype_table = "| Column | Dtype |\n|---|---|\n" + "\n".join(dtype_lines)

    # NaN counts
    nan_counts = df.isna().sum()
    nan_nonzero = nan_counts[nan_counts > 0]
    if nan_nonzero.empty:
        nan_section = "No missing values."
    else:
        nan_lines = [f"| {c} | {n:,} |" for c, n in nan_nonzero.items()]
        nan_section = "| Column | Missing |\n|---|---|\n" + "\n".join(nan_lines)

    # Numeric describe
    numeric_cols = df.select_dtypes(include="number")
    if len(numeric_cols.columns) > 0:
        desc = numeric_cols.describe().round(4)
        numeric_section = _df_to_markdown(
            desc.reset_index().rename(columns={"index": "stat"})
        )
    else:
        numeric_section = "No numeric columns."

    # Categorical distributions for key columns
    cat_cols = [c for c in ("underlying_symbol", "option_type") if c in df.columns]
    cat_sections = []
    for c in cat_cols:
        vc = df[c].value_counts().head(10)
        vc_lines = [f"| {v} | {cnt:,} |" for v, cnt in vc.items()]
        cat_sections.append(
            f"**{c}** value_counts (top 10)\n\n"
            f"| Value | Count |\n|---|---|\n" + "\n".join(vc_lines)
        )

    # Date column ranges
    date_cols = [c for c in ("quote_date", "expiration") if c in df.columns]
    date_sections = []
    for c in date_cols:
        dates = pd.to_datetime(df[c], errors="coerce").dropna()
        if dates.empty:
            date_sections.append(f"**{c}**: no valid dates")
        else:
            date_sections.append(
                f"**{c}**: {dates.min().date()} to {dates.max().date()} "
                f"({dates.dt.date.nunique():,} unique)"
            )

    # LLM summary (compact, bounded to avoid blowing up context)
    _MAX_NAN_COLS = 10
    _MAX_NUMERIC_COLS = 10

    def _fmt_stat(value):
        if pd.isna(value):
            return "NaN"
        try:
            return f"{value:.4f}"
        except (TypeError, ValueError):
            return str(value)

    llm_parts = [f"describe_data({label}): {shape}"]
    if not nan_nonzero.empty:
        nan_sorted = nan_nonzero.sort_values(ascending=False)
        top_nan = nan_sorted.head(_MAX_NAN_COLS)
        llm_parts.append(f"NaN columns: {dict(top_nan)}")
        if len(nan_sorted) > _MAX_NAN_COLS:
            llm_parts.append(
                f"... and {len(nan_sorted) - _MAX_NAN_COLS} more NaN columns"
            )
    if len(numeric_cols.columns) > 0:
        for c in list(numeric_cols.columns)[:_MAX_NUMERIC_COLS]:
            col = numeric_cols[c]
            llm_parts.append(
                f"{c}: min={_fmt_stat(col.min())}, max={_fmt_stat(col.max())}, "
                f"mean={_fmt_stat(col.mean())}"
            )
        if len(numeric_cols.columns) > _MAX_NUMERIC_COLS:
            remaining = len(numeric_cols.columns) - _MAX_NUMERIC_COLS
            llm_parts.append(f"... and {remaining} more numeric columns")
    for d in date_sections:
        llm_parts.append(d)
    llm_summary = "\n".join(llm_parts)

    # User display (full markdown)
    display_parts = [
        f"### Dataset: {label}\n",
        f"**Shape:** {shape}\n",
        f"**Data Types**\n\n{dtype_table}\n",
        f"**Missing Values**\n\n{nan_section}\n",
        f"**Numeric Summary**\n\n{numeric_section}\n",
    ]
    for cs in cat_sections:
        display_parts.append(cs + "\n")
    for ds in date_sections:
        display_parts.append(ds + "\n")

    user_display = "\n".join(display_parts)
    return _result(llm_summary, user_display=user_display)


@_register("suggest_strategy_params")
def _handle_suggest_strategy_params(
    arguments, dataset, signals, datasets, results, _result
):
    active_ds, _, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None

    strategy_name = arguments.get("strategy_name")

    # DTE distribution — compute without copying the full dataset
    dte_series = (
        pd.to_datetime(active_ds["expiration"])
        - pd.to_datetime(active_ds["quote_date"])
    ).dt.days.dropna()
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

    # Delta distribution — only include rows that have a delta column
    delta_series = (
        active_ds["delta"].dropna()
        if "delta" in active_ds.columns
        else pd.Series(dtype="float64")
    )
    if not delta_series.empty:
        delta_pcts = {
            k: round(float(delta_series.abs().quantile(q)), 4)
            for k, q in [
                ("p10", 0.10),
                ("p25", 0.25),
                ("p50", 0.50),
                ("p75", 0.75),
                ("p90", 0.90),
            ]
        }
        delta_stats = {
            "min": round(float(delta_series.abs().min()), 4),
            **delta_pcts,
            "max": round(float(delta_series.abs().max()), 4),
        }
    else:
        delta_stats = {}

    has_delta = bool(delta_stats)

    # Base recommendations
    recommended: dict = {
        "max_entry_dte": dte_stats["p75"],
        "exit_dte": max(0, dte_stats["p10"]),
    }
    strategy_note = ""

    # Strategy-specific overrides (DTE + delta targets)
    if strategy_name in CALENDAR_STRATEGIES:
        recommended = {
            "front_dte_min": max(10, dte_stats["p10"]),
            "front_dte_max": min(45, dte_stats["p50"]),
            "back_dte_min": min(50, dte_stats["p75"]),
            "back_dte_max": min(120, dte_stats["p90"]),
        }
        strategy_note = (
            "Calendar strategy — use front/back DTE instead of max_entry_dte. "
            "Delta defaults apply per-leg automatically."
        )
    elif strategy_name in {
        "iron_condor",
        "reverse_iron_condor",
    }:
        recommended["max_entry_dte"] = min(45, dte_stats["p75"])
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_OTM_DELTA
            recommended["leg2_delta"] = _DEFAULT_DELTA
            recommended["leg3_delta"] = _DEFAULT_DELTA
            recommended["leg4_delta"] = _DEFAULT_OTM_DELTA
        strategy_note = (
            "Iron condor — outer legs at 0.10 delta (wings), inner legs at 0.30 delta. "
            "Typically works best in the 20-45 DTE range."
        )
    elif strategy_name in {
        "iron_butterfly",
        "reverse_iron_butterfly",
    }:
        recommended["max_entry_dte"] = min(45, dte_stats["p75"])
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_OTM_DELTA
            recommended["leg2_delta"] = _DEFAULT_ATM_DELTA
            recommended["leg3_delta"] = _DEFAULT_ATM_DELTA
            recommended["leg4_delta"] = _DEFAULT_OTM_DELTA
        strategy_note = (
            "Iron butterfly — outer legs at 0.10 delta, inner legs at 0.50 (ATM). "
            "Typically works best in the 20-45 DTE range."
        )
    elif strategy_name and "butterfly" in strategy_name:
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_ITM_WING_DELTA
            recommended["leg2_delta"] = _DEFAULT_ATM_DELTA
            recommended["leg3_delta"] = _DEFAULT_OTM_WING_DELTA
        strategy_note = (
            "Butterfly — ITM wing at 0.40, body at 0.50 (ATM), OTM wing at 0.10."
        )
    elif strategy_name and "spread" in strategy_name:
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_ATM_DELTA
            recommended["leg2_delta"] = _DEFAULT_OTM_DELTA
        strategy_note = (
            "Vertical spread — long leg at 0.50 (ATM), short leg at 0.10 (OTM)."
        )
    elif strategy_name and "straddle" in strategy_name:
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_ATM_DELTA
            recommended["leg2_delta"] = _DEFAULT_ATM_DELTA
        strategy_note = "Straddle — both legs at 0.50 delta (ATM)."
    elif strategy_name and "strangle" in strategy_name:
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_DELTA
            recommended["leg2_delta"] = _DEFAULT_DELTA
        strategy_note = "Strangle — both legs at 0.30 delta."
    elif strategy_name and "covered_call" in strategy_name:
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_DEEP_ITM_DELTA
            recommended["leg2_delta"] = _DEFAULT_DELTA
        strategy_note = (
            "Covered call — deep ITM call (0.80 delta) + 0.30 delta short call."
        )
    elif strategy_name and "protective_put" in strategy_name:
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_DEEP_ITM_DELTA
            recommended["leg2_delta"] = _DEFAULT_DELTA
        strategy_note = (
            "Protective put — deep ITM put (0.80 delta) + 0.30 delta long put."
        )
    elif strategy_name:
        # Single-leg strategies
        if has_delta:
            recommended["leg1_delta"] = _DEFAULT_DELTA
        strategy_note = "Default delta target: 0.30 (range 0.20-0.40)."

    if not has_delta and strategy_name:
        delta_warning = (
            "WARNING: Dataset has no delta column. Delta-based strike selection "
            "will not work. To use delta targeting, load data that includes "
            "a 'delta' column."
        )
        strategy_note = (
            f"{delta_warning} {strategy_note}" if strategy_note else delta_warning
        )

    reco_json = _json.dumps(recommended, indent=2)
    label = f" for `{strategy_name}`" if strategy_name else ""

    dte_rows = "\n".join(f"| {k} | {v} |" for k, v in dte_stats.items())

    llm_parts = [
        f"suggest_strategy_params{label}",
        f"DTE distribution: {dte_stats}",
    ]
    display_parts = [
        f"### Parameter Suggestions{label}\n",
        f"**DTE Distribution** ({len(dte_series):,} options)\n",
        f"| Percentile | DTE |\n|---|---|\n{dte_rows}\n",
    ]

    if delta_stats:
        delta_rows = "\n".join(f"| {k} | {v:.4f} |" for k, v in delta_stats.items())
        llm_parts.append(f"Delta (abs) distribution: {delta_stats}")
        display_parts.append(
            f"**Delta (abs) Distribution** ({len(delta_series):,} options)\n\n"
            f"| Percentile | |Delta| |\n|---|---|\n{delta_rows}\n"
        )

    llm_parts.append(f"Recommended: {recommended}")
    if strategy_note:
        llm_parts.append(f"Note: {strategy_note}")

    display_parts.append(
        f"**Recommended starting parameters:**\n```json\n{reco_json}\n```"
    )
    if strategy_note:
        display_parts.append(f"\n*{strategy_note}*")

    llm_summary = "\n".join(llm_parts)
    user_display = "\n".join(display_parts)
    return _result(llm_summary, user_display=user_display)
