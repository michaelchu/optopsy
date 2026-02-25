"""Plugin discovery via Python entry points.

Discovers and loads extensions registered under these entry point groups:

- ``optopsy.strategies`` — each entry point loads a registrar returning
  ``{name: (func, description, is_calendar, option_type)}``
- ``optopsy.signals`` — each entry point loads a registrar returning
  ``{name: factory_lambda}``
- ``optopsy.providers`` — each entry point loads a ``DataProvider`` subclass
- ``optopsy.tools`` — each entry point loads a registrar returning
  ``{"schemas": [...], "handlers": {...}, "models": {...}, "descriptions": {...}}``

All discovery is lazy and cached.  The public optopsy package never
references any plugin package by name.
"""

import importlib.metadata
import logging
from typing import Any

_log = logging.getLogger(__name__)

_cache: dict[str, list[Any]] = {}


def _discover(group: str) -> list[Any]:
    """Load all entry points for *group*, caching the results.

    Failures are logged and skipped so one broken plugin cannot crash the host.
    """
    if group in _cache:
        return _cache[group]

    eps = importlib.metadata.entry_points(group=group)
    results: list[Any] = []
    for ep in eps:
        try:
            results.append(ep.load())
        except Exception:
            _log.warning(
                "Failed to load plugin entry point '%s' (dist=%s)",
                ep.name,
                ep.dist,
                exc_info=True,
            )
    _cache[group] = results
    return results


def get_plugin_strategies() -> dict[str, tuple]:
    """Discover plugin strategies.

    Each entry point must resolve to a callable returning::

        {name: (function, description, is_calendar, option_type)}

    where *option_type* is ``"call"``, ``"put"``, or ``None``.
    """
    merged: dict[str, tuple] = {}
    for registrar in _discover("optopsy.strategies"):
        try:
            merged.update(registrar())
        except Exception:
            _log.warning("Plugin strategy registrar failed", exc_info=True)
    return merged


def get_plugin_signals() -> dict[str, Any]:
    """Discover plugin signals.

    Each entry point must resolve to a callable returning::

        {name: factory_lambda}

    matching the shape of ``SIGNAL_REGISTRY`` in ``_schemas.py``.
    """
    merged: dict[str, Any] = {}
    for registrar in _discover("optopsy.signals"):
        try:
            merged.update(registrar())
        except Exception:
            _log.warning("Plugin signal registrar failed", exc_info=True)
    return merged


def get_plugin_providers() -> list[type]:
    """Discover plugin ``DataProvider`` subclasses.

    Each entry point must resolve to a ``DataProvider`` subclass (the class
    itself, not an instance).  The caller is responsible for instantiation.
    """
    return list(_discover("optopsy.providers"))


def get_plugin_tools() -> list[dict[str, Any]]:
    """Discover plugin tool registrations.

    Each entry point must resolve to a callable returning::

        {
            "schemas": [OpenAI-compatible tool schema dicts],
            "handlers": {tool_name: handler_callable},
            "models": {tool_name: PydanticModel},
            "descriptions": {tool_name: description_string},
        }
    """
    registrations: list[dict[str, Any]] = []
    for registrar in _discover("optopsy.tools"):
        try:
            registrations.append(registrar())
        except Exception:
            _log.warning("Plugin tool registrar failed", exc_info=True)
    return registrations
