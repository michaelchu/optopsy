# External Library Opportunities

Last updated: 2026-02-24

This document identifies areas of the codebase where hand-rolled implementations could be replaced by well-maintained external libraries, reducing code volume, improving correctness, and lowering maintenance burden.

---

## Priority Summary

| Module | Lines | Library Replacement | Priority | Impact |
|---|---|---|---|---|
| `signals.py` | 943 | pandas-ta (already a dep) | **Done** | Already fully integrated — all 6 indicators delegate to pandas-ta |
| `rules.py` | 134 | Boolean indexing | **Done** | IDE support, type checking, no string interpolation |
| `checks.py` | 324 | Pydantic + Pandera | **Medium** | Eliminates boilerplate, gains serialization (adds core dep) |
| `metrics.py` | 275 | empyrical-reloaded | **Low** | Battle-tested financial math (adds dependency) |
| `evaluation.py` | 188 | `pd.merge_asof()` | **Low** | Cleaner exit matching, built into pandas (behavior risk) |
| `simulator.py` | 704 | vectorbt | **Deferred** | Biggest win but biggest migration |

---

## 1. `signals.py` — Technical Indicators (Already Done)

### Current State

~943 lines total. **All 6 technical indicators already delegate to pandas-ta**:

| Signal | Implementation | pandas-ta Call |
|---|---|---|
| RSI | `ta.rsi(prices, length=period)` | Fully outsourced |
| SMA | `ta.sma(prices, length=period)` | Fully outsourced |
| EMA | `ta.ema(prices, length=fast/slow)` | Fully outsourced |
| MACD | `ta.macd(prices, fast, slow, signal)` | Fully outsourced |
| Bollinger Bands | `ta.bbands(prices, length, std)` | Fully outsourced |
| ATR | `ta.atr(high, low, close, length)` | Fully outsourced |

The remaining ~600 lines are custom logic that **should stay**:
- Signal composition framework (`Signal` class, `and_signals`, `or_signals`, `sustained`)
- Calendar signals (`day_of_week`)
- IV Rank signals (`_compute_atm_iv`, `_compute_iv_rank_series`) — options-domain-specific, no library equivalent
- Per-symbol isolation (`_per_symbol_signal`) and crossover detection (`_crossover_signal`)
- NaN handling and signal application (`apply_signal`)

### Action Required

None — pandas-ta integration is already complete. No further code reduction is possible here.

---

## 2. `checks.py` — Parameter & DataFrame Validation (High Priority)

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

## 3. `metrics.py` — Risk-Adjusted Performance Metrics (Medium Priority)

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

`win_rate()` and `profit_factor()` are simple enough to keep in-house (3-5 lines each).

### Expected Reduction

~180 lines removed. The `compute_risk_metrics()` aggregation wrapper would stay but delegate to empyrical.

### New Dependencies

- `empyrical-reloaded` — community-maintained fork of Quantopian's empyrical. Lightweight, numpy/pandas only.

### Risks

- empyrical assumes daily returns by default; must pass correct `period` or `annualization` factor for options trade frequency.
- The original `empyrical` is unmaintained; use `empyrical-reloaded` fork.
- Subtle differences in annualization conventions could change metric values — verify against existing test fixtures.

---

## 4. `evaluation.py` — Entry/Exit Matching (Medium Priority)

### Current State

`_get_exits()` (~30 lines) implements tolerance-based nearest-match logic: for each entry, find the exit row with DTE closest to the target exit DTE. Uses `groupby` + absolute-difference + `idxmin` + `drop_duplicates`.

### What To Replace

`pd.merge_asof()` is purpose-built for "nearest key" merges on sorted data:

```python
# Before (_get_exits — ~30 lines)
def _get_exits(data, dte):
    data["_diff"] = (data["dte"] - dte).abs()
    idx = data.groupby([...])["_diff"].idxmin()
    return data.loc[idx].drop(columns="_diff").drop_duplicates(...)

# After (~5 lines)
exits = pd.merge_asof(
    entries.sort_values("dte"),
    data.sort_values("dte"),
    on="dte",
    by=["underlying_symbol", "option_type", "expiration", "strike"],
    direction="nearest",
    tolerance=tolerance,
)
```

