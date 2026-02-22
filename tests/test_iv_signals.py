"""Tests for IV rank signal functions and IV surface/term structure tools."""

import pandas as pd
import pytest

from optopsy.signals import (
    _compute_atm_iv,
    _compute_iv_rank_series,
    apply_signal,
    iv_rank_above,
    iv_rank_below,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def options_data_with_iv():
    """Options data with implied_volatility for IV rank signal testing.

    Creates 60 trading days of options data with a known IV pattern:
    - Days 1-20: IV rising from 0.15 to 0.35 (low to high)
    - Days 21-40: IV stays high at ~0.35
    - Days 41-60: IV drops from 0.35 to 0.15
    """
    dates = pd.date_range("2023-01-01", periods=60, freq="B")
    rows = []
    for i, qd in enumerate(dates):
        # IV pattern: rise, plateau, fall
        if i < 20:
            base_iv = 0.15 + (i / 20) * 0.20  # 0.15 -> 0.35
        elif i < 40:
            base_iv = 0.35
        else:
            base_iv = 0.35 - ((i - 40) / 20) * 0.20  # 0.35 -> 0.15

        underlying_price = 100.0 + i * 0.1
        exp_date = qd + pd.Timedelta(days=30)

        # Add multiple strikes/types per date
        for strike_offset in [-5, 0, 5]:
            strike = underlying_price + strike_offset
            for opt_type in ["c", "p"]:
                # IV smile: slightly higher IV for OTM options
                iv = base_iv + abs(strike_offset) * 0.005
                if opt_type == "c":
                    bid = max(underlying_price - strike, 0) + 1.0
                else:
                    bid = max(strike - underlying_price, 0) + 1.0
                rows.append(
                    [
                        "SPX",
                        underlying_price,
                        opt_type,
                        exp_date,
                        qd,
                        strike,
                        bid,
                        bid + 0.10,
                        iv,
                    ]
                )

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "implied_volatility",
    ]
    return pd.DataFrame(data=rows, columns=cols)


@pytest.fixture
def options_data_no_iv():
    """Options data without implied_volatility column."""
    dates = pd.date_range("2023-01-01", periods=10, freq="B")
    rows = []
    for qd in dates:
        exp_date = qd + pd.Timedelta(days=30)
        rows.append(["SPX", 100.0, "c", exp_date, qd, 100.0, 3.0, 3.10])
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


@pytest.fixture
def multi_symbol_options_iv():
    """Options data with IV for two symbols with opposite IV trends."""
    dates = pd.date_range("2023-01-01", periods=30, freq="B")
    rows = []
    for i, qd in enumerate(dates):
        exp_date = qd + pd.Timedelta(days=30)
        # SPX: IV rising
        spx_iv = 0.15 + (i / 30) * 0.30
        # NDX: IV falling
        ndx_iv = 0.45 - (i / 30) * 0.30

        for symbol, iv, price in [("SPX", spx_iv, 100.0), ("NDX", ndx_iv, 200.0)]:
            rows.append([symbol, price, "c", exp_date, qd, price, 3.0, 3.10, iv])
            rows.append([symbol, price, "p", exp_date, qd, price, 3.0, 3.10, iv])

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "implied_volatility",
    ]
    return pd.DataFrame(data=rows, columns=cols)


# ============================================================================
# Tests for _compute_atm_iv helper
# ============================================================================


