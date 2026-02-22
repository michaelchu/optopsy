"""Tests for entry_signal_days parameter in the run_strategy tool executor."""

from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools import execute_tool


class TestEntrySignalDaysExecutor:
    def test_signal_days_wraps_with_sustained(self, option_data_entry_exit):
        """entry_signal_days > 1 should wrap the signal with sustained()."""
        # day_of_week Thursday fires on Thu only (1 day); requiring 2 consecutive
        # days means it can never fire (Thu is isolated), so result is empty.
        result = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "entry_signal": "day_of_week",
                "entry_signal_params": {"days": [3]},
                "entry_signal_days": 2,
                "raw": True,
            },
            option_data_entry_exit,
        )
        # Sustained Thursday (2 consecutive days) can never fire, so we get
        # either "no results" (strategy returned empty) or the overlap warning
        # (signal produced 0 dates intersecting the options data). Both mean
        # "no valid entry dates".
        summary = result.llm_summary.lower()
        assert "no results" in summary or "no dates" in summary or "overlap" in summary

    def test_signal_days_1_same_as_omitted(self, option_data_entry_exit):
        """entry_signal_days=1 should behave identically to no days param."""
        result_no_days = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "entry_signal": "day_of_week",
                "entry_signal_params": {"days": [3]},
                "raw": True,
            },
            option_data_entry_exit,
        )
        result_days_1 = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "entry_signal": "day_of_week",
                "entry_signal_params": {"days": [3]},
                "entry_signal_days": 1,
                "raw": True,
            },
            option_data_entry_exit,
        )
        assert result_no_days.llm_summary == result_days_1.llm_summary

    def test_signal_days_omitted_no_wrapping(self, option_data_entry_exit):
        """Without entry_signal_days, signal should not be wrapped."""
        result = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "entry_signal": "day_of_week",
                "entry_signal_params": {"days": [3]},
                "raw": True,
            },
            option_data_entry_exit,
        )
        # Thursday entry exists, so we should get results
        assert "no results" not in result.llm_summary.lower()

    def test_signal_days_without_signal_ignored(self, option_data_entry_exit):
        """entry_signal_days without entry_signal should be harmlessly ignored."""
        result = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "entry_signal_days": 5,
                "raw": True,
            },
            option_data_entry_exit,
        )
        # Should run normally without error
        assert "error" not in result.llm_summary.lower()

    def test_signal_days_with_different_signals(self, option_data_entry_exit):
        """entry_signal_days should work with any signal from the registry."""
        # Use sma_above_20 — with only 3 dates there's no 20-bar SMA,
        # so the signal is all-False regardless. Adding days shouldn't crash.
        # Mock yfinance fetch since "SPX" isn't a downloadable ticker.
        fake_stock = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 3,
                "quote_date": pd.to_datetime(
                    ["2018-01-03", "2018-01-04", "2018-02-03"]
                ),
                "open": [213.0, 214.0, 219.0],
                "high": [214.5, 215.0, 221.0],
                "low": [213.0, 213.5, 219.0],
                "close": [213.93, 214.50, 220.0],
                "volume": [1000, 1000, 1000],
            }
        )
        with patch(
            "optopsy.ui.tools._executor._fetch_stock_data_for_signals",
            return_value=fake_stock,
        ):
            result = execute_tool(
                "run_strategy",
                {
                    "strategy_name": "long_calls",
                    "max_entry_dte": 90,
                    "exit_dte": 0,
                    "entry_signal": "sma_above",
                    "entry_signal_params": {"period": 20},
                    "entry_signal_days": 3,
                    "raw": True,
                },
                option_data_entry_exit,
            )
        # Should not error out — either empty results or valid results
        assert "error" not in result.llm_summary.lower()

    def test_unknown_signal_still_rejected(self, option_data_entry_exit):
        """Unknown entry_signal should still return an error even with days."""
        result = execute_tool(
            "run_strategy",
            {
                "strategy_name": "long_calls",
                "max_entry_dte": 90,
                "exit_dte": 0,
                "entry_signal": "nonexistent_signal",
                "entry_signal_days": 5,
                "raw": True,
            },
            option_data_entry_exit,
        )
        summary = result.llm_summary.lower()
        assert "unknown" in summary or "invalid" in summary
