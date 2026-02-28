"""Tests for optopsy/ui/tools/_simulators.py — simulate & get_simulation_trades."""

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from unittest.mock import MagicMock, patch

import pandas as pd

from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# simulate tool tests
# ---------------------------------------------------------------------------


def test_simulate_unknown_strategy():
    """Unknown strategy_name should return an error listing available strategies."""
    result = execute_tool("simulate", {"strategy_name": "bogus_strat"}, dataset=None)
    assert "Unknown strategy" in result.llm_summary
    assert "bogus_strat" in result.llm_summary


def test_simulate_no_dataset():
    """Missing dataset should return an error."""
    result = execute_tool("simulate", {"strategy_name": "long_calls"}, dataset=None)
    assert "No dataset loaded" in result.llm_summary


@patch("optopsy.ui.tools._simulators._resolve_signals_for_strategy")
def test_simulate_signal_error(mock_signals):
    """Signal resolution error should propagate."""
    mock_signals.return_value = ({}, "Signal error: bad signal")
    df = pd.DataFrame({"col": [1]})
    result = execute_tool("simulate", {"strategy_name": "long_calls"}, dataset=df)
    assert "Signal error" in result.llm_summary


@patch("optopsy.ui.tools._simulators._resolve_signals_for_strategy")
@patch("optopsy.simulator.simulate")
def test_simulate_exception(mock_sim, mock_signals):
    """Exception during simulation should return an error message."""
    mock_signals.return_value = ({}, None)
    mock_sim.side_effect = ValueError("boom")
    df = pd.DataFrame({"col": [1]})
    result = execute_tool("simulate", {"strategy_name": "long_calls"}, dataset=df)
    assert "Error running simulation" in result.llm_summary
    assert "boom" in result.llm_summary


@patch("optopsy.ui.tools._simulators._resolve_signals_for_strategy")
@patch("optopsy.simulator.simulate")
def test_simulate_zero_trades(mock_sim, mock_signals):
    """Zero trades should return an informative message."""
    mock_signals.return_value = ({}, None)
    mock_result = MagicMock()
    mock_result.summary = {"total_trades": 0}
    mock_result.trade_log = pd.DataFrame()
    mock_sim.return_value = mock_result
    df = pd.DataFrame({"col": [1]})
    result = execute_tool("simulate", {"strategy_name": "long_calls"}, dataset=df)
    assert "no trades generated" in result.llm_summary


@patch("optopsy.ui.tools._simulators.ResultStore")
@patch("optopsy.ui.tools._simulators._resolve_signals_for_strategy")
@patch("optopsy.simulator.simulate")
def test_simulate_success(mock_sim, mock_signals, mock_store_cls):
    """Successful simulation should return stats and update results."""
    mock_signals.return_value = ({}, None)
    mock_result = MagicMock()
    mock_result.summary = {
        "total_trades": 10,
        "winning_trades": 6,
        "losing_trades": 4,
        "win_rate": 0.6,
        "total_pnl": 500.0,
        "total_return": 0.05,
        "avg_pnl": 50.0,
        "avg_win": 120.0,
        "avg_loss": -55.0,
        "max_win": 300.0,
        "max_loss": -100.0,
        "profit_factor": 1.5,
        "max_drawdown": -0.10,
        "avg_days_in_trade": 30.0,
        "sharpe_ratio": 1.2,
        "sortino_ratio": 1.8,
        "var_95": -0.03,
        "cvar_95": -0.05,
        "calmar_ratio": 0.5,
    }
    mock_result.trade_log = pd.DataFrame(
        {
            "trade_id": [1, 2],
            "entry_date": ["2024-01-01", "2024-02-01"],
            "exit_date": ["2024-01-15", "2024-02-15"],
            "days_held": [14, 14],
            "entry_cost": [-100, -100],
            "exit_proceeds": [120, 80],
            "realized_pnl": [20, -20],
            "equity": [10020, 10000],
        }
    )
    mock_sim.return_value = mock_result

    # Mock the store so it doesn't hit disk
    mock_store = MagicMock()
    mock_store.has.return_value = False
    mock_store_cls.return_value = mock_store

    df = pd.DataFrame({"col": [1]})
    result = execute_tool("simulate", {"strategy_name": "long_calls"}, dataset=df)

    assert "10 trades" in result.llm_summary
    assert "win_rate=60.0%" in result.llm_summary
    assert result.results  # results dict should be updated
    # Verify no store.write since no dataset fingerprint was injected
    mock_store.write.assert_not_called()


