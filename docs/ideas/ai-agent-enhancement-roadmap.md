# AI Agent Enhancement Roadmap

Ideas for extending the optopsy chat agent beyond its current capabilities, organized by theme. Each section describes the gap, a concrete approach, and expected impact.

## 1. Agent evaluation and testing

### Gap

The agent has no end-to-end tests. `test_tools_*.py` covers individual tool execution, and `test_cli.py` covers the CLI, but there are no tests for the agent loop itself — multi-turn conversations, tool-calling sequences, error recovery, or history compaction behavior.

### Approach

- **Deterministic replay harness**: Record LLM responses from real conversations as fixtures. Replay them against `OptopsyAgent` with a mock LLM client that returns canned responses in sequence. Assert on tool call order, final state (datasets, signals, results), and user-facing output.
- **Scenario library**: Build a set of canonical scenarios: "load CSV and run single strategy", "fetch EODHD data with cache hit", "build composite signal and run scan", "hit 15-iteration limit gracefully". Each scenario is a JSON file with messages and expected tool calls.
- **Compaction regression tests**: Verify that history compaction preserves tool_call/tool message pairing (breaking this causes LLM confusion). Test that results in `self.results` survive compaction even when their original tool messages are truncated.

### Impact

Catches regressions in the agent loop — especially around compaction, error handling, and provider fallback — without requiring live LLM calls.

## 2. Additional data providers

### Gap

Only EODHD is implemented. The `DataProvider` ABC is designed for extension but no other providers exist. Users without an EODHD key are limited to local CSV files.

### Candidates

| Provider | Data | Free tier | Notes |
|---|---|---|---|
| **Tradier** | Options chains, greeks, IV | 5,000 calls/day (delayed) | REST API, good docs, delayed data is free |
| **Polygon.io** | Options, stocks, indices | 5 calls/min (free) | Websocket support for real-time |
| **CBOE DataShop** | VIX, term structure, skew | Public downloads | No API key needed for index data |
| **Yahoo Finance** | Options chains (limited) | Unlimited (scraping) | Already have yfinance for stocks; options chains are available but less reliable |

### Approach

Each provider follows the existing pattern:
1. Subclass `DataProvider` in `providers/`
2. Implement `get_tool_schemas()`, `execute()`, `get_arg_model()`
3. Register in `providers/__init__.py`
4. Provider auto-detected when env key is set

For Tradier specifically:
- `fetch_options_data` tool (same interface as EODHD, different backend)
- `fetch_options_chain_snapshot` for current-day chains (useful for "what's trading now?")
- Greeks columns (delta, gamma, theta, vega) preserved through the pipeline — requires `core.py` passthrough for extra columns

### Impact

Broadens the user base significantly. Most users don't have EODHD keys but many have Tradier or Polygon accounts.

## 3. Implied volatility integration

### Gap

IV is the most important variable in options pricing but is absent from the analysis pipeline. The EODHD API returns `impliedVolatility` but it's dropped during normalization. There's no way to filter by IV, rank strategies by IV regime, or visualize the vol surface.

### Approach

**Phase 1 — Preserve IV through the pipeline:**
- Update EODHD provider's column mapping to retain `implied_volatility` (currently normalized away)
- Update `core.py` to pass through extra columns beyond the required 8 (underlying_symbol, underlying_price, option_type, expiration, quote_date, strike, bid, ask)
- Add `iv` to the leg output definitions in `definitions.py`

**Phase 2 — IV-aware filtering:**
- Add `iv_rank_min`/`iv_rank_max` parameters to `run_strategy` — filter entries by IV rank (percentile of current IV relative to trailing N-day range)
- Requires computing IV rank from the dataset itself (no external dependency)

**Phase 3 — Vol surface tools:**
- `plot_vol_surface` tool: 3D surface or heatmap of IV by strike/expiration for a given quote date
- `iv_term_structure` tool: IV across expirations for ATM options on a given date
- Both use `create_chart` infrastructure (Plotly figures attached to ToolResult)

### Impact

