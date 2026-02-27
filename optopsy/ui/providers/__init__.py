"""UI-layer provider registry.

Re-exports the core registry from ``optopsy.data.providers`` but overrides
``_load_providers`` to use the UI's ``EODHDProvider`` subclass (which adds
``get_arg_model`` for Pydantic validation).
"""

import logging
from typing import Any

import optopsy.data.providers as _data_providers
from optopsy.data.providers import (  # noqa: F401
    get_all_provider_tool_schemas,
    get_available_providers,
    get_provider_for_tool,
    get_provider_names,
)
from optopsy.data.providers.base import DataProvider  # noqa: F401

_log = logging.getLogger(__name__)

# Expose _ALL_PROVIDERS from the data layer so tests that patch it still work.
# This is a module-level alias; mutations go through to the data layer.


def _get_all_providers():
    return _data_providers._ALL_PROVIDERS


def _set_all_providers(value):
    _data_providers._ALL_PROVIDERS = value


# Property-like access for backwards compat with tests that do
# ``providers_mod._ALL_PROVIDERS = None``
_ALL_PROVIDERS = _data_providers._ALL_PROVIDERS


def __getattr__(name: str):
    if name == "_ALL_PROVIDERS":
        return _data_providers._ALL_PROVIDERS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __setattr__(name: str, value):
    if name == "_ALL_PROVIDERS":
        _data_providers._ALL_PROVIDERS = value
        return
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _load_providers():
    """Delegate to the data layer's _load_providers.

    After loading, replaces the base EODHDProvider with the UI subclass
    that adds get_arg_model() support.
    """
    providers = _data_providers._load_providers()

    # Swap in the UI EODHDProvider subclass if the base one was loaded
    from optopsy.data.providers.eodhd import EODHDProvider as _BaseEODHD

    try:
        from .eodhd import EODHDProvider as _UIEodhd
    except ImportError:
        return providers

    for i, p in enumerate(providers):
        if type(p) is _BaseEODHD:
            providers[i] = _UIEodhd()

    return providers
