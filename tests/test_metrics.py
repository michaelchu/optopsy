"""Tests for the risk metrics module."""


import numpy as np
import pandas as pd
import pytest

from optopsy.metrics import (
    calmar_ratio,
    compute_risk_metrics,
    conditional_value_at_risk,
    max_drawdown,
    max_drawdown_from_returns,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    value_at_risk,
    win_rate,
)

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

# Simple known returns: [+10%, -5%, +3%, -2%, +7%]
_SIMPLE_RETURNS = np.array([0.10, -0.05, 0.03, -0.02, 0.07])

# All positive returns (no losses)
_ALL_WINS = np.array([0.05, 0.10, 0.03, 0.02])

# All negative returns (no wins)
_ALL_LOSSES = np.array([-0.05, -0.10, -0.03, -0.02])

# Single element
_SINGLE = np.array([0.05])

# Empty
_EMPTY = np.array([])


# ---------------------------------------------------------------------------
# sharpe_ratio
# ---------------------------------------------------------------------------


class TestSharpeRatio:
    def test_basic_computation(self):
        result = sharpe_ratio(_SIMPLE_RETURNS)
        # mean=0.026, std~0.0586, sharpe = 0.026/0.0586 * sqrt(252) ≈ 7.04
        assert result > 0
        assert isinstance(result, float)

    def test_empty_returns_zero(self):
        assert sharpe_ratio(_EMPTY) == 0.0

    def test_single_element_returns_zero(self):
        assert sharpe_ratio(_SINGLE) == 0.0

    def test_constant_returns_zero_std(self):
        constant = np.array([0.05, 0.05, 0.05])
        assert sharpe_ratio(constant) == 0.0

    def test_negative_sharpe(self):
        result = sharpe_ratio(_ALL_LOSSES)
        assert result < 0

    def test_pandas_series_input(self):
        series = pd.Series(_SIMPLE_RETURNS)
        result = sharpe_ratio(series)
        assert result > 0

    def test_with_risk_free_rate(self):
        # Higher risk-free rate should reduce sharpe
        base = sharpe_ratio(_SIMPLE_RETURNS, risk_free_rate=0.0)
        with_rf = sharpe_ratio(_SIMPLE_RETURNS, risk_free_rate=0.05)
        assert with_rf < base

    def test_nan_handling(self):
        data = np.array([0.10, np.nan, -0.05, 0.03])
        result = sharpe_ratio(data)
        # NaNs are dropped, should still compute
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# sortino_ratio
# ---------------------------------------------------------------------------


class TestSortinoRatio:
    def test_basic_computation(self):
        result = sortino_ratio(_SIMPLE_RETURNS)
        assert result > 0
        assert isinstance(result, float)

    def test_empty_returns_zero(self):
        assert sortino_ratio(_EMPTY) == 0.0

    def test_single_element_returns_zero(self):
        assert sortino_ratio(_SINGLE) == 0.0

    def test_all_positive_returns_zero(self):
        # No downside deviation — returns 0 because downside is empty
        assert sortino_ratio(_ALL_WINS) == 0.0

    def test_higher_than_sharpe_for_positive_skew(self):
        # For positive-skewed returns, Sortino should be >= Sharpe
        # because it ignores upside volatility
        s = sharpe_ratio(_SIMPLE_RETURNS)
        so = sortino_ratio(_SIMPLE_RETURNS)
        assert so >= s


# ---------------------------------------------------------------------------
# max_drawdown
# ---------------------------------------------------------------------------


class TestMaxDrawdown:
    def test_basic_drawdown(self):
        equity = np.array([100, 110, 105, 115, 100])
        result = max_drawdown(equity)
        # Peak at 115, trough at 100 → dd = (100-115)/115 ≈ -0.1304
        assert result == pytest.approx(-15 / 115, abs=1e-4)

    def test_monotonically_increasing(self):
        equity = np.array([100, 110, 120, 130])
        assert max_drawdown(equity) == 0.0

    def test_empty_returns_zero(self):
        assert max_drawdown(np.array([])) == 0.0

    def test_single_element(self):
        assert max_drawdown(np.array([100])) == 0.0

    def test_from_returns(self):
        returns = np.array([0.10, -0.20, 0.05])
        result = max_drawdown_from_returns(returns)
        # equity: 1.0, 1.10, 0.88, 0.924
        # dd from 1.10 to 0.88 = -0.20
        assert result == pytest.approx(-0.20, abs=1e-4)


# ---------------------------------------------------------------------------
# value_at_risk
# ---------------------------------------------------------------------------


class TestVaR:
    def test_basic_var(self):
        result = value_at_risk(_SIMPLE_RETURNS, 0.95)
        # 5th percentile of [−0.05, −0.02, 0.03, 0.07, 0.10]
        assert result < 0

    def test_empty_returns_zero(self):
        assert value_at_risk(_EMPTY) == 0.0

    def test_all_positive(self):
        result = value_at_risk(_ALL_WINS, 0.95)
        # Even all positive, the 5th percentile is still positive
        assert result >= 0

    def test_higher_confidence_lower_var(self):
        var_95 = value_at_risk(_SIMPLE_RETURNS, 0.95)
        var_99 = value_at_risk(_SIMPLE_RETURNS, 0.99)
        # 99% VaR should be more extreme (lower) than 95%
        assert var_99 <= var_95


# ---------------------------------------------------------------------------
# conditional_value_at_risk
# ---------------------------------------------------------------------------


