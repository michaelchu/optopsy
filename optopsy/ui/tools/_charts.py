"""Chart tool handlers: create_chart, plot_vol_surface, iv_term_structure."""

import logging
from typing import Any

import pandas as pd

from ..providers.result_store import ResultStore
from ._executor import _register, _require_dataset, _resolve_dataset
from ._helpers import (
    _IV_COLUMN_MISSING_MSG,
    _YF_CACHE_CATEGORY,
    _filter_by_quote_date,
    _resolve_result_key,
    _select_results,
    _yf_cache,
    resolve_price_column,
)

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data source resolution
# ---------------------------------------------------------------------------

_DATA_SOURCE_NAMES = "dataset, result, results, simulation, signal, or stock"


def _resolve_chart_data(
    data_source: str,
    arguments: dict[str, Any],
    dataset: pd.DataFrame | None,
    datasets: dict[str, pd.DataFrame],
    results: dict[str, dict],
    signals: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame | None, str, str | None]:
    """Resolve chart data source to a DataFrame.

    Returns ``(df, source_label, error_msg)``.  When ``error_msg`` is not
    None the caller should return it as a tool result immediately.
    """
    resolver = _DATA_SOURCE_RESOLVERS.get(data_source)
    if resolver is None:
        return (
            None,
            "",
            f"Unknown data_source '{data_source}'. Use: {_DATA_SOURCE_NAMES}.",
        )
    return resolver(arguments, dataset, datasets, results, signals)


def _resolve_ds_dataset(arguments, dataset, datasets, _results, _signals):
    ds_name = arguments.get("dataset_name")
    df = _resolve_dataset(ds_name, dataset, datasets)
    label = ds_name or "active dataset"
    if df is None:
        if ds_name and datasets:
            return (
                None,
                label,
                f"Dataset '{ds_name}' not found. Available: {list(datasets.keys())}",
            )
        return None, label, "No dataset loaded. Load data first."
    return df, label, None


def _resolve_ds_result(arguments, _dataset, _datasets, results, _signals):
    result_key = arguments.get("result_key")
    if not result_key:
        if not results:
            return None, "", "No strategy results available. Run a strategy first."
        result_key = list(results.keys())[-1]
    canonical = _resolve_result_key(results, result_key)
    if canonical is None:
        available = [entry.get("display_key", k) for k, entry in results.items()]
        return (
            None,
            result_key,
            f"Result '{result_key}' not found. Available: {available}",
        )
    entry = results[canonical]
    display_label = entry.get("display_key") or canonical
    return pd.DataFrame([entry]), display_label, None


def _resolve_ds_results(arguments, _dataset, _datasets, results, _signals):
    if not results:
        return None, "", "No strategy results available. Run strategies first."
    selected, sel_err = _select_results(results, arguments.get("result_keys"))
    if sel_err:
        return None, "results", sel_err
    assert selected is not None
    strat_entries = {k: v for k, v in selected.items() if v.get("type") != "simulation"}
    if not strat_entries:
        return None, "results", "No strategy results found (only simulations)."
    rows = [
        {**entry, "result_key": entry.get("display_key") or key}
        for key, entry in strat_entries.items()
    ]
    return pd.DataFrame(rows), "results", None


def _resolve_ds_simulation(arguments, _dataset, _datasets, results, _signals):
    sim_key = arguments.get("simulation_key")
    if not sim_key:
        sim_entries = [k for k, v in results.items() if v.get("type") == "simulation"]
        if not sim_entries:
            return None, "", "No simulations run yet. Use simulate first."
        sim_key = sim_entries[-1]
    canonical = _resolve_result_key(results, sim_key)
    entry = results.get(canonical, {}) if canonical else {}
    display_label = entry.get("display_key") or sim_key
    cache_key = entry.get("_cache_key")
    store = ResultStore()
    trade_log = store.read(cache_key) if cache_key else None
    if trade_log is None:
        return (
            None,
            display_label,
            f"Simulation '{display_label}' has no trade log data.",
        )
    return trade_log, display_label, None


