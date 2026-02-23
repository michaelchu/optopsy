# Optopsy Code Review

## 1. Pandas Performance & Optimization (HIGH PRIORITY)

### ✅ 1.1 — Repeated string operations in `_calls()` / `_puts()`

**File:** `optopsy/core.py:364-371`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** `_calls()` and `_puts()` apply `.str.lower().str.startswith()` on every call. In a multi-leg strategy (e.g., iron condor with 4 legs), this runs 4 times on the same column. Each `.str` accessor creates temporary Series objects and iterates element-wise.

**Risk:** Moderate — these are called in the inner loop of every strategy. On a 500K-row dataset with a 4-leg strategy, that's ~2M string operations that could be replaced with a single pre-lowered column.

**What was done:** `option_type` is now normalized once with `.str.lower()` in both `_process_strategy()` and `_process_calendar_strategy()`. The `_calls()` and `_puts()` functions now use only `.str.startswith("c"/"p")` without the redundant `.str.lower()`.

---

### ✅ 1.2 — `csv_data()` reads all columns then discards

**File:** `optopsy/datafeeds.py:170`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** `pd.read_csv(file_path)` reads every column into memory, then `_trim_cols` selects a subset via `.iloc`. For wide CSVs (e.g., CBOE data with 30+ columns), this wastes memory and I/O.

**Risk:** Low-medium — depends on CSV width. For the typical 8-12 column files it's fine, but for provider files with many extra columns it matters.

**What was done:** `csv_data()` now computes `col_indices` from `column_mapping` and passes `usecols=col_indices` to `pd.read_csv()`. The `_trim_cols` pipe step was removed since it's no longer needed.

---

### 🟡 1.3 — Mid-price always computed even when overridden by slippage

**File:** `optopsy/core.py:307-315`
**Status:** **NOT ADDRESSED** — Deferred as "nice to have"; low-risk, larger refactor.

**Problem:** `_evaluate_options` always computes `entry = (bid_entry + ask_entry) / 2` and `exit = (bid_exit + ask_exit) / 2` via `.assign()`. Then `_apply_ratios` recalculates fill prices from bid/ask when `slippage != "mid"`, discarding the work.

**Risk:** Low — the wasted computation is two vectorized additions per DataFrame, which is fast. But it's conceptual overhead and could confuse maintainers.

**Fix:** Move the mid-price calculation into `_apply_ratios` (or `_strategy_engine`) so it's only done when actually needed. This is a larger refactor so consider it a "nice to have" rather than urgent.

---

### ✅ 1.4 — `suggest_strategy_params` copies entire dataset

**File:** `optopsy/ui/tools/_executor.py:203`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** `df = active_ds.copy()` creates a full copy of the dataset just to compute DTE and OTM% statistics. On a 1M-row dataset this is a significant allocation.

**What was done:** The full `.copy()` was replaced with targeted series computations — `dte_series` and `otm_series` are now computed directly from `active_ds` columns without copying the entire DataFrame.

---

### 🟢 1.5 — Python loop over groupby groups in signals

**File:** `optopsy/signals.py:90-99`

**Problem:** `_per_symbol_signal` uses `for _symbol, group in data.groupby(...)` with Python-level iteration. For single-symbol datasets (the common case), this is fine. For multi-symbol, each group creates a slice, runs the indicator, and writes back via `.loc`.

**Risk:** Low — this is correct and readable. The indicators themselves (pandas_ta) are the bottleneck, not the loop overhead. Only becomes an issue with 100+ symbols.

**No fix needed** — the pattern is acceptable for the use case.

---

## 2. Bug Potential

### ✅ 2.1 — `setup.py` UI packages separated from core

**File:** `setup.py`
**Status:** **COMPLETE** — Implemented across commits `95bd464` and subsequent update.

**Problem (original):** The hard-coded `packages` list did not include `"optopsy.ui.tools"`, causing the chat UI to crash with `ImportError` on non-editable installs.

**Problem (follow-up):** The initial fix (`find_packages(exclude=["tests", "tests.*", "samples"])`) bundled all UI subpackages (`optopsy.ui.tools`, `optopsy.ui.providers`) unconditionally, even for users who only install the core library. The `tools` and `providers` packages should conceptually only be installed when the user opts into the `[ui]` extra.

**Risk:** Critical (original); Medium (follow-up — unnecessary files shipped to core-only users).

