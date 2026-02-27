"""UI compatibility shim mirroring :mod:`optopsy.data._compat`.

This module provides a local ``import_optional_dependency`` helper for the
UI package, keeping the ``optopsy[ui]`` install hint so that callers inside
the UI package get the correct suggestion.
"""

from __future__ import annotations

import importlib
import types


def import_optional_dependency(name: str) -> types.ModuleType:
    """Import an optional dependency or raise a helpful error.

    Used at CLI entry points so users get an actionable message
    instead of a raw ``ModuleNotFoundError``.
    """
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        # Only treat as missing optional dep if the top-level module is
        # what's absent; re-raise internal import failures unchanged.
        top_level_name = name.split(".", 1)[0]
        if exc.name == top_level_name:
            raise ImportError(
                f"Missing optional dependency '{name}'. "
                f"Install it with: pip install optopsy[ui]"
            ) from None
        raise
