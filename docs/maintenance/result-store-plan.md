# Plan: Per-Session Result Store with Query Tool

Last updated: 2026-02-24

## Context

The LLM agent loses access to full strategy result data after message compaction (300-char truncation). It only has scalar summaries (mean, std, win_rate), so it can't answer follow-up questions like "sort by returns" or "which bucket performed best." We need persistent, queryable result storage scoped per session.

## Approach

**Write at the app layer, read via a query tool.** This avoids changing all 15+ handler signatures.

- **Writing:** `app.py`'s `on_tool_call` callback already has access to `result._result_df`, `arguments`, and `thread_id`. It writes result DataFrames to disk after each strategy run.
- **Reading:** A new `query_results` tool reads from disk. It receives `thread_id` injected into arguments by `execute_tool` (only for this tool).

## Files to Change

| File | Change |
|---|---|
| `optopsy/ui/providers/result_store.py` | **New.** `ResultStore` class — parquet read/write scoped by thread_id |
| `optopsy/ui/app.py` | Write results to `ResultStore` in `on_tool_call`; update resume message |
| `optopsy/ui/tools/_executor.py` | Add `thread_id` param to `execute_tool`; inject into args for `query_results` only |
| `optopsy/ui/tools/_results_manager.py` | Add `query_results` handler |
| `optopsy/ui/tools/_models.py` | Add `QueryResultsArgs` Pydantic model |
| `optopsy/ui/tools/_schemas.py` | Add `query_results` tool schema |
| `optopsy/ui/agent.py` | Add `thread_id` attr; pass to `execute_tool`; simplify results memo |
| `tests/` | Add tests for `ResultStore` and `query_results` |

## Step-by-Step

### 1. Create `ResultStore` (`optopsy/ui/providers/result_store.py`)

New class mirroring `ParquetCache` API but scoped by thread_id:

```
~/.optopsy/results/{thread_id}/{sanitized_result_key}.parquet
```

Methods:
- `write(thread_id, result_key, df)` — persist DataFrame
- `read(thread_id, result_key)` — load DataFrame or None
- `list_keys(thread_id)` — enumerate stored result keys
- `clear_thread(thread_id)` — delete all results for a session
- `_sanitize_key(key)` — filesystem-safe key (colons, commas → underscores)

Key mapping challenge: `_sanitize_key` is one-way (`"long_calls:dte=45,exit=0"` → `"long_calls_dte_45_exit_0"`). Store a `_manifest.json` mapping sanitized filenames back to original result keys.

### 2. Wire up writing in `app.py`

In `on_tool_call`, after the existing strategy tracking block (line 758-762), persist to ResultStore:

```python
if tool_name in ("run_strategy", "scan_strategies") and hasattr(result, "_result_df") and result._result_df is not None:
    from optopsy.ui.providers.result_store import ResultStore
    from optopsy.ui.tools._helpers import _make_result_key
    thread_id = cl.context.session.thread_id
    if tool_name == "run_strategy":
        key = _make_result_key(arguments.get("strategy_name", ""), arguments)
    else:
        key = "_scan_leaderboard"
    ResultStore().write(thread_id, key, result._result_df)
```

No handler signature changes needed for writing.

### 3. Add `thread_id` to `execute_tool` (minimal change)

Add `thread_id: str | None = None` parameter. Only inject it for tools that need it:

```python
def execute_tool(tool_name, arguments, dataset, signals, datasets, results, thread_id=None):
    ...
    # Inject thread_id for tools that need session-scoped storage
    if thread_id and tool_name in ("query_results",):
        arguments = {**arguments, "_thread_id": thread_id}
    ...
```

No handler signature changes. `query_results` extracts `_thread_id` from arguments.

### 4. Thread `thread_id` through `agent.py`

- Add `self.thread_id: str | None = None` to `OptopsyAgent.__init__`
- In `chat()`, pass `self.thread_id` to `execute_tool` via `functools.partial`
- Set `agent.thread_id` in `app.py`'s `on_chat_start` and `on_chat_resume`

### 5. Add `query_results` tool

**Schema** (`_schemas.py`): description explaining it queries stored result data.

**Model** (`_models.py`):
- `result_key: str | None` — omit to list available keys
- `sort_by: str | None` — column to sort by
- `ascending: bool = False`
- `head: int | None` — first N rows
- `filter_column: str | None` + `filter_op` + `filter_value` — basic filtering
- `columns: list[str] | None` — select specific columns

**Handler** (`_results_manager.py`):
- If no `result_key`: list available keys with scalar summaries from `results` dict
- If `result_key`: read from ResultStore, apply sort/filter/slice, return markdown table to LLM
- LLM gets full data (up to 50 rows) so it can answer follow-up questions

### 6. Simplify results memo in system prompt

Replace the top-5 detailed memo (which invalidates Anthropic prompt cache every call) with:

```
"Session has {N} strategy result(s). Use query_results to access full data."
```

This is stable across runs (only count changes), reducing cache invalidation.

### 7. Update system prompt

Add to the `## Workflow` section:

```
- Use `query_results` to examine, sort, filter, or slice results from previous strategy
  runs without re-running them. This is the preferred way to answer follow-up questions
  about results.
```

### 8. Update session resume message

Change the resume message to note results ARE still accessible:

```
"[Session resumed] In-memory datasets and signals were cleared.
Previous strategy results are still accessible via query_results."
```

### 9. Tests

- `ResultStore`: write/read round-trip, list_keys, clear_thread, manifest mapping
- `query_results` handler: list mode, sort, filter, head/tail, missing key error
- Integration: run_strategy writes to store, query_results reads it back

## Verification

1. `uv run pytest tests/ -v` — all existing + new tests pass
2. `uv run ruff check optopsy/ tests/` — no lint errors
3. Manual test flow:
   - Start chat, run a strategy
   - Ask "sort the results by mean return descending" → LLM calls `query_results`
   - Reload page (session resume) → ask about results → still accessible
   - Run `query_results` with no args → lists all stored results