**What was done:** Replaced the single `find_packages()` call with two explicit package lists:
- `_core_packages`: discovered via `find_packages(exclude=[..., "optopsy.ui", "optopsy.ui.*"])` — always installed.
- `_ui_packages`: explicitly listed (`optopsy.ui`, `optopsy.ui.tools`, `optopsy.ui.providers`) — conceptually tied to the `[ui]` extra.

Both lists are combined in `packages=_core_packages + _ui_packages`. This is because **setuptools `extras_require` only controls dependencies, not which packages are included in a wheel/sdist**. True conditional package exclusion would require splitting into a separate distribution (e.g., `optopsy-ui`). The current approach ensures `pip install optopsy[ui]` works correctly for both editable and non-editable installs, while clearly documenting the core/UI boundary. The `console_scripts` entry point is gated with `[ui]` so the `optopsy-chat` command is only registered when UI dependencies are present.

---

### ✅ 2.2 — Global `pd.set_option` side effects on import (library anti-pattern)

**File:** `optopsy/core.py:8-9`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** These execute at import time and modify global pandas display settings for the entire Python process. Any code that `import optopsy` — including the user's own scripts, notebooks, or the Chainlit web app — gets these display defaults silently changed.

**Risk:** High for a library. Users may be confused when their DataFrame `repr()` suddenly shows all rows/columns. This is a well-known anti-pattern in library code.

**What was done:** Both `pd.set_option` calls were removed from `core.py`.

---

### ✅ 2.3 — `_check_positive_integer` checks value before type

**File:** `optopsy/checks.py:113`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** If `value` is a type that doesn't support `<=` with `0` (e.g., a string), this raises a `TypeError` instead of the intended `ValueError`. The `isinstance` check should come first.

**Risk:** Low in practice — the UI layer validates types before passing to strategies. But it's defensive-coding 101.

**What was done:** Reordered the conditions in all three functions (`_check_positive_integer`, `_check_positive_integer_inclusive`, `_check_positive_float`) so `isinstance` is checked first, preventing `TypeError` on non-numeric input.

---

### ✅ 2.4 — Bollinger Band column name depends on float formatting

**File:** `optopsy/signals.py:295`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** `std` is a float. If `std=2.0`, this produces `"BBU_20_2.0_2.0"` — which matches pandas_ta's naming convention. But if someone passes `std=2` (int), it produces `"BBU_20_2_2"` which won't match the DataFrame column, causing a `KeyError`.

**Risk:** Medium — the `_bb_signal` function does `std = float(std)` on line 293, so `2` becomes `2.0`. But if pandas_ta changes its column naming (e.g., to strip trailing `.0`), this breaks silently.

**What was done:** Added a comment explaining the coupling between the `float()` cast and pandas_ta's column naming convention.

---

### 🟡 2.5 — `_infer_date_cols` mutates the input DataFrame

**File:** `optopsy/datafeeds.py:59-72`

**Problem:** `_infer_date_cols` modifies `data["expiration"]` and `data["quote_date"]` in place, which is only safe because it's called in a pipe chain where `data` is a fresh DataFrame from `read_csv`. But if someone called it on a user's DataFrame, it would mutate their original.

**Risk:** Low — the function is private and only called in the pipe chain. But the convention in this codebase is to use `.assign()` or `.copy()` for safety.

**No urgent fix needed** — just be aware if refactoring.

---

## 3. Code Quality

### 🟢 3.1 — Inconsistent type annotations

**File:** Multiple files
**Status:** **NOT ADDRESSED** — Low priority, opportunistic fix when touching these files.

**Problem:** `core.py`, `strategies.py`, `datafeeds.py`, and `checks.py` use `from typing import Dict, List, Optional, Tuple` (old-style), while `signals.py` and the `ui/` layer use `dict`, `list`, `tuple`, `X | None` (modern PEP 604/585 style).

**Risk:** None — both work. But inconsistency makes the codebase harder to skim.

**Fix:** When touching these files for other reasons, modernize to PEP 604 style (`dict`, `list`, `X | None`). Not worth a standalone PR.

---

### 🟢 3.2 — `Side` enum could live in `types.py`

**File:** `optopsy/strategies.py:68-72`
**Status:** **NOT ADDRESSED** — Organizational only, no functional impact.

