"""Tests for multi-symbol portfolio simulation."""

import datetime

import pandas as pd
import pytest

import optopsy as op
from optopsy.simulator import (
    PortfolioResult,
    SimulationResult,
    simulate,
    simulate_portfolio,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_CHAIN_COLS = [
    "underlying_symbol",
    "underlying_price",
    "option_type",
    "expiration",
    "quote_date",
    "strike",
    "bid",
    "ask",
    "delta",
]

# Summary keys that every result should have
_SUMMARY_KEYS = {
    "total_trades",
    "winning_trades",
    "losing_trades",
    "win_rate",
    "total_pnl",
    "total_return",
    "avg_pnl",
    "avg_win",
    "avg_loss",
    "max_win",
    "max_loss",
    "profit_factor",
    "max_drawdown",
    "avg_days_in_trade",
    "sharpe_ratio",
    "sortino_ratio",
    "var_95",
    "cvar_95",
    "calmar_ratio",
    "omega_ratio",
    "tail_ratio",
}

# ---------------------------------------------------------------------------
# Fixture factories
# ---------------------------------------------------------------------------


def _make_data(symbol, direction):
    """Build option chain data for a single symbol + direction."""
    exp_date = datetime.datetime(2018, 1, 31)
    entry = datetime.datetime(2018, 1, 1)
    exit_day = datetime.datetime(2018, 1, 31)
    rows = [
        # Entry — Calls
        [symbol, 213.93, "call", exp_date, entry, 210.0, 8.50, 8.60, 0.65],
        [symbol, 213.93, "call", exp_date, entry, 212.5, 7.35, 7.45, 0.50],
        [symbol, 213.93, "call", exp_date, entry, 215.0, 6.00, 6.05, 0.30],
        # Entry — Puts
        [symbol, 213.93, "put", exp_date, entry, 210.0, 4.50, 4.60, -0.30],
        [symbol, 213.93, "put", exp_date, entry, 212.5, 5.70, 5.80, -0.50],
        [symbol, 213.93, "put", exp_date, entry, 215.0, 7.10, 7.20, -0.65],
    ]
    if direction == "up":
        rows += [
            [symbol, 220.0, "call", exp_date, exit_day, 210.0, 9.90, 10.0, 0.99],
            [symbol, 220.0, "call", exp_date, exit_day, 212.5, 7.45, 7.55, 0.95],
            [symbol, 220.0, "call", exp_date, exit_day, 215.0, 4.96, 5.05, 0.85],
            [symbol, 220.0, "put", exp_date, exit_day, 210.0, 0.0, 0.0, -0.01],
            [symbol, 220.0, "put", exp_date, exit_day, 212.5, 0.0, 0.0, -0.05],
            [symbol, 220.0, "put", exp_date, exit_day, 215.0, 0.0, 0.0, -0.15],
        ]
    else:  # down
        rows += [
            [symbol, 207.0, "call", exp_date, exit_day, 210.0, 0.50, 0.60, 0.15],
            [symbol, 207.0, "call", exp_date, exit_day, 212.5, 0.10, 0.20, 0.05],
            [symbol, 207.0, "call", exp_date, exit_day, 215.0, 0.02, 0.08, 0.01],
            [symbol, 207.0, "put", exp_date, exit_day, 210.0, 2.80, 3.00, -0.85],
            [symbol, 207.0, "put", exp_date, exit_day, 212.5, 5.30, 5.50, -0.95],
            [symbol, 207.0, "put", exp_date, exit_day, 215.0, 7.80, 8.00, -0.99],
        ]
    return pd.DataFrame(data=rows, columns=_CHAIN_COLS)


@pytest.fixture(scope="module")
def spy_data_up():
    return _make_data("SPY", "up")


@pytest.fixture(scope="module")
def qqq_data_up():
    return _make_data("QQQ", "up")


@pytest.fixture(scope="module")
def spy_data_down():
    return _make_data("SPY", "down")


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_legs_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            simulate_portfolio(legs=[], capital=100_000)

    def test_missing_data_key_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="missing required key 'data'"):
            simulate_portfolio(
                legs=[{"strategy": op.long_calls, "weight": 1.0}],
            )

    def test_missing_strategy_key_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="missing required key 'strategy'"):
            simulate_portfolio(
                legs=[{"data": spy_data_up, "weight": 1.0}],
            )

    def test_missing_weight_key_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="missing required key 'weight'"):
            simulate_portfolio(
                legs=[{"data": spy_data_up, "strategy": op.long_calls}],
            )

    def test_weight_zero_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="weight must be"):
            simulate_portfolio(
                legs=[{"data": spy_data_up, "strategy": op.long_calls, "weight": 0.0}],
            )

    def test_weight_negative_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="weight must be"):
            simulate_portfolio(
                legs=[{"data": spy_data_up, "strategy": op.long_calls, "weight": -0.5}],
            )

    def test_weight_over_one_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="weight must be"):
            simulate_portfolio(
                legs=[{"data": spy_data_up, "strategy": op.long_calls, "weight": 1.5}],
            )

    def test_weights_not_summing_to_one_raises(self, spy_data_up, qqq_data_up):
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            simulate_portfolio(
                legs=[
                    {"data": spy_data_up, "strategy": op.long_calls, "weight": 0.5},
                    {"data": qqq_data_up, "strategy": op.long_puts, "weight": 0.3},
                ],
            )

    def test_non_callable_strategy_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="callable"):
            simulate_portfolio(
                legs=[{"data": spy_data_up, "strategy": "not_a_func", "weight": 1.0}],
            )

    def test_boolean_weight_raises(self, spy_data_up):
        with pytest.raises(ValueError, match="weight must be"):
            simulate_portfolio(
                legs=[{"data": spy_data_up, "strategy": op.long_calls, "weight": True}],
            )


# ---------------------------------------------------------------------------
# Core functionality tests
# ---------------------------------------------------------------------------


class TestBasicPortfolio:
    def test_single_leg_matches_simulate(self, spy_data_up):
        """A single-leg portfolio with weight=1.0 should match plain simulate()."""
        kwargs = {"max_entry_dte": 90, "exit_dte": 0, "selector": "first"}
        portfolio = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 1.0,
                    **kwargs,
                }
            ],
            capital=100_000,
        )
        single = simulate(spy_data_up, op.long_calls, capital=100_000, **kwargs)

        assert isinstance(portfolio, PortfolioResult)
        assert portfolio.summary["total_trades"] == single.summary["total_trades"]
        assert portfolio.summary["total_pnl"] == pytest.approx(
            single.summary["total_pnl"], rel=1e-6
        )
        assert portfolio.summary["win_rate"] == pytest.approx(
            single.summary["win_rate"], rel=1e-6
        )

    def test_two_leg_portfolio(self, spy_data_up, qqq_data_up):
        """Two legs should both appear in the combined trade log."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.6,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.4,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert isinstance(result, PortfolioResult)
        assert "leg" in result.trade_log.columns
        assert set(result.trade_log["leg"].unique()) == {"long_calls", "long_puts"}

    def test_leg_results_present(self, spy_data_up, qqq_data_up):
        """Each leg should have its own SimulationResult in leg_results."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "name": "spy_calls",
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "name": "qqq_puts",
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert "spy_calls" in result.leg_results
        assert "qqq_puts" in result.leg_results
        for name, leg_result in result.leg_results.items():
            assert isinstance(leg_result, SimulationResult)

    def test_custom_leg_names(self, spy_data_up, qqq_data_up):
        """Custom names should be used in trade log and leg_results."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "name": "alpha",
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "name": "beta",
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert set(result.leg_results.keys()) == {"alpha", "beta"}
        assert set(result.trade_log["leg"].unique()) == {"alpha", "beta"}

    def test_default_names_from_strategy(self, spy_data_up, qqq_data_up):
        """Without explicit names, strategy __name__ is used."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert set(result.leg_results.keys()) == {"long_calls", "long_puts"}

    def test_duplicate_names_deduplicated(self, spy_data_up, qqq_data_up):
        """Two legs with same strategy should get unique names."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert len(result.leg_results) == 2
        assert "long_calls" in result.leg_results
        assert "long_calls_1" in result.leg_results

    def test_dedup_avoids_collision_with_explicit_name(self, spy_data_up, qqq_data_up):
        """Dedup suffix should not collide with an explicitly named leg."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 1.0 / 3,
                    "name": "strat_1",
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_calls,
                    "weight": 1.0 / 3,
                    "name": "strat",
                    "selector": "first",
                },
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 1.0 / 3,
                    "name": "strat",
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        names = set(result.leg_results.keys())
        # "strat_1" is taken, so the duplicate "strat" should get "strat_2"
        assert names == {"strat_1", "strat", "strat_2"}
        assert len(result.leg_results) == 3


# ---------------------------------------------------------------------------
# Trade log tests
# ---------------------------------------------------------------------------


class TestTradeLog:
    def test_trade_ids_sequential(self, spy_data_up, qqq_data_up):
        """Combined trade IDs should be re-numbered sequentially."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        expected_ids = list(range(1, len(result.trade_log) + 1))
        assert result.trade_log["trade_id"].tolist() == expected_ids

    def test_cumulative_pnl_recomputed(self, spy_data_up, qqq_data_up):
        """Cumulative P&L should be the running sum of realized_pnl."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        if not result.trade_log.empty:
            expected_cum = result.trade_log["realized_pnl"].cumsum()
            pd.testing.assert_series_equal(
                result.trade_log["cumulative_pnl"].reset_index(drop=True),
                expected_cum.reset_index(drop=True),
                check_names=False,
            )

    def test_equity_from_capital_plus_cumulative(self, spy_data_up, qqq_data_up):
        """Equity should equal capital + cumulative_pnl."""
        capital = 100_000
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=capital,
        )

        if not result.trade_log.empty:
            expected_equity = capital + result.trade_log["cumulative_pnl"]
            pd.testing.assert_series_equal(
                result.trade_log["equity"].reset_index(drop=True),
                expected_equity.reset_index(drop=True),
                check_names=False,
            )

    def test_sorted_by_exit_date(self, spy_data_up, qqq_data_up):
        """Combined trade log should be sorted by exit_date (P&L realization order)."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        if len(result.trade_log) > 1:
            dates = pd.to_datetime(result.trade_log["exit_date"])
            assert dates.is_monotonic_increasing


# ---------------------------------------------------------------------------
# Summary tests
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_has_all_keys(self, spy_data_up, qqq_data_up):
        """Portfolio summary should have all 21 standard keys."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert _SUMMARY_KEYS.issubset(result.summary.keys())

    def test_total_trades_is_sum_of_legs(self, spy_data_up, qqq_data_up):
        """Portfolio total_trades should be sum of per-leg trades."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        leg_total = sum(r.summary["total_trades"] for r in result.leg_results.values())
        assert result.summary["total_trades"] == leg_total

    def test_total_pnl_is_sum_of_legs(self, spy_data_up, qqq_data_up):
        """Portfolio total P&L should be sum of per-leg P&L."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        leg_pnl = sum(r.summary["total_pnl"] for r in result.leg_results.values())
        assert result.summary["total_pnl"] == pytest.approx(leg_pnl, rel=1e-6)


# ---------------------------------------------------------------------------
# Equity curve tests
# ---------------------------------------------------------------------------


