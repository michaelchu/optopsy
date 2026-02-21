# Optopsy Code Review

## 1. Pandas Performance & Optimization (HIGH PRIORITY)

### 🟡 1.1 — Repeated string operations in `_calls()` / `_puts()`

**File:** `optopsy/core.py:364-371`

**Problem:** `_calls()` and `_puts()` apply `.str.lower().str.startswith()` on every call. In a multi-leg strategy (e.g., iron condor with 4 legs), this runs 4 times on the same column. Each `.str` accessor creates temporary Series objects and iterates element-wise.

**Risk:** Moderate — these are called in the inner loop of every strategy. On a 500K-row dataset with a 4-leg strategy, that's ~2M string operations that could be replaced with a single pre-lowered column.

**Fix:**

```python
# core.py — normalize once when entering the pipeline
def _process_strategy(data: pd.DataFrame, **context: Any) -> pd.DataFrame:
    _run_checks(context["params"], data)
    data = data.copy()
    data["quote_date"] = normalize_dates(data["quote_date"])
    data["expiration"] = normalize_dates(data["expiration"])
    # Normalize option_type once here:
    data["option_type"] = data["option_type"].str.lower()
    ...

# Then simplify the filters:
def _calls(data: pd.DataFrame) -> pd.DataFrame:
    return data[data["option_type"].str.startswith("c")]

def _puts(data: pd.DataFrame) -> pd.DataFrame:
    return data[data["option_type"].str.startswith("p")]
```

Even better — if option_type values are always "call"/"put" (or "c"/"p"), use equality:

```python
def _calls(data: pd.DataFrame) -> pd.DataFrame:
    return data[data["option_type"] == "call"]
```

---

### 🟡 1.2 — `csv_data()` reads all columns then discards

**File:** `optopsy/datafeeds.py:170`

**Problem:** `pd.read_csv(file_path)` reads every column into memory, then `_trim_cols` selects a subset via `.iloc`. For wide CSVs (e.g., CBOE data with 30+ columns), this wastes memory and I/O.

**Risk:** Low-medium — depends on CSV width. For the typical 8-12 column files it's fine, but for provider files with many extra columns it matters.

**Fix:**

```python
# Compute usecols from the column_mapping before reading
col_indices = sorted(c for c, _ in column_mapping if c is not None)
return (
    pd.read_csv(file_path, usecols=col_indices)
    .pipe(_standardize_cols, column_mapping)
    # _trim_cols is now redundant since we only read needed columns
    .pipe(_infer_date_cols)
    .pipe(_trim_dates, params["start_date"], params["end_date"])
)
```

---

### 🟡 1.3 — Mid-price always computed even when overridden by slippage

**File:** `optopsy/core.py:307-315`

**Problem:** `_evaluate_options` always computes `entry = (bid_entry + ask_entry) / 2` and `exit = (bid_exit + ask_exit) / 2` via `.assign()`. Then `_apply_ratios` recalculates fill prices from bid/ask when `slippage != "mid"`, discarding the work.

**Risk:** Low — the wasted computation is two vectorized additions per DataFrame, which is fast. But it's conceptual overhead and could confuse maintainers.

**Fix:** Move the mid-price calculation into `_apply_ratios` (or `_strategy_engine`) so it's only done when actually needed. This is a larger refactor so consider it a "nice to have" rather than urgent.

---

### 🟡 1.4 — `suggest_strategy_params` copies entire dataset

**File:** `optopsy/ui/tools/_executor.py:203`

**Problem:** `df = active_ds.copy()` creates a full copy of the dataset just to compute DTE and OTM% statistics. On a 1M-row dataset this is a significant allocation.

**Fix:**