**Problem:** The `Side` enum is defined in `strategies.py` but conceptually belongs with the other type definitions in `types.py`. It's referenced via leg definitions passed to `core.py`.

**Risk:** None — this is organizational only.

---

## 4. DRY (Don't Repeat Yourself)

### 🟡 4.1 — Strategy helper functions are formulaic

**File:** `optopsy/strategies.py:75-127`
**Status:** **NOT ADDRESSED** — Optional refactor, trades explicitness for indirection.

**Problem:** `_singles`, `_straddles`, `_strangles`, `_spread`, `_butterfly`, `_iron_condor`, `_iron_butterfly`, `_covered_call`, `_calendar_spread` — all 9 helpers follow the exact same pattern:

```python
def _helper(data, leg_def, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(data, internal_cols=..., external_cols=...,
                             leg_def=leg_def, rules=..., join_on=..., params=params)
```

**Risk:** Low — the repetition is annoying but not dangerous. Each helper is ~5 lines. A data-driven approach would reduce this to a single generic function + a config dict, but trades explicitness for indirection.

---

### ✅ 4.2 — Dataset resolution pattern repeated in `_executor.py`

**File:** `optopsy/ui/tools/_executor.py` — lines 174, 193, 315, 520, 705
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** This exact block appears 5 times:

```python
ds_name = arguments.get("dataset_name")
active_ds = _resolve_dataset(ds_name, dataset, datasets)
if active_ds is None:
    if datasets:
        return _result(f"Dataset '{ds_name}' not found. Available: ...")
    return _result("No dataset loaded. Load data first.")
```

**What was done:** Extracted a `_require_dataset()` helper that returns `(active_ds, ds_name, error_result)`. All 5 call sites now use this helper, eliminating the duplicated resolution logic.

---

## 5. Architecture & Maintainability

### ✅ 5.1 — `execute_tool` is a 989-line monolithic function

**File:** `optopsy/ui/tools/_executor.py:49-989`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** A single function handles all 11+ tool calls via `if tool_name == "..."` chains. This is the biggest maintainability concern in the codebase. Each tool branch is 30-100 lines with its own local variables, early returns, and state mutations. Adding a new tool requires reading through the entire function to understand where to insert code.

**Risk:** High for maintainability. Merge conflicts when modifying concurrent tools. Hard to test individual tools in isolation.

**What was done:** Refactored into a `_TOOL_HANDLERS` registry with a `@_register(name)` decorator pattern. Each tool is now its own function (e.g., `_handle_load_csv`, `_handle_preview_data`, `_handle_run_strategy`). The `execute_tool()` function dispatches via `_TOOL_HANDLERS.get(tool_name)` and falls through to provider dispatch for unregistered tools.

---

### ✅ 5.2 — `eodhd.py` imports `yfinance` at module level

**File:** `optopsy/ui/providers/eodhd.py:11`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** The EODHD provider imports `yfinance` unconditionally at the top level. If a user has configured an EODHD API key but hasn't installed yfinance, the import of `eodhd.py` fails, preventing EODHD from loading at all.

**Risk:** Medium — the EODHD provider uses yfinance for underlying stock price lookups, but the core options functionality doesn't require it.

**What was done:** Removed the top-level `import yfinance as yf`. Added a lazy `try/except ImportError` inside `_resolve_underlying_prices()` that logs a warning and sets `underlying_price` to `pd.NA` if yfinance is not installed.

---

### 🟢 5.3 — `SYSTEM_PROMPT` is 277 lines embedded in `agent.py`

**File:** `optopsy/ui/agent.py:12-277`
**Status:** **NOT ADDRESSED** — Low priority, cosmetic improvement.

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

### ✅ 6.2 — `_strategy_engine` copies leg DataFrames redundantly

**File:** `optopsy/core.py:570-573`
**Status:** **COMPLETE** — Implemented in commit `95bd464`.

**Problem:** For a 4-leg iron condor, this creates 4 explicit copies of the filtered DataFrame. But `_rename_leg_columns` calls `.rename()` which already returns a new DataFrame, making the `.copy()` redundant.

**What was done:** Removed the `.copy()` call from the list comprehension in `_strategy_engine`. Added a comment explaining why it's unnecessary (`.rename()` already returns a new DataFrame).

---

## 7. Testing Gaps

### 🟡 7.1 — No tests for `_executor.py` tool dispatch