def _resolve_ds_signal(arguments, _dataset, _datasets, _results, signals):
    slot = arguments.get("signal_slot")
    if not slot or slot not in signals:
        available = list(signals.keys()) if signals else []
        return (
            None,
            f"signal:{slot}",
            (
                f"Signal slot '{slot}' not found. "
                f"Available: {available or 'none — use build_signal first'}"
            ),
        )
    return signals[slot], f"signal:{slot}", None


def _resolve_ds_stock(arguments, _dataset, _datasets, _results, _signals):
    symbol = arguments.get("symbol", "").strip().upper()
    if not symbol:
        return None, "", "data_source='stock' requires a 'symbol' parameter."
    cached = _yf_cache.read(_YF_CACHE_CATEGORY, symbol)
    if cached is None or cached.empty:
        return (
            None,
            f"stock:{symbol}",
            f"No cached stock data for {symbol}. Use fetch_stock_data first.",
        )
    return cached, f"stock:{symbol}", None


_DATA_SOURCE_RESOLVERS = {
    "dataset": _resolve_ds_dataset,
    "result": _resolve_ds_result,
    "results": _resolve_ds_results,
    "simulation": _resolve_ds_simulation,
    "signal": _resolve_ds_signal,
    "stock": _resolve_ds_stock,
}


# ---------------------------------------------------------------------------
# Column validation helpers
# ---------------------------------------------------------------------------


def _check_xy_columns(
    df: pd.DataFrame, x: str | None, y: str | None, chart_type: str
) -> str | None:
    """Validate that x and y columns exist. Returns error message or None."""
    if not x or not y:
        return f"{chart_type.title()} chart requires 'x' and 'y' column names."
    missing = [c for c in (x, y) if c not in df.columns]
    if missing:
        return f"Column(s) {missing} not found. Available: {list(df.columns)}"
    return None


def _validate_columns(df: pd.DataFrame, columns: list[str]) -> str | None:
    """Return error message if any columns are missing from df, else None."""
    missing = [c for c in columns if c not in df.columns]
    if missing:
        return f"Column(s) {missing} not found. Available: {list(df.columns)}"
    return None


def _resolve_candlestick_columns(
    df: pd.DataFrame, x: str | None
) -> tuple[str | None, str | None]:
    """Validate OHLC columns and resolve the date column for candlestick charts.

    Returns ``(date_col, error_msg)``.  When ``error_msg`` is not None the
    caller should return it as a tool error.
    """
    date_col = x or next((c for c in ("date", "quote_date") if c in df.columns), None)
    if date_col is None or date_col not in df.columns:
        return None, (
            f"Candlestick chart needs a date column. Available: {list(df.columns)}"
        )
    for required in ("open", "high", "low", "close"):
        if required not in df.columns:
            return None, (
                f"Candlestick chart requires 'open', 'high', 'low', 'close' "
                f"columns. Missing: '{required}'. "
                f"Available: {list(df.columns)}"
            )
    return date_col, None


# ---------------------------------------------------------------------------
# Chart type builders — each returns (error_msg,) or None on success
# ---------------------------------------------------------------------------


def _build_multi_series(fig, go, df, arguments, x, y, color):
    """Build line/bar/scatter traces with optional y_columns and group_by."""
    chart_type = arguments["chart_type"]
    y_columns = arguments.get("y_columns")
    group_by_col = arguments.get("group_by")

    if y_columns and y:
        return "Provide either 'y' or 'y_columns', not both."

    effective_y_list: list[str] = y_columns if y_columns else ([y] if y else [])

    if not x:
        return f"{chart_type.title()} chart requires an 'x' column name."
    if not effective_y_list:
        return f"{chart_type.title()} chart requires 'y' or 'y_columns'."

    cols_to_check = [x] + effective_y_list
    if group_by_col:
        cols_to_check.append(group_by_col)
    col_err = _validate_columns(df, cols_to_check)
    if col_err:
        return col_err

    trace_builders = {
        "line": lambda tx, ty, n, uc: go.Scatter(
            x=tx,
            y=ty,
            mode="lines",
            name=n,
            line={"color": color} if uc and color else {},
        ),
        "bar": lambda tx, ty, n, uc: go.Bar(
            x=tx,
            y=ty,
            name=n,
            marker_color=color if uc else None,
        ),
        "scatter": lambda tx, ty, n, uc: go.Scatter(
            x=tx,
            y=ty,
            mode="markers",
            name=n,
            marker={"color": color} if uc and color else {},
        ),
    }
    build = trace_builders[chart_type]
    single_trace = not group_by_col and len(effective_y_list) == 1

    if group_by_col:
        for group_name, group_df in df.groupby(group_by_col):
            for y_col in effective_y_list:
                name = (
                    str(group_name)
                    if len(effective_y_list) == 1
                    else f"{group_name} — {y_col}"
                )
                fig.add_trace(build(group_df[x], group_df[y_col], name, False))
    else:
        for y_col in effective_y_list:
            fig.add_trace(build(df[x], df[y_col], y_col, single_trace))
    return None


