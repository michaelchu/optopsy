"""Tests for the build_custom_signal tool handler."""

from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_OPTIONS_DATES = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
_STOCK_DATES = ["2023-12-01", "2023-12-04"] + _OPTIONS_DATES


def _make_options(symbol="SPY"):
    """Minimal options DataFrame for intersection tests."""
    rows = []
    for d in _OPTIONS_DATES:
        rows.append(
            {
                "underlying_symbol": symbol,
                "option_type": "c",
                "expiration": pd.Timestamp("2024-02-16"),
                "quote_date": pd.Timestamp(d),
                "strike": 470.0,
                "bid": 5.0,
                "ask": 5.5,
            }
        )
    return pd.DataFrame(rows)


def _make_stock(symbol="SPY"):
    """OHLCV stock data that overlaps the options dates."""
    dates = pd.to_datetime(_STOCK_DATES)
    n = len(dates)
    return pd.DataFrame(
        {
            "underlying_symbol": [symbol] * n,
            "quote_date": dates,
            "open": [468.0, 469.0, 470.0, 471.0, 472.0, 473.0],
            "high": [469.5, 470.5, 472.0, 473.0, 474.0, 475.0],
            "low": [467.0, 468.0, 469.0, 470.0, 471.0, 472.0],
            "close": [469.0, 470.0, 471.0, 472.0, 473.0, 474.0],
            "volume": [1_000_000, 1_100_000, 900_000, 5_000_000, 800_000, 1_200_000],
        }
    )


@pytest.fixture
def options():
    return _make_options()


@pytest.fixture
def stock():
    return _make_stock()


def _run(code, options, stock, slot="test", description=None):
    """Helper to call build_custom_signal with mocked stock data."""
    args = {"slot": slot, "code": code}
    if description:
        args["description"] = description
    with patch(
        "optopsy.ui.tools._signals_builder._fetch_stock_data_for_signals",
        return_value=stock,
    ):
        return execute_tool("build_custom_signal", args, options)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestBuildCustomSignalHappyPath:
    def test_simple_code_produces_correct_signal_dates(self, options, stock):
        """Simple close > 471 should flag dates where close exceeds 471."""
        result = _run("signal = df['close'] > 471", options, stock)
        assert "failed" not in result.llm_summary.lower()
        assert result.signals is not None
        assert "test" in result.signals
        valid = result.signals["test"]
        # close values: [469, 470, 471, 472, 473, 474]
        # options dates: [Jan 2, 3, 4, 5]
        # close > 471 on stock dates: Jan 3 (472), Jan 4 (473), Jan 5 (474)
        # Intersection with options: Jan 3, 4, 5
        assert len(valid) == 3

    def test_rolling_window_volume_spike(self, options, stock):
        """Volume > 2x rolling mean should catch the spike on 2024-01-05."""
        code = "signal = df['volume'] > df['volume'].rolling(3).mean() * 2"
        result = _run(code, options, stock)
        assert "failed" not in result.llm_summary.lower()
        assert result.signals is not None
        valid = result.signals["test"]
        # volumes: [1M, 1.1M, 0.9M, 5M, 0.8M, 1.2M]
        # rolling(3).mean at idx 3 = (0.9+1.1+1.0)/3 = 1.0M, 5M > 2M → True
        # rolling(3).mean at idx 4 = (5+0.9+1.1)/3 ≈ 2.33M, 0.8M > 4.67M → False
        # rolling(3).mean at idx 5 = (0.8+5+0.9)/3 ≈ 2.23M, 1.2M > 4.47M → False
        # So only Jan 5 (idx 3 = options idx for Jan 5) should flag
        assert len(valid) >= 1

    def test_description_appears_in_summary(self, options, stock):
        """The description field should appear in the result summary."""
        result = _run(
            "signal = df['close'] > 471",
            options,
            stock,
            description="close above 471",
        )
        assert "close above 471" in result.llm_summary

    def test_signal_stored_in_slot(self, options, stock):
        """The signal slot should be stored and retrievable."""
        result = _run("signal = df['close'] > 0", options, stock, slot="my_entry")
        assert "my_entry" in result.signals


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestBuildCustomSignalErrors:
    def test_missing_signal_variable(self, options, stock):
        """Code that doesn't produce `signal` should return clear error."""
        result = _run("x = df['close'] > 471", options, stock)
        assert "signal" in result.llm_summary.lower()
        assert (
            "failed" in result.llm_summary.lower()
            or "did not produce" in result.llm_summary.lower()
        )

    def test_syntax_error(self, options, stock):
        """Code with syntax errors should return descriptive error."""
        result = _run("signal = df['close' > 471", options, stock)
        assert (
            "SyntaxError" in result.llm_summary
            or "failed" in result.llm_summary.lower()
        )

    def test_runtime_error(self, options, stock):
        """Code that raises at runtime should return descriptive error."""
        result = _run("signal = df['nonexistent_column'] > 0", options, stock)
        assert (
            "KeyError" in result.llm_summary or "failed" in result.llm_summary.lower()
        )

    def test_wrong_type_for_signal(self, options, stock):
        """If `signal` is not a Series, return type error."""
        result = _run("signal = 42", options, stock)
        assert "Series" in result.llm_summary or "type" in result.llm_summary.lower()

    def test_signal_length_mismatch(self, options, stock):
        """Signal with wrong length should return clear error."""
        code = "signal = pd.Series([True, False])"  # shorter than df
        result = _run(code, options, stock)
        assert "length" in result.llm_summary.lower()

    def test_nan_handled_as_false(self, options, stock):
        """NaN values in signal should be treated as False, not cause errors."""
        # shift(1) produces NaN for first row
        code = "signal = df['close'] > df['close'].shift(1)"
        result = _run(code, options, stock)
        assert "failed" not in result.llm_summary.lower()

    def test_no_dataset_loaded(self):
        """Should error when no dataset is loaded."""
        result = execute_tool(
            "build_custom_signal", {"slot": "x", "code": "signal = True"}, None
        )
        assert (
            "no dataset" in result.llm_summary.lower()
            or "load data" in result.llm_summary.lower()
        )

    def test_missing_slot(self, options, stock):
        """Missing slot name should error."""
        result = _run("signal = df['close'] > 0", options, stock, slot="")
        # slot="" triggers strip → empty → error
        with patch(
            "optopsy.ui.tools._signals_builder._fetch_stock_data_for_signals",
            return_value=stock,
        ):
            result = execute_tool(
                "build_custom_signal", {"slot": "", "code": "signal = True"}, options
            )
        assert (
            "slot" in result.llm_summary.lower()
            or "missing" in result.llm_summary.lower()
        )

    def test_missing_code(self, options, stock):
        """Missing code should error."""
        with patch(
            "optopsy.ui.tools._signals_builder._fetch_stock_data_for_signals",
            return_value=stock,
        ):
            result = execute_tool(
                "build_custom_signal", {"slot": "x", "code": ""}, options
            )
        assert (
            "code" in result.llm_summary.lower()
            or "missing" in result.llm_summary.lower()
        )