**File:** `optopsy/ui/tools/_executor.py`
**Status:** **NOT ADDRESSED** — Still needs unit tests for the tool dispatch layer.

**Problem:** The `execute_tool` function (now refactored into registry handlers) has no unit tests. The test suite covers strategies, signals, checks, rules, datafeeds, cache, timestamps, and CLI — but the tool dispatch layer that glues everything together for the chat UI is untested.

**Risk:** Medium — this is the most complex integration point in the codebase. The registry refactor (5.1) makes individual handlers easier to test now.

**Fix:** Add a `tests/test_executor.py` with unit tests for each tool handler. The registry pattern now makes this straightforward since each handler is an independent function.

---

### 🟡 7.2 — No tests for `agent.py` chat loop

**File:** `optopsy/ui/agent.py`
**Status:** **NOT ADDRESSED** — Still needs unit tests, especially for `_compact_history`.

**Problem:** The `OptopsyAgent.chat()` method — including the streaming loop, message compaction, retry logic, and state management — has no tests.

**Risk:** Medium — the `_compact_history` function (which truncates old messages) is especially tricky and could corrupt message history if it has off-by-one errors.

**Fix:** At minimum, test `_compact_history` as a unit.

---

### 🟢 7.3 — Edge case: empty DataFrame through strategy pipeline

**Status:** **NOT ADDRESSED** — Low risk, nice-to-have test coverage.

**Problem:** Several strategy pipelines assume the DataFrame is non-empty at various stages. The `_format_output` / `_format_calendar_output` functions handle empty DataFrames, but intermediate steps (e.g., `_cut_options_by_dte`, `_group_by_intervals`) don't always guard against empty input.

**Risk:** Low — pandas operations on empty DataFrames generally return empty DataFrames without errors. But explicit tests confirming empty-input behavior for each strategy would increase confidence.

---

## Overall Health Summary

**The codebase is in good shape.** The core strategy engine (`core.py`) is well-structured with a clean pipeline architecture. The signal system is elegantly decoupled. The caching layer is thoughtful (gap detection, dedup). Test coverage for the library layer is solid with dedicated test files for strategies, signals, checks, rules, datafeeds, cache, timestamps, and CLI. All 197 tests pass.

### Implementation Progress

**12 of 19 items addressed** (3 critical, 5 moderate, 4 low-priority). The remaining 7 are low-priority or deferred by design.

| # | Item | Priority | Status |
|---|------|----------|--------|
| 1.1 | Pre-lowercase `option_type` | 🟡 | ✅ Done |
| 1.2 | `usecols` in `csv_data()` | 🟡 | ✅ Done |
| 1.3 | Mid-price computed unconditionally | 🟡 | Deferred |
| 1.4 | `suggest_strategy_params` copy | 🟡 | ✅ Done |
| 1.5 | Python loop in signals | 🟢 | N/A (acceptable) |
| 2.1 | `setup.py` UI packages separated | 🔴 | ✅ Done |
| 2.2 | `pd.set_option` side effects | 🔴 | ✅ Done |
| 2.3 | `isinstance` check order | 🟡 | ✅ Done |
| 2.4 | BB column name comment | 🟡 | ✅ Done |
| 2.5 | `_infer_date_cols` mutation | 🟡 | N/A (acceptable) |
| 3.1 | Inconsistent type annotations | 🟢 | Deferred |
| 3.2 | `Side` enum location | 🟢 | Deferred |
| 4.1 | Strategy helper DRY | 🟡 | Deferred |
| 4.2 | `_require_dataset` helper | 🟡 | ✅ Done |
| 5.1 | Registry pattern refactor | 🔴 | ✅ Done |
| 5.2 | Lazy-import yfinance | 🟡 | ✅ Done |
| 5.3 | Extract SYSTEM_PROMPT | 🟢 | Deferred |
| 6.1 | Calendar exit tolerance loop | 🟡 | N/A (acceptable) |
| 6.2 | Redundant `.copy()` in partials | 🟡 | ✅ Done |
| 7.1 | Tests for `_executor.py` | 🟡 | Open |
| 7.2 | Tests for `agent.py` | 🟡 | Open |
| 7.3 | Empty DataFrame edge cases | 🟢 | Open |

### Remaining Action Items