def _build_histogram(fig, go, df, arguments, x, y, color):
    """Build a histogram trace."""
    col = x or y
    if not col:
        return "Histogram requires 'x' (or 'y') column name."
    col_err = _validate_columns(df, [col])
    if col_err:
        return col_err
    hist_kwargs: dict[str, Any] = {"x": df[col], "name": col}
    bins = arguments.get("bins")
    if bins:
        hist_kwargs["nbinsx"] = int(bins)
    if color:
        hist_kwargs["marker_color"] = color
    fig.add_trace(go.Histogram(**hist_kwargs))
    return None


def _build_heatmap(fig, go, df, arguments, x, y, _color):
    """Build a heatmap trace."""
    heatmap_col = arguments.get("heatmap_col")
    if not x or not y or not heatmap_col:
        return "Heatmap requires 'x', 'y', and 'heatmap_col' column names."
    col_err = _validate_columns(df, [x, y, heatmap_col])
    if col_err:
        return col_err
    pivot = df.pivot_table(index=y, columns=x, values=heatmap_col, aggfunc="mean")
    fig.add_trace(
        go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=[str(r) for r in pivot.index],
            colorscale="RdYlGn",
        )
    )
    return None


def _build_indicators(fig, go, make_subplots, df, arguments, x, y, color):
    """Build a candlestick or line chart with technical indicator overlays/subplots."""
    from ._indicators import (
        add_overlay_indicators,
        add_subplot_indicators,
        classify_indicators,
        compute_figure_height,
        compute_row_heights,
        validate_indicator_columns,
    )

    chart_type = arguments["chart_type"]
    indicators = arguments["indicators"]

    if chart_type == "candlestick":
        date_col, col_err = _resolve_candlestick_columns(df, x)
        if col_err:
            return col_err, None
        assert date_col is not None
    else:
        col_err = _check_xy_columns(df, x, y, chart_type)
        if col_err:
            return col_err, None
        assert x is not None
        date_col = x

    overlay_specs, subplot_specs, ind_err = classify_indicators(indicators)
    if ind_err:
        return ind_err, None

    sorted_df = df.sort_values(date_col)
    col_err = validate_indicator_columns(indicators, list(sorted_df.columns))
    if col_err:
        return col_err, None

    n_subplot_panels = len(subplot_specs)
    indicator_fig = make_subplots(
        rows=1 + n_subplot_panels,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=compute_row_heights(n_subplot_panels),
    )

    if chart_type == "candlestick":
        indicator_fig.add_trace(
            go.Candlestick(
                x=sorted_df[date_col],
                open=sorted_df["open"],
                high=sorted_df["high"],
                low=sorted_df["low"],
                close=sorted_df["close"],
                name="Price",
            ),
            row=1,
            col=1,
        )
    else:
        indicator_fig.add_trace(
            go.Scatter(
                x=sorted_df[date_col],
                y=sorted_df[y],
                mode="lines",
                name=y,
                line={"color": color} if color else {},
            ),
            row=1,
            col=1,
        )

    close = sorted_df["close"] if "close" in sorted_df.columns else None
    add_overlay_indicators(indicator_fig, go, sorted_df[date_col], close, overlay_specs)
    add_subplot_indicators(indicator_fig, go, sorted_df, date_col, close, subplot_specs)

    height = arguments.get("figsize_height", compute_figure_height(n_subplot_panels))
    indicator_fig.update_layout(xaxis_rangeslider_visible=False)
    return None, (indicator_fig, height)


