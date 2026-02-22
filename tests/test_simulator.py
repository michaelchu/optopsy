"""Tests for the lightweight backtest simulation layer."""

import datetime

import pandas as pd
import pytest

import optopsy as op
from optopsy.simulator import (
    SimulationResult,
    _build_trade_log,
    _filter_trades,
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
        # With max_positions=1, the second trade overlaps the first and is skipped
        assert result.summary["total_trades"] == 1

    def test_max_positions_greater_allows_concurrent(self, multi_entry_data):
        result = simulate(
            multi_entry_data, op.long_calls, max_positions=5, selector="first"
        )
        # With high max_positions, both trades should execute
        assert result.summary["total_trades"] == 2


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
        if result.summary["total_trades"] > 0:
            trade = result.trade_log.iloc[0]
            assert (
                trade["realized_pnl"] != 0
                or trade["entry_cost"] != trade["exit_proceeds"]
            )
            assert trade["dollar_cost"] > 0

    def test_iron_condor_simulation(self, multi_strike_data):
        result = simulate(multi_strike_data, op.iron_condor, selector="first")
        assert isinstance(result, SimulationResult)
        if result.summary["total_trades"] > 0:
            trade = result.trade_log.iloc[0]
            assert trade["dollar_cost"] > 0
            assert trade["days_held"] >= 0


# ---------------------------------------------------------------------------
# Credit strategy P&L
# ---------------------------------------------------------------------------


class TestCreditStrategy:
    def test_short_call_entry_cost_negative(self, data):
        """Short single-leg strategies should have negative entry_cost (credit)."""
        result = simulate(data, op.short_calls, selector="first")
        assert result.summary["total_trades"] == 1
        trade = result.trade_log.iloc[0]
        # After normalisation, short single-leg entry_cost is negative
        assert trade["entry_cost"] < 0

    def test_short_call_pnl_formula(self, data):
        """P&L = (exit_proceeds - entry_cost) * qty * mult for all strategies."""
        result = simulate(data, op.short_calls, selector="first")
        assert result.summary["total_trades"] == 1
        trade = result.trade_log.iloc[0]
        expected_pnl = (
            (trade["exit_proceeds"] - trade["entry_cost"])
            * trade["quantity"]
            * trade["multiplier"]
        )
        assert trade["realized_pnl"] == pytest.approx(expected_pnl)

    def test_short_call_losing_trade_negative_pnl(self, data):
        """Short call where underlying goes up should lose money."""
        # Data has underlying going from 213.93 to 220 — calls go up
        result = simulate(data, op.short_calls, selector="first")
        assert result.summary["total_trades"] == 1
        trade = result.trade_log.iloc[0]
        # Option went up: bad for short seller → negative P&L
        assert trade["realized_pnl"] < 0

    def test_short_put_spread_pnl(self, data):
        """Short put spread (credit spread) P&L = (exit - entry) * qty * mult."""
        result = simulate(data, op.short_put_spread, selector="first")
        assert result.summary["total_trades"] == 1
        trade = result.trade_log.iloc[0]
        expected_pnl = (
            (trade["exit_proceeds"] - trade["entry_cost"])
            * trade["quantity"]
            * trade["multiplier"]
        )
        assert trade["realized_pnl"] == pytest.approx(expected_pnl)


# ---------------------------------------------------------------------------
# Capital tracking
# ---------------------------------------------------------------------------


class TestCapitalTracking:
    def test_equity_equals_capital_plus_pnl(self, data):
        capital = 50_000.0
        result = simulate(data, op.long_calls, capital=capital, selector="first")
        assert result.summary["total_trades"] == 1
        last_trade = result.trade_log.iloc[-1]
        assert last_trade["equity"] == pytest.approx(
            capital + last_trade["cumulative_pnl"]
        )

    def test_low_capital_trade_still_executes(self, data):
        """Trades execute regardless of capital; no pre-trade capital gate."""
        result = simulate(data, op.long_calls, capital=1.0, selector="first")
        # The trade executes even with $1 capital
        assert result.summary["total_trades"] == 1

    def test_quantity_multiplier_affect_cost(self, data):
        result1 = simulate(
            data, op.long_calls, quantity=1, multiplier=100, selector="first"
        )
        result2 = simulate(
            data, op.long_calls, quantity=2, multiplier=100, selector="first"
        )
        assert result1.summary["total_trades"] == 1
        assert result2.summary["total_trades"] == 1
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

    def test_breakeven_not_counted_as_loss(self):
        """A trade with $0 P&L should not count as a loss."""
        from optopsy.simulator import _compute_summary

        trade_log = pd.DataFrame(
            {
                "realized_pnl": [100.0, 0.0, -50.0],
                "equity": [100_100.0, 100_100.0, 100_050.0],
                "days_held": [30, 30, 30],
            }
        )
        s = _compute_summary(trade_log, 100_000.0)
        assert s["winning_trades"] == 1
        assert s["losing_trades"] == 1
        assert s["total_trades"] == 3

    def test_profit_factor_zero_when_all_breakeven(self):
        """All breakeven trades → profit_factor should be 0, not inf."""
        from optopsy.simulator import _compute_summary

        trade_log = pd.DataFrame(
            {
                "realized_pnl": [0.0, 0.0],
                "equity": [100_000.0, 100_000.0],
                "days_held": [30, 30],
            }
        )
        s = _compute_summary(trade_log, 100_000.0)
        assert s["profit_factor"] == 0.0


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class TestArgumentValidation:
    def test_zero_capital_raises(self, data):
        with pytest.raises(ValueError, match="capital"):
            simulate(data, op.long_calls, capital=0)

    def test_negative_capital_raises(self, data):
        with pytest.raises(ValueError, match="capital"):
            simulate(data, op.long_calls, capital=-1000)

    def test_zero_quantity_raises(self, data):
        with pytest.raises(ValueError, match="quantity"):
            simulate(data, op.long_calls, quantity=0)

    def test_zero_max_positions_raises(self, data):
        with pytest.raises(ValueError, match="max_positions"):
            simulate(data, op.long_calls, max_positions=0)

    def test_zero_multiplier_raises(self, data):
        with pytest.raises(ValueError, match="multiplier"):
            simulate(data, op.long_calls, multiplier=0)


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


class TestExitDte:
    def test_nonzero_exit_dte(self):
        """When exit_dte > 0, exit_date = expiration - exit_dte and days_held adjusts."""
        exp_date = datetime.datetime(2018, 1, 31)
        entry = datetime.datetime(2018, 1, 1)
        # exit_dte=7 means exit 7 days before expiration → Jan 24
        exit_day = datetime.datetime(2018, 1, 24)
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
            ["SPX", 213.93, "call", exp_date, entry, 212.5, 7.35, 7.45],
            ["SPX", 213.93, "call", exp_date, entry, 215.0, 6.00, 6.05],
            ["SPX", 218.0, "call", exp_date, exit_day, 212.5, 7.45, 7.55],
            ["SPX", 218.0, "call", exp_date, exit_day, 215.0, 4.96, 5.05],
        ]
        df = pd.DataFrame(data=d, columns=cols)

        exit_dte = 7
        result = simulate(df, op.long_calls, selector="first", exit_dte=exit_dte)
        assert result.summary["total_trades"] == 1
        trade = result.trade_log.iloc[0]
        expected_exit = pd.Timestamp("2018-01-24")
        assert pd.Timestamp(trade["exit_date"]) == expected_exit
        expected_days = (expected_exit - pd.Timestamp("2018-01-01")).days
        assert trade["days_held"] == expected_days


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