```python
# Only compute on the columns we need, no full copy
dte_series = (
    pd.to_datetime(active_ds["expiration"]) - pd.to_datetime(active_ds["quote_date"])
).dt.days.dropna()

mask = active_ds["underlying_price"] > 0
otm_series = (
    (active_ds.loc[mask, "strike"] - active_ds.loc[mask, "underlying_price"]).abs()
    / active_ds.loc[mask, "underlying_price"]
).dropna()
```

---

### 🟢 1.5 — Python loop over groupby groups in signals

**File:** `optopsy/signals.py:90-99`

**Problem:** `_per_symbol_signal` uses `for _symbol, group in data.groupby(...)` with Python-level iteration. For single-symbol datasets (the common case), this is fine. For multi-symbol, each group creates a slice, runs the indicator, and writes back via `.loc`.

**Risk:** Low — this is correct and readable. The indicators themselves (pandas_ta) are the bottleneck, not the loop overhead. Only becomes an issue with 100+ symbols.

**No fix needed** — the pattern is acceptable for the use case.

---

## 2. Bug Potential

### 🔴 2.1 — Global `pd.set_option` side effects on import

**File:** `optopsy/core.py:8-9`

```python
pd.set_option("expand_frame_repr", False)
pd.set_option("display.max_rows", None, "display.max_columns", None)
```

**Problem:** These execute at import time and modify global pandas display settings for the entire Python process. Any code that `import optopsy` — including the user's own scripts, notebooks, or the Chainlit web app — gets these display defaults silently changed.

**Risk:** High for a library. Users may be confused when their DataFrame `repr()` suddenly shows all rows/columns. This is a well-known anti-pattern in library code.

**Fix:** Remove these lines entirely. They were likely added for development convenience but should not ship in a library. If they're needed for the chat UI, set them in `app.py` instead.

```python
# Delete lines 8-9 from core.py entirely
```

---

### 🟡 2.2 — `_check_positive_integer` checks value before type

**File:** `optopsy/checks.py:113`

```python
def _check_positive_integer(key: str, value: Any) -> None:
    if value <= 0 or not isinstance(value, int):
        raise ValueError(...)
```

**Problem:** If `value` is a type that doesn't support `<=` with `0` (e.g., a string), this raises a `TypeError` instead of the intended `ValueError`. The `isinstance` check should come first.

**Risk:** Low in practice — the UI layer validates types before passing to strategies. But it's defensive-coding 101.

**Fix:**

```python
def _check_positive_integer(key: str, value: Any) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"Invalid setting for {key}, must be positive integer")
```

Same issue exists in `_check_positive_integer_inclusive` (line 119) and `_check_positive_float` (line 125).

---

### 🟡 2.3 — Bollinger Band column name depends on float formatting

**File:** `optopsy/signals.py:295`

```python
band_col = f"BBU_{length}_{std}_{std}"
```

**Problem:** `std` is a float. If `std=2.0`, this produces `"BBU_20_2.0_2.0"` — which matches pandas_ta's naming convention. But if someone passes `std=2` (int), it produces `"BBU_20_2_2"` which won't match the DataFrame column, causing a `KeyError`.

**Risk:** Medium — the `_bb_signal` function does `std = float(std)` on line 293, so `2` becomes `2.0`. But if pandas_ta changes its column naming (e.g., to strip trailing `.0`), this breaks silently.

**Fix:** The current `float()` cast on line 293 mitigates this. Add a comment explaining the coupling:

```python
# pandas_ta names BB columns as BBU_{length}_{std}_{std} where std is a float.
# The float() cast ensures we match this format.
```

---

### 🟡 2.4 — `_infer_date_cols` mutates the input DataFrame

**File:** `optopsy/datafeeds.py:59-72`

**Problem:** `_infer_date_cols` modifies `data["expiration"]` and `data["quote_date"]` in place, which is only safe because it's called in a pipe chain where `data` is a fresh DataFrame from `read_csv`. But if someone called it on a user's DataFrame, it would mutate their original.

**Risk:** Low — the function is private and only called in the pipe chain. But the convention in this codebase is to use `.assign()` or `.copy()` for safety.