1. **Add unit tests for `_executor.py` tool handlers** (🟡 — the registry refactor makes this straightforward now)
2. **Add unit tests for `agent.py` `_compact_history`** (🟡 — high-risk function with no test coverage)
3. **Modernize type annotations** (🟢 — opportunistic, do when touching files)
4. **Mid-price refactor** (🟡 — larger refactor, low practical impact)

### Strengths

- Clean functional pipeline in `core.py` using `.pipe()` chains
- Well-designed caching with incremental gap fetching
- Comprehensive strategy coverage (28 strategies, all tested)
- Good separation of concerns: signals, strategies, data providers
- Dual LLM/user display pattern in `ToolResult` is a smart token-saving design
- Solid test infrastructure with well-designed fixtures
- `_executor.py` is now modular with registry pattern (was the top maintainability concern)

### Areas for Improvement

- Missing test coverage for the UI integration layer (`execute_tool` handlers, `agent.py`)
- Minor pandas performance wins still available (mid-price refactor)

---

## 8. Enhancement Roadmap Items 1–3: Code Review

Review of the implementations for Risk Metrics (item 1), IV Rank Signals (item 2), and Strategy Comparison Report (item 3) from `docs/ideas/ai-agent-enhancement-roadmap.md`.

### 8.1 — Risk Metrics (`metrics.py`, `simulator.py`, `core.py`)

**Overall assessment:** Well-structured, well-tested, clean separation of concerns.

#### 8.1.1 — DRY: Profit factor reimplemented in 3 places

**Files:**
- `optopsy/metrics.py:182-203` — canonical `profit_factor()` function
- `optopsy/simulator.py:463-467` — inline reimplementation in `_compute_summary()`
- `optopsy/ui/tools/_helpers.py:440-446` — inline reimplementation in `_make_result_summary()`

**Problem:** The simulator computes profit factor inline:

```python
# simulator.py:463-467
"profit_factor": (
    abs(total_wins / total_losses)
    if total_losses != 0
    else (float("inf") if total_wins > 0 else 0.0)
),
```

And `_make_result_summary` does the same:

```python
# _helpers.py:440-446
if losses == 0:
    pf = float("inf") if wins > 0 else 0.0
else:
    pf = abs(wins) / abs(losses)
```

Both duplicate the exact logic from `metrics.profit_factor()`. The simulator already imports from `metrics` (sharpe, sortino, VaR, CVaR, calmar, max_drawdown) but skips `profit_factor` and `win_rate`.

**Fix:** Import and call `metrics.profit_factor(pnl)` in `_compute_summary()`. In `_make_result_summary()`, call `metrics.profit_factor(pct)` for raw-mode results. For aggregated-mode results (lines 469-479), the group-level aggregation logic is different enough to justify keeping it separate, but add a comment explaining why.

#### 8.1.2 — DRY: Win rate reimplemented in 3 places

**Files:**
- `optopsy/metrics.py:167-179` — canonical `win_rate()` function
- `optopsy/simulator.py:455` — inline: `len(wins) / len(trade_log)`
- `optopsy/ui/tools/_helpers.py:452` — inline: `float((pct > 0).mean())`

**Problem:** Same pattern as profit factor. Three independent calculations of the same metric.

**Fix:** Use `metrics.win_rate()` in both `_compute_summary()` and `_make_result_summary()`.

#### 8.1.3 — `_compute_summary` selectively imports from metrics

**File:** `optopsy/simulator.py:375-384`

**Problem:** The function imports `sharpe_ratio`, `sortino_ratio`, `value_at_risk`, `conditional_value_at_risk`, `calmar_ratio`, and `max_drawdown` from `metrics` — but manually computes `win_rate` (line 455) and `profit_factor` (lines 463-467). This inconsistency makes the code harder to reason about: a reader sees the imports and assumes all metrics come from the module, then finds inline reimplementations.

**Fix:** Import `win_rate` and `profit_factor` from `metrics` and use them. The `_compute_summary` function can then be simplified to ~10 fewer lines with no logic duplication.

#### 8.1.4 — `_fmt_pf` utility could live in a shared location

**File:** `optopsy/ui/tools/_executor.py:73-79`

**Observation:** The `_fmt_pf()` helper formats profit factor for display (handling infinity and NaN). It's used by both `_handle_simulate` and `_handle_compare_results` in the same file, so this is fine for now. But if profit_factor formatting is needed elsewhere (e.g., future tools), consider moving it to `_helpers.py`.

---

### 8.2 — IV Rank Signals (`signals.py`, `eodhd.py`, `core.py`)

