"""
Entry/exit signal filters for controlling when option positions are entered or exited.

Signals are functions that take a DataFrame of underlying price data
(with columns: underlying_symbol, quote_date, underlying_price) and
return a boolean Series indicating which dates are valid for entry/exit.

Built-in signals can be combined with and_signals() / or_signals(), or with
the fluent Signal class using & and | operators.

Use ``apply_signal()`` to run a signal function on data and get back a
DataFrame of valid ``(underlying_symbol, quote_date)`` pairs to pass as
``entry_dates`` or ``exit_dates`` to any strategy.

Example:
    >>> from optopsy.signals import rsi_below, day_of_week, and_signals, apply_signal
    >>> import optopsy as op
    >>> data = op.csv_data('./SPX_2018.csv')
    >>> stock = load_stock_data(...)  # OHLCV DataFrame

    >>> # Compute entry dates: Thursdays when RSI(14) < 30
    >>> sig = and_signals(rsi_below(14, 30), day_of_week(3))
    >>> entry_dates = apply_signal(stock, sig)
    >>> results = op.long_calls(data, entry_dates=entry_dates, raw=True)

    >>> # Fluent API with Signal class
    >>> sig = signal(rsi_below(14, 30)) & signal(day_of_week(3))
    >>> entry_dates = apply_signal(stock, sig)
    >>> results = op.long_calls(data, entry_dates=entry_dates, raw=True)
"""

import operator
from typing import Callable

import pandas as pd
import pandas_ta as ta

from .timestamps import normalize_dates

# Signal function type: takes a DataFrame with (underlying_symbol, quote_date,
# underlying_price) and returns a boolean Series indicating valid entry/exit dates.
SignalFunc = Callable[[pd.DataFrame], "pd.Series[bool]"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_rsi(prices: pd.Series, period: int) -> pd.Series:
    """
    Compute RSI for a price series using pandas_ta.

    Kept as a named function for test compatibility. Uses Wilder smoothing
    (RMA) internally via pandas_ta, which is equivalent to the previous
    hand-rolled EWM implementation.

    Args:
        prices: Series of prices sorted chronologically
        period: Lookback period for RSI calculation

    Returns:
        Series of RSI values (0-100), with NaN for the first `period` entries.
        Returns a NaN series if pandas_ta cannot compute (insufficient data).
    """
    result = ta.rsi(prices, length=period)
    if result is None:
        return pd.Series(float("nan"), index=prices.index)
    return result


def _per_symbol_signal(
    indicator_fn: Callable[[pd.Series], pd.Series],
    compare_fn: Callable[[pd.Series, pd.Series], "pd.Series[bool]"],
) -> SignalFunc:
    """
    Build a signal that computes an indicator per symbol and applies a comparison.

    This is the shared skeleton behind RSI, SMA, and similar per-symbol signals.
    NaN indicator values default to False (never trigger a signal).

    Args:
        indicator_fn: Takes a price Series, returns an indicator Series (or None)
        compare_fn: Takes (prices, indicator), returns a boolean Series

    Returns:
        Signal function
    """

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for _symbol, group in data.groupby("underlying_symbol", sort=False):
            prices = group["underlying_price"]
            indicator = indicator_fn(prices)
            if indicator is None:
                continue
            bools = compare_fn(prices, indicator)
            result.loc[group.index] = bools.fillna(False)
        return result

    return signal


def _crossover_signal(
    compute_lines_fn: Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]],
    above: bool,
) -> SignalFunc:
    """
    Build a crossover signal that fires when line_a crosses line_b.

    Shared skeleton for MACD and EMA crossover signals.

    Args:
        compute_lines_fn: Takes prices, returns (line_a, line_b) or (None, None)
        above: True → line_a crosses above line_b; False → line_a crosses below

    Returns:
        Signal function
    """
    if above:
        cur_op, prev_op = operator.gt, operator.le
    else:
        cur_op, prev_op = operator.lt, operator.ge

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for _symbol, group in data.groupby("underlying_symbol", sort=False):
            prices = group["underlying_price"]
            line_a, line_b = compute_lines_fn(prices)
            if line_a is None or line_b is None:
                continue
            cross = cur_op(line_a, line_b) & prev_op(line_a.shift(1), line_b.shift(1))
            result.loc[group.index] = cross.fillna(False)
        return result

    return _signal


