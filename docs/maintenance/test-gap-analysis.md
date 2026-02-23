# Test Gap Analysis

Last updated: 2026-02-23

This document catalogues untested and under-tested code paths across the core library and the UI module. Use it to prioritise future test work.

---

## Coverage Summary

**Overall: 74%** (3856 statements, 1010 uncovered) — 854 tests, 12 skipped

### Core Library

| File | Stmts | Miss | Cover | Uncovered lines |
|---|---|---|---|---|
| `__init__.py` | 9 | 0 | 100% | — |
| `checks.py` | 96 | 0 | 100% | — |
| `core.py` | 349 | 4 | 99% | 63, 182, 206, 925 |
| `datafeeds.py` | 51 | 9 | 82% | 83-84, 186, 201-206 |
| `definitions.py` | 16 | 0 | 100% | — |
| `metrics.py` | 92 | 3 | 97% | 79, 100, 163 |
| `rules.py` | 24 | 0 | 100% | — |
| `signals.py` | 231 | 0 | 100% | — |
| `simulator.py` | 231 | 2 | 99% | 665, 696 |
| `strategies.py` | 104 | 0 | 100% | — |
| `timestamps.py` | 6 | 0 | 100% | — |
| `types.py` | 25 | 0 | 100% | — |

### UI Module

| File | Stmts | Miss | Cover | Uncovered lines |
|---|---|---|---|---|
| `ui/__init__.py` | 0 | 0 | 100% | — |
| `ui/_compat.py` | 8 | 8 | 0% | 3-18 |
| `ui/agent.py` | 141 | 141 | 0% | 21-624 |
| `ui/app.py` | 144 | 144 | 0% | 14-376 |
| `ui/cli.py` | 159 | 115 | 28% | 16, 21-34, 39-51, 56-63, 67-104, 109-168, 173-216, 287-290 |
| `ui/providers/__init__.py` | 25 | 4 | 84% | 30-31, 42, 57 |
| `ui/providers/base.py` | 24 | 2 | 92% | 143, 151 |
| `ui/providers/cache.py` | 108 | 5 | 95% | 132-133, 159, 178, 199 |
| `ui/providers/eodhd.py` | 391 | 318 | 19% | *(extensive — see details below)* |
| `ui/tools/__init__.py` | 5 | 0 | 100% | — |
| `ui/tools/_executor.py` | 908 | 203 | 78% | *(see details below)* |
| `ui/tools/_helpers.py` | 296 | 39 | 87% | 66-69, 96-97, 102, 129-131, 293, 296, 362, 416, 420-421, 474-475, 489-492, 516, 566, 578, 638-639, 691, 695, 707, 710-716, 720, 725, 756-758, 804-805 |
| `ui/tools/_indicators.py` | 94 | 3 | 97% | 37, 64, 122 |
| `ui/tools/_models.py` | 273 | 1 | 99% | 637 |
| `ui/tools/_schemas.py` | 46 | 9 | 80% | 193, 195, 198, 202-207, 312 |

---

## Gap Analysis

### Core Library

### Completely Untested Features

None — all significant features are now covered.

### Partially Tested (missing key branches)

| Feature | What's missing |
|---|---|
| `_apply_ratios()` no bid/ask branch | `core.py:488-494` — fallback when bid/ask columns are absent |

### Dead Code (unreachable)

These lines are guarded at call sites and cannot be reached through normal execution:

| Line | Location | Why unreachable |
|---|---|---|
| 45 | `core.py` `_calculate_fill_price` | `ratio = fill_ratio` — validation in `_check_fill_ratio` prevents reaching this |
| 164 | `core.py` `_filter_by_delta` | `return data` — guarded by `_requires_delta()` check at call site (line 325) |
| 188 | `core.py` `_cut_options_by_delta` | `return data` — guarded by `delta_interval is not None` check at call site (line 397) |

### Recently Covered

These gaps were addressed and now have tests:

