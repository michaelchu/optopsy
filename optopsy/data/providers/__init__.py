"""Pluggable data provider registry.

Providers are lazily imported so that ``import optopsy`` never requires
extras (requests, pyarrow, etc.).  A provider is "available" when its
``env_key`` (e.g. ``EODHD_API_KEY``) is set in the environment.

Public helpers:

- ``get_available_providers()`` — list providers with configured API keys
- ``get_provider_for_tool(tool_name)`` — find the provider that handles a tool
- ``get_all_provider_tool_schemas()`` — aggregate tool schemas for the LLM
"""

import logging
from typing import Any

from .base import DataProvider

_log = logging.getLogger(__name__)

# Providers are lazily imported to avoid requiring extras (requests,
# pyarrow, etc.) when only the core library is installed.
_ALL_PROVIDERS: list[DataProvider] | None = None


def _load_providers() -> list[DataProvider]:
    global _ALL_PROVIDERS
    if _ALL_PROVIDERS is None:
        providers: list[DataProvider] = []
        try:
            from .eodhd import EODHDProvider

            providers.append(EODHDProvider())
        except ImportError:
            pass

        # Discover plugin providers
        try:
            from optopsy.plugins import get_plugin_providers

            for cls in get_plugin_providers():
                if not isinstance(cls, type) or not issubclass(cls, DataProvider):
                    _log.warning(
                        "Skipping plugin provider %s: not a DataProvider subclass",
                        cls,
                    )
                    continue
                try:
                    providers.append(cls())
                except Exception:
                    _log.warning(
                        "Failed to instantiate plugin provider %s",
                        cls,
                        exc_info=True,
                    )
        except Exception:
            _log.warning("Plugin provider discovery failed", exc_info=True)

        _ALL_PROVIDERS = providers
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


def get_provider_for_tool(tool_name: str) -> DataProvider | None:
    """Find which available provider handles a given tool name."""
    for p in get_available_providers():
        if tool_name in p.get_tool_names():
            return p
    return None
