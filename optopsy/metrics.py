"""Risk-adjusted performance metrics for options strategy evaluation.

Provides standard risk metrics computed from returns series or equity curves.
Used by both the simulation layer (``simulator.py``) and the aggregated
strategy output (``core.py``) to enrich results beyond basic descriptive
statistics.

All functions accept pandas Series or numpy arrays and return scalar floats.
"""

from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd

_ArrayLike = Union[pd.Series, np.ndarray]

# Default annualisation factor: 252 trading days per year
_TRADING_DAYS = 252


def sharpe_ratio(
    returns: _ArrayLike,
    trading_days: int = _TRADING_DAYS,
    risk_free_rate: float = 0.0,
) -> float:
    """Annualised Sharpe ratio.

    ``(mean(returns) - risk_free_daily) / std(returns) * sqrt(trading_days)``

    Args:
        returns: Series of periodic returns (e.g. per-trade or daily).
        trading_days: Annualisation factor.
        risk_free_rate: Annual risk-free rate (default 0).

    Returns:
        Sharpe ratio as a float, or 0.0 if std is zero or data is empty.
    """
    returns = _to_array(returns)
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / trading_days
    excess = returns - daily_rf
    std = float(np.nanstd(excess, ddof=1))
    if std < 1e-12:
        return 0.0
    return float(np.nanmean(excess) / std * np.sqrt(trading_days))


def sortino_ratio(
    returns: _ArrayLike,
    trading_days: int = _TRADING_DAYS,
    risk_free_rate: float = 0.0,
) -> float:
    """Annualised Sortino ratio (penalises only downside deviation).

    More appropriate than Sharpe for asymmetric options payoffs.

    Args:
        returns: Series of periodic returns.
        trading_days: Annualisation factor.
        risk_free_rate: Annual risk-free rate (default 0).

    Returns:
        Sortino ratio as a float, or 0.0 if downside deviation is zero.
    """
    returns = _to_array(returns)
    if len(returns) < 2:
        return 0.0
    daily_rf = risk_free_rate / trading_days
    excess = returns - daily_rf
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 0.0
    downside_std = float(np.sqrt(np.nanmean(downside**2)))
    if downside_std == 0:
        return 0.0
    return float(np.nanmean(excess) / downside_std * np.sqrt(trading_days))


def max_drawdown(equity: _ArrayLike) -> float:
    """Maximum peak-to-trough drawdown as a negative fraction.

    Args:
        equity: Equity curve series (absolute values, not returns).

    Returns:
        Max drawdown as a negative float (e.g. -0.15 for 15% drawdown),
        or 0.0 if the equity curve is empty or monotonically increasing.
    """
    equity = _to_array(equity)
    if len(equity) < 2:
        return 0.0
    running_max = np.maximum.accumulate(equity)
    # Avoid division by zero for zero-equity entries
    mask = running_max > 0
    if not mask.any():
        return 0.0
    drawdowns = np.where(mask, (equity - running_max) / running_max, 0.0)
    return float(np.min(drawdowns))


def max_drawdown_from_returns(
    returns: _ArrayLike, initial_capital: float = 1.0
) -> float:
    """Compute max drawdown from a returns series by reconstructing the equity curve.

    Args:
        returns: Series of periodic returns.
        initial_capital: Starting equity value.

    Returns:
        Max drawdown as a negative float.
    """
    returns = _to_array(returns)
    if len(returns) == 0:
        return 0.0
    equity = initial_capital * np.cumprod(1 + returns)
    equity = np.insert(equity, 0, initial_capital)
    return max_drawdown(equity)


def value_at_risk(returns: _ArrayLike, confidence: float = 0.95) -> float:
    """Historical Value at Risk (VaR).

    The loss threshold at the given confidence level. For example, at 95%
    confidence, VaR is the 5th percentile of returns.

    Args:
        returns: Series of periodic returns.
        confidence: Confidence level (default 0.95).

    Returns:
        VaR as a float (typically negative, representing a loss).
        Returns 0.0 if data is empty.
    """
    returns = _to_array(returns)
    if len(returns) == 0:
        return 0.0
    return float(np.nanpercentile(returns, (1 - confidence) * 100))


