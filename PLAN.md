# Post-PR #213 Cleanup Plan

PR #213 ("Extract optopsy/data/ package") was merged with unaddressed Copilot review comments and outstanding follow-up work. This document tracks what remains.

---

## Phase 1: Address PR #213 Review Comments

These are unresolved review comments from the now-merged PR. They should be fixed in a follow-up PR before any new feature work.

### 1. Guard `EODHDProvider` import in CLI download path
**File:** `optopsy/data/cli.py:90`
**Issue:** The non-`--stocks` download path imports `EODHDProvider`, which imports `requests` at the top level. Running `optopsy-data download` without `optopsy[data]` crashes with a stacktrace instead of a helpful message.
**Fix:** Add `import_optional_dependency("requests")` guard before importing `EODHDProvider`.

### 2. Guard `yfinance` in `_download_stocks_with_rich`
**File:** `optopsy/data/cli.py:196`
**Issue:** `_yf_fetch_and_cache` does `import yfinance` internally. If yfinance isn't installed, the `except` only handles `OSError`/`ValueError`, so the CLI crashes with `ImportError`.
**Fix:** Call `import_optional_dependency("yfinance")` before invoking the helper, or catch `ImportError` in the except block.

### 3. Guard `dotenv` import in `_load_env()`
**File:** `optopsy/data/cli.py:63`
**Issue:** `_load_env()` imports `dotenv` directly. Missing the `data` extra gives `ModuleNotFoundError` instead of an actionable install hint.
**Fix:** Use `import_optional_dependency("dotenv")` so the error message points to `pip install optopsy[data]`.

### 4. Narrow `import_optional_dependency()` exception handling
**File:** `optopsy/data/_compat.py:21`
**Issue:** Catching bare `ImportError` can hide real import failures inside a dependency's sub-imports. A missing sub-dependency gets misreported as "Missing optional dependency".
**Fix:** Catch `ModuleNotFoundError` and check `exc.name` matches the requested top-level module; re-raise otherwise.

### 5. Fix `_compat.py` docstring
**File:** `optopsy/ui/_compat.py:4`
**Issue:** Docstring says "Re-export from optopsy.data._compat" but the file defines its own function. Misleading.
**Fix:** Update docstring to clarify it's a local helper with a UI-specific install hint.

### 6. Fix misleading comment in `result_store.py` shim
**File:** `optopsy/ui/providers/result_store.py:3`
**Issue:** Comment claims re-exporting `_RESULTS_DIR` preserves monkeypatch behavior, but `ResultStore` reads from the data-layer module's `_RESULTS_DIR`. Monkeypatching the UI re-export has no effect.
**Fix:** Reword comment to clarify that `ResultStore` reads from `optopsy.data.providers.result_store`.

### 7. Remove module-level `plotly` skip in integration tests
**File:** `tests/test_tools_integration.py:15`
**Issue:** `pytest.importorskip("plotly")` at module level skips the entire file when Plotly isn't installed, even though most tests don't need Plotly.
**Fix:** Remove module-level skip; keep only the in-test `importorskip` for chart-specific tests.

---

## Phase 2: Clean Up `underlying_price` Dependency (Separate PR)

`underlying_price` is mostly legacy from removed OTM selection logic. It's passed through the strategy pipeline via pandas merge suffixes (`_entry`/`_exit`) but isn't used for core computations.

### Consumers
1. **`strategies/_helpers.py:94`** — Redundant straddle join key (already implied by same `quote_date`)
2. **`simulator.py:299`** — Fallback ATM selection when delta is missing
3. **`signals/_helpers.py`** — Signal functions that read price series

### Tasks
- Remove `underlying_price` from `checks.expected_types` (make it optional)
- Remove redundant straddle join key in `_helpers.py`
- Update signals to accept stock data as a separate input
- Remove `_resolve_underlying_prices()` query-time merge

---

## Phase 3: Add `cached_data()` / `cached_stock_data()` (Separate PR)

Bridge functions for the data package once the schema is finalized after Phase 2.

---

## Phase 4: Finalize CLI Commands (Separate PR)

- Download both options + stock data sources
- `merge` command
- Cache backfill for legacy data
