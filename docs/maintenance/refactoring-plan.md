# Refactoring Plan: Large File Decomposition

Last updated: 2026-02-23

This document outlines the plan to break down the three largest source files into smaller, focused modules. Each phase is independent and can be tackled separately.

---

## Priority Summary

| File | Lines | Priority | Reason |
|---|---|---|---|
| `optopsy/ui/tools/_executor.py` | 2,456 | **High** | Monolithic dispatcher mixing 6 concerns across 19 handlers |
| `optopsy/core.py` | 1,225 | **Medium** | Two parallel pipelines (regular + calendar) with duplicated logic |
| `optopsy/strategies.py` | 1,024 | **Low** | Clean pattern but naturally splits by leg count |

---

## Phase 1: Split `_executor.py` (2,456 -> ~8 files)

### Current State

Single file acts as both the tool dispatcher and the implementation of all 19 tool handlers. Concerns are mixed: data inspection, charting, signals, strategy execution, simulation, and result management all live together.

### Target Structure

```
optopsy/ui/tools/
├── _executor.py          (~450 lines)  Core dispatcher, registry, shared utilities
├── _data_inspector.py    (~280 lines)  preview_data, describe_data, suggest_strategy_params
├── _quality_checks.py    (~380 lines)  check_data_quality + per-date uniqueness helpers
├── _signals_builder.py   (~220 lines)  build_signal, preview_signal, list_signals, fetch_stock_data
├── _strategy_runners.py  (~180 lines)  run_strategy, scan_strategies
├── _simulators.py        (~170 lines)  simulate, get_simulation_trades
├── _results_manager.py   (~430 lines)  compare_results, list_results, inspect_cache, clear_cache
├── _charts.py            (~360 lines)  create_chart, plot_vol_surface, iv_term_structure + helpers
├── _helpers.py           (unchanged)
├── _models.py            (unchanged)
└── _schemas.py           (unchanged)
```

### Steps

1. **Extract shared utilities** — Move `_resolve_dataset()`, `_require_dataset()`, `_fmt_pf()`, `_STRIKE_THRESHOLDS`, and `_check_per_date_uniqueness()` into a shared location (keep in `_executor.py` or move to `_helpers.py`). These are used across multiple handler groups.

2. **Extract `_charts.py`** — Move chart handlers and their support functions:
   - `_handle_create_chart()` (215 lines, 6 chart types)
   - `_handle_plot_vol_surface()` (65 lines)
   - `_handle_iv_term_structure()` (73 lines)
   - `_resolve_chart_data()` (94 lines)
   - `_check_xy_columns()`, `_resolve_candlestick_columns()`
   - Import `_require_dataset`, `_resolve_dataset` from shared location

3. **Extract `_quality_checks.py`** — Move the largest single handler:
   - `_handle_check_data_quality()` (396 lines)
   - `_check_per_date_uniqueness()`, `_STRIKE_THRESHOLDS`
   - Constants: `_CORE_REQUIRED_COLS`, `_OPTIONAL_COLS`, `_NULL_CHECK_COLS`

4. **Extract `_results_manager.py`** — Move result/cache handlers:
   - `_handle_compare_results()` (243 lines)
   - `_handle_list_results()` (69 lines)
   - `_handle_inspect_cache()` (71 lines)
   - `_handle_clear_cache()` (16 lines)
   - `_COMPARISON_FORMATS` constant

5. **Extract `_data_inspector.py`** — Move data inspection handlers:
   - `_handle_preview_data()` (33 lines)
   - `_handle_describe_data()` (124 lines)
   - `_handle_suggest_strategy_params()` (109 lines)

6. **Extract `_signals_builder.py`** — Move signal handlers:
   - `_handle_build_signal()` (130 lines)
   - `_handle_preview_signal()` (24 lines)
   - `_handle_list_signals()` (32 lines)
   - `_handle_fetch_stock_data()` (45 lines)

7. **Extract `_strategy_runners.py`** — Move strategy execution:
   - `_handle_run_strategy()` (50 lines)
   - `_handle_scan_strategies()` (125 lines)

8. **Extract `_simulators.py`** — Move simulation handlers:
   - `_handle_simulate()` (124 lines)
   - `_handle_get_simulation_trades()` (33 lines)

9. **Update `_executor.py`** — Keep only:
   - `_TOOL_HANDLERS` registry and `@_register` decorator
   - `execute_tool()` dispatcher (113 lines)
   - Import and register all handlers from new modules
   - Shared utilities if not moved to `_helpers.py`

10. **Update imports** — Ensure `execute_tool` is still importable from `_executor` (no public API change).

### Key Decisions

