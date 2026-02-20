# AI Agent Backtesting Architecture Evaluation

An evaluation of the optopsy chat agent architecture for AI-driven options strategy exploration.

## What works well

### Tool decomposition is sound

The four core tools (`list_data_files`, `load_csv_data`/`fetch_eodhd_options`, `preview_data`, `run_strategy`) map cleanly to the data-load-then-backtest workflow. The agent doesn't have to manage DataFrames directly — it just passes parameter dicts and gets results back.

### LLM/UI output split is well-designed

`ToolResult` with separate `llm_summary` and `user_display` is a good pattern. The LLM gets compact stats while the user sees full tables. This is critical for keeping token budgets manageable across multi-tool explorations.

### Signal system is well-abstracted

The 13 signals in `SIGNAL_REGISTRY` with string-name resolution and optional `params`/`days` overrides give the LLM a clean interface. The agent doesn't need to construct function objects — it just passes `"rsi_below"` and `{"threshold": 40}`.

### Strategy coverage is comprehensive

28 strategies covering single-leg, spreads, butterflies, iron condors, calendars, diagonals, covered calls, and protective puts. The parameterization (DTE, OTM%, slippage, signals) gives meaningful exploration axes.

## Structural problems for exploration

### 1. No way to compare results across runs

This is the biggest gap. The agent's exploratory value depends on comparing strategies, parameters, or signals against each other. Currently:

- Each `run_strategy` call returns results independently.
- History compaction truncates previous tool results to a single line after the next iteration.
- The agent literally loses access to earlier backtest results mid-conversation.

An exploration agent that can't hold multiple results in working memory and compare them is severely limited. The system prompt tells the agent to "run both strategies and compare", but the architecture actively works against this by compacting away the data it needs.

### 2. Single active dataset

`OptopsyAgent` holds one `self.dataset`. To compare SPY vs AAPL iron condors, the agent must:

1. Fetch SPY, run strategy, mentally note results
2. Fetch AAPL (overwrites dataset), run strategy
3. Compare from (compacted) memory

There's no multi-symbol workspace.

### 3. No parameter sweep tool

The most common exploration question is "what DTE works best for short puts?" The agent's only option is calling `run_strategy` N times with different `max_entry_dte` values. With a 15-iteration cap and 1-second throttle per iteration, it can test at most ~6-7 parameter values before hitting the limit (each strategy run + the comparison response consume iterations).

A `sweep_parameter` tool that runs a strategy across a range of values and returns a comparison table would be far more efficient.

### 4. No derived metrics

The aggregated output gives `count, mean, std, min, 25%, 50%, 75%, max` of `pct_change` — that's `DataFrame.describe()`. Missing for real exploration:

- Win rate (% of trades with positive pct_change)
- Profit factor (gross profit / gross loss)
- Max drawdown (sequential losses)
- Sharpe-like ratio (mean / std is mentioned in the prompt but not computed)
- Expected value per trade

These are computable from raw trades but there's no tool to do it. The agent would have to request `raw=true`, get a 50-row-capped table, and try to compute metrics from truncated data.

### 5. No visualization

Options exploration is inherently visual — P&L profiles by strike, return distributions, DTE heatmaps. The Chainlit framework supports image/chart rendering, but no tool produces charts. The agent can only return markdown tables.

### 6. Missing IV dimension

Implied volatility is the most important variable in options pricing, but it's absent from the tooling:

- EODHD data likely includes IV but it's not surfaced.
- No IV rank/percentile filtering.
- No vol surface analysis.
- Can't answer "do iron condors work better in high-IV environments?" without IV data.

### 7. No result persistence or labeling

Each backtest is fire-and-forget. The agent can't say "save this as 'baseline'" and later "compare against baseline." For iterative exploration (tweak one parameter, compare), this forces the agent to re-run the baseline every time.

## Smaller issues

- `run_strategy` is monolithic — it handles all 28 strategies plus signals plus slippage in one function. This means the agent can't compose intermediate steps (e.g., "filter the data to March, then run a strategy").
- The 50-row cap on displayed results limits what the agent can analyze in raw mode.
- Calendar/diagonal strategies have separate DTE parameters (`front_dte_min/max`, `back_dte_min/max`) but these are silently ignored for non-calendar strategies rather than raising an error, which could confuse the agent.
- No tool to inspect the actual strikes/expirations available in data — `preview_data` shows shape and date range but not strike distribution or DTE histogram.

## Recommendations

The highest-impact additions for exploration, roughly in priority order:

### 1. `compare_strategies` tool

Accept a list of `(strategy_name, params)` tuples, run all of them on the current dataset, return a side-by-side comparison table with win rate, mean return, Sharpe, max drawdown, and trade count. This single tool would eliminate the most common multi-turn pattern.

### 2. `sweep_parameter` tool

Accept a strategy, a parameter name, and a range of values. Return a table showing how the key metric changes across the parameter space. This turns a 10-iteration workflow into 1 call.

### 3. Result memory

A lightweight dict of `{label: summary_stats}` that persists across the conversation and survives compaction. The agent can label results and refer back to them.

### 4. Richer metrics in aggregated output

Add win rate, profit factor, and mean/std ratio to the default aggregated stats. These are trivial to compute from `pct_change` and would eliminate the need for raw-mode workarounds.

### 5. `preview_data` enhancements

Include strike distribution (min/max/count by expiration), DTE histogram, and available option types. This helps the agent choose sensible parameters without trial-and-error.

### 6. A charting tool

Even a simple matplotlib-to-PNG tool for return distributions and DTE/OTM heatmaps would add significant exploration value.

## Summary

The architecture is solid for single-strategy, single-run backtesting — load data, run strategy, interpret results. But "exploring ideas" requires iteration, comparison, and memory, and those are the areas where the tooling falls short. The agent can technically explore by running strategies one at a time, but the 15-iteration cap, aggressive history compaction, single-dataset constraint, and lack of comparison/sweep tools make multi-hypothesis exploration slow and lossy. Adding 2-3 comparison-oriented tools would substantially improve the agent's ability to actually explore the strategy space.
