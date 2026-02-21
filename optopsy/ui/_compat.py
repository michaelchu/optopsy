"""Centralized optional dependency imports for the UI package.

Follows the pandas pattern: all UI source files ship with the core package,
but the third-party dependencies (chainlit, litellm, etc.) are only installed
when the user runs ``pip install optopsy[ui]``.  This module provides a single
function that gives consistent, actionable error messages when a dependency is
missing.
"""

from __future__ import annotations

import importlib
import types
from typing import Literal

# Minimum versions for UI dependencies.  Only packages that have known
# compatibility constraints need an entry here — others are checked for
# presence only.
VERSIONS: dict[str, str] = {
    "chainlit": "1.0.0",
    "litellm": "1.0.0",
    "pyarrow": "14.0.0",
    "requests": "2.28.0",
    "yfinance": "0.2.0",
}

# When the PyPI package name differs from the Python import name, map
# import_name -> pip_name so the error message tells users the right thing.
INSTALL_MAPPING: dict[str, str] = {
    "dotenv": "python-dotenv",
}


def import_optional_dependency(
    name: str,
    extra: str = "ui",
    *,
    errors: Literal["raise", "warn", "ignore"] = "raise",
) -> types.ModuleType | None:
    """Import an optional dependency, returning the module or ``None``.

    Parameters
    ----------
    name : str
        The module to import (e.g. ``"chainlit"``).
    extra : str
        The pip extras group that provides this dependency.  Used in the
        error message: ``pip install optopsy[{extra}]``.
    errors : {"raise", "warn", "ignore"}
        * ``"raise"`` (default) — raise :class:`ImportError` with an
          actionable message.
        * ``"warn"`` — emit a :class:`UserWarning` and return ``None``.
        * ``"ignore"`` — silently return ``None``.
    """
    pip_name = INSTALL_MAPPING.get(name, name)
    install_hint = (
        f"pip install optopsy[{extra}]" if extra else f"pip install {pip_name}"
    )

    try:
        module = importlib.import_module(name)
    except ImportError:
        msg = (
            f"Missing optional dependency '{pip_name}'. "
            f"Install it with: {install_hint}"
        )
        if errors == "raise":
            raise ImportError(msg) from None
        if errors == "warn":
            import warnings

            warnings.warn(msg, UserWarning, stacklevel=2)
        return None

    # Version check (best-effort).
    min_version = VERSIONS.get(name)
    if min_version is not None:
        installed_version = getattr(module, "__version__", None)
        if installed_version is not None:
            from packaging.version import Version

            try:
                if Version(installed_version) < Version(min_version):
                    msg = (
                        f"optopsy requires version '{min_version}' or newer of "
                        f"'{pip_name}' (version '{installed_version}' currently "
                        f"installed). Upgrade with: {install_hint}"
                    )
                    if errors == "raise":
                        raise ImportError(msg)
                    if errors == "warn":
                        import warnings

                        warnings.warn(msg, UserWarning, stacklevel=2)
                        return None
                    return None
            except Exception:
                # packaging not available or version string unparseable — skip
                pass

    return module