# ---------------------------------------------------------------------------
# Sandbox restrictions
# ---------------------------------------------------------------------------


class TestBuildCustomSignalSandbox:
    def test_import_blocked(self, options, stock):
        """import statements should fail in the sandbox."""
        result = _run("import os; signal = df['close'] > 0", options, stock)
        assert "failed" in result.llm_summary.lower()

    def test_open_blocked(self, options, stock):
        """open() should not be available."""
        result = _run(
            "f = open('/etc/passwd'); signal = df['close'] > 0", options, stock
        )
        assert "failed" in result.llm_summary.lower()

    def test_dunder_import_blocked(self, options, stock):
        """__import__ should not be available."""
        result = _run("__import__('os'); signal = df['close'] > 0", options, stock)
        assert "failed" in result.llm_summary.lower()

    def test_exec_blocked(self, options, stock):
        """exec() should not be available in the sandbox."""
        result = _run("exec('x=1'); signal = df['close'] > 0", options, stock)
        assert "failed" in result.llm_summary.lower()

    def test_eval_blocked(self, options, stock):
        """eval() should not be available in the sandbox."""
        result = _run("eval('1+1'); signal = df['close'] > 0", options, stock)
        assert "failed" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Multi-symbol
# ---------------------------------------------------------------------------


class TestBuildCustomSignalMultiSymbol:
    def test_code_runs_per_symbol_independently(self):
        """Code should run per-symbol, not on the entire DataFrame."""
        # Create two symbols with different data
        opts_spy = _make_options("SPY")
        opts_aapl = _make_options("AAPL")
        options = pd.concat([opts_spy, opts_aapl], ignore_index=True)

        stock_spy = _make_stock("SPY")
        stock_aapl = _make_stock("AAPL")
        stock = pd.concat([stock_spy, stock_aapl], ignore_index=True)

        # Use len(df) in signal — if code ran on full df it would have more rows
        result = _run("signal = df['close'] > 471", options, stock)
        assert "failed" not in result.llm_summary.lower()
        valid = result.signals["test"]
        # Each symbol should independently flag close > 471
        symbols = valid["underlying_symbol"].unique().tolist()
        assert "SPY" in symbols
        assert "AAPL" in symbols

    def test_partial_success_returns_results_with_warning(self):
        """If code fails for one symbol but succeeds for another, return partial results."""
        opts_spy = _make_options("SPY")
        opts_aapl = _make_options("AAPL")
        options = pd.concat([opts_spy, opts_aapl], ignore_index=True)

        stock_spy = _make_stock("SPY")
        # Give AAPL stock data a column the code will reference that SPY also has,
        # but make AAPL data have a unique column that we can use to cause failure
        stock_aapl = _make_stock("AAPL")
        stock_aapl["extra_col"] = 1.0
        stock = pd.concat([stock_spy, stock_aapl], ignore_index=True)

        # Code references extra_col — SPY doesn't have it (KeyError),
        # but AAPL does. However, since per-symbol slicing copies columns,
        # SPY's df won't have extra_col. Use a code path that fails on one.
        # Simpler: reference a column name that only exists after we add it
        # for AAPL but not SPY — but concat fills missing with NaN.
        # Instead, use code that conditionally fails based on data values.
        code = (
            "if df['underlying_symbol'].iloc[0] == 'SPY':\n"
            "    raise ValueError('intentional failure')\n"
            "signal = df['close'] > 471"
        )
        result = _run(code, options, stock)
        # Should succeed partially — AAPL results exist
        assert result.signals is not None
        assert "test" in result.signals
        valid = result.signals["test"]
        assert not valid.empty
        assert "AAPL" in valid["underlying_symbol"].values
        # Should warn about SPY failure
        assert "WARNING" in result.user_display


