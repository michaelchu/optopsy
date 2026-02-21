---
applyTo: "tests/**/*.py,conftest.py"
---

# Test Review Instructions

## Conventions

- Test framework is pytest (config in `pytest.ini`).
- Test files mirror the module they cover (e.g., `test_strategies.py` tests `strategies.py`).
- Shared fixtures live in `conftest.py` at the repo root.
- Tests must run with both `pip install -e .` (core only) and `pip install -e ".[ui]"`.

## What to Check

- New tests cover the stated behavior, not just the happy path — include edge cases, invalid inputs, and boundary conditions.
- DataFrames used in assertions have deterministic data; avoid randomness without seeding.
- Tests are independent and do not rely on execution order.
- No hardcoded file paths or system-specific assumptions.
- Assertions are specific: prefer `assert df["col"].tolist() == [...]` over `assert not df.empty`.
