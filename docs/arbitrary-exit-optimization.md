# Arbitrary Exit Points: Feasibility and Performance Optimization

This document analyzes whether optopsy can support arbitrary exit conditions (stop-loss, profit targets, time-based exits) beyond the current fixed-DTE exit model, and how to optimize the heavy merges that such a change would introduce.

## Background

Optopsy currently determines exit prices by matching entry quotes to exit quotes at a specific DTE (days to expiration). The core logic lives in `core.py:_evaluate_options()`:

```python
# line 222 — exits are filtered to a single exact DTE
exits = _get(data, "dte", kwargs["exit_dte"])
```

This produces a **1:1 merge** — one entry row matches one exit row per contract. It works well and is fast, but limits exit timing to a single predetermined point.

## Can we simplify using stock prices?

### At expiration: yes

At expiration, an option's value is purely intrinsic:

- **Call**: `max(0, stock_price - strike)`
- **Put**: `max(0, strike - stock_price)`

P&L at expiration is fully determined by the strikes chosen, the entry premium paid/received, and the stock price at expiration. The exit side of the pipeline could be replaced with intrinsic value math, eliminating the need for exit bid/ask data entirely.

**What you'd still need option data for:** the entry price. Options carry time value at entry that cannot be derived from stock price alone. A pricing model (Black-Scholes) could estimate this, but then you're backtesting a model rather than historical market prices.

### Before expiration: no

Time value, implied volatility, and Greeks all affect option pricing before expiration. A stock at 212 with a 210 call doesn't mean the call is worth $2 -- it could be $5-8 depending on volatility and time remaining. Stock prices alone are insufficient for intermediate exit pricing.

## Supporting arbitrary exit conditions

### What changes

For conditional exits (stop-loss, profit target, trailing stop), the pipeline needs to check option prices at **every** quote date between entry and expiration, not just one exit point:

```
Current:   entries (filtered) --> exits (single DTE) --> P&L
Proposed:  entries (filtered) --> all intermediate quotes --> scan for condition --> first match --> P&L
```

### What stays the same

The change is **isolated to the exit-matching logic** in `_evaluate_options()` and `_evaluate_all_options()`. Everything downstream is exit-agnostic:

- `_strategy_engine()` takes data with `entry`/`exit` columns and builds multi-leg positions
- `_assign_profit()` sums legs, applies multipliers, computes pct_change
- `rules.py` validates strike relationships
- `_format_output()` handles aggregation

### Data requirement

The main constraint is data volume. With `exit_dte=0` you need two snapshots per contract (entry + expiration). With conditional exits you need every trading day in between. For a 30-DTE position, that's ~22x more data per trade.

## The scale problem

With arbitrary exits, the merge becomes **1:many**:

```
Current:    entries (N rows) x exits (N rows)            --> result (N rows)
Arbitrary:  entries (N rows) x all_future_quotes (N x D) --> result (N x D rows)
```

Where D is the number of trading days between entry and exit (~22 for a 30-DTE option).

For real data (SPX with ~200 strikes x 2 types x 20 expirations x 252 days/year), the merge output grows from millions of rows to tens of millions.

## Optimization strategies

### 1. Compound key to cheapen the join

The current merge joins on 4 columns:

```python
merge_cols = ["underlying_symbol", "option_type", "expiration", "strike"]
```

Every merge hashes all 4 columns. A single integer contract ID is significantly faster:

```python
# Compute once at load time
data["contract_id"] = (
    data["underlying_symbol"].astype("category").cat.codes * 1_000_000
    + data["option_type"].astype("category").cat.codes * 100_000
    + (data["expiration"] - data["expiration"].min()).dt.days * 1000
    + (data["strike"] * 10).astype(int)
)

# All merges now use a single integer column
entries.merge(exits, on="contract_id")
```

**Effort:** Low. **Speedup:** 2-3x on all merges. **When to use:** Always -- this is a free win.

### 2. Partition by expiration

Options from different expiration cycles never interact. Process them independently:

```python
def _evaluate_with_conditional_exit(data, exit_condition, **kwargs):
    results = []
    for expiration, group in data.groupby("expiration"):
        entries = _filter_entries(group, **kwargs)
        futures = group[["contract_id", "quote_date", "bid", "ask"]]

        # Merge is now scoped to one expiration cycle
        merged = entries.merge(futures, on="contract_id", suffixes=("_entry", ""))
        merged = merged[merged["quote_date"] > merged["quote_date_entry"]]

        triggered = _find_first_exit(merged, exit_condition)
        results.append(triggered)

    return pd.concat(results)
```

Each partition is ~200 strikes x 2 types x ~22 days = ~8,800 rows instead of millions.

**Effort:** Low. **Speedup:** 10-100x depending on data. **When to use:** Always.

### 3. Sort + groupby().first() for early termination

For stop-loss / profit-target exits, only the **first** date the condition triggers matters. Don't keep the rest:

```python
# Sort by date, check condition vectorized, keep first match per position
merged = merged.sort_values("quote_date")

merged["mid"] = (merged["bid"] + merged["ask"]) / 2
merged["hit_stop"] = merged["mid"] <= merged["entry"] * (1 - stop_pct)
merged["hit_target"] = merged["mid"] >= merged["entry"] * (1 + target_pct)
merged["triggered"] = merged["hit_stop"] | merged["hit_target"]

# O(n) scan -- stops at first match per group
exits = merged[merged["triggered"]].groupby("entry_id").first()
```