class TestComputeATMIV:
    def test_returns_one_row_per_date(self, options_data_with_iv):
        """Should return exactly one ATM IV value per (symbol, date) pair."""
        result = _compute_atm_iv(options_data_with_iv)
        n_dates = options_data_with_iv["quote_date"].nunique()
        assert len(result) == n_dates
        assert "implied_volatility" in result.columns
        assert "underlying_symbol" in result.columns
        assert "quote_date" in result.columns

    def test_selects_closest_strike(self):
        """Should pick the strike closest to underlying_price."""
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 3,
                "quote_date": [pd.Timestamp("2023-01-01")] * 3,
                "underlying_price": [100.0] * 3,
                "strike": [95.0, 100.0, 105.0],
                "option_type": ["c", "c", "c"],
                "implied_volatility": [0.20, 0.25, 0.30],
            }
        )
        result = _compute_atm_iv(data)
        assert len(result) == 1
        assert result["implied_volatility"].iloc[0] == pytest.approx(0.25)

    def test_averages_call_and_put_iv(self):
        """Should average IV across call and put at the ATM strike."""
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 2,
                "quote_date": [pd.Timestamp("2023-01-01")] * 2,
                "underlying_price": [100.0] * 2,
                "strike": [100.0, 100.0],
                "option_type": ["c", "p"],
                "implied_volatility": [0.20, 0.30],
            }
        )
        result = _compute_atm_iv(data)
        assert len(result) == 1
        assert result["implied_volatility"].iloc[0] == pytest.approx(0.25)

    def test_empty_when_no_iv(self):
        """Should return empty DataFrame when all IV values are NaN."""
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"],
                "quote_date": [pd.Timestamp("2023-01-01")],
                "underlying_price": [100.0],
                "strike": [100.0],
                "option_type": ["c"],
                "implied_volatility": [float("nan")],
            }
        )
        result = _compute_atm_iv(data)
        assert result.empty

    def test_multi_symbol(self, multi_symbol_options_iv):
        """Should compute ATM IV independently per symbol."""
        result = _compute_atm_iv(multi_symbol_options_iv)
        spx_rows = result[result["underlying_symbol"] == "SPX"]
        ndx_rows = result[result["underlying_symbol"] == "NDX"]
        n_dates = multi_symbol_options_iv["quote_date"].nunique()
        assert len(spx_rows) == n_dates
        assert len(ndx_rows) == n_dates


# ============================================================================
# Tests for _compute_iv_rank_series
# ============================================================================


class TestComputeIVRankSeries:
    def test_rank_range(self, options_data_with_iv):
        """IV rank values should be between 0 and 1."""
        atm_iv = _compute_atm_iv(options_data_with_iv)
        rank = _compute_iv_rank_series(atm_iv, window=20)
        valid = rank.dropna()
        assert (valid >= 0).all()
        assert (valid <= 1).all()

    def test_high_iv_gets_high_rank(self, options_data_with_iv):
        """When IV is at the top of its range, rank should be near 1."""
        atm_iv = _compute_atm_iv(options_data_with_iv)
        rank = _compute_iv_rank_series(atm_iv, window=20)
        # Day 20-40 has high IV (0.35), so rank should be high after warmup
        # After 20 days of seeing the full range, rank at plateau should be ~1
        assert rank.iloc[25] > 0.8

    def test_low_iv_gets_low_rank(self, options_data_with_iv):
        """When IV is at the bottom of its range, rank should be near 0."""
        atm_iv = _compute_atm_iv(options_data_with_iv)
        rank = _compute_iv_rank_series(atm_iv, window=252)
        # Last day: IV is back to 0.15 after seeing 0.35, so rank should be low
        assert rank.iloc[-1] < 0.2

    def test_constant_iv_returns_half(self):
        """When IV is constant, rank should be 0.5 (denom is 0)."""
        dates = pd.date_range("2023-01-01", periods=10, freq="B")
        atm_iv = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "implied_volatility": [0.25] * 10,
            }
        )
        rank = _compute_iv_rank_series(atm_iv, window=5)
        assert (rank == 0.5).all()


# ============================================================================
# Tests for iv_rank_above / iv_rank_below signals
# ============================================================================