def _build_candlestick(fig, go, df, arguments, x, _y, _color):
    """Build a plain candlestick trace (no indicators)."""
    date_col, col_err = _resolve_candlestick_columns(df, x)
    if col_err:
        return col_err
    assert date_col is not None
    sorted_df = df.sort_values(date_col)
    fig.add_trace(
        go.Candlestick(
            x=sorted_df[date_col],
            open=sorted_df["open"],
            high=sorted_df["high"],
            low=sorted_df["low"],
            close=sorted_df["close"],
        )
    )
    fig.update_layout(xaxis_rangeslider_visible=False)
    return None


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


@_register("create_chart")
def _handle_create_chart(arguments, dataset, signals, datasets, results, _result):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    chart_type = arguments.get("chart_type")
    if not chart_type:
        return _result("Missing required parameter 'chart_type'.")

    data_source = arguments.get("data_source")
    if not data_source:
        return _result("Missing required parameter 'data_source'.")

    df, source_label, err = _resolve_chart_data(
        data_source, arguments, dataset, datasets, results, signals
    )
    if err:
        return _result(err)
    if df is None or df.empty:
        return _result(f"Data source '{source_label}' is empty.")

    x = arguments.get("x")
    y = arguments.get("y")
    color = arguments.get("color")
    figsize_width = arguments.get("figsize_width", 800)
    figsize_height = arguments.get("figsize_height", 500)

    fig = go.Figure()

    # Dispatch to the appropriate builder
    has_indicators = arguments.get("indicators")
    if chart_type in ("candlestick", "line") and has_indicators:
        result = _build_indicators(fig, go, make_subplots, df, arguments, x, y, color)
        build_err, extra = result
        if build_err:
            return _result(build_err)
        fig, figsize_height = extra

    elif chart_type in ("line", "bar", "scatter"):
        build_err = _build_multi_series(fig, go, df, arguments, x, y, color)
        if build_err:
            return _result(build_err)

    elif chart_type == "histogram":
        build_err = _build_histogram(fig, go, df, arguments, x, y, color)
        if build_err:
            return _result(build_err)

    elif chart_type == "heatmap":
        build_err = _build_heatmap(fig, go, df, arguments, x, y, color)
        if build_err:
            return _result(build_err)

    elif chart_type == "candlestick":
        build_err = _build_candlestick(fig, go, df, arguments, x, y, color)
        if build_err:
            return _result(build_err)

    else:
        return _result(
            f"Unknown chart_type '{chart_type}'. "
            "Use: line, bar, scatter, histogram, heatmap, or candlestick."
        )

    # Layout
    xlabel = arguments.get("xlabel", "")
    ylabel = arguments.get("ylabel", "")
    multi_trace = len(fig.data) > 1
    layout_kwargs: dict[str, Any] = dict(
        xaxis_title=xlabel or x or "",
        yaxis_title=ylabel or y or "",
        width=figsize_width,
        height=figsize_height,
        template="plotly_white",
        showlegend=multi_trace,
        margin=dict(l=40, r=20, t=10, b=30),
    )
    if chart_type == "bar" and multi_trace:
        layout_kwargs["barmode"] = arguments.get("bar_mode", "group")
    fig.update_layout(**layout_kwargs)

    trace_info = f" {len(fig.data)} traces." if multi_trace else ""
    llm_summary = (
        f"Created {chart_type} chart from {source_label}. "
        f"{len(df)} data points.{trace_info}"
    )
    return _result(llm_summary, user_display=llm_summary, chart_figure=fig)


# ---------------------------------------------------------------------------
# IV surface tools
# ---------------------------------------------------------------------------


