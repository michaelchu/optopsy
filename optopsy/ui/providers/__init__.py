from typing import Any

from .base import DataProvider
from .eodhd import EODHDProvider

# Add new providers here. That's the only change needed.
ALL_PROVIDERS: list[DataProvider] = [
    EODHDProvider(),
]


def get_available_providers() -> list[DataProvider]:
    """Return only providers whose API keys are configured."""
    return [p for p in ALL_PROVIDERS if p.is_available()]


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