class TestIVRankSignals:
    def test_iv_rank_above_returns_bool_series(self, options_data_with_iv):
        """iv_rank_above should return a boolean Series."""
        sig = iv_rank_above(threshold=0.5, window=20)
        result = sig(options_data_with_iv)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert len(result) == len(options_data_with_iv)

    def test_iv_rank_below_returns_bool_series(self, options_data_with_iv):
        """iv_rank_below should return a boolean Series."""
        sig = iv_rank_below(threshold=0.5, window=20)
        result = sig(options_data_with_iv)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert len(result) == len(options_data_with_iv)

    def test_iv_rank_above_fires_during_high_iv(self, options_data_with_iv):
        """iv_rank_above should fire when IV is in the top of its range."""
        sig = iv_rank_above(threshold=0.8, window=20)
        result = sig(options_data_with_iv)
        assert result.any(), "Expected iv_rank_above to fire during high IV period"

    def test_iv_rank_below_fires_during_low_iv(self, options_data_with_iv):
        """iv_rank_below should fire when IV is in the bottom of its range."""
        sig = iv_rank_below(threshold=0.2, window=252)
        result = sig(options_data_with_iv)
        assert result.any(), "Expected iv_rank_below to fire during low IV period"

    def test_iv_rank_above_below_not_both_true(self, options_data_with_iv):
        """iv_rank_above(0.5) and iv_rank_below(0.5) should not both be True."""
        above = iv_rank_above(threshold=0.5, window=20)(options_data_with_iv)
        below = iv_rank_below(threshold=0.5, window=20)(options_data_with_iv)
        # They're complementary: rank > 0.5 vs rank < 0.5, so no overlap
        assert not (above & below).any()

    def test_no_iv_column_returns_all_false(self, options_data_no_iv):
        """Signal should return all False when data lacks implied_volatility."""
        result = iv_rank_above(threshold=0.5)(options_data_no_iv)
        assert not result.any()

    def test_multi_symbol_isolation(self, multi_symbol_options_iv):
        """IV rank should be computed independently per symbol."""
        sig = iv_rank_above(threshold=0.5, window=20)
        result = sig(multi_symbol_options_iv)
        # SPX has rising IV -> should have some True at the end
        spx_mask = multi_symbol_options_iv["underlying_symbol"] == "SPX"
        ndx_mask = multi_symbol_options_iv["underlying_symbol"] == "NDX"
        # SPX last few days should have high rank (IV rising)
        assert result[spx_mask].iloc[-1]
        # NDX last few days should have low rank (IV falling)
        assert not result[ndx_mask].iloc[-1]


# ============================================================================
# Tests for apply_signal with IV rank
# ============================================================================


class TestApplySignalWithIVRank:
    def test_apply_signal_with_iv_rank(self, options_data_with_iv):
        """apply_signal should work with IV rank signals on options data."""
        sig = iv_rank_above(threshold=0.5, window=20)
        result = apply_signal(options_data_with_iv, sig)
        assert isinstance(result, pd.DataFrame)
        assert "underlying_symbol" in result.columns
        assert "quote_date" in result.columns
        assert len(result) > 0

    def test_apply_signal_iv_rank_below(self, options_data_with_iv):
        """apply_signal should work with iv_rank_below."""
        sig = iv_rank_below(threshold=0.3, window=252)
        result = apply_signal(options_data_with_iv, sig)
        assert isinstance(result, pd.DataFrame)

    def test_apply_signal_no_iv_returns_empty(self, options_data_no_iv):
        """apply_signal with IV signal on data without IV returns empty."""
        sig = iv_rank_above(threshold=0.5)
        result = apply_signal(options_data_no_iv, sig)
        assert len(result) == 0

    def test_high_threshold_fewer_dates(self, options_data_with_iv):
        """Higher threshold should produce fewer valid dates."""
        dates_50 = apply_signal(
            options_data_with_iv, iv_rank_above(threshold=0.5, window=20)
        )
        dates_80 = apply_signal(
            options_data_with_iv, iv_rank_above(threshold=0.8, window=20)
        )
        assert len(dates_80) <= len(dates_50)
