"""Integration tests proving plugins wire into the running system.

These tests verify that plugins discovered by ``optopsy.plugins`` actually
appear in the strategy/signal/tool registries and can be dispatched through
``execute_tool()``, ``get_tool_schemas()``, and the provider system.

Because ``_schemas.py`` runs plugin discovery at module import time, we must
patch the plugin functions *before* importing those modules.  Tests that touch
``_executor.py`` must also reset its ``_PLUGINS_LOADED`` flag between runs.
"""

import importlib
import sys
from unittest.mock import patch

import pytest

_SCHEMAS_MOD = "optopsy.ui.tools._schemas"


@pytest.fixture(autouse=True)
def _restore_schemas_module():
    """Restore the original _schemas module after tests that reimport it.

    Tests in this file delete _schemas from sys.modules and reimport it with
    mocked plugins.  Without cleanup the tainted module leaks into later tests.
    """
    original = sys.modules.get(_SCHEMAS_MOD)
    yield
    # Restore the original module (or remove the tainted one)
    if original is not None:
        sys.modules[_SCHEMAS_MOD] = original
    elif _SCHEMAS_MOD in sys.modules:
        del sys.modules[_SCHEMAS_MOD]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_strategy(data, **kwargs):
    """Dummy strategy function for testing."""
    return data


def _fake_handler(arguments, dataset, signals, datasets, results, _result):
    """Dummy tool handler that returns a simple ToolResult."""
    return _result(f"plugin_tool ran with {arguments}")


# ---------------------------------------------------------------------------
# Strategy integration
# ---------------------------------------------------------------------------


class TestPluginStrategyIntegration:
    """Verify plugin strategies appear in STRATEGIES and STRATEGY_NAMES."""

    def test_plugin_strategy_in_registry(self):
        plugin_strategies = {
            "jade_lizard": (_fake_strategy, "Jade lizard spread", False, "call"),
        }

        with (
            patch(
                "optopsy.plugins.get_plugin_strategies", return_value=plugin_strategies
            ),
            patch("optopsy.plugins.get_plugin_signals", return_value={}),
            patch("optopsy.plugins.get_plugin_tools", return_value=[]),
        ):
            # Force reimport so module-level code re-runs with our mock
            mod = self._reimport_schemas()

            assert "jade_lizard" in mod.STRATEGIES
            func, desc, is_cal = mod.STRATEGIES["jade_lizard"]
            assert func is _fake_strategy
            assert desc == "Jade lizard spread"
            assert is_cal is False

            assert "jade_lizard" in mod.STRATEGY_NAMES
            assert mod.STRATEGY_OPTION_TYPE["jade_lizard"] == "call"
            assert "jade_lizard" not in mod.CALENDAR_STRATEGIES

    def test_plugin_calendar_strategy(self):
        plugin_strategies = {
            "custom_calendar": (_fake_strategy, "Custom calendar", True, "put"),
        }

        with (
            patch(
                "optopsy.plugins.get_plugin_strategies", return_value=plugin_strategies
            ),
            patch("optopsy.plugins.get_plugin_signals", return_value={}),
            patch("optopsy.plugins.get_plugin_tools", return_value=[]),
        ):
            mod = self._reimport_schemas()

            assert "custom_calendar" in mod.CALENDAR_STRATEGIES
            assert mod.STRATEGY_OPTION_TYPE["custom_calendar"] == "put"

    def test_plugin_strategy_option_type_none(self):
        """Plugin strategy with option_type=None sets it explicitly."""
        plugin_strategies = {
            "custom_straddle": (_fake_strategy, "Custom straddle", False, None),
        }

        with (
            patch(
                "optopsy.plugins.get_plugin_strategies", return_value=plugin_strategies
            ),
            patch("optopsy.plugins.get_plugin_signals", return_value={}),
            patch("optopsy.plugins.get_plugin_tools", return_value=[]),
        ):
            mod = self._reimport_schemas()

            assert mod.STRATEGY_OPTION_TYPE["custom_straddle"] is None

    @staticmethod
    def _reimport_schemas():
        """Force reimport of _schemas to re-run module-level plugin code."""
        mod_name = "optopsy.ui.tools._schemas"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# Signal integration
# ---------------------------------------------------------------------------


class TestPluginSignalIntegration:
    """Verify plugin signals appear in SIGNAL_REGISTRY and SIGNAL_NAMES."""

    def test_plugin_signal_in_registry(self):
        factory = lambda **kw: lambda df: df["close"] > 0  # noqa: E731
        plugin_signals = {"vwap_cross": factory}

        with (
            patch("optopsy.plugins.get_plugin_signals", return_value=plugin_signals),
            patch("optopsy.plugins.get_plugin_strategies", return_value={}),
            patch("optopsy.plugins.get_plugin_tools", return_value=[]),
        ):
            mod = self._reimport_schemas()

            assert "vwap_cross" in mod.SIGNAL_REGISTRY
            assert mod.SIGNAL_REGISTRY["vwap_cross"] is factory
            assert "vwap_cross" in mod.SIGNAL_NAMES

    @staticmethod
    def _reimport_schemas():
        mod_name = "optopsy.ui.tools._schemas"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# Tool integration — execute_tool dispatches plugin handlers
# ---------------------------------------------------------------------------


