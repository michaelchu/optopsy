"""Result management tool handlers: compare_results, list_results, inspect_cache, clear_cache, query_results."""

import pandas as pd

from ..providers.cache import ParquetCache
from ..providers.result_store import ResultStore
from ._executor import _fmt_pf, _register
from ._helpers import _df_to_markdown, _select_results


@_register("inspect_cache")
def _handle_inspect_cache(arguments, dataset, signals, datasets, results, _result):
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
        date_col = next((c for c in ("quote_date", "date") if c in df.columns), None)
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


@_register("clear_cache")
def _handle_clear_cache(arguments, dataset, signals, datasets, results, _result):
    symbol = arguments.get("symbol", "").strip().upper() or None
    cache = ParquetCache()
    target = f" for {symbol}" if symbol else ""
    size_before = cache.total_size_bytes()
    count = cache.clear(symbol)
    size_after = cache.total_size_bytes()
    freed_mb = round((size_before - size_after) / 1_048_576, 2)

    if count == 0:
        return _result(f"No cached files found{target}. Nothing to clear.")

    summary = f"Cleared {count} cached file(s){target}. Freed {freed_mb} MB."
    return _result(summary)


@_register("compare_results")
def _handle_compare_results(arguments, dataset, signals, datasets, results, _result):
    if not results:
        return _result(
            "No strategy runs in this session yet. "
            "Use run_strategy or scan_strategies first, then compare_results."
        )

    selected, sel_err = _select_results(results, arguments.get("result_keys"))
    if sel_err:
        return _result(sel_err)
    assert selected is not None

    if len(selected) < 2:
        return _result(
            "Need at least 2 results to compare. "
            f"Currently have {len(selected)}. Run more strategies first."
        )

    sort_by = arguments.get("sort_by", "mean_return")
    include_chart = arguments.get("include_chart", True)
    # Build comparison rows from both strategy and simulation results
    rows = []
    for key, entry in selected.items():
        is_sim = entry.get("type") == "simulation"
        if is_sim:
            s = entry.get("summary", {})
            row = {
                "label": key,
                "strategy": entry.get("strategy", "?"),
                "type": "simulation",
                "count": s.get("total_trades", 0),
                "mean_return": (
                    round(s["total_return"], 4)
                    if s.get("total_return") is not None
                    else None
                ),
                "win_rate": s.get("win_rate"),
                "max_drawdown": s.get("max_drawdown"),
                "profit_factor": s.get("profit_factor"),
            }
        else:
            pct_mean = entry.get("mean_return")
            pct_std = entry.get("std")
            win_rate = entry.get("win_rate")
            count = entry.get("count", 0)

            sharpe = None
            if pct_mean is not None and pct_std and pct_std > 0:
                sharpe = round(float(pct_mean / pct_std), 4)

            row = {
                "label": key,
                "strategy": entry.get("strategy", "?"),
                "type": "backtest",
                "count": count,
                "mean_return": pct_mean,
                "std": pct_std,
                "win_rate": win_rate,
                "sharpe": sharpe,
                "max_drawdown": None,
                "profit_factor": entry.get("profit_factor"),
            }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Determine valid sort column
    valid_sort_cols = [
        "mean_return",
        "win_rate",
        "sharpe",
        "max_drawdown",
        "profit_factor",
        "count",
    ]
    if sort_by not in valid_sort_cols or sort_by not in df.columns:
        sort_by = "mean_return"

    ascending = False
    if sort_by in df.columns and df[sort_by].notna().any():
        df = df.sort_values(sort_by, ascending=ascending, na_position="last")
    df = df.reset_index(drop=True)

    # Build verdict row — best value for each metric
    verdict = {}
    metric_cols = {
        "mean_return": "highest",
        "win_rate": "highest",
        "sharpe": "highest",
        "count": "highest",
        "max_drawdown": "lowest_abs",
        "profit_factor": "highest",
    }
    for col, direction in metric_cols.items():
        if col not in df.columns or df[col].isna().all():
            continue
        valid = df[df[col].notna()]
        if valid.empty:
            continue
        if direction == "lowest_abs":
            best_idx = valid[col].abs().idxmin()
        else:
            best_idx = valid[col].idxmax()
        verdict[col] = valid.loc[best_idx, "label"]

    # Format display columns
    display_cols = ["label", "strategy", "type", "count"]
    for c in [
        "mean_return",
        "std",
        "win_rate",
        "sharpe",
        "max_drawdown",
        "profit_factor",
    ]:
        if c in df.columns and df[c].notna().any():
            display_cols.append(c)
    display_df = df[[c for c in display_cols if c in df.columns]].copy()

    # Format percentage columns for user display using config dict
    _COMPARISON_FORMATS = {
        "mean_return": ".4f",
        "std": ".4f",
        "win_rate": ".2%",
        "max_drawdown": ".2%",
        "sharpe": ".4f",
        "profit_factor": ".2f",
    }
    format_df = display_df.copy()
    for col, fmt in _COMPARISON_FORMATS.items():
        if col in format_df.columns:
            format_df[col] = format_df[col].apply(
                lambda x, f=fmt: f"{x:{f}}" if pd.notna(x) else "—"
            )

    table = _df_to_markdown(format_df, max_rows=100)

    # Build verdict line
    if verdict:
        verdict_parts = []
        for metric, label in verdict.items():
            verdict_parts.append(f"**{metric}**: {label}")
        verdict_line = "**Best on each metric:** " + " · ".join(verdict_parts)
    else:
        verdict_line = ""

    # LLM summary — compact, using metric config list
    _LLM_METRICS = [
        ("mean_return", "mean", ".4f"),
        ("win_rate", "wr", ".2%"),
        ("sharpe", "sharpe", ".4f"),
        ("max_drawdown", "mdd", ".2%"),
        ("profit_factor", "pf", ".2f"),
    ]
    llm_lines = [f"compare_results: {len(df)} results compared, sorted by {sort_by}"]
    for _, row in df.head(5).iterrows():
        parts = [str(row["label"])]
        for col, abbrev, fmt in _LLM_METRICS:
            if pd.notna(row.get(col)):
                parts.append(f"{abbrev}={row[col]:{fmt}}")
        llm_lines.append(" | ".join(parts))
    if verdict:
        llm_lines.append(
            "Best: " + ", ".join(f"{m}→{lbl}" for m, lbl in verdict.items())
        )
    llm_summary = "\n".join(llm_lines)

    # User display
    user_display = (
        f"### Strategy Comparison ({len(df)} results)\n\n"
        f"*Sorted by {sort_by}*\n\n"
        f"{table}\n\n"
        f"{verdict_line}"
    )

    # Optional grouped bar chart
    chart_figure = None
    if include_chart and len(df) >= 2:
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            chart_metrics = []
            for m in ["mean_return", "win_rate", "sharpe", "profit_factor"]:
                if m in df.columns and df[m].notna().any():
                    chart_metrics.append(m)

            if chart_metrics:
                labels = df["label"].tolist()
                short_labels = [
                    (lbl[:30] + "\u2026") if len(lbl) > 30 else lbl for lbl in labels
                ]

                fig = make_subplots(
                    rows=len(chart_metrics),
                    cols=1,
                    subplot_titles=chart_metrics,
                    vertical_spacing=0.08,
                )
                for i, metric in enumerate(chart_metrics, start=1):
                    fig.add_trace(
                        go.Bar(
                            name=metric,
                            x=short_labels,
                            y=df[metric].tolist(),
                            text=[
                                f"{v:.4f}" if pd.notna(v) else "" for v in df[metric]
                            ],
                            textposition="auto",
                            showlegend=False,
                        ),
                        row=i,
                        col=1,
                    )
                fig.update_layout(
                    template="plotly_white",
                    width=max(600, len(df) * 120),
                    height=300 * len(chart_metrics),
                    margin=dict(l=40, r=20, t=30, b=40),
                )
                chart_figure = fig
        except ImportError:
            pass  # plotly not available, skip chart

    return _result(llm_summary, user_display=user_display, chart_figure=chart_figure)


