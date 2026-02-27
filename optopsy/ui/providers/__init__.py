"""UI-layer provider registry.

Re-exports the core registry from ``optopsy.data.providers`` but patches
``_load_providers`` to use the UI's ``EODHDProvider`` subclass (which adds
``get_arg_model`` for Pydantic validation).
"""

import logging
import sys

import optopsy.data.providers as _data_providers
from optopsy.data.providers import (  # noqa: F401
    get_all_provider_tool_schemas,
    get_available_providers,
    get_provider_for_tool,
    get_provider_names,
)
from optopsy.data.providers.base import DataProvider  # noqa: F401

_log = logging.getLogger(__name__)

_THIS = sys.modules[__name__]


# --- UI-specific _load_providers override ---------------------------------

# Store the real data-layer function once to survive importlib.reload().
if not hasattr(_THIS, "_DATA_LOAD_PROVIDERS"):
    object.__setattr__(_THIS, "_DATA_LOAD_PROVIDERS", _data_providers._load_providers)


def _load_providers():
    """Delegate to the data layer's _load_providers.

    After loading, replaces the base EODHDProvider with the UI subclass
    that adds get_arg_model() support.
    """
    providers = _THIS._DATA_LOAD_PROVIDERS()

    # Swap in the UI EODHDProvider subclass if the base one was loaded
    try:
        from optopsy.data.providers.eodhd import EODHDProvider as _BaseEODHD

        from .eodhd import EODHDProvider as _UIEodhd
    except (ImportError, ModuleNotFoundError):
        return providers

    for i, p in enumerate(providers):
        if type(p) is _BaseEODHD:
            providers[i] = _UIEodhd()

    return providers


# Patch the data layer so re-exported functions use the UI's _load_providers.
_data_providers._load_providers = _load_providers


# --- _ALL_PROVIDERS proxy -------------------------------------------------
# Backwards compat with tests that do ``providers_mod._ALL_PROVIDERS = None``.


def __getattr__(name: str):
    if name == "_ALL_PROVIDERS":
        return _data_providers._ALL_PROVIDERS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __setattr__(name: str, value):
    if name == "_ALL_PROVIDERS":
        _data_providers._ALL_PROVIDERS = value
        return
    # Allow normal module attribute assignment for everything else
    object.__setattr__(_THIS, name, value)
