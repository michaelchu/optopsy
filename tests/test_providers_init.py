"""Tests for optopsy/ui/providers/__init__.py — provider registry."""

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from unittest.mock import MagicMock, patch

import optopsy.ui.providers as providers_mod
from optopsy.ui.providers import (
    get_all_provider_tool_schemas,
    get_provider_for_tool,
    get_provider_names,
)


@pytest.fixture(autouse=True)
def _reset_providers_cache():
    """Reset the global _ALL_PROVIDERS cache between tests."""
    original = providers_mod._ALL_PROVIDERS
    providers_mod._ALL_PROVIDERS = None
    yield
    providers_mod._ALL_PROVIDERS = original


def test_load_providers_import_error():
    """When eodhd import fails, _load_providers returns an empty list."""
    with patch.dict("sys.modules", {"optopsy.ui.providers.eodhd": None}):
        # Force reimport to trigger ImportError path
        providers_mod._ALL_PROVIDERS = None
        result = providers_mod._load_providers()
        assert result == []


def test_get_provider_names():
    """get_provider_names returns names of available providers."""
    mock_provider = MagicMock()
    mock_provider.name = "TestProvider"
    mock_provider.is_available.return_value = True

    providers_mod._ALL_PROVIDERS = [mock_provider]
    names = get_provider_names()
    assert names == ["TestProvider"]


def test_get_provider_names_unavailable():
    """Unavailable providers are excluded from names."""
    mock_provider = MagicMock()
    mock_provider.name = "TestProvider"
    mock_provider.is_available.return_value = False

    providers_mod._ALL_PROVIDERS = [mock_provider]
    names = get_provider_names()
    assert names == []


def test_get_all_provider_tool_schemas():
    """get_all_provider_tool_schemas aggregates schemas from available providers."""
    mock_provider = MagicMock()
    mock_provider.is_available.return_value = True
    mock_provider.get_tool_schemas.return_value = [
        {"type": "function", "function": {"name": "tool_a"}},
        {"type": "function", "function": {"name": "tool_b"}},
    ]

    providers_mod._ALL_PROVIDERS = [mock_provider]
    schemas = get_all_provider_tool_schemas()
    assert len(schemas) == 2
    assert schemas[0]["function"]["name"] == "tool_a"


def test_get_all_provider_tool_schemas_empty():
    """No available providers should return an empty list."""
    mock_provider = MagicMock()
    mock_provider.is_available.return_value = False

    providers_mod._ALL_PROVIDERS = [mock_provider]
    schemas = get_all_provider_tool_schemas()
    assert schemas == []


def test_get_provider_for_tool_found():
    """Returns the provider that handles the given tool name."""
    mock_provider = MagicMock()
    mock_provider.is_available.return_value = True
    mock_provider.get_tool_names.return_value = ["my_tool", "other_tool"]

    providers_mod._ALL_PROVIDERS = [mock_provider]
    result = get_provider_for_tool("my_tool")
    assert result is mock_provider


def test_get_provider_for_tool_not_found():
    """Returns None when no provider handles the tool."""
    mock_provider = MagicMock()
    mock_provider.is_available.return_value = True
    mock_provider.get_tool_names.return_value = ["my_tool"]

    providers_mod._ALL_PROVIDERS = [mock_provider]
    result = get_provider_for_tool("unknown_tool")
    assert result is None
