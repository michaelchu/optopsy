"""End-to-end tests for the simulator.

These tests exercise the full pipeline:
  CSV on disk → csv_data() → strategy() → simulate() → validate output

Unlike the unit tests in test_simulator.py (which use in-memory fixtures),
these create temporary CSV files to verify the entire data flow.
"""

import os
import tempfile

import pandas as pd
import pytest

import optopsy as op
from optopsy.signals import (
    and_signals,
    apply_signal,
    day_of_week,
    or_signals,
    sma_above,
)
from optopsy.simulator import _TRADE_LOG_COLUMNS, SimulationResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(df: pd.DataFrame, tmpdir: str, name: str = "chain.csv") -> str:
    """Write a DataFrame to CSV and return the path."""
    path = os.path.join(tmpdir, name)
    df.to_csv(path, index=False)
    return path


def _make_chain(rows: list[list]) -> pd.DataFrame:
    """Build an option-chain DataFrame from compact row data."""
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
    return pd.DataFrame(data=rows, columns=cols)


# ---------------------------------------------------------------------------
# Multi-date chain fixture — 3 entry dates, 3 expirations
#
# Trade 1: Entry Jan 2, exits Jan 31.  Underlying 212 → 216.
#   long call 210: buy ask 4.60, sell bid 6.00 → profit
#   long call 215: buy ask 1.50, sell bid 1.00 → loss
#   short put 210: sell bid 2.40 → credit, expires worthless → profit
#   short put 215: sell bid 5.30 → credit, expires worthless → profit
#
# Trade 2: Entry Jan 16, exits Feb 28.  Underlying 214 → 218.
#   long call 210: buy ask 6.10, sell bid 8.00 → profit
#
# Trade 3: Entry Feb 1, exits Mar 29.  Underlying 215 → 220.
#   long call 210: buy ask 7.10, sell bid 10.00 → profit
#
# Trade 2 overlaps Trade 1 (Jan 16 < Jan 31), so with max_positions=1
# only Trade 1 and Trade 3 execute.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def chain_csv():
    """Create a realistic multi-date option chain CSV on disk."""
    exp1 = "2018-01-31"
    exp2 = "2018-02-28"
    exp3 = "2018-03-29"
    entry1 = "2018-01-02"
    entry2 = "2018-01-16"
    entry3 = "2018-02-01"

    rows = [
        # --- Entry 1 (Jan 2) → exits at exp1 (Jan 31) ---
        ["SPX", 212.0, "call", exp1, entry1, 210.0, 4.50, 4.60],
        ["SPX", 212.0, "call", exp1, entry1, 215.0, 1.40, 1.50],
        ["SPX", 212.0, "put", exp1, entry1, 210.0, 2.40, 2.50],
        ["SPX", 212.0, "put", exp1, entry1, 215.0, 5.30, 5.40],
        # --- Exit 1 (Jan 31) ---
        ["SPX", 216.0, "call", exp1, exp1, 210.0, 6.00, 6.10],
        ["SPX", 216.0, "call", exp1, exp1, 215.0, 1.00, 1.10],
        ["SPX", 216.0, "put", exp1, exp1, 210.0, 0.00, 0.10],
        ["SPX", 216.0, "put", exp1, exp1, 215.0, 0.00, 0.10],
        # --- Entry 2 (Jan 16) → exits at exp2 (Feb 28) ---
        ["SPX", 214.0, "call", exp2, entry2, 210.0, 6.00, 6.10],
        ["SPX", 214.0, "call", exp2, entry2, 215.0, 2.00, 2.10],
        ["SPX", 214.0, "put", exp2, entry2, 210.0, 1.90, 2.00],
        ["SPX", 214.0, "put", exp2, entry2, 215.0, 4.90, 5.00],
        # --- Exit 2 (Feb 28) ---
        ["SPX", 218.0, "call", exp2, exp2, 210.0, 8.00, 8.10],
        ["SPX", 218.0, "call", exp2, exp2, 215.0, 3.00, 3.10],
        ["SPX", 218.0, "put", exp2, exp2, 210.0, 0.00, 0.10],
        ["SPX", 218.0, "put", exp2, exp2, 215.0, 0.00, 0.10],
        # --- Entry 3 (Feb 1) → exits at exp3 (Mar 29) ---
        ["SPX", 215.0, "call", exp3, entry3, 210.0, 7.00, 7.10],
        ["SPX", 215.0, "call", exp3, entry3, 215.0, 2.50, 2.60],
        ["SPX", 215.0, "put", exp3, entry3, 210.0, 1.90, 2.00],
        ["SPX", 215.0, "put", exp3, entry3, 215.0, 4.80, 4.90],
        # --- Exit 3 (Mar 29) ---
        ["SPX", 220.0, "call", exp3, exp3, 210.0, 10.00, 10.10],
        ["SPX", 220.0, "call", exp3, exp3, 215.0, 5.00, 5.10],
        ["SPX", 220.0, "put", exp3, exp3, 210.0, 0.00, 0.10],
        ["SPX", 220.0, "put", exp3, exp3, 215.0, 0.00, 0.10],
    ]

    df = _make_chain(rows)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_csv(df, tmpdir)
        yield path


