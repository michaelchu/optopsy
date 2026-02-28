"""Price signals: levels, crossovers, gaps, breakouts, returns, drawdowns."""

import pandas as pd

from ._helpers import (
    SignalFunc,
    _crossover_signal,
    _get_close,
    _get_high,
    _get_low,
    _get_open,
    _groupby_symbol,
    _per_symbol_signal,
)

# ---------------------------------------------------------------------------
# State-based: price above/below a fixed level
# ---------------------------------------------------------------------------


def price_above(level: float) -> SignalFunc:
    """True every bar where the close price is above *level*."""
    level = float(level)
    return _per_symbol_signal(
        lambda p: pd.Series(level, index=p.index),
        lambda prices, lvl: prices > lvl,
    )


def price_below(level: float) -> SignalFunc:
    """True every bar where the close price is below *level*."""
    level = float(level)
    return _per_symbol_signal(
        lambda p: pd.Series(level, index=p.index),
        lambda prices, lvl: prices < lvl,
    )


# ---------------------------------------------------------------------------
# Event-based: price crosses a fixed level
# ---------------------------------------------------------------------------


def price_cross_above(level: float) -> SignalFunc:
    """True on the bar where close crosses above *level*."""
    level = float(level)
    return _crossover_signal(
        lambda prices: (prices, pd.Series(level, index=prices.index)),
        above=True,
    )


def price_cross_below(level: float) -> SignalFunc:
    """True on the bar where close crosses below *level*."""
    level = float(level)
    return _crossover_signal(
        lambda prices: (prices, pd.Series(level, index=prices.index)),
        above=False,
    )


# ---------------------------------------------------------------------------
# Gap signals (need open + close)
# ---------------------------------------------------------------------------


def gap_up(pct: float = 0.5) -> SignalFunc:
    """True when today's open gaps above yesterday's close by at least *pct* %."""
    pct = float(pct)

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            open_ = _get_open(group)
            if close is None or open_ is None:
                return pd.Series(False, index=group.index)
            threshold = close.shift(1) * (1 + pct / 100)
            return (open_ > threshold).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def gap_down(pct: float = 0.5) -> SignalFunc:
    """True when today's open gaps below yesterday's close by at least *pct* %."""
    pct = float(pct)

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            open_ = _get_open(group)
            if close is None or open_ is None:
                return pd.Series(False, index=group.index)
            threshold = close.shift(1) * (1 - pct / 100)
            return (open_ < threshold).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


# ---------------------------------------------------------------------------
# N-period high/low breakout signals
# ---------------------------------------------------------------------------


def high_of_n_days(period: int = 252) -> SignalFunc:
    """True when close reaches or exceeds the N-bar rolling high (breakout).

    The rolling window is shifted by 1 to avoid look-ahead bias — the
    comparison is against the highest high of the *previous* N bars.
    """
    period = int(period)

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            high = _get_high(group)
            if close is None or high is None:
                return pd.Series(False, index=group.index)
            rolling_high = high.rolling(period, min_periods=1).max().shift(1)
            return (close >= rolling_high).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def low_of_n_days(period: int = 252) -> SignalFunc:
    """True when close reaches or falls below the N-bar rolling low (breakdown).

    The rolling window is shifted by 1 to avoid look-ahead bias — the
    comparison is against the lowest low of the *previous* N bars.
    """
    period = int(period)

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            low = _get_low(group)
            if close is None or low is None:
                return pd.Series(False, index=group.index)
            rolling_low = low.rolling(period, min_periods=1).min().shift(1)
            return (close <= rolling_low).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


# ---------------------------------------------------------------------------
# Daily return signals
# ---------------------------------------------------------------------------


def daily_return_above(pct: float = 1.0) -> SignalFunc:
    """True when the daily close-to-close return exceeds *pct* %.

    Example: ``daily_return_above(2.0)`` fires on days the stock gains > 2%.
    """
    threshold = float(pct) / 100  # compare in decimal form

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            if close is None:
                return pd.Series(False, index=group.index)
            ret = close.pct_change()
            return (ret > threshold).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def daily_return_below(pct: float = -1.0) -> SignalFunc:
    """True when the daily close-to-close return is below *pct* %.

    Use negative values for drops: ``daily_return_below(-3.0)`` fires on
    days the stock falls more than 3%.
    """
    threshold = float(pct) / 100  # compare in decimal form

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            if close is None:
                return pd.Series(False, index=group.index)
            ret = close.pct_change()
            return (ret < threshold).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


# ---------------------------------------------------------------------------
# Drawdown / rally signals
# ---------------------------------------------------------------------------


def drawdown_from_high(period: int = 20, pct: float = 5.0) -> SignalFunc:
    """True when close is down at least *pct* % from its *period*-bar rolling high.

    Measures how far the current close has fallen from the highest close
    over the last *period* bars (inclusive of the current bar).
    """
    period = int(period)
    threshold = float(pct) / 100  # convert to decimal

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            if close is None:
                return pd.Series(False, index=group.index)
            rolling_high = close.rolling(period, min_periods=1).max()
            dd_ratio = (close - rolling_high) / rolling_high  # negative values
            return (dd_ratio <= -threshold).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def rally_from_low(period: int = 20, pct: float = 5.0) -> SignalFunc:
    """True when close is up at least *pct* % from its *period*-bar rolling low.

    Measures how far the current close has risen from the lowest close
    over the last *period* bars (inclusive of the current bar).
    """
    period = int(period)
    threshold = float(pct) / 100  # convert to decimal

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            if close is None:
                return pd.Series(False, index=group.index)
            rolling_low = close.rolling(period, min_periods=1).min()
            rally_ratio = (close - rolling_low) / rolling_low
            return (rally_ratio >= threshold).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


# ---------------------------------------------------------------------------
# Consecutive up/down day signals
# ---------------------------------------------------------------------------


def consecutive_up(days: int = 3) -> SignalFunc:
    """True on the bar completing *days* consecutive closes above prior close.

    Example: ``consecutive_up(3)`` fires after 3 straight up-closes.
    """
    days = int(days)
    if days < 1:
        raise ValueError(f"days must be >= 1, got {days}")

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            if close is None:
                return pd.Series(False, index=group.index)
            up = (close > close.shift(1)).astype(int)
            streak = up.rolling(days, min_periods=days).sum()
            return (streak == days).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def consecutive_down(days: int = 3) -> SignalFunc:
    """True on the bar completing *days* consecutive closes below prior close.

    Example: ``consecutive_down(3)`` fires after 3 straight down-closes.
    """
    days = int(days)
    if days < 1:
        raise ValueError(f"days must be >= 1, got {days}")

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            close = _get_close(group)
            if close is None:
                return pd.Series(False, index=group.index)
            down = (close < close.shift(1)).astype(int)
            streak = down.rolling(days, min_periods=days).sum()
            return (streak == days).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal
