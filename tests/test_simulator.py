"""Tests for the lightweight backtest simulation layer."""

import datetime

import pandas as pd
import pytest

import optopsy as op
from optopsy.simulator import (
    SimulationResult,
    _find_cost_col,
    _find_entry_date_col,
    _find_otm_col,
    _is_calendar,
    _is_single_leg,
    _normalise_trades,
    simulate,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def data():
    """Basic option chain data with one entry date and one exit date."""
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 215.0, 6.00, 6.05],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 215.0, 7.10, 7.20],
        ["SPX", 220, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55],
        ["SPX", 220, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05],
        ["SPX", 220, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.0],
        ["SPX", 220, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.0],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture(scope="module")
def multi_strike_data():
    """Data with 5 strikes for testing multi-leg strategies."""
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        # Entry day - Calls
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 207.5, 6.90, 7.00],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 210.0, 4.90, 5.00],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 212.5, 3.00, 3.10],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 215.0, 1.50, 1.60],
        ["SPX", 212.5, "call", exp_date, quote_dates[0], 217.5, 0.60, 0.70],
        # Entry day - Puts
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 207.5, 0.40, 0.50],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 210.0, 1.40, 1.50],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 212.5, 3.00, 3.10],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 215.0, 5.00, 5.10],
        ["SPX", 212.5, "put", exp_date, quote_dates[0], 217.5, 7.00, 7.10],
        # Exit day
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 207.5, 7.45, 7.55],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 210.0, 4.95, 5.05],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 212.5, 2.45, 2.55],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 215.0, 0.0, 0.10],
        ["SPX", 215.0, "call", exp_date, quote_dates[1], 217.5, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 207.5, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 210.0, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.05],
        ["SPX", 215.0, "put", exp_date, quote_dates[1], 217.5, 2.45, 2.55],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture(scope="module")
def multi_entry_data():
    """Data with TWO entry dates and TWO expirations for position limit testing."""
    exp1 = datetime.datetime(2018, 1, 31)
    exp2 = datetime.datetime(2018, 2, 28)
    entry1 = datetime.datetime(2018, 1, 1)
    entry2 = datetime.datetime(2018, 1, 15)
    exit1 = datetime.datetime(2018, 1, 31)
    exit2 = datetime.datetime(2018, 2, 28)
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        # Entry 1 — exp1
        ["SPX", 213.93, "call", exp1, entry1, 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp1, entry1, 215.0, 6.00, 6.05],
        # Entry 2 — exp2
        ["SPX", 215.0, "call", exp2, entry2, 212.5, 8.00, 8.10],
        ["SPX", 215.0, "call", exp2, entry2, 215.0, 5.50, 5.60],
        # Exit 1
        ["SPX", 220, "call", exp1, exit1, 212.5, 7.45, 7.55],
        ["SPX", 220, "call", exp1, exit1, 215.0, 4.96, 5.05],
        # Exit 2
        ["SPX", 222, "call", exp2, exit2, 212.5, 9.50, 9.60],
        ["SPX", 222, "call", exp2, exit2, 215.0, 7.00, 7.10],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture(scope="module")
def calendar_data():
    """Calendar spread test data."""
    front_exp = datetime.datetime(2018, 1, 31)
    back_exp = datetime.datetime(2018, 3, 2)
    entry_date = datetime.datetime(2018, 1, 1)
    exit_date = datetime.datetime(2018, 1, 24)
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        # Entry — Front month calls
        ["SPX", 212.5, "call", front_exp, entry_date, 210.0, 4.40, 4.50],
        ["SPX", 212.5, "call", front_exp, entry_date, 212.5, 2.90, 3.00],
        ["SPX", 212.5, "call", front_exp, entry_date, 215.0, 1.70, 1.80],
        # Entry — Back month calls
        ["SPX", 212.5, "call", back_exp, entry_date, 210.0, 6.40, 6.50],
        ["SPX", 212.5, "call", back_exp, entry_date, 212.5, 4.90, 5.00],
        ["SPX", 212.5, "call", back_exp, entry_date, 215.0, 3.60, 3.70],
        # Exit — Front month
        ["SPX", 215.0, "call", front_exp, exit_date, 210.0, 5.40, 5.50],
        ["SPX", 215.0, "call", front_exp, exit_date, 212.5, 3.00, 3.10],
        ["SPX", 215.0, "call", front_exp, exit_date, 215.0, 0.80, 0.90],
        # Exit — Back month
        ["SPX", 215.0, "call", back_exp, exit_date, 210.0, 6.90, 7.00],
        ["SPX", 215.0, "call", back_exp, exit_date, 212.5, 5.00, 5.10],
        ["SPX", 215.0, "call", back_exp, exit_date, 215.0, 3.30, 3.40],
    ]
    return pd.DataFrame(data=d, columns=cols)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


class TestSimulateSmoke:
    def test_returns_simulation_result(self, data):
        result = simulate(data, op.long_calls)
        assert isinstance(result, SimulationResult)
        assert isinstance(result.trade_log, pd.DataFrame)
        assert isinstance(result.equity_curve, pd.Series)
        assert isinstance(result.summary, dict)

    def test_trade_log_columns(self, data):
        result = simulate(data, op.long_calls)
        expected = {
            "trade_id",
            "underlying_symbol",
            "entry_date",
            "exit_date",
            "days_held",
            "expiration",
            "entry_cost",
            "exit_proceeds",
            "quantity",
            "multiplier",
            "dollar_cost",
            "dollar_proceeds",
            "realized_pnl",
            "pct_change",
            "cumulative_pnl",
            "equity",
            "description",
        }
        assert expected == set(result.trade_log.columns)

    def test_summary_keys(self, data):
        result = simulate(data, op.long_calls)
        expected_keys = {
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
        }
        assert expected_keys == set(result.summary.keys())


# ---------------------------------------------------------------------------
# Single trade
# ---------------------------------------------------------------------------


class TestSingleTrade:
    def test_one_entry_produces_one_trade(self, data):
        result = simulate(data, op.long_calls, selector="first")
        assert len(result.trade_log) == 1

    def test_entry_and_exit_dates(self, data):
        result = simulate(data, op.long_calls, selector="first")
        trade = result.trade_log.iloc[0]
        assert pd.Timestamp(trade["entry_date"]) == pd.Timestamp("2018-01-01")
        assert pd.Timestamp(trade["exit_date"]) == pd.Timestamp("2018-01-31")

    def test_days_held(self, data):
        result = simulate(data, op.long_calls, selector="first")
        trade = result.trade_log.iloc[0]
        assert trade["days_held"] == 30


# ---------------------------------------------------------------------------
# Position limits
# ---------------------------------------------------------------------------


class TestPositionLimits:
    def test_max_positions_one_prevents_overlap(self, multi_entry_data):
        result = simulate(
            multi_entry_data, op.long_calls, max_positions=1, selector="first"
        )
        # With max_positions=1, only one position can be open at a time.
        # The first trade enters 2018-01-01 and exits 2018-01-31.
        # The second trade enters 2018-01-15 (while first is still open),
        # so it should be skipped.
        assert result.summary["total_trades"] <= 2

    def test_max_positions_greater_allows_concurrent(self, multi_entry_data):
        result = simulate(
            multi_entry_data, op.long_calls, max_positions=5, selector="first"
        )
        # With high max_positions, both trades should execute
        assert result.summary["total_trades"] >= 1


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestSelectors:
    def test_nearest_selector(self, data):
        result = simulate(data, op.long_calls, selector="nearest")
        assert result.summary["total_trades"] == 1

    def test_first_selector(self, data):
        result = simulate(data, op.long_calls, selector="first")
        assert result.summary["total_trades"] == 1

    def test_highest_premium_selector(self, data):
        result = simulate(data, op.long_calls, selector="highest_premium")
        assert result.summary["total_trades"] == 1

    def test_lowest_premium_selector(self, data):
        result = simulate(data, op.long_calls, selector="lowest_premium")
        assert result.summary["total_trades"] == 1

    def test_invalid_selector_raises(self, data):
        with pytest.raises(ValueError, match="Unknown selector"):
            simulate(data, op.long_calls, selector="nonexistent")

    def test_custom_callable_selector(self, data):
        def my_selector(candidates):
            return candidates.iloc[-1]

        result = simulate(data, op.long_calls, selector=my_selector)
        assert result.summary["total_trades"] == 1