### Expected Reduction

~25 lines removed, clearer intent. No temporary columns or manual index manipulation.

### New Dependencies

None — `pd.merge_asof()` is built into pandas.

### Risks

- `merge_asof` requires both DataFrames to be sorted by the `on` key. Must ensure sorting is applied before the call.
- The `tolerance` parameter semantics differ slightly (absolute value vs. the current custom logic). Verify edge cases with existing tests.
- Current implementation drops duplicates with `keep="first"`; `merge_asof` uses a different tie-breaking strategy. May need post-merge dedup.

---

## 5. `simulator.py` — Position-Level Backtesting (Low Priority)

### Current State

~704 lines of iterative simulation with manual position state tracking. Iterates row-by-row through strategy results, maintaining a list of active positions, checking exit conditions (profit target, stop loss, trailing stop, time exit), and accumulating an equity curve.

### What To Replace

**vectorbt** provides vectorized portfolio simulation:

```python
import vectorbt as vbt

pf = vbt.Portfolio.from_signals(
    close=prices,
    entries=entry_signals,
    exits=exit_signals,
    sl_stop=stop_loss,
    tp_stop=take_profit,
    size=position_size,
)
equity = pf.value()
trades = pf.trades.records_readable
```

### Expected Reduction

~500 lines removed. vectorbt handles position sizing, concurrent position limits, stop-loss/take-profit, equity tracking, and trade logging.

### New Dependencies

- `vectorbt` — heavy dependency (pulls in numba, plotly, scipy). Consider `vectorbt-pro` for lighter install.

### Risks

- **Largest migration effort** — the current simulator has options-specific logic (multi-leg P&L, expiration-based exits) that vectorbt doesn't natively support.
- vectorbt is designed for single-instrument equity/futures; adapting it to multi-leg options positions may require significant wrapper code, potentially negating the benefit.
- Heavy dependency footprint may not be acceptable for a lightweight library.
- **Recommendation**: Defer this unless the simulator becomes a maintenance burden. The current implementation is self-contained and well-tested.

---

## 6. `rules.py` — Strike Validation (Done)

Replaced `.query()` string-based filters with direct boolean indexing.

**Benefits gained:**
- IDE autocomplete and type checking for column names
- No string interpolation bugs
- Identical runtime behaviour (both are standard pandas operations)

No line reduction — this was a quality-of-life improvement, not a code reduction.

---

## Implementation Order

Status and recommended sequencing:

1. ~~**`signals.py`**~~ — **Done.** Already fully integrated with pandas-ta.
2. ~~**`rules.py`**~~ — **Done.** Replaced `.query()` strings with boolean indexing.
3. **`checks.py`** — Evaluate whether Pydantic should become a core dep. Start with parameter validation only (skip Pandera initially).
4. **`evaluation.py`** — Low risk but requires careful testing of edge cases vs current `_get_exits()` behaviour.
5. **`metrics.py`** — Add empyrical-reloaded, verify annualization conventions match options trade frequency.
6. **`simulator.py`** — Defer unless simulator maintenance becomes painful.

---

## Dependencies Impact

| Library | Version | Size | New? | Status |
|---|---|---|---|---|
| pandas-ta | >= 0.4.67b0 | ~2MB | No (existing) | Already integrated in signals.py |
| pydantic | >= 2.0 | ~5MB | Promote from optional | Candidate for checks.py |
| pandera | >= 0.20 | ~3MB | Yes | Optional — skip initially |
| empyrical-reloaded | >= 0.5.7 | ~500KB | Yes | Candidate for metrics.py |
| vectorbt | >= 0.26 | ~50MB+ | Yes | Deferred (simulator.py) |
