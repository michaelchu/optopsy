---
applyTo: "**/*.py"
---

# Code Review Instructions

## Project Context

Optopsy is a Python 3.12–3.13 backtesting library for options strategies. It processes historical option chain data through pandas pipelines. CI enforces Black formatting and pytest on every PR.

## Formatting

- All code must pass `black --check` with default settings.
- Do not add type annotations, docstrings, or comments to unchanged code.
- Use f-strings for string formatting.
- Keep changes minimal — no speculative error handling, abstractions, or configurability.

## Correctness

- DataFrame operations must preserve index alignment and avoid implicit index joins.
- Strategy leg definitions must use correct `Side` enum values (`long=1`, `short=-1`) and quantities.
- P&L calculations must apply bid/ask pricing correctly (buy at ask, sell at bid) unless slippage mode overrides.
- Date filtering must use proper datetime comparisons, not string comparisons.
- New strategies must follow the pattern: public function in `strategies.py` → helper → `core._process_strategy()`.

## Data Integrity

- New parameters require a validation function registered in `param_checks` in `checks.py`.
- New required columns need dtype entries in `expected_types` (or optional type dicts) in `checks.py`.
- NaN/NaT handling must be explicit — never silently drop or fill missing data.
- All pandas merges must specify `on=` columns explicitly; no ambiguous joins.

## Performance

- Prefer vectorized pandas operations over row-by-row iteration (no `iterrows()`, `itertuples()` in hot paths).
- Avoid unnecessary `.copy()` calls on large DataFrames.
- Use built-in aggregation functions with groupby, not `.apply()` with Python-level loops.

## Testing

- Every new strategy or behavioral change must have corresponding tests in `tests/`.
- Tests use fixtures from `conftest.py` at the repo root.
- Public functions in `strategies.py` must be exported in `__init__.py`.
