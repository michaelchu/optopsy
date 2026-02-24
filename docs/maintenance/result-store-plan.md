# Plan: Global Result Store with Query Tool

Last updated: 2026-02-24

## Context

The LLM agent loses access to full strategy result data after message compaction (300-char truncation). It only has scalar summaries (mean, std, win_rate), so it can't answer follow-up questions like "sort by returns" or "which bucket performed best."

Additionally, strategy backtests are expensive and deterministic — same strategy + same params + same data always produces the same result. We should cache results globally so they can be reused across sessions.

## Approach

**Global result cache with content-hashed keys, queryable via a tool.**

- **Cache key:** Deterministic hash of (strategy_name, all params, dataset content hash). Uses `pd.util.hash_pandas_object(df, index=False).sum()` to fingerprint the dataset (~15-30ms for 50k rows, computed once per dataset load). Same inputs = same key = cache hit.
- **Writing:** Strategy handler checks cache before executing. On miss, runs strategy and writes result. On hit, returns cached result instantly.
- **Reading:** A new `query_results` tool lets the LLM read, sort, filter, and slice stored results from the current session.
- **No thread_id scoping:** Results are global. Any session can reuse cached results.

### Why global over per-session

| | Per-session | Global cache |
|---|---|---|
| Thread ID plumbing | Need to thread through agent → executor | Not needed |
| Cleanup | Manual per-thread | Size-based pruning |
| Cross-session reuse | No | **Yes — saves compute** |
| Key collisions | Same params overwrite (signals/dataset ignored) | Content hash prevents collisions |
| Session resume | Works (files on disk per thread) | Works (files on disk, global) |

## Cache Key Design

```python
import hashlib, json, pandas as pd

def make_cache_key(strategy_name: str, arguments: dict, dataset_fingerprint: str) -> str:
    """Deterministic cache key for a strategy run."""
    # Strategy params (sorted for determinism, excluding non-strategy keys)
    param_keys = sorted(k for k in arguments.keys() if k != "strategy_name")
    params_str = json.dumps({k: arguments[k] for k in param_keys}, sort_keys=True)

    # Combine into a single hash
    raw = f"{strategy_name}:{params_str}:{dataset_fingerprint}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

Produces a short hex string like `"a3f8b2c1d4e5f678"` — no sanitization needed, no collisions.

The human-readable display key (`long_calls:dte=45,...`) is stored as metadata alongside the hash.

## Directory Structure

```
~/.optopsy/results/
  {hash}.parquet          # full result DataFrame
  _index.json             # maps hash → {strategy, params, display_key, created_at}
```

A single `_index.json` maps hashes to metadata for listing and display.

## Files to Change

| File | Change |
|---|---|
| `optopsy/ui/providers/result_store.py` | **New.** `ResultStore` class with content-hashed keys |
| `optopsy/ui/tools/_strategy_runners.py` | Check cache before running; write on miss |
| `optopsy/ui/tools/_executor.py` | Pass `dataset_fingerprint` for strategy tools |
| `optopsy/ui/tools/_results_manager.py` | Add `query_results` handler |
| `optopsy/ui/tools/_models.py` | Add `QueryResultsArgs` Pydantic model |
| `optopsy/ui/tools/_schemas.py` | Add `query_results` tool schema |
| `optopsy/ui/agent.py` | Compute + cache dataset fingerprint; simplify results memo |
| `tests/` | Add tests for `ResultStore` and `query_results` |

## Step-by-Step

### 1. Create `ResultStore` (`optopsy/ui/providers/result_store.py`)

```python
class ResultStore:
    """Global parquet cache for strategy result DataFrames.

    Keys are SHA-256 hashes of (strategy_name, params, dataset_fingerprint).
    A JSON index maps hashes to human-readable metadata.
    """

    def __init__(self, results_dir="~/.optopsy/results"): ...
    def make_key(strategy_name, arguments, dataset_fingerprint) -> str: ...
    def write(key, df, metadata) -> None: ...
    def read(key) -> pd.DataFrame | None: ...
    def has(key) -> bool: ...
    def list_all() -> dict[str, dict]: ...
    def clear(key=None) -> int: ...
    def total_size_bytes() -> int: ...