@_register("plot_vol_surface")
def _handle_plot_vol_surface(arguments, dataset, signals, datasets, results, _result):
    import plotly.graph_objects as go

    active_ds, label, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None
    ds = active_ds

    if "implied_volatility" not in ds.columns:
        return _result(_IV_COLUMN_MISSING_MSG)

    df, quote_date_str, qd_err = _filter_by_quote_date(ds, arguments.get("quote_date"))
    if qd_err:
        return _result(qd_err)
    assert df is not None

    option_type = arguments.get("option_type", "call")
    ot = option_type.lower()[:1]
    df = df[df["option_type"].str.lower().str[0] == ot]
    df = df.dropna(subset=["implied_volatility"])

    if df.empty:
        return _result(f"No {option_type} options with IV data on {quote_date_str}.")

    # Pivot: rows=strike, columns=expiration, values=IV
    pivot = df.pivot_table(
        index="strike",
        columns="expiration",
        values="implied_volatility",
        aggfunc="mean",
    )
    pivot = pivot.sort_index(ascending=True)

    strikes = pivot.index.tolist()
    expirations = [
        str(e.date()) if hasattr(e, "date") and callable(e.date) else str(e)  # type: ignore[union-attr]
        for e in pivot.columns
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=expirations,
            y=strikes,
            colorscale="Viridis",
            colorbar=dict(title="IV"),
        )
    )
    fig.update_layout(
        title=f"Volatility Surface — {label} {option_type}s ({quote_date_str})",
        xaxis_title="Expiration",
        yaxis_title="Strike",
        width=arguments.get("figsize_width", 900),
        height=arguments.get("figsize_height", 600),
    )

    n_strikes = len(strikes)
    n_exps = len(expirations)
    summary = (
        f"Volatility surface for {label} {option_type}s on {quote_date_str}: "
        f"{n_strikes} strikes × {n_exps} expirations."
    )
    return _result(summary, user_display=summary, chart_figure=fig)


@_register("iv_term_structure")
def _handle_iv_term_structure(arguments, dataset, signals, datasets, results, _result):
    import plotly.graph_objects as go

    active_ds, label, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None
    ds = active_ds

    if "implied_volatility" not in ds.columns:
        return _result(_IV_COLUMN_MISSING_MSG)

    df, quote_date_str, qd_err = _filter_by_quote_date(ds, arguments.get("quote_date"))
    if qd_err:
        return _result(qd_err)
    assert df is not None

    # Resolve price column for ATM computation
    df, price_err = resolve_price_column(df)
    if price_err:
        return _result(price_err)
    _price_col = "close"

    df = df.dropna(subset=["implied_volatility", _price_col])

    if df.empty:
        return _result(f"No options with IV data on {quote_date_str}.")

    # Find ATM options: closest strike to price per (symbol, expiration).
    df["_abs_otm"] = (df["strike"] - df[_price_col]).abs()
    atm_idx = df.groupby(["underlying_symbol", "expiration"])["_abs_otm"].idxmin()
    atm_df = df.loc[atm_idx].copy()

    # If both call and put exist at ATM strike, average their IV
    atm_strikes = atm_df[
        ["underlying_symbol", "expiration", "strike"]
    ].drop_duplicates()
    atm_iv = (
        df.merge(atm_strikes, on=["underlying_symbol", "expiration", "strike"])
        .groupby(["underlying_symbol", "expiration"])["implied_volatility"]
        .mean()
        .reset_index()
    )
    assert quote_date_str is not None
    atm_iv["dte"] = (atm_iv["expiration"] - pd.to_datetime(quote_date_str)).dt.days
    atm_iv = atm_iv.sort_values(["underlying_symbol", "dte"])
    atm_iv = atm_iv[atm_iv["dte"] > 0]

    if atm_iv.empty:
        return _result(f"No forward expirations found on {quote_date_str}.")

    fig = go.Figure()
    symbols = atm_iv["underlying_symbol"].unique()
    for sym in symbols:
        sym_data = atm_iv[atm_iv["underlying_symbol"] == sym]
        fig.add_trace(
            go.Scatter(
                x=sym_data["dte"],
                y=sym_data["implied_volatility"],
                mode="lines+markers",
                name=f"{sym} ATM IV" if len(symbols) > 1 else "ATM IV",
                marker=dict(size=8),
            )
        )
    fig.update_layout(
        title=f"IV Term Structure — {label} ATM ({quote_date_str})",
        xaxis_title="Days to Expiration",
        yaxis_title="Implied Volatility",
        width=arguments.get("figsize_width", 800),
        height=arguments.get("figsize_height", 500),
    )

    exps_shown = atm_iv["expiration"].nunique()
    iv_range = f"{atm_iv['implied_volatility'].min():.2%} – {atm_iv['implied_volatility'].max():.2%}"
    summary = (
        f"IV term structure for {label} on {quote_date_str}: "
        f"{exps_shown} expirations, ATM IV range {iv_range}."
    )
    return _result(summary, user_display=summary, chart_figure=fig)
