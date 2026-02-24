# Plan: Global Result Store with Query Tool

Last updated: 2026-02-25

## Context

The LLM agent loses access to full strategy result data after message compaction (300-char truncation). It only has scalar summaries (mean, std, win_rate), so it can't answer follow-up questions like "sort by returns" or "which bucket performed best."

Additionally, strategy backtests and simulations are expensive and deterministic — same inputs always produce the same result. We should cache results globally so they can be reused across sessions.

## Approach

**Global result cache with content-hashed keys, queryable via a tool. Unified caching for both strategy results and simulator trade logs.**

- **Cache key:** Deterministic SHA-256 hash of (name, all params, dataset content hash). Uses `pd.util.hash_pandas_object(df, index=False).sum()` to fingerprint the dataset (computed once per dataset load; performance varies with column types and data complexity). Same inputs = same key = cache hit. The fingerprint covers all rows and columns, so loading the same symbol with a different date range produces a different fingerprint and a different cache key.
- **Writing:** Handlers check cache before executing. On miss, run and write. On hit, return cached result instantly.
- **Reading:** A new `query_results` tool lets the LLM read, sort, filter, and slice stored results.
- **No thread_id scoping:** Results are global. Any session can reuse cached results.
- **Both raw and aggregated** strategy results are cached as separate entries (the `raw` param is part of the hash, producing different keys).

### Why global over per-session

| | Per-session | Global cache |
|---|---|---|
| Thread ID plumbing | Need to thread through agent → executor | Not needed |
| Cleanup | Manual per-thread | Size-based pruning |
| Cross-session reuse | No | **Yes — saves compute** |
| Key collisions | Same params overwrite (signals/dataset ignored) | Content hash prevents collisions |
| Session resume | Works (files on disk per thread) | Works (files on disk, global) |

### Unified caching for strategies and simulations

Strategy results and simulator results have different formats but the **caching mechanism is identical**: hash inputs, store DataFrame, return on cache hit.

| | Strategy results | Simulator results |
|---|---|---|
| Output format | Trades (raw) or bucketed stats (aggregated) | Trade log with equity curve |
| Key metrics | mean return, win rate per bucket | Sharpe, Sortino, max drawdown, VaR |
| Capital tracking | No | Yes (sequential equity simulation) |
| What's cached | Result DataFrame | Trade log DataFrame |
| Scalar summary in `agent.results` | count, mean_return, std, win_rate, profit_factor | 18 metrics (total_return, sharpe, etc.) |

The result **formats stay different** — they answer different analytical questions. What's unified is the **caching layer**: same `ResultStore`, same content-hashing, same `_cache_key` pattern in `agent.results`.

This also **retires the simulator's existing persistence** (`write_sim_trade_log` / `read_sim_trade_log` using `ParquetCache` with lossy `_sim_fs_key` sanitization) in favor of ResultStore.

## Cache Key Design

```python
import hashlib, json

# Implemented as ResultStore.make_key() static method
def make_key(name: str, arguments: dict, dataset_fingerprint: str) -> str:
    """Deterministic cache key for any result (strategy or simulation)."""
    param_keys = sorted(k for k in arguments.keys() if k not in ("strategy_name",))
    params_str = json.dumps({k: arguments[k] for k in param_keys}, sort_keys=True)
    raw = f"{name}:{params_str}:{dataset_fingerprint}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

Produces a short hex string like `"a3f8b2c1d4e5f678"` — no sanitization needed, no collisions.

Examples of how the same strategy with different params produces different keys:

```
# Aggregated (raw=false, default)
hash("long_calls:{"max_entry_dte":45,"raw":false,...}:9823745...") → "a3f8b2c1d4e5f678"

# Raw trades (raw=true)
hash("long_calls:{"max_entry_dte":45,"raw":true,...}:9823745...") → "7e2d9f04b1c3a896"

# Different dataset
hash("long_calls:{"max_entry_dte":45,"raw":false,...}:5567812...") → "c4d1e8f2a9b30756"

# Simulation
hash("sim:long_calls:{"initial_capital":10000,...}:9823745...") → "f1a2b3c4d5e6f789"
```

## Directory Structure

```
~/.optopsy/results/
  {hash}.parquet          # full result DataFrame (strategy or trade log)
  _index.json             # maps hash → {type, strategy, params, display_key, created_at}