Unlocks the most-asked question in options backtesting: "does this strategy work better in high-IV environments?" Also enables vol surface visualization, which is valuable for understanding skew and term structure.

## 4. Custom strategy builder

### Gap

The 28 strategies cover standard structures, but users frequently want custom combinations — ratio spreads (1x2, 1x3), jade lizards (short put + short call spread), broken-wing butterflies (unequal wing widths), or custom multi-leg positions.

### Approach

- **`build_custom_strategy` tool**: Accept a list of leg definitions, each with: `option_type` (call/put), `side` (long/short), `quantity`, `otm_pct` (target moneyness), and optional `dte_offset` (for diagonals).
- Under the hood, call `core._strategy_engine()` directly with dynamically constructed leg definitions and skip the hardcoded strategy functions.
- Validation: Ensure legs are compatible (same underlying, overlapping dates), warn on undefined-risk positions.
- The tool returns the same ToolResult format as `run_strategy`, so comparison with standard strategies works seamlessly.

### Impact

Removes the constraint that users must use predefined structures. Power users can test arbitrary multi-leg positions without writing code.

## 5. Strategy optimization via parameter sweeps

### Gap

`scan_strategies` does Cartesian product sweeps across strategies, DTE, and OTM, but there's no tool for focused single-parameter optimization. The agent must call `run_strategy` repeatedly to find the best DTE for a given strategy, consuming iterations quickly.

### Approach

- **`optimize_parameter` tool**: Accept a strategy, a parameter to sweep (e.g., `max_entry_dte`), a range (start, stop, step), and a target metric (e.g., `mean_return`, `win_rate`, `sharpe`).
- Run the strategy for each parameter value in a single tool call.
- Return a table of parameter_value vs. metric, plus the optimal value.
- Optionally return a line chart showing the metric across the parameter range.

This is distinct from `scan_strategies` because:
- It sweeps a continuous range of a single parameter (not a Cartesian product)
- It targets a specific optimization metric
- It includes visualization of the parameter sensitivity curve

### Impact

Turns a 10-iteration agent workflow into 1 tool call. Essential for answering "what's the optimal X?" questions efficiently.

## 6. Enhanced simulation capabilities

### Gap

The `simulate` tool runs chronological portfolio simulation with capital tracking, but it's limited to a single strategy on a single symbol. Real portfolio backtesting requires:
- Multiple strategies running simultaneously
- Multiple underlyings
- Portfolio-level risk constraints (max positions, sector limits, delta budget)

### Approach

**Phase 1 — Multi-strategy simulation:**
- Extend `simulate` to accept a list of `(strategy, params, dataset_name)` tuples
- Each strategy generates trades independently
- Capital allocation: equal-weight, risk-parity, or fixed-notional per strategy
- Output: combined equity curve, per-strategy contribution, correlation matrix

**Phase 2 — Portfolio constraints:**
- `max_positions`: Limit total open positions across all strategies
- `max_delta`: Cap net portfolio delta (requires greeks — see IV integration)
- `stop_loss` / `profit_target`: Position-level exit rules independent of DTE

**Phase 3 — Walk-forward analysis:**
- Split data into in-sample/out-of-sample windows
- Optimize parameters on in-sample, test on out-of-sample
- Report in-sample vs. out-of-sample degradation

### Impact

Moves from "does this strategy work?" to "does this portfolio work?" — a much more realistic question for actual trading.

## 7. Conversation export and reporting

### Gap

Analysis sessions produce valuable insights but they're trapped in the Chainlit chat interface. Users can't export a session as a report, share findings with others, or reproduce an analysis later.

### Approach

- **`export_session` tool**: Generate a markdown or HTML report from the current conversation:
  - Include all strategy results from `self.results`
  - Embed chart images (Plotly figures exported as static images)
  - Include parameter settings and data sources used
  - Add a "methodology" section derived from the tool call sequence
- **`export_notebook` tool**: Generate a Jupyter notebook that reproduces the analysis:
  - Each tool call becomes a code cell using the optopsy Python API
  - Markdown cells with the agent's commentary
  - Users can re-run, modify, and extend the analysis

