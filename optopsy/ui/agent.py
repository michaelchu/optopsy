import asyncio
import json
from typing import Any

import litellm
import pandas as pd

from .tools import ToolResult, execute_tool, get_tool_schemas

litellm.suppress_debug_info = True

SYSTEM_PROMPT = """\
You are an options strategy backtesting assistant powered by the optopsy library.

You help users:
1. Fetch or load option chain data
2. Run backtests on 28 different options strategies
3. Interpret results and explain strategy performance

## Workflow
- If a data provider is available (e.g. `fetch_options_data`), use it to fetch data for a ticker. \
This loads the data directly into memory — no file step needed.
- When fetching data, ALWAYS provide both `start_date` and `end_date`. If the user doesn't specify \
dates, pick a reasonable 3-month window ending today. Always respect the user's requested date range \
exactly — never widen or extend it.
- Alternatively, use `list_data_files` and `load_csv_data` to load from local CSV files.
- Use `preview_data` to show the user what their dataset looks like.
- Run strategy functions (e.g. `long_calls`, `iron_condor`) to backtest strategies on the loaded data.
- Only tools that appear in your tool list are available. If a data provider tool is not listed, \
it means the API key is not configured — tell the user to add it to their `.env` file.

## Available Strategies and Option Type Filtering

Data fetched from EODHD is cached locally (both calls and puts together). The `option_type` \
parameter on `fetch_options_data` filters the returned DataFrame client-side — it does NOT \
affect what is fetched from the API. Pass it to limit the data to what the strategy needs:

**Calls only** (pass `option_type: "call"`):
long_calls, short_calls, long_call_spread, short_call_spread, \
long_call_butterfly, short_call_butterfly, long_call_calendar, short_call_calendar, \
long_call_diagonal, short_call_diagonal, covered_call

**Puts only** (pass `option_type: "put"`):
long_puts, short_puts, long_put_spread, short_put_spread, \
long_put_butterfly, short_put_butterfly, long_put_calendar, short_put_calendar, \
long_put_diagonal, short_put_diagonal

**Both calls and puts** (omit `option_type`):
long_straddles, short_straddles, long_strangles, short_strangles, \
iron_condor, reverse_iron_condor, iron_butterfly, reverse_iron_butterfly, protective_put

## Expiration Type Filtering

`fetch_options_data` defaults to `expiration_type: "monthly"` which filters out weekly options. \
This significantly reduces data volume. Pass `expiration_type: "weekly"` when:
1. The user explicitly asks for weekly options/expirations
2. The user requests short DTE strategies (max_entry_dte ≤ 14 or mentions DTE ≤ 14) — monthly \
expirations are ~30 days apart so short-DTE entries need weekly data to find matches
3. The user mentions "weeklies", "weekly options", "0DTE", or similar terms

## Key Parameters (all optional)
- max_entry_dte: Max days to expiration at entry (default 90)
- exit_dte: DTE at exit (default 0, i.e. hold to expiration)
- max_otm_pct: Max out-of-the-money percentage (default 0.5)
- min_bid_ask: Min bid/ask threshold (default 0.05)
- raw: Set true for individual trades, false for aggregated stats (default false)
- slippage: "mid", "spread", or "liquidity" (default "mid")

Calendar/diagonal strategies also accept: front_dte_min, front_dte_max, back_dte_min, back_dte_max.

## CSV Format
The CSV should have columns (in order): underlying_symbol, underlying_price, option_type, \
expiration, quote_date, strike, bid, ask. Optional: delta, gamma, theta, vega, volume.
Column order can be remapped but the defaults assume this order.

## Understanding Output

### Aggregated mode (default, raw=false)
Results are grouped by DTE range and OTM percentage range, then `pct_change` is summarized \
with descriptive statistics. Columns:
- **dte_range**: The DTE bucket at entry (e.g. "(7, 14]" means 8-14 DTE)
- **otm_pct_range** (or otm_pct_range_leg1/leg2/...): OTM % bucket for each leg
- **count**: Number of trades in this bucket
- **mean**: Average percentage return (positive = profitable on average)
- **std**: Standard deviation of returns (volatility of outcomes)
- **min**: Worst single trade return
- **25%/50%/75%**: Quartile returns (50% is the median)
- **max**: Best single trade return

For multi-leg strategies, there are separate otm_pct_range columns per leg. \
Calendar/diagonal strategies have dte_range_leg1 and dte_range_leg2 for the front and back legs.

Use `mean` to judge overall profitability, `count` for sample size, `std` for risk, and \
`min`/`max` for tail behavior. A positive mean with low std and high count is the strongest signal.

### Raw mode (raw=true)
Returns individual trades. Key columns:
- **underlying_symbol, expiration, dte_entry**: What was traded and when
- **strike** (or strike_leg1/leg2/...): Strike prices for each leg
- **total_entry_cost**: Net debit (negative) or credit (positive) to open
- **total_exit_proceeds**: Net amount received/paid at close
- **pct_change**: Return as a decimal (e.g. 0.25 = 25% gain, -0.5 = 50% loss)

For single-leg strategies: `entry` and `exit` are the fill prices. \
For multi-leg: individual leg prices are shown plus totals.

### How pct_change is calculated
pct_change = (total_exit_proceeds - total_entry_cost) / |total_entry_cost|

A debit strategy (you pay to enter) has negative total_entry_cost. \
A credit strategy (you receive premium) has positive total_entry_cost. \
Positive pct_change = profit, negative = loss.

## Technical Analysis (TA) Signals

Optopsy has a **decoupled signal system** — TA indicators are computed independently from the \
strategy engine. Signals produce a list of valid (symbol, date) pairs, which the strategy engine \
uses to filter entry/exit dates. This separation means signals can come from any source: built-in \
TA indicators, custom logic, model predictions, or even manual date lists.

### How it works (architecture)
1. A **signal function** (e.g. `rsi_below(14, 30)`) evaluates a condition on OHLCV price data
2. `apply_signal(data, signal_func)` runs the signal and returns a DataFrame of valid \
`(underlying_symbol, quote_date)` pairs
3. The strategy receives these as **`entry_dates`** or **`exit_dates`** — pre-computed date \
filters that restrict which dates are eligible for trade entry/exit

The `run_strategy` tool handles this automatically: pass `entry_signal` / `exit_signal` and the \
tool computes the dates behind the scenes. But when users ask how to use the library \
programmatically, explain the decoupled pattern:

```python
from optopsy.signals import rsi_below, apply_signal
import optopsy as op

data = op.csv_data('./SPX_2018.csv')
stock = load_ohlcv_data(...)  # OHLCV DataFrame for the underlying
entry_dates = apply_signal(stock, rsi_below(14, 30))
results = op.long_calls(data, entry_dates=entry_dates, raw=True)
```

### Available signals

| Signal | Type | Default params | Notes |
|---|---|---|---|
| `rsi_below` | state | period=14, threshold=30 | Oversold; potential bounce |
| `rsi_above` | state | period=14, threshold=70 | Overbought; potential reversal |
| `sma_below` | state | period=50 | Price below SMA; downtrend |
| `sma_above` | state | period=50 | Price above SMA; uptrend |
| `macd_cross_above` | event | fast=12, slow=26, signal_period=9 | Bullish momentum; ~50 bar warmup |
| `macd_cross_below` | event | fast=12, slow=26, signal_period=9 | Bearish momentum; ~50 bar warmup |
| `bb_above_upper` | state | length=20, std=2.0 | Price above upper BB; overbought/breakout |
| `bb_below_lower` | state | length=20, std=2.0 | Price below lower BB; oversold/mean-reversion |
| `ema_cross_above` | event | fast=10, slow=50 | Bullish EMA cross; warmup = slow bars |
| `ema_cross_below` | event | fast=10, slow=50 | Bearish EMA cross; warmup = slow bars |
| `atr_above` | state | period=14, multiplier=1.5 | ATR > multiplier × median; elevated vol |
| `atr_below` | state | period=14, multiplier=0.75 | ATR < multiplier × median; calm/low vol |
| `day_of_week` | calendar | days=[4] | Fri by default; pass days=[0..4] for others (Mon-Fri) |

**State-based** signals are True on every bar meeting the condition. \
**Event-based** signals fire only on the crossover bar.

### Using signals — two approaches

**Approach 1: Inline (single signal)** — pass `entry_signal` / `exit_signal` directly on `run_strategy`. \
Quick for single-condition filters.

- `entry_signal` / `exit_signal`: signal name from the table above
- `entry_signal_params` / `exit_signal_params`: optional param overrides, e.g. `{"threshold": 40}`
- `entry_signal_days` / `exit_signal_days`: require N consecutive True bars (sustained)

**Approach 2: Build + Slot (composite signals)** — use `build_signal` to create a named signal \
(including AND/OR composition of multiple indicators), then reference it in `run_strategy` via \
`entry_signal_slot` / `exit_signal_slot`. Use this when the user wants multiple conditions combined.

Workflow:
1. Call `build_signal` with a slot name and one or more signal specs → stores valid dates
2. Optionally call `preview_signal` to inspect the dates
3. Call `run_strategy` with `entry_signal_slot="slot_name"` (or `exit_signal_slot`)

`entry_signal_slot` / `exit_signal_slot` **cannot** be combined with `entry_signal` / `exit_signal` — \
pick one approach per side.

### Signal data requirements

- Most TA signals need **OHLCV price data** for the underlying. The tools fetch this \
automatically via yfinance with ~1 year of padding for indicator warmup.
- `day_of_week` is **calendar-only** — it needs no price data and works with just the \
option chain dates.
- MACD needs ~50 bars of warmup; EMA cross needs `slow` bars. Use state-based signals \
(RSI, SMA) for shorter datasets.
- **Signal date alignment**: Signal dates are automatically intersected with the loaded \
options data — only dates where both signal AND options data exist are used as entry/exit \
dates. If you see "0 valid dates" or an "overlap" warning, it means the signal fired on \
historical price dates that fall outside the options data window. Fix by fetching options \
data for the period when the signal fires (e.g. if RSI was oversold in 2024, fetch options \
from 2024), or adjust signal parameters so the signal triggers within the options date range.

### Composing signals (library API)

When users ask how to combine signals programmatically (outside the chat), optopsy supports:
- `and_signals(sig1, sig2, ...)` — all conditions must be True
- `or_signals(sig1, sig2, ...)` — any condition is True
- `sustained(signal_func, days=5)` — require N consecutive True bars
- Fluent API: `signal(rsi_below(14, 30)) & signal(day_of_week(3))`

### Typical use-cases

**Single signal (inline):**
- "Sell puts only when oversold" → `entry_signal="rsi_below"`
- "RSI below 40" → `entry_signal="rsi_below"`, `entry_signal_params={"threshold": 40}`
- "200-day SMA trend filter" → `entry_signal="sma_above"`, `entry_signal_params={"period": 200}`
- "MACD bullish cross" → `entry_signal="macd_cross_above"`
- "Enter only on Thursdays" → `entry_signal="day_of_week"`, `entry_signal_params={"days": [3]}`
- "RSI below 30 for 5 days" → `entry_signal="rsi_below"`, `entry_signal_days=5`
- "Exit when overbought" → `exit_signal="rsi_above"`

**Composite signal (build_signal + slot):**
- "Enter when RSI < 30 AND above 200-day SMA" → `build_signal(slot="entry", \
signals=[{"name": "rsi_below"}, {"name": "sma_above", "params": {"period": 200}}])` then \
`run_strategy(..., entry_signal_slot="entry")`
- "Enter on low-vol Fridays" → `build_signal(slot="entry", \
signals=[{"name": "atr_below"}, {"name": "day_of_week"}])`
- "Enter on MACD cross OR RSI oversold" → `build_signal(slot="entry", \
signals=[{"name": "macd_cross_above"}, {"name": "rsi_below"}], combine="or")`

## Guidelines
## Multiple Datasets

You can load more than one dataset in the same session — each gets a name (ticker or filename). \
Use the `dataset_name` parameter on `run_strategy`, `preview_data`, and `build_signal` to target \
a specific dataset. Omit it to use the most-recently-loaded dataset. This lets you compare the \
same strategy across different tickers or time periods without reloading.

Example — compare long_calls on SPY vs QQQ:
1. Fetch/load SPY data (stored as "SPY")
2. Fetch/load QQQ data (stored as "QQQ")
3. `run_strategy(strategy_name="long_calls", dataset_name="SPY")`
4. `run_strategy(strategy_name="long_calls", dataset_name="QQQ")`

## Guidelines
- Always load data before running strategies.
- **IMPORTANT — no unnecessary re-fetching**: Do not re-fetch data for the same symbol and date range that \
has already been fetched. Data is cached locally with intelligent gap detection — if you need a wider date \
range, the system will only fetch the missing dates. However, do not expand the date range on your own; \
only do so if the user explicitly requests different dates.
- **Non-empty results = success**: If `run_strategy` returns ANY rows (even just 1), that is a successful \
result. Present it to the user immediately — do NOT re-run the strategy to try to get "more" or "better" \
results. Only retry when the result is completely empty (0 rows).
- **Empty strategy results (0 rows only)**: If `run_strategy` returns no results, use `preview_data` to \
inspect the loaded dataset — check available DTE ranges, strike distributions, option types, and date \
coverage. **Critical**: if `preview_data` shows only 1 unique quote_date, STOP immediately — backtesting \
requires multiple quote dates to build entry/exit pairs. Tell the user the data is too sparse and suggest \
fetching a wider date range or using monthly expirations. Otherwise, intelligently adjust parameters based \
on what the data actually contains (e.g. if max DTE in the data is 45, don't set max_entry_dte to 90). \
Retry up to 10 times, changing one or two parameters each attempt. Explain your reasoning to the user each \
time. After 10 failed attempts, report what you tried and suggest the user try a different strategy, date \
range, or expiration type. Never re-fetch data just because a strategy was empty.
- When interpreting aggregated results, focus on: which DTE/OTM buckets are most profitable (highest mean), \
which have enough trades to be statistically meaningful (count > 10), and risk-adjusted performance (mean/std).
- For comparisons, run both strategies and compare mean returns, win rates (% of buckets with positive mean), \
and consistency (lower std is better).
- Be concise but helpful. The tool results are already formatted as markdown tables.

## Avoiding Redundant Strategy Calls
- Before running a strategy when the user has not specified parameters, call \
`suggest_strategy_params` first to get data-anchored DTE/OTM% recommendations. Do not guess.
- When comparing multiple DTE values, OTM% values, or strategies, use `scan_strategies` (one \
call) instead of multiple `run_strategy` calls.
- Before re-running a strategy with parameters you may have tried before, call `list_results` \
to check what combinations were already executed this session.
- `scan_strategies` does not support TA signals or calendar strategies — use `run_strategy` \
for those.
"""