```

A single `_index.json` maps hashes to metadata. The `type` field distinguishes `"strategy"` from `"simulation"`.

Example `_index.json`:

```json
{
  "a3f8b2c1d4e5f678": {
    "type": "strategy",
    "strategy": "long_calls",
    "display_key": "long_calls:dte=45,exit=0,otm=0.50,slip=mid",
    "params": {"max_entry_dte": 45, "exit_dte": 0, "max_otm_pct": 0.5, "slippage": "mid"}
  },
  "f1a2b3c4d5e6f789": {
    "type": "simulation",
    "strategy": "short_puts",
    "display_key": "sim:short_puts",
    "params": {"capital": 100000, "max_entry_dte": 45},
    "summary": {"total_trades": 52, "win_rate": 0.73, "total_return": 0.15, "sharpe_ratio": 1.42, "...": "..."}
  }
}
```

## Files to Change

| File | Change |
|---|---|
| `optopsy/ui/providers/result_store.py` | **New.** `ResultStore` class with content-hashed keys |
| `optopsy/ui/tools/_strategy_runners.py` | Check cache before running strategy; write on miss |
| `optopsy/ui/tools/_simulators.py` | Check cache before running simulation; write on miss; retire `write_sim_trade_log` |
| `optopsy/ui/tools/_helpers.py` | Remove `write_sim_trade_log`, `read_sim_trade_log`, `_sim_cache`, `_sim_fs_key` |
| `optopsy/ui/tools/_executor.py` | Pass `dataset_fingerprint` for strategy/simulation tools |
| `optopsy/ui/tools/_results_manager.py` | Add `query_results` handler; update `get_simulation_trades` to use ResultStore |
| `optopsy/ui/tools/_models.py` | Add `QueryResultsArgs` Pydantic model |
| `optopsy/ui/tools/_schemas.py` | Add `query_results` tool schema |
| `optopsy/ui/agent.py` | Compute + cache dataset fingerprint; simplify results memo |
| `tests/` | Add tests for `ResultStore`, `query_results`, cache hit paths |

## Reusable Helpers

Shared helpers in `_helpers.py` to keep the cache integration DRY across `run_strategy`, `scan_strategies`, and `simulate`.

### `_cached_run()` — cache check/execute/write wrapper

The core caching pattern extracted into a single function. All three cacheable handlers use this instead of duplicating cache logic.

```python
def _cached_run(
    store: ResultStore,
    name: str,
    params: dict,
    dataset_fingerprint: str | None,
    execute_fn: Callable[[], tuple[pd.DataFrame | None, str]],
    metadata: dict,
) -> tuple[pd.DataFrame | None, str | None, str]:
    """Check ResultStore cache, execute on miss, write on miss.

    Returns (result_df, cache_key, error_str).
    """
    cache_key = (
        store.make_key(name, params, dataset_fingerprint)
        if dataset_fingerprint
        else None
    )

    if cache_key and store.has(cache_key):
        return store.read(cache_key), cache_key, ""

    df, err = execute_fn()
    if err:
        return None, cache_key, err

    if cache_key and df is not None and not df.empty:
        try:
            store.write(cache_key, df, metadata)
        except OSError:
            pass  # Non-fatal — result is still returned, just not cached

    return df, cache_key, ""
