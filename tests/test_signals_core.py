"""Tests for signal combinators, Signal class, sustained(), custom_signal(), and edge cases."""

import pandas as pd
import pytest

from optopsy.signals import (
    Signal,
    and_signals,
    apply_signal,
    custom_signal,
    day_of_week,
    or_signals,
    rsi_below,
    signal,
    sma_above,
    sma_below,
    sustained,
)
from optopsy.strategies import long_calls

# ============================================================================
# Local fixtures
# ============================================================================


@pytest.fixture
def multi_symbol_price_data():
    """Two symbols with opposite trends: SPX declining, NDX rising."""
    dates = pd.date_range("2018-01-01", periods=20, freq="B")
    rows = []
    for i, d in enumerate(dates):
        rows.append({"underlying_symbol": "SPX", "quote_date": d, "close": 100.0 - i})
        rows.append({"underlying_symbol": "NDX", "quote_date": d, "close": 100.0 + i})
    return pd.DataFrame(rows)


def _make_data(prices, symbol="SPX"):
    """Helper: build a minimal price DataFrame from a list of prices."""
    dates = pd.date_range("2018-01-01", periods=len(prices), freq="B")
    return pd.DataFrame(
        {"underlying_symbol": symbol, "quote_date": dates, "close": prices}
    )


# ============================================================================
# Signal combinators
# ============================================================================