@_register("list_results")
def _handle_list_results(arguments, dataset, signals, datasets, results, _result):
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


@_register("query_results")
def _handle_query_results(arguments, dataset, signals, datasets, results, _result):
    result_key = arguments.get("result_key")
    store = ResultStore()

    # List mode — no result_key specified
    if not result_key:
        if not results:
            # Fall back to global store
            all_entries = store.list_all()
            if not all_entries:
                return _result(
                    "No results available. Run a strategy or simulation first."
                )
            lines = ["Available cached results (global store):"]
            for key, meta in all_entries.items():
                display = meta.get("display_key", key[:12])
                rtype = meta.get("type", "?")
                lines.append(f"  {display} ({rtype})")
            return _result("\n".join(lines))

        lines = [f"Session has {len(results)} result(s):"]
        for key, entry in results.items():
            rtype = entry.get("type", "strategy")
            parts = [f"  {key} ({rtype})"]
            if rtype == "simulation":
                s = entry.get("summary", {})
                if s:
                    parts.append(
                        f"  trades={s.get('total_trades', '?')}, "
                        f"return={s.get('total_return', '?')}"
                    )
            else:
                mr = entry.get("mean_return")
                wr = entry.get("win_rate")
                if mr is not None:
                    parts.append(f"mean={mr:.4f}")
                if wr is not None:
                    parts.append(f"wr={wr:.2%}")
            lines.append(" | ".join(parts))
        return _result("\n".join(lines))

    # Query mode — result_key specified
    # Look up _cache_key from session results
    entry = results.get(result_key)
    cache_key = entry.get("_cache_key") if entry else None

    if not cache_key:
        # Try to find by display_key in global store
        for k, meta in store.list_all().items():
            if meta.get("display_key") == result_key:
                cache_key = k
                break

    if not cache_key:
        available = list(results.keys()) if results else []
        return _result(
            f"Result key '{result_key}' not found. "
            f"Available: {available or 'none — run a strategy first'}"
        )

    df = store.read(cache_key)
    if df is None or df.empty:
        return _result(f"No data found for '{result_key}' (cache key: {cache_key}).")

    # Apply column selection
    columns = arguments.get("columns")
    if columns:
        valid_cols = [c for c in columns if c in df.columns]
        if not valid_cols:
            return _result(
                f"None of the requested columns {columns} exist. "
                f"Available: {list(df.columns)}"
            )
        df = df[valid_cols]

    # Apply filter
    filter_col = arguments.get("filter_column")
    filter_op = arguments.get("filter_op")
    filter_val = arguments.get("filter_value")
    filter_parts = [filter_col, filter_op, filter_val is not None]
    if any(filter_parts) and not all(filter_parts):
        missing = []
        if not filter_col:
            missing.append("filter_column")
        if not filter_op:
            missing.append("filter_op")
        if filter_val is None:
            missing.append("filter_value")
        return _result(
            f"Incomplete filter: missing {', '.join(missing)}. "
            "All three (filter_column, filter_op, filter_value) are required."
        )
    if filter_col and filter_op and filter_val is not None:
        if filter_col not in df.columns:
            return _result(
                f"Filter column '{filter_col}' not found. Available: {list(df.columns)}"
            )
        col = df[filter_col]
        try:
            if filter_op == "contains":
                mask = col.astype(str).str.contains(filter_val, case=False, na=False)
            else:
                # Cast filter_value to column dtype for numeric comparisons
                try:
                    val = col.dtype.type(filter_val)
                except (ValueError, TypeError):
                    try:
                        val = float(filter_val)
                    except (ValueError, TypeError):
                        return _result(
                            f"Invalid filter_value '{filter_val}' for column "
                            f"'{filter_col}' (dtype {col.dtype})."
                        )
                ops = {
                    "gt": col > val,
                    "lt": col < val,
                    "eq": col == val,
                    "gte": col >= val,
                    "lte": col <= val,
                }
                mask = ops.get(filter_op)
                if mask is None:
                    return _result(f"Unknown filter_op '{filter_op}'.")
            df = df[mask]
        except Exception as e:
            return _result(f"Filter error: {e}")

    # Apply sort
    sort_by = arguments.get("sort_by")
    ascending = arguments.get("ascending", False)
    if sort_by:
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=ascending, na_position="last")
        else:
            return _result(
                f"Sort column '{sort_by}' not found. Available: {list(df.columns)}"
            )

    # Apply head
    head = arguments.get("head")
    if head:
        df = df.head(head)

    df = df.reset_index(drop=True)
    table = _df_to_markdown(df)
    llm_summary = (
        f"query_results({result_key}): {len(df)} rows, columns={list(df.columns)}"
    )
    user_display = f"### Query: {result_key}\n\n{table}"
    return _result(llm_summary, user_display=user_display)