_MAX_TOOL_ITERATIONS = 15

# Tool results longer than this (in chars) get truncated in older messages
# to keep token usage manageable across many iterations.
_COMPACT_THRESHOLD = 300


def _compact_history(messages: list[dict[str, Any]]) -> None:
    """Truncate old tool results and assistant reasoning in-place.

    Called at the start of each iteration (after the first) so previous
    tool outputs — which the LLM has already processed — don't bloat every
    subsequent API call.  Only the *last* tool result and assistant message
    are left intact so the LLM has full context for its next decision.
    """
    # Find indices of all tool-result messages (excluding the last batch)
    tool_indices = [i for i, m in enumerate(messages) if m.get("role") == "tool"]
    # Find indices of all assistant messages with tool_calls (intermediate turns)
    assistant_tc_indices = [
        i
        for i, m in enumerate(messages)
        if m.get("role") == "assistant" and m.get("tool_calls")
    ]

    # Keep the last batch of tool results intact (messages after the last
    # assistant-with-tool-calls message).
    last_assistant_tc = assistant_tc_indices[-1] if assistant_tc_indices else -1
    old_tool_indices = [i for i in tool_indices if i < last_assistant_tc]
    old_assistant_indices = (
        assistant_tc_indices[:-1] if len(assistant_tc_indices) > 1 else []
    )

    for i in old_tool_indices:
        content = messages[i].get("content", "")
        if len(content) > _COMPACT_THRESHOLD:
            # Keep just the first line (e.g. "long_calls — 37 aggregated stats")
            first_line = content.split("\n", 1)[0]
            messages[i]["content"] = first_line + " [truncated]"

    for i in old_assistant_indices:
        content = messages[i].get("content", "")
        if len(content) > _COMPACT_THRESHOLD:
            messages[i]["content"] = content[:_COMPACT_THRESHOLD] + "… [truncated]"


