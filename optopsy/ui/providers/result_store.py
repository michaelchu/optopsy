"""Re-export from optopsy.data.providers.result_store for backwards compatibility."""

# Re-export module-level constant and class for backwards-compatible imports.
# Note: ResultStore reads _RESULTS_DIR from optopsy.data.providers.result_store.
from optopsy.data.providers.result_store import (
    _RESULTS_DIR,  # noqa: F401
    ResultStore,  # noqa: F401
)