**Overall assessment:** Good design — conditional passthrough, per-strike preservation, signal incompatibility checks are all well thought out. The main issue is duplication in the signal functions themselves and in the executor's signal resolution logic.

#### 8.2.1 — DRY: `iv_rank_above` and `iv_rank_below` are near-identical (HIGH)

**File:** `optopsy/signals.py:613-693`

**Problem:** These two functions are ~40 lines each and differ by exactly one character: `>` vs `<` on the comparison line. The entire body — checking for `implied_volatility` column, computing ATM IV, computing rank, building the MultiIndex lookup, mapping rank back to original rows — is identical.

Compare:
- `iv_rank_above` line 649: `return (iv_rank_for_rows > threshold).fillna(False)`
- `iv_rank_below` line 690: `return (iv_rank_for_rows < threshold).fillna(False)`

**Fix:** Extract a `_iv_rank_signal(threshold, window, compare_op)` factory:

```python
def _iv_rank_signal(threshold: float, window: int, compare_op) -> SignalFunc:
    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        if "implied_volatility" not in data.columns:
            return pd.Series(False, index=data.index)
        atm_iv = _compute_atm_iv(data)
        if atm_iv.empty:
            return pd.Series(False, index=data.index)
        rank = _compute_iv_rank_series(atm_iv, window)
        rank_lookup = pd.Series(
            rank.values,
            index=pd.MultiIndex.from_arrays(
                [atm_iv["underlying_symbol"], atm_iv["quote_date"]]
            ),
        )
        keys = pd.MultiIndex.from_arrays(
            [data["underlying_symbol"], data["quote_date"]]
        )
        iv_rank_for_rows = pd.Series(rank_lookup.reindex(keys).values, index=data.index)
        return compare_op(iv_rank_for_rows, threshold).fillna(False)
    _signal.requires_per_strike = True
    return _signal

def iv_rank_above(threshold: float = 0.5, window: int = 252) -> SignalFunc:
    """True when IV rank exceeds a threshold. ..."""
    return _iv_rank_signal(threshold, window, operator.gt)

def iv_rank_below(threshold: float = 0.5, window: int = 252) -> SignalFunc:
    """True when IV rank is below a threshold. ..."""
    return _iv_rank_signal(threshold, window, operator.lt)
```

This follows the same pattern already used by `_bb_signal`, `_atr_signal`, and `_crossover_signal` in the same file. The `operator` module is already imported.

#### 8.2.2 — DRY: Signal resolution logic duplicated between `run_strategy` and `simulate` (HIGH)

**File:** `optopsy/ui/tools/_executor.py`
- `_handle_run_strategy`: lines 671-774
- `_handle_simulate`: lines 972-1070

**Problem:** These two handlers contain ~100 lines of nearly identical signal resolution code:

1. **Entry/exit slot resolution** (checking slot exists, retrieving from `signals` dict)
2. **Inline signal name validation** (checking against `SIGNAL_REGISTRY`)
3. **Data source classification** (`needs_stock`, `needs_iv`, `has_non_iv_signal`)
4. **Data fetching** (stock data, IV data, date-only fallback)
5. **The for-loop resolving inline signals** via `_resolve_inline_signal()`

The only differences are:
- `simulate` also strips simulation-specific keys (`capital`, `quantity`, etc.)
- Variable names differ slightly (`iv_signal_data` vs `iv_signal_data_sim`, `has_non_iv_signal` vs `has_non_iv_signal_sim`)

**Fix:** Extract a `_resolve_signals_for_strategy()` helper in `_helpers.py` that:
- Takes `arguments`, `signals`, `dataset`, `_result`
- Returns `(strat_kwargs_update, error_result)` where `strat_kwargs_update` is a dict with `entry_dates` and/or `exit_dates` if signals were resolved
- Both handlers call this helper and merge the result into their `strat_kwargs`

This would eliminate ~80 duplicated lines and ensure signal resolution stays consistent between `run_strategy` and `simulate`.

#### 8.2.3 — DRY: IV error message repeated 4+ times

**Files:**
- `_executor.py:452-457` (build_signal)
- `_executor.py:745-750` (run_strategy)
- `_executor.py:1043-1048` (simulate)
- `_executor.py:1966-1970` (plot_vol_surface)
- `_executor.py:2054-2059` (iv_term_structure)