### Impact

Bridges the gap between interactive exploration and reproducible research. Users get both the speed of chat-driven analysis and the rigor of documented methodology.

## 8. Streaming large results

### Gap

Large DataFrames are truncated before being sent to the LLM (50-row cap in display, compaction to first line after 300 chars). This means the agent loses access to detailed results almost immediately. For raw-mode backtests with hundreds of trades, the agent can only see a sample.

### Approach

- **Result pagination**: Instead of truncating, store full results in `self.results` (already done) and add a `get_result_detail` tool that retrieves specific slices: "show trades 50-100 from result X", "show trades where pct_change < -0.05", "show trades on date 2024-03-15".
- **Summary statistics in compacted messages**: When compacting a tool result, replace it with computed summary stats (win rate, mean return, trade count) rather than just the first line. This preserves analytical value even after compaction.
- **Lazy chart generation**: Instead of pre-generating charts, let the agent request specific visualizations of stored results: "histogram of returns for result X", "scatter of DTE vs return for result X".

### Impact

The agent retains analytical access to all results throughout the conversation, even after compaction. Enables deeper follow-up analysis without re-running strategies.

## 9. Real-time signal monitoring

### Gap

Signals are currently only used for historical backtesting. Users can't ask "tell me when RSI drops below 30 on SPY" and get notified.

### Approach

- **`watch_signal` tool**: Accept a symbol, signal name, and parameters. Register a polling job that checks the signal condition on a configurable interval (e.g., every 5 minutes during market hours).
- Use yfinance's real-time data (1-minute bars) as the data source.
- When the signal fires, send a Chainlit message to the user's session with the signal details and current market state.
- Limit to 3 active watches per session to prevent resource exhaustion.

### Considerations

- This is a significant architectural change — the agent currently has no background task system.
- Would need a lightweight scheduler (asyncio task or threading timer) managed by the agent.
- Market hours awareness (no point polling on weekends).
- Chainlit's WebSocket connection must remain active for notifications.

### Impact

Transforms the agent from a historical analysis tool into a real-time assistant. High user value but significant implementation complexity.

## 10. Agent memory across sessions

### Gap

Each chat session starts fresh. The agent has no memory of previous sessions — no awareness of strategies the user has explored before, preferred parameters, or prior findings. The SQLite persistence stores message history for resume, but the agent doesn't learn from past sessions.

### Approach

- **User profile store**: Persist key preferences and findings to `~/.optopsy/user_profile.json`:
  - Preferred symbols and strategies
  - Parameter presets ("my usual SPY iron condor settings")
  - Bookmarked results ("the short put strategy from last Tuesday")
- **Session summary**: At the end of each session, generate a 1-paragraph summary of what was explored and what was found. Store in the profile.
- **Session start injection**: On `on_chat_start`, load the profile and inject a system message: "In previous sessions, the user explored X, Y, Z. Their preferred settings are..."

### Impact

Reduces repetitive setup across sessions. The agent becomes a persistent research assistant rather than a stateless tool.

## Priority ranking

Roughly ordered by impact-to-effort ratio:

1. **Agent evaluation and testing** — Low effort, prevents regressions, enables confident iteration on everything else
2. **Implied volatility integration (Phase 1)** — Moderate effort (mostly column passthrough), unlocks the most-requested analysis dimension
3. **Strategy optimization tool** — Low effort (builds on existing scan infrastructure), eliminates the most common multi-turn bottleneck
4. **Streaming large results** — Moderate effort, fixes a fundamental limitation of the current compaction system
5. **Additional data providers (Tradier)** — Moderate effort (follows existing pattern), broadens user base
6. **Conversation export** — Moderate effort, high value for users who want to share or reproduce findings
7. **Enhanced simulation** — High effort, high value for portfolio-level analysis
8. **Custom strategy builder** — Moderate effort, high value for power users
9. **Agent memory across sessions** — Low-moderate effort, quality-of-life improvement
10. **Real-time signal monitoring** — High effort, transformative but architecturally complex
