"""Momentum-based signals: RSI, MACD, Stochastic, CCI, Williams %R, ROC, PPO, etc."""

from typing import Callable

import pandas as pd
import pandas_ta_classic as ta

from ._helpers import (
    SignalFunc,
    _crossover_signal,
    _get_close,
    _get_hl,
    _get_ohlc,
    _ohlcv_signal,
    _per_symbol_signal,
)

# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


def _compute_rsi(prices: pd.Series, period: int) -> pd.Series:
    """Compute RSI using pandas_ta_classic (Wilder smoothing / RMA)."""
    result = ta.rsi(prices, length=period)
    if result is None:
        return pd.Series(float("nan"), index=prices.index)
    return result


def rsi_below(period: int = 14, threshold: float = 30) -> SignalFunc:
    """True when RSI is below a threshold (oversold condition)."""
    return _per_symbol_signal(
        lambda p: _compute_rsi(p, period),
        lambda _prices, rsi: rsi < threshold,
    )


def rsi_above(period: int = 14, threshold: float = 70) -> SignalFunc:
    """True when RSI is above a threshold (overbought condition)."""
    return _per_symbol_signal(
        lambda p: _compute_rsi(p, period),
        lambda _prices, rsi: rsi > threshold,
    )


# ---------------------------------------------------------------------------
# MACD crossover
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
    """True when the MACD line crosses above the signal line (bullish momentum)."""
    fast, slow, signal_period = int(fast), int(slow), int(signal_period)
    return _crossover_signal(_macd_lines(fast, slow, signal_period), above=True)


def macd_cross_below(
    fast: int = 12, slow: int = 26, signal_period: int = 9
) -> SignalFunc:
    """True when the MACD line crosses below the signal line (bearish momentum)."""
    fast, slow, signal_period = int(fast), int(slow), int(signal_period)
    return _crossover_signal(_macd_lines(fast, slow, signal_period), above=False)


# ---------------------------------------------------------------------------
# Stochastic Oscillator
# ---------------------------------------------------------------------------


def stoch_below(
    k_period: int = 14, d_period: int = 3, threshold: float = 20
) -> SignalFunc:
    """True when Stochastic %K is below threshold (oversold)."""
    col = f"STOCHk_{k_period}_{d_period}_{d_period}"

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        result = ta.stoch(high, low, close, k=k_period, d=d_period)
        if result is None or col not in result.columns:
            return None
        return result[col]

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


def stoch_above(
    k_period: int = 14, d_period: int = 3, threshold: float = 80
) -> SignalFunc:
    """True when Stochastic %K is above threshold (overbought)."""
    col = f"STOCHk_{k_period}_{d_period}_{d_period}"

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        result = ta.stoch(high, low, close, k=k_period, d=d_period)
        if result is None or col not in result.columns:
            return None
        return result[col]

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


# ---------------------------------------------------------------------------
# Stochastic RSI
# ---------------------------------------------------------------------------


def stochrsi_below(
    period: int = 14,
    rsi_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
    threshold: float = 20,
) -> SignalFunc:
    """True when StochRSI %K is below threshold (oversold)."""
    col = f"STOCHRSIk_{period}_{rsi_period}_{k_smooth}_{d_smooth}"

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        close = _get_close(group)
        if close is None:
            return None
        result = ta.stochrsi(
            close, length=period, rsi_length=rsi_period, k=k_smooth, d=d_smooth
        )
        if result is None or col not in result.columns:
            return None
        return result[col]

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


def stochrsi_above(
    period: int = 14,
    rsi_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
    threshold: float = 80,
) -> SignalFunc:
    """True when StochRSI %K is above threshold (overbought)."""
    col = f"STOCHRSIk_{period}_{rsi_period}_{k_smooth}_{d_smooth}"

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        close = _get_close(group)
        if close is None:
            return None
        result = ta.stochrsi(
            close, length=period, rsi_length=rsi_period, k=k_smooth, d=d_smooth
        )
        if result is None or col not in result.columns:
            return None
        return result[col]

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


