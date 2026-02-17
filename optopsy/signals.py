"""
Entry signal filters for controlling when option positions are entered.

Signals are functions that take a DataFrame of underlying price data
(with columns: underlying_symbol, quote_date, underlying_price) and
return a boolean Series indicating which dates are valid for entry.

Built-in signals can be combined with and_signals() and or_signals().

Example:
    >>> from optopsy.signals import rsi_below, day_of_week, and_signals
    >>> import optopsy as op
    >>> data = op.csv_data('./SPX_2018.csv')
    >>> # Enter long calls only on Thursdays when RSI(14) < 30
    >>> results = op.long_calls(
    ...     data,
    ...     max_entry_dte=1,
    ...     exit_dte=0,
    ...     entry_signal=and_signals(
    ...         rsi_below(period=14, threshold=30),
    ...         day_of_week(3),  # Thursday
    ...     ),
    ...     raw=True,
    ... )
"""

from typing import Callable, List

import numpy as np
import pandas as pd

# Signal function type: takes a DataFrame with (underlying_symbol, quote_date,
# underlying_price) and returns a boolean Series indicating valid entry dates.
SignalFunc = Callable[[pd.DataFrame], "pd.Series[bool]"]


def _compute_rsi(prices: pd.Series, period: int) -> pd.Series:
    """
    Compute the Relative Strength Index (RSI) for a price series.

    Uses the standard Wilder smoothing method (exponential moving average).

    Args:
        prices: Series of prices sorted chronologically
        period: Lookback period for RSI calculation

    Returns:
        Series of RSI values (0-100), with NaN for the first `period` entries
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def rsi_below(period: int = 14, threshold: float = 30) -> SignalFunc:
    """
    Create a signal that is True when RSI is below a threshold (oversold).

    Args:
        period: RSI lookback period (default 14)
        threshold: RSI threshold value (default 30)

    Returns:
        Signal function
    """

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for symbol in data["underlying_symbol"].unique():
            mask = data["underlying_symbol"] == symbol
            prices = data.loc[mask, "underlying_price"]
            rsi = _compute_rsi(prices, period)
            result.loc[mask] = rsi < threshold
        return result

    return signal


def rsi_above(period: int = 14, threshold: float = 70) -> SignalFunc:
    """
    Create a signal that is True when RSI is above a threshold (overbought).

    Args:
        period: RSI lookback period (default 14)
        threshold: RSI threshold value (default 70)

    Returns:
        Signal function
    """

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for symbol in data["underlying_symbol"].unique():
            mask = data["underlying_symbol"] == symbol
            prices = data.loc[mask, "underlying_price"]
            rsi = _compute_rsi(prices, period)
            result.loc[mask] = rsi > threshold
        return result

    return signal


def day_of_week(*days: int) -> SignalFunc:
    """
    Create a signal that is True on specific days of the week.

    Args:
        *days: Day numbers where Monday=0, Tuesday=1, ..., Sunday=6.
               For example, day_of_week(3) filters for Thursdays.

    Returns:
        Signal function
    """
    day_set = set(days)

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        return data["quote_date"].dt.dayofweek.isin(day_set)

    return signal


def sma_below(period: int = 20) -> SignalFunc:
    """
    Create a signal that is True when the underlying price is below its
    simple moving average (potential oversold / downtrend condition).

    Args:
        period: SMA lookback period (default 20)

    Returns:
        Signal function
    """

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for symbol in data["underlying_symbol"].unique():
            mask = data["underlying_symbol"] == symbol
            prices = data.loc[mask, "underlying_price"]
            sma = prices.rolling(window=period, min_periods=period).mean()
            result.loc[mask] = prices < sma
        return result

    return signal


def sma_above(period: int = 20) -> SignalFunc:
    """
    Create a signal that is True when the underlying price is above its
    simple moving average (potential uptrend condition).

    Args:
        period: SMA lookback period (default 20)

    Returns:
        Signal function
    """

    def signal(data: pd.DataFrame) -> "pd.Series[bool]":
        result = pd.Series(False, index=data.index)
        for symbol in data["underlying_symbol"].unique():
            mask = data["underlying_symbol"] == symbol
            prices = data.loc[mask, "underlying_price"]
            sma = prices.rolling(window=period, min_periods=period).mean()
            result.loc[mask] = prices > sma
        return result

    return signal


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