# ---------------------------------------------------------------------------
# Losing-trade fixture — underlying drops, long calls lose
#
# Nearest selector picks 215 strike (distance 0 from underlying 215).
# Entry: mid = (2.40+2.50)/2 = 2.45
# Exit:  mid = (0.00+0.10)/2 = 0.05 (OTM, nearly worthless)
# P&L = (0.05 - 2.45) * 1 * 100 = -240
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def losing_csv():
    """Chain where underlying drops — long calls lose money."""
    rows = [
        # Entry (Jan 2)
        ["SPX", 215.0, "call", "2018-01-31", "2018-01-02", 210.0, 5.90, 6.00],
        ["SPX", 215.0, "call", "2018-01-31", "2018-01-02", 215.0, 2.40, 2.50],
        ["SPX", 215.0, "put", "2018-01-31", "2018-01-02", 210.0, 0.80, 0.90],
        ["SPX", 215.0, "put", "2018-01-31", "2018-01-02", 215.0, 2.30, 2.40],
        # Exit (Jan 31) — underlying dropped to 208
        ["SPX", 208.0, "call", "2018-01-31", "2018-01-31", 210.0, 0.00, 0.10],
        ["SPX", 208.0, "call", "2018-01-31", "2018-01-31", 215.0, 0.00, 0.10],
        ["SPX", 208.0, "put", "2018-01-31", "2018-01-31", 210.0, 1.90, 2.00],
        ["SPX", 208.0, "put", "2018-01-31", "2018-01-31", 215.0, 6.90, 7.00],
    ]
    df = _make_chain(rows)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = _write_csv(df, tmpdir)
        yield path


# ---------------------------------------------------------------------------
# E2E: long_calls — hand-calculated P&L
# ---------------------------------------------------------------------------