def conditional_value_at_risk(returns: _ArrayLike, confidence: float = 0.95) -> float:
    """Conditional VaR (CVaR), also known as Expected Shortfall.

    Mean of returns that fall at or below the VaR threshold.

    Args:
        returns: Series of periodic returns.
        confidence: Confidence level (default 0.95).

    Returns:
        CVaR as a float (typically negative). Returns 0.0 if data is empty.
    """
    returns = _to_array(returns)
    if len(returns) == 0:
        return 0.0
    var = value_at_risk(returns, confidence)
    tail = returns[returns <= var]
    if len(tail) == 0:
        return float(var)
    return float(np.nanmean(tail))


def win_rate(pnl: _ArrayLike) -> float:
    """Fraction of trades with positive P&L.

    Args:
        pnl: Series of P&L values (absolute or percentage).

    Returns:
        Win rate as a float between 0 and 1. Returns 0.0 if empty.
    """
    pnl = _to_array(pnl)
    if len(pnl) == 0:
        return 0.0
    return float(np.nansum(pnl > 0) / len(pnl))


def profit_factor(pnl: _ArrayLike) -> float:
    """Ratio of gross profits to gross losses.

    ``sum(winning_trades) / abs(sum(losing_trades))``

    Args:
        pnl: Series of P&L values.

    Returns:
        Profit factor as a float. Returns inf if no losses, 0.0 if no wins
        or empty.
    """
    pnl = _to_array(pnl)
    if len(pnl) == 0:
        return 0.0
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    total_wins = float(np.nansum(wins))
    total_losses = float(np.nansum(losses))
    if total_losses == 0:
        return float("inf") if total_wins > 0 else 0.0
    return abs(total_wins / total_losses)


def calmar_ratio(
    returns: _ArrayLike,
    trading_days: int = _TRADING_DAYS,
    initial_capital: float = 1.0,
) -> float:
    """Calmar ratio: annualised return divided by max drawdown.

    Args:
        returns: Series of periodic returns.
        trading_days: Number of trading days per year for annualisation.
        initial_capital: Starting equity for drawdown computation.

    Returns:
        Calmar ratio as a float, or 0.0 if max drawdown is zero or data
        is insufficient.
    """
    returns = _to_array(returns)
    if len(returns) < 2:
        return 0.0
    ann_return = float(np.nanmean(returns)) * trading_days
    mdd = max_drawdown_from_returns(returns, initial_capital)
    if mdd == 0:
        return 0.0
    return float(ann_return / abs(mdd))


def compute_risk_metrics(
    returns: _ArrayLike,
    equity: _ArrayLike | None = None,
    trading_days: int = _TRADING_DAYS,
) -> dict[str, float]:
    """Compute all risk metrics from a returns series.

    Convenience function that returns a flat dict of all metrics. Used by
    both the simulation and aggregated strategy output paths.

    Args:
        returns: Series of periodic returns (per-trade pct_change).
        equity: Optional equity curve. If not provided, drawdown is computed
            from returns.
        trading_days: Annualisation factor.

    Returns:
        Dict with keys: sharpe_ratio, sortino_ratio, max_drawdown, var_95,
        cvar_95, win_rate, profit_factor, calmar_ratio.
    """
    returns = _to_array(returns)

    mdd = (
        max_drawdown(equity)
        if equity is not None and len(equity) > 0  # type: ignore[arg-type]
        else max_drawdown_from_returns(returns)
    )

    return {
        "sharpe_ratio": sharpe_ratio(returns, trading_days),
        "sortino_ratio": sortino_ratio(returns, trading_days),
        "max_drawdown": mdd,
        "var_95": value_at_risk(returns, 0.95),
        "cvar_95": conditional_value_at_risk(returns, 0.95),
        "win_rate": win_rate(returns),
        "profit_factor": profit_factor(returns),
        "calmar_ratio": calmar_ratio(returns, trading_days),
    }


def _to_array(data: _ArrayLike) -> np.ndarray:
    """Convert input to a flat numpy array, dropping NaNs."""
    arr = np.asarray(data)
    return arr[~np.isnan(arr)]