# ---------------------------------------------------------------------------
# Williams %R
# ---------------------------------------------------------------------------


def willr_below(period: int = 14, threshold: float = -80) -> SignalFunc:
    """True when Williams %R is below threshold (oversold, default -80)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        result = ta.willr(high, low, close, length=period)
        return result

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


def willr_above(period: int = 14, threshold: float = -20) -> SignalFunc:
    """True when Williams %R is above threshold (overbought, default -20)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        result = ta.willr(high, low, close, length=period)
        return result

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


# ---------------------------------------------------------------------------
# CCI (Commodity Channel Index)
# ---------------------------------------------------------------------------


def cci_below(period: int = 20, threshold: float = -100) -> SignalFunc:
    """True when CCI is below threshold (oversold, default -100)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        return ta.cci(high, low, close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


def cci_above(period: int = 20, threshold: float = 100) -> SignalFunc:
    """True when CCI is above threshold (overbought, default 100)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        return ta.cci(high, low, close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


# ---------------------------------------------------------------------------
# ROC (Rate of Change)
# ---------------------------------------------------------------------------


def roc_above(period: int = 10, threshold: float = 0) -> SignalFunc:
    """True when Rate of Change is above threshold (positive momentum)."""
    return _per_symbol_signal(
        lambda p: ta.roc(p, length=period),
        lambda _prices, roc: roc > threshold,
    )


def roc_below(period: int = 10, threshold: float = 0) -> SignalFunc:
    """True when Rate of Change is below threshold (negative momentum)."""
    return _per_symbol_signal(
        lambda p: ta.roc(p, length=period),
        lambda _prices, roc: roc < threshold,
    )


# ---------------------------------------------------------------------------
# PPO (Percentage Price Oscillator) crossover
# ---------------------------------------------------------------------------


def _ppo_lines(
    fast: int, slow: int, signal_period: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    """Return (PPO_line, PPO_signal_line) from prices."""
    ppo_col = f"PPO_{fast}_{slow}_{signal_period}"
    sig_col = f"PPOs_{fast}_{slow}_{signal_period}"

    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        result = ta.ppo(prices, fast=fast, slow=slow, signal=signal_period)
        if result is None:
            return None, None
        if ppo_col not in result.columns or sig_col not in result.columns:
            return None, None
        return result[ppo_col], result[sig_col]

    return _compute


def ppo_cross_above(
    fast: int = 12, slow: int = 26, signal_period: int = 9
) -> SignalFunc:
    """True when PPO line crosses above its signal line (bullish)."""
    return _crossover_signal(_ppo_lines(fast, slow, signal_period), above=True)


def ppo_cross_below(
    fast: int = 12, slow: int = 26, signal_period: int = 9
) -> SignalFunc:
    """True when PPO line crosses below its signal line (bearish)."""
    return _crossover_signal(_ppo_lines(fast, slow, signal_period), above=False)


# ---------------------------------------------------------------------------
# TSI (True Strength Index) crossover
# ---------------------------------------------------------------------------


def _tsi_lines(
    long: int, short: int, signal_period: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    """Return (TSI_line, TSI_signal_line) from prices."""
    tsi_col = f"TSI_{long}_{short}_{signal_period}"
    sig_col = f"TSIs_{long}_{short}_{signal_period}"

    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        result = ta.tsi(prices, long=long, short=short, signal=signal_period)
        if result is None:
            return None, None
        if tsi_col not in result.columns or sig_col not in result.columns:
            return None, None
        return result[tsi_col], result[sig_col]

    return _compute


def tsi_cross_above(
    long: int = 25, short: int = 13, signal_period: int = 13
) -> SignalFunc:
    """True when TSI crosses above its signal line (bullish)."""
    return _crossover_signal(_tsi_lines(long, short, signal_period), above=True)


def tsi_cross_below(
    long: int = 25, short: int = 13, signal_period: int = 13
) -> SignalFunc:
    """True when TSI crosses below its signal line (bearish)."""
    return _crossover_signal(_tsi_lines(long, short, signal_period), above=False)


# ---------------------------------------------------------------------------
# CMO (Chande Momentum Oscillator)
# ---------------------------------------------------------------------------


def cmo_above(period: int = 14, threshold: float = 50) -> SignalFunc:
    """True when CMO is above threshold (strong bullish momentum)."""
    return _per_symbol_signal(
        lambda p: ta.cmo(p, length=period),
        lambda _prices, cmo: cmo > threshold,
    )


def cmo_below(period: int = 14, threshold: float = -50) -> SignalFunc:
    """True when CMO is below threshold (strong bearish momentum)."""
    return _per_symbol_signal(
        lambda p: ta.cmo(p, length=period),
        lambda _prices, cmo: cmo < threshold,
    )


# ---------------------------------------------------------------------------
# UO (Ultimate Oscillator)
# ---------------------------------------------------------------------------


def uo_above(
    fast: int = 7, medium: int = 14, slow: int = 28, threshold: float = 70
) -> SignalFunc:
    """True when Ultimate Oscillator is above threshold (overbought)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        return ta.uo(high, low, close, fast=fast, medium=medium, slow=slow)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def uo_below(
    fast: int = 7, medium: int = 14, slow: int = 28, threshold: float = 30
) -> SignalFunc:
    """True when Ultimate Oscillator is below threshold (oversold)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        return ta.uo(high, low, close, fast=fast, medium=medium, slow=slow)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


# ---------------------------------------------------------------------------
# Squeeze (Bollinger Bands + Keltner Channel)
# ---------------------------------------------------------------------------


def squeeze_on(
    bb_length: int = 20,
    bb_std: float = 2.0,
    kc_length: int = 20,
    kc_scalar: float = 1.5,
) -> SignalFunc:
    """True when the Squeeze is on (low volatility compression).

    The squeeze fires when Bollinger Bands are inside Keltner Channels,
    indicating a period of low volatility that often precedes a breakout.
    """

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        result = ta.squeeze(
            high,
            low,
            close,
            bb_length=bb_length,
            bb_std=bb_std,
            kc_length=kc_length,
            kc_scalar=kc_scalar,
        )
        if result is None:
            return None
        sq_col = f"SQZ_{bb_length}_{bb_std}_{kc_length}_{kc_scalar}"
        if sq_col not in result.columns:
            # Try alternate column naming
            for col in result.columns:
                if col.startswith("SQZ_"):
                    return result[col]
            return None
        return result[sq_col]

    # SQZ column: 0 = squeeze on (BB inside KC), 1 = no squeeze
    return _ohlcv_signal(_indicator, lambda ind: ind == 0)


def squeeze_off(
    bb_length: int = 20,
    bb_std: float = 2.0,
    kc_length: int = 20,
    kc_scalar: float = 1.5,
) -> SignalFunc:
    """True when the Squeeze is off (volatility expansion).

    The squeeze releases when Bollinger Bands expand outside Keltner Channels.
    """

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        result = ta.squeeze(
            high,
            low,
            close,
            bb_length=bb_length,
            bb_std=bb_std,
            kc_length=kc_length,
            kc_scalar=kc_scalar,
        )
        if result is None:
            return None
        sq_col = f"SQZ_{bb_length}_{bb_std}_{kc_length}_{kc_scalar}"
        if sq_col not in result.columns:
            for col in result.columns:
                if col.startswith("SQZ_"):
                    return result[col]
            return None
        return result[sq_col]

    return _ohlcv_signal(_indicator, lambda ind: ind == 1)


# ---------------------------------------------------------------------------
# AO (Awesome Oscillator)
# ---------------------------------------------------------------------------


def ao_above(fast: int = 5, slow: int = 34, threshold: float = 0) -> SignalFunc:
    """True when Awesome Oscillator is above threshold (bullish momentum)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        hl = _get_hl(group)
        if hl is None:
            return None
        high, low = hl
        return ta.ao(high, low, fast=fast, slow=slow)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def ao_below(fast: int = 5, slow: int = 34, threshold: float = 0) -> SignalFunc:
    """True when Awesome Oscillator is below threshold (bearish momentum)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        hl = _get_hl(group)
        if hl is None:
            return None
        high, low = hl
        return ta.ao(high, low, fast=fast, slow=slow)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


# ---------------------------------------------------------------------------
# SMI (Stochastic Momentum Index) crossover
# ---------------------------------------------------------------------------


def _smi_lines(
    fast: int, slow: int, signal_period: int
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    """Return (SMI_line, SMI_signal) from prices."""
    smi_col = f"SMI_{fast}_{slow}_{signal_period}"
    sig_col = f"SMIs_{fast}_{slow}_{signal_period}"

    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        result = ta.smi(prices, fast=fast, slow=slow, signal=signal_period)
        if result is None:
            return None, None
        if smi_col not in result.columns or sig_col not in result.columns:
            return None, None
        return result[smi_col], result[sig_col]

    return _compute


def smi_cross_above(
    fast: int = 5, slow: int = 20, signal_period: int = 5
) -> SignalFunc:
    """True when SMI crosses above its signal line (bullish)."""
    return _crossover_signal(_smi_lines(fast, slow, signal_period), above=True)


def smi_cross_below(
    fast: int = 5, slow: int = 20, signal_period: int = 5
) -> SignalFunc:
    """True when SMI crosses below its signal line (bearish)."""
    return _crossover_signal(_smi_lines(fast, slow, signal_period), above=False)


# ---------------------------------------------------------------------------
# KST (Know Sure Thing) crossover
# ---------------------------------------------------------------------------


def _kst_lines(
    prices: pd.Series,
) -> tuple[pd.Series | None, pd.Series | None]:
    """Compute (KST_line, KST_signal) from prices."""
    result = ta.kst(prices)
    if result is None:
        return None, None
    kst_cols = [c for c in result.columns if c.startswith("KST_")]
    sig_cols = [c for c in result.columns if c.startswith("KSTs_")]
    if not kst_cols or not sig_cols:
        return None, None
    return result[kst_cols[0]], result[sig_cols[0]]


def kst_cross_above() -> SignalFunc:
    """True when KST crosses above its signal line (bullish)."""
    return _crossover_signal(_kst_lines, above=True)


def kst_cross_below() -> SignalFunc:
    """True when KST crosses below its signal line (bearish)."""
    return _crossover_signal(_kst_lines, above=False)


# ---------------------------------------------------------------------------
# Fisher Transform crossover
# ---------------------------------------------------------------------------


def _fisher_lines(
    period: int,
) -> Callable[[pd.Series], tuple[pd.Series | None, pd.Series | None]]:
    """Return (Fisher, Fisher_signal) from prices."""

    def _compute(prices: pd.Series) -> tuple[pd.Series | None, pd.Series | None]:
        # Fisher needs high/low but will work with just close as both
        result = ta.fisher(prices, prices, length=period)
        if result is None:
            return None, None
        fisher_cols = [c for c in result.columns if c.startswith("FISHERT_")]
        signal_cols = [c for c in result.columns if c.startswith("FISHERTs_")]
        if not fisher_cols or not signal_cols:
            return None, None
        return result[fisher_cols[0]], result[signal_cols[0]]

    return _compute


def fisher_cross_above(period: int = 9) -> SignalFunc:
    """True when Fisher Transform crosses above its signal line (bullish)."""
    return _crossover_signal(_fisher_lines(period), above=True)


def fisher_cross_below(period: int = 9) -> SignalFunc:
    """True when Fisher Transform crosses below its signal line (bearish)."""
    return _crossover_signal(_fisher_lines(period), above=False)
