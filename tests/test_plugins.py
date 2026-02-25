"""Tests for optopsy/plugins.py — entry-point-based plugin discovery."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import optopsy.plugins as plugins_mod
from optopsy.plugins import (
    get_plugin_providers,
    get_plugin_signals,
    get_plugin_strategies,
    get_plugin_tools,
)


@pytest.fixture(autouse=True)
def _reset_plugin_cache():
    """Clear the plugin discovery cache between tests."""
    plugins_mod._cache.clear()
    yield
    plugins_mod._cache.clear()


# ---------------------------------------------------------------------------
# Helper to build mock entry points
# ---------------------------------------------------------------------------


def _make_ep(name: str, load_return):
    """Create a mock entry point whose .load() returns *load_return*."""
    ep = SimpleNamespace(name=name, dist=SimpleNamespace(name="test-plugin"))
    ep.load = MagicMock(return_value=load_return)
    return ep


def _make_failing_ep(name: str, exc: Exception | None = None):
    """Create a mock entry point whose .load() raises."""
    ep = SimpleNamespace(name=name, dist=SimpleNamespace(name="broken-plugin"))
    ep.load = MagicMock(side_effect=exc or RuntimeError("boom"))
    return ep


# ---------------------------------------------------------------------------
# No plugins installed — baseline behaviour
# ---------------------------------------------------------------------------


def test_no_plugins_strategies():
    with patch("importlib.metadata.entry_points", return_value=[]):
        assert get_plugin_strategies() == {}


def test_no_plugins_signals():
    with patch("importlib.metadata.entry_points", return_value=[]):
        assert get_plugin_signals() == {}


def test_no_plugins_providers():
    with patch("importlib.metadata.entry_points", return_value=[]):
        assert get_plugin_providers() == []


def test_no_plugins_tools():
    with patch("importlib.metadata.entry_points", return_value=[]):
        assert get_plugin_tools() == []


# ---------------------------------------------------------------------------
# Strategy plugin discovery
# ---------------------------------------------------------------------------


def _fake_strategy(data, **kwargs):
    return data


def test_strategy_plugin():
    registrar = lambda: {  # noqa: E731
        "jade_lizard": (_fake_strategy, "Jade lizard", False, None),
    }
    ep = _make_ep("pro", registrar)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = get_plugin_strategies()

    assert "jade_lizard" in result
    func, desc, is_cal, opt_type = result["jade_lizard"]
    assert func is _fake_strategy
    assert desc == "Jade lizard"
    assert is_cal is False
    assert opt_type is None


def test_strategy_plugin_with_option_type():
    registrar = lambda: {  # noqa: E731
        "ratio_call": (_fake_strategy, "Ratio call spread", False, "call"),
    }
    ep = _make_ep("pro", registrar)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = get_plugin_strategies()

    assert result["ratio_call"][3] == "call"


# ---------------------------------------------------------------------------
# Signal plugin discovery
# ---------------------------------------------------------------------------


def test_signal_plugin():
    factory = lambda **kw: lambda df: df["close"] > 0  # noqa: E731
    registrar = lambda: {"vwap_cross": factory}  # noqa: E731
    ep = _make_ep("pro", registrar)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = get_plugin_signals()

    assert "vwap_cross" in result
    assert result["vwap_cross"] is factory


# ---------------------------------------------------------------------------
# Provider plugin discovery
# ---------------------------------------------------------------------------


def test_provider_plugin():
    mock_cls = MagicMock
    ep = _make_ep("polygon", mock_cls)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = get_plugin_providers()

    assert len(result) == 1
    assert result[0] is mock_cls


# ---------------------------------------------------------------------------
# Tool plugin discovery
# ---------------------------------------------------------------------------


def test_tool_plugin():
    handler = MagicMock()
    registrar = lambda: {  # noqa: E731
        "schemas": [{"type": "function", "function": {"name": "my_tool"}}],
        "handlers": {"my_tool": handler},
        "models": {},
        "descriptions": {"my_tool": "A custom tool"},
    }
    ep = _make_ep("pro", registrar)

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        result = get_plugin_tools()

    assert len(result) == 1
    assert result[0]["handlers"]["my_tool"] is handler
    assert result[0]["descriptions"]["my_tool"] == "A custom tool"


# ---------------------------------------------------------------------------
# Error handling — broken plugins are logged and skipped
# ---------------------------------------------------------------------------


def test_broken_entry_point_load(caplog):
    """A plugin whose entry point .load() raises is skipped with a warning."""
    ep = _make_failing_ep("broken")

    with (
        patch("importlib.metadata.entry_points", return_value=[ep]),
        caplog.at_level(logging.WARNING, logger="optopsy.plugins"),
    ):
        result = get_plugin_strategies()

    assert result == {}
    assert "Failed to load plugin entry point 'broken'" in caplog.text


def test_broken_registrar(caplog):
    """A registrar that raises is skipped with a warning."""

    def bad_registrar():
        raise ValueError("registrar exploded")

    ep = _make_ep("bad", bad_registrar)

    with (
        patch("importlib.metadata.entry_points", return_value=[ep]),
        caplog.at_level(logging.WARNING, logger="optopsy.plugins"),
    ):
        result = get_plugin_strategies()

    assert result == {}
    assert "Plugin strategy registrar failed" in caplog.text


def test_broken_signal_registrar(caplog):
    def bad_registrar():
        raise RuntimeError("signal boom")

    ep = _make_ep("bad", bad_registrar)

    with (
        patch("importlib.metadata.entry_points", return_value=[ep]),
        caplog.at_level(logging.WARNING, logger="optopsy.plugins"),
    ):
        result = get_plugin_signals()

    assert result == {}
    assert "Plugin signal registrar failed" in caplog.text


def test_broken_tool_registrar(caplog):
    def bad_registrar():
        raise RuntimeError("tool boom")

    ep = _make_ep("bad", bad_registrar)

    with (
        patch("importlib.metadata.entry_points", return_value=[ep]),
        caplog.at_level(logging.WARNING, logger="optopsy.plugins"),
    ):
        result = get_plugin_tools()

    assert result == []
    assert "Plugin tool registrar failed" in caplog.text


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def test_discovery_is_cached():
    """Calling the same group twice should only invoke entry_points once."""
    registrar = lambda: {"cached_strat": (_fake_strategy, "Cached", False, None)}  # noqa: E731
    ep = _make_ep("pro", registrar)

    with patch("importlib.metadata.entry_points", return_value=[ep]) as mock_eps:
        first = get_plugin_strategies()
        second = get_plugin_strategies()

    assert first == second
    # entry_points called once for the group, cached thereafter
    assert mock_eps.call_count == 1


# ---------------------------------------------------------------------------
# Multiple plugins merge correctly
# ---------------------------------------------------------------------------


def test_multiple_strategy_plugins():
    reg1 = lambda: {"strat_a": (_fake_strategy, "A", False, None)}  # noqa: E731
    reg2 = lambda: {"strat_b": (_fake_strategy, "B", True, "put")}  # noqa: E731
    ep1 = _make_ep("plugin1", reg1)
    ep2 = _make_ep("plugin2", reg2)

    with patch("importlib.metadata.entry_points", return_value=[ep1, ep2]):
        result = get_plugin_strategies()

    assert "strat_a" in result
    assert "strat_b" in result
    assert result["strat_b"][2] is True  # is_calendar
    assert result["strat_b"][3] == "put"  # option_type