class TestPluginToolIntegration:
    """Verify plugin tools are callable via execute_tool()."""

    def setup_method(self):
        """Reset executor plugin state before each test."""
        import optopsy.ui.tools._executor as _exec

        _exec._PLUGINS_LOADED = False
        # Remove any plugin handlers from a previous test
        self._original_handlers = dict(_exec._TOOL_HANDLERS)

    def teardown_method(self):
        """Restore executor state after each test."""
        import optopsy.ui.tools._executor as _exec

        _exec._TOOL_HANDLERS.clear()
        _exec._TOOL_HANDLERS.update(self._original_handlers)
        _exec._PLUGINS_LOADED = False

    def test_plugin_tool_dispatched(self):
        """A plugin tool handler is called via execute_tool()."""
        plugin_reg = {
            "schemas": [
                {
                    "type": "function",
                    "function": {
                        "name": "custom_analysis",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "handlers": {"custom_analysis": _fake_handler},
            "models": {},
            "descriptions": {"custom_analysis": "Run custom analysis"},
        }

        with patch("optopsy.plugins.get_plugin_tools", return_value=[plugin_reg]):
            from optopsy.ui.tools._executor import execute_tool

            result = execute_tool(
                "custom_analysis",
                {"param": "value"},
                dataset=None,
            )

        assert "plugin_tool ran" in result.llm_summary
        assert "param" in result.llm_summary

    def test_plugin_tool_not_found_without_plugin(self):
        """Without plugins, an unknown tool returns an error."""
        with patch("optopsy.plugins.get_plugin_tools", return_value=[]):
            from optopsy.ui.tools._executor import execute_tool

            result = execute_tool("nonexistent_tool", {}, dataset=None)

        assert "Unknown tool" in result.llm_summary


# ---------------------------------------------------------------------------
# Tool schema integration — plugin schemas appear in get_tool_schemas()
# ---------------------------------------------------------------------------


class TestPluginToolSchemaIntegration:
    """Verify plugin tool schemas appear in get_tool_schemas() output."""

    def test_plugin_schema_in_tool_list(self):
        plugin_reg = {
            "schemas": [
                {
                    "type": "function",
                    "function": {
                        "name": "custom_scanner",
                        "description": "Scan for custom patterns",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "handlers": {},
            "models": {},
            "descriptions": {},
        }

        with (
            patch("optopsy.plugins.get_plugin_tools", return_value=[plugin_reg]),
            patch("optopsy.plugins.get_plugin_strategies", return_value={}),
            patch("optopsy.plugins.get_plugin_signals", return_value={}),
        ):
            mod = self._reimport_schemas()
            schemas = mod.get_tool_schemas()

        tool_names = [s["function"]["name"] for s in schemas]
        assert "custom_scanner" in tool_names

    def test_plugin_description_merged_into_schema(self):
        """Plugin descriptions fill missing schema descriptions."""
        plugin_reg = {
            "schemas": [
                {
                    "type": "function",
                    "function": {
                        "name": "bare_tool",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "handlers": {},
            "models": {},
            "descriptions": {"bare_tool": "Description from plugin"},
        }

        with (
            patch("optopsy.plugins.get_plugin_tools", return_value=[plugin_reg]),
            patch("optopsy.plugins.get_plugin_strategies", return_value={}),
            patch("optopsy.plugins.get_plugin_signals", return_value={}),
        ):
            mod = self._reimport_schemas()
            schemas = mod.get_tool_schemas()

        bare = next(s for s in schemas if s["function"]["name"] == "bare_tool")
        assert bare["function"]["description"] == "Description from plugin"

    @staticmethod
    def _reimport_schemas():
        mod_name = "optopsy.ui.tools._schemas"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        return importlib.import_module(mod_name)


# ---------------------------------------------------------------------------
# Provider integration
# ---------------------------------------------------------------------------


class TestPluginProviderIntegration:
    """Verify plugin providers are instantiated and returned."""

    def setup_method(self):
        """Reset provider cache before each test."""
        import optopsy.ui.providers as _prov

        _prov._ALL_PROVIDERS = None

    def teardown_method(self):
        import optopsy.ui.providers as _prov

        _prov._ALL_PROVIDERS = None

    def test_plugin_provider_instantiated(self):
        """A valid DataProvider subclass from a plugin is instantiated."""
        from optopsy.ui.providers.base import DataProvider

        class FakeProvider(DataProvider):
            name = "fake"
            env_key = "FAKE_API_KEY"

            def get_tool_schemas(self):
                return []

            def get_tool_names(self):
                return []

            def execute(self, tool_name, arguments):
                return "ok", None

            def is_available(self):
                return True

        with (
            patch("optopsy.plugins.get_plugin_providers", return_value=[FakeProvider]),
            patch(
                "optopsy.ui.providers.EODHDProvider",
                side_effect=ImportError("no eodhd"),
                create=True,
            ),
        ):
            # Reset and reload
            import optopsy.ui.providers as _prov

            _prov._ALL_PROVIDERS = None

            # Patch the EODHD import to fail so we only get plugin providers
            with patch.dict(sys.modules, {"optopsy.ui.providers.eodhd": None}):
                # Force reimport
                importlib.reload(_prov)
                _prov._ALL_PROVIDERS = None
                providers = _prov.get_available_providers()

        assert len(providers) == 1
        assert isinstance(providers[0], FakeProvider)
        assert providers[0].name == "fake"

    def test_non_dataprovider_skipped(self):
        """A plugin returning a non-DataProvider class is skipped."""

        class NotAProvider:
            pass

        with patch("optopsy.plugins.get_plugin_providers", return_value=[NotAProvider]):
            with patch.dict(sys.modules, {"optopsy.ui.providers.eodhd": None}):
                import optopsy.ui.providers as _prov

                importlib.reload(_prov)
                _prov._ALL_PROVIDERS = None
                providers = _prov._load_providers()

        # NotAProvider should have been skipped
        assert all(type(p).__name__ != "NotAProvider" for p in providers)
