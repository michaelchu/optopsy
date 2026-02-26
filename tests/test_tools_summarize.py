"""Tests for the summarize_session tool handler."""

import math

import pandas as pd
import pytest


@pytest.fixture()
def execute():
    from optopsy.ui.tools._executor import execute_tool

    def _run(datasets=None, results=None, signals=None, dataset=None):
        return execute_tool(
            "summarize_session",
            {},
            dataset,
            signals=signals or {},
            datasets=datasets or {},
            results=results or {},
        )

    return _run


# ---------------------------------------------------------------------------
# 1. Empty session
# ---------------------------------------------------------------------------


class TestEmptySession:
    def test_llm_summary_contains_all_sections(self, execute):
        result = execute()
        assert "Datasets loaded: none" in result.llm_summary
        assert "Strategy backtests: none" in result.llm_summary
        assert "Simulations: none" in result.llm_summary
        assert "Signals built: none" in result.llm_summary

    def test_user_display_contains_all_sections(self, execute):
        result = execute()
        assert "## Session Summary" in result.user_display
        assert "No datasets loaded" in result.user_display
        assert "No strategy backtests run" in result.user_display
        assert "No simulations run" in result.user_display
        assert "No signals built" in result.user_display


# ---------------------------------------------------------------------------
# 2. Only datasets
# ---------------------------------------------------------------------------


class TestDatasetsOnly:
    def _make_ds(self, n=10):
        return pd.DataFrame(
            {
                "quote_date": pd.date_range("2023-01-03", periods=n),
                "strike": range(100, 100 + n),
            }
        )

    def test_single_dataset_summary(self, execute):
        ds = self._make_ds()
        result = execute(datasets={"SPY": ds})
        assert "SPY" in result.llm_summary
        assert "10 rows" in result.llm_summary
        assert "2023-01-03" in result.llm_summary

    def test_date_range_in_display(self, execute):
        ds = self._make_ds(5)
        result = execute(datasets={"AAPL": ds})
        assert "2023-01-03" in result.user_display
        assert "2023-01-07" in result.user_display  # 5th period: Jan 3+4 days

    def test_multiple_datasets(self, execute):
        ds1 = self._make_ds(3)
        ds2 = self._make_ds(7)
        result = execute(datasets={"SPY": ds1, "QQQ": ds2})
        assert "SPY" in result.llm_summary
        assert "QQQ" in result.llm_summary

    def test_empty_dataset_does_not_raise(self, execute):
        empty_df = pd.DataFrame({"quote_date": pd.Series([], dtype="datetime64[ns]")})
        result = execute(datasets={"EMPTY": empty_df})
        assert "EMPTY" in result.llm_summary
        assert "unknown date range" in result.llm_summary

    def test_dataset_without_date_column(self, execute):
        df = pd.DataFrame({"strike": [100, 105, 110]})
        result = execute(datasets={"NODATE": df})
        assert "NODATE" in result.llm_summary
        assert "unknown date range" in result.llm_summary

    def test_dataset_with_nat_dates_does_not_raise(self, execute):
        df = pd.DataFrame({"quote_date": [pd.NaT, pd.NaT]})
        result = execute(datasets={"NATDF": df})
        assert "NATDF" in result.llm_summary
        assert "unknown date range" in result.llm_summary


# ---------------------------------------------------------------------------
# 3. Only backtest results
# ---------------------------------------------------------------------------


def _make_backtest_entry(**overrides):
    base = {
        "strategy": "long_calls",
        "max_entry_dte": 90,
        "exit_dte": 0,
        "slippage": "mid",
        "count": 50,
        "mean_return": 0.0312,
        "std": 0.15,
        "win_rate": 0.55,
        "profit_factor": 1.2,
    }
    base.update(overrides)
    return base


class TestBacktestResultsOnly:
    def test_single_backtest_appears_in_summary(self, execute):
        results = {"long_calls_90": _make_backtest_entry()}
        result = execute(results=results)
        assert "long_calls" in result.llm_summary
        assert "0.0312" in result.llm_summary

    def test_win_rate_formatted_as_percent(self, execute):
        results = {"lc": _make_backtest_entry(win_rate=0.55)}
        result = execute(results=results)
        assert "55.00%" in result.user_display

    def test_profit_factor_formatted(self, execute):
        results = {"lc": _make_backtest_entry(profit_factor=1.75)}
        result = execute(results=results)
        assert "1.75" in result.user_display

    def test_profit_factor_infinity_handled(self, execute):
        results = {"lc": _make_backtest_entry(profit_factor=float("inf"))}
        result = execute(results=results)
        assert "no losses" in result.user_display

    def test_profit_factor_nan_handled(self, execute):
        results = {"lc": _make_backtest_entry(profit_factor=float("nan"))}
        result = execute(results=results)
        assert "N/A" in result.user_display

    def test_none_metrics_display_dash(self, execute):
        results = {"lc": _make_backtest_entry(mean_return=None, win_rate=None, profit_factor=None)}
        result = execute(results=results)
        assert "—" in result.user_display

    def test_results_sorted_by_mean_return_descending(self, execute):
        results = {
            "strat_low": _make_backtest_entry(strategy="long_puts", mean_return=0.01),
            "strat_high": _make_backtest_entry(strategy="long_calls", mean_return=0.05),
            "strat_mid": _make_backtest_entry(strategy="short_puts", mean_return=0.03),
        }
        result = execute(results=results)
        display = result.user_display
        # long_calls (0.05) should appear before short_puts (0.03) before long_puts (0.01)
        pos_high = display.index("long_calls")
        pos_mid = display.index("short_puts")
        pos_low = display.index("long_puts")
        assert pos_high < pos_mid < pos_low

    def test_backtest_results_not_mixed_with_simulations(self, execute):
        results = {
            "bt": _make_backtest_entry(),
            "sim": {
                "type": "simulation",
                "strategy": "long_calls",
                "summary": {"total_trades": 20, "total_return": 0.1, "win_rate": 0.6, "profit_factor": 1.5},
            },
        }
        result = execute(results=results)
        assert "Strategy Backtests (1)" in result.user_display
        assert "Simulations (1)" in result.user_display