class TestSignalCombinators:
    def test_and_signals(self, price_data, always_true_signal):
        """and_signals should require all signals to be True."""

        def always_false(data):
            return pd.Series(False, index=data.index)

        result = and_signals(always_true_signal, always_true_signal)(price_data)
        assert result.all()

        result = and_signals(always_true_signal, always_false)(price_data)
        assert not result.any()

    def test_or_signals(self, price_data, always_true_signal):
        """or_signals should require at least one signal to be True."""

        def always_false(data):
            return pd.Series(False, index=data.index)

        result = or_signals(always_true_signal, always_false)(price_data)
        assert result.all()

        result = or_signals(always_false, always_false)(price_data)
        assert not result.any()

    def test_and_signals_with_real_signals(self, price_data):
        """and_signals should work with actual signal functions."""
        signal = and_signals(day_of_week(0, 1, 2, 3, 4), sma_below(period=5))
        result = signal(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool


# ============================================================================
# Signal class and fluent API
# ============================================================================


class TestSignalClass:
    def test_signal_is_callable(self, price_data):
        """Signal wrapping a SignalFunc is itself callable."""
        sig = Signal(day_of_week(0))
        result = sig(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_signal_and_operator(self, price_data):
        """& operator should produce the logical AND of both signals."""
        # All weekdays AND Monday only = Monday only
        sig1 = Signal(day_of_week(0, 1, 2, 3, 4))
        sig2 = Signal(day_of_week(0))
        combined = sig1 & sig2
        result = combined(price_data)
        expected = day_of_week(0)(price_data)
        pd.testing.assert_series_equal(result, expected)

    def test_signal_or_operator(self, price_data):
        """| operator should produce the logical OR of both signals."""
        sig1 = Signal(day_of_week(0))  # Monday
        sig2 = Signal(day_of_week(4))  # Friday
        combined = sig1 | sig2
        result = combined(price_data)
        expected = or_signals(day_of_week(0), day_of_week(4))(price_data)
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_signal_chaining_three_conditions(self, price_data):
        """Three signals chained with | should equal or_signals with all three."""
        sig = Signal(day_of_week(0)) | Signal(day_of_week(1)) | Signal(day_of_week(2))
        result = sig(price_data)
        expected = or_signals(day_of_week(0), day_of_week(1), day_of_week(2))(
            price_data
        )
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_signal_factory_function(self, price_data):
        """signal() factory produces a Signal equivalent to Signal()."""
        sig = signal(day_of_week(3))
        result = sig(price_data)
        expected = day_of_week(3)(price_data)
        pd.testing.assert_series_equal(result, expected)

    def test_signal_factory_supports_and(self, price_data):
        """signal() return value should support & operator."""
        combined = signal(day_of_week(0)) & signal(day_of_week(1))
        result = combined(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        # Monday AND Tuesday — no single day can be both
        assert not result.any()

    def test_signal_accepted_via_apply_signal(self, option_data_entry_exit):
        """Signal object accepted by apply_signal and used as entry_dates."""
        sig = Signal(day_of_week(3))  # Thursday
        entry_dates = apply_signal(option_data_entry_exit, sig)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)

    def test_signal_combined_with_callable(self, option_data_entry_exit):
        """Signal combined with another Signal and used via apply_signal works."""

        def always_true(data):
            return pd.Series(True, index=data.index)

        sig = Signal(day_of_week(3)) & Signal(always_true)
        entry_dates = apply_signal(option_data_entry_exit, sig)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)


# ============================================================================
# Multi-symbol per-symbol isolation
# ============================================================================


class TestMultiSymbolIsolation:
    """Verify signals compute per-symbol, not mixing price histories."""

    def test_rsi_computed_per_symbol(self, multi_symbol_price_data):
        """RSI on declining SPX should fire; RSI on rising NDX should not."""
        sig = rsi_below(period=14, threshold=30)
        result = sig(multi_symbol_price_data)
        spx_mask = multi_symbol_price_data["underlying_symbol"] == "SPX"
        ndx_mask = multi_symbol_price_data["underlying_symbol"] == "NDX"
        # SPX strong downtrend -> last bar RSI < 30
        assert result.loc[spx_mask].iloc[-1] == True
        # NDX strong uptrend -> last bar RSI should NOT be < 30
        assert result.loc[ndx_mask].iloc[-1] == False

    def test_sma_computed_per_symbol(self, multi_symbol_price_data):
        """SMA signal isolates each symbol's price history."""
        sig_below = sma_below(period=10)
        sig_above = sma_above(period=10)
        result_below = sig_below(multi_symbol_price_data)
        result_above = sig_above(multi_symbol_price_data)
        spx_mask = multi_symbol_price_data["underlying_symbol"] == "SPX"
        ndx_mask = multi_symbol_price_data["underlying_symbol"] == "NDX"
        # SPX declining: last bar should be below its SMA
        assert result_below.loc[spx_mask].iloc[-1] == True
        # NDX rising: last bar should be above its SMA
        assert result_above.loc[ndx_mask].iloc[-1] == True

    def test_signal_result_length_matches_all_symbols(self, multi_symbol_price_data):
        """Signal output must have same length as input (all symbols)."""
        result = rsi_below()(multi_symbol_price_data)
        assert len(result) == len(multi_symbol_price_data)


# ============================================================================
# sustained() combinator
# ============================================================================


class TestSustainedSignal:
    def test_sustained_not_true_before_streak(self):
        """Should be False when streak is shorter than required days."""
        # Always-True signal, but only 4 bars, days=5 → all False
        data = _make_data([100.0] * 4)

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = sustained(always_true, days=5)(data)
        assert not result.any()

    def test_sustained_fires_after_streak(self):
        """Should be True on the Nth consecutive True bar (exactly days bars)."""
        # 6 bars of always-True, days=5 → bars 4 and 5 (0-indexed) should fire
        data = _make_data([100.0] * 6)

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = sustained(always_true, days=5)(data)
        # First 4 bars False (warmup), last 2 True
        assert not result.iloc[:4].any()
        assert result.iloc[4]
        assert result.iloc[5]

    def test_sustained_resets_on_false(self):
        """A single False bar breaks the streak; must restart from 0."""
        # True*4, False, True*5 — streak resets; only last 5 bars should fire
        inner_bools = [True] * 4 + [False] + [True] * 5
        data = _make_data([100.0] * len(inner_bools))

        def inner(d):
            return pd.Series(inner_bools, index=d.index)

        result = sustained(inner, days=5)(data)
        # All bars before the streak of 5 is complete should be False
        assert not result.iloc[:8].any()
        # The 5th consecutive True (index 9, 0-based) should fire
        assert result.iloc[9]

    def test_sustained_all_false_returns_all_false(self):
        """Wrapping an always-False signal stays all False regardless of days."""
        data = _make_data([100.0] * 20)

        def always_false(d):
            return pd.Series(False, index=d.index)

        result = sustained(always_false, days=3)(data)
        assert not result.any()

    def test_sustained_all_true_fires_after_warmup(self):
        """Wrapping always-True: first days-1 bars False, then True forever."""
        days = 4
        n = 10
        data = _make_data([100.0] * n)

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = sustained(always_true, days=days)(data)
        assert not result.iloc[: days - 1].any()
        assert result.iloc[days - 1 :].all()

    def test_sustained_days_1_is_identity(self):
        """days=1 should produce the same output as the unwrapped signal."""
        data = _make_data([100.0 - i for i in range(20)])
        inner = rsi_below(period=14, threshold=30)
        raw = inner(data)
        wrapped = sustained(inner, days=1)(data)
        pd.testing.assert_series_equal(raw.astype(bool), wrapped)

    def test_sustained_per_symbol_isolation(self, multi_symbol_price_data):
        """Each symbol's streak is counted independently."""
        # SPX is declining (RSI will drop below 30), NDX rising (RSI stays high).
        # With days=1 we test that streaks don't bleed across symbols.
        inner = rsi_below(period=14, threshold=30)
        raw = inner(multi_symbol_price_data)
        wrapped = sustained(inner, days=1)(multi_symbol_price_data)
        # With days=1, sustained == raw
        pd.testing.assert_series_equal(raw.astype(bool), wrapped)

    def test_sustained_returns_bool_series(self, price_data):
        """Return type must be a boolean Series with the same length as input."""
        result = sustained(rsi_below(14, 30), days=3)(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert len(result) == len(price_data)

    def test_sustained_works_with_signal_class(self, price_data):
        """sustained() output can be wrapped in Signal and combined with &."""
        # sustained(all weekdays, 1) & Monday = Monday only
        all_weekdays = day_of_week(0, 1, 2, 3, 4)
        sig = signal(sustained(all_weekdays, days=1)) & signal(day_of_week(0))
        result = sig(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        # All True entries must be Mondays
        flagged_days = price_data.loc[result, "quote_date"].dt.dayofweek
        assert (flagged_days == 0).all()

    def test_sustained_accepted_via_apply_signal(self, option_data_entry_exit):
        """sustained() output is accepted by apply_signal and used as entry_dates."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        sig = sustained(always_true, days=1)
        entry_dates = apply_signal(option_data_entry_exit, sig)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)


# ============================================================================
# Edge cases
# ============================================================================


class TestSignalEdgeCases:
    def test_ta_signal_insufficient_data_returns_all_false(self):
        """TA indicator returning None (insufficient data) should produce all-False.

        sma_below with period=20 on only 2 bars: ta.sma() returns None,
        hitting the `if indicator is None: continue` path (line 96).
        """
        dates = pd.date_range("2018-01-01", periods=2, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100.0, 101.0],
            }
        )
        result = sma_below(period=20)(data)
        assert not result.any()

    def test_ta_signal_no_price_column_returns_all_false(self):
        """TA signals should return all-False (not raise) when no close column exists.

        When the DataFrame has neither ``close`` nor ``underlying_price``,
        ``_get_close`` returns None and every TA signal skeleton falls back
        to an all-False series rather than raising KeyError.
        """
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                # No 'close' or 'underlying_price' column
                "implied_volatility": [0.2, 0.21, 0.22, 0.23, 0.24],
            }
        )
        from optopsy.signals import macd_cross_above, rsi_below

        result_rsi = rsi_below(period=14, threshold=30)(data)
        result_macd = macd_cross_above()(data)
        assert not result_rsi.any(), (
            "rsi_below should return all-False with no price column"
        )
        assert not result_macd.any(), (
            "macd_cross_above should return all-False with no price column"
        )

    def test_apply_signal_normalizes_underlying_price_to_close(self):
        """apply_signal should rename underlying_price to close (one-way normalization).

        When the input only has underlying_price, the internal df passed to the
        signal function must have close (not underlying_price). The original
        DataFrame must be unmodified.
        """
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 103.0, 104.0],
            }
        )
        seen_columns: list = []

        def capture_columns(df):
            seen_columns.append(set(df.columns))
            return pd.Series(True, index=df.index)

        apply_signal(data, capture_columns)
        # Signal received close, not underlying_price
        assert "close" in seen_columns[0]
        assert "underlying_price" not in seen_columns[0]
        # Original data is unchanged
        assert "underlying_price" in data.columns
        assert "close" not in data.columns

    def test_apply_signal_no_duplicate_when_close_provided(self):
        """apply_signal must NOT add underlying_price when input already has close."""
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100.0, 101.0, 102.0, 103.0, 104.0],
            }
        )
        seen_columns: list = []

        def capture_columns(df):
            seen_columns.append(set(df.columns))
            return pd.Series(True, index=df.index)

        apply_signal(data, capture_columns)
        assert "close" in seen_columns[0]
        assert "underlying_price" not in seen_columns[0]

    def test_sustained_days_zero_raises(self):
        """sustained() with days < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="days must be >= 1"):
            sustained(rsi_below(14, 30), days=0)

    def test_signal_repr(self):
        """Signal.__repr__ returns expected string representation."""
        inner = day_of_week(3)
        sig = Signal(inner)
        r = repr(sig)
        assert r.startswith("Signal(")
        assert r.endswith(")")


# ============================================================================
# custom_signal()
# ============================================================================


class TestCustomSignal:
    """Tests for custom_signal() — create SignalFunc from a pre-flagged DataFrame."""

    @pytest.fixture
    def flagged_df(self):
        """DataFrame with underlying_symbol, quote_date, and a boolean flag."""
        return pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY", "SPY", "SPY"],
                "quote_date": pd.to_datetime(
                    ["2018-01-02", "2018-01-03", "2018-01-04", "2018-01-05"]
                ),
                "signal": [True, False, True, False],
            }
        )

    def test_returns_callable(self, flagged_df):
        """custom_signal() should return a callable (SignalFunc)."""
        sig = custom_signal(flagged_df)
        assert callable(sig)

    def test_true_dates_are_selected(self, flagged_df):
        """Rows where flag is True should produce True in the signal output."""
        sig = custom_signal(flagged_df)
        result = sig(flagged_df)
        assert result.tolist() == [True, False, True, False]

    def test_custom_flag_col(self, flagged_df):
        """flag_col parameter should accept any boolean column name."""
        df = flagged_df.rename(columns={"signal": "buy"})
        sig = custom_signal(df, flag_col="buy")
        result = sig(df)
        assert result.tolist() == [True, False, True, False]

    def test_integer_flag_col(self, flagged_df):
        """Integer 0/1 flag columns should be treated as False/True."""
        df = flagged_df.copy()
        df["signal"] = df["signal"].astype(int)
        sig = custom_signal(df)
        result = sig(df)
        assert result.tolist() == [True, False, True, False]

    def test_apply_signal_integration(self, flagged_df):
        """custom_signal() returned SignalFunc should work with apply_signal()."""
        sig = custom_signal(flagged_df)
        result = apply_signal(flagged_df, sig)
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["underlying_symbol", "quote_date"]
        assert len(result) == 2  # only dates where flag is True
        assert set(result["quote_date"].dt.date) == {
            pd.Timestamp("2018-01-02").date(),
            pd.Timestamp("2018-01-04").date(),
        }

    def test_all_false_returns_empty(self):
        """All-False flag column should produce an empty result from apply_signal."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY"],
                "quote_date": pd.to_datetime(["2018-01-02", "2018-01-03"]),
                "signal": [False, False],
            }
        )
        sig = custom_signal(df)
        result = apply_signal(df, sig)
        assert result.empty

    def test_all_true_returns_all_dates(self, flagged_df):
        """All-True flag column should return all dates."""
        df = flagged_df.copy()
        df["signal"] = True
        sig = custom_signal(df)
        result = apply_signal(df, sig)
        assert len(result) == len(df)

    def test_composable_with_and_signals(self, flagged_df):
        """custom_signal() result should compose with and_signals()."""
        # All Tuesdays (day_of_week(1)) AND custom signal True
        # 2018-01-02 is Tuesday, flagged True → should be in result
        # 2018-01-03 is Wednesday, flagged False → not in result
        # 2018-01-04 is Thursday, flagged True → not in result (not Tuesday)
        sig = and_signals(custom_signal(flagged_df), day_of_week(1))
        result = apply_signal(flagged_df, sig)
        assert len(result) == 1
        assert result.iloc[0]["quote_date"] == pd.Timestamp("2018-01-02")

    def test_composable_with_signal_class(self, flagged_df):
        """custom_signal() result should compose with the Signal fluent API."""
        sig = signal(custom_signal(flagged_df)) & signal(day_of_week(1))
        result = apply_signal(flagged_df, sig)
        assert len(result) == 1
        assert result.iloc[0]["quote_date"] == pd.Timestamp("2018-01-02")

    def test_date_normalization(self):
        """Dates with time components should match date-only option chain dates."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"],
                "quote_date": [pd.Timestamp("2018-01-02 09:30:00")],
                "signal": [True],
            }
        )
        sig = custom_signal(df)
        # Query with date-only
        query_df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"],
                "quote_date": [pd.Timestamp("2018-01-02")],
            }
        )
        result = sig(query_df)
        assert result.iloc[0]

    def test_multi_symbol(self):
        """custom_signal() should correctly scope flags per symbol."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY", "QQQ", "QQQ"],
                "quote_date": pd.to_datetime(
                    ["2018-01-02", "2018-01-03", "2018-01-02", "2018-01-03"]
                ),
                "signal": [True, False, False, True],
            }
        )
        sig = custom_signal(df)
        result = sig(df)
        # SPY 2018-01-02 → True, SPY 2018-01-03 → False
        # QQQ 2018-01-02 → False, QQQ 2018-01-03 → True
        assert result.tolist() == [True, False, False, True]

    def test_nan_in_flag_col_treated_as_false(self):
        """NaN values in flag column should be treated as False, not True."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY", "SPY"],
                "quote_date": pd.to_datetime(
                    ["2018-01-02", "2018-01-03", "2018-01-04"]
                ),
                "signal": [True, None, False],
            }
        )
        sig = custom_signal(df)
        result = sig(df)
        assert result.tolist() == [True, False, False]

    def test_missing_flag_col_raises(self):
        """Missing flag column should raise ValueError with clear message."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"],
                "quote_date": pd.to_datetime(["2018-01-02"]),
            }
        )
        with pytest.raises(ValueError, match="missing required columns"):
            custom_signal(df)

    def test_missing_required_columns_raises(self):
        """Missing underlying_symbol or quote_date should raise ValueError."""
        df = pd.DataFrame(
            {"signal": [True], "quote_date": pd.to_datetime(["2018-01-02"])}
        )
        with pytest.raises(ValueError, match="missing required columns"):
            custom_signal(df)

        df2 = pd.DataFrame({"signal": [True], "underlying_symbol": ["SPY"]})
        with pytest.raises(ValueError, match="missing required columns"):
            custom_signal(df2)

    def test_exported_from_top_level(self):
        """custom_signal should be importable from the top-level optopsy package."""
        import optopsy as op

        assert hasattr(op, "custom_signal")
        assert callable(op.custom_signal)