class TestLongCallsE2E:
    """Full pipeline: CSV → csv_data → long_calls → simulate.

    With nearest selector and underlying at 212, the 210 strike is nearest.
    Trade 1: buy ask 4.60, sell bid 6.00.
      realized_pnl = (6.00 - 4.60) * 1 * 100 = 140.00
    """

    def test_full_pipeline_returns_simulation_result(self, chain_csv):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls)
        assert isinstance(result, SimulationResult)

    def test_trade_log_has_correct_columns(self, chain_csv):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls)
        assert set(result.trade_log.columns) == set(_TRADE_LOG_COLUMNS)

    def test_trade_count(self, chain_csv):
        data = op.csv_data(chain_csv)
        # max_positions=1: trade 2 overlaps trade 1, so only 2 trades execute
        result = op.simulate(data, op.long_calls, max_positions=1)
        assert len(result.trade_log) == 2

    def test_first_trade_pnl(self, chain_csv):
        """Verify hand-calculated P&L for the first long call trade.

        Nearest selector picks 210 strike (closest to underlying 212).
        entry_cost = mid = (4.50+4.60)/2 = 4.55
        exit_proceeds = mid = (6.00+6.10)/2 = 6.05
        realized_pnl = (6.05 - 4.55) * 1 * 100 = 150.00
        """
        data = op.csv_data(chain_csv)
        result = op.simulate(
            data, op.long_calls, capital=100_000, quantity=1, multiplier=100
        )
        first = result.trade_log.iloc[0]
        assert first["entry_cost"] == pytest.approx(4.55)
        assert first["exit_proceeds"] == pytest.approx(6.05)
        assert first["realized_pnl"] == pytest.approx(150.0)
        assert first["dollar_cost"] == pytest.approx(455.0)

    def test_equity_curve_matches_trade_log(self, chain_csv):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls)
        assert len(result.equity_curve) == len(result.trade_log)
        assert result.equity_curve.iloc[-1] == result.trade_log.iloc[-1]["equity"]

    def test_summary_metrics_consistent(self, chain_csv):
        capital = 50_000.0
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls, capital=capital)
        s = result.summary

        assert s["total_trades"] == len(result.trade_log)
        assert s["winning_trades"] + s["losing_trades"] == s["total_trades"]
        assert s["total_return"] == pytest.approx(s["total_pnl"] / capital)

    def test_cumulative_pnl_is_cumsum(self, chain_csv):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls)
        log = result.trade_log
        expected_cum = log["realized_pnl"].cumsum()
        pd.testing.assert_series_equal(
            log["cumulative_pnl"].reset_index(drop=True),
            expected_cum.reset_index(drop=True),
            check_names=False,
        )

    def test_equity_equals_capital_plus_cumulative_pnl(self, chain_csv):
        capital = 75_000.0
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls, capital=capital)
        log = result.trade_log
        expected_equity = capital + log["cumulative_pnl"]
        pd.testing.assert_series_equal(
            log["equity"].reset_index(drop=True),
            expected_equity.reset_index(drop=True),
            check_names=False,
        )


# ---------------------------------------------------------------------------
# E2E: losing long call
# ---------------------------------------------------------------------------


class TestLosingTradeE2E:
    """Underlying drops — long call expires nearly worthless.

    Nearest selector picks 215 strike (distance 0 from underlying 215).
    entry_cost = mid = (2.40+2.50)/2 = 2.45
    exit_proceeds = mid = (0.00+0.10)/2 = 0.05
    realized_pnl = (0.05 - 2.45) * 1 * 100 = -240.00
    """

    def test_losing_trade_negative_pnl(self, losing_csv):
        data = op.csv_data(losing_csv)
        result = op.simulate(
            data, op.long_calls, capital=100_000, quantity=1, multiplier=100
        )
        assert len(result.trade_log) == 1
        trade = result.trade_log.iloc[0]
        assert trade["realized_pnl"] == pytest.approx(-240.0)
        assert trade["equity"] == pytest.approx(100_000 - 240.0)

    def test_losing_trade_counted_as_loss(self, losing_csv):
        data = op.csv_data(losing_csv)
        result = op.simulate(data, op.long_calls)
        assert result.summary["losing_trades"] == 1
        assert result.summary["winning_trades"] == 0
        assert result.summary["win_rate"] == pytest.approx(0.0)

    def test_total_return_reflects_loss(self, losing_csv):
        capital = 100_000.0
        data = op.csv_data(losing_csv)
        result = op.simulate(data, op.long_calls, capital=capital)
        assert result.summary["total_pnl"] == pytest.approx(-240.0)
        assert result.summary["total_return"] == pytest.approx(-240.0 / capital)


# ---------------------------------------------------------------------------
# E2E: short_puts — hand-calculated P&L
# ---------------------------------------------------------------------------