| Feature | Tests added | Coverage |
|---|---|---|
| `delta_interval` grouping | `test_strategies.py::TestDeltaInterval` | core.py line 397 |
| `entry_dates`/`exit_dates` signal integration | `test_strategies.py::test_entry_dates_filter_*`, `test_exit_dates_filter_*`, calendar variants | core.py lines 330, 337, 1065, 1085, 1088 |
| `exit_dte_tolerance` (non-calendar) | `test_strategies.py::test_exit_dte_tolerance_non_calendar` | core.py lines 273-289 |
| Calendar `exit_dte_tolerance` | `test_strategies.py::test_calendar_tolerance_no_nearby_dates` | core.py lines 842-886 |
| Calendar empty aggregated output | `test_strategies.py::test_calendar_empty_aggregated_output` | core.py line 1125 |
| `delta_max`-only filtering | `test_strategies.py::test_delta_max_only_filter` | core.py `_filter_by_delta` rtrim branch |
| IV passthrough | `test_strategies.py::test_implied_volatility_passthrough` | core.py line 361 |
| `_check_positive_number` | `test_checks.py::TestCheckPositiveNumber` | checks.py line 131 |
| `_requires_delta` / `_requires_volume` | `test_checks.py::TestRequiresDelta`, `TestRequiresVolume` | checks.py lines 234-244 |
| `_trim_cols` / `_standardize_cols` | `test_datafeeds.py::TestTrimCols`, `TestStandardizeCols` | datafeeds.py internal helpers |
| Profit factor all-losers | `test_simulator.py::test_profit_factor_zero_when_all_losers` | simulator.py edge case |
| IV rank signals | `test_iv_signals.py` (pre-existing) | signals.py:516-677 |
| Calendar DTE range validation | `test_strategies.py` (pre-existing strategy-level tests) | checks.py:85-110 |
| Slippage modes | `test_strategies.py` (pre-existing) | Covered at strategy level |
| Butterfly quantity 2x | `test_strategies.py::test_long_call_butterfly_raw` (pre-existing) | Verified via raw output |
| Selector OTM% path | `test_simulator.py::TestSelectorEdgeCases::test_select_nearest_with_otm_column` | simulator.py line 255 |
| Selector ultimate fallback | `test_simulator.py::TestSelectorEdgeCases::test_select_nearest_ultimate_fallback` | simulator.py line 273 |
| Highest premium multi-leg | `test_simulator.py::TestSelectorEdgeCases::test_select_highest_premium_multi_leg` | simulator.py line 289 |
| _derive_entry_date error | `test_simulator.py::TestResolveHelperErrors::test_derive_entry_date_no_columns_raises` | simulator.py line 352 |
| _resolve_expiration error | `test_simulator.py::TestResolveHelperErrors::test_resolve_expiration_no_columns_raises` | simulator.py line 361 |
| _filter_trades empty | `test_simulator.py::TestEmptyDataPaths::test_filter_trades_empty` | simulator.py line 495 |
| _build_trade_log empty | `test_simulator.py::TestEmptyDataPaths::test_build_trade_log_empty` | simulator.py line 548 |
| TA indicator returns None | `test_signals.py::TestSignalEdgeCases::test_ta_signal_insufficient_data_returns_all_false` | signals.py line 96 |
| sustained days < 1 | `test_signals.py::TestSignalEdgeCases::test_sustained_days_zero_raises` | signals.py line 787 |
| Signal.__repr__ | `test_signals.py::TestSignalEdgeCases::test_signal_repr` | signals.py line 853 |
| IV rank empty after DTE filter | `test_signals.py::TestIVRankEdgeCases::test_iv_rank_empty_after_dte_filter` | signals.py lines 552, 621 |

**Current core.py coverage: 99%** (349 statements, 4 uncovered — 3 dead code, 1 edge case)
**Current simulator.py coverage: 99%** (231 statements, 2 uncovered — defensive edge cases)
**Current signals.py coverage: 100%** (231 statements, 0 uncovered)

---

## UI Module

### 0% Coverage

