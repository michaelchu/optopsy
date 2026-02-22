"""Integration tests for multi-tool data flow through execute_tool().

Verifies that ToolResult state (dataset, signals, datasets, results) threads
correctly between sequential tool calls after Pydantic validation.
"""

import datetime

import pandas as pd
import pytest

pyarrow = pytest.importorskip("pyarrow")  # noqa: F841
pydantic = pytest.importorskip("pydantic")  # noqa: F841

from optopsy.ui.tools._executor import execute_tool  # noqa: E402
from optopsy.ui.tools._helpers import ToolResult  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_dataset():
    """Minimal option chain with entry + exit dates."""
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


# ---------------------------------------------------------------------------
# TestDatasetThreading
# ---------------------------------------------------------------------------


class TestDatasetThreading:
    """Verify dataset state flows between preview_data and describe_data."""

    def test_preview_then_describe(self, basic_dataset):
        """preview_data preserves dataset; describe_data works on it."""
        r1 = execute_tool("preview_data", {"rows": 3}, basic_dataset)
        assert isinstance(r1, ToolResult)
        assert r1.dataset is basic_dataset

        # Feed r1's state into describe_data
        r2 = execute_tool(
            "describe_data",
            {},
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        assert isinstance(r2, ToolResult)
        # describe_data should report on the same dataset
        assert "8 rows" in r2.llm_summary or "8 rows" in r2.user_display

    def test_named_datasets_preserved(self, basic_dataset):
        """datasets dict with multiple entries threads through unchanged."""
        ds_a = basic_dataset.copy()
        ds_b = basic_dataset.head(4).copy()
        named = {"SPX_full": ds_a, "SPX_partial": ds_b}

        r = execute_tool(
            "preview_data",
            {"dataset_name": "SPX_full", "rows": 2},
            ds_a,
            datasets=named,
        )
        assert r.datasets is named
        assert "SPX_full" in r.datasets
        assert "SPX_partial" in r.datasets


# ---------------------------------------------------------------------------
# TestResultsThreading
# ---------------------------------------------------------------------------


class TestResultsThreading:
    """Verify results dict accumulates across run_strategy calls."""

    def test_run_strategy_populates_results(self, basic_dataset):
        """run_strategy returns a results dict with the run's summary."""
        r = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        assert r.results is not None
        assert len(r.results) == 1
        key = list(r.results.keys())[0]
        assert "long_calls" in key
        summary = r.results[key]
        assert summary["strategy"] == "long_calls"
        assert "count" in summary

    def test_list_results_finds_prior_run(self, basic_dataset):
        """run_strategy → list_results finds the prior run."""
        r1 = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        r2 = execute_tool(
            "list_results",
            {},
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        assert "long_calls" in r2.llm_summary or "long_calls" in r2.user_display
        # results should carry forward
        assert r2.results is not None
        assert len(r2.results) >= 1

    def test_multiple_runs_accumulate(self, basic_dataset):
        """Running long_calls then short_puts accumulates both in results."""
        r1 = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        r2 = execute_tool(
            "run_strategy",
            {"strategy_name": "short_puts"},
            basic_dataset,
            results=r1.results,
        )
        assert r2.results is not None
        assert len(r2.results) == 2
        strategies = {v["strategy"] for v in r2.results.values()}
        assert strategies == {"long_calls", "short_puts"}


# ---------------------------------------------------------------------------
# TestSignalThreading
# ---------------------------------------------------------------------------


class TestSignalThreading:
    """Verify signal slots flow between build_signal and downstream tools."""

    def test_build_then_preview_signal(self, option_data_entry_exit):
        """build_signal creates a slot; preview_signal reads it."""
        r1 = execute_tool(
            "build_signal",
            {
                "slot": "entry_dow",
                "signals": [{"name": "day_of_week", "params": {"day": 3}}],
            },
            option_data_entry_exit,
        )
        assert r1.signals is not None
        assert "entry_dow" in r1.signals

        r2 = execute_tool(
            "preview_signal",
            {"slot": "entry_dow"},
            r1.dataset,
            signals=r1.signals,
        )
        assert "entry_dow" in r2.llm_summary or "entry_dow" in r2.user_display
        # Signals should carry forward
        assert r2.signals is not None
        assert "entry_dow" in r2.signals

    def test_build_signal_then_run_strategy_with_slot(self, option_data_entry_exit):
        """build_signal → run_strategy via entry_signal_slot filters entries."""
        # Build a Thursday-only signal (day_of_week=3, Thursday)
        r1 = execute_tool(
            "build_signal",
            {
                "slot": "thu_only",
                "signals": [{"name": "day_of_week", "params": {"day": 3}}],
            },
            option_data_entry_exit,
        )
        assert "thu_only" in r1.signals

        # Run without signal — should use both Wed and Thu entries
        r_no_signal = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls", "raw": True},
            option_data_entry_exit,
        )

        # Run with signal slot — should only use Thursday entries
        r_with_signal = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "raw": True,
                "entry_signal_slot": "thu_only",
            },
            option_data_entry_exit,
            signals=r1.signals,
        )

        # Signal-filtered run should have fewer (or equal) rows
        if r_no_signal.results and r_with_signal.results:
            no_sig_count = list(r_no_signal.results.values())[0]["count"]
            sig_count = list(r_with_signal.results.values())[0]["count"]
            assert sig_count <= no_sig_count