@_register("summarize_session")
def _handle_summarize_session(arguments, dataset, signals, datasets, results, _result):
    sections_llm: list[str] = ["summarize_session:"]
    sections_display: list[str] = ["## Session Summary"]

    # --- Datasets ---
    if datasets:
        ds_lines_llm: list[str] = []
        ds_lines_display: list[str] = []
        for name, df in datasets.items():
            # Default to unknown; only compute a range when we have valid dates
            date_range = "unknown date range"
            date_col = next(
                (c for c in ("quote_date", "date") if c in df.columns), None
            )
            if date_col and not df.empty:
                dates = pd.to_datetime(df[date_col])
                valid_dates = dates.dropna()
                if not valid_dates.empty:
                    date_min = valid_dates.min()
                    date_max = valid_dates.max()
                    if pd.notna(date_min) and pd.notna(date_max):
                        date_range = f"{date_min.date()} to {date_max.date()}"
            ds_lines_llm.append(
                f"  {name}: {len(df):,} rows, {date_range}"
            )
            ds_lines_display.append(
                f"- **{name}**: {len(df):,} rows, {date_range}"
            )
        sections_llm.append(
            f"Datasets loaded ({len(datasets)}):\n" + "\n".join(ds_lines_llm)
        )
        sections_display.append(
            f"### Datasets Loaded ({len(datasets)})\n\n" + "\n".join(ds_lines_display)
        )
    else:
        sections_llm.append("Datasets loaded: none")
        sections_display.append("### Datasets Loaded\n\n*No datasets loaded.*")

    # --- Strategy runs ---
    backtest_results = {k: v for k, v in results.items() if v.get("type") != "simulation"}
    sim_results = {k: v for k, v in results.items() if v.get("type") == "simulation"}

    if backtest_results:
        bt_rows = []
        for key, entry in backtest_results.items():
            mr = entry.get("mean_return")
            wr = entry.get("win_rate")
            pf = entry.get("profit_factor")
            bt_rows.append({
                "key": key,
                "strategy": entry.get("strategy", "?"),
                "max_entry_dte": entry.get("max_entry_dte", "?"),
                "exit_dte": entry.get("exit_dte", "?"),
                "count": entry.get("count", 0),
                # Keep raw numeric values for proper sorting
                "mean_return": mr,
                "win_rate": wr,
                "profit_factor": pf,
            })
        bt_df = pd.DataFrame(bt_rows)
        # Sort by mean_return descending (best first), consistent with
        # list_results and compare_results.
        if "mean_return" in bt_df.columns and bt_df["mean_return"].notna().any():
            bt_df = bt_df.sort_values(
                "mean_return", ascending=False, na_position="last"
            )
        bt_df = bt_df.reset_index(drop=True)

        # Build a formatted display copy
        bt_display_df = bt_df.copy()
        if "mean_return" in bt_display_df.columns:
            bt_display_df["mean_return"] = bt_display_df["mean_return"].apply(
                lambda v: f"{v:.4f}" if pd.notna(v) else "—"
            )
        if "win_rate" in bt_display_df.columns:
            bt_display_df["win_rate"] = bt_display_df["win_rate"].apply(
                lambda v: f"{v:.2%}" if pd.notna(v) else "—"
            )
        if "profit_factor" in bt_display_df.columns:
            bt_display_df["profit_factor"] = bt_display_df["profit_factor"].apply(
                lambda v: _fmt_pf(v) if v is not None else "—"
            )

        bt_table = _df_to_markdown(bt_display_df, max_rows=100)
        sections_llm.append(
            f"Strategy backtests ({len(backtest_results)}):\n"
            + "\n".join(
                f"  {r['key']}: strategy={r['strategy']}, "
                f"mean={r['mean_return']}, wr={r['win_rate']}"
                for _, r in bt_display_df.iterrows()
            )
        )
        sections_display.append(
            f"### Strategy Backtests ({len(backtest_results)})\n\n{bt_table}"
        )
    else:
        sections_llm.append("Strategy backtests: none")
        sections_display.append(
            "### Strategy Backtests\n\n*No strategy backtests run.*"
        )

    # --- Simulations ---
    if sim_results:
        sim_lines_llm: list[str] = []
        sim_lines_display: list[str] = []
        for key, entry in sim_results.items():
            s = entry.get("summary", {})
            total_trades = s.get("total_trades")
            total_return = s.get("total_return")
            win_rate = s.get("win_rate")
            profit_factor = s.get("profit_factor")
            trades_str = f"{int(total_trades):,}" if total_trades is not None else "?"
            return_str = f"{total_return:.2%}" if total_return is not None else "?"
            wr_str = f"{win_rate:.1%}" if win_rate is not None else "?"
            pf_str = _fmt_pf(profit_factor) if profit_factor is not None else "?"
            sim_lines_llm.append(
                f"  {key}: strategy={entry.get('strategy', '?')}, "
                f"trades={trades_str}, "
                f"return={return_str}, "
                f"win_rate={wr_str}"
            )
            sim_lines_display.append(
                f"- **{key}**: strategy={entry.get('strategy', '?')}, "
                f"trades={trades_str}, "
                f"total return={return_str}, "
                f"win rate={wr_str}, "
                f"profit factor={pf_str}"
            )
        sections_llm.append(
            f"Simulations ({len(sim_results)}):\n" + "\n".join(sim_lines_llm)
        )
        sections_display.append(
            f"### Simulations ({len(sim_results)})\n\n"
            + "\n".join(sim_lines_display)
        )
    else:
        sections_llm.append("Simulations: none")
        sections_display.append("### Simulations\n\n*No simulations run.*")

    # --- Signals ---
    if signals:
        sig_lines_llm: list[str] = []
        sig_lines_display: list[str] = []
        for slot, sig_df in signals.items():
            n_dates = len(sig_df) if sig_df is not None else 0
            sig_lines_llm.append(f"  {slot}: {n_dates} valid dates")
            sig_lines_display.append(f"- **{slot}**: {n_dates} valid dates")
        sections_llm.append(
            f"Signals built ({len(signals)}):\n" + "\n".join(sig_lines_llm)
        )
        sections_display.append(
            f"### Signals Built ({len(signals)})\n\n"
            + "\n".join(sig_lines_display)
        )
    else:
        sections_llm.append("Signals built: none")
        sections_display.append("### Signals Built\n\n*No signals built.*")

    llm_summary = "\n".join(sections_llm)
    user_display = "\n\n".join(sections_display)
    return _result(llm_summary, user_display=user_display)