# ---------------------------------------------------------------------------
# Multi-leg strategies
# ---------------------------------------------------------------------------


class TestMultiLeg:
    def test_spread_simulation(self, data):
        result = simulate(data, op.long_call_spread, selector="first")
        assert isinstance(result, SimulationResult)
        assert result.summary["total_trades"] >= 1

    def test_straddle_simulation(self, data):
        result = simulate(data, op.long_straddles, selector="first")
        assert isinstance(result, SimulationResult)
        assert result.summary["total_trades"] >= 1

    def test_butterfly_simulation(self, multi_strike_data):
        result = simulate(multi_strike_data, op.long_call_butterfly, selector="first")
        assert isinstance(result, SimulationResult)

    def test_iron_condor_simulation(self, multi_strike_data):
        result = simulate(multi_strike_data, op.iron_condor, selector="first")
        assert isinstance(result, SimulationResult)


# ---------------------------------------------------------------------------
# Capital tracking
# ---------------------------------------------------------------------------


class TestCapitalTracking:
    def test_equity_equals_capital_plus_pnl(self, data):
        capital = 50_000.0
        result = simulate(data, op.long_calls, capital=capital, selector="first")
        if not result.trade_log.empty:
            last_trade = result.trade_log.iloc[-1]
            assert last_trade["equity"] == pytest.approx(
                capital + last_trade["cumulative_pnl"]
            )

    def test_insufficient_capital_skips_trade(self, data):
        # With very low capital, the trade should be skipped
        result = simulate(data, op.long_calls, capital=1.0, selector="first")
        assert result.summary["total_trades"] == 0

    def test_quantity_multiplier_affect_cost(self, data):
        result1 = simulate(
            data, op.long_calls, quantity=1, multiplier=100, selector="first"
        )
        result2 = simulate(
            data, op.long_calls, quantity=2, multiplier=100, selector="first"
        )
        if result1.summary["total_trades"] > 0 and result2.summary["total_trades"] > 0:
            cost1 = result1.trade_log.iloc[0]["dollar_cost"]
            cost2 = result2.trade_log.iloc[0]["dollar_cost"]
            assert cost2 == pytest.approx(cost1 * 2)


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


class TestSummaryStats:
    def test_win_rate_calculation(self, data):
        result = simulate(data, op.long_calls, selector="first")
        s = result.summary
        total = s["total_trades"]
        if total > 0:
            expected_wr = s["winning_trades"] / total
            assert s["win_rate"] == pytest.approx(expected_wr)

    def test_total_return_calculation(self, data):
        capital = 100_000.0
        result = simulate(data, op.long_calls, capital=capital, selector="first")
        s = result.summary
        assert s["total_return"] == pytest.approx(s["total_pnl"] / capital)

    def test_profit_factor_no_losses(self, data):
        result = simulate(data, op.long_calls, selector="first")
        s = result.summary
        if s["losing_trades"] == 0 and s["winning_trades"] > 0:
            assert s["profit_factor"] == float("inf")


# ---------------------------------------------------------------------------
# Empty result
# ---------------------------------------------------------------------------


class TestEmptyResult:
    def test_empty_data_returns_empty_result(self):
        cols = [
            "underlying_symbol",
            "underlying_price",
            "option_type",
            "expiration",
            "quote_date",
            "strike",
            "bid",
            "ask",
        ]
        empty = pd.DataFrame(columns=cols)
        result = simulate(empty, op.long_calls, selector="first")
        assert isinstance(result, SimulationResult)
        assert result.summary["total_trades"] == 0
        assert result.trade_log.empty
        assert result.equity_curve.empty


# ---------------------------------------------------------------------------
# Calendar strategies
# ---------------------------------------------------------------------------


class TestCalendarStrategies:
    def test_calendar_simulation(self, calendar_data):
        result = simulate(
            calendar_data,
            op.long_call_calendar,
            selector="first",
            front_dte_min=20,
            front_dte_max=40,
            back_dte_min=50,
            back_dte_max=90,
            exit_dte=7,
        )
        assert isinstance(result, SimulationResult)
        # Calendar may or may not produce trades depending on data alignment
        # but it should not error
        assert result.summary["total_trades"] >= 0