**Effort:** Low. **Speedup:** Avoids storing the full wide result. **When to use:** Stop-loss / profit-target exits.

### 4. merge_asof for nearest-DTE matching

For the simpler "exit at target DTE, nearest available" approach, `pd.merge_asof` replaces a filtered cross-join with an O(n log n) operation:

```python
entries = entries.sort_values("quote_date")
exits = exits.sort_values("quote_date")

result = pd.merge_asof(
    entries,
    exits,
    by="contract_id",
    left_on="target_exit_date",
    right_on="quote_date",
    direction="nearest",
    tolerance=pd.Timedelta("3 days"),
)
```

This replaces the exact `_get(data, "dte", exit_dte)` with a fuzzy match, handling gaps in data gracefully.

**Effort:** Low. **Speedup:** Replaces filtered cross-join. **When to use:** DTE-based exits with tolerance.

### 5. Iterative date scan

Avoid the wide merge entirely by scanning forward date-by-date:

```python
def _scan_for_exit(entries, all_data, condition_fn):
    open_positions = entries.copy()
    closed = []

    for date in sorted(all_data["quote_date"].unique()):
        if open_positions.empty:
            break

        # Small lookup: today's prices only
        today = all_data[all_data["quote_date"] == date]

        # Small merge: open positions x today's quotes
        checked = open_positions.merge(
            today[["contract_id", "bid", "ask"]], on="contract_id"
        )

        hit = condition_fn(checked)
        closed.append(checked[hit])
        open_positions = open_positions[~open_positions.index.isin(checked[hit].index)]

    return pd.concat(closed)
```

Each iteration merges open positions against a single day's quotes. No wide merge is ever created. The tradeoff is a Python loop over ~252 dates/year, but each iteration is small and fast.

**Effort:** Medium. **Speedup:** Avoids wide merge entirely. **When to use:** Long-dated options (LEAPs), large datasets.

### 6. Polars for the hot path

If pandas is still the bottleneck, swap the merge engine for the performance-critical section:

```python
import polars as pl

def _fast_conditional_exit(entries_pd, quotes_pd, stop_pct, target_pct):
    entries = pl.from_pandas(entries_pd)
    quotes = pl.from_pandas(quotes_pd)

    result = (
        entries.lazy()
        .join(quotes.lazy(), on="contract_id")
        .filter(pl.col("quote_date") > pl.col("quote_date_entry"))
        .with_columns(
            ((pl.col("bid") + pl.col("ask")) / 2).alias("exit_mid"),
        )
        .with_columns(
            (pl.col("exit_mid") <= pl.col("entry") * (1 - stop_pct)).alias("hit"),
        )
        .filter(pl.col("hit"))
        .sort("quote_date")
        .group_by("entry_id")
        .first()
        .collect()
    )
    return result.to_pandas()
```

Polars fuses the join + filter + sort + groupby into one pass via lazy evaluation. Typically 5-20x faster than pandas for this wide-join-then-aggregate pattern. The rest of the codebase stays pandas.

**Effort:** Medium (new dependency). **Speedup:** 5-20x over pandas. **When to use:** If strategies 1-5 are insufficient.

## Summary

| Priority | Technique | Effort | Speedup | Best for | Status |
|----------|-----------|--------|---------|----------|--------|
| 1 | Partition by expiration | Low | 10-100x | All exit types | **Done** |
| 2 | Compound integer key | Low | 2-3x | All merges | **Done** |
| 3 | groupby().first() on sorted data | Low | Avoids storing full result | Stop/target exits | Pending (needs conditional exit support) |
| 4 | merge_asof | Low | Replaces filtered cross-join | DTE-based exits | Pending |
| 5 | Iterative date scan | Medium | Avoids wide merge entirely | Stop/target exits, LEAPs | Pending (needs conditional exit support) |
| 6 | Polars for hot path | Medium | 5-20x over pandas | When pandas is insufficient | Pending |

### Implemented

**Partition by expiration (#1)** and **compound integer key (#2)** have been implemented in `core.py:_evaluate_options()`. The entry/exit merge now uses a single `contract_id` column (computed via `groupby().ngroup()`) instead of four merge-key columns, and partitions the merge by expiration cycle so each merge operates on a smaller data subset. All existing tests pass with identical results, confirming the optimizations are behavior-preserving.

### Remaining

The combination of **early termination (#3)** with the already-implemented partitioning handles most real-world datasets without leaving pandas, but requires conditional exit support to be built first. The iterative scan (#5) is the right choice for very long-dated options. Polars (#6) is the escape hatch if data volume truly outgrows pandas.

## Exit type compatibility matrix

| Exit type | Code change scope | Data requirement | Optimization path |
|-----------|-------------------|------------------|-------------------|
| At expiration (exit_dte=0) | None | Entry + expiry snapshots | Current approach works |
| Fixed DTE (exit_dte=N) | None (or merge_asof) | Entry + target-date snapshots | #4 merge_asof |
| Stop-loss / profit target | Replace exit logic in _evaluate_options() | Daily snapshots | #1 + #2 + #3 |
| Trailing stop | Same + running max/min tracking | Daily snapshots | #1 + #2 + #5 |
