"""Re-export from optopsy.data.providers.result_store for backwards compatibility."""

# Re-export module-level constant so monkeypatching in tests still works.
from optopsy.data.providers.result_store import (
    _RESULTS_DIR,  # noqa: F401
    ResultStore,  # noqa: F401
)