**Problem:** The error message about needing an `implied_volatility` column is repeated verbatim:

```python
"IV rank signals require options data with an "
"'implied_volatility' column. Fetch data from a provider "
"that includes IV (e.g. EODHD), or load a CSV with an "
"implied_volatility column."
```

And the `plot_vol_surface`/`iv_term_structure` variants:

```python
"Dataset does not contain 'implied_volatility'. "
"Fetch data from a provider that includes IV (e.g. EODHD) "
"or load a CSV with an implied_volatility column."
```

**Fix:** Define a constant `_IV_MISSING_MSG` in `_helpers.py` and reference it. Or add a `_require_iv_column(ds, _result)` helper that returns an error ToolResult if the column is missing, similar to `_require_dataset()`.

#### 8.2.4 — DRY: Quote date parsing + closest-date logic in vol surface tools

**File:** `optopsy/ui/tools/_executor.py`
- `_handle_plot_vol_surface`: lines 1972-1995
- `_handle_iv_term_structure`: lines 2062-2085

**Problem:** Both handlers follow the exact same pattern:

```python
quote_dates = pd.to_datetime(ds["quote_date"])
if quote_date_str:
    target_date = pd.to_datetime(quote_date_str)
    df = ds[quote_dates.dt.normalize() == target_date.normalize()].copy()
    if df.empty:
        available = sorted(quote_dates.dt.date.unique())
        closest = min(available, key=lambda d: abs(...))
        return _result(f"No data for {quote_date_str}. Closest: {closest}...")
else:
    latest_day = quote_dates.dt.normalize().max()
    df = ds[quote_dates.dt.normalize() == latest_day].copy()
    quote_date_str = str(latest_day.date())
```

**Fix:** Extract `_filter_by_quote_date(ds, quote_date_str, _result)` that returns `(filtered_df, resolved_date_str, error_result)`. Both handlers call it and proceed with the filtered data.

#### 8.2.5 — `_compute_atm_iv` uses `idxmin` which selects only one strike per group

**File:** `optopsy/signals.py:560`

**Observation:** The ATM strike selection uses `groupby(...).idxmin()` which returns a single row per group. If two strikes are equidistant from the underlying (e.g., underlying=100, strikes at 99 and 101), only one is used. This is acceptable for practical purposes but worth noting — averaging both equidistant strikes would be slightly more robust.

---

### 8.3 — Strategy Comparison Report (`_executor.py:1284-1529`)

**Overall assessment:** Functional and complete. The main concern is the handler's length (~245 lines) and the formatting logic that could be reusable.

#### 8.3.1 — `_handle_compare_results` is 245 lines and does too many things

**File:** `optopsy/ui/tools/_executor.py:1284-1529`

**Problem:** This single function handles:
1. Input validation and result selection (lines 1286-1307)
2. Building comparison rows from heterogeneous result types (lines 1312-1356)
3. Sorting and verdict computation (lines 1358-1401)
4. Display column formatting with multiple format patterns (lines 1403-1436)
5. Markdown table generation (lines 1438)
6. LLM summary generation (lines 1449-1468)
7. User display assembly (lines 1470-1476)
8. Plotly chart creation (lines 1478-1527)

**Fix:** Break into smaller helpers:
- `_build_comparison_rows(selected)` → returns `pd.DataFrame`
- `_compute_verdicts(df, metric_cols)` → returns `dict`
- `_format_comparison_table(df)` → returns formatted display DataFrame
- Keep the chart creation inline or extract to `_build_comparison_chart(df)`

#### 8.3.2 — Column formatting uses repetitive lambda patterns

**File:** `optopsy/ui/tools/_executor.py:1417-1436`

**Problem:**

```python
for col in ["mean_return", "std"]:
    if col in format_df.columns:
        format_df[col] = format_df[col].apply(
            lambda x: f"{x:.4f}" if pd.notna(x) else "—"
        )
for col in ["win_rate", "max_drawdown"]:
    if col in format_df.columns:
        format_df[col] = format_df[col].apply(
            lambda x: f"{x:.2%}" if pd.notna(x) else "—"
        )
# ... similar blocks for sharpe, profit_factor
```

**Fix:** Use a formatting config dict:

```python
_COMPARISON_FORMATS = {
    "mean_return": ".4f", "std": ".4f",
    "win_rate": ".2%", "max_drawdown": ".2%",
    "sharpe": ".4f", "profit_factor": ".2f",
}
for col, fmt in _COMPARISON_FORMATS.items():
    if col in format_df.columns:
        format_df[col] = format_df[col].apply(
            lambda x, f=fmt: f"{x:{f}}" if pd.notna(x) else "—"
        )
```

This is more concise and makes the format specs easy to adjust in one place.

#### 8.3.3 — LLM summary row building is verbose

**File:** `optopsy/ui/tools/_executor.py:1451-1463`

**Problem:** The per-row LLM summary manually checks and formats each metric:

```python
if pd.notna(row.get("mean_return")):
    parts.append(f"mean={row['mean_return']:.4f}")
if pd.notna(row.get("win_rate")):
    parts.append(f"wr={row['win_rate']:.2%}")
# ... repeated for sharpe, max_drawdown, profit_factor
```

**Fix:** Use a metric config list:

```python
_LLM_METRICS = [
    ("mean_return", "mean", ".4f"),
    ("win_rate", "wr", ".2%"),
    ("sharpe", "sharpe", ".4f"),
    ("max_drawdown", "mdd", ".2%"),
    ("profit_factor", "pf", ".2f"),
]
for col, abbrev, fmt in _LLM_METRICS:
    if pd.notna(row.get(col)):
        parts.append(f"{abbrev}={row[col]:{fmt}}")
```

---

### 8.4 — Cross-cutting Issues

#### 8.4.1 — `_non_strat_keys` sets duplicated between `run_strategy` and `simulate`

**File:** `optopsy/ui/tools/_executor.py`
- `_handle_run_strategy` lines 653-663: `_signal_keys` set
- `_handle_simulate` lines 948-964: `_non_strat_keys` set

**Problem:** Both handlers define local sets of keys to strip from `arguments` before passing to the strategy function. The signal-related keys are the same; `simulate` just adds the simulation-specific keys (`capital`, `quantity`, etc.). These sets are defined inline as literals in each handler, so if a new signal parameter is added, both must be updated.

**Fix:** Define `_SIGNAL_PARAM_KEYS` as a module-level frozenset in `_executor.py` or `_schemas.py`:

```python
_SIGNAL_PARAM_KEYS = frozenset({
    "strategy_name", "entry_signal", "entry_signal_params",
    "entry_signal_days", "exit_signal", "exit_signal_params",
    "exit_signal_days", "entry_signal_slot", "exit_signal_slot",
})
_SIM_PARAM_KEYS = frozenset({"capital", "quantity", "max_positions", "multiplier", "selector"})
```

Both handlers reference these constants.

---

## 9. Summary of DRY / Refactoring Priorities

| # | Issue | Impact | Effort | Location |
|---|-------|--------|--------|----------|
| 8.2.2 | Signal resolution duplicated between `run_strategy` and `simulate` | High | Medium | `_executor.py` |
| 8.2.1 | `iv_rank_above`/`iv_rank_below` near-identical | Medium | Low | `signals.py` |
| 8.1.1 | Profit factor reimplemented in 3 places | Medium | Low | `simulator.py`, `_helpers.py` |
| 8.1.2 | Win rate reimplemented in 3 places | Medium | Low | `simulator.py`, `_helpers.py` |
| 8.3.1 | `compare_results` handler is 245 lines | Medium | Medium | `_executor.py` |
| 8.2.4 | Quote date + closest-date logic duplicated in vol tools | Low | Low | `_executor.py` |
| 8.2.3 | IV error message repeated 4+ times | Low | Low | `_executor.py` |
| 8.4.1 | Signal param key sets duplicated | Low | Low | `_executor.py` |
| 8.3.2 | Column formatting uses repetitive lambdas | Low | Low | `_executor.py` |

### Recommended Order of Attack

1. **Signal resolution extraction** (8.2.2) — Highest impact, eliminates ~80 duplicated lines and the main maintenance risk. If the signal resolution logic changes (e.g., new signal types, new validation), you'd currently need to update two places.
2. **IV rank signal factory** (8.2.1) — Quick win, follows existing patterns in the file.
3. **Metrics reuse in simulator** (8.1.1 + 8.1.2) — Quick win, just replace inline code with function calls.
4. **Compare results decomposition** (8.3.1) — Improves readability, enables easier testing of individual parts.
5. **Everything else** — Low effort, opportunistic.
