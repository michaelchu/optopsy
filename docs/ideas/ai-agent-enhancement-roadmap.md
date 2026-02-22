# AI Agent Enhancement Roadmap

Ideas for extending the optopsy chat agent, ranked by impact vs. effort. Each section describes the gap, a concrete approach, and where it fits in the codebase.

## Priority ranking

| # | Feature | Impact | Effort | Rationale |
|---|---|---|---|---|
| 1 | Risk metrics (Sharpe, VaR, etc.) | High | Low | Extends simulate output with standard formulas |
| 2 | IV rank signals | High | Medium | Differentiator — every options trader wants this |
| 3 | Strategy comparison report | High | Low | Structures data the agent already produces |
| 4 | Saved workflows | High | Medium | Eliminates repetitive multi-step prompts |
| 5 | Portfolio construction | Very High | High | Unique capability, but significant engineering |
| 6 | Autonomous research mode | High | Medium | Mostly prompt engineering + orchestration logic |
| 7 | What-if scenario tool | Medium | Medium | Useful but requires good Greeks data |

---

## 1. Risk metrics from simulations

### Gap

The `simulate` tool (`tools/_executor.py`) tracks capital, positions, and equity curves, but the output lacks standard risk-adjusted metrics. Users get raw P&L and equity values but can't evaluate risk-adjusted performance without manual calculation. The aggregated strategy output (`core.py`) uses `DataFrame.describe()` which gives count/mean/std/percentiles of `pct_change` — useful but not what a trader needs to evaluate a strategy.

### Metrics to add

- **Sharpe ratio**: `mean(returns) / std(returns) * sqrt(252)` — annualized, using daily equity curve returns
- **Sortino ratio**: Like Sharpe but only penalizes downside deviation — more appropriate for asymmetric options payoffs
- **Max drawdown**: Largest peak-to-trough decline in the equity curve — already have the equity series, just need `(peak - trough) / peak`
- **Value at Risk (VaR)**: 95th/99th percentile daily loss — `np.percentile(returns, 5)`
- **Conditional VaR (CVaR)**: Mean of losses beyond VaR — `returns[returns <= var].mean()`
- **Win rate**: `count(pnl > 0) / count(all trades)` — trivial but missing from aggregated output
- **Profit factor**: `sum(winning trades) / abs(sum(losing trades))`
- **Calmar ratio**: `annualized_return / max_drawdown`

### Where it fits

- **Simulation metrics**: Extend the simulate handler in `tools/_executor.py`. The equity curve DataFrame is already computed — these are all derived from it. Add a `_compute_risk_metrics(equity_df)` helper that returns a dict, include it in both `llm_summary` and `user_display`.
- **Aggregated strategy metrics**: Extend `core._process_strategy()` to compute win rate and profit factor from the raw `pct_change` column before calling `.describe()`. These two metrics require only the existing data.
- **ToolResult enrichment**: Add the metrics dict to `self.results` entries so the agent can reference them in later comparisons without re-running.

### Impact

Low effort, high value. Every metric is a one-liner on data the system already produces. Transforms the output from "here are some stats" to "here's whether this strategy is worth trading."

---

## 2. IV rank signals

### Gap

Implied volatility is the most important variable in options pricing but is completely absent from the analysis pipeline. The EODHD API returns `impliedVolatility` but it's dropped during column normalization in `providers/eodhd.py`. The signal system (`signals.py`) has 12 technical signals — all price/volume based — but none for IV.

### Approach

**Phase 1 — Preserve IV through the pipeline:**
- Update EODHD provider's column mapping to retain `implied_volatility`
- Update `core.py` to pass through extra columns beyond the required 8 (underlying_symbol, underlying_price, option_type, expiration, quote_date, strike, bid, ask)
- Add `iv` to the leg output definitions in `definitions.py`

**Phase 2 — IV rank/percentile signal:**
- Add `iv_rank_above` and `iv_rank_below` signals to `signals.py` and `SIGNAL_REGISTRY` in `tools/_schemas.py`
- IV rank = percentile of current ATM IV relative to trailing N-day range (default 252 days)
- Compute from the options dataset itself: for each quote_date, find the ATM option, get its IV, rank against the trailing window
- No external data dependency — works on any dataset that includes IV

**Phase 3 — IV surface tools:**
- `plot_vol_surface` tool: 3D surface or heatmap of IV by strike/expiration for a given quote date
- `iv_term_structure` tool: IV across expirations for ATM options on a given date
- Both use existing `create_chart` infrastructure (Plotly figures attached to ToolResult)

### Impact

Unlocks the most-asked question in options backtesting: "do iron condors work better in high-IV environments?" This is a genuine differentiator — most backtesting tools don't offer IV-conditional entry signals.

---

## 3. Strategy comparison report

### Gap