- **Registry pattern**: Each new module should import `_register` from `_executor` and use it to self-register handlers. Alternatively, each module can export a dict of handlers that `_executor` merges at import time.
- **Shared utilities**: `_require_dataset()` and `_resolve_dataset()` are used by 12+ handlers. Keep them in `_executor.py` or move to `_helpers.py` to avoid circular imports.

### Risks

- Circular imports if `_executor.py` imports from modules that also import from `_executor.py`. Mitigate by extracting shared utilities to `_helpers.py` first.
- The `@_register` decorator mutates `_TOOL_HANDLERS` at import time — import order matters. Ensure all handler modules are imported in `_executor.py` before `execute_tool()` is called.

---

## Phase 2: Split `core.py` (1,225 -> ~6 files)

### Current State

Two main entry points (`_process_strategy` and `_process_calendar_strategy`) with overlapping logic. Filtering, evaluation, pricing, and output formatting are interleaved. Calendar strategy logic (lines 715-1194) is essentially a parallel pipeline with ~70% shared code.

### Target Structure

```
optopsy/
├── core.py               (~150 lines)  Orchestration: _process_strategy, _process_calendar_strategy
├── filters.py            (~200 lines)  Filtering primitives
├── pricing.py            (~200 lines)  Fill price, slippage, P&L calculation
├── evaluation.py         (~250 lines)  Option evaluation, entry/exit matching
├── calendar.py           (~400 lines)  Calendar-specific evaluation, leg prep, exit matching
└── output.py             (~150 lines)  Output formatting (regular + calendar)
```

### Steps

1. **Extract `filters.py`** — Move filtering primitives:
   - `_assign_dte()`, `_trim()`, `_ltrim()`, `_rtrim()`, `_get()`
   - `_remove_min_bid_ask()`, `_remove_invalid_evaluated_options()`
   - `_apply_signal_filter()`, `_filter_by_delta()`
   - `_cut_options_by_dte()`, `_cut_options_by_otm()`, `_cut_options_by_delta()`

2. **Extract `pricing.py`** — Move pricing and P&L logic:
   - `_calculate_fill_price()` (slippage models)
   - `_apply_ratios()` (price adjustments)
   - `_assign_profit()` (P&L + percentage change)
   - `_calculate_otm_pct()`, `_get_leg_quantity()`

3. **Extract `evaluation.py`** — Move option evaluation pipeline:
   - `_evaluate_options()` (single-leg evaluation)
   - `_evaluate_all_options()` (full pipeline orchestration)
   - `_get_exits()` (exit price matching)
   - `_calls()`, `_puts()` (option type filters — note: imported by `strategies.py`)

4. **Extract `calendar.py`** — Move calendar-specific logic:
   - `_evaluate_calendar_options()`
   - `_prepare_calendar_leg()`, `_get_strike_column()`, `_get_calendar_leg_columns()`
   - `_merge_calendar_legs()`
   - `_get_exit_leg_subset()`, `_find_calendar_exit_prices()`
   - `_calculate_calendar_pnl()`

5. **Extract `output.py`** — Move output formatting:
   - `_format_output()` (regular strategies)
   - `_format_calendar_output()` (calendar strategies)
   - `_group_by_intervals()` (statistics aggregation)
   - Consider unifying the two formatting functions (90% identical logic)

6. **Update `core.py`** — Keep only:
   - `_strategy_engine()` (multi-leg join logic)
   - `_rename_leg_columns()`
   - `_process_strategy()` (main entry, imports from new modules)
   - `_process_calendar_strategy()` (calendar entry, imports from new modules)

7. **Preserve public imports** — `strategies.py` imports `_calls`, `_puts`, `_process_strategy`, `_process_calendar_strategy` from `core`. Either keep re-exports in `core.py` or update `strategies.py` imports.

### Key Decisions

- **`_calls` and `_puts`**: Used by both `core.py` and `strategies.py`. Place in `evaluation.py` and re-export from `core.py` for backward compat, or update `strategies.py` to import from the new location.
- **Slippage duplication**: `_calculate_fill_price()` is called from both `_apply_ratios()` (regular) and `_calculate_calendar_pnl()` (calendar). Extracting to `pricing.py` eliminates the implicit coupling.

### Risks

- `strategies.py` directly imports `_calls`, `_puts`, `_process_strategy`, `_process_calendar_strategy` from `core`. Must maintain these imports via re-exports or update downstream.
- Test files may import internal functions from `core`. Check and update.

---

## Phase 3: Split `strategies.py` (1,024 -> 7 files)

### Current State

28 public strategy functions + 8 internal helpers + `Side` enum. Each strategy function is a thin wrapper (10-40 lines) that defines a `leg_def` tuple and delegates to a helper. The file is well-organized but large.