class TestShortPutsE2E:
    """Full pipeline for a credit strategy.

    Using the losing_csv fixture where underlying drops to 208:
      short put 210: sell bid 0.80, buy back ask 2.00
      entry_cost = -0.80 (credit received)
      exit_proceeds = -2.00 (paid to close)
      realized_pnl = (-2.00 - (-0.80)) * 100 = -120

    Using the chain_csv where underlying rises to 216:
      short put 210: sell bid 2.40, put expires worthless (bid=0.00)
      entry_cost = -2.40 (credit received)
      exit_proceeds = -0.00
      realized_pnl = (0.00 - (-2.40)) * 100 = 240
    """

    def test_short_puts_entry_cost_negative(self, chain_csv):
        """Short strategies receive premium → entry_cost is negative."""
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.short_puts)
        assert len(result.trade_log) > 0
        assert (result.trade_log["entry_cost"] < 0).all()

    def test_short_puts_winning_when_otm(self, chain_csv):
        """Puts expire worthless when underlying rises → positive P&L."""
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.short_puts, capital=100_000)
        first = result.trade_log.iloc[0]
        assert first["realized_pnl"] > 0

    def test_short_puts_losing_when_itm(self, losing_csv):
        """Underlying drops → short puts lose money (buy back > premium)."""
        data = op.csv_data(losing_csv)
        result = op.simulate(data, op.short_puts, capital=100_000)
        assert len(result.trade_log) == 1
        trade = result.trade_log.iloc[0]
        assert trade["entry_cost"] < 0  # received premium
        assert trade["realized_pnl"] < 0  # lost money


# ---------------------------------------------------------------------------
# E2E: spread strategy
# ---------------------------------------------------------------------------


class TestSpreadE2E:
    """Full pipeline for a multi-leg strategy."""

    def test_long_call_spread_produces_trades(self, chain_csv):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_call_spread)
        assert isinstance(result, SimulationResult)
        assert len(result.trade_log) > 0

    def test_spread_trade_log_complete(self, chain_csv):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_call_spread)
        log = result.trade_log
        assert set(log.columns) == set(_TRADE_LOG_COLUMNS)
        assert not log["realized_pnl"].isna().any()
        assert not log["equity"].isna().any()


# ---------------------------------------------------------------------------
# E2E: position limits across full pipeline
# ---------------------------------------------------------------------------


class TestPositionLimitsE2E:
    """Position limits work correctly through the full pipeline."""

    def test_max_positions_one_no_overlap(self, chain_csv):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls, max_positions=1)
        log = result.trade_log
        # With max_positions=1, no two trades should overlap
        for i in range(len(log) - 1):
            assert log.iloc[i + 1]["entry_date"] >= log.iloc[i]["exit_date"]

    def test_higher_position_limit_allows_overlapping_trade(self, chain_csv):
        """Trade 2 overlaps trade 1. max_positions=1 skips it; higher allows it."""
        data = op.csv_data(chain_csv)
        r1 = op.simulate(data, op.long_calls, max_positions=1)
        r10 = op.simulate(data, op.long_calls, max_positions=10)
        assert len(r1.trade_log) == 2  # trades 1 and 3 (trade 2 skipped)
        assert len(r10.trade_log) == 3  # all three trades


# ---------------------------------------------------------------------------
# E2E: quantity and multiplier affect dollar amounts
# ---------------------------------------------------------------------------


class TestQuantityMultiplierE2E:
    """Verify quantity and multiplier scale dollar amounts correctly."""

    def test_quantity_scales_dollar_cost(self, chain_csv):
        data = op.csv_data(chain_csv)
        r1 = op.simulate(data, op.long_calls, quantity=1)
        r3 = op.simulate(data, op.long_calls, quantity=3)

        assert len(r1.trade_log) > 0
        assert len(r3.trade_log) > 0
        ratio = (
            r3.trade_log.iloc[0]["dollar_cost"] / r1.trade_log.iloc[0]["dollar_cost"]
        )
        assert ratio == pytest.approx(3.0)

    def test_multiplier_scales_pnl(self, chain_csv):
        data = op.csv_data(chain_csv)
        r100 = op.simulate(data, op.long_calls, multiplier=100)
        r50 = op.simulate(data, op.long_calls, multiplier=50)

        assert len(r100.trade_log) > 0
        assert len(r50.trade_log) > 0
        ratio = (
            r100.trade_log.iloc[0]["realized_pnl"]
            / r50.trade_log.iloc[0]["realized_pnl"]
        )
        assert ratio == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# E2E: selector variants
