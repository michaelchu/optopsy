"""Entry/exit signal filters for controlling when option positions are entered or exited.

Signals are functions that take a DataFrame of underlying price data
(with columns: underlying_symbol, quote_date, close) and return a boolean
Series indicating which dates are valid for entry/exit.

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

# Type alias
# Combinators, Signal class, apply_signal, custom_signal
from ._combinators import (
    Signal,
    and_signals,
    apply_signal,
    custom_signal,
    or_signals,
    signal,
    sustained,
)

# Internal helpers — re-exported for backward compatibility with tests
from ._helpers import (
    SignalFunc,
    # New helpers
    _band_signal,
    _crossover_signal,
    _direction_signal,
    _get_close,
    _get_high,
    _get_low,
    _get_volume,
    _groupby_symbol,
    _ohlcv_crossover_signal,
    _ohlcv_signal,
    _per_symbol_signal,
)

# --- Calendar signals ---
from .calendar_signal import day_of_week

# --- IV rank signals ---
from .iv import (
    _compute_atm_iv,
    _compute_iv_rank_series,
    iv_rank_above,
    iv_rank_below,
)

# --- Momentum signals ---
from .momentum import (
    # RSI
    _compute_rsi,
    # AO
    ao_above,
    ao_below,
    # CCI
    cci_above,
    cci_below,
    # CMO
    cmo_above,
    cmo_below,
    # Fisher crossover
    fisher_cross_above,
    fisher_cross_below,
    # KST crossover
    kst_cross_above,
    kst_cross_below,
    # MACD
    macd_cross_above,
    macd_cross_below,
    # PPO crossover
    ppo_cross_above,
    ppo_cross_below,
    # ROC
    roc_above,
    roc_below,
    rsi_above,
    rsi_below,
    # SMI crossover
    smi_cross_above,
    smi_cross_below,
    # Squeeze
    squeeze_off,
    squeeze_on,
    # Stochastic
    stoch_above,
    stoch_below,
    # StochRSI
    stochrsi_above,
    stochrsi_below,
    # TSI crossover
    tsi_cross_above,
    tsi_cross_below,
    # UO
    uo_above,
    uo_below,
    # Williams %R
    willr_above,
    willr_below,
)

# --- Overlap / moving-average signals ---
from .overlap import (
    # ALMA crossover
    alma_cross_above,
    alma_cross_below,
    # DEMA crossover
    dema_cross_above,
    dema_cross_below,
    # EMA crossover
    ema_cross_above,
    ema_cross_below,
    # HMA crossover
    hma_cross_above,
    hma_cross_below,
    # KAMA crossover
    kama_cross_above,
    kama_cross_below,
    # SMA
    sma_above,
    sma_below,
    # TEMA crossover
    tema_cross_above,
    tema_cross_below,
    # WMA crossover
    wma_cross_above,
    wma_cross_below,
    # ZLMA crossover
    zlma_cross_above,
    zlma_cross_below,
)

# --- Trend signals ---
from .trend import (
    # ADX
    adx_above,
    adx_below,
    # Aroon crossover
    aroon_cross_above,
    aroon_cross_below,
    # Choppiness
    chop_above,
    chop_below,
    # PSAR
    psar_buy,
    psar_sell,
    # Supertrend
    supertrend_buy,
    supertrend_sell,
    # VHF
    vhf_above,
    vhf_below,
)

# --- Volatility signals ---
from .volatility import (
    # ATR
    _compute_atr,
    atr_above,
    atr_below,
    # Bollinger Bands
    bb_above_upper,
    bb_below_lower,
    # Donchian Channel
    donchian_above_upper,
    donchian_below_lower,
    # Keltner Channel
    kc_above_upper,
    kc_below_lower,
    # Mass Index
    massi_above,
    massi_below,
    # NATR
    natr_above,
    natr_below,
)

# --- Volume signals ---
from .volume import (
    # AD crossover with SMA
    ad_cross_above_sma,
    ad_cross_below_sma,
    # CMF
    cmf_above,
    cmf_below,
    # MFI
    mfi_above,
    mfi_below,
    # OBV crossover with SMA
    obv_cross_above_sma,
    obv_cross_below_sma,
)

__all__ = [
    # Type alias
    "SignalFunc",
    # Combinators & utilities
    "and_signals",
    "or_signals",
    "sustained",
    "custom_signal",
    "Signal",
    "signal",
    "apply_signal",
    # Momentum
    "rsi_below",
    "rsi_above",
    "macd_cross_above",
    "macd_cross_below",
    "stoch_below",
    "stoch_above",
    "stochrsi_below",
    "stochrsi_above",
    "willr_below",
    "willr_above",
    "cci_below",
    "cci_above",
    "roc_above",
    "roc_below",
    "ppo_cross_above",
    "ppo_cross_below",
    "tsi_cross_above",
    "tsi_cross_below",
    "cmo_above",
    "cmo_below",
    "uo_above",
    "uo_below",
    "squeeze_on",
    "squeeze_off",
    "ao_above",
    "ao_below",
    "smi_cross_above",
    "smi_cross_below",
    "kst_cross_above",
    "kst_cross_below",
    "fisher_cross_above",
    "fisher_cross_below",
    # Overlap
    "sma_below",
    "sma_above",
    "ema_cross_above",
    "ema_cross_below",
    "dema_cross_above",
    "dema_cross_below",
    "tema_cross_above",
    "tema_cross_below",
    "hma_cross_above",
    "hma_cross_below",
    "kama_cross_above",
    "kama_cross_below",
    "wma_cross_above",
    "wma_cross_below",
    "zlma_cross_above",
    "zlma_cross_below",
    "alma_cross_above",
    "alma_cross_below",
    # Volatility
    "atr_above",
    "atr_below",
    "bb_above_upper",
    "bb_below_lower",
    "kc_above_upper",
    "kc_below_lower",
    "donchian_above_upper",
    "donchian_below_lower",
    "natr_above",
    "natr_below",
    "massi_above",
    "massi_below",
    # Trend
    "adx_above",
    "adx_below",
    "aroon_cross_above",
    "aroon_cross_below",
    "supertrend_buy",
    "supertrend_sell",
    "psar_buy",
    "psar_sell",
    "chop_above",
    "chop_below",
    "vhf_above",
    "vhf_below",
    # Volume
    "mfi_above",
    "mfi_below",
    "obv_cross_above_sma",
    "obv_cross_below_sma",
    "cmf_above",
    "cmf_below",
    "ad_cross_above_sma",
    "ad_cross_below_sma",
    # IV rank
    "iv_rank_above",
    "iv_rank_below",
    # Calendar
    "day_of_week",
]
