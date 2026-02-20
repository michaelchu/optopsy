# AI Chat: Strategy Search & Discovery Enhancements

> Design document for giving the AI chat agent richer tools to autonomously
> search, scan, and discover profitable options strategies.

## Problem Statement

The AI chat currently has four tools:

| Tool | What it does |
|---|---|
| `list_data_files` | List available CSVs |
| `load_csv_data` | Load a CSV into memory |
| `preview_data` | Show shape / columns / sample rows |
| `run_strategy` | Run **one** strategy with **one** set of parameters |

This means every question like *"What's the most profitable strategy for SPX?"*
forces the AI into a tedious loop: run a strategy, read the result, adjust
parameters, run again, run a different strategy, compare mentally, etc.  It has
no way to systematically search the parameter space or compare strategies
side-by-side.  The 15-iteration tool-call limit means it can explore at most
~12 configurations before running out of turns.

## Inspiration from EODHD Guides

Two EODHD guides informed these ideas:

**Advanced guide (Greeks-first approach):**

- Uses option Greeks (delta, gamma, theta, vega) as primary search dimensions
  rather than just strike/DTE
- Strategies are categorized by which Greek they exploit: gamma scalping,
  vega-based volatility plays, theta decay harvesting
- Advocates scanning across Greek exposures to find the right risk dimension,
  then structuring positions around it
- Multi-Greek portfolio-level risk management: hedging delta while harvesting
  theta, etc.

**Beginner guide (signal-filtered backtesting):**

- Combines technical signals (SMA crossovers) with options entry/exit timing
- Uses multiple exit mechanisms: profit targets, stop losses, trailing stops
- Measures win rate, total ROI, and win/loss counts as primary metrics
- Highlights that raw backtests without slippage/fees overstate returns

**Key takeaways for our tools:**