# ---------------------------------------------------------------------------


class TestSelectorsE2E:
    """Different selectors produce valid results through the full pipeline."""

    @pytest.mark.parametrize(
        "selector", ["nearest", "first", "highest_premium", "lowest_premium"]
    )
    def test_all_builtin_selectors_produce_results(self, chain_csv, selector):
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls, selector=selector)
        assert isinstance(result, SimulationResult)
        assert set(result.trade_log.columns) == set(_TRADE_LOG_COLUMNS)

    def test_nearest_vs_highest_premium_select_different_strikes(self, chain_csv):
        """Nearest picks 210 (closer to underlying 212);
        highest_premium also picks 210 (higher ask). Verify entry costs match
        the expected strikes."""
        data = op.csv_data(chain_csv)
        r_nearest = op.simulate(data, op.long_calls, selector="nearest")
        r_lowest = op.simulate(data, op.long_calls, selector="lowest_premium")
        assert len(r_nearest.trade_log) > 0
        assert len(r_lowest.trade_log) > 0
        # Lowest premium picks 215 strike (mid=1.45), nearest picks 210 (mid=4.55)
        assert r_nearest.trade_log.iloc[0]["entry_cost"] == pytest.approx(4.55)
        assert r_lowest.trade_log.iloc[0]["entry_cost"] == pytest.approx(1.45)


# ---------------------------------------------------------------------------
# E2E: signal-based entry filtering
#
# The chain_csv entry dates and their weekdays:
#   Jan 2  = Tuesday  (weekday 1)
#   Jan 16 = Tuesday  (weekday 1)
#   Feb 1  = Thursday (weekday 3)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def stock_data(chain_csv):
    """Build a stock price DataFrame from the chain CSV for signal computation.

    apply_signal needs: underlying_symbol, quote_date, underlying_price.
    We extract unique (symbol, date, price) rows from the option chain.
    """
    data = op.csv_data(chain_csv)
    stock = (
        data[["underlying_symbol", "quote_date", "underlying_price"]]
        .drop_duplicates(["underlying_symbol", "quote_date"])
        .sort_values("quote_date")
        .reset_index(drop=True)
    )
    return stock