**No urgent fix needed** — just be aware if refactoring.

---

## 3. Code Quality

### 🟢 3.1 — Inconsistent type annotations

**File:** Multiple files

**Problem:** `core.py`, `strategies.py`, `datafeeds.py`, and `checks.py` use `from typing import Dict, List, Optional, Tuple` (old-style), while `signals.py` and the `ui/` layer use `dict`, `list`, `tuple`, `X | None` (modern PEP 604/585 style).

**Risk:** None — both work. But inconsistency makes the codebase harder to skim.

**Fix:** When touching these files for other reasons, modernize to PEP 604 style (`dict`, `list`, `X | None`). Not worth a standalone PR.

---

### 🟢 3.2 — `Side` enum could live in `types.py`

**File:** `optopsy/strategies.py:68-72`

**Problem:** The `Side` enum is defined in `strategies.py` but conceptually belongs with the other type definitions in `types.py`. It's referenced via leg definitions passed to `core.py`.

**Risk:** None — this is organizational only.

---

## 4. DRY (Don't Repeat Yourself)

### 🟡 4.1 — Strategy helper functions are formulaic

**File:** `optopsy/strategies.py:75-127`

**Problem:** `_singles`, `_straddles`, `_strangles`, `_spread`, `_butterfly`, `_iron_condor`, `_iron_butterfly`, `_covered_call`, `_calendar_spread` — all 9 helpers follow the exact same pattern:

```python
def _helper(data, leg_def, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(data, internal_cols=..., external_cols=...,
                             leg_def=leg_def, rules=..., join_on=..., params=params)
```

**Risk:** Low — the repetition is annoying but not dangerous. Each helper is ~5 lines. A data-driven approach would reduce this to a single generic function + a config dict.

**Fix (optional):**

```python
_STRATEGY_CONFIG = {
    "singles": {
        "internal_cols": single_strike_internal_cols,
        "external_cols": single_strike_external_cols,
    },
    "straddles": {
        "internal_cols": straddle_internal_cols,
        "external_cols": single_strike_external_cols,
        "join_on": ["underlying_symbol", "expiration", "strike", "dte_entry", ...],
    },
    # ...
}

def _run_strategy(config_key, data, leg_def, **kwargs):
    config = _STRATEGY_CONFIG[config_key]
    params = {**default_kwargs, **kwargs}
    return _process_strategy(data, **config, leg_def=leg_def, params=params)
```

This eliminates ~50 lines of boilerplate. But it trades explicitness for indirection — a judgment call.

---

### 🟡 4.2 — Dataset resolution pattern repeated in `_executor.py`

**File:** `optopsy/ui/tools/_executor.py` — lines 174, 193, 315, 520, 705

**Problem:** This exact block appears 5 times:

```python
ds_name = arguments.get("dataset_name")
active_ds = _resolve_dataset(ds_name, dataset, datasets)
if active_ds is None:
    if datasets:
        return _result(f"Dataset '{ds_name}' not found. Available: ...")
    return _result("No dataset loaded. Load data first.")
```

**Fix:** Extract a helper:

```python
def _require_dataset(arguments, dataset, datasets, _result):
    ds_name = arguments.get("dataset_name")
    active_ds = _resolve_dataset(ds_name, dataset, datasets)
    if active_ds is not None:
        return active_ds, ds_name, None
    if datasets:
        return None, ds_name, _result(
            f"Dataset '{ds_name}' not found. Available: {list(datasets.keys())}"
        )
    return None, ds_name, _result("No dataset loaded. Load data first.")
```

---

## 5. Architecture & Maintainability

### 🔴 5.1 — `execute_tool` is a 989-line monolithic function

**File:** `optopsy/ui/tools/_executor.py:49-989`

