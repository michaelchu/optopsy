# Test Gap Analysis

Last updated: 2026-02-23

This document catalogues untested and under-tested code paths across the core library and the UI module. Use it to prioritise future test work.

---

## Core Library

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

**Current core.py coverage: 99%** (349 statements, 5 uncovered — 3 dead code, 2 edge cases)
**Current simulator.py coverage: 99%** (231 statements, 2 uncovered — defensive edge cases)
**Current signals.py coverage: 100%** (231 statements, 0 uncovered)

---

## UI Module

### 0% Coverage — Critical Components

| File | Lines | What's untested |
|---|---|---|
| `agent.py` | ~600 | Entire `OptopsyAgent.chat()` loop: streaming, tool dispatch, retry/backoff for `RateLimitError`/`AuthenticationError`, message compaction (`_compact_history`), iteration throttle, max iterations guard |
| `app.py` | ~364 | All Chainlit handlers: `on_chat_start`, `on_chat_resume`, `on_message`, CSV upload handling, session state recovery, chart element collection, token streaming |
| `_executor.py` | ~1000+ | Tool dispatch (`execute_tool`), and every handler: `_handle_preview_data`, `_handle_describe_data`, `_handle_suggest_strategy_params`, `_handle_run_strategy`, `_handle_scan_strategies`, `_handle_build_signal`, `_handle_simulate`, `_handle_create_chart`, `_handle_plot_vol_surface`, `_handle_iv_term_structure`, plus helpers `_fmt_pf`, `_resolve_dataset`, `_require_dataset` |
| `_schemas.py` | ~454 | `get_tool_schemas()`, signal registry lambdas, `_normalize_days_param()`, `get_required_option_type()` |
| `providers/__init__.py` | ~46 | `_load_providers()`, `get_available_providers()`, `get_provider_for_tool()` — the entire provider discovery system |

### ~10% Coverage

| File | What's tested | What's NOT |
|---|---|---|
| `eodhd.py` | `_compute_date_gaps`, `_fetch_with_cache` error path | `_request_with_retry`, `_paginate_window` (complex pagination), `_fetch_options_from_api` (adaptive windowing), `_apply_options_transforms`, `_filter_options`, `_resolve_underlying_prices` (yfinance integration), `_select_options_columns`, `_parse_date`, `_coerce_numeric`, `_safe_raise_for_status` (API token sanitization) |
| `_helpers.py` | Minimal | `_fetch_stock_data_for_signals` (yfinance caching), `_intersect_with_options_dates`, `write_sim_trade_log`/`read_sim_trade_log`, `_empty_signal_suggestion`, `_df_to_markdown`, `ToolResult` class |

### ~30% Coverage

| File | What's tested | What's NOT |
|---|---|---|
| `cli.py` | `_format_bytes`, arg parsing | `_cmd_cache_size`, `_cmd_cache_clear`, `_cmd_run` (auth secret generation, env setup, Chainlit config) |
| `_models.py` | Pydantic happy paths | Schema conversion (`pydantic_to_openai_params`, `_resolve_refs`, `_strip_titles`), output models, most enum classes, mixin validators |

### ~85% Coverage

| File | Minor gaps |
|---|---|
| `cache.py` | Path traversal safety, `merge_and_save` with partial dedup_cols |

---

## Recommended Priority

### Core — highest impact first

1. **`_apply_ratios()` no bid/ask branch** — fallback path (`core.py:488-494`)
2. **Simulator `no underlying_symbol`** — contrived edge case (`simulator.py:665, 696`)

### UI — highest impact first

1. **`_executor.py` tool handlers** — unit-testable without Chainlit; mock the dataset registry and verify each handler returns correct results/errors
2. **`agent.py` `_compact_history`** — pure function, easy to unit test
3. **`agent.py` `chat()`** — mock LiteLLM calls, verify tool loop, retry logic, iteration cap
4. **`_schemas.py` `get_tool_schemas()`** — verify schema shape, signal registry correctness
5. **`providers/__init__.py`** — provider loading/discovery with mocked env vars
6. **`eodhd.py` pagination and retry** — mock `requests` and verify windowing logic
7. **`app.py` `on_message` CSV upload path** — mock Chainlit context, verify dataset registration
8. **`_helpers.py` stock data fetching** — mock yfinance, verify caching and gap detection
9. **`cli.py` `_cmd_run`** — mock Chainlit import, verify env/config setup
10. **`_models.py` schema conversion** — `pydantic_to_openai_params` output shape