class TestEquityCurve:
    def test_equity_curve_not_empty(self, spy_data_up, qqq_data_up):
        """Portfolio equity curve should not be empty when trades exist."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert not result.equity_curve.empty

    def test_equity_curve_name(self, spy_data_up):
        """Equity curve series should be named 'equity'."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 1.0,
                    "selector": "first",
                }
            ],
            capital=100_000,
        )

        assert result.equity_curve.name == "equity"

    def test_equity_curve_daily_index(self, spy_data_up, qqq_data_up):
        """Equity curve should have daily-frequency datetime index."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        if len(result.equity_curve) > 1:
            assert isinstance(result.equity_curve.index, pd.DatetimeIndex)


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_data_returns_empty_result(self):
        """Empty input data should produce an empty PortfolioResult."""
        empty = pd.DataFrame(columns=_CHAIN_COLS)
        result = simulate_portfolio(
            legs=[{"data": empty, "strategy": op.long_calls, "weight": 1.0}],
            capital=100_000,
        )

        assert isinstance(result, PortfolioResult)
        assert result.trade_log.empty
        assert result.equity_curve.empty
        assert result.summary["total_trades"] == 0

    def test_one_empty_one_active(self, spy_data_up):
        """One leg with no trades should not break the portfolio."""
        empty = pd.DataFrame(columns=_CHAIN_COLS)
        result = simulate_portfolio(
            legs=[
                {"data": empty, "strategy": op.long_calls, "weight": 0.5},
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert result.summary["total_trades"] > 0
        # Only the active leg should have trades
        assert set(result.trade_log["leg"].unique()) == {"long_calls_1"}

    def test_all_legs_empty(self):
        """All legs empty should produce empty PortfolioResult."""
        empty = pd.DataFrame(columns=_CHAIN_COLS)
        result = simulate_portfolio(
            legs=[
                {"data": empty, "strategy": op.long_calls, "weight": 0.5},
                {"data": empty, "strategy": op.long_puts, "weight": 0.5},
            ],
            capital=100_000,
        )

        assert result.trade_log.empty
        assert result.equity_curve.empty
        assert result.summary["total_trades"] == 0

    def test_capital_allocation(self, spy_data_up, qqq_data_up):
        """Each leg should receive its weighted share of capital."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.7,
                    "name": "spy",
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.3,
                    "name": "qqq",
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        # Verify per-leg capital is reflected in the summary
        spy_result = result.leg_results["spy"]
        qqq_result = result.leg_results["qqq"]

        # total_return = total_pnl / capital, so we can verify capital allocation
        if spy_result.summary["total_trades"] > 0:
            expected_return = spy_result.summary["total_pnl"] / 70_000
            assert spy_result.summary["total_return"] == pytest.approx(
                expected_return, rel=1e-6
            )
        if qqq_result.summary["total_trades"] > 0:
            expected_return = qqq_result.summary["total_pnl"] / 30_000
            assert qqq_result.summary["total_return"] == pytest.approx(
                expected_return, rel=1e-6
            )

    def test_strategy_kwargs_passthrough(self, spy_data_up):
        """Strategy-specific kwargs should pass through to simulate()."""
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 1.0,
                    "max_entry_dte": 45,
                    "exit_dte": 0,
                    "selector": "first",
                }
            ],
            capital=100_000,
        )

        assert isinstance(result, PortfolioResult)

    def test_weight_tolerance(self, spy_data_up, qqq_data_up):
        """Weights summing to within 0.01 of 1.0 should be accepted."""
        # 0.501 + 0.504 = 1.005, within tolerance of 0.01
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.501,
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.504,
                    "selector": "first",
                },
            ],
            capital=100_000,
        )

        assert isinstance(result, PortfolioResult)

    def test_weights_normalized(self, spy_data_up, qqq_data_up):
        """Weights within tolerance are normalized so capital sums to total."""
        capital = 100_000
        # 0.501 + 0.504 = 1.005; after normalization, allocated capital = 100k
        result = simulate_portfolio(
            legs=[
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.501,
                    "name": "a",
                    "selector": "first",
                },
                {
                    "data": qqq_data_up,
                    "strategy": op.long_puts,
                    "weight": 0.504,
                    "name": "b",
                    "selector": "first",
                },
            ],
            capital=capital,
        )

        # Per-leg capital should sum to total capital (not 100,500)
        a_cap = (
            result.leg_results["a"].summary["total_pnl"]
            / result.leg_results["a"].summary["total_return"]
        )
        b_cap = (
            result.leg_results["b"].summary["total_pnl"]
            / result.leg_results["b"].summary["total_return"]
        )
        assert a_cap + b_cap == pytest.approx(capital, rel=1e-4)

    def test_idle_cash_in_equity_curve(self, spy_data_up):
        """Equity curve for one-empty-leg portfolio should include idle cash."""
        capital = 100_000
        empty = pd.DataFrame(columns=_CHAIN_COLS)
        result = simulate_portfolio(
            legs=[
                {"data": empty, "strategy": op.long_calls, "weight": 0.5},
                {
                    "data": spy_data_up,
                    "strategy": op.long_calls,
                    "weight": 0.5,
                    "selector": "first",
                },
            ],
            capital=capital,
        )

        # The empty leg's 50k should still be in the equity curve
        # so equity should never drop below 50k (the idle cash)
        assert not result.equity_curve.empty
        assert result.equity_curve.iloc[0] >= capital * 0.5