# ---------------------------------------------------------------------------
# 4. Only simulation results
# ---------------------------------------------------------------------------


def _make_sim_entry(**overrides):
    summary = {
        "total_trades": 30,
        "total_return": 0.15,
        "win_rate": 0.60,
        "profit_factor": 2.0,
        **overrides,
    }
    return {"type": "simulation", "strategy": "long_calls", "summary": summary}


class TestSimulationResultsOnly:
    def test_simulation_appears_in_summary(self, execute):
        results = {"sim:long_calls": _make_sim_entry()}
        result = execute(results=results)
        assert "Simulations (1)" in result.user_display

    def test_total_return_formatted_as_percent(self, execute):
        results = {"sim:lc": _make_sim_entry(total_return=0.1523)}
        result = execute(results=results)
        assert "15.23%" in result.user_display

    def test_win_rate_formatted_as_percent(self, execute):
        results = {"sim:lc": _make_sim_entry(win_rate=0.76)}
        result = execute(results=results)
        assert "76.0%" in result.user_display

    def test_profit_factor_infinity_handled(self, execute):
        results = {"sim:lc": _make_sim_entry(profit_factor=float("inf"))}
        result = execute(results=results)
        assert "no losses" in result.user_display

    def test_profit_factor_nan_handled(self, execute):
        results = {"sim:lc": _make_sim_entry(profit_factor=float("nan"))}
        result = execute(results=results)
        assert "N/A" in result.user_display

    def test_trades_formatted_as_integer(self, execute):
        results = {"sim:lc": _make_sim_entry(total_trades=1234)}
        result = execute(results=results)
        assert "1,234" in result.user_display

    def test_none_metrics_display_question_mark(self, execute):
        results = {"sim:lc": _make_sim_entry(total_return=None, win_rate=None, profit_factor=None)}
        result = execute(results=results)
        # None metrics fall back to "?"
        assert "?" in result.user_display

    def test_no_simulations_message(self, execute):
        result = execute()
        assert "No simulations run" in result.user_display


# ---------------------------------------------------------------------------
# 5. Only signals
# ---------------------------------------------------------------------------


class TestSignalsOnly:
    def test_signal_slot_appears(self, execute):
        sig_df = pd.DataFrame({"quote_date": pd.date_range("2023-01-01", periods=10)})
        result = execute(signals={"rsi_slot": sig_df})
        assert "rsi_slot" in result.llm_summary
        assert "10 valid dates" in result.llm_summary

    def test_multiple_signals(self, execute):
        sigs = {
            "rsi_slot": pd.DataFrame({"quote_date": pd.date_range("2023-01-01", periods=5)}),
            "macd_slot": pd.DataFrame({"quote_date": pd.date_range("2023-06-01", periods=3)}),
        }
        result = execute(signals=sigs)
        assert "rsi_slot" in result.user_display
        assert "macd_slot" in result.user_display

    def test_none_signal_df_counts_zero(self, execute):
        result = execute(signals={"empty_slot": None})
        assert "0 valid dates" in result.llm_summary

    def test_no_signals_message(self, execute):
        result = execute()
        assert "No signals built" in result.user_display


# ---------------------------------------------------------------------------
# 6. Mixed session (all types present)
# ---------------------------------------------------------------------------


class TestMixedSession:
    def test_all_sections_present(self, execute):
        ds = pd.DataFrame({"quote_date": pd.date_range("2023-01-01", periods=5)})
        results = {
            "bt": _make_backtest_entry(),
            "sim": _make_sim_entry(),
        }
        sigs = {"rsi": pd.DataFrame({"quote_date": pd.date_range("2023-01-01", periods=3)})}
        result = execute(datasets={"SPY": ds}, results=results, signals=sigs)

        assert "Datasets Loaded" in result.user_display
        assert "Strategy Backtests" in result.user_display
        assert "Simulations" in result.user_display
        assert "Signals Built" in result.user_display

    def test_llm_summary_is_concise(self, execute):
        # LLM summary should be concise enough to fit in a message window
        # (no full tables — those go in user_display only).
        _MAX_LLM_SUMMARY_LENGTH = 2000
        ds = pd.DataFrame({"quote_date": pd.date_range("2023-01-01", periods=5)})
        results = {
            "bt": _make_backtest_entry(),
            "sim": _make_sim_entry(),
        }
        sigs = {"rsi": pd.DataFrame({"quote_date": pd.date_range("2023-01-01", periods=3)})}
        result = execute(datasets={"SPY": ds}, results=results, signals=sigs)
        assert len(result.llm_summary) < _MAX_LLM_SUMMARY_LENGTH
