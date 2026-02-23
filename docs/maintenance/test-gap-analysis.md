# Test Gap Analysis

Last reviewed: 2026-02-23

This document catalogues untested and under-tested code paths across the core library and the UI module. Use it to prioritise future test work.

---

## Core Library

### Completely Untested Features

| Feature | Location | Notes |
|---|---|---|
| IV Rank signals | `signals.py:516-677` | `_compute_atm_iv`, `_compute_iv_rank_series`, `iv_rank_above`, `iv_rank_below` — ~160 lines, zero tests |
| Signal-strategy integration | `entry_dates`/`exit_dates` params | Implemented in `_evaluate_options()` and `_process_calendar_strategy()` but never exercised |
| `delta_interval` grouping | `core.py` + all strategies | Parameter accepted everywhere, never tested |
| Calendar `exit_dte_tolerance` | `core.py:842-886` | Tolerance-based date snapping logic, untested branch |
| Multi-position filtering | `simulator.py:511-531` | `max_positions > 1` concurrent positions path untested |
| Custom selector callables | `simulator.py:636-637` | Only built-in selectors tested |

### Partially Tested (missing key branches)

| Feature | What's missing |
|---|---|
| Slippage modes on strategies | Only `"mid"` tested via strategies; `"spread"` and `"liquidity"` modes never used in strategy-level tests |
| Quantity-aware legs | Butterflies define middle leg `quantity=2` but no test verifies the 2x P&L math |
| `_apply_ratios()` no bid/ask branch | `core.py:488-494` — fallback when bid/ask columns are absent |
| Profit factor edge cases | All-winners (`inf`), all-losers (`0.0`), zero-P&L trades |
| Calendar DTE range validation | `checks.py:85-110` — `front_min > front_max`, `back_min > back_max`, and overlap detection all untested |
| `apply_signal()` per-strike dedup | `signals.py:929-937` — `requires_per_strike` attribute handling |
| ATR with close-only | `signals.py:434-435` — high/low fallback path |
| Simulator ruin detection | `simulator.py:578-582` — equity hitting zero |
| `_compute_summary()` multi-date equity | `simulator.py:432-450` — conditional logic for multi-date curves |

### Untested Helpers

These are lower priority but easy wins for coverage:

- `_check_positive_number()` in `checks.py:131` — in param registry but no test
- `_requires_delta()` / `_requires_volume()` in `checks.py:234-244`
- `_trim_cols()` / `_standardize_cols()` in `datafeeds.py`
- `_macd_lines()`, `_bb_signal()`, `_ema_lines()`, `_atr_signal()` in `signals.py`

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

1. **IV rank signals** — large untested feature surface (`signals.py:516-677`)
2. **Signal-strategy integration** — `entry_dates`/`exit_dates` flowing through strategies
3. **Calendar `exit_dte_tolerance`** — real code path, zero coverage
4. **Non-mid slippage on multi-leg strategies** — `"spread"` and `"liquidity"` modes
5. **`delta_interval` grouping** — on any strategy
6. **Calendar DTE range validation** — error paths in `checks.py:85-110`
7. **Profit factor / win rate edge cases** — all-winners, all-losers, single trade
8. **Quantity-aware butterfly P&L** — verify 2x middle leg math
9. **Simulator `max_positions > 1`** — concurrent position filtering
10. **`apply_signal()` per-strike dedup** — `requires_per_strike` branch

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