# ---------------------------------------------------------------------------
# Trade filtering (overlap and expiration dedup)
# ---------------------------------------------------------------------------


class TestFilterTrades:
    def test_overlap_filter(self):
        """Trade 2 overlaps trade 1; trade 3 does not. Only 2 trades execute."""
        trades = pd.DataFrame(
            {
                "entry_date": pd.to_datetime(
                    ["2018-01-01", "2018-01-15", "2018-02-01"]
                ),
                "exit_date": pd.to_datetime(["2018-01-31", "2018-02-15", "2018-02-28"]),
                "expiration": pd.to_datetime(
                    ["2018-01-31", "2018-02-15", "2018-02-28"]
                ),
                "underlying_symbol": ["SPX"] * 3,
                "entry_cost": [1.0, 1.0, 1.0],
                "exit_proceeds": [1.5, 1.5, 1.5],
                "pct_change": [0.5, 0.5, 0.5],
                "description": ["t1", "t2", "t3"],
            }
        )
        filtered = _filter_trades(trades, max_positions=1)
        assert len(filtered) == 2
        assert filtered.iloc[0]["description"] == "t1"
        assert filtered.iloc[1]["description"] == "t3"

    def test_multi_position_expiration_dedup(self):
        """With max_positions=3, trades with duplicate expirations are skipped."""
        trades = pd.DataFrame(
            {
                "entry_date": pd.to_datetime(
                    ["2018-01-01", "2018-01-05", "2018-01-10"]
                ),
                "exit_date": pd.to_datetime(["2018-01-31", "2018-01-31", "2018-02-28"]),
                "expiration": pd.to_datetime(
                    ["2018-01-31", "2018-01-31", "2018-02-28"]
                ),
                "underlying_symbol": ["SPX"] * 3,
                "entry_cost": [1.0, 1.0, 1.0],
                "exit_proceeds": [1.5, 1.5, 1.5],
                "pct_change": [0.5, 0.5, 0.5],
                "description": ["t1", "t2", "t3"],
            }
        )
        filtered = _filter_trades(trades, max_positions=3)
        # t1 and t3 kept; t2 skipped because same expiration as t1
        assert len(filtered) == 2
        assert filtered.iloc[0]["description"] == "t1"
        assert filtered.iloc[1]["description"] == "t3"

    def test_ruin_truncation(self):
        """Build trade log stops at first trade where equity <= 0."""
        trades = pd.DataFrame(
            {
                "entry_date": pd.to_datetime(
                    ["2018-01-01", "2018-02-01", "2018-03-01"]
                ),
                "exit_date": pd.to_datetime(["2018-01-31", "2018-02-28", "2018-03-31"]),
                "expiration": pd.to_datetime(
                    ["2018-01-31", "2018-02-28", "2018-03-31"]
                ),
                "underlying_symbol": ["SPX"] * 3,
                "entry_cost": [5.0, 5.0, 5.0],
                "exit_proceeds": [1.0, 1.0, 1.0],
                "pct_change": [-0.8, -0.8, -0.8],
                "description": ["t1", "t2", "t3"],
            }
        )
        # capital=500, each trade loses (1-5)*1*100 = -400
        # After trade 1: equity = 500 + (-400) = 100
        # After trade 2: equity = 500 + (-800) = -300 → ruin
        log = _build_trade_log(trades, capital=500.0, quantity=1, multiplier=100)
        assert len(log) == 2
        assert log.iloc[-1]["equity"] <= 0