| File | Stmts | What's untested |
|---|---|---|
| `_compat.py` | 8 | Compatibility shim — conditional imports |
| `agent.py` | 141 | Entire `OptopsyAgent.chat()` loop: streaming, tool dispatch, retry/backoff for `RateLimitError`/`AuthenticationError`, message compaction (`_compact_history`), iteration throttle, max iterations guard |
| `app.py` | 144 | All Chainlit handlers: `on_chat_start`, `on_chat_resume`, `on_message`, CSV upload handling, session state recovery, chart element collection, token streaming |

### 19% Coverage

| File | Stmts | Miss | What's tested | What's NOT |
|---|---|---|---|---|
| `eodhd.py` | 391 | 318 | `_compute_date_gaps`, `_fetch_with_cache` error path | `_request_with_retry`, `_paginate_window` (complex pagination), `_fetch_options_from_api` (adaptive windowing), `_apply_options_transforms`, `_filter_options`, `_resolve_underlying_prices` (yfinance integration), `_select_options_columns`, `_parse_date`, `_coerce_numeric`, `_safe_raise_for_status` (API token sanitization) |

### 28% Coverage

| File | Stmts | Miss | What's tested | What's NOT |
|---|---|---|---|---|
| `cli.py` | 159 | 115 | `_format_bytes`, arg parsing | `_cmd_cache_size`, `_cmd_cache_clear`, `_cmd_run` (auth secret generation, env setup, Chainlit config), `_cmd_download` |

### 78–87% Coverage

| File | Stmts | Miss | Cover | Remaining gaps |
|---|---|---|---|---|
| `_executor.py` | 908 | 203 | 78% | `_handle_scan_strategies` (lines 313-418), `_handle_simulate` error paths, `_handle_create_chart` edge cases, `_fmt_pf` formatting helper |
| `_schemas.py` | 46 | 9 | 80% | Signal registry lambdas (lines 193-207), `get_required_option_type()` (line 312) |
| `providers/__init__.py` | 25 | 4 | 84% | `_load_providers()` import error handling (lines 30-31), `get_provider_for_tool()` miss path (line 57) |
| `_helpers.py` | 296 | 39 | 87% | `_fetch_stock_data_for_signals` error paths, `write_sim_trade_log`/`read_sim_trade_log`, `_df_to_markdown` edge cases |

### 92–100% Coverage

| File | Stmts | Miss | Cover | Remaining gaps |
|---|---|---|---|---|
| `base.py` | 24 | 2 | 92% | Abstract method stubs (lines 143, 151) |
| `cache.py` | 108 | 5 | 95% | Path traversal safety (line 132-133), `merge_and_save` partial dedup (line 159), edge cases (lines 178, 199) |
| `_indicators.py` | 94 | 3 | 97% | Fallback branches (lines 37, 64, 122) |
| `_models.py` | 273 | 1 | 99% | Single uncovered line (637) |
| `tools/__init__.py` | 5 | 0 | 100% | Fully covered |

---

## Recommended Priority

### Core — highest impact first

1. **`_apply_ratios()` no bid/ask branch** — fallback path (`core.py:488-494`)
2. **Simulator `no underlying_symbol`** — contrived edge case (`simulator.py:665, 696`)

### UI — highest impact first

1. **`agent.py` `_compact_history`** — pure function, easy to unit test
2. **`agent.py` `chat()`** — mock LiteLLM calls, verify tool loop, retry logic, iteration cap
3. **`app.py` `on_message` CSV upload path** — mock Chainlit context, verify dataset registration
4. **`eodhd.py` pagination and retry** — mock `requests` and verify windowing logic
5. **`_executor.py` `_handle_scan_strategies`** — largest remaining uncovered handler (~100 lines)
6. **`cli.py` `_cmd_run`** — mock Chainlit import, verify env/config setup
7. **`_helpers.py` stock data fetching** — mock yfinance, verify caching and gap detection
8. **`_schemas.py` signal registry lambdas** — verify schema shape correctness