# ---------------------------------------------------------------------------
# RSI signals
# ---------------------------------------------------------------------------


def rsi_below(period: int = 14, threshold: float = 30) -> SignalFunc:
    """
    True when RSI is below a threshold (oversold condition).

    Args:
        period: RSI lookback period (default 14)
        threshold: RSI value below which signal fires (default 30)

    Returns:
        Signal function
    """
    return _per_symbol_signal(
        lambda p: _compute_rsi(p, period),
        lambda _prices, rsi: rsi < threshold,
    )


def rsi_above(period: int = 14, threshold: float = 70) -> SignalFunc:
    """
    True when RSI is above a threshold (overbought condition).

    Args:
        period: RSI lookback period (default 14)
        threshold: RSI value above which signal fires (default 70)

    Returns:
        Signal function
    """
    return _per_symbol_signal(
        lambda p: _compute_rsi(p, period),
        lambda _prices, rsi: rsi > threshold,
    )


# ---------------------------------------------------------------------------
# SMA signals
# ---------------------------------------------------------------------------


def sma_below(period: int = 20) -> SignalFunc:
    """
    True when the underlying price is below its simple moving average.

    Args:
        period: SMA lookback period (default 20)

    Returns:
        Signal function
    """
    return _per_symbol_signal(
        lambda p: ta.sma(p, length=period),
        lambda prices, sma: prices < sma,
    )


def sma_above(period: int = 20) -> SignalFunc:
    """
    True when the underlying price is above its simple moving average.

    Args:
        period: SMA lookback period (default 20)

    Returns:
        Signal function
    """
    return _per_symbol_signal(
        lambda p: ta.sma(p, length=period),
        lambda prices, sma: prices > sma,
    )


# ---------------------------------------------------------------------------
# MACD crossover signals
# ---------------------------------------------------------------------------