The agent already stores results in `self.results` (added to address the earlier eval doc's recommendation), but there's no tool to produce a structured side-by-side comparison. The agent must describe differences in prose, which is slow and loses precision. `scan_strategies` produces a comparison table across parameter combinations, but not across arbitrary prior runs.

### Approach

- **`compare_results` tool**: Accept a list of result labels (keys from `self.results`). Produce a comparison table with one row per result, columns for: strategy name, parameters, trade count, mean return, win rate, Sharpe, max drawdown, profit factor.
- If risk metrics (item #1) are already computed and stored in `self.results`, this is purely a formatting tool — pull the metrics, build a DataFrame, render as markdown table for the user and a compact summary for the LLM.
- Include a "verdict" row highlighting the best performer on each metric.
- Optionally attach a grouped bar chart (Plotly) comparing key metrics across results.

### Dependencies

Best built after item #1 (risk metrics) so there are meaningful metrics to compare. Without risk metrics, the comparison table only has mean/std from `.describe()`.

### Impact

Low effort — the data already exists in `self.results`, this just structures and presents it. Eliminates the most common multi-turn pattern: "run strategy A... now run strategy B... now compare them."

---

## 4. Saved workflows

### Gap

Users repeat the same multi-step sequences across sessions: fetch SPY data, load it, run a specific strategy with specific parameters, compare against a baseline. Each session starts fresh (`OptopsyAgent.__init__` resets all state). The Chainlit persistence layer saves message history for resume, but there's no way to save and replay a sequence of tool calls as a reusable workflow.

### Approach

- **`save_workflow` tool**: Capture the current session's tool call sequence (already tracked in message history) as a named workflow. Store to `~/.optopsy/workflows/{name}.json` with:
  - Ordered list of tool calls with their arguments
  - Optional parameter placeholders (e.g., `$SYMBOL`, `$START_DATE`) for reuse with different inputs
  - Metadata: creation date, description, last-used date

- **`run_workflow` tool**: Load a saved workflow by name, resolve any placeholders from provided arguments, and execute the tool sequence. Each step feeds its output state (dataset, signals) into the next, just like the normal agent loop but without LLM round-trips.

- **`list_workflows` / `delete_workflow` tools**: Management utilities.

- **Session start integration**: On `on_chat_start` in `app.py`, list available workflows in the welcome message so the user can say "run my SPY analysis workflow."

### Considerations

- Workflow replay skips the LLM entirely — it's deterministic execution of a recorded sequence. This means it's fast but can't adapt if data has changed (e.g., a strategy that returned results last week might return nothing on new data).
- Need to handle failures gracefully: if step 3 of 5 fails, report the failure and stop (don't blindly continue).
- Placeholder resolution should support defaults: `$SYMBOL` defaults to `SPY` if not provided.

### Impact

Eliminates the "every session starts from scratch" problem. Power users who have a standard analysis routine can replay it in one command instead of 5-10 prompts.

---

## 5. Portfolio construction

### Gap

The `simulate` tool handles single-strategy, single-symbol backtesting with capital tracking. Real portfolio analysis requires running multiple strategies across multiple underlyings simultaneously, with shared capital and risk constraints. Currently, comparing a portfolio of strategies requires multiple independent simulate runs with no way to model capital allocation, correlation, or position limits across them.

### Approach

**Phase 1 — Multi-strategy simulation:**
- Extend `simulate` to accept a list of `(strategy, params, dataset_name)` tuples
- Each strategy generates trades independently from its own dataset
- Capital allocation modes: equal-weight, risk-parity, or fixed-notional per strategy
- Output: combined equity curve, per-strategy contribution breakdown, correlation matrix of strategy returns

**Phase 2 — Portfolio constraints:**
- `max_positions`: Limit total open positions across all strategies
- `max_notional`: Cap total capital deployed at any point
- `max_delta`: Cap net portfolio delta (requires Greeks — depends on IV integration)
- `stop_loss` / `profit_target`: Position-level exit rules independent of DTE

**Phase 3 — Walk-forward analysis:**
- Split data into in-sample/out-of-sample windows (rolling or anchored)
- Optimize parameters on in-sample, test on out-of-sample
- Report in-sample vs. out-of-sample performance degradation
- Key for detecting overfitting — "did this strategy work because the parameters are good, or because they were fit to this specific data?"

### Where it fits

- Phase 1 extends the existing `simulate` handler in `tools/_executor.py`
- Phase 2 adds constraint parameters to the same handler
- Phase 3 is a new `walk_forward` tool that wraps optimize + simulate in a loop
- All phases build on the multi-dataset system (`self.datasets`) already in place

### Impact

Very high impact but significant engineering. This is a unique capability — most options backtesting tools don't offer portfolio-level simulation. Would be a major differentiator, but Phase 2+ depends on Greeks data (IV integration) for delta-based constraints.

---

## 6. Autonomous research mode

### Gap

The agent currently requires the user to drive each step: "fetch data", "run this strategy", "now try that one", "compare them." For exploratory questions like "what's the best options strategy for SPY in the current environment?", the agent should be able to autonomously plan and execute a multi-step research workflow without per-step prompting.

### Approach

- **`research` tool or prompt mode**: Accept a research question (e.g., "find the best-performing strategy for SPY over the last year"). The agent then:
  1. Plans a research sequence (fetch data, identify available DTE/strike ranges via `suggest_strategy_params`, select candidate strategies)
  2. Runs `scan_strategies` with broad parameters to get an overview
  3. Narrows to the top 3-5 performers
  4. Runs focused backtests with refined parameters on the top candidates
  5. Compares results (using the comparison report from item #3)
  6. Presents a structured finding with confidence level

- **Implementation**: This is primarily prompt engineering + orchestration logic:
  - Add a "research mode" system prompt section that teaches the agent the research methodology
  - Raise `_MAX_TOOL_ITERATIONS` for research mode (or make it configurable per-request)
  - Use the existing tool infrastructure — no new tools needed, just better sequencing
  - The agent's own reasoning drives the workflow; the prompt guides the methodology

- **Guard rails**:
  - Cap research mode at 25 iterations (vs. the normal 15)
  - Require user confirmation before starting ("I'll research this by running ~10 backtests across 5 strategies. Proceed?")
  - Summarize progress at checkpoints ("Scanned 28 strategies, narrowing to top 5...")

### Considerations

- Quality depends heavily on the LLM's ability to follow a multi-step research plan without drifting. The system prompt needs to be prescriptive about methodology.
- Token costs will be higher per conversation — compaction becomes even more important.
- Risk of "runaway" research if the agent keeps finding interesting tangents. The iteration cap and checkpoint confirmations mitigate this.

### Impact

High impact, medium effort. Mostly prompt engineering with minor code changes (iteration limit, confirmation flow). Transforms the agent from a tool executor into a research assistant.

---

## 7. What-if scenario tool

### Gap

Users want to ask "what would happen to my iron condor if SPY drops 5% tomorrow?" or "how does this position perform if IV spikes 20%?" Currently there's no way to model hypothetical scenarios — all analysis is on historical data as-is.

### Approach

- **`what_if` tool**: Accept a result label (from `self.results`) and a set of scenario adjustments:
  - `price_change_pct`: Shift underlying price by X% (recomputes moneyness and P&L)
  - `iv_change_pct`: Shift IV by X% (requires Greeks — delta, gamma, vega from the dataset)
  - `days_forward`: Fast-forward time by N days (theta decay)
  - `spread_widen_pct`: Widen bid-ask spreads by X% (liquidity shock)

- **Greeks requirement**: Meaningful what-if analysis requires delta, gamma, theta, vega for each leg. Two paths:
  1. **Data-driven**: If the dataset includes Greeks (Tradier, or EODHD with Greeks preserved), use them directly
  2. **Model-driven**: Compute Greeks from Black-Scholes given strike, underlying, DTE, IV, and risk-free rate. This is self-contained but adds a pricing model dependency.

- **Output**: For each scenario, show the adjusted P&L, the change from the base case, and which legs drove the change. Attach a scenario comparison chart.

### Considerations

- Without Greeks data, this tool has limited utility — price changes can be modeled mechanically (new intrinsic value), but IV and time effects need Greeks.
- The Black-Scholes path is well-understood but adds a dependency (scipy for the normal CDF, or a pure-Python implementation).
- Best implemented after IV integration (item #2) so there's actual IV data to perturb.

### Impact

Medium impact, medium effort. Very useful for position analysis ("should I hold or close?") but depends on Greeks availability. Most valuable when combined with the IV integration work.

---

## Additional ideas (unranked)

These are worth tracking but don't rise to the priority level of the 7 items above.

### Agent evaluation and testing

The agent has no end-to-end tests. A deterministic replay harness (mock LLM responses, assert on tool call sequences and final state) would catch regressions in the agent loop without requiring live LLM calls. Important infrastructure but not a user-facing feature.

### Additional data providers

Only EODHD is implemented. Tradier (free delayed data with Greeks) and Polygon.io are strong candidates. Each follows the existing `DataProvider` pattern — subclass, implement, register. Broadens the user base but doesn't add new capabilities.

### Conversation export

`export_session` tool to generate markdown/HTML reports or Jupyter notebooks from a chat session. Bridges interactive exploration and reproducible research. Moderate effort, nice-to-have.

### Agent memory across sessions

Persist user preferences, parameter presets, and session summaries to `~/.optopsy/user_profile.json`. Inject into system prompt on session start. Reduces repetitive setup but not transformative.