```

### 2. Compute dataset fingerprint in agent

In `OptopsyAgent`, cache the fingerprint when dataset changes:

```python
# After self.dataset is updated in chat():
if result.dataset is not None:
    self.dataset = result.dataset
    self._dataset_fingerprint = str(
        pd.util.hash_pandas_object(self.dataset, index=False).sum()
    )
```

Computed once per dataset load. Reused for all subsequent strategy runs.

### 3. Pass fingerprint through executor

Add `dataset_fingerprint: str | None = None` to `execute_tool`. Inject into arguments for strategy tools only:

```python
def execute_tool(..., dataset_fingerprint=None):
    ...
    if dataset_fingerprint and tool_name in ("run_strategy", "scan_strategies"):
        arguments = {**arguments, "_dataset_fingerprint": dataset_fingerprint}
    ...
```

No handler signature changes. Handlers pop `_dataset_fingerprint` from arguments.

### 4. Cache check in strategy runners

In `_handle_run_strategy`, before calling `_run_one_strategy`:

```python
from ..providers.result_store import ResultStore

store = ResultStore()
ds_fp = strat_kwargs.pop("_dataset_fingerprint", None)
cache_key = store.make_key(strategy_name, strat_kwargs, ds_fp) if ds_fp else None

# Check cache
if cache_key and store.has(cache_key):
    result_df = store.read(cache_key)
else:
    result_df, err = _run_one_strategy(strategy_name, dataset, strat_kwargs)
    # Write to cache on success
    if cache_key and result_df is not None and not result_df.empty:
        store.write(cache_key, result_df, metadata={
            "strategy": strategy_name,
            "display_key": _make_result_key(strategy_name, arguments),
            "params": strat_kwargs,
        })
```

Same approach for `scan_strategies` (cache the leaderboard).

### 5. Add `query_results` tool

**Model** (`_models.py`):
- `result_key: str | None` — display key from `list_results`. Omit to list available.
- `sort_by: str | None` — column to sort by
- `ascending: bool = False`
- `head: int | None` — first N rows
- `filter_column: str | None` + `filter_op` (`gt`, `lt`, `eq`, `contains`, etc.) + `filter_value`
- `columns: list[str] | None` — select specific columns

**Handler** (`_results_manager.py`):
- If no `result_key`: list keys from current session's `agent.results` with summaries
- If `result_key`: look up `_cache_key` from `agent.results`, read from store, apply sort/filter/slice, return markdown table (up to 50 rows)

Session's `agent.results` dict stores `{"_cache_key": hash, ...}` so the handler can find the parquet file.

### 6. Simplify results memo in system prompt

Replace top-5 detailed memo (invalidates Anthropic prompt cache every call) with:

```
"Session has {N} strategy result(s). Use query_results to access full data."
```

Stable text reduces cache invalidation.

### 7. Update system prompt

Add to `## Workflow`:

```
- Use `query_results` to examine, sort, filter, or slice results from previous strategy
  runs without re-running them. This is the preferred way to answer follow-up questions
  about results.
- Strategy results are cached globally — if the same strategy with identical parameters
  has been run before on the same data, the cached result is returned instantly.
```

### 8. Update session resume message

```
"[Session resumed] In-memory datasets and signals were cleared.
Previous strategy results are still accessible via query_results."
```

### 9. Tests

- `ResultStore`: write/read round-trip, `make_key` determinism, `has()`, `list_all`, `clear`
- `query_results` handler: list mode, sort, filter, head/tail, missing key
- Cache hit: `run_strategy` returns cached result without re-executing
- Content hash: same data → same fingerprint, different data → different fingerprint

## Verification

1. `uv run pytest tests/ -v` — all existing + new tests pass
2. `uv run ruff check optopsy/ tests/` — no lint errors
3. Manual test flow:
   - Start chat, load data, run a strategy → result stored in global cache
   - Ask "sort the results by mean return descending" → LLM calls `query_results`
   - Run the same strategy again → instant cache hit, no recomputation
   - New session, load same data, run same strategy → cache hit across sessions
   - Reload page (session resume) → `query_results` still works
