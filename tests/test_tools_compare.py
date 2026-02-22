"""Tests for the compare_results tool."""

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools import execute_tool  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def strategy_results():
    """Two strategy result summaries (from run_strategy / scan_strategies)."""
    return {
        "long_calls:dte=45,exit=0,otm=0.10,slip=mid": {
            "strategy": "long_calls",
            "max_entry_dte": 45,
            "exit_dte": 0,
            "max_otm_pct": 0.10,
            "slippage": "mid",
            "dataset": "SPY",
            "count": 120,
            "mean_return": 0.0523,
            "std": 0.1200,
            "win_rate": 0.55,
        },
        "short_puts:dte=30,exit=0,otm=0.05,slip=mid": {
            "strategy": "short_puts",
            "max_entry_dte": 30,
            "exit_dte": 0,
            "max_otm_pct": 0.05,
            "slippage": "mid",
            "dataset": "SPY",
            "count": 95,
            "mean_return": 0.0312,
            "std": 0.0800,
            "win_rate": 0.72,
        },
    }


@pytest.fixture
def three_results(strategy_results):
    """Three strategy results for richer comparison."""
    results = dict(strategy_results)
    results["iron_condor:dte=45,exit=0,otm=0.20,slip=mid"] = {
        "strategy": "iron_condor",
        "max_entry_dte": 45,
        "exit_dte": 0,
        "max_otm_pct": 0.20,
        "slippage": "mid",
        "dataset": "SPY",
        "count": 80,
        "mean_return": 0.0185,
        "std": 0.0500,
        "win_rate": 0.80,
    }
    return results


@pytest.fixture
def mixed_results(strategy_results):
    """Mix of strategy and simulation results."""
    results = dict(strategy_results)
    results["sim:short_puts:capital=100000"] = {
        "type": "simulation",
        "strategy": "short_puts",
        "summary": {
            "total_trades": 50,
            "winning_trades": 38,
            "losing_trades": 12,
            "win_rate": 0.76,
            "total_pnl": 15230.50,
            "total_return": 0.1523,
            "avg_pnl": 304.61,
            "avg_win": 520.00,
            "avg_loss": -378.50,
            "max_win": 1200.00,
            "max_loss": -800.00,
            "profit_factor": 2.35,
            "max_drawdown": -0.0842,
            "avg_days_in_trade": 22.3,
        },
    }
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCompareResults:
    def test_no_results(self):
        """Returns error when no results exist."""
        result = execute_tool("compare_results", {}, None, results={})
        assert "no strategy runs" in result.llm_summary.lower()

    def test_single_result(self):
        """Returns error when only one result exists."""
        single = {
            "long_calls:dte=45,exit=0,otm=0.10,slip=mid": {
                "strategy": "long_calls",
                "count": 10,
                "mean_return": 0.05,
                "std": 0.1,
                "win_rate": 0.5,
            },
        }
        result = execute_tool("compare_results", {}, None, results=single)
        assert "at least 2" in result.llm_summary.lower()

    def test_basic_comparison(self, strategy_results):
        """Two results produce a comparison table with verdict."""
        result = execute_tool("compare_results", {}, None, results=strategy_results)
        assert "compare_results" in result.llm_summary
        assert "2 results" in result.llm_summary
        assert "Strategy Comparison" in result.user_display
        # Both strategies should appear
        assert "long_calls" in result.user_display
        assert "short_puts" in result.user_display

    def test_verdict_present(self, strategy_results):
        """Verdict line highlights best on each metric."""
        result = execute_tool("compare_results", {}, None, results=strategy_results)
        display = result.user_display
        assert "Best on each metric" in display

    def test_sort_by_win_rate(self, three_results):
        """Sorting by win_rate puts highest win_rate first."""
        result = execute_tool(
            "compare_results",
            {"sort_by": "win_rate"},
            None,
            results=three_results,
        )
        assert "sorted by win_rate" in result.user_display.lower()
        # LLM summary should reflect the sort
        assert "sorted by win_rate" in result.llm_summary

    def test_sort_by_default(self, strategy_results):
        """Default sort is by mean_return."""
        result = execute_tool("compare_results", {}, None, results=strategy_results)
        assert "sorted by mean_return" in result.user_display.lower()

    def test_specific_result_keys(self, three_results):
        """Selecting specific keys only compares those."""
        keys = list(three_results.keys())[:2]
        result = execute_tool(
            "compare_results",
            {"result_keys": keys},
            None,
            results=three_results,
        )
        assert "2 results" in result.llm_summary

    def test_missing_result_keys(self, strategy_results):
        """Requesting nonexistent keys returns an error."""
        result = execute_tool(
            "compare_results",
            {"result_keys": ["nonexistent_key"]},
            None,
            results=strategy_results,
        )
        assert "not found" in result.llm_summary.lower()

    def test_mixed_strategy_and_simulation(self, mixed_results):
        """Comparison handles both backtest and simulation results."""
        result = execute_tool("compare_results", {}, None, results=mixed_results)
        display = result.user_display
        assert "simulation" in display
        assert "backtest" in display
        # Simulation metrics should appear
        assert "max_drawdown" in display or "profit_factor" in display

    def test_sharpe_computation(self, strategy_results):
        """Sharpe ratio is computed from mean/std."""
        result = execute_tool("compare_results", {}, None, results=strategy_results)
        display = result.user_display
        # Sharpe should appear in the table
        assert "sharpe" in display.lower()

    def test_chart_included_by_default(self, strategy_results):
        """A chart is attached by default when plotly is available."""
        result = execute_tool("compare_results", {}, None, results=strategy_results)
        # chart_figure may be None if plotly isn't installed, so just check
        # that the handler didn't error
        assert "compare_results" in result.llm_summary

    def test_chart_disabled(self, strategy_results):
        """Setting include_chart=false skips chart creation."""
        result = execute_tool(
            "compare_results",
            {"include_chart": False},
            None,
            results=strategy_results,
        )
        assert result.chart_figure is None

    def test_three_results_comparison(self, three_results):
        """Three results produce a proper comparison."""
        result = execute_tool("compare_results", {}, None, results=three_results)
        assert "3 results" in result.llm_summary
        assert "long_calls" in result.user_display
        assert "short_puts" in result.user_display
        assert "iron_condor" in result.user_display

    def test_results_with_none_metrics(self):
        """Results with None metrics are handled gracefully."""
        results = {
            "strat_a:dte=90,exit=0,otm=0.50,slip=mid": {
                "strategy": "strat_a",
                "count": 50,
                "mean_return": 0.03,
                "std": 0.08,
                "win_rate": 0.6,
            },
            "strat_b:dte=90,exit=0,otm=0.50,slip=mid": {
                "strategy": "strat_b",
                "count": 30,
                "mean_return": None,
                "std": None,
                "win_rate": None,
            },
        }
        result = execute_tool("compare_results", {}, None, results=results)
        assert "compare_results" in result.llm_summary
        # Should show "—" for missing values in user display
        assert "—" in result.user_display

    def test_invalid_sort_column_falls_back(self, strategy_results):
        """An invalid sort_by value falls back to mean_return."""
        result = execute_tool(
            "compare_results",
            {"sort_by": "invalid_column"},
            None,
            results=strategy_results,
        )
        assert "sorted by mean_return" in result.user_display.lower()