# ---------------------------------------------------------------------------
# TestChartDataFlow
# ---------------------------------------------------------------------------


class TestChartDataFlow:
    """Verify strategy results flow into chart creation."""

    def test_run_strategy_then_chart(self, basic_dataset):
        """run_strategy → create_chart(data_source='result') produces a figure."""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        r1 = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        assert r1.results

        result_key = list(r1.results.keys())[0]
        r2 = execute_tool(
            "create_chart",
            {
                "chart_type": "bar",
                "data_source": "result",
                "result_key": result_key,
                "x": "strategy",
                "y": "count",
            },
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        assert r2.chart_figure is not None


# ---------------------------------------------------------------------------
# TestValidationPreservesState
# ---------------------------------------------------------------------------


class TestValidationPreservesState:
    """Verify that Pydantic validation errors preserve all state."""

    def test_invalid_args_preserve_state(self, basic_dataset):
        """Invalid arguments produce an error but carry all state forward."""
        existing_signals = {
            "my_sig": pd.DataFrame(
                {
                    "underlying_symbol": ["SPX"],
                    "quote_date": [datetime.datetime(2018, 1, 4)],
                }
            )
        }
        existing_results = {
            "long_calls:dte=90,exit=0,otm=0.50,slip=mid": {
                "strategy": "long_calls",
                "count": 5,
                "mean_return": 0.02,
            }
        }

        r = execute_tool(
            "run_strategy",
            {"strategy_name": "not_a_real_strategy"},
            basic_dataset,
            signals=existing_signals,
            datasets={"default": basic_dataset},
            results=existing_results,
        )
        # Should be an error
        assert "invalid" in r.llm_summary.lower() or "unknown" in r.llm_summary.lower()
        # All state must survive
        assert r.dataset is basic_dataset
        assert r.signals is existing_signals
        assert r.results is existing_results

    def test_pydantic_validates_signal_names(self, basic_dataset):
        """Valid entry_signal passes; bogus entry_signal is rejected."""
        # Valid signal name should not cause a validation error
        r_ok = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls", "entry_signal": "day_of_week"},
            basic_dataset,
        )
        # Should not contain "Invalid arguments" — it may fail later for
        # other reasons (e.g., no matching dates) but not at validation.
        assert "Invalid arguments" not in r_ok.llm_summary

        # Bogus signal name should be rejected
        r_bad = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls", "entry_signal": "bogus_signal"},
            basic_dataset,
        )
        assert (
            "invalid" in r_bad.llm_summary.lower()
            or "unknown" in r_bad.llm_summary.lower()
        )