class OptopsyAgent:
    def __init__(self, model: str = "anthropic/claude-haiku-4-5-20251001"):
        self.model = model
        self.tools = get_tool_schemas()
        self.dataset: pd.DataFrame | None = None
        self.signals: dict[str, pd.DataFrame] = {}
        # Named dataset registry — multiple datasets can be active at once.
        # Keys are ticker symbols or filenames; values are DataFrames.
        self.datasets: dict[str, pd.DataFrame] = {}
        # Session-scoped strategy run registry — keyed by result key string,
        # values are lightweight scalar summaries (no DataFrames).
        self.results: dict[str, dict] = {}

    async def chat(
        self,
        messages: list[dict[str, Any]],
        on_tool_call=None,
        on_token=None,
        on_thinking_token=None,
        on_assistant_tool_calls=None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Run the agent loop: send messages to LLM, execute any tool calls,
        and return (final_response_text, updated_messages).

        on_tool_call: async callback(tool_name, arguments, result, tool_call_id)
                      — UI step display.
        on_token: async callback(token_str) — called for each streamed token on
                  the *final* response (the one shown to the user).
        on_thinking_token: async callback(token_str) — called for streamed tokens
                  on intermediate tool-calling turns (reasoning shown separately).
        on_assistant_tool_calls: async callback(tool_calls: list[dict]) — fired
                  when the LLM emits tool_calls so the UI can persist them for
                  session resume.

        Note: The system prompt is prepended on every LLM call so context is
        maintained across tool-calling iterations.  This is intentional but
        means token usage grows with conversation length.  For very long
        sessions consider adding history summarization before calling chat().
        """
        # Use Anthropic prompt caching for the system prompt: mark it with
        # cache_control so it is cached after the first call and not re-billed
        # on subsequent iterations.  LiteLLM passes this header to the API
        # transparently; for non-Anthropic providers the content block form is
        # used as-is without the extra key, so it degrades gracefully.
        system_msg: dict[str, Any]
        if self.model.startswith("anthropic/") or self.model.startswith("claude"):
            system_msg = {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        else:
            system_msg = {"role": "system", "content": SYSTEM_PROMPT}

        full_messages = [system_msg] + messages

        for _iteration in range(_MAX_TOOL_ITERATIONS):
            # Throttle LLM calls: skip delay on the first iteration,
            # pause briefly on subsequent ones to avoid rate-limiting.
            if _iteration > 0:
                await asyncio.sleep(1)
                # Compact previous tool results and assistant reasoning to
                # reduce token usage.  The LLM has already seen these — it
                # only needs a short reminder of what happened.
                _compact_history(full_messages)

            # Stream every LLM turn so the user sees reasoning tokens live,
            # even during intermediate tool-calling iterations.
            # Retry on RateLimitError with exponential backoff (up to 3 attempts).
            content_parts: list[str] = []
            # tool_calls_acc: index -> {id, name, arguments_chunks}
            tool_calls_acc: dict[int, dict[str, Any]] = {}

            _MAX_LLM_RETRIES = 3
            for _attempt in range(_MAX_LLM_RETRIES):
                content_parts = []
                tool_calls_acc = {}
                # On the first attempt stream tokens live to on_thinking_token
                # (intermediate reasoning).  We don't yet know if this is a
                # final turn — that's determined only after the stream ends.
                # On retries, collect silently to avoid garbled partial output.
                live_token_cb = on_thinking_token if _attempt == 0 else None
                try:
                    stream = await litellm.acompletion(
                        model=self.model,
                        messages=full_messages,
                        tools=self.tools,
                        tool_choice="auto",
                        stream=True,
                    )
                    async for chunk in stream:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta is None:
                            continue
                        # Accumulate text content
                        if delta.content:
                            content_parts.append(delta.content)
                            if live_token_cb:
                                await live_token_cb(delta.content)
                        # Accumulate tool call chunks
                        if delta.tool_calls:
                            for tc_chunk in delta.tool_calls:
                                idx = tc_chunk.index
                                if idx not in tool_calls_acc:
                                    tool_calls_acc[idx] = {
                                        "id": "",
                                        "name": "",
                                        "arguments": "",
                                    }
                                if tc_chunk.id:
                                    tool_calls_acc[idx]["id"] = tc_chunk.id
                                if tc_chunk.function:
                                    if tc_chunk.function.name:
                                        tool_calls_acc[idx][
                                            "name"
                                        ] += tc_chunk.function.name
                                    if tc_chunk.function.arguments:
                                        tool_calls_acc[idx][
                                            "arguments"
                                        ] += tc_chunk.function.arguments
                    break  # Success — exit retry loop
                except litellm.AuthenticationError:
                    raise RuntimeError(
                        "No API key configured. Add your LLM provider key "
                        "(e.g. `OPENAI_API_KEY`) to a `.env` file in this directory."
                    )
                except litellm.RateLimitError:
                    if _attempt == _MAX_LLM_RETRIES - 1:
                        raise RuntimeError(
                            "LLM rate limit exceeded after retries. "
                            "Wait a moment and try again, or switch to a model "
                            "with higher rate limits."
                        )
                    backoff = 2**_attempt  # 1s, 2s
                    await asyncio.sleep(backoff)
                except (litellm.ServiceUnavailableError, litellm.APIConnectionError):
                    if _attempt == _MAX_LLM_RETRIES - 1:
                        raise RuntimeError(
                            "LLM service is temporarily unavailable. Please try again shortly."
                        )
                    await asyncio.sleep(2**_attempt)

            content = "".join(content_parts)
            tool_calls_list = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
                for tc in tool_calls_acc.values()
            ]

            # Append assistant message to history
            msg_dict: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls_list:
                msg_dict["tool_calls"] = tool_calls_list
            full_messages.append(msg_dict)

            # Notify the UI so it can persist tool_calls for session resume.
            if tool_calls_list and on_assistant_tool_calls:
                await on_assistant_tool_calls(tool_calls_list)

            # If no tool calls this is the final answer.
            # The content was streamed to on_thinking_token (or silently on
            # retries), so re-emit it to on_token for the main message.
            if not tool_calls_list:
                if on_token and content:
                    for chunk in content_parts:
                        await on_token(chunk)
                return content, full_messages[1:]

            # Execute each tool call
            for tc in tool_calls_list:
                func_name = tc["function"]["name"]
                tc_id = tc["id"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                # Run tool in a thread so the event loop stays alive
                # (keeps WebSocket heartbeats flowing during long fetches).
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda fn=func_name, a=args, ds=self.dataset, sg=self.signals, dss=self.datasets, rs=self.results: execute_tool(
                        fn, a, ds, sg, dss, rs
                    ),
                )
                self.dataset = result.dataset
                if result.signals is not None:
                    self.signals = result.signals
                if result.datasets is not None:
                    self.datasets = result.datasets
                if result.results is not None:
                    self.results = result.results

                # Show the rich version to the user in the UI
                if on_tool_call:
                    await on_tool_call(func_name, args, result.user_display, tc_id)

                # Send only the concise summary to the LLM
                full_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": result.llm_summary,
                    }
                )

        # If we exhausted the iteration limit, return what we have
        raise RuntimeError(
            f"Agent exceeded {_MAX_TOOL_ITERATIONS} tool-calling iterations. "
            "This likely indicates a loop — please simplify your request."
        )