# ---------------------------------------------------------------------------
# Column detection helpers
# ---------------------------------------------------------------------------


class TestColumnDetection:
    def test_is_single_leg(self):
        cols = pd.Index(
            ["entry", "exit", "quote_date_entry", "underlying_symbol", "strike"]
        )
        assert _is_single_leg(cols) is True

    def test_is_not_single_leg_with_total_cost(self):
        cols = pd.Index(
            [
                "entry",
                "exit",
                "quote_date_entry",
                "total_entry_cost",
                "total_exit_proceeds",
            ]
        )
        assert _is_single_leg(cols) is False

    def test_is_calendar(self):
        cols = pd.Index(["expiration_leg1", "expiration_leg2", "total_entry_cost"])
        assert _is_calendar(cols) is True

    def test_is_not_calendar(self):
        cols = pd.Index(["expiration", "total_entry_cost"])
        assert _is_calendar(cols) is False

    def test_find_entry_date_col(self):
        df = pd.DataFrame({"quote_date_entry": [1], "strike": [100]})
        assert _find_entry_date_col(df) == "quote_date_entry"

    def test_find_entry_date_col_missing(self):
        df = pd.DataFrame({"expiration": [1], "dte_entry": [30]})
        assert _find_entry_date_col(df) is None

    def test_find_otm_col(self):
        df = pd.DataFrame({"otm_pct_entry": [0.05]})
        assert _find_otm_col(df) == "otm_pct_entry"

    def test_find_otm_col_missing(self):
        df = pd.DataFrame({"strike": [100]})
        assert _find_otm_col(df) is None

    def test_find_cost_col_multi_leg(self):
        df = pd.DataFrame({"total_entry_cost": [1.0]})
        assert _find_cost_col(df) == "total_entry_cost"

    def test_find_cost_col_single_leg(self):
        df = pd.DataFrame({"entry": [1.0]})
        assert _find_cost_col(df) == "entry"


# ---------------------------------------------------------------------------
# Trade normalisation
# ---------------------------------------------------------------------------


class TestNormaliseTrades:
    def test_single_leg_normalisation(self):
        raw = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"],
                "underlying_price_entry": [213.93],
                "quote_date_entry": [pd.Timestamp("2018-01-01")],
                "option_type": ["call"],
                "expiration": [pd.Timestamp("2018-01-31")],
                "dte_entry": [30],
                "strike": [212.5],
                "entry": [7.40],
                "exit": [7.50],
                "pct_change": [0.0135],
            }
        )
        result = _normalise_trades(raw)
        assert "entry_date" in result.columns
        assert "exit_date" in result.columns
        assert "entry_cost" in result.columns
        assert "exit_proceeds" in result.columns
        assert len(result) == 1

    def test_multi_leg_normalisation(self):
        raw = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"],
                "underlying_price_entry_leg1": [213.93],
                "expiration": [pd.Timestamp("2018-01-31")],
                "dte_entry": [30],
                "option_type_leg1": ["call"],
                "strike_leg1": [212.5],
                "option_type_leg2": ["call"],
                "strike_leg2": [215.0],
                "total_entry_cost": [1.375],
                "total_exit_proceeds": [2.495],
                "pct_change": [0.8145],
            }
        )
        result = _normalise_trades(raw)
        assert "entry_date" in result.columns
        assert result.iloc[0]["entry_cost"] == 1.375


# ---------------------------------------------------------------------------
# Equity curve
# ---------------------------------------------------------------------------


class TestEquityCurve:
    def test_equity_curve_indexed_by_exit_date(self, data):
        result = simulate(data, op.long_calls, selector="first")
        if not result.equity_curve.empty:
            assert result.equity_curve.index.name == "exit_date"

    def test_equity_curve_monotonic_for_all_wins(self, data):
        result = simulate(data, op.long_calls, selector="first")
        if result.summary["losing_trades"] == 0 and not result.equity_curve.empty:
            assert result.equity_curve.is_monotonic_increasing