@patch("optopsy.ui.tools._simulators.ResultStore")
@patch("optopsy.ui.tools._simulators._resolve_signals_for_strategy")
@patch("optopsy.simulator.simulate")
def test_simulate_caches_on_miss(mock_sim, mock_signals, mock_store_cls):
    """With a dataset fingerprint, simulate should write to ResultStore on cache miss."""
    mock_signals.return_value = ({}, None)
    mock_result = MagicMock()
    mock_result.summary = {
        "total_trades": 10,
        "winning_trades": 6,
        "losing_trades": 4,
        "win_rate": 0.6,
        "total_pnl": 500.0,
        "total_return": 0.05,
        "avg_pnl": 50.0,
        "avg_win": 120.0,
        "avg_loss": -55.0,
        "max_win": 300.0,
        "max_loss": -100.0,
        "profit_factor": 1.5,
        "max_drawdown": -0.10,
        "avg_days_in_trade": 30.0,
        "sharpe_ratio": 1.2,
        "sortino_ratio": 1.8,
        "var_95": -0.03,
        "cvar_95": -0.05,
        "calmar_ratio": 0.5,
    }
    mock_result.trade_log = pd.DataFrame(
        {
            "trade_id": [1, 2],
            "entry_date": ["2024-01-01", "2024-02-01"],
            "exit_date": ["2024-01-15", "2024-02-15"],
            "days_held": [14, 14],
            "entry_cost": [-100, -100],
            "exit_proceeds": [120, 80],
            "realized_pnl": [20, -20],
            "equity": [10020, 10000],
        }
    )
    mock_sim.return_value = mock_result

    mock_store = MagicMock()
    mock_store.has.return_value = False
    mock_store.make_key.return_value = "fake_cache_key"
    mock_store_cls.return_value = mock_store

    df = pd.DataFrame({"col": [1]})
    result = execute_tool(
        "simulate",
        {"strategy_name": "long_calls"},
        dataset=df,
        dataset_fingerprint="fp123",
    )

    assert "10 trades" in result.llm_summary
    mock_store.write.assert_called_once()
    # Verify the cache key is used as the session result key (SHA-256 hash strategy)
    assert "fake_cache_key" in result.results
    entry = result.results["fake_cache_key"]
    assert entry.get("_cache_key") == "fake_cache_key"
    assert entry.get("display_key") == "sim:long_calls"


# ---------------------------------------------------------------------------
# get_simulation_trades tool tests
# ---------------------------------------------------------------------------


def test_get_trades_no_simulations():
    """No prior simulations should return an error."""
    result = execute_tool("get_simulation_trades", {}, dataset=None, results={})
    assert "No simulations run yet" in result.llm_summary


def test_get_trades_invalid_key():
    """Invalid simulation key should list available keys."""
    results = {
        "sim:long_calls": {"type": "simulation", "strategy": "long_calls"},
    }
    result = execute_tool(
        "get_simulation_trades",
        {"simulation_key": "sim:bogus"},
        dataset=None,
        results=results,
    )
    assert "No simulation found" in result.llm_summary
    assert "sim:long_calls" in result.llm_summary


@patch("optopsy.ui.tools._simulators.ResultStore")
def test_get_trades_no_trade_log(mock_store_cls):
    """Simulation exists but trade log is missing/empty."""
    mock_store = MagicMock()
    mock_store.read.return_value = None
    mock_store_cls.return_value = mock_store
    results = {
        "sim:long_calls": {
            "type": "simulation",
            "strategy": "long_calls",
            "_cache_key": "abc123",
        },
    }
    result = execute_tool(
        "get_simulation_trades",
        {"simulation_key": "sim:long_calls"},
        dataset=None,
        results=results,
    )
    assert "no cached trade log" in result.llm_summary


@patch("optopsy.ui.tools._simulators.ResultStore")
def test_get_trades_with_key(mock_store_cls):
    """Retrieve trades for a specific simulation key."""
    trade_df = pd.DataFrame({"trade_id": [1, 2], "pnl": [100, -50]})
    mock_store = MagicMock()
    mock_store.read.return_value = trade_df
    mock_store_cls.return_value = mock_store
    results = {
        "sim:long_calls": {
            "type": "simulation",
            "strategy": "long_calls",
            "_cache_key": "abc123",
        },
    }
    result = execute_tool(
        "get_simulation_trades",
        {"simulation_key": "sim:long_calls"},
        dataset=None,
        results=results,
    )
    assert "2 trades" in result.llm_summary
    assert result.user_display is not None


@patch("optopsy.ui.tools._simulators.ResultStore")
def test_get_trades_no_key_fallback(mock_store_cls):
    """Without a key, should use the most recent simulation."""
    trade_df = pd.DataFrame({"trade_id": [1], "pnl": [100]})
    mock_store = MagicMock()
    mock_store.read.return_value = trade_df
    mock_store_cls.return_value = mock_store
    results = {
        "run:long_calls": {"type": "strategy", "strategy": "long_calls"},
        "sim:short_puts": {
            "type": "simulation",
            "strategy": "short_puts",
            "_cache_key": "def456",
        },
    }
    result = execute_tool(
        "get_simulation_trades",
        {},
        dataset=None,
        results=results,
    )
    assert "1 trades" in result.llm_summary
    mock_store.read.assert_called_once_with("def456")