```

**Usage in `run_strategy`:**
```python
store = ResultStore()
ds_fp = _pop_internal_keys(strat_kwargs)
result_df, cache_key, err = _cached_run(
    store, strategy_name, strat_kwargs, ds_fp,
    execute_fn=lambda: _run_one_strategy(strategy_name, dataset, strat_kwargs),
    metadata={"type": "strategy", "strategy": strategy_name, ...},
)
```

**Usage in `simulate`:**
```python
result_df, cache_key, err = _cached_run(
    store, f"sim:{strategy_name}", all_params, ds_fp,
    execute_fn=lambda: _run_simulation(active_ds, func, sim_params, strat_kwargs),
    metadata={"type": "simulation", "strategy": strategy_name, "summary": s, ...},
)
```

### `_validate_strategy_and_dataset()` — deduplicate handler preamble

Both `run_strategy` and `simulate` repeat the same 12 lines of validation. Extract to:

```python
def _validate_strategy_and_dataset(
    arguments: dict,
    dataset: pd.DataFrame | None,
    datasets: dict,
    _result: Callable,
) -> tuple[str, Callable, pd.DataFrame, ToolResult | None]:
    """Validate strategy name and require active dataset.

    Returns (strategy_name, strategy_func, active_dataset, error_or_None).
    """
    strategy_name = arguments.get("strategy_name")
    if not strategy_name or strategy_name not in STRATEGIES:
        return "", None, None, _result(
            f"Unknown strategy '{strategy_name}'. "
            f"Available: {', '.join(STRATEGY_NAMES)}",
        )
    active_ds, _, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return "", None, None, err
    func, _, _ = STRATEGIES[strategy_name]
    return strategy_name, func, active_ds, None
```

### `_build_strat_kwargs()` — clean kwargs extraction

Both handlers strip signal keys and calendar extra params. Simulator also strips sim-specific keys. Unified:

```python
def _build_strat_kwargs(
    arguments: dict,
    strategy_name: str,
    extra_exclude: frozenset[str] = frozenset(),
) -> dict:
    """Build clean strategy kwargs, stripping non-strategy keys."""
    exclude = _SIGNAL_PARAM_KEYS | extra_exclude | {"dataset_name", "_dataset_fingerprint"}
    return {
        k: v
        for k, v in arguments.items()
        if k not in exclude
        and (strategy_name in CALENDAR_STRATEGIES or k not in CALENDAR_EXTRA_PARAMS)
    }
```

### `_pop_internal_keys()` — extract injected fingerprint

```python
def _pop_internal_keys(arguments: dict) -> str | None:
    """Pop and return _dataset_fingerprint from arguments dict."""
    return arguments.pop("_dataset_fingerprint", None)
```

### `_with_cache_key()` — attach cache key to result summary

```python
def _with_cache_key(summary: dict, cache_key: str | None) -> dict:
    """Add _cache_key to a result summary for later ResultStore lookups.

    Must be called before inserting the summary into agent.results so that
    query_results and get_simulation_trades can recover the parquet file
    via results[key]["_cache_key"].
    """
    if cache_key:
        summary["_cache_key"] = cache_key
    return summary
```

### Helper summary

| Helper | Location | Used by | Purpose |
|---|---|---|---|
| `_cached_run()` | `_helpers.py` | `run_strategy`, `scan_strategies`, `simulate` | Cache check → execute → cache write |
| `_validate_strategy_and_dataset()` | `_helpers.py` | `run_strategy`, `scan_strategies`, `simulate` | Strategy name + dataset validation |
| `_build_strat_kwargs()` | `_helpers.py` | `run_strategy`, `simulate` | Clean kwargs extraction |
| `_pop_internal_keys()` | `_helpers.py` | All cacheable handlers | Extract `_dataset_fingerprint` |
| `_with_cache_key()` | `_helpers.py` | `run_strategy`, `simulate` | Attach cache key to result entry |

## Step-by-Step

### 1. Create `ResultStore` (`optopsy/ui/providers/result_store.py`)

```python
class ResultStore:
    """Global parquet cache for result DataFrames (strategies + simulations).

    Keys are SHA-256 hashes of (name, params, dataset_fingerprint).
    A JSON index maps hashes to human-readable metadata.
    """

    def __init__(self, results_dir="~/.optopsy/results"): ...
    def make_key(name, arguments, dataset_fingerprint) -> str: ...
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

Computed once per dataset load. Reused for all subsequent strategy/simulation runs.

### 3. Pass fingerprint through executor

Add `dataset_fingerprint: str | None = None` to `execute_tool`. Inject into arguments for strategy and simulation tools only:

```python
_CACHEABLE_TOOLS = ("run_strategy", "scan_strategies", "simulate")

def execute_tool(..., dataset_fingerprint=None):
    ...
    if dataset_fingerprint and tool_name in _CACHEABLE_TOOLS:
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
    if cache_key and result_df is not None and not result_df.empty:
        store.write(cache_key, result_df, metadata={
            "type": "strategy",
            "strategy": strategy_name,
            "display_key": _make_result_key(strategy_name, arguments),
            "params": strat_kwargs,
        })
```