**Problem:** A single function handles all 11+ tool calls via `if tool_name == "..."` chains. This is the biggest maintainability concern in the codebase. Each tool branch is 30-100 lines with its own local variables, early returns, and state mutations. Adding a new tool requires reading through the entire function to understand where to insert code.

**Risk:** High for maintainability. Merge conflicts when modifying concurrent tools. Hard to test individual tools in isolation.

**Fix:** Use a registry pattern:

```python
_TOOL_HANDLERS: dict[str, Callable] = {}

def _register(name: str):
    def decorator(fn):
        _TOOL_HANDLERS[name] = fn
        return fn
    return decorator

@_register("load_csv_data")
def _handle_load_csv(arguments, dataset, signals, datasets, results, _result):
    ...

@_register("preview_data")
def _handle_preview(arguments, dataset, signals, datasets, results, _result):
    ...

def execute_tool(tool_name, arguments, dataset, signals=None, datasets=None, results=None):
    # ... setup ...
    handler = _TOOL_HANDLERS.get(tool_name)
    if handler:
        return handler(arguments, dataset, signals, datasets, results, _result)
    # fall through to provider dispatch, then unknown tool
```

This splits the monolith into ~11 focused functions of 30-80 lines each, all independently testable.

---

### 🟡 5.2 — `eodhd.py` imports `yfinance` at module level

**File:** `optopsy/ui/providers/eodhd.py:11`

```python
import yfinance as yf
```

**Problem:** The EODHD provider imports `yfinance` unconditionally at the top level. If a user has configured an EODHD API key but hasn't installed yfinance, the import of `eodhd.py` fails, preventing EODHD from loading at all.

**Risk:** Medium — the EODHD provider uses yfinance for underlying stock price lookups, but the core options functionality doesn't require it.

**Fix:** Lazy-import yfinance where it's used (as is already done in `_helpers.py:76`):

```python
# Remove top-level import
# Import lazily where needed:
try:
    import yfinance as yf
except ImportError:
    yf = None
```

---

### 🟢 5.3 — `SYSTEM_PROMPT` is 277 lines embedded in `agent.py`

**File:** `optopsy/ui/agent.py:12-277`

**Problem:** The system prompt is a massive string literal embedded in the agent module. Changes to tool documentation, strategy lists, or signal instructions require editing `agent.py`.

**Risk:** Low — it works fine. But extracting it to a separate file (e.g., `prompts.py` or `system_prompt.md`) would improve readability.

---

## 6. General Performance

### 🟡 6.1 — `_find_calendar_exit_prices` tolerance loop is Python-level

**File:** `optopsy/core.py:832-837`

```python
date_map = {}
for target_date in all_exit_dates:
    diffs = np.abs(available_dates - target_date)
    min_idx = diffs.argmin()
    if diffs[min_idx] <= tolerance_td:
        date_map[target_date] = available_dates[min_idx]
```

**Problem:** This is a Python loop over exit dates doing NumPy operations. For small exit date counts (typical), this is fine.

**Risk:** Low — `all_exit_dates` is typically <100 unique dates. The NumPy operations inside the loop are vectorized over `available_dates`.

**No fix needed** unless profiling shows this is a bottleneck.

---

### 🟡 6.2 — `_strategy_engine` copies leg DataFrames redundantly

**File:** `optopsy/core.py:570-573`

```python
partials = [
    _rename_leg_columns(leg[1](data).copy(), idx, join_on or [])
    for idx, leg in enumerate(leg_def, start=1)
]
```

**Problem:** For a 4-leg iron condor, this creates 4 explicit copies of the filtered DataFrame. But `_rename_leg_columns` calls `.rename()` which already returns a new DataFrame, making the `.copy()` redundant.

**Fix:** Remove the `.copy()`:

```python
partials = [
    _rename_leg_columns(leg[1](data), idx, join_on or [])
    for idx, leg in enumerate(leg_def, start=1)
]
```

---

## 7. Testing Gaps