1. Users think in terms of *goals* ("I want theta income", "I want to profit
   from a volatility spike") not individual strategy names
2. Comparing strategies across a shared metric (Sharpe, win rate, profit
   factor) is more useful than eyeballing separate tables
3. Greeks-based filtering (especially delta) should be a first-class search
   dimension alongside DTE and OTM%
4. Signal-filtered entry timing (RSI, SMA) can dramatically change results and
   should be easy to toggle during scans

---

## Proposed New Tools

### 1. `scan_strategies` — Strategy Scanner

**Purpose:** Run all (or a filtered subset of) the 28 strategies against the
loaded data in a single tool call and return a ranked leaderboard.

**Why the AI needs this:** Today, testing 6 strategies requires 6 separate
`run_strategy` calls consuming 6+ of the 15 iteration budget.  A scanner does
it in one call.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `strategies` | `string[]` (optional) | Subset of strategy names to scan. Default: all 28. |
| `category` | `string` (optional) | Filter by category: `"bullish"`, `"bearish"`, `"neutral"`, `"volatile"`, `"income"`. Overridden by explicit `strategies` list. |
| `max_entry_dte` | `integer` | Shared DTE param (default 90) |
| `exit_dte` | `integer` | Shared exit DTE (default 0) |
| `max_otm_pct` | `float` | Shared OTM filter (default 0.5) |
| `min_bid_ask` | `float` | Shared bid/ask floor (default 0.05) |
| `slippage` | `string` | Shared slippage model (default `"mid"`) |
| `sort_by` | `string` | Ranking metric: `"mean"`, `"median"`, `"win_rate"`, `"sharpe"`, `"profit_factor"`. Default `"sharpe"`. |
| `top_n` | `integer` | Return only top N results (default 10) |

**Strategy categories mapping:**

```
bullish:  long_calls, short_puts, long_call_spread, short_put_spread,
          covered_call
bearish:  long_puts, short_calls, long_put_spread, short_call_spread,
          protective_put
neutral:  short_straddles, short_strangles, iron_condor, iron_butterfly,
          long_call_butterfly, long_put_butterfly
volatile: long_straddles, long_strangles, reverse_iron_condor,
          reverse_iron_butterfly, short_call_butterfly, short_put_butterfly
income:   short_puts, short_calls, short_straddles, short_strangles,
          iron_condor, iron_butterfly, covered_call
```

**Output (returned to AI):**

A compact table with one row per strategy:

```
| strategy            | trades | mean    | median  | win_rate | sharpe | profit_factor |
|---------------------|--------|---------|---------|----------|--------|---------------|
| short_put_spread    | 312    |  0.0843 |  0.0621 | 0.68     |  1.24  |  2.14         |
| iron_condor         | 287    |  0.0712 |  0.0534 | 0.72     |  1.18  |  2.01         |
| covered_call        | 245    |  0.0398 |  0.0312 | 0.61     |  0.95  |  1.65         |
...
```

**Metrics computed per strategy (using raw=True internally):**

- `trades`: total number of trades
- `mean`: mean pct_change
- `median`: median pct_change
- `std`: standard deviation
- `win_rate`: fraction of trades with pct_change > 0
- `sharpe`: mean / std (annualization optional, but raw ratio is useful enough)
- `profit_factor`: sum(winning trades) / abs(sum(losing trades))
- `max_drawdown`: worst single trade pct_change
- `best_trade`: best single trade pct_change

**Implementation approach:**

Run each strategy with `raw=True` internally, compute summary metrics from the
raw DataFrame, collect into a single comparison DataFrame, sort by requested
metric, and return the top N.  Strategies that return empty results are
included with zeroed metrics and a note.

---

### 2. `parameter_sweep` — Parameter Optimizer

**Purpose:** Sweep one or two parameters across a range for a single strategy
to find the optimal configuration.

**Why the AI needs this:** The AI currently has to guess good parameters or
try them one at a time.  A sweep tool lets it answer *"What DTE works best
for iron condors?"* in a single call.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `strategy_name` | `string` | Strategy to sweep |
| `sweep_param` | `string` | Primary parameter to sweep: `"max_entry_dte"`, `"exit_dte"`, `"max_otm_pct"`, `"min_bid_ask"`, or `"slippage"` |
| `sweep_values` | `number[]` or `string[]` | Explicit list of values to try |
| `sweep_param_2` | `string` (optional) | Second parameter for 2D sweep |
| `sweep_values_2` | `number[]` or `string[]` (optional) | Values for second param |
| `sort_by` | `string` | Metric to optimize: `"mean"`, `"median"`, `"win_rate"`, `"sharpe"`, `"profit_factor"`. Default `"sharpe"`. |
| *(other strategy params)* | | Fixed values for non-swept params |

**Output:**

For 1D sweep:

```
| max_entry_dte | trades | mean    | win_rate | sharpe | profit_factor |
|---------------|--------|---------|----------|--------|---------------|
| 30            | 89     |  0.1021 | 0.72     |  1.45  |  2.31         |
| 45            | 156    |  0.0843 | 0.68     |  1.24  |  2.14         |  <-- best
| 60            | 201    |  0.0612 | 0.63     |  0.98  |  1.78         |
| 90            | 312    |  0.0398 | 0.58     |  0.72  |  1.42         |
```

For 2D sweep (e.g., DTE x OTM):

```
| max_entry_dte | max_otm_pct | trades | mean    | sharpe |
|---------------|-------------|--------|---------|--------|
| 30            | 0.05        | 23     |  0.1201 |  1.65  |
| 30            | 0.10        | 45     |  0.0987 |  1.42  |
| 45            | 0.05        | 41     |  0.1021 |  1.51  |
...
```

**Implementation approach:**

Use `itertools.product` to generate all parameter combinations.  For each
combination, call the strategy function with `raw=True`, compute summary
metrics, and collect results.  Sort by the requested metric.

---

### 3. `compare_strategies` — Side-by-Side Comparison

**Purpose:** Run 2-4 explicitly named strategies with identical parameters and
return a unified comparison table.

**Why the AI needs this:** Users frequently ask *"Should I use an iron condor
or iron butterfly?"*  Today the AI runs them separately and tries to remember
the first result while processing the second.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `strategies` | `string[]` | 2-4 strategy names to compare |
| *(all standard strategy params)* | | Shared parameters |

**Output:**

```
| metric         | iron_condor | iron_butterfly | short_straddle |
|----------------|-------------|----------------|----------------|
| trades         | 287         | 245            | 312            |
| mean           |  0.0712     |  0.0543        |  0.0892        |
| median         |  0.0534     |  0.0421        |  0.0654        |
| std            |  0.0832     |  0.0987        |  0.1243        |
| win_rate       |  0.72       |  0.65          |  0.63          |
| sharpe         |  1.18       |  0.95          |  0.72          |
| profit_factor  |  2.01       |  1.78          |  1.56          |
| max_drawdown   | -0.4521     | -0.6234        | -0.8901        |
| best_trade     |  0.3201     |  0.2987        |  0.4523        |
```

This is similar to `scan_strategies` but intentionally limited to a small
set and includes more detailed metrics since there are fewer strategies to
display.

---

### 4. `analyze_trades` — Trade-Level Analytics

**Purpose:** Compute detailed analytics on raw trade results that go beyond
what the default aggregated output provides.

**Why the AI needs this:** The current `run_strategy` with `raw=False` only
returns descriptive statistics grouped by DTE/OTM buckets.  There's no win
rate, no Sharpe, no profit factor, no drawdown curve.  With `raw=True` the AI
gets individual trades but has to mentally compute statistics — which LLMs are
bad at.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `strategy_name` | `string` | Strategy to analyze |
| `group_by` | `string` (optional) | Additional grouping: `"month"`, `"weekday"`, `"dte_range"`, `"otm_pct_range"`. Default: overall (no grouping). |
| *(all standard strategy params)* | | Strategy parameters |

**Output (overall mode):**

```
Summary for short_put_spread (312 trades, 2018-01-03 to 2023-12-28):

| metric              | value   |
|---------------------|---------|
| total_trades        | 312     |
| winners             | 212     |
| losers              | 100     |
| win_rate            | 0.6795  |
| mean_return         | 0.0843  |
| median_return       | 0.0621  |
| std_return          | 0.0987  |
| sharpe_ratio        | 0.854   |
| profit_factor       | 2.14    |
| avg_winner          | 0.1523  |
| avg_loser           | -0.0612 |
| max_win             | 0.4521  |
| max_loss            | -0.3201 |
| expectancy          | 0.0843  |
| payoff_ratio        | 2.49    |
```

**Output (grouped by month):**

```
| month | trades | win_rate | mean    | sharpe |
|-------|--------|----------|---------|--------|
| Jan   | 26     | 0.73     |  0.0921 |  1.32  |
| Feb   | 24     | 0.71     |  0.0843 |  1.18  |
| Mar   | 28     | 0.54     | -0.0123 | -0.15  |
...
```

This lets the AI discover seasonality, day-of-week effects, and which
DTE/OTM buckets drive performance.

**Metrics glossary:**

- **win_rate**: winners / total_trades
- **sharpe_ratio**: mean_return / std_return (simple, non-annualized)
- **profit_factor**: gross_profit / gross_loss
- **expectancy**: (win_rate * avg_winner) + ((1 - win_rate) * avg_loser)
- **payoff_ratio**: avg_winner / abs(avg_loser)

---

### 5. `best_buckets` — Top Performing Segments

**Purpose:** Find the top N DTE/OTM/delta segments across one or more
strategies, ranked by a chosen metric.

**Why the AI needs this:** The current aggregated output returns *all* buckets
for one strategy.  The AI has to scan a 30+ row table to find the good ones.
This tool does the scanning automatically across multiple strategies.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `strategies` | `string[]` (optional) | Strategies to scan (default: all non-calendar) |
| `sort_by` | `string` | `"mean"`, `"median"`, `"count"`, `"sharpe"`. Default: `"mean"` |
| `min_count` | `integer` | Minimum trade count for a bucket to qualify (default 10). Filters noise. |
| `top_n` | `integer` | Number of top buckets to return (default 15) |
| *(standard strategy params)* | | Shared parameters |

**Output:**

```
| strategy         | dte_range | otm_pct_range | count | mean    | std    | sharpe |
|------------------|-----------|---------------|-------|---------|--------|--------|
| short_put_spread | (21, 28]  | (0.05, 0.10]  | 45    |  0.1201 | 0.0654 |  1.84  |
| iron_condor      | (28, 35]  | (0.10, 0.15]  | 38    |  0.1087 | 0.0721 |  1.51  |
| short_straddle   | (14, 21]  | (0.00, 0.05]  | 52    |  0.0954 | 0.0687 |  1.39  |
...
```

This is the single most powerful discovery tool — it answers *"Where in the
DTE/OTM space do options strategies make money?"* across all strategies at
once.

---

## Enhanced System Prompt Additions

The agent system prompt needs to teach the AI *when* to use each new tool.
Proposed additions to the `## Workflow` section:

```
## Strategy Discovery Workflow

When a user wants to FIND profitable strategies (not just run a specific one):

1. **Start broad → `scan_strategies`**
   Use category filters to match the user's market view:
   - "I'm bullish on AAPL" → scan with category="bullish"
   - "I want income" → scan with category="income"
   - "What works best?" → scan all strategies

2. **Drill into winners → `parameter_sweep`**
   Take the top 2-3 strategies from the scan and sweep their key params:
   - Sweep max_entry_dte across [14, 21, 30, 45, 60, 90]
   - Sweep max_otm_pct across [0.05, 0.10, 0.15, 0.20, 0.30]
   - 2D sweep of DTE x OTM for the best strategy

3. **Compare finalists → `compare_strategies`**
   Run the top 2-3 with their optimal params side-by-side

4. **Deep-dive → `analyze_trades`**
   For the chosen strategy, show monthly seasonality, day-of-week effects,
   and detailed risk metrics

5. **Find the sweet spot → `best_buckets`**
   Show the user exactly which DTE/OTM combinations are most profitable

## When to use which tool:

- User asks "what strategy should I use?" → scan_strategies
- User asks "what DTE is best for iron condors?" → parameter_sweep
- User asks "iron condor vs iron butterfly?" → compare_strategies
- User asks "how risky is this strategy?" → analyze_trades
- User asks "where do options make money?" → best_buckets
- User asks "run a long call spread" → run_strategy (existing tool)
```

---

## Greeks-Aware Search (Future Enhancement)

The EODHD advanced guide highlights that professionals think in terms of Greek
exposures, not strategy names.  A future enhancement could add a
`search_by_greeks` tool:

**Concept:**

| Parameter | Type | Description |
|---|---|---|
| `target_delta` | `float` (optional) | Desired net delta exposure (e.g. 0.0 for neutral) |
| `target_theta` | `string` (optional) | `"positive"` (collect decay) or `"negative"` (pay for optionality) |
| `target_vega` | `string` (optional) | `"positive"` (long vol) or `"negative"` (short vol) |
| `target_gamma` | `string` (optional) | `"positive"` or `"negative"` |

This would internally map to appropriate strategies:

- delta-neutral + positive theta + negative vega → iron condor, iron butterfly, short straddle
- delta-neutral + negative theta + positive vega → long straddle, long strangle, reverse iron condor
- positive delta + positive theta → short puts, bull put spread, covered call

**Prerequisite:** This requires the dataset to include Greek columns (delta at
minimum).  The tool would validate this and fall back to strategy-name-based
search if Greeks aren't available.

This is not proposed for the initial implementation but is a natural extension
once the core search tools are in place.

---

## Signal-Enhanced Scanning (Future Enhancement)

The EODHD beginner guide shows that combining technical signals with entry
timing changes results dramatically.  Optopsy already has signals (`rsi_below`,
`rsi_above`, `sma_below`, `sma_above`, `day_of_week`, `and_signals`,
`or_signals`) but they aren't exposed to the AI chat at all.

**Proposed approach:**

Add a `signals` parameter to `scan_strategies` and `parameter_sweep`:

```json
{
  "signals": {
    "entry": {
      "type": "and",
      "conditions": [
        {"signal": "rsi_below", "period": 14, "threshold": 30},
        {"signal": "day_of_week", "days": [3]}
      ]
    },
    "exit": {
      "type": "or",
      "conditions": [
        {"signal": "rsi_above", "period": 14, "threshold": 70}
      ]
    }
  }
}
```

The tool would construct the appropriate `and_signals()` / `or_signals()`
compositions and pass them as `entry_signal` / `exit_signal` to each strategy.

This would let the AI answer questions like:
- *"Do iron condors work better when entered on oversold RSI days?"*
- *"What's the best strategy to enter when price is above the 50-day SMA?"*

**Not proposed for initial implementation** because the combinatorial space
(strategy x params x signals) is large and could be slow.  Better to get the
core search tools working first.

---

## Implementation Priority

| Priority | Tool | Effort | Impact |
|----------|------|--------|--------|
| **P0** | `scan_strategies` | Medium | Highest — unlocks "what's best?" questions |
| **P0** | `analyze_trades` | Low | High — proper metrics for any strategy result |
| **P1** | `parameter_sweep` | Medium | High — finds optimal params automatically |
| **P1** | `compare_strategies` | Low | Medium — cleaner than manual comparison |
| **P2** | `best_buckets` | Medium | Medium — cross-strategy bucket discovery |
| **P3** | `search_by_greeks` | High | Medium — requires Greek data in dataset |
| **P3** | Signal-enhanced scanning | High | Medium — combinatorial complexity |

P0 items should be built first.  They cover the two most common user intents:
*"What strategy should I use?"* and *"How good is this strategy, really?"*

---

## Performance Considerations

- **`scan_strategies` running all 28 strategies** could be slow on large
  datasets.  Mitigation: run non-calendar strategies first (they share the same
  data pipeline), skip strategies that require data columns not present (e.g.,
  skip delta-filtered strategies when no delta column exists).  Consider running
  strategies in parallel using `concurrent.futures`.
- **`parameter_sweep` with 2D sweeps** can generate many combinations (e.g.,
  6 DTE values x 5 OTM values = 30 runs).  Mitigation: cap at 50 combinations
  per sweep call and warn the user if they request more.
- **Memory**: All tools compute results from `raw=True` trades and discard
  intermediate DataFrames.  Only the summary metrics table is kept.
- **LLM token budget**: All new tools should follow the existing pattern of
  returning a compact `llm_summary` (table + key insight) to the AI and a
  richer `user_display` to the UI.

---

## Testing Strategy

Each new tool needs:

1. **Unit tests** using the existing test fixtures in `conftest.py` (the
   `data` and `multi_strike_data` fixtures provide enough rows for basic
   strategy runs)
2. **Edge cases**: empty results, single-strategy scan, sweep with one value,
   dataset missing optional columns
3. **Integration test**: load sample data, run `scan_strategies`, verify the
   output has expected columns and is sorted correctly

---

## Summary

These five tools transform the AI from a manual strategy runner into an
autonomous strategy discovery engine.  The user says *"Find me the best income
strategy for SPX"* and the AI can:

1. `scan_strategies(category="income")` to find the top candidates
2. `parameter_sweep(strategy="short_put_spread", sweep_param="max_entry_dte")`
   to optimize the winner
3. `analyze_trades(strategy="short_put_spread", group_by="month")` to check
   for seasonality
4. Present a complete recommendation with supporting data

Instead of 12+ tool calls and mental arithmetic, this takes 3 focused calls
with proper statistical metrics at every step.
