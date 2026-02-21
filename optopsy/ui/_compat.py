"""Helpers for optional UI dependency imports."""

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
    except ImportError:
        raise ImportError(
            f"Missing optional dependency '{name}'. "
            f"Install it with: pip install optopsy[ui]"
        ) from None