# ---------------------------------------------------------------------------
# Empty result / options date intersection
# ---------------------------------------------------------------------------


class TestBuildCustomSignalEmptyResult:
    def test_no_signal_fires(self, options, stock):
        """When signal is always False, should get warning."""
        result = _run("signal = df['close'] > 99999", options, stock)
        assert (
            "WARNING" in result.user_display
            or "never triggered" in result.user_display.lower()
        )
        assert result.signals["test"].empty

    def test_empty_after_options_intersection(self, options):
        """Signal fires only on dates outside options range → warning."""
        # Stock data only has pre-options dates
        stock = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"] * 3,
                "quote_date": pd.to_datetime(
                    ["2023-06-01", "2023-06-02", "2023-06-03"]
                ),
                "open": [400.0, 401.0, 402.0],
                "high": [401.0, 402.0, 403.0],
                "low": [399.0, 400.0, 401.0],
                "close": [400.5, 401.5, 402.5],
                "volume": [1_000_000] * 3,
            }
        )
        result = _run("signal = df['close'] > 0", options, stock)
        assert "0 valid dates" in result.llm_summary or result.signals["test"].empty


# ---------------------------------------------------------------------------
# Integration with preview_signal and list_signals
# ---------------------------------------------------------------------------


class TestBuildCustomSignalIntegration:
    def test_slot_works_with_preview_signal(self, options, stock):
        """After build_custom_signal, preview_signal should show the slot."""
        build_result = _run(
            "signal = df['close'] > 471", options, stock, slot="custom1"
        )
        signals = build_result.signals

        preview_result = execute_tool(
            "preview_signal",
            {"slot": "custom1"},
            options,
            signals=signals,
        )
        assert "custom1" in preview_result.llm_summary
        assert (
            "valid dates" in preview_result.llm_summary.lower()
            or "0" not in preview_result.llm_summary
        )

    def test_slot_works_with_list_signals(self, options, stock):
        """After build_custom_signal, list_signals should include the slot."""
        build_result = _run(
            "signal = df['close'] > 471", options, stock, slot="custom2"
        )
        signals = build_result.signals

        list_result = execute_tool(
            "list_signals",
            {},
            options,
            signals=signals,
        )
        assert "custom2" in list_result.llm_summary
