# External Library Opportunities

Last updated: 2026-02-24

This document identifies areas of the codebase where hand-rolled implementations could be replaced by well-maintained external libraries, reducing code volume, improving correctness, and lowering maintenance burden.

---

## Priority Summary

| Module | Lines | Library Replacement | Priority | Impact |
|---|---|---|---|---|
| `checks.py` | 324 | Pydantic + Pandera | **Medium** | Eliminates boilerplate, gains serialization (adds core dep) |
| `metrics.py` | 275 | empyrical-reloaded | **Low** | Battle-tested financial math, add omega/tail ratio (adds dependency) |

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

## 2. `metrics.py` — Risk-Adjusted Performance Metrics (Medium Priority)

### Current State

~275 lines implementing Sharpe ratio, Sortino ratio, max drawdown, Value at Risk, Calmar ratio, profit factor, and win rate with numpy. Includes manual edge-case handling (zero division, insufficient data, annualization factors).

### What To Replace

| Metric | Current | empyrical Equivalent |
|---|---|---|
| Sharpe ratio | Manual annualized excess return / std | `empyrical.sharpe_ratio()` |
| Sortino ratio | Manual downside deviation | `empyrical.sortino_ratio()` |
| Max drawdown | Manual running-max accumulation | `empyrical.max_drawdown()` |
| Value at Risk | `np.percentile()` | `empyrical.value_at_risk()` |
| Calmar ratio | Manual return / max_drawdown | `empyrical.calmar_ratio()` |
| Omega ratio | *(new metric)* | `empyrical.omega_ratio()` |
| Tail ratio | *(new metric)* | `empyrical.tail_ratio()` |

`win_rate()` and `profit_factor()` are simple enough to keep in-house (3-5 lines each).

**New metrics to add:** Omega ratio and tail ratio are not currently implemented but are especially valuable for options strategies due to non-normal return distributions. Omega ratio captures the full return distribution (not just mean/variance), while tail ratio measures the relationship between right and left tail extremes.

### Expected Reduction

~180 lines removed. The `compute_risk_metrics()` aggregation wrapper would stay but delegate to empyrical.

### New Dependencies

- `empyrical-reloaded` — community-maintained fork of Quantopian's empyrical. Lightweight, numpy/pandas only.

### Risks

- empyrical assumes daily returns by default; must pass correct `period` or `annualization` factor for options trade frequency.
- The original `empyrical` is unmaintained; use `empyrical-reloaded` fork.
- Subtle differences in annualization conventions could change metric values — verify against existing test fixtures.

---

## Implementation Order

Status and recommended sequencing:

1. **`checks.py`** — Evaluate whether Pydantic should become a core dep. Start with parameter validation only (skip Pandera initially).
2. **`metrics.py`** — Add empyrical-reloaded, verify annualization conventions match options trade frequency. Also add omega ratio and tail ratio as new metrics.

---

## Dependencies Impact

| Library | Version | Size | New? | Status |
|---|---|---|---|---|
| pydantic | >= 2.0 | ~5MB | Promote from optional | Candidate for checks.py |
| pandera | >= 0.20 | ~3MB | Yes | Optional — skip initially |
| empyrical-reloaded | >= 0.5.7 | ~500KB | Yes | Candidate for metrics.py |
