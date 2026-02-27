"""Integration tests for multi-tool data flow through execute_tool().

Verifies that ToolResult state (dataset, signals, datasets, results) threads
correctly between sequential tool calls after Pydantic validation.
"""

import datetime
from pathlib import Path

import pandas as pd
import pytest

pyarrow = pytest.importorskip("pyarrow")  # noqa: F841
pydantic = pytest.importorskip("pydantic")  # noqa: F841

from optopsy.ui.tools._executor import execute_tool  # noqa: E402
from optopsy.ui.tools._helpers import ToolResult  # noqa: E402
from optopsy.ui.tools._models import (  # noqa: E402
    SimulationResultEntry,
    StrategyResultSummary,
)

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
        "delta",
    ]
    d = [
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 212.5, 7.35, 7.45, 0.55],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 215.0, 6.00, 6.05, 0.30],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80, -0.30],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 215.0, 7.10, 7.20, -0.55],
        ["SPX", 220, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55, 0.65],
        ["SPX", 220, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05, 0.30],
        ["SPX", 220, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.0, -0.05],
        ["SPX", 220, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.0, -0.05],
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
# TestLoadCsvData — e2e from CSV file on disk through execute_tool
# ---------------------------------------------------------------------------

TEST_DATA_DIR = str(Path(__file__).parent / "test_data")


