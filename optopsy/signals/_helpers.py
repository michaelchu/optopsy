"""Shared helpers for building signal functions.

All signal modules import from here to avoid circular dependencies.
"""

import operator
from typing import Callable

import pandas as pd

# Signal function type: takes a DataFrame with (underlying_symbol, quote_date,
# close or underlying_price) columns and returns a boolean Series indicating
# valid entry/exit dates.
SignalFunc = Callable[[pd.DataFrame], "pd.Series[bool]"]


# ---------------------------------------------------------------------------
# Per-symbol grouping
# ---------------------------------------------------------------------------


def _groupby_symbol(
    data: pd.DataFrame,
    compute_group: Callable[[pd.DataFrame], "pd.Series[bool]"],
) -> "pd.Series[bool]":
    """Apply *compute_group* per underlying_symbol and concatenate results.

    Handles the empty-DataFrame and empty-groups (all-NA symbols) edge cases
    that every per-symbol signal needs.
    """
    if data.empty:
        return pd.Series(False, index=data.index, dtype=bool)
    parts = [
        compute_group(group)
        for _, group in data.groupby("underlying_symbol", sort=False)
    ]
    if not parts:
        return pd.Series(False, index=data.index, dtype=bool)
    return pd.concat(parts).reindex(data.index, fill_value=False)


# ---------------------------------------------------------------------------
# Signal skeleton builders
# ---------------------------------------------------------------------------


def _per_symbol_signal(
    indicator_fn: Callable[[pd.Series], pd.Series],
    compare_fn: Callable[[pd.Series, pd.Series], "pd.Series[bool]"],
) -> SignalFunc:
    """Build a signal that computes an indicator per symbol and applies a comparison.

    This is the shared skeleton behind RSI, SMA, and similar per-symbol signals.
    NaN indicator values default to False (never trigger a signal).

    Args:
        indicator_fn: Takes a price Series, returns an indicator Series (or None)
        compare_fn: Takes (prices, indicator), returns a boolean Series
    """

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            prices = _get_close(group)
            if prices is None:
                return pd.Series(False, index=group.index)
            indicator = indicator_fn(prices)
            if indicator is None:
                return pd.Series(False, index=group.index)
            return compare_fn(prices, indicator).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return signal


def _crossover_signal(
    compute_lines_fn: Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]],
    above: bool,
) -> SignalFunc:
    """Build a crossover signal that fires when line_a crosses line_b.

    Shared skeleton for MACD, EMA, and similar crossover signals.

    Args:
        compute_lines_fn: Takes prices, returns (line_a, line_b) or (None, None)
        above: True -> line_a crosses above line_b; False -> line_a crosses below
    """
    if above:
        cur_op, prev_op = operator.gt, operator.le
    else:
        cur_op, prev_op = operator.lt, operator.ge

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            prices = _get_close(group)
            if prices is None:
                return pd.Series(False, index=group.index)
            line_a, line_b = compute_lines_fn(prices)
            if line_a is None or line_b is None:
                return pd.Series(False, index=group.index)
            cross = cur_op(line_a, line_b) & prev_op(line_a.shift(1), line_b.shift(1))
            return cross.fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


# ---------------------------------------------------------------------------
# OHLCV-aware signal builders (new)
# ---------------------------------------------------------------------------


def _ohlcv_signal(
    indicator_fn: Callable[[pd.DataFrame], "pd.Series | None"],
    compare_fn: Callable[["pd.Series"], "pd.Series[bool]"],
) -> SignalFunc:
    """Build a signal from an OHLCV-based indicator per symbol.

    Like ``_per_symbol_signal`` but passes the full group DataFrame
    (with high, low, volume columns when available) instead of just close.
    Returns all-False when the indicator cannot be computed.

    Args:
        indicator_fn: Takes a group DataFrame, returns an indicator Series (or None)
        compare_fn: Takes the indicator Series, returns a boolean Series
    """

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            indicator = indicator_fn(group)
            if indicator is None:
                return pd.Series(False, index=group.index)
            return compare_fn(indicator).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return signal


def _ohlcv_crossover_signal(
    compute_lines_fn: Callable[
        [pd.DataFrame], tuple["pd.Series | None", "pd.Series | None"]
    ],
    above: bool,
) -> SignalFunc:
    """Build a crossover signal from OHLCV data.

    Like ``_crossover_signal`` but the compute function receives the full
    group DataFrame instead of just prices.
    """
    if above:
        cur_op, prev_op = operator.gt, operator.le
    else:
        cur_op, prev_op = operator.lt, operator.ge

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            line_a, line_b = compute_lines_fn(group)
            if line_a is None or line_b is None:
                return pd.Series(False, index=group.index)
            cross = cur_op(line_a, line_b) & prev_op(line_a.shift(1), line_b.shift(1))
            return cross.fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def _band_signal(
    compute_bands_fn: Callable[
        [pd.DataFrame], tuple["pd.Series | None", "pd.Series | None"]
    ],
    above: bool,
) -> SignalFunc:
    """Build a band-breakout signal (price above upper / below lower).

    Generalised version of the Bollinger Band pattern for Keltner, Donchian, etc.

    Args:
        compute_bands_fn: Takes a group DataFrame, returns (upper_band, lower_band).
                          Either may be None on failure.
        above: True -> price > upper band; False -> price < lower band
    """
    if above:
        fill_val = float("inf")
        cmp = operator.gt
    else:
        fill_val = float("-inf")
        cmp = operator.lt

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            upper, lower = compute_bands_fn(group)
            band = upper if above else lower
            if band is None:
                return pd.Series(False, index=group.index)
            prices = _get_close(group)
            if prices is None:
                return pd.Series(False, index=group.index)
            return cmp(prices, band.fillna(fill_val)).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def _direction_signal(
    compute_fn: Callable[[pd.DataFrame], "pd.Series | None"],
    buy: bool,
) -> SignalFunc:
    """Build a direction-change signal (Supertrend flip, PSAR flip).

    Fires on the bar where the direction indicator transitions.

    Args:
        compute_fn: Takes a group DataFrame, returns a direction Series
                    where 1 = bullish and -1 = bearish (or similar convention).
                    Returns None on failure.
        buy: True -> fires when direction changes to bullish (1);
             False -> fires when direction changes to bearish (-1)
    """
    target = 1 if buy else -1

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            direction = compute_fn(group)
            if direction is None:
                return pd.Series(False, index=group.index)
            # Fire when direction changes to target value
            changed = (direction == target) & (direction.shift(1) != target)
            return changed.fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


# ---------------------------------------------------------------------------
# OHLC column helpers
# ---------------------------------------------------------------------------


def _get_close(group: pd.DataFrame) -> "pd.Series | None":
    """Get close price from a group DataFrame, or None if the column is absent.

    Requires the ``close`` column to be present.  Callers that previously relied
    on the ``underlying_price`` fallback should ensure
    ``resolve_price_column()`` has been applied before signals run.
    """
    if "close" in group.columns:
        return group["close"]
    return None


def _get_high(group: pd.DataFrame) -> "pd.Series | None":
    """Get high prices, falling back to close.  Returns None when unavailable."""
    if "high" in group.columns:
        return group["high"]
    return _get_close(group)


def _get_low(group: pd.DataFrame) -> "pd.Series | None":
    """Get low prices, falling back to close.  Returns None when unavailable."""
    if "low" in group.columns:
        return group["low"]
    return _get_close(group)


def _get_volume(group: pd.DataFrame) -> "pd.Series | None":
    """Get volume if available, else None."""
    if "volume" in group.columns:
        return group["volume"]
    return None
