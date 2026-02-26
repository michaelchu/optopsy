"""Overlap / moving-average signals: SMA, EMA, DEMA, TEMA, HMA, KAMA, WMA, ZLMA, ALMA."""

from typing import Callable

import pandas as pd
import pandas_ta_classic as ta

from ._helpers import SignalFunc, _crossover_signal, _per_symbol_signal

# ---------------------------------------------------------------------------
# SMA signals
# ---------------------------------------------------------------------------


def sma_below(period: int = 20) -> SignalFunc:
    """True when the underlying price is below its simple moving average."""
    return _per_symbol_signal(
        lambda p: ta.sma(p, length=period),
        lambda prices, sma: prices < sma,
    )


def sma_above(period: int = 20) -> SignalFunc:
    """True when the underlying price is above its simple moving average."""
    return _per_symbol_signal(
        lambda p: ta.sma(p, length=period),
        lambda prices, sma: prices > sma,
    )


# ---------------------------------------------------------------------------
# EMA crossover
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
    """True when the fast EMA crosses above the slow EMA (bullish golden cross)."""
    fast, slow = int(fast), int(slow)
    return _crossover_signal(_ema_lines(fast, slow), above=True)


def ema_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when the fast EMA crosses below the slow EMA (bearish death cross)."""
    fast, slow = int(fast), int(slow)
    return _crossover_signal(_ema_lines(fast, slow), above=False)


# ---------------------------------------------------------------------------
# DEMA crossover
# ---------------------------------------------------------------------------


def _dema_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ma = ta.dema(prices, length=fast)
        slow_ma = ta.dema(prices, length=slow)
        if fast_ma is None or slow_ma is None:
            return None, None
        return fast_ma, slow_ma

    return _compute


def dema_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast DEMA crosses above slow DEMA (bullish)."""
    return _crossover_signal(_dema_lines(int(fast), int(slow)), above=True)


def dema_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast DEMA crosses below slow DEMA (bearish)."""
    return _crossover_signal(_dema_lines(int(fast), int(slow)), above=False)


# ---------------------------------------------------------------------------
# TEMA crossover
# ---------------------------------------------------------------------------


def _tema_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ma = ta.tema(prices, length=fast)
        slow_ma = ta.tema(prices, length=slow)
        if fast_ma is None or slow_ma is None:
            return None, None
        return fast_ma, slow_ma

    return _compute


def tema_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast TEMA crosses above slow TEMA (bullish)."""
    return _crossover_signal(_tema_lines(int(fast), int(slow)), above=True)


def tema_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast TEMA crosses below slow TEMA (bearish)."""
    return _crossover_signal(_tema_lines(int(fast), int(slow)), above=False)


# ---------------------------------------------------------------------------
# HMA crossover
# ---------------------------------------------------------------------------


def _hma_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ma = ta.hma(prices, length=fast)
        slow_ma = ta.hma(prices, length=slow)
        if fast_ma is None or slow_ma is None:
            return None, None
        return fast_ma, slow_ma

    return _compute


def hma_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast HMA crosses above slow HMA (bullish)."""
    return _crossover_signal(_hma_lines(int(fast), int(slow)), above=True)


def hma_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast HMA crosses below slow HMA (bearish)."""
    return _crossover_signal(_hma_lines(int(fast), int(slow)), above=False)


# ---------------------------------------------------------------------------
# KAMA crossover
# ---------------------------------------------------------------------------


def _kama_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ma = ta.kama(prices, length=fast)
        slow_ma = ta.kama(prices, length=slow)
        if fast_ma is None or slow_ma is None:
            return None, None
        return fast_ma, slow_ma

    return _compute


def kama_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast KAMA crosses above slow KAMA (bullish)."""
    return _crossover_signal(_kama_lines(int(fast), int(slow)), above=True)


def kama_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast KAMA crosses below slow KAMA (bearish)."""
    return _crossover_signal(_kama_lines(int(fast), int(slow)), above=False)


# ---------------------------------------------------------------------------
# WMA crossover
# ---------------------------------------------------------------------------


def _wma_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ma = ta.wma(prices, length=fast)
        slow_ma = ta.wma(prices, length=slow)
        if fast_ma is None or slow_ma is None:
            return None, None
        return fast_ma, slow_ma

    return _compute


def wma_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast WMA crosses above slow WMA (bullish)."""
    return _crossover_signal(_wma_lines(int(fast), int(slow)), above=True)


def wma_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast WMA crosses below slow WMA (bearish)."""
    return _crossover_signal(_wma_lines(int(fast), int(slow)), above=False)


# ---------------------------------------------------------------------------
# ZLMA crossover
# ---------------------------------------------------------------------------


def _zlma_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ma = ta.zlma(prices, length=fast)
        slow_ma = ta.zlma(prices, length=slow)
        if fast_ma is None or slow_ma is None:
            return None, None
        return fast_ma, slow_ma

    return _compute


def zlma_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast ZLMA crosses above slow ZLMA (bullish)."""
    return _crossover_signal(_zlma_lines(int(fast), int(slow)), above=True)


def zlma_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast ZLMA crosses below slow ZLMA (bearish)."""
    return _crossover_signal(_zlma_lines(int(fast), int(slow)), above=False)


# ---------------------------------------------------------------------------
# ALMA crossover
# ---------------------------------------------------------------------------


def _alma_lines(
    fast: int, slow: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        fast_ma = ta.alma(prices, length=fast)
        slow_ma = ta.alma(prices, length=slow)
        if fast_ma is None or slow_ma is None:
            return None, None
        return fast_ma, slow_ma

    return _compute


def alma_cross_above(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast ALMA crosses above slow ALMA (bullish)."""
    return _crossover_signal(_alma_lines(int(fast), int(slow)), above=True)


def alma_cross_below(fast: int = 10, slow: int = 50) -> SignalFunc:
    """True when fast ALMA crosses below slow ALMA (bearish)."""
    return _crossover_signal(_alma_lines(int(fast), int(slow)), above=False)