Then when building the results dict entry, attach the cache key so `query_results` can find the parquet file:

```python
summary = _make_result_summary(strategy_name, result_df, arguments)
updated_results = {
    **results,
    result_key: _with_cache_key(summary, cache_key),  # Adds {"_cache_key": "a3f8..."} to the entry
}
```

Same pattern for `scan_strategies` (cache the leaderboard).

### 5. Cache check in simulator

In `_handle_simulate`, before calling `_simulate`:

```python
store = ResultStore()
ds_fp = arguments.pop("_dataset_fingerprint", None)
all_params = {**sim_params, **strat_kwargs}
cache_key = store.make_key(f"sim:{strategy_name}", all_params, ds_fp) if ds_fp else None

if cache_key and store.has(cache_key):
    trade_log = store.read(cache_key)
    # Recover the 18 scalar summary metrics from _index.json metadata
    # instead of re-deriving from the trade log (avoids importing simulator internals).
    s = store.get_metadata(cache_key).get("summary", {})
else:
    result = _simulate(active_ds, func, **sim_params, **strat_kwargs)
    trade_log = result.trade_log
    s = result.summary
    if cache_key and not trade_log.empty:
        store.write(cache_key, trade_log, metadata={
            "type": "simulation",
            "strategy": strategy_name,
            "display_key": sim_key,
            "params": all_params,
            "summary": s,  # Store scalar summary alongside so cache hits don't need to re-derive
        })
```

### 6. Retire old simulator persistence

Remove from `_helpers.py`:
- `_sim_cache` (ParquetCache instance)
- `_SIM_CATEGORY`
- `_sim_fs_key()` (lossy sanitization)
- `write_sim_trade_log()`
- `read_sim_trade_log()`

Update `get_simulation_trades` in `_simulators.py` to read from ResultStore:

```python
cache_key = results[sim_key].get("_cache_key")
trade_log = ResultStore().read(cache_key) if cache_key else None
```

### 7. Add `query_results` tool

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
- Works for both strategy and simulation results — format-agnostic

Session's `agent.results` entries all carry `{"_cache_key": hash, ...}` so the handler can find any parquet file.

### 8. Simplify results memo in system prompt

Replace top-5 detailed memo (invalidates Anthropic prompt cache every call) with:

```
"Session has {N} strategy result(s). Use query_results to access full data."
```

Stable text reduces cache invalidation.

### 9. Update system prompt

Add to `## Workflow`:

```
- Use `query_results` to examine, sort, filter, or slice results from previous strategy
  runs or simulations without re-running them. This is the preferred way to answer
  follow-up questions about results.
- Strategy and simulation results are cached globally — if the same run with identical
  parameters has been done before on the same data, the cached result is returned instantly.
```

### 10. Update session resume message

```
"[Session resumed] In-memory datasets and signals were cleared.
Previous strategy and simulation results are still accessible via query_results."
```

### 11. Tests

- `ResultStore`: write/read round-trip, `make_key` determinism, `has()`, `list_all`, `clear`
- `query_results` handler: list mode, sort, filter, head/tail, missing key
- Strategy cache hit: `run_strategy` returns cached result without re-executing
- Simulation cache hit: `simulate` returns cached trade log without re-executing
- Content hash: same data → same fingerprint, different data → different fingerprint
- `get_simulation_trades` reads from ResultStore instead of old ParquetCache path

## Verification

1. `uv run pytest tests/ -v` — all existing + new tests pass
2. `uv run ruff check optopsy/ tests/` — no lint errors
3. Manual test flow:
   - Start chat, load data, run a strategy → result stored in global cache
   - Ask "sort the results by mean return descending" → LLM calls `query_results`
   - Run the same strategy again → instant cache hit, no recomputation
   - Run a simulation → trade log cached
   - Run same simulation again → instant cache hit
   - New session, load same data, run same strategy → cache hit across sessions
   - Reload page (session resume) → `query_results` still works for both types