def _macd_lines(
    fast: int, slow: int, signal_period: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    """Return a function that computes (macd_line, signal_line) from prices."""
    macd_col = f"MACD_{fast}_{slow}_{signal_period}"
    sig_col = f"MACDs_{fast}_{slow}_{signal_period}"

    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        macd_df = ta.macd(prices, fast=fast, slow=slow, signal=signal_period)
        if macd_df is None:
            return None, None
        return macd_df[macd_col], macd_df[sig_col]

    return _compute


def macd_cross_above(
    fast: int = 12, slow: int = 26, signal_period: int = 9
) -> SignalFunc:
    """
    True when the MACD line crosses above the signal line (bullish momentum event).

    This detects the crossover *event* (two-bar comparison), not the state
    (MACD is above signal). Requires at least fast+slow+signal_period bars of
    warmup (~50 bars with defaults). Returns False during the warmup period.

    Args:
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal_period: Signal line smoothing period (default 9)

    Returns:
        Signal function
    """
    fast, slow, signal_period = int(fast), int(slow), int(signal_period)
    return _crossover_signal(_macd_lines(fast, slow, signal_period), above=True)


def macd_cross_below(
    fast: int = 12, slow: int = 26, signal_period: int = 9
) -> SignalFunc:
    """
    True when the MACD line crosses below the signal line (bearish momentum event).

    This detects the crossover *event* (two-bar comparison), not the state.
    Requires at least fast+slow+signal_period bars of warmup (~50 bars with defaults).

    Args:
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal_period: Signal line smoothing period (default 9)

    Returns:
        Signal function
    """
    fast, slow, signal_period = int(fast), int(slow), int(signal_period)
    return _crossover_signal(_macd_lines(fast, slow, signal_period), above=False)


# ---------------------------------------------------------------------------
# Bollinger Band signals
# ---------------------------------------------------------------------------


def _bb_signal(length: int, std: float, above: bool) -> SignalFunc:
    """
    Shared Bollinger Band signal logic.

    Args:
        length: BB window period
        std: Number of standard deviations
        above: True → price > upper band; False → price < lower band
    """
    length, std = int(length), float(std)
    if above:
        band_col = f"BBU_{length}_{std}_{std}"
        fill_val = float("inf")
        cmp = operator.gt
    else:
        band_col = f"BBL_{length}_{std}_{std}"
        fill_val = float("-inf")
        cmp = operator.lt

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for _symbol, group in data.groupby("underlying_symbol", sort=False):
            prices = group["underlying_price"]
            bb = ta.bbands(prices, length=length, std=std)
            if bb is None:
                continue
            band = bb[band_col].fillna(fill_val)
            result.loc[group.index] = cmp(prices, band).fillna(False)
        return result

    return _signal


def bb_above_upper(length: int = 20, std: float = 2.0) -> SignalFunc:
    """
    True when the underlying price is above the upper Bollinger Band.

    Useful for detecting breakouts or overbought conditions.

    Args:
        length: Bollinger Band window period (default 20)
        std: Number of standard deviations for the bands (default 2.0)

    Returns:
        Signal function
    """
    return _bb_signal(length, std, above=True)


def bb_below_lower(length: int = 20, std: float = 2.0) -> SignalFunc:
    """
    True when the underlying price is below the lower Bollinger Band.

    Useful for detecting oversold conditions or mean-reversion setups.

    Args:
        length: Bollinger Band window period (default 20)
        std: Number of standard deviations for the bands (default 2.0)

    Returns:
        Signal function
    """
    return _bb_signal(length, std, above=False)


# ---------------------------------------------------------------------------
# EMA crossover signals
# ---------------------------------------------------------------------------


def _ema_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    """Return a function that computes (fast_ema, slow_ema) from prices."""

    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ema = ta.ema(prices, length=fast)
        slow_ema = ta.ema(prices, length=slow)
        if fast_ema is None or slow_ema is None:
            return None, None
        return fast_ema, slow_ema

    return _compute


def ema_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """
    True when the fast EMA crosses above the slow EMA (bullish golden cross).

    Detects the crossover *event* (two-bar comparison). Requires at least
    `slow` bars of warmup. Returns False during the warmup period.

    Args:
        fast: Fast EMA period (default 10)
        slow: Slow EMA period (default 50)

    Returns:
        Signal function
    """
    fast, slow = int(fast), int(slow)
    return _crossover_signal(_ema_lines(fast, slow), above=True)


def ema_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """
    True when the fast EMA crosses below the slow EMA (bearish death cross).

    Detects the crossover *event* (two-bar comparison). Requires at least
    `slow` bars of warmup. Returns False during the warmup period.

    Args:
        fast: Fast EMA period (default 10)
        slow: Slow EMA period (default 50)

    Returns:
        Signal function
    """
    fast, slow = int(fast), int(slow)
    return _crossover_signal(_ema_lines(fast, slow), above=False)


# ---------------------------------------------------------------------------
# ATR volatility regime signals
# ---------------------------------------------------------------------------


def _compute_atr(
    close: pd.Series,
    period: int,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
) -> pd.Series:
    """
    Compute ATR using real OHLC data when available, or close-only proxy.

    When ``high`` and ``low`` are provided (from yfinance OHLCV stock data),
    the True Range uses the standard max(H-L, |H-Prev_C|, |L-Prev_C|) formula.
    Otherwise, falls back to close-only: True Range = |close_t - close_{t-1}|.

    Args:
        close: Close price series
        period: ATR lookback period
        high: High price series (optional, from OHLCV data)
        low: Low price series (optional, from OHLCV data)

    Returns:
        Series of ATR values, or NaN series if insufficient data
    """
    hi = high if high is not None else close
    lo = low if low is not None else close
    result = ta.atr(high=hi, low=lo, close=close, length=period)
    if result is None:
        return pd.Series(float("nan"), index=close.index)
    return result


def _atr_signal(period: int, multiplier: float, above: bool) -> SignalFunc:
    """
    Shared ATR regime signal logic.

    Args:
        period: ATR lookback period
        multiplier: Fraction of median ATR to use as threshold
        above: True → ATR > threshold; False → ATR < threshold
    """
    period = int(period)
    cmp = operator.gt if above else operator.lt

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        has_ohlcv = "high" in data.columns and "low" in data.columns
        result = pd.Series(False, index=data.index)
        for _symbol, group in data.groupby("underlying_symbol", sort=False):
            prices = group["underlying_price"]
            high = group["high"] if has_ohlcv else None
            low = group["low"] if has_ohlcv else None
            atr = _compute_atr(prices, period, high=high, low=low)
            median_atr = atr.median()
            if pd.isna(median_atr):
                continue
            result.loc[group.index] = cmp(atr, multiplier * median_atr).fillna(False)
        return result

    return _signal


def atr_above(period: int = 14, multiplier: float = 1.0) -> SignalFunc:
    """
    True when ATR exceeds `multiplier` times the full-history median ATR.

    Use to filter entries to high-volatility regimes (e.g. multiplier=1.5
    means ATR is 50% above its historical median — elevated vol environment).

    When the signal receives OHLCV data, uses real high/low prices.
    Falls back to close-to-close proxy otherwise.

    Args:
        period: ATR lookback period (default 14)
        multiplier: Fraction of median ATR to use as threshold (default 1.0)

    Returns:
        Signal function
    """
    return _atr_signal(period, multiplier, above=True)


def atr_below(period: int = 14, multiplier: float = 1.0) -> SignalFunc:
    """
    True when ATR is below `multiplier` times the full-history median ATR.

    Use to filter entries to low-volatility / calm market regimes (e.g.
    multiplier=0.75 means ATR is 25% below its historical median).

    When the signal receives OHLCV data, uses real high/low prices.
    Falls back to close-to-close proxy otherwise.

    Args:
        period: ATR lookback period (default 14)
        multiplier: Fraction of median ATR to use as threshold (default 1.0)

    Returns:
        Signal function
    """
    return _atr_signal(period, multiplier, above=False)


# ---------------------------------------------------------------------------
# Day-of-week signal
# ---------------------------------------------------------------------------


def day_of_week(*days: int) -> SignalFunc:
    """
    True on specific days of the week.

    Args:
        *days: Day numbers where Monday=0, Tuesday=1, ..., Sunday=6.
               For example, day_of_week(3) filters for Thursdays.

    Returns:
        Signal function
    """
    day_set = set(days)

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        return data["quote_date"].dt.dayofweek.isin(day_set)

    return _signal


# ---------------------------------------------------------------------------
# Signal combinators
# ---------------------------------------------------------------------------


def and_signals(*signals: SignalFunc) -> SignalFunc:
    """
    Combine multiple signals with logical AND.

    All signals must be True for a date to be valid.

    Args:
        *signals: Signal functions to combine

    Returns:
        Combined signal function
    """

    def combined(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(True, index=data.index)
        for sig in signals:
            result = result & sig(data)
        return result

    return combined


def or_signals(*signals: SignalFunc) -> SignalFunc:
    """
    Combine multiple signals with logical OR.

    At least one signal must be True for a date to be valid.

    Args:
        *signals: Signal functions to combine

    Returns:
        Combined signal function
    """

    def combined(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for sig in signals:
            result = result | sig(data)
        return result

    return combined


# ---------------------------------------------------------------------------
# Sustained combinator
# ---------------------------------------------------------------------------


def sustained(signal_func: SignalFunc, days: int = 5) -> SignalFunc:
    """
    True only when signal_func has been True for at least `days` consecutive bars.

    Uses a rolling minimum over the boolean output of the inner signal: the
    window minimum is 1 only when every bar in the window was True. A single
    False bar resets the streak. Operates per-symbol so each ticker's streak
    is computed independently.

    Args:
        signal_func: Any SignalFunc to wrap (e.g. rsi_below(14, 30))
        days: Minimum consecutive True bars required (default 5)

    Returns:
        Signal function

    Raises:
        ValueError: If days < 1

    Example:
        >>> # Enter only after RSI has been below 30 for 5+ consecutive days
        >>> sig = sustained(rsi_below(14, 30), days=5)
        >>> entry_dates = apply_signal(stock, sig)
        >>> results = op.long_calls(data, entry_dates=entry_dates)

        >>> # Compose with Signal class
        >>> sig = signal(sustained(rsi_below(14, 30), days=5)) & signal(day_of_week(3))
    """
    if days < 1:
        raise ValueError(f"days must be >= 1, got {days}")

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for _symbol, group in data.groupby("underlying_symbol", sort=False):
            raw = signal_func(group)
            # rolling(days).min() == 1 only when all `days` bars in the window are True.
            # One False resets to 0. fillna(0) makes the warmup period False.
            streak = raw.astype(int).rolling(days).min().fillna(0).astype(bool)
            result.loc[group.index] = streak
        return result

    return _signal


# ---------------------------------------------------------------------------
# Fluent Signal class
# ---------------------------------------------------------------------------


class Signal:
    """
    Composable wrapper around a SignalFunc with & and | operator support.

    Wrapping a signal function in Signal enables fluent chaining without
    nesting and_signals() / or_signals() calls. A Signal instance is itself
    callable with the correct SignalFunc signature, so it can be passed
    directly to ``apply_signal()`` to compute valid dates.

    Example:
        >>> from optopsy.signals import Signal, signal, rsi_below, day_of_week, apply_signal
        >>> import optopsy as op
        >>>
        >>> # Fluent AND
        >>> sig = signal(rsi_below(14, 30)) & signal(day_of_week(3))
        >>> entry_dates = apply_signal(stock, sig)
        >>> results = op.long_calls(data, entry_dates=entry_dates)
        >>>
        >>> # Chain multiple conditions
        >>> sig = (
        ...     signal(macd_cross_above())
        ...     & signal(atr_below(14, 0.75))
        ...     & signal(sma_above(50))
        ... )
        >>> entry_dates = apply_signal(stock, sig)
    """

    def __init__(self, func: SignalFunc) -> None:
        self._func = func

    def __call__(self, data: pd.DataFrame) -> "pd.Series[bool]":
        return self._func(data)

    def __and__(self, other: "Signal | SignalFunc") -> "Signal":
        def combined(data: pd.DataFrame) -> "pd.Series[bool]":
            return self(data) & other(data)

        return Signal(combined)

    def __or__(self, other: "Signal | SignalFunc") -> "Signal":
        def combined(data: pd.DataFrame) -> "pd.Series[bool]":
            return self(data) | other(data)

        return Signal(combined)

    def __repr__(self) -> str:
        return f"Signal({self._func!r})"


def signal(func: SignalFunc) -> Signal:
    """
    Wrap a signal function in a Signal for fluent operator chaining.

    Args:
        func: Any SignalFunc (e.g. rsi_below(14), macd_cross_above())

    Returns:
        Signal instance with & and | operator support

    Example:
        >>> sig = signal(rsi_below(14, 30)) & signal(day_of_week(3))
        >>> entry_dates = apply_signal(stock, sig)
        >>> results = op.long_calls(data, entry_dates=entry_dates)
    """
    return Signal(func)


# ---------------------------------------------------------------------------
# apply_signal — public helper to compute valid dates from a signal
# ---------------------------------------------------------------------------


def apply_signal(data: pd.DataFrame, signal_func: SignalFunc) -> pd.DataFrame:
    """
    Run a signal function on data and return valid (symbol, date) pairs.

    This decouples signal computation from the strategy engine.  Call this
    before running a strategy and pass the result as ``entry_dates`` or
    ``exit_dates``.

    The returned ``quote_date`` values are normalized to date-only so that
    they reliably match option chain dates from any provider, regardless
    of timezone or time-of-day differences.

    Args:
        data: DataFrame with at least ``underlying_symbol`` and ``quote_date``.
              For price-based signals (RSI, SMA, MACD, etc.), also needs
              ``underlying_price`` (or ``close``, which is auto-mapped).
              For OHLCV signals (ATR), also needs ``open``, ``high``,
              ``low``, ``volume``.
        signal_func: Callable that takes a DataFrame and returns a boolean
                     Series indicating which dates are valid.

    Returns:
        DataFrame with columns ``(underlying_symbol, quote_date)`` for
        dates where the signal is True.

    Example:
        >>> import optopsy as op
        >>> from optopsy.signals import rsi_below, day_of_week, apply_signal
        >>>
        >>> data = op.csv_data('./SPX_2018.csv')
        >>> stock = load_stock_data(...)  # OHLCV DataFrame
        >>>
        >>> # Compute entry dates where RSI < 30
        >>> entry_dates = apply_signal(stock, rsi_below(14, 30))
        >>>
        >>> # Pass pre-computed dates to the strategy
        >>> results = op.long_calls(data, entry_dates=entry_dates)
        >>>
        >>> # Date-only signals work with minimal data
        >>> friday_dates = apply_signal(data, day_of_week(4))
    """
    df = data.copy()
    if "underlying_price" not in df.columns and "close" in df.columns:
        df["underlying_price"] = df["close"]
    df["quote_date"] = normalize_dates(df["quote_date"])
    df = (
        df.drop_duplicates(["underlying_symbol", "quote_date"])
        .sort_values(["underlying_symbol", "quote_date"])
        .reset_index(drop=True)
    )
    mask = signal_func(df)
    return df.loc[mask, ["underlying_symbol", "quote_date"]].reset_index(drop=True)