class TestLoadCsvData:
    """Verify load_csv_data loads CSVs with correct column mapping."""

    def test_load_8col_csv_with_defaults(self):
        """8-column CSV (no underlying_price) loads with default indices."""
        csv_path = f"{TEST_DATA_DIR}/data_no_underlying_price.csv"
        r = execute_tool("load_csv_data", {"file_path": csv_path}, None)

        assert isinstance(r, ToolResult)
        assert r.dataset is not None
        df = r.dataset
        assert "underlying_symbol" in df.columns
        assert "option_type" in df.columns
        assert "strike" in df.columns
        assert "bid" in df.columns
        assert "ask" in df.columns
        assert "delta" in df.columns
        assert "underlying_price" not in df.columns
        assert len(df) > 0

    def test_load_9col_csv_with_explicit_mapping(self):
        """9-column CSV (with underlying_price) loads when indices are explicit."""
        csv_path = f"{TEST_DATA_DIR}/data.csv"
        r = execute_tool(
            "load_csv_data",
            {
                "file_path": csv_path,
                "underlying_symbol": 0,
                "underlying_price": 1,
                "option_type": 2,
                "expiration": 3,
                "quote_date": 4,
                "strike": 5,
                "bid": 6,
                "ask": 7,
                "delta": 8,
            },
            None,
        )

        assert isinstance(r, ToolResult)
        assert r.dataset is not None
        df = r.dataset
        assert "underlying_symbol" in df.columns
        assert "underlying_price" in df.columns
        assert "option_type" in df.columns
        assert "delta" in df.columns
        assert len(df) > 0
        # Verify underlying_price is numeric (not a string like "call")
        assert pd.api.types.is_numeric_dtype(df["underlying_price"])

    def test_load_csv_sets_active_dataset_and_datasets_dict(self):
        """load_csv_data populates both active dataset and named datasets."""
        csv_path = f"{TEST_DATA_DIR}/data_no_underlying_price.csv"
        r = execute_tool("load_csv_data", {"file_path": csv_path}, None)

        assert r.dataset is not None
        assert r.datasets is not None
        assert "data_no_underlying_price.csv" in r.datasets
        assert r.datasets["data_no_underlying_price.csv"] is r.dataset

    def test_load_csv_wrong_mapping_returns_error(self):
        """Incorrect column index returns an error, not corrupted data."""
        csv_path = f"{TEST_DATA_DIR}/data_no_underlying_price.csv"
        # delta=99 is out of range for an 8-column CSV
        r = execute_tool(
            "load_csv_data",
            {"file_path": csv_path, "delta": 99},
            None,
        )
        assert "Failed to load CSV" in r.llm_summary

    def test_load_csv_missing_file(self, tmp_path):
        """Non-existent file returns an error."""
        r = execute_tool(
            "load_csv_data",
            {"file_path": str(tmp_path / "nonexistent.csv")},
            None,
        )
        assert "Failed to load CSV" in r.llm_summary

    def test_load_csv_rejects_unknown_label(self):
        """file_path label not in uploaded_files is rejected."""
        r = execute_tool(
            "load_csv_data",
            {"file_path": "unknown.csv"},
            None,
            uploaded_files={"other.csv": "/tmp/other.csv"},
        )
        assert "Access denied" in r.llm_summary

    def test_load_csv_rejects_when_no_uploads(self):
        """Empty uploaded_files dict denies all requests."""
        r = execute_tool(
            "load_csv_data",
            {"file_path": "data.csv"},
            None,
            uploaded_files={},
        )
        assert "Access denied" in r.llm_summary

    def test_load_csv_allows_uploaded_label(self):
        """file_path matching an uploaded label resolves to the real path."""
        csv_path = f"{TEST_DATA_DIR}/data_no_underlying_price.csv"
        r = execute_tool(
            "load_csv_data",
            {"file_path": "data_no_underlying_price.csv"},
            None,
            uploaded_files={"data_no_underlying_price.csv": csv_path},
        )
        assert r.dataset is not None
        assert "Access denied" not in r.llm_summary

    def test_load_then_preview(self):
        """Full flow: load_csv_data → preview_data on the loaded dataset."""
        csv_path = f"{TEST_DATA_DIR}/data_no_underlying_price.csv"
        r1 = execute_tool("load_csv_data", {"file_path": csv_path}, None)
        assert r1.dataset is not None

        r2 = execute_tool(
            "preview_data",
            {"rows": 3},
            r1.dataset,
            datasets=r1.datasets,
        )
        assert isinstance(r2, ToolResult)
        assert "rows" in r2.llm_summary.lower() or "row" in r2.llm_summary.lower()


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
            "long_calls:dte=90,exit=0,slip=mid": {
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


# ---------------------------------------------------------------------------
# TestCompareResultsEndToEnd
# ---------------------------------------------------------------------------


class TestCompareResultsEndToEnd:
    """End-to-end: run_strategy output feeds directly into compare_results.

    Unlike test_tools_compare.py which uses hand-crafted fixture dicts, these
    tests verify the full chain: run_strategy produces ToolResult.results dicts
    that compare_results consumes without format mismatches.
    """

    def test_two_strategies_then_compare(self, basic_dataset):
        """run_strategy x2 → compare_results produces a valid comparison."""
        r1 = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        assert r1.results and len(r1.results) == 1

        r2 = execute_tool(
            "run_strategy",
            {"strategy_name": "short_puts"},
            basic_dataset,
            results=r1.results,
        )
        assert r2.results and len(r2.results) == 2

        # Now compare — using the actual results dict produced by run_strategy
        r3 = execute_tool(
            "compare_results",
            {},
            r2.dataset,
            signals=r2.signals,
            datasets=r2.datasets,
            results=r2.results,
        )
        assert "2 results" in r3.llm_summary
        assert "long_calls" in r3.user_display
        assert "short_puts" in r3.user_display
        # Results should carry forward unchanged
        assert r3.results is r2.results

    def test_compare_with_sort_on_real_results(self, basic_dataset):
        """compare_results sort_by works on actual run_strategy output."""
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
        r3 = execute_tool(
            "compare_results",
            {"sort_by": "win_rate"},
            r2.dataset,
            results=r2.results,
        )
        assert "sorted by win_rate" in r3.llm_summary

    def test_compare_specific_keys_from_real_results(self, basic_dataset):
        """compare_results with result_keys selecting actual run_strategy keys."""
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
        r3 = execute_tool(
            "run_strategy",
            {"strategy_name": "long_puts"},
            basic_dataset,
            results=r2.results,
        )
        assert len(r3.results) == 3

        # Compare only the first two using their actual keys
        keys = list(r3.results.keys())[:2]
        r4 = execute_tool(
            "compare_results",
            {"result_keys": keys},
            r3.dataset,
            results=r3.results,
        )
        assert "2 results" in r4.llm_summary

    def test_result_summaries_validate_as_strategy_result_summary(self, basic_dataset):
        """Every result dict produced by run_strategy validates as StrategyResultSummary."""
        r = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        assert r.results
        for key, summary in r.results.items():
            # Must round-trip through the Pydantic model without error
            validated = StrategyResultSummary(**summary)
            assert validated.strategy == "long_calls"
            assert validated.count >= 0

    def test_scan_then_compare(self, basic_dataset):
        """scan_strategies → compare_results end-to-end."""
        r1 = execute_tool(
            "scan_strategies",
            {"strategy_names": ["long_calls", "short_puts"]},
            basic_dataset,
        )
        assert r1.results and len(r1.results) >= 2

        r2 = execute_tool(
            "compare_results",
            {},
            r1.dataset,
            results=r1.results,
        )
        assert "results" in r2.llm_summary
        # Both strategies should appear
        assert "long_calls" in r2.user_display
        assert "short_puts" in r2.user_display


# ---------------------------------------------------------------------------
# TestIVSurfaceEndToEnd
# ---------------------------------------------------------------------------


@pytest.fixture
def iv_option_chain():
    """Option chain with implied_volatility for IV surface integration tests.

    Two quote dates, two expirations, calls and puts at three strikes.
    Suitable for threading through preview_data → plot_vol_surface / iv_term_structure.
    """
    qd1 = datetime.datetime(2024, 1, 2)
    qd2 = datetime.datetime(2024, 1, 3)
    exp1 = datetime.datetime(2024, 2, 16)
    exp2 = datetime.datetime(2024, 3, 15)
    rows = []
    for qd, price in [(qd1, 100.0), (qd2, 101.0)]:
        for exp in [exp1, exp2]:
            for strike in [95.0, 100.0, 105.0]:
                for ot in ["call", "put"]:
                    iv = 0.20 + abs(strike - price) * 0.005
                    bid = (
                        max(price - strike, 0) + 1.0
                        if ot == "call"
                        else max(strike - price, 0) + 1.0
                    )
                    rows.append(
                        [
                            "SPX",
                            price,
                            ot,
                            exp,
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


class TestIVSurfaceEndToEnd:
    """End-to-end: data-loading tool output feeds into IV surface tools.

    Unlike test_tools_iv_surface.py which uses hand-built DataFrames passed
    directly, these tests thread a dataset through preview_data first (as a
    user session would), then pass the ToolResult's dataset into the IV tools.
    """

    def test_preview_then_vol_surface(self, iv_option_chain):
        """preview_data → plot_vol_surface using threaded dataset."""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        # Simulate loading data: preview_data receives the dataset
        r1 = execute_tool(
            "preview_data",
            {"rows": 5},
            iv_option_chain,
            datasets={"SPX": iv_option_chain},
        )
        assert r1.dataset is iv_option_chain

        # Feed r1's state into plot_vol_surface
        r2 = execute_tool(
            "plot_vol_surface",
            {"quote_date": "2024-01-02"},
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        assert r2.chart_figure is not None
        assert "Volatility surface" in r2.llm_summary
        assert "strikes" in r2.llm_summary
        assert "expirations" in r2.llm_summary

    def test_preview_then_iv_term_structure(self, iv_option_chain):
        """preview_data → iv_term_structure using threaded dataset."""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        r1 = execute_tool(
            "preview_data",
            {"rows": 5},
            iv_option_chain,
            datasets={"SPX": iv_option_chain},
        )

        r2 = execute_tool(
            "iv_term_structure",
            {"quote_date": "2024-01-02"},
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        assert r2.chart_figure is not None
        assert "IV term structure" in r2.llm_summary
        assert "ATM IV range" in r2.llm_summary

    def test_describe_then_vol_surface(self, iv_option_chain):
        """describe_data → plot_vol_surface using threaded dataset."""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        r1 = execute_tool(
            "describe_data",
            {},
            iv_option_chain,
            datasets={"SPX": iv_option_chain},
        )
        # Verify dataset threads through describe_data
        assert r1.dataset is iv_option_chain

        r2 = execute_tool(
            "plot_vol_surface",
            {},
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        # With no quote_date arg, should default to latest (2024-01-03)
        assert r2.chart_figure is not None
        assert "2024-01-03" in r2.llm_summary

    def test_named_dataset_flows_to_iv_tools(self, iv_option_chain):
        """Named dataset from datasets dict flows into IV surface tools."""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        named = {"SPX_IV": iv_option_chain}
        r1 = execute_tool(
            "preview_data",
            {"dataset_name": "SPX_IV", "rows": 3},
            iv_option_chain,
            datasets=named,
        )
        assert r1.datasets is named

        # plot_vol_surface uses the active dataset threaded from preview
        r2 = execute_tool(
            "plot_vol_surface",
            {"quote_date": "2024-01-02", "option_type": "put"},
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        assert r2.chart_figure is not None
        assert "put" in r2.llm_summary.lower()

    def test_iv_tool_without_iv_column_after_preview(self, basic_dataset):
        """IV tools reject dataset without IV column even when threaded."""
        plotly = pytest.importorskip("plotly")  # noqa: F841
        r1 = execute_tool(
            "preview_data",
            {"rows": 3},
            basic_dataset,
        )
        r2 = execute_tool(
            "plot_vol_surface",
            {},
            r1.dataset,
            signals=r1.signals,
            datasets=r1.datasets,
            results=r1.results,
        )
        assert r2.chart_figure is None
        assert "implied_volatility" in r2.llm_summary


# ---------------------------------------------------------------------------
# TestOutputModelEnforcement
# ---------------------------------------------------------------------------


class TestOutputModelEnforcement:
    """Verify that output models are enforced at the boundary where results
    are created — not just tested in isolation."""

    def test_run_strategy_result_validates_as_pydantic_model(self, basic_dataset):
        """Each result dict from run_strategy round-trips through StrategyResultSummary."""
        r = execute_tool(
            "run_strategy",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        assert r.results
        for summary in r.results.values():
            model = StrategyResultSummary(**summary)
            dumped = model.model_dump()
            # Round-tripped dict should match the original
            for key in ("strategy", "count", "mean_return", "win_rate"):
                assert dumped[key] == summary[key], f"Mismatch on {key}"
            # std can be NaN (single observation) — use 'is' or approx
            import math

            if summary["std"] is not None and math.isnan(summary["std"]):
                assert math.isnan(dumped["std"])
            else:
                assert dumped["std"] == summary["std"]

    def test_scan_strategies_results_validate(self, basic_dataset):
        """Each result dict from scan_strategies validates as StrategyResultSummary."""
        r = execute_tool(
            "scan_strategies",
            {"strategy_names": ["long_calls", "short_puts"]},
            basic_dataset,
        )
        assert r.results
        for key, summary in r.results.items():
            # scan_strategies adds a "source" field — StrategyResultSummary
            # should still accept the core fields (extra fields are OK with
            # model_validate which strips extras, or via dict unpacking if
            # the model uses model_config allowing extras).
            core = {k: v for k, v in summary.items() if k != "source"}
            model = StrategyResultSummary(**core)
            assert model.strategy in ("long_calls", "short_puts")

    def test_simulate_result_validates_as_simulation_entry(self, basic_dataset):
        """Simulation results validate as SimulationResultEntry."""
        r = execute_tool(
            "simulate",
            {"strategy_name": "long_calls"},
            basic_dataset,
        )
        if not r.results:
            pytest.skip("Simulation produced no results with this dataset")

        sim_entries = {
            k: v for k, v in r.results.items() if v.get("type") == "simulation"
        }
        for key, entry in sim_entries.items():
            model = SimulationResultEntry(**entry)
            assert model.type == "simulation"
            assert model.strategy == "long_calls"
            assert isinstance(model.summary, dict)
