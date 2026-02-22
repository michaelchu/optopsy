"""Indicator trace builders for multi-panel Plotly charts.

Each builder function takes indicator parameters and source data, and adds
traces to a Plotly figure at the specified row.  This keeps the chart tool
handler thin and makes individual indicators independently testable.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pandas_ta as ta

# ---------------------------------------------------------------------------
# Indicator classification
# ---------------------------------------------------------------------------

OVERLAY_TYPES = frozenset({"sma", "ema", "bbands"})
SUBPLOT_TYPES = frozenset({"rsi", "macd", "volume"})
VALID_INDICATOR_TYPES = OVERLAY_TYPES | SUBPLOT_TYPES


def classify_indicators(
    indicators: list[dict[str, Any]],
) -> tuple[list[dict], list[dict], str | None]:
    """Split indicator specs into overlay and subplot lists.

    Returns ``(overlay_specs, subplot_specs, error_msg)``.  When
    ``error_msg`` is not None the caller should return it immediately.
    """
    overlay: list[dict] = []
    subplot: list[dict] = []
    for ind in indicators:
        ind_type = ind.get("type", "")
        if ind_type not in VALID_INDICATOR_TYPES:
            return (
                [],
                [],
                (
                    f"Unknown indicator type '{ind_type}'. "
                    f"Valid: {sorted(VALID_INDICATOR_TYPES)}"
                ),
            )
        if ind_type in OVERLAY_TYPES:
            overlay.append(ind)
        else:
            subplot.append(ind)
    return overlay, subplot, None


def validate_indicator_columns(
    indicators: list[dict[str, Any]],
    columns: list[str],
) -> str | None:
    """Check that the DataFrame has the columns needed by *indicators*.

    Returns an error message string, or None if everything is valid.
    """
    needs_close = any(
        ind["type"] in ("sma", "ema", "bbands", "rsi", "macd") for ind in indicators
    )
    if needs_close and "close" not in columns:
        return f"Technical indicators require a 'close' column. Available: {columns}"
    needs_volume = any(ind["type"] == "volume" for ind in indicators)
    if needs_volume and "volume" not in columns:
        return f"Volume indicator requires a 'volume' column. Available: {columns}"
    return None


# ---------------------------------------------------------------------------
# Overlay indicator builders (added to the price panel, row=1)
# ---------------------------------------------------------------------------


def add_sma_trace(
    fig: Any, go: Any, dates: pd.Series, close: pd.Series, ind: dict
) -> None:
    period = ind.get("period", 20)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ta.sma(close, length=period),
            mode="lines",
            name=f"SMA({period})",
        ),
        row=1,
        col=1,
    )


def add_ema_trace(
    fig: Any, go: Any, dates: pd.Series, close: pd.Series, ind: dict
) -> None:
    period = ind.get("period", 20)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ta.ema(close, length=period),
            mode="lines",
            name=f"EMA({period})",
        ),
        row=1,
        col=1,
    )


def add_bbands_traces(
    fig: Any,
    go: Any,
    dates: pd.Series,
    close: pd.Series,
    ind: dict,
) -> None:
    period = ind.get("period", 20)
    std = ind.get("std", 2.0)
    bb = ta.bbands(close, length=period, std=std)
    if bb is None or bb.empty:
        return
    # pandas_ta column names vary (e.g. BBL_20_2.0 vs BBL_20_2.0_2.0)
    upper_col = next(c for c in bb.columns if c.startswith("BBU_"))
    lower_col = next(c for c in bb.columns if c.startswith("BBL_"))
    mid_col = next(c for c in bb.columns if c.startswith("BBM_"))

    _BAND_COLOR = "rgba(128,128,128,0.5)"
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=bb[upper_col],
            mode="lines",
            name=f"BB Upper({period})",
            line={"dash": "dash", "color": _BAND_COLOR},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=bb[lower_col],
            mode="lines",
            name=f"BB Lower({period})",
            line={"dash": "dash", "color": _BAND_COLOR},
            fill="tonexty",
            fillcolor="rgba(128,128,128,0.1)",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=bb[mid_col],
            mode="lines",
            name=f"BB Mid({period})",
            line={"dash": "dot", "color": "rgba(128,128,128,0.7)"},
        ),
        row=1,
        col=1,
    )


_OVERLAY_BUILDERS = {
    "sma": add_sma_trace,
    "ema": add_ema_trace,
    "bbands": add_bbands_traces,
}


def add_overlay_indicators(
    fig: Any,
    go: Any,
    dates: pd.Series,
    close: pd.Series,
    specs: list[dict],
) -> None:
    """Add all overlay indicator traces to the price panel (row 1)."""
    for ind in specs:
        _OVERLAY_BUILDERS[ind["type"]](fig, go, dates, close, ind)


# ---------------------------------------------------------------------------
# Subplot indicator builders (each gets its own row)
# ---------------------------------------------------------------------------


def add_rsi_traces(
    fig: Any,
    go: Any,
    dates: pd.Series,
    close: pd.Series,
    ind: dict,
    row: int,
) -> None:
    period = ind.get("period", 14)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ta.rsi(close, length=period),
            mode="lines",
            name=f"RSI({period})",
        ),
        row=row,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=row, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=row, col=1)
    fig.update_yaxes(title_text="RSI", row=row, col=1)


def add_macd_traces(
    fig: Any,
    go: Any,
    dates: pd.Series,
    close: pd.Series,
    ind: dict,
    row: int,
) -> None:
    fast = ind.get("fast", 12)
    slow = ind.get("slow", 26)
    signal_period = ind.get("signal", 9)
    macd_df = ta.macd(close, fast=fast, slow=slow, signal=signal_period)
    if macd_df is not None and not macd_df.empty:
        macd_col = f"MACD_{fast}_{slow}_{signal_period}"
        signal_col = f"MACDs_{fast}_{slow}_{signal_period}"
        hist_col = f"MACDh_{fast}_{slow}_{signal_period}"
        fig.add_trace(
            go.Scatter(x=dates, y=macd_df[macd_col], mode="lines", name="MACD"),
            row=row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=dates, y=macd_df[signal_col], mode="lines", name="Signal"),
            row=row,
            col=1,
        )
        hist_vals = macd_df[hist_col]
        colors = ["green" if v >= 0 else "red" for v in hist_vals.fillna(0)]
        fig.add_trace(
            go.Bar(x=dates, y=hist_vals, name="Histogram", marker_color=colors),
            row=row,
            col=1,
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=row, col=1)
    fig.update_yaxes(title_text="MACD", row=row, col=1)


def add_volume_traces(
    fig: Any,
    go: Any,
    sorted_df: pd.DataFrame,
    date_col: str,
    row: int,
) -> None:
    closes = sorted_df["close"]
    # Vectorised: green when close >= previous close (or first bar)
    vol_colors = (closes >= closes.shift(1).bfill()).map({True: "green", False: "red"})
    fig.add_trace(
        go.Bar(
            x=sorted_df[date_col],
            y=sorted_df["volume"],
            name="Volume",
            marker_color=vol_colors.tolist(),
        ),
        row=row,
        col=1,
    )
    fig.update_yaxes(title_text="Volume", row=row, col=1)


def add_subplot_indicators(
    fig: Any,
    go: Any,
    sorted_df: pd.DataFrame,
    date_col: str,
    close: pd.Series | None,
    specs: list[dict],
    start_row: int = 2,
) -> None:
    """Add all subplot indicator traces, each in its own row."""
    dates = sorted_df[date_col]
    for i, ind in enumerate(specs, start=start_row):
        ind_type = ind["type"]
        if ind_type == "rsi":
            add_rsi_traces(fig, go, dates, close, ind, i)
        elif ind_type == "macd":
            add_macd_traces(fig, go, dates, close, ind, i)
        elif ind_type == "volume":
            add_volume_traces(fig, go, sorted_df, date_col, i)


# ---------------------------------------------------------------------------
# Subplot layout helpers
# ---------------------------------------------------------------------------


def compute_row_heights(n_subplot_panels: int) -> list[float]:
    """Return row_heights list for make_subplots (price panel + N subplots)."""
    if n_subplot_panels == 0:
        return [1.0]
    price_ratio = 0.65
    sub_ratio = (1.0 - price_ratio) / n_subplot_panels
    return [price_ratio] + [sub_ratio] * n_subplot_panels


def compute_figure_height(n_subplot_panels: int) -> int:
    """Auto-scale figure height: 500px base + 200px per subplot."""
    return 500 + 200 * n_subplot_panels