class TestSignalEntryE2E:
    """Signal-filtered entry dates through the full pipeline."""

    def test_day_of_week_filters_entries(self, chain_csv, stock_data):
        """day_of_week(3) = Thursday only allows Feb 1 entry."""
        entry_dates = apply_signal(stock_data, day_of_week(3))  # Thursday
        data = op.csv_data(chain_csv)
        result = op.simulate(
            data, op.long_calls, entry_dates=entry_dates, max_positions=10
        )
        assert len(result.trade_log) == 1
        # The only Thursday entry is Feb 1
        entry = result.trade_log.iloc[0]["entry_date"]
        assert pd.Timestamp(entry).day == 1
        assert pd.Timestamp(entry).month == 2

    def test_day_of_week_tuesday_allows_two_entries(self, chain_csv, stock_data):
        """day_of_week(1) = Tuesday allows Jan 2 and Jan 16 entries."""
        entry_dates = apply_signal(stock_data, day_of_week(1))  # Tuesday
        data = op.csv_data(chain_csv)
        result = op.simulate(
            data, op.long_calls, entry_dates=entry_dates, max_positions=10
        )
        assert len(result.trade_log) == 2

    def test_no_matching_signal_returns_empty(self, chain_csv, stock_data):
        """day_of_week(4) = Friday — no entries on Friday → empty result."""
        entry_dates = apply_signal(stock_data, day_of_week(4))  # Friday
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls, entry_dates=entry_dates)
        assert len(result.trade_log) == 0
        assert result.summary["total_trades"] == 0

    def test_or_signals_union(self, chain_csv, stock_data):
        """or_signals(Tuesday, Thursday) allows all 3 entries."""
        sig = or_signals(day_of_week(1), day_of_week(3))
        entry_dates = apply_signal(stock_data, sig)
        data = op.csv_data(chain_csv)
        result = op.simulate(
            data, op.long_calls, entry_dates=entry_dates, max_positions=10
        )
        assert len(result.trade_log) == 3

    def test_and_signals_intersection(self, chain_csv, stock_data):
        """and_signals(Tuesday, Thursday) — impossible, empty result."""
        sig = and_signals(day_of_week(1), day_of_week(3))
        entry_dates = apply_signal(stock_data, sig)
        data = op.csv_data(chain_csv)
        result = op.simulate(data, op.long_calls, entry_dates=entry_dates)
        assert len(result.trade_log) == 0

    def test_signal_with_position_limits(self, chain_csv, stock_data):
        """Tuesday signal gives 2 entries, but max_positions=1 and they overlap
        (Jan 16 entry < Jan 31 exit), so only 1 trade executes."""
        entry_dates = apply_signal(stock_data, day_of_week(1))
        data = op.csv_data(chain_csv)
        result = op.simulate(
            data, op.long_calls, entry_dates=entry_dates, max_positions=1
        )
        assert len(result.trade_log) == 1

    def test_signal_pnl_matches_unfiltered(self, chain_csv, stock_data):
        """Thursday-only signal picks the same trade as the Feb 1 entry
        in the unfiltered run. Verify P&L matches."""
        entry_dates = apply_signal(stock_data, day_of_week(3))
        data = op.csv_data(chain_csv)

        # Signal-filtered: only the Feb 1 trade
        r_signal = op.simulate(data, op.long_calls, entry_dates=entry_dates)
        assert len(r_signal.trade_log) == 1

        # Unfiltered with max_positions=10: all 3 trades
        r_all = op.simulate(data, op.long_calls, max_positions=10)
        assert len(r_all.trade_log) == 3

        # The Feb 1 trade should have the same P&L in both runs
        signal_pnl = r_signal.trade_log.iloc[0]["realized_pnl"]
        # Find the Feb 1 trade in the unfiltered run
        all_feb = r_all.trade_log[
            pd.to_datetime(r_all.trade_log["entry_date"]).dt.month == 2
        ]
        assert len(all_feb) == 1
        assert all_feb.iloc[0]["realized_pnl"] == pytest.approx(signal_pnl)

    def test_sma_signal_with_sufficient_history(self, chain_csv):
        """sma_above with a short period on synthetic stock data.

        Build stock data with enough history for the SMA to compute,
        then verify it correctly filters entries.
        """
        # Build 30 days of stock data with rising prices (always above SMA)
        dates = pd.bdate_range("2017-12-01", "2018-02-28")
        stock = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": range(200, 200 + len(dates)),
            }
        )
        # SMA(5) on monotonically rising prices → price always above SMA
        entry_dates = apply_signal(stock, sma_above(5))
        data = op.csv_data(chain_csv)
        result = op.simulate(
            data, op.long_calls, entry_dates=entry_dates, max_positions=10
        )
        # All 3 entry dates should pass the SMA filter since prices always rise
        assert len(result.trade_log) == 3


# ---------------------------------------------------------------------------
# E2E: empty / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCasesE2E:
    """Edge cases through the full pipeline."""

    def test_empty_csv(self):
        """CSV with headers but no data rows."""
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
        df = pd.DataFrame(columns=cols)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_csv(df, tmpdir)
            data = op.csv_data(path)
            result = op.simulate(data, op.long_calls)
            assert isinstance(result, SimulationResult)
            assert len(result.trade_log) == 0
            assert result.summary["total_trades"] == 0

    def test_single_date_no_exit(self):
        """Only one quote date — no exit possible, should return empty."""
        rows = [
            ["SPX", 212.0, "call", "2018-01-31", "2018-01-02", 210.0, 4.50, 4.60],
            ["SPX", 212.0, "put", "2018-01-31", "2018-01-02", 210.0, 2.40, 2.50],
        ]
        df = _make_chain(rows)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_csv(df, tmpdir)
            data = op.csv_data(path)
            result = op.simulate(data, op.long_calls)
            assert isinstance(result, SimulationResult)
            assert len(result.trade_log) == 0