class TestCVaR:
    def test_basic_cvar(self):
        result = conditional_value_at_risk(_SIMPLE_RETURNS, 0.95)
        # CVaR is the mean of returns <= VaR
        assert result <= value_at_risk(_SIMPLE_RETURNS, 0.95)

    def test_empty_returns_zero(self):
        assert conditional_value_at_risk(_EMPTY) == 0.0

    def test_cvar_worse_than_var(self):
        # CVaR should always be <= VaR (more extreme)
        var = value_at_risk(_SIMPLE_RETURNS, 0.95)
        cvar = conditional_value_at_risk(_SIMPLE_RETURNS, 0.95)
        assert cvar <= var


# ---------------------------------------------------------------------------
# win_rate
# ---------------------------------------------------------------------------


class TestWinRate:
    def test_basic_win_rate(self):
        result = win_rate(_SIMPLE_RETURNS)
        # 3 positive out of 5
        assert result == pytest.approx(3 / 5)

    def test_empty_returns_zero(self):
        assert win_rate(_EMPTY) == 0.0

    def test_all_wins(self):
        assert win_rate(_ALL_WINS) == 1.0

    def test_all_losses(self):
        assert win_rate(_ALL_LOSSES) == 0.0

    def test_with_nans(self):
        data = np.array([0.10, np.nan, -0.05])
        # NaN is dropped, so 1 win out of 2
        assert win_rate(data) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# profit_factor
# ---------------------------------------------------------------------------


class TestProfitFactor:
    def test_basic_profit_factor(self):
        result = profit_factor(_SIMPLE_RETURNS)
        # wins: 0.10 + 0.03 + 0.07 = 0.20
        # losses: -0.05 + -0.02 = -0.07
        # pf = 0.20 / 0.07 ≈ 2.857
        assert result == pytest.approx(0.20 / 0.07, abs=1e-3)

    def test_empty_returns_zero(self):
        assert profit_factor(_EMPTY) == 0.0

    def test_all_wins_returns_inf(self):
        assert profit_factor(_ALL_WINS) == float("inf")

    def test_all_losses_returns_zero(self):
        assert profit_factor(_ALL_LOSSES) == 0.0


# ---------------------------------------------------------------------------
# calmar_ratio
# ---------------------------------------------------------------------------


class TestCalmarRatio:
    def test_basic_computation(self):
        result = calmar_ratio(_SIMPLE_RETURNS)
        assert isinstance(result, float)

    def test_empty_returns_zero(self):
        assert calmar_ratio(_EMPTY) == 0.0

    def test_single_element_returns_zero(self):
        assert calmar_ratio(_SINGLE) == 0.0

    def test_monotonically_increasing_returns_zero(self):
        # No drawdown → calmar is 0
        assert calmar_ratio(_ALL_WINS) == 0.0


# ---------------------------------------------------------------------------
# compute_risk_metrics (convenience function)
# ---------------------------------------------------------------------------


class TestComputeRiskMetrics:
    def test_returns_all_keys(self):
        result = compute_risk_metrics(_SIMPLE_RETURNS)
        expected_keys = {
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "var_95",
            "cvar_95",
            "win_rate",
            "profit_factor",
            "calmar_ratio",
        }
        assert set(result.keys()) == expected_keys

    def test_empty_returns(self):
        result = compute_risk_metrics(_EMPTY)
        assert result["sharpe_ratio"] == 0.0
        assert result["win_rate"] == 0.0

    def test_with_equity_curve(self):
        equity = pd.Series([100, 110, 105, 115, 120])
        result = compute_risk_metrics(_SIMPLE_RETURNS, equity=equity)
        # Should use equity-based drawdown, not returns-based
        assert result["max_drawdown"] == pytest.approx(
            max_drawdown(equity.values), abs=1e-6
        )

    def test_all_values_are_floats(self):
        result = compute_risk_metrics(_SIMPLE_RETURNS)
        for key, val in result.items():
            assert isinstance(val, float), f"{key} is not float: {type(val)}"


# ---------------------------------------------------------------------------
# Integration: simulator summary includes risk metrics
# ---------------------------------------------------------------------------


class TestSimulatorIntegration:
    """Verify that the simulator's _compute_summary includes risk metrics."""

    def test_empty_summary_has_risk_keys(self):
        from optopsy.simulator import _compute_summary

        summary = _compute_summary(pd.DataFrame(), capital=100_000)
        for key in (
            "sharpe_ratio",
            "sortino_ratio",
            "var_95",
            "cvar_95",
            "calmar_ratio",
        ):
            assert key in summary, f"Missing key: {key}"
            assert summary[key] == 0.0

    def test_populated_summary_has_risk_keys(self):
        from optopsy.simulator import _compute_summary

        trade_log = pd.DataFrame(
            {
                "realized_pnl": [100, -50, 75, -25, 60],
                "equity": [100100, 100050, 100125, 100100, 100160],
                "pct_change": [0.10, -0.05, 0.075, -0.025, 0.06],
                "days_held": [30, 25, 28, 20, 35],
            }
        )
        summary = _compute_summary(trade_log, capital=100_000)
        assert summary["sharpe_ratio"] != 0.0
        assert summary["sortino_ratio"] != 0.0
        assert "var_95" in summary
        assert "cvar_95" in summary
        assert "calmar_ratio" in summary


# ---------------------------------------------------------------------------
# Integration: aggregated strategy output includes win_rate & profit_factor
# ---------------------------------------------------------------------------


class TestAggregatedOutput:
    """Verify that aggregated strategy output includes new columns."""

    def test_describe_cols_include_new_metrics(self):
        from optopsy.definitions import describe_cols

        assert "win_rate" in describe_cols
        assert "profit_factor" in describe_cols
