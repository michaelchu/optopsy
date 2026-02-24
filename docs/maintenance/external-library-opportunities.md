# External Library Opportunities

Last updated: 2026-02-24

This document identifies areas of the codebase where hand-rolled implementations could be replaced by well-maintained external libraries, reducing code volume, improving correctness, and lowering maintenance burden.

---

## Priority Summary

| Module | Lines | Library Replacement | Priority | Status |
|---|---|---|---|---|
| `checks.py` | 324 | Pydantic + Pandera | **Medium** | Pending |
| ~~`metrics.py`~~ | ~~275~~ | ~~empyrical-reloaded~~ | ~~Low~~ | **Done** |

---

## 1. `checks.py` — Parameter & DataFrame Validation (Medium Priority)

### Current State

~324 lines of manual type-checking via a `param_checks` dict that maps parameter names to validator functions. Each validator is a hand-written `isinstance` / range check. DataFrame schema validation walks `.dtypes.astype(str).to_dict()` manually.

### What To Replace

**Parameter validation** — Replace `StrategyParams` TypedDict + manual validators with a Pydantic `BaseModel`:

```python
# Before (checks.py — ~50 lines per parameter group)
def _check_positive_int(name, val):
    if not isinstance(val, int) or val < 0:
        raise ValueError(f"{name} must be a positive integer")

# After (types.py or params.py)
class StrategyParams(BaseModel):
    dte_interval: tuple[int, int] = Field(ge=0)
    otm_pct_interval: tuple[float, float] = Field(ge=0, le=1)
    slippage: Literal["mid", "spread", "liquidity"] = "mid"
    # ... validators are declarative
```

**DataFrame schema validation** — Replace manual dtype walks with Pandera schemas:

```python
# Before (checks.py — ~80 lines)
def _check_df(df):
    expected = {"strike": "float64", "bid": "float64", ...}
    actual = df.dtypes.astype(str).to_dict()
    for col, dtype in expected.items():
        if actual.get(col) != dtype:
            raise ValueError(...)

# After
import pandera as pa
schema = pa.DataFrameSchema({
    "strike": pa.Column(float),
    "bid": pa.Column(float, pa.Check.ge(0)),
    "expiration": pa.Column("datetime64[ns]"),
})
schema.validate(df)
```

### Expected Reduction

~250 lines removed from `checks.py`. Gains: automatic error messages, JSON serialization, OpenAPI schema generation (useful for the UI agent tools).

### New Dependencies

- `pydantic >= 2.0` — already an optional dep for UI; would become a core dep.
- `pandera` — new dependency (~lightweight, pandas-native).

### Risks

- Moving Pydantic from optional to core increases install footprint for users who only use the backtesting library.
- Pandera adds a new dependency. Alternative: keep manual dtype checks but use Pydantic only for parameter validation (smaller change, still high value).

---

## 2. `metrics.py` — Risk-Adjusted Performance Metrics (Done)

Completed in `claude/review-external-libs` branch.

### What Changed

Replaced hand-rolled Sharpe, Sortino, VaR, CVaR, Calmar, and `max_drawdown_from_returns` with thin wrappers over `empyrical-reloaded`, preserving edge-case guards (return 0.0 on empty/NaN/inf). Added `omega_ratio` and `tail_ratio` as new metrics.

| Metric | Status |
|---|---|
| Sharpe ratio | Delegated to `empyrical.sharpe_ratio()` |
| Sortino ratio | Delegated to `empyrical.sortino_ratio()` |
| Max drawdown (returns) | Delegated to `empyrical.max_drawdown()` |
| Max drawdown (equity) | Kept in-house (empyrical only takes returns) |
| Value at Risk | Delegated to `empyrical.value_at_risk()` |
| CVaR | Delegated to `empyrical.conditional_value_at_risk()` |
| Calmar ratio | Delegated to `empyrical.calmar_ratio()` |
| Omega ratio | **New** — `empyrical.omega_ratio()` |
| Tail ratio | **New** — `empyrical.tail_ratio()` |
| `win_rate`, `profit_factor` | Kept in-house (no empyrical equivalent) |

### Result

- `metrics.py`: 275 → 323 lines (net +48 from new metrics; ~100 lines of implementation replaced with 1-line delegations)
- New dependency: `empyrical-reloaded>=0.5.7` + `pytz` (transitive dep not declared by empyrical)
- All 1098 existing + new tests pass
- `omega_ratio` and `tail_ratio` added to `compute_risk_metrics()` and simulator `_compute_summary()`

---

## Implementation Order

1. ~~**`metrics.py`**~~ — **Done.** Replaced with empyrical-reloaded wrappers, added omega/tail ratio.
2. **`checks.py`** — Evaluate whether Pydantic should become a core dep. Start with parameter validation only (skip Pandera initially).

---

## Dependencies Impact

| Library | Version | Size | New? | Status |
|---|---|---|---|---|
| pydantic | >= 2.0 | ~5MB | Promote from optional | Candidate for checks.py |
| pandera | >= 0.20 | ~3MB | Yes | Optional — skip initially |
| empyrical-reloaded | >= 0.5.7 | ~500KB | Yes | **Installed** |
| pytz | any | ~500KB | Yes | **Installed** (transitive dep of empyrical) |