### Target Structure

```
optopsy/strategies/
├── __init__.py           (~50 lines)   Re-exports all 28 public functions + Side enum
├── _helpers.py           (~200 lines)  8 internal helpers, Side enum, default_kwargs
├── singles.py            (~55 lines)   long_calls, long_puts, short_calls, short_puts
├── two_leg.py            (~290 lines)  straddles, strangles, spreads, covered, protective
├── butterflies.py        (~130 lines)  4 butterfly strategies
├── iron_strategies.py    (~135 lines)  iron_condor, reverse_iron_condor, iron_butterfly, reverse_iron_butterfly
└── calendar.py           (~210 lines)  4 calendar spreads + 4 diagonal spreads
```

### Steps

1. **Create `strategies/` package directory**.

2. **Create `strategies/_helpers.py`** — Move internals:
   - `Side` enum
   - `default_kwargs`, `_calendar_only_keys`, `calendar_default_kwargs`
   - All 8 helper functions: `_singles`, `_straddles`, `_strangles`, `_spread`, `_butterfly`, `_iron_condor`, `_iron_butterfly`, `_covered_call`, `_calendar_spread`

3. **Create `strategies/singles.py`** — Move 4 single-leg strategies:
   - `long_calls`, `long_puts`, `short_calls`, `short_puts`
   - Import `_singles`, `Side` from `_helpers`

4. **Create `strategies/two_leg.py`** — Move 12 two-leg strategies:
   - Straddles: `long_straddles`, `short_straddles`
   - Strangles: `long_strangles`, `short_strangles`
   - Vertical spreads: `long_call_spread`, `short_call_spread`, `long_put_spread`, `short_put_spread`
   - Covered: `covered_call`, `protective_put`
   - Import `_straddles`, `_strangles`, `_spread`, `_covered_call`, `Side` from `_helpers`

5. **Create `strategies/butterflies.py`** — Move 4 butterfly strategies:
   - `long_call_butterfly`, `short_call_butterfly`, `long_put_butterfly`, `short_put_butterfly`
   - Import `_butterfly`, `Side` from `_helpers`

6. **Create `strategies/iron_strategies.py`** — Move 4 iron strategies:
   - `iron_condor`, `reverse_iron_condor`, `iron_butterfly`, `reverse_iron_butterfly`
   - Import `_iron_condor`, `_iron_butterfly`, `Side` from `_helpers`

7. **Create `strategies/calendar.py`** — Move 8 calendar/diagonal strategies:
   - Calendar: `long_call_calendar`, `short_call_calendar`, `long_put_calendar`, `short_put_calendar`
   - Diagonal: `long_call_diagonal`, `short_call_diagonal`, `long_put_diagonal`, `short_put_diagonal`
   - Import `_calendar_spread`, `Side` from `_helpers`

8. **Create `strategies/__init__.py`** — Re-export everything:
   - All 28 public strategy functions
   - `Side` enum
   - `default_kwargs`, `calendar_default_kwargs`
   - This preserves `from optopsy.strategies import long_calls` and `from optopsy import long_calls`

9. **Update `optopsy/__init__.py`** — Ensure top-level imports still work. Since `strategies` changes from a module to a package, verify `from optopsy.strategies import *` still resolves.

10. **Update test imports** — `tests/test_strategies.py` imports from `optopsy.strategies`. Verify all imports still resolve via the `__init__.py` re-exports.

### Key Decisions

- **Package vs. module**: Converting `strategies.py` to `strategies/` is a breaking change for any code that does `import optopsy.strategies` and expects a module. The `__init__.py` re-exports mitigate this.
- **Helper location**: All helpers go in `_helpers.py` since they're shared across strategy groups. Each strategy file only imports the helper(s) it needs.

### Risks

- The `STRATEGIES` registry in `optopsy/ui/tools/_schemas.py` maps strategy names to functions. Verify it still resolves after the move.
- Any `isinstance(strategies, ModuleType)` checks would break. Unlikely but worth grepping for.
- The old `strategies.py` file must be deleted (not left alongside the new package).

---

## General Guidelines

### Testing Strategy

For each phase:
1. Run `uv run pytest tests/ -v` before starting to establish a green baseline.
2. After each extraction step, run the full test suite to verify no regressions.
3. No test changes should be needed if public imports are preserved via re-exports.

### Branch Strategy

Each phase should be done on a separate branch:
- `feature/refactor-executor`
- `feature/refactor-core`
- `feature/refactor-strategies`

### Import Preservation

The critical constraint for all phases: **no public API changes**. All existing imports must continue to work. Use `__init__.py` re-exports and backward-compatible import paths.