### 🟡 7.1 — No tests for `_executor.py` tool dispatch

**File:** `optopsy/ui/tools/_executor.py`

**Problem:** The 989-line `execute_tool` function has no unit tests. The test suite covers strategies, signals, checks, rules, datafeeds, cache, timestamps, and CLI — but the tool dispatch layer that glues everything together for the chat UI is untested.

**Risk:** Medium — this is the most complex integration point in the codebase. Regressions in dataset resolution, signal slot management, or result registry are only caught by manual testing.

**Fix:** Add a `tests/test_executor.py` with unit tests for each tool branch:

```python
def test_preview_data_no_dataset():
    result = execute_tool("preview_data", {}, dataset=None)
    assert "No dataset loaded" in result.llm_summary

def test_run_strategy_returns_results():
    df = make_test_options_data()
    result = execute_tool("run_strategy", {"strategy_name": "long_calls"}, dataset=df)
    assert result.results  # should populate the registry
```

---

### 🟡 7.2 — No tests for `agent.py` chat loop

**File:** `optopsy/ui/agent.py`

**Problem:** The `OptopsyAgent.chat()` method — including the streaming loop, message compaction, retry logic, and state management — has no tests.

**Risk:** Medium — the `_compact_history` function (which truncates old messages) is especially tricky and could corrupt message history if it has off-by-one errors.

**Fix:** At minimum, test `_compact_history` as a unit:

```python
def test_compact_history_preserves_last_tool_result():
    messages = [
        {"role": "assistant", "content": "thinking...", "tool_calls": [{"id": "1"}]},
        {"role": "tool", "content": "A" * 500, "tool_call_id": "1"},
        {"role": "assistant", "content": "more thinking...", "tool_calls": [{"id": "2"}]},
        {"role": "tool", "content": "B" * 500, "tool_call_id": "2"},
    ]
    _compact_history(messages)
    assert "[truncated]" in messages[1]["content"]  # old tool result truncated
    assert messages[3]["content"] == "B" * 500       # latest preserved
```

---

### 🟢 7.3 — Edge case: empty DataFrame through strategy pipeline

**Problem:** Several strategy pipelines assume the DataFrame is non-empty at various stages. The `_format_output` / `_format_calendar_output` functions handle empty DataFrames, but intermediate steps (e.g., `_cut_options_by_dte`, `_group_by_intervals`) don't always guard against empty input.

**Risk:** Low — pandas operations on empty DataFrames generally return empty DataFrames without errors. But explicit tests confirming empty-input behavior for each strategy would increase confidence.

---

## Overall Health Summary

**The codebase is in good shape for a personal project.** The core strategy engine (`core.py`) is well-structured with a clean pipeline architecture. The signal system is elegantly decoupled. The caching layer is thoughtful (gap detection, dedup). Test coverage for the library layer is solid with dedicated test files for strategies, signals, checks, rules, datafeeds, cache, timestamps, and CLI.

### Top 3 Action Items

1. **Remove `pd.set_option` from `core.py`** (🔴 — 2-line delete, prevents silent side effects for all importers)
2. **Refactor `_executor.py` into a registry pattern** (🔴 — biggest maintainability win, enables testability)
3. **Pre-lowercase `option_type` in `_process_strategy`** (🟡 — simple performance win for multi-leg strategies)

### Strengths

- Clean functional pipeline in `core.py` using `.pipe()` chains
- Well-designed caching with incremental gap fetching
- Comprehensive strategy coverage (28 strategies, all tested)
- Good separation of concerns: signals, strategies, data providers
- Dual LLM/user display pattern in `ToolResult` is a smart token-saving design
- Solid test infrastructure with well-designed fixtures

### Areas for Improvement

- The `_executor.py` monolith is the main drag on maintainability
- Missing test coverage for the UI integration layer (`execute_tool`, `agent.py`)
- Minor pandas performance wins available in the hot path
