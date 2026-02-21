from typing import Any

from .base import DataProvider

# Providers are lazily imported to avoid requiring UI extras (requests,
# pyarrow, etc.) when only the core library is installed.
_ALL_PROVIDERS: list[DataProvider] | None = None

# Cached lookup: tool_name -> DataProvider for O(1) dispatch.
_TOOL_LOOKUP: dict[str, DataProvider] | None = None


def _load_providers() -> list[DataProvider]:
    global _ALL_PROVIDERS
    if _ALL_PROVIDERS is None:
        try:
            from .eodhd import EODHDProvider

            _ALL_PROVIDERS = [EODHDProvider()]
        except ImportError:
            _ALL_PROVIDERS = []
    return _ALL_PROVIDERS


def get_available_providers() -> list[DataProvider]:
    """Return only providers whose API keys are configured."""
    return [p for p in _load_providers() if p.is_available()]


def get_provider_names() -> list[str]:
    """Return human-readable names of available providers."""
    return [p.name for p in get_available_providers()]


def get_all_provider_tool_schemas() -> list[dict[str, Any]]:
    """Return tool schemas from all available providers."""
    schemas: list[dict[str, Any]] = []
    for p in get_available_providers():
        schemas.extend(p.get_tool_schemas())
    return schemas


def _build_tool_lookup() -> dict[str, DataProvider]:
    """Build and cache a {tool_name: provider} mapping for O(1) dispatch."""
    global _TOOL_LOOKUP
    if _TOOL_LOOKUP is None:
        _TOOL_LOOKUP = {}
        for p in get_available_providers():
            for name in p.get_tool_names():
                _TOOL_LOOKUP[name] = p
    return _TOOL_LOOKUP


def get_provider_for_tool(tool_name: str) -> DataProvider | None:
    """Find which available provider handles a given tool name."""
    return _build_tool_lookup().get(tool_name)
